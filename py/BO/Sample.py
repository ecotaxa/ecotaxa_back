# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A Sample BO + enumerated set of Sample(s)
#
from dataclasses import dataclass
from typing import List, ClassVar, Dict, Optional, Tuple

from DB.Acquisition import Acquisition
from DB.Object import VALIDATED_CLASSIF_QUAL, DUBIOUS_CLASSIF_QUAL, PREDICTED_CLASSIF_QUAL
from DB.Project import ProjectIDListT, Project
from DB.Sample import Sample
from DB.helpers import Session, Result
from DB.helpers.Direct import text
from DB.helpers.ORM import any_
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer
from . import ProjectVarsDefault as DefaultVars
from .Acquisition import AcquisitionIDT, AcquisitionBO
from .Classification import ClassifIDListT, ClassifIDT
from .ColumnUpdate import ColUpdateList
from .Mappings import ProjectMapping
from .Process import ProcessBO
from .helpers.MappedEntity import MappedEntity
from .helpers.MappedTable import MappedTable

SampleIDT = int
SampleIDListT = List[int]  # Typings, to be clear that these are not e.g. project IDs
SampleOrigIDT = str

logger = get_logger(__name__)


@dataclass()
class SampleTaxoStats:
    """
        Taxonomy statistics for a sample.
    """
    sample_id: SampleIDT
    used_taxa: ClassifIDListT
    nb_unclassified: int
    nb_validated: int
    nb_dubious: int
    nb_predicted: int


@dataclass()
class SampleAggregForTaxon:
    """
        Aggregation for a given taxon, inside a sample.
    """
    abundance: int  # i.e. count of organisms
    concentration: Optional[float]
    biovolume: Optional[float]


def _get_proj(sam: Sample) -> Project:
    return sam.project


class SampleBO(MappedEntity):
    """
        A Sample.
    """
    FREE_COLUMNS_ATTRIBUTE: ClassVar = 'sample'
    PROJECT_ACCESSOR: ClassVar = _get_proj
    MAPPING_IN_PROJECT: ClassVar = 'sample_mappings'

    def __init__(self, session: Session, sample_id: SampleIDT):
        super().__init__(session)
        self.sample = session.query(Sample).get(sample_id)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Sample field somehow then return it """
        return getattr(self.sample, item)

    @classmethod
    def get_acquisitions(cls, session: Session, sample: Sample) -> List[Acquisition]:
        """ Get acquisitions for the sample """
        qry = session.query(Acquisition)
        qry = qry.join(Sample)
        qry = qry.filter(Sample.sampleid == sample.sampleid)
        return qry.all()

    @classmethod
    def aggregate_for_sample(cls, session: Session, sample: Sample,
                             morpho2phylo: Optional[Dict[ClassifIDT, ClassifIDT]], with_computations: bool,
                             warnings: List[str]) -> Dict[ClassifIDT, SampleAggregForTaxon]:
        """
            :param session: SQLA DB session for queries.
            :param sample: The Sample for which computations needs to be done.
            :param with_computations: If not set, just do abundance calculations (e.g. to save time
                or when it's known to be impossible).
            :param morpho2phylo: The Morpho taxa to their nearest Phylo parent. If not provided
                then _no_ up-the-taxa-tree consolidation will be done, i.e. there _will be_ Morpho taxa in 'ret' keys.
            :param warnings: Eventual non-blocking problems found.

            Do the aggregations for the given sample for each taxon and return them.
            They will become emofs if used from DWC:
                - 'Abundance' -> CountOfBiologicalEntity -> count of objects group by taxon
                - 'Concentration' -> AbundancePerUnitVolumeOfTheWaterBody
                    -> sum(individual_concentration) group by taxon
                        with individual_concentration = 1 / subsample_coef / total_water_volume
                - 'Biovolume' -> BiovolumeOfBiologicalEntity -> sum(individual_biovolume) group by taxon
                    with individual_biovolume = individual_volume / subsample_coef / total_water_volume
            The abundance can always be computed. The 2 other ones depend on availability of values
                for the project and the configuration variable.
        """
        # We return all _per taxon_.
        ret: Dict[ClassifIDT, SampleAggregForTaxon]

        acquis_for_sample = SampleBO.get_acquisitions(session, sample)

        # Start with abundances, simple count and giving its keys to the returned dict.
        ret, count_per_taxon_per_acquis = cls.aggregate_abundances(session, acquis_for_sample, morpho2phylo)

        if not with_computations:
            return ret

        # Enrich with concentrations
        subsampling_coeff_per_acquis: Dict[AcquisitionIDT, float] = {}
        try:
            # Fetch calculation data at sample level
            sample_volume = SampleBO.get_computed_var(sample, DefaultVars.volume_sampled)
        except TypeError as e:
            warnings.append("Could not compute volume sampled from sample %s (%s),"
                            " no concentration or biovolume will be computed." % (sample.orig_id, str(e)))
            sample_volume = -1
        if sample_volume > 0:
            # Cumulate for subsamples AKA acquisitions
            for an_acquis in acquis_for_sample:
                try:
                    subsampling_coefficient = AcquisitionBO.get_computed_var(an_acquis, DefaultVars.subsample_coeff)
                    subsampling_coeff_per_acquis[an_acquis.acquisid] = subsampling_coefficient
                except TypeError as e:
                    warnings.append("Could not compute subsampling coefficient from acquisition %s (%s),"
                                    " no concentration or biovolume will be computed" %
                                    (an_acquis.orig_id, str(e)))
                    logger.info("concentrations: no subsample coeff for '%s' (%s)", an_acquis.orig_id, str(e))
                    continue
                # Get counts for acquisition (sub-sample)
                logger.info("computing concentrations for '%s'", an_acquis.orig_id)
                count_per_taxon_for_acquis = count_per_taxon_per_acquis[an_acquis.acquisid]
                for an_id, count_4_acquis in count_per_taxon_for_acquis.items():
                    aggreg_for_taxon = ret[an_id]
                    concentration_for_taxon = count_4_acquis / subsampling_coefficient / sample_volume
                    if aggreg_for_taxon.concentration is None:
                        aggreg_for_taxon.concentration = 0
                    aggreg_for_taxon.concentration += concentration_for_taxon

        # Enrich with biovolumes. This needs a computation for each object, so it's likely to be slow.
        if sample_volume > 0:
            # TODO: There are circular references
            from .Object import ObjectBO, ObjectBOSet
            # Mappings are constant for the sample
            # noinspection PyTypeChecker
            mapping = ProjectMapping().load_from_project(sample.project)
            # Cumulate for subsamples AKA acquisitions
            for an_acquis in acquis_for_sample:
                subsampling_coefficient = subsampling_coeff_per_acquis.get(an_acquis.acquisid)
                if subsampling_coefficient is None:
                    logger.info("biovolumes: no subsample coeff for '%s'", an_acquis.orig_id)
                    continue
                # Get pixel size from associated process, it a constant to individual biovol computations
                try:
                    pixel_size, = ProcessBO.get_free_fields(an_acquis.process, ["particle_pixel_size_mm"],
                                                            [float],
                                                            [None])
                except TypeError as _e:
                    logger.info("biovolumes: no pixel size for '%s'", an_acquis.orig_id)
                    continue
                constants = {"pixel_size": pixel_size}
                # Get all objects for the acquisition. The filter on classif_id is useless for now.
                with CodeTimer("Objects IDs for '%s': " % an_acquis.orig_id, logger):
                    acq_object_ids = AcquisitionBO.get_all_object_ids(session=session,
                                                                      acquis_id=an_acquis.acquisid,
                                                                      classif_ids=list(ret.keys()))
                with CodeTimer("Objects for '%s': " % an_acquis.orig_id, logger):
                    objects = ObjectBOSet(session, acq_object_ids, mapping.object_mappings)
                nb_biovols = 0
                for an_obj in objects.all:
                    # Compute a biovol if possible
                    try:
                        biovol = ObjectBO.get_computed_var(an_obj, DefaultVars.equivalent_ellipsoidal_volume,
                                                           mapping, constants)
                        biovol = -1
                    except TypeError as _e:
                        biovol = -1
                    if biovol == -1:
                        try:
                            biovol = ObjectBO.get_computed_var(an_obj, DefaultVars.equivalent_spherical_volume,
                                                               mapping, constants)
                        except TypeError as _e:
                            continue
                    # Aggregate by category/taxon
                    aggreg_for_taxon = ret[an_obj.classif_id]
                    individual_biovolume = biovol / subsampling_coefficient / sample_volume
                    if aggreg_for_taxon.biovolume is None:
                        aggreg_for_taxon.biovolume = 0
                    aggreg_for_taxon.biovolume += individual_biovolume
                    # Update stats
                    nb_biovols += 1
                # A bit of display
                logger.info("%d biovolumes computed for '%s' out of %d objects", nb_biovols, an_acquis.orig_id,
                            len(acq_object_ids))

        return ret

    @classmethod
    def aggregate_abundances(cls, session: Session, acquis_for_sample: List[Acquisition],
                             morpho2phylo: Optional[Dict[ClassifIDT, ClassifIDT]]) \
            -> Tuple[Dict[ClassifIDT, SampleAggregForTaxon], Dict[AcquisitionIDT, Dict[ClassifIDT, int]]]:
        aggreg_per_taxon: Dict[ClassifIDT, SampleAggregForTaxon] = {}
        count_per_taxon_per_acquis: Dict[AcquisitionIDT, Dict[ClassifIDT, int]] = {}
        for an_acquis in acquis_for_sample:
            # Get counts for acquisition (subsample)
            count_per_taxon_for_acquis: Dict[ClassifIDT, int] = AcquisitionBO.get_sums_by_taxon(session,
                                                                                                an_acquis.acquisid)
            if morpho2phylo is not None:
                cls.add_morpho_counts(count_per_taxon_for_acquis, morpho2phylo)
            count_per_taxon_per_acquis[an_acquis.acquisid] = count_per_taxon_for_acquis
            for an_id, count_4_acquis in count_per_taxon_for_acquis.items():
                aggreg_for_taxon = aggreg_per_taxon.get(an_id)
                if aggreg_for_taxon is None:
                    # Create new aggregation data for this taxon
                    aggreg_per_taxon[an_id] = SampleAggregForTaxon(count_4_acquis, None, None)
                else:
                    # Sum if taxon already there
                    aggreg_for_taxon.abundance += count_4_acquis
        return aggreg_per_taxon, count_per_taxon_per_acquis

    @classmethod
    def add_morpho_counts(cls, count_per_taxon_for_acquis: Dict[ClassifIDT, int],
                          morpho2phylo: Dict[ClassifIDT, ClassifIDT]) -> None:
        """
            If there are Morpho taxa with counts, cumulate and wipe them out.
        """
        for an_id, count_4_acquis in dict(count_per_taxon_for_acquis).items():
            phylo_id = morpho2phylo.get(an_id)
            if phylo_id is not None:
                del count_per_taxon_for_acquis[an_id]
                if phylo_id in count_per_taxon_for_acquis:
                    # Accumulate in parent count
                    count_per_taxon_for_acquis[phylo_id] += count_4_acquis
                else:
                    # Create the parent
                    count_per_taxon_for_acquis[phylo_id] = count_4_acquis


class DescribedSampleSet(object):
    """
        A set of samples, so far all of them for a set of projects.
    """

    def __init__(self, session: Session, prj_ids: ProjectIDListT, orig_id_pattern: str):
        self._session = session
        self.prj_ids = prj_ids
        self.pattern = '%' + orig_id_pattern.replace('*', '%') + '%'

    def list(self) -> List[SampleBO]:
        """
            Return all samples from description.
            TODO: No free columns value so far.
        """
        qry = self._session.query(Sample)
        qry = qry.join(Sample, Project.all_samples)
        qry = qry.filter(Project.projid.in_(self.prj_ids))
        qry = qry.filter(Sample.orig_id.ilike(self.pattern))
        return qry.all()


class EnumeratedSampleSet(MappedTable):
    """
        A list of samples, known by their IDs.
    """

    def __init__(self, session: Session, ids: SampleIDListT):
        super().__init__(session)
        self.ids = ids

    def get_projects_ids(self) -> ProjectIDListT:
        """
            Return the project IDs for the held sample IDs.
        """
        qry = self.session.query(Project.projid).distinct(Project.projid)
        qry = qry.join(Sample, Project.all_samples)
        qry = qry.filter(Sample.sampleid == any_(self.ids))
        with CodeTimer("Prjs for %d samples: " % len(self.ids), logger):
            return [an_id for an_id, in qry]

    def apply_on_all(self, project: Project, updates: ColUpdateList) -> int:
        """
            Apply all updates on all samples.
        """
        return self._apply_on_all(Sample, project, updates.lst)

    def add_filter(self, upd):
        return upd.filter(Sample.sampleid == any_(self.ids))

    def read_taxo_stats(self) -> List[SampleTaxoStats]:
        sql = text("""
        SELECT sam.sampleid as sample_id,
               ARRAY_AGG(DISTINCT COALESCE(obh.classif_id, -1)) as used_taxa,
               SUM(CASE WHEN obh.classif_id <> -1 THEN 0 ELSE 1 END) as nb_unclassified,
               COUNT(CASE WHEN obh.classif_qual = '""" + VALIDATED_CLASSIF_QUAL + """' THEN 1 END) nb_validated,
               COUNT(CASE WHEN obh.classif_qual = '""" + DUBIOUS_CLASSIF_QUAL + """' THEN 1 END) nb_dubious, 
               COUNT(CASE WHEN obh.classif_qual = '""" + PREDICTED_CLASSIF_QUAL + """' THEN 1 END) nb_predicted
          FROM obj_head obh
          JOIN acquisitions acq ON acq.acquisid = obh.acquisid 
          JOIN samples sam ON sam.sampleid = acq.acq_sample_id
         WHERE sam.sampleid = ANY(:ids)
         GROUP BY sam.sampleid;""")
        with CodeTimer("Stats for %d samples: " % len(self.ids), logger):
            res: Result = self.session.execute(sql, {'ids': self.ids})
            ret = [SampleTaxoStats(**rec) for rec in res]  # type:ignore # case4
        return ret
