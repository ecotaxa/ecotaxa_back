# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Useful links:
#   - https://github.com/EMODnet/EMODnetBiocheck for doing quality control of DwCA archives
#
# GBIF validator:
#      ../../DwCA/gbif-data-validator/validator-ws/run-prod coll_6512_export.zip
# EMODnet QC source code:
#      https://github.com/EMODnet/EMODnetBiocheck
import datetime
import re
from collections import OrderedDict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, cast, Set, Any
from urllib.parse import quote_plus

import BO.ProjectVarsDefault as DefaultVars
from API_models.exports import ExportRsp, SciExportTypeEnum
from BO.Acquisition import AcquisitionIDT
from BO.Classification import ClassifIDT, ClassifIDSetT
from BO.Collection import CollectionIDT, CollectionBO
from BO.CommonObjectSets import CommonObjectSets
from BO.DataLicense import LicenseEnum, DataLicense
from BO.ObjectSet import DescribedObjectSet
from BO.ObjectSetQueryPlus import ResultGrouping, TaxoRemappingT, ObjectSetQueryPlus
from BO.Project import ProjectBO, ProjectTaxoStats
from BO.Rights import RightsBO
from BO.Sample import SampleBO, SampleAggregForTaxon
from BO.TaxonomySwitch import TaxonomyMapper
from BO.Vocabulary import Vocabulary, Units
from DB.Collection import Collection
from DB.Project import ProjectTaxoStat, ProjectIDT, ProjectIDListT, Project
from DB.Sample import Sample
from DB.Taxonomy import Taxonomy
from DB.User import User, Role
from DB.WoRMs import WoRMS
from DB.helpers.Postgres import timestamp_to_str
from data.Countries import countries_by_name
from formats.DarwinCore.Archive import DwC_Archive, DwcArchive
from formats.DarwinCore.DatasetMeta import DatasetMetadata
from formats.DarwinCore.MoF import (
    SamplingNetMeshSizeInMicrons,
    SampleDeviceApertureAreaInSquareMeters,
    AbundancePerUnitVolumeOfTheWaterBody,
    BiovolumeOfBiologicalEntity,
    SamplingInstrumentName,
    CountOfBiologicalEntity,
    ImagingInstrumentName,
)
from formats.DarwinCore.models import (
    DwC_Event,
    RecordTypeEnum,
    DwC_Occurrence,
    OccurrenceStatusEnum,
    BasisOfRecordEnum,
    IdentificationVerificationEnum,
    EMLGeoCoverage,
    EMLTemporalCoverage,
    EMLMeta,
    EMLTitle,
    EMLPerson,
    EMLKeywordSet,
    EMLTaxonomicClassification,
    EMLAdditionalMeta,
    EMLIdentifier,
    EMLAssociatedPerson,
)
from helpers.DateTime import now_time
from helpers.DynamicLogs import get_logger, LogsSwitcher
# TODO: Move somewhere else
from ..helpers.JobService import JobServiceBase, ArgsDict

logger = get_logger(__name__)

AbundancePerAcquisitionT = Dict[AcquisitionIDT, Dict[ClassifIDT, int]]
LsidT = str  # Life Science Identifier @see https://en.wikipedia.org/wiki/LSID


class DarwinCoreExport(JobServiceBase):
    """
    EMODNet export.
    Help during development:
        http://tools.gbif.org/dwca-assistant/
    Output validation:
        Before IPT publishing:
            https://www.gbif.org/fr/tools/data-validator/
        After IPT publishing
            http://rshiny.lifewatch.be/BioCheck/
    """

    JOB_TYPE = "DarwinCoreExport"

    def init_args(self, args: ArgsDict) -> ArgsDict:
        # A bit unusual to find a method before init(), but here we can visually ensure
        # that arg lists are identical.
        args.update(
            {
                "collection_id": self.collection.id,
                "dry_run": self.dry_run,
                "taxo_recast": self.taxo_recast,
                "include_predicted": self.include_predicted,
                "with_absent": self.with_absent,
                "with_computations": self.with_computations,
                "formulae": self.formulae,
            }
        )
        return args

    def __init__(
        self,
        collection_id: CollectionIDT,
        dry_run: bool,
        taxo_recast: TaxoRemappingT,
        include_predicted: bool,
        with_absent: bool,
        with_computations: List[SciExportTypeEnum],
        formulae: Dict[str, str],
    ):
        super().__init__()
        # Old param now constant
        self.auto_morpho = True
        # Input params
        collection = self.ro_session.query(Collection).get(collection_id)
        assert collection is not None, "Invalid collection ID"
        self.collection = collection
        self.dry_run = dry_run
        self.include_predicted = include_predicted
        # Args are serialized in JSON -> keys have become str
        self.taxo_recast: TaxoRemappingT = {int(k): v for k, v in taxo_recast.items()}
        # Output params
        self.with_absent = with_absent
        self.with_computations = with_computations
        if len(formulae) == 0 and len(with_computations) > 0:
            assert False, "Need formulae for " + str(with_computations)
        # TODO: We have all this at project level now, but how to mix with API?
        self.formulae = formulae
        #
        # During processing
        #
        # The Phylo taxa to their WoRMS counterpart
        self.phylo2worms: Dict[ClassifIDT, WoRMS] = {}
        # The Morpho taxa to their nearest Phylo parent
        # Is computed always for taxonomic coverage
        self.morpho2phylo: TaxoRemappingT = {}
        self.taxa_per_sample: Dict[str, Set[ClassifIDT]] = {}
        # Output
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # Summary for logging issues
        self.validated_count = 0
        self.predicted_count = 0
        self.produced_count = 0
        self.ignored_count: Dict[ClassifIDT, int] = {}
        self.ignored_morpho: int = 0
        self.ignored_taxa: Dict[ClassifIDT, Tuple[ClassifIDT, str]] = {}
        self.unknown_nets: Dict[str, List[str]] = {}
        self.empty_samples: List[Tuple[ProjectIDT, str]] = []
        self.stats_per_rank: Dict[str, Dict[str, Any]] = {}
        self.suspicious_vals: Dict[str, List[str]] = {}

    DWC_ZIP_NAME = "dwca.zip"
    PRODUCED_FILE_NAME = DWC_ZIP_NAME

    def run(self, current_user_id: int) -> ExportRsp:
        """
        Initial run, basically just create the job.
        """
        # TODO, for now only admins
        _user = RightsBO.user_has_role(
            self.ro_session, current_user_id, Role.APP_ADMINISTRATOR
        )
        # OK, go background straight away
        self.create_job(self.JOB_TYPE, current_user_id)
        ret = ExportRsp(job_id=self.job_id)
        return ret

    def do_background(self) -> None:
        """
        Background part of the job.
        """
        with LogsSwitcher(self):
            self.do_export()

    def do_export(self) -> None:
        # Security check
        # Do the job
        logger.info("------------ starting --------------")
        # Update DB statistics
        self.update_db_stats()
        # Build metadata with what comes from the collection
        meta = self.build_meta()
        if meta is None:
            # If we can't have meta there has to be reasons
            assert len(self.errors) > 0
            self.set_job_result(self.errors, {"wrns": self.warnings})
            return
        # Create a container
        # TODO: Duplicated code
        arch = DwC_Archive(
            DatasetMetadata(meta),
            self.temp_for_jobs.base_dir_for(self.job_id) / self.DWC_ZIP_NAME,
        )
        # Add data from DB
        # OK because https://edmo.seadatanet.org/v_edmo/browse_step.asp?step=003IMEV_0021
        # But TODO: hardcoded, implement https://github.com/oceanomics/ecotaxa_dev/issues/514
        self.institution_code = "IMEV"
        self.add_events(arch)
        # Loop over _absent_ data
        # For https://github.com/ecotaxa/ecotaxa_dev/issues/603
        # Loop over taxa which are in the collection but not in present sample
        if self.with_absent:
            self.add_absent_occurrences(arch)
        # OK we issue warning in case of individual issue, but if there is no content at all
        # then it's an error
        if (
            arch.events.count() == 0
            and arch.occurences.count() == 0
            and arch.emofs.count() == 0
        ):
            self.errors.append(
                "No content produced."
                " See previous warnings or check the presence of samples in the projects"
            )
        else:
            # Produce the zip
            arch.build()
            self.log_stats()
        self.set_job_result(self.errors, {"wrns": self.warnings})

    def add_absent_occurrences(self, arch: DwcArchive) -> None:
        """
        Second pass, occurrence creations for absent taxa.
        """
        all_taxa = self.compute_all_seen_taxa()
        # For what's missing, issue an 'absent' record
        for an_event_id, an_id_set in self.taxa_per_sample.items():
            missing_for_sample = all_taxa.difference(an_id_set)
            for a_missing_id in missing_for_sample:
                occurrence_id = an_event_id + "_" + str(a_missing_id)
                # No need to catch any exception here, the lookup worked during the
                # "present" records generation.
                worms = self.phylo2worms[a_missing_id]
                occ = DwC_Occurrence(
                    eventID=an_event_id,
                    occurrenceID=occurrence_id,
                    individualCount=0,
                    scientificName=worms.scientificname,
                    scientificNameID=worms.lsid,
                    kingdom=worms.kingdom,
                    occurrenceStatus=OccurrenceStatusEnum.absent,
                    basisOfRecord=BasisOfRecordEnum.machineObservation,
                )
                arch.occurences.add(occ)

    def compute_all_seen_taxa(self) -> ClassifIDSetT:
        # Cumulate all categories
        all_taxa: ClassifIDSetT = set()
        for an_id_set in self.taxa_per_sample.values():
            all_taxa.update(an_id_set)
        return all_taxa

    @staticmethod
    def organisation_to_eml_person(an_org: str) -> EMLPerson:
        return EMLPerson(organizationName=an_org)

    @staticmethod
    def capitalize_name(name: str) -> str:
        """
        e.g. JEAN -> Jean
        but as well JEAN-MARC -> Jean-Marc
        and even FOo--BAR -> Foo--Bar
        """
        return "".join([a_word.capitalize() for a_word in re.split(r"(\W+)", name)])

    @staticmethod
    def user_to_eml_person(
        user: Optional[User], for_messages: str
    ) -> Tuple[Optional[EMLPerson], List[str]]:
        """
        Build & return an EMLPerson entity from a DB User one.
        """
        problems = []
        ret = None

        if user is None:
            problems.append("No %s at all" % for_messages)
            return ret, problems

        if not user.organisation:
            problems.append(
                "%s user '%s' has no organization (it should contain a - )."
                % (for_messages, user.name)
            )
        else:
            try:
                _dummy, organization = user.organisation.strip().split("-")
                organization = organization.strip()
            except ValueError:
                problems.append(
                    "Cannot determine short organization from %s org: '%s' (need a - )."
                    % (for_messages, user.organisation)
                )

        # TODO: Organization should fit from https://edmo.seadatanet.org/search

        try:
            # Try to get name+sur_name from stored value
            name, sur_name = user.name.strip().split(" ", 1)
        except ZeroDivisionError:
            problems.append(
                "Cannot determine name+surname from %s name: %s."
                % (for_messages, user.name)
            )
        else:
            name, sur_name = DarwinCoreExport.capitalize_name(
                name
            ), DarwinCoreExport.capitalize_name(sur_name)

        try:
            country = countries_by_name[user.country]
        except KeyError:
            problems.append(
                "Unknown country name for %s: %s." % (for_messages, user.country)
            )
        else:
            country_name = country["alpha_2"]

        if len(problems) == 0:
            # noinspection PyUnboundLocalVariable
            ret = EMLPerson(
                organizationName=organization,
                givenName=name,
                surName=sur_name,
                country=country_name,
            )
            # Optional but useful field
            if "@" in user.email:
                ret.electronicMailAddress = user.email
        return ret, problems

    @staticmethod
    def eml_person_to_associated_person(
        in_model: EMLPerson, role: str
    ) -> EMLAssociatedPerson:
        return EMLAssociatedPerson(
            organizationName=in_model.organizationName,
            givenName=in_model.givenName,
            surName=in_model.surName,
            country=in_model.country,
            role=role,
        )

    MIN_ABSTRACT_CHARS = 256
    """ Minimum size of a 'quality' abstract """

    OK_LICENSES = [LicenseEnum.CC0, LicenseEnum.CC_BY, LicenseEnum.CC_BY_NC]

    def build_meta(self) -> Optional[EMLMeta]:
        """
        Various queries/copies on/from the projects for getting metadata.
        """
        ret = None
        the_collection: CollectionBO = CollectionBO(self.collection).enrich()

        identifier = EMLIdentifier(
            packageId=the_collection.external_id,
            system=the_collection.external_id_system,
        )

        title = EMLTitle(title=the_collection.title)

        creators: List[EMLPerson] = []
        for a_user in the_collection.creator_users:
            person, errs = self.user_to_eml_person(a_user, "creator '%s'" % a_user.name)
            if errs:
                self.warnings.extend(errs)
            else:
                assert person is not None
                creators.append(person)
        for an_org in the_collection.creator_organisations:
            creators.append(self.organisation_to_eml_person(an_org))
        if len(creators) == 0:
            self.errors.append(
                "No valid data creator (user or organisation) found for EML metadata."
            )

        contact, errs = self.user_to_eml_person(the_collection.contact_user, "contact")
        if contact is None:
            self.errors.append("No valid contact user found for EML metadata.")

        provider, errs = self.user_to_eml_person(
            the_collection.provider_user, "provider"
        )
        if provider is None:
            self.errors.append(
                "No valid metadata provider user found for EML metadata."
            )

        associates: List[EMLPerson] = []
        for a_user in the_collection.associate_users:
            person, errs = self.user_to_eml_person(
                a_user, "associated person %d" % a_user.id
            )
            if errs:
                self.warnings.extend(errs)
            else:
                assert person is not None
                associates.append(
                    self.eml_person_to_associated_person(person, "originator")
                )
        for an_org in the_collection.associate_organisations:
            # noinspection PyTypeChecker
            associates.append(self.organisation_to_eml_person(an_org))

        # TODO if needed
        # EMLAssociatedPerson = EMLPerson + specific role

        # TODO: a marine regions substitute
        (min_lat, max_lat, min_lon, max_lon) = ProjectBO.get_bounding_geo(
            self.session, the_collection.project_ids
        )
        geo_cov = EMLGeoCoverage(
            geographicDescription="See coordinates",
            westBoundingCoordinate=self.geo_to_txt(min_lon),
            eastBoundingCoordinate=self.geo_to_txt(max_lon),
            northBoundingCoordinate=self.geo_to_txt(min_lat),
            southBoundingCoordinate=self.geo_to_txt(max_lat),
        )

        (min_date, max_date) = ProjectBO.get_date_range(
            self.session, the_collection.project_ids
        )
        time_cov = EMLTemporalCoverage(
            beginDate=timestamp_to_str(min_date), endDate=timestamp_to_str(max_date)
        )

        publication_date = now_time().date().isoformat()

        abstract = the_collection.abstract
        if not abstract:
            self.errors.append("Collection 'abstract' field is empty")
        elif len(abstract) < self.MIN_ABSTRACT_CHARS:
            self.errors.append(
                "Collection 'abstract' field is too short (%d chars) to make a good EMLMeta abstract. Minimum is %d"
                % (len(abstract), self.MIN_ABSTRACT_CHARS)
            )

        additional_info = None  # Just to see if it goes thru QC
        # additional_info = """  marine, harvested by iOBIS.
        # The OOV supported the financial effort of the survey.
        # We are grateful to the crew of the research boat at OOV that collected plankton during the temporal survey."""

        coll_license: LicenseEnum = cast(LicenseEnum, the_collection.license)
        if coll_license not in self.OK_LICENSES:
            self.errors.append(
                "Collection license should be one of %s to be accepted, not %s."
                % (self.OK_LICENSES, coll_license)
            )
        else:
            lic_url = DataLicense.EXPORT_EXPLANATIONS[coll_license] + "legalcode"
            lic_txt = DataLicense.NAMES[coll_license]
            lic_txt = lic_txt.replace("International Public ", "")
            # ipt.gbif.org does not find the full license name, so adjust a bit
            version = "4.0"
            if version in lic_txt:
                lic_txt = lic_txt.replace(
                    version, "(%s) " % DataLicense.SHORT_NAMES[coll_license] + version
                )
            licence = (
                'This work is licensed under a <ulink url="%s"><citetitle>%s</citetitle></ulink>.'
                % (lic_url, lic_txt)
            )

        # Preferably one of https://www.emodnet-biology.eu/contribute?page=list&subject=thestdas&SpColID=552&showall=1#P
        keywords = EMLKeywordSet(
            keywords=[
                "Plankton",
                "Imaging",
                "EcoTaxa"  # Not in list above
                # "Ligurian sea" TODO: Geo area?
                # TODO: ZooProcess (from projects)
            ],
            keywordThesaurus="GBIF Dataset Type Vocabulary: "
            "http://rs.gbif.org/vocabulary/gbif/dataset_type.xml",
        )

        taxo_cov = self.get_taxo_coverage(the_collection.project_ids)

        now = now_time().replace(microsecond=0)
        meta_plus = EMLAdditionalMeta(dateStamp=now.isoformat())

        coll_title = the_collection.title
        info_url = (
            "https://ecotaxa.obs-vlfr.fr/api/collections/by_title?q=%s"
            % quote_plus(coll_title)
        )

        if len(self.errors) == 0:
            # The research project
            # noinspection PyUnboundLocalVariable
            # project = EMLProject(title=the_collection.title,
            #                      personnel=[])  # TODO: Unsure about duplicated information with metadata
            # noinspection PyUnboundLocalVariable
            ret = EMLMeta(
                identifier=identifier,
                titles=[title],
                creators=creators,
                contacts=[contact],
                metadataProviders=[provider],
                associatedParties=associates,
                pubDate=publication_date,
                abstract=[abstract],
                keywordSet=keywords,
                additionalInfo=additional_info,
                geographicCoverage=geo_cov,
                temporalCoverage=time_cov,
                taxonomicCoverage=taxo_cov,
                intellectualRights=licence,
                # project=project,
                maintenance="periodic review of origin data",
                maintenanceUpdateFrequency="unknown",  # From XSD
                additionalMetadata=meta_plus,
                informationUrl=info_url,
            )
        return ret

    def get_taxo_coverage(
        self, project_ids: ProjectIDListT
    ) -> List[EMLTaxonomicClassification]:
        """
        Taxonomic coverage is the list of taxa which can be found in the projects, regardless
        of their validation state.
        """
        ret: List[EMLTaxonomicClassification] = []
        # Fetch the used taxa in the projects
        taxo_qry = self.session.query(ProjectTaxoStat.id).distinct()
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.nbr > 0)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.id > 0)  # Exclude unclassified
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.projid.in_(project_ids))
        used_taxa = {an_id for an_id, in taxo_qry}
        # The recast destination taxa might appear in coverage
        recast_taxa = used_taxa.copy()
        for from_, to_ in self.taxo_recast.items():
            if from_ in used_taxa:
                recast_taxa.discard(from_)
                if to_ is not None:
                    recast_taxa.add(to_)
        # Map them to WoRMS
        self.phylo2worms, self.morpho2phylo = TaxonomyMapper(
            self.ro_session, list(recast_taxa)
        ).do_match()
        # Sanity check that no mapped P taxon is present anymore in the transformation to WoRMS
        assert set(self.phylo2worms.keys()).isdisjoint(set(self.morpho2phylo.keys()))
        # Update recast to apply during calculations
        full_recast: TaxoRemappingT = {}
        provided_recast = self.taxo_recast.copy()
        for from_, to_ in self.morpho2phylo.items():
            if to_ in provided_recast:
                # The target phylo is a recast source
                recast_to = provided_recast[to_]
                if recast_to is not None:
                    full_recast[from_] = recast_to
                else:
                    full_recast[from_] = None  # Drop entry
                del provided_recast[from_]
            elif from_ in provided_recast:
                # The source morpho is a recast source
                # Override with provided recast, if None then drop it's OK
                full_recast[from_] = provided_recast[from_]
                del provided_recast[from_]
            else:
                # No impact on this entry from provided recast
                full_recast[from_] = to_
        # Re-inject what's left
        full_recast.update(provided_recast)
        self.morpho2phylo = full_recast
        # Warnings for non-matches
        for an_id in recast_taxa:
            if an_id not in self.phylo2worms:
                if an_id not in self.morpho2phylo:
                    txon = self.session.get(Taxonomy, an_id)
                    assert txon is not None
                    self.ignored_taxa[an_id] = (an_id, txon.name)
                    self.ignored_count[an_id] = 0
        # TODO: Temporary until the whole system has a WoRMS taxo tree
        # Error out if nothing at all
        if len(self.phylo2worms) == 0:
            self.errors.append(
                "Could not match in WoRMS _any_ classification in this project"
            )
            return ret
        # Produce the coverage
        produced = set()
        for _an_id, a_worms_entry in self.phylo2worms.items():
            assert a_worms_entry is not None, "None for %d" % _an_id
            rank = a_worms_entry.rank
            value = a_worms_entry.scientificname
            assert rank is not None, "No name for %d" % _an_id
            tracked = (rank, value)
            if tracked not in produced:
                ret.append(
                    EMLTaxonomicClassification(taxonRankName=rank, taxonRankValue=value)
                )
                produced.add(tracked)
        return ret

    @staticmethod
    def geo_to_txt(lat_or_lon: float) -> str:
        # Round coordinates to ~ 110mm
        return "%.6f" % lat_or_lon

    def add_events(self, arch: DwC_Archive) -> None:
        """
        Add DwC events into the archive.
            We produce sample-type events.
        """
        # TODO: Dup code
        the_collection: CollectionBO = CollectionBO(self.collection).enrich()

        ds_name = self.sanitize_title(self.collection.title)
        for a_prj_id in the_collection.project_ids:
            samples = Sample.get_orig_id_and_model(self.ro_session, prj_id=a_prj_id)
            a_sample: Sample
            events = arch.events
            for orig_id, a_sample in samples.items():
                assert a_sample.latitude is not None and a_sample.longitude is not None
                event_id = orig_id
                evt_type = RecordTypeEnum.sample
                summ = Sample.get_sample_summary(self.session, a_sample.sampleid)
                if summ[0] is None or summ[1] is None:
                    self.empty_samples.append((a_prj_id, a_sample.orig_id))
                    continue
                evt_date = self.event_date(summ[0], summ[1])
                latitude = self.geo_to_txt(float(a_sample.latitude))
                longitude = self.geo_to_txt(float(a_sample.longitude))
                evt = DwC_Event(
                    eventID=event_id,
                    type=evt_type,
                    institutionCode=self.institution_code,
                    datasetName=ds_name,
                    eventDate=evt_date,
                    decimalLatitude=latitude,
                    decimalLongitude=longitude,
                    minimumDepthInMeters=str(summ[2]),
                    maximumDepthInMeters=str(summ[3]),
                )
                events.add(evt)
                self.add_eMoFs_for_sample(sample=a_sample, arch=arch, event_id=event_id)
                # Humans first :)
                nb_added = self.add_occurences(
                    sample=a_sample, arch=arch, event_id=event_id, predicted=False
                )
                if self.include_predicted:
                    by_ml = self.add_occurences(
                        sample=a_sample, arch=arch, event_id=event_id, predicted=True
                    )
                    nb_added += by_ml
                if nb_added == 0:
                    self.warnings.append(
                        "No occurrence added for sample '%s' in project #%d"
                        % (a_sample.orig_id, a_prj_id)
                    )
                self.add_instrument_eMoFs_for_sample(
                    sample=a_sample, arch=arch, event_id=event_id
                )

    nine_nine_re = re.compile("999+.0$")

    # The nets in dataset but no official BODC definition
    bodc_unknown_nets = {
        "jb": "Juday-Bogorov net",
        "regent": "Regent net",
        "rg": "Regent net",
    }

    # noinspection PyPep8Naming
    def add_eMoFs_for_sample(
        self, sample: Sample, arch: DwC_Archive, event_id: str
    ) -> None:
        """
        Add eMoF instances, for given sample, i.e. event, into the archive.
        """
        # emof = SamplingSpeed(event_id, "2")
        # arch.emofs.add(emof)
        try:
            total_water_volume = SampleBO.get_computed_var(
                sample, DefaultVars.volume_sampled
            )
        except (TypeError, ValueError) as _e:
            pass
        else:
            if self.nine_nine_re.match(str(total_water_volume)):
                self.suspicious_vals.setdefault("total_water_volume", []).append(
                    str(total_water_volume) + " in " + sample.orig_id
                )
            # Add sampled water volume
            # 13/04/2021: Removed as it might give the impression that the individual count is
            # the number found inside the volume, when there is subsampling involved.
            # if total_water_volume > 0:
            #     arch.emofs.add(SampleVolumeInCubicMeters(event_id, str(total_water_volume)))

        # Get the net features from the sample
        try:
            net_type, net_mesh, net_surf = SampleBO.get_free_fields(
                sample,
                ["net_type", "net_mesh", "net_surf"],
                [str, float, float],
                ["", -1, -1],
            )
        except TypeError as e:
            self.warnings.append(
                "Could not extract sampling net name and features from sample %s (%s)."
                % (sample.orig_id, str(e))
            )
        else:
            ins = None
            if net_type == "bongo":
                # TODO: There could be more specific, a dozen of bongos are there:
                #  http://vocab.nerc.ac.uk/collection/L22/current/
                ins = SamplingInstrumentName(
                    event_id,
                    "Bongo net",
                    "http://vocab.nerc.ac.uk/collection/L22/current/NETT0176/",
                )
            elif net_type == "wp2":
                if net_mesh == 200 and net_surf == 0.25:  # 0.2 mm
                    ins = SamplingInstrumentName(
                        event_id,
                        "WP-2 net",
                        "http://vocab.nerc.ac.uk/collection/L22/current/TOOL0979/",
                    )
                else:
                    ins = SamplingInstrumentName(
                        event_id,
                        "WP-2-style net",
                        "http://vocab.nerc.ac.uk/collection/L22/current/TOOL0980/",
                    )
            elif net_type == "multinet":
                ins = SamplingInstrumentName(
                    event_id,
                    "multinet",
                    "http://vocab.nerc.ac.uk/collection/L05/current/68/",
                )
            elif net_type in self.bodc_unknown_nets:
                # Quoting RP from VLIZ: "In case you can’t find a term in BODC, we recommend to leave
                # the measurementValueID field empty until BODC has created that term, instead of populating it
                # with more generic terms such as “plankton nets” in order to not mask the “issue (lack a suitable term)”.
                # Also measurementValue would be “Regent net” and “Juday-Bogorov net” respectively
                value = self.bodc_unknown_nets[net_type]
                ins = SamplingInstrumentName(event_id, value, "")
            else:
                self.unknown_nets.setdefault(net_type, []).append(sample.orig_id)
            if ins is not None:
                arch.emofs.add(ins)
            # Produce net traits even if no net
            arch.emofs.add(SamplingNetMeshSizeInMicrons(event_id, str(net_mesh)))
            arch.emofs.add(
                SampleDeviceApertureAreaInSquareMeters(event_id, str(net_surf))
            )

    @lru_cache(maxsize=None)
    def _get_instrument_url(self, project: Project):
        """Cache projects' instrument URL"""
        ret = project.instrument.bodc_url
        if ret is None:
            self.warnings.append(
                "Project %s instrument does not have an associated BODC term."
                % (project.projid,)
            )
        return ret

    def add_instrument_eMoFs_for_sample(
        self, sample: Sample, arch: DwC_Archive, event_id: str
    ) -> None:
        """
        Add imaging instrument eMoF. Unsure at which level the event should be, so kept separated.
        """
        instrument_url = self._get_instrument_url(sample.project)
        if instrument_url is not None:
            ins = ImagingInstrumentName(event_id=event_id, value=instrument_url)
            arch.emofs.add(ins)

    def _aggregate_for_sample(
        self,
        sample: Sample,
        morpho2phylo: TaxoRemappingT,
        with_computations: List[SciExportTypeEnum],
        predicted: bool,
    ) -> Dict[ClassifIDT, SampleAggregForTaxon]:
        """
        :param sample: The Sample for which computations needs to be done.
        :param with_computations: Computations to do.
        :param morpho2phylo: The Morpho taxa to their nearest Phylo parent. If not provided
            then _no_ up-the-taxa-tree consolidation will be done, i.e. there _will be_ Morpho taxa in 'ret' keys.

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
        ret: Dict[ClassifIDT, SampleAggregForTaxon] = {}

        # The source data. Note: I know it could be simplified by passing the 'P' or 'V' filter.
        if predicted:
            object_set = CommonObjectSets.predictedInSample(self.ro_session, sample)
        else:
            object_set = CommonObjectSets.validatedInSample(self.ro_session, sample)

        # TODO but the tests assume that: anything here -> go for abundances
        #  if SciExportTypeEnum.abundances in with_computations:
        if True:
            # Abundances, 'simple' count but eventually with remapping
            counts = self.abundances_for_sample(object_set, morpho2phylo)
            for a_count in counts:
                ret[a_count["txo_id"]] = SampleAggregForTaxon(
                    a_count["count"], None, None
                )

        if SciExportTypeEnum.concentrations in with_computations:
            # Enrich with concentrations
            concentrations = self.concentrations_for_sample(
                self.formulae, object_set, morpho2phylo
            )
            conc_wrn_txos = []
            for a_conc in concentrations:
                txo_id, conc = a_conc["txo_id"], a_conc["conc"]
                if conc == conc:  # NaN test
                    ret[txo_id].concentration = conc
                else:
                    conc_wrn_txos.append(txo_id)
            if len(conc_wrn_txos) > 0:
                wrn = "Sample '{}' taxo(s) #{}: Computed concentration is NaN, input data is missing or incorrect"
                wrn = wrn.format(sample.orig_id, conc_wrn_txos)
                self.warnings.append(wrn)

        if SciExportTypeEnum.biovols in with_computations:
            # Enrich with biovolumes, note that we need previous formulae for scaling
            biovolumes = self.biovolumes_for_sample(
                self.formulae, object_set, morpho2phylo
            )
            biovol_wrn_txos = []
            for a_biovol in biovolumes:
                txo_id, biovol = a_biovol["txo_id"], a_biovol["biovol"]
                if biovol == biovol:  # NaN test
                    ret[txo_id].biovolume = biovol
                else:
                    biovol_wrn_txos.append(txo_id)
            if len(biovol_wrn_txos) > 0:
                wrn = "Sample '{}' taxo(s) #{}: Computed biovolume is NaN, input data is missing or incorrect"
                wrn = wrn.format(sample.orig_id, biovol_wrn_txos)
                self.warnings.append(wrn)

        return ret

    def abundances_for_sample(
        self, obj_set: DescribedObjectSet, morpho2phylo: TaxoRemappingT
    ) -> List[Dict[str, Any]]:
        """
        Compute abundances (count) for given sample.
        """
        aug_qry = ObjectSetQueryPlus(obj_set)
        aug_qry.remap_categories(morpho2phylo)
        aug_qry.add_selects(["txo.id", aug_qry.COUNT_STAR])
        aug_qry.set_aliases(
            {"txo.id": "txo_id", aug_qry.COUNT_STAR: "count"}
        ).set_grouping(ResultGrouping.BY_TAXO)
        return aug_qry.get_result(self.ro_session, lambda e: self.warnings.append(e))

    def concentrations_for_sample(
        self,
        formulae: Dict[str, str],
        obj_set: DescribedObjectSet,
        morpho2phylo: TaxoRemappingT,
    ) -> List[Dict[str, Any]]:
        """
        Compute concentration of each taxon for given sample.
        """
        aug_qry = ObjectSetQueryPlus(obj_set)
        aug_qry.remap_categories(morpho2phylo)
        aug_qry.set_formulae(formulae)
        sum_formula = "sql_count/subsample_coef/total_water_volume"
        aug_qry.set_aliases(
            {
                "txo.id": "txo_id",
                "acq.acquisid": "acq_id",
                aug_qry.COUNT_STAR: "sql_count",
                sum_formula: "conc",
            }
        )
        aug_qry.add_selects(["txo.id", "acq.acquisid"]).set_grouping(
            ResultGrouping.BY_SUBSAMPLE_AND_TAXO
        )
        aug_qry.aggregate_with_computed_sum(
            sum_formula, Vocabulary.concentrations, Units.number_per_cubic_metre
        )
        return aug_qry.get_result(self.ro_session, lambda e: self.warnings.append(e))

    def biovolumes_for_sample(
        self,
        formulae: Dict[str, str],
        obj_set: DescribedObjectSet,
        morpho2phylo: TaxoRemappingT,
    ) -> List[Dict[str, Any]]:
        """
        Compute biovolume of each taxon for given sample.
        """
        aug_qry = ObjectSetQueryPlus(obj_set)
        aug_qry.remap_categories(morpho2phylo)
        aug_qry.set_formulae(formulae)
        sum_formula = "individual_volume/subsample_coef/total_water_volume"
        aug_qry.set_aliases({"txo.id": "txo_id", sum_formula: "biovol"})
        aug_qry.add_selects(["txo.id"]).aggregate_with_computed_sum(
            sum_formula, Vocabulary.biovolume, Units.cubic_millimetres_per_cubic_metre
        )
        aug_qry.set_grouping(ResultGrouping.BY_TAXO)
        return aug_qry.get_result(self.ro_session, lambda e: self.warnings.append(e))

    def add_occurences(
        self, sample: Sample, arch: DwC_Archive, event_id: str, predicted: bool
    ) -> int:
        """
        Add DwC occurrences, for given sample, into the archive. A single line per WoRMS taxon.
        If 'predicted' is set, do the counts on predicted (but not validated) objects.
        Otherwise, use human-validated objects.
        """
        aggregs = self._aggregate_for_sample(
            sample=sample,
            morpho2phylo=self.morpho2phylo if self.auto_morpho else {},
            with_computations=self.with_computations,
            predicted=predicted,
        )

        # Group by lsid, in order to have a single occurrence
        by_lsid: Dict[LsidT, Tuple[str, SampleAggregForTaxon, WoRMS]] = {}
        for an_id, an_aggreg in aggregs.items():
            try:
                worms = self.phylo2worms[an_id]
            except KeyError:
                # Mapping failed, count how many of them
                if an_id in self.ignored_count:
                    self.ignored_count[an_id] += an_aggreg.abundance
                else:
                    # Sanity check, there should be no morpho left
                    if self.auto_morpho:
                        assert an_id not in self.morpho2phylo
                    self.ignored_morpho += an_aggreg.abundance
                continue
            worms_lsid = worms.lsid
            assert worms_lsid is not None
            if worms_lsid in by_lsid:
                # Manage here the mapping of _several_ EcoTaxa taxa to a _single_ Worms entry.
                # e.g. jb20140319_72396_92230
                # is because both 72396 (Diphyidae) and 92230 (Diphyidae>bract)
                #    become Diphyidae 135338 (https://www.marinespecies.org/aphia.php?p=taxdetails&id=135338)
                occurrence_id, aggreg_for_lsid, _worms = by_lsid[worms_lsid]
                # Accumulate abundance
                aggreg_for_lsid.abundance += an_aggreg.abundance
                # Add the new taxon ID to complete the occurrence ID
                occurrence_id += "_" + str(an_id)
                by_lsid[worms_lsid] = (occurrence_id, aggreg_for_lsid, worms)
            else:
                # Take the original taxo ID to build an occurrence
                # It's unique because it's based on the sample ID, and we append the taxon EcoTaxa ID
                occurrence_id = (
                    event_id + ("_P" if predicted else "") + "_" + str(an_id)
                )
                by_lsid[worms_lsid] = (occurrence_id, an_aggreg, worms)

        # Sort per abundance desc
        # noinspection PyTypeChecker
        by_lsid_desc = OrderedDict(
            sorted(by_lsid.items(), key=lambda itm: itm[1][1].abundance, reverse=True)
        )
        # Record production for this sample i.e. event
        self.taxa_per_sample[event_id] = set()
        # Loop over WoRMS taxa
        nb_added_occurences = 0
        for a_lsid, for_lsid in by_lsid_desc.items():
            occurrence_id, aggreg_for_lsid, worms = for_lsid
            self.produced_count += aggreg_for_lsid.abundance
            occ = DwC_Occurrence(
                eventID=event_id,
                occurrenceID=occurrence_id,
                # Below is better as an EMOF @see CountOfBiologicalEntity
                # individualCount=individual_count,
                scientificName=worms.scientificname,
                scientificNameID=worms.lsid,
                kingdom=worms.kingdom,
                occurrenceStatus=OccurrenceStatusEnum.present,
                basisOfRecord=BasisOfRecordEnum.machineObservation,
            )
            if self.include_predicted:
                # TODO: More in record depends on the status (validated or just predicted),
                #  not just identificationVerificationStatus
                # @see https://github.com/ecotaxa/ecotaxa_front/issues/764#issuecomment-1420324532
                verif_status = (
                    IdentificationVerificationEnum.predictedByMachine
                    if predicted
                    else IdentificationVerificationEnum.validatedByHuman
                )
                occ.identificationVerificationStatus = verif_status
            arch.occurences.add(occ)
            nb_added_occurences += 1
            # Add eMoFs if possible and required, but the decision is made inside the def
            self.add_eMoFs_for_occurence(
                arch=arch,
                event_id=event_id,
                occurrence_id=occurrence_id,
                values=aggreg_for_lsid,
            )
            # TODO
            # if self.with_zeroes:
            #     # Record the production of a 'present' occurence for this taxon
            #     self.taxa_per_sample[event_id].add(an_id)
        return nb_added_occurences

    @staticmethod
    def add_eMoFs_for_occurence(
        arch: DwC_Archive,
        event_id: str,
        occurrence_id: str,
        values: SampleAggregForTaxon,
    ) -> None:
        """
        Add eMoF instances, for given occurrence, into the archive.
        Conditions are: - the value exists
                        - the value was required by the call
        """
        cnt_emof = CountOfBiologicalEntity(
            event_id, occurrence_id, str(values.abundance)
        )
        arch.emofs.add(cnt_emof)
        if values.concentration is not None:
            value = round(values.concentration, 6)
            emof = AbundancePerUnitVolumeOfTheWaterBody(
                event_id, occurrence_id, str(value)
            )
            arch.emofs.add(emof)
        if values.biovolume is not None:
            value = round(values.biovolume, 6)
            emof2 = BiovolumeOfBiologicalEntity(event_id, occurrence_id, str(value))
            arch.emofs.add(emof2)

    @staticmethod
    def event_date(min_date: datetime.datetime, max_date: datetime.datetime) -> str:
        """
        Return a date range if dates are different, otherwise the date. Separator is "/"
        """
        if min_date != max_date:
            return timestamp_to_str(min_date) + "/" + timestamp_to_str(max_date)
        else:
            return timestamp_to_str(min_date)

    @staticmethod
    def sanitize_title(title: str) -> str:
        """
        So far, nothing.
        """
        return title

    def keep_stats(self, taxon_info: WoRMS, count: int) -> None:
        """
        Keep statistics per various entries.
        """
        assert taxon_info.rank is not None
        stats = self.stats_per_rank.setdefault(
            taxon_info.rank, {"cnt": 0, "nms": set()}
        )
        stats["cnt"] += count
        stats["nms"].add(taxon_info.scientificname)

    def log_stats(self) -> None:
        not_produced = sum(self.ignored_count.values())
        self.warnings.append(
            "Stats: predicted:%d validated:%d produced to zip:%d not produced (M):%d not produced (P):%d"
            % (
                self.predicted_count,
                self.validated_count,
                self.produced_count,
                self.ignored_morpho,
                not_produced,
            )
        )
        if len(self.ignored_count) > 0:
            unmatched = []
            ids = list(self.ignored_count.keys())
            ids.sort(key=lambda i: self.ignored_count[i], reverse=True)
            for an_id in ids:
                unmatched.append(
                    str({self.ignored_count[an_id]: self.ignored_taxa[an_id]})
                )
            self.warnings.append(
                "Not produced due to non-match in WoRMS, format is {number:taxon}: %s"
                % ", ".join(unmatched)
            )
        if len(self.unknown_nets) > 0:
            for a_net, sample_ids in self.unknown_nets.items():
                self.warnings.append(
                    "Net type '%s' is not mapped to a BODC term. It is used in %s"
                    % (a_net, str(sample_ids))
                )
        if len(self.empty_samples) > 0:
            self.warnings.append(
                "Empty samples found, format is (project ID, sample ID): %s"
                % str(self.empty_samples)
            )
        if len(self.suspicious_vals) > 0:
            self.warnings.append(
                "Suspicious values found, format is (variable, values): %s"
                % str(self.suspicious_vals)
            )
        ranks_asc = sorted(self.stats_per_rank.keys())
        for a_rank in ranks_asc:
            logger.info(
                "rank '%s' stats %s", str(a_rank), self.stats_per_rank.get(a_rank)
            )

    def update_db_stats(self) -> None:
        """
        Refresh the database for aggregates.
        """
        project_ids = [a_project.projid for a_project in self.collection.projects]
        for a_project_id in project_ids:
            # Ensure the taxo stats are OK
            ProjectBO.update_taxo_stats(self.session, projid=a_project_id)
            # Ensure that the geography is OK propagated upwards from objects, for all projects inside the collection
            Sample.propagate_geo(self.session, prj_id=a_project_id)
        a_stat: ProjectTaxoStats
        for a_stat in ProjectBO.read_taxo_stats(self.session, project_ids, []):
            self.validated_count += a_stat.nb_validated
            self.predicted_count += a_stat.nb_predicted
