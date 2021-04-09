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
import re
from datetime import date, datetime
from typing import Dict, List, Optional, Tuple, cast, Set
from urllib.parse import quote_plus

from dataclasses import dataclass

from API_models.exports import EMODnetExportRsp
from BO.Acquisition import AcquisitionBO, AcquisitionIDT
from BO.Classification import ClassifIDT
from BO.Collection import CollectionIDT, CollectionBO
from BO.DataLicense import LicenseEnum, DataLicense
from BO.Mappings import ProjectMapping
from BO.Object import ObjectBO, ObjectBOSet
from BO.Process import ProcessBO
from BO.Project import ProjectBO, ProjectIDListT, ProjectTaxoStats, ProjectIDT
from BO.ProjectVars import DefaultVars
from BO.Rights import RightsBO
from BO.Sample import SampleBO
from BO.TaxonomySwitch import TaxonomyMapper
from DB import User, Taxonomy, WoRMS, Collection, Role
from DB.Project import ProjectTaxoStat
from DB.Sample import Sample
from DB.helpers.ORM import Query
from DB.helpers.Postgres import timestamp_to_str
from data.Countries import countries_by_name
from formats.EMODnet.Archive import DwC_Archive
from formats.EMODnet.DatasetMeta import DatasetMetadata
from formats.EMODnet.MoF import SamplingNetMeshSizeInMicrons, SampleDeviceApertureAreaInSquareMeters, \
    AbundancePerUnitVolumeOfTheWaterBody, \
    SampleVolumeInCubicMeters, BiovolumeOfBiologicalEntity, SamplingInstrumentName
from formats.EMODnet.models import DwC_Event, RecordTypeEnum, DwC_Occurrence, OccurrenceStatusEnum, \
    BasisOfRecordEnum, EMLGeoCoverage, EMLTemporalCoverage, EMLMeta, EMLTitle, EMLPerson, EMLKeywordSet, \
    EMLTaxonomicClassification, EMLAdditionalMeta, EMLIdentifier, EMLAssociatedPerson
from helpers.DynamicLogs import get_logger, LogsSwitcher
from helpers.Timer import CodeTimer
# TODO: Move somewhere else
from ..helpers.TaskService import TaskServiceBase

logger = get_logger(__name__)


class EMODnetExport(TaskServiceBase):
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

    def __init__(self, collection_id: CollectionIDT, dry_run: bool, with_zeroes: bool,
                 with_computations: bool, auto_morpho: bool):
        super().__init__(task_type="TaskExportTxt")
        # Input
        self.dry_run = dry_run
        self.with_zeroes = with_zeroes
        self.auto_morpho = auto_morpho
        self.with_computations = with_computations
        self.collection = self.ro_session.query(Collection).get(collection_id)
        assert self.collection is not None, "Invalid collection ID"
        # During processing
        # The Phylo taxa to their WoRMS conterpart
        self.mapping: Dict[ClassifIDT, WoRMS] = {}
        # The Morpho taxa to their nearest Phylo parent
        self.morpho2phylo: Dict[ClassifIDT, ClassifIDT] = {}
        self.taxa_per_sample: Dict[str, Set[ClassifIDT]] = {}
        # Output
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # Summary for logging issues
        self.validated_count = 0
        self.produced_count = 0
        self.ignored_count: Dict[ClassifIDT, int] = {}
        self.ignored_morpho: int = 0
        self.ignored_taxa: Dict[ClassifIDT, Tuple[str, ClassifIDT]] = {}
        self.unknown_nets: Dict[str, List[str]] = {}
        self.empty_samples: List[Tuple[ProjectIDT, str]] = []
        self.stats_per_rank: Dict[str, Dict] = {}
        self.suspicious_vals: Dict[str, List[str]] = {}

    DWC_ZIP_NAME = "dwca.zip"

    def run(self, current_user_id: int) -> EMODnetExportRsp:
        with LogsSwitcher(self):
            return self.do_run(current_user_id)

    def do_run(self, current_user_id: int) -> EMODnetExportRsp:
        # Security check
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.ro_session, current_user_id, Role.APP_ADMINISTRATOR)
        # Adjust the task
        self.set_task_params(current_user_id, self.DWC_ZIP_NAME)
        # Do the job
        logger.info("------------ starting --------------")
        # Update DB statistics
        self.update_db_stats()
        ret = EMODnetExportRsp()
        # Build metadata with what comes from the collection
        meta = self.build_meta()
        if meta is None:
            # If we can't have meta there has to be reasons
            assert len(self.errors) > 0
            ret.errors = self.errors
            ret.warnings = self.warnings
            return ret
        # Create a container
        arch = DwC_Archive(DatasetMetadata(meta), self.temp_for_task.base_dir_for(self.task_id) / self.DWC_ZIP_NAME)
        # Add data from DB
        # OK because https://edmo.seadatanet.org/v_edmo/browse_step.asp?step=003IMEV_0021
        # But TODO: hardcoded, implement https://github.com/oceanomics/ecotaxa_dev/issues/514
        self.institution_code = "IMEV"
        self.add_events(arch)
        # Loop over _absent_ data
        # For https://github.com/ecotaxa/ecotaxa_dev/issues/603
        # Loop over taxa which are in the collection but not in present sample
        if self.with_zeroes:
            self.add_absent_occurrences(arch)
        # OK we issue warning in case of individual issue, but if there is no content at all
        # then it's an error
        if arch.events.count() == 0 and arch.occurences.count() == 0 and arch.emofs.count() == 0:
            self.errors.append("No content produced."
                               " See previous warnings or check the presence of samples in the projects")
        else:
            # Produce the zip
            arch.build()
            self.log_stats()
        ret.errors = self.errors
        ret.warnings = self.warnings
        if len(ret.errors) == 0:
            ret.task_id = self.task_id
        return ret

    def add_absent_occurrences(self, arch):
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
                worms = self.mapping[a_missing_id]
                occ = DwC_Occurrence(eventID=an_event_id,
                                     occurrenceID=occurrence_id,
                                     individualCount=0,
                                     scientificName=worms.scientificname,
                                     scientificNameID=worms.lsid,
                                     kingdom=worms.kingdom,
                                     occurrenceStatus=OccurrenceStatusEnum.absent,
                                     basisOfRecord=BasisOfRecordEnum.machineObservation)
                arch.occurences.add(occ)

    def compute_all_seen_taxa(self):
        # Cumulate all categories
        all_taxa: Set[ClassifIDT] = set()
        for an_id_set in self.taxa_per_sample.values():
            all_taxa.update(an_id_set)
        return all_taxa

    @staticmethod
    def organisation_to_eml_person(an_org):
        return EMLPerson(organizationName=an_org)

    @staticmethod
    def capitalize_name(name: str):
        """
            e.g. JEAN -> Jean
            but as well JEAN-MARC -> Jean-Marc
            and even FOo--BAR -> Foo--Bar
        """
        return "".join([a_word.capitalize() for a_word in re.split(r'(\W+)', name)])

    @staticmethod
    def user_to_eml_person(user: Optional[User], for_messages: str) -> Tuple[Optional[EMLPerson], List[str]]:
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
                "%s user '%s' has no organization (it should contain a - )." % (for_messages, user.name))
        else:
            try:
                _dummy, organization = user.organisation.strip().split("-")
                organization = organization.strip()
            except ValueError:
                problems.append(
                    "Cannot determine short organization from %s org: '%s' (need a - )." % (
                        for_messages, user.organisation))

        # TODO: Organization should fit from https://edmo.seadatanet.org/search

        try:
            # Try to get name+sur_name from stored value
            name, sur_name = user.name.strip().split(" ", 1)
        except ZeroDivisionError:
            problems.append(
                "Cannot determine name+surname from %s name: %s." % (for_messages, user.name))
        else:
            name, sur_name = EMODnetExport.capitalize_name(name), EMODnetExport.capitalize_name(sur_name)

        try:
            country = countries_by_name[user.country]
        except KeyError:
            problems.append("Unknown country name for %s: %s." % (for_messages, user.country))
        else:
            country_name = country["alpha_2"]

        if len(problems) == 0:
            # noinspection PyUnboundLocalVariable
            ret = EMLPerson(organizationName=organization,
                            givenName=name,
                            surName=sur_name,
                            country=country_name)
            # Optional but useful field
            if "@" in user.email:
                ret.electronicMailAddress = user.email
        return ret, problems

    @staticmethod
    def eml_person_to_associated_person(in_model: EMLPerson, role: str) -> EMLAssociatedPerson:
        return EMLAssociatedPerson(organizationName=in_model.organizationName,
                                   givenName=in_model.givenName,
                                   surName=in_model.surName,
                                   country=in_model.country,
                                   role=role)

    MIN_ABSTRACT_CHARS = 256
    """ Minimum size of a 'quality' abstract """

    OK_LICENSES = [LicenseEnum.CC0, LicenseEnum.CC_BY, LicenseEnum.CC_BY_NC]

    def build_meta(self) -> Optional[EMLMeta]:
        """
            Various queries/copies on/from the projects for getting metadata.
        """
        ret = None
        the_collection: CollectionBO = CollectionBO(self.collection).enrich()

        identifier = EMLIdentifier(packageId=the_collection.external_id,
                                   system=the_collection.external_id_system)

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
            self.errors.append("No valid data creator (user or organisation) found for EML metadata.")

        contact, errs = self.user_to_eml_person(the_collection.contact_user, "contact")
        if contact is None:
            self.errors.append("No valid contact user found for EML metadata.")

        provider, errs = self.user_to_eml_person(the_collection.provider_user, "provider")
        if provider is None:
            self.errors.append("No valid metadata provider user found for EML metadata.")

        associates: List[EMLAssociatedPerson] = []
        for a_user in the_collection.associate_users:
            person, errs = self.user_to_eml_person(a_user, "associated person %d" % a_user.id)
            if errs:
                self.warnings.extend(errs)
            else:
                assert person is not None
                associates.append(self.eml_person_to_associated_person(person, "originator"))
        for an_org in the_collection.associate_organisations:
            # noinspection PyTypeChecker
            associates.append(self.organisation_to_eml_person(an_org))

        # TODO if needed
        # EMLAssociatedPerson = EMLPerson + specific role

        # TODO: a marine regions substitute
        (min_lat, max_lat, min_lon, max_lon) = ProjectBO.get_bounding_geo(self.session, the_collection.project_ids)
        geo_cov = EMLGeoCoverage(geographicDescription="See coordinates",
                                 westBoundingCoordinate=self.geo_to_txt(min_lon),
                                 eastBoundingCoordinate=self.geo_to_txt(max_lon),
                                 northBoundingCoordinate=self.geo_to_txt(min_lat),
                                 southBoundingCoordinate=self.geo_to_txt(max_lat))

        (min_date, max_date) = ProjectBO.get_date_range(self.session, the_collection.project_ids)
        time_cov = EMLTemporalCoverage(beginDate=timestamp_to_str(min_date),
                                       endDate=timestamp_to_str(max_date))

        publication_date = date.today().isoformat()

        abstract = the_collection.abstract
        if not abstract:
            self.errors.append("Collection 'abstract' field is empty")
        elif len(abstract) < self.MIN_ABSTRACT_CHARS:
            self.errors.append(
                "Collection 'abstract' field is too short (%d chars) to make a good EMLMeta abstract. Minimum is %d"
                % (len(abstract), self.MIN_ABSTRACT_CHARS))

        additional_info = None  # Just to see if it goes thru QC
        # additional_info = """  marine, harvested by iOBIS.
        # The OOV supported the financial effort of the survey.
        # We are grateful to the crew of the research boat at OOV that collected plankton during the temporal survey."""

        coll_license: LicenseEnum = cast(LicenseEnum, the_collection.license)
        if coll_license not in self.OK_LICENSES:
            self.errors.append(
                "Collection license should be one of %s to be accepted, not %s."
                % (self.OK_LICENSES, coll_license))
        else:
            lic_url = DataLicense.EXPORT_EXPLANATIONS[coll_license] + "legalcode"
            lic_txt = DataLicense.NAMES[coll_license]
            lic_txt = lic_txt.replace("International Public ", "")
            # ipt.gbif.org does not find the full license name, so adjust a bit
            version = "4.0"
            if version in lic_txt:
                lic_txt = lic_txt.replace(version, "(%s) " % DataLicense.SHORT_NAMES[coll_license] + version)
            licence = "This work is licensed under a <ulink url=\"%s\"><citetitle>%s</citetitle></ulink>." % (
                lic_url, lic_txt)

        # Preferably one of https://www.emodnet-biology.eu/contribute?page=list&subject=thestdas&SpColID=552&showall=1#P
        keywords = EMLKeywordSet(keywords=["Plankton",
                                           "Imaging", "EcoTaxa"  # Not in list above
                                           # "Ligurian sea" TODO: Geo area?
                                           # TODO: ZooProcess (from projects)
                                           ],
                                 keywordThesaurus="GBIF Dataset Type Vocabulary: "
                                                  "http://rs.gbif.org/vocabulary/gbif/dataset_type.xml")

        taxo_cov = self.get_taxo_coverage(the_collection.project_ids)

        now = datetime.now().replace(microsecond=0)
        meta_plus = EMLAdditionalMeta(dateStamp=now.isoformat())

        coll_title = the_collection.title
        info_url = "https://ecotaxa.obs-vlfr.fr/api/collections/by_title?q=%s" % quote_plus(coll_title)

        if len(self.errors) == 0:
            # The research project
            # noinspection PyUnboundLocalVariable
            # project = EMLProject(title=the_collection.title,
            #                      personnel=[])  # TODO: Unsure about duplicated information with metadata
            # noinspection PyUnboundLocalVariable
            ret = EMLMeta(identifier=identifier,
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
                          informationUrl=info_url)
        return ret

    def get_taxo_coverage(self, project_ids: ProjectIDListT) -> List[EMLTaxonomicClassification]:
        """
            Taxonomic coverage is the list of taxa which can be found in the projects.

        """
        ret: List[EMLTaxonomicClassification] = []
        # Fetch the used taxa in the projects
        taxo_qry: Query = self.session.query(ProjectTaxoStat.id, Taxonomy.name).distinct()
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.id == Taxonomy.id)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.nbr > 0)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.projid.in_(project_ids))
        used_taxa = {an_id: a_name for (an_id, a_name) in taxo_qry.all()}
        # Map them to WoRMS
        self.mapping, self.morpho2phylo = TaxonomyMapper(self.ro_session, list(used_taxa.keys())).do_match()
        assert set(self.mapping.keys()).isdisjoint(set(self.morpho2phylo.keys()))
        # Warnings for non-matches
        for an_id, a_name in used_taxa.items():
            if an_id not in self.mapping:
                if an_id in self.morpho2phylo:
                    pass
                else:
                    self.ignored_taxa[an_id] = (a_name, an_id)
                    self.ignored_count[an_id] = 0
        # TODO: Temporary until the whole system has a WoRMS taxo tree
        # Error out if nothing at all
        if len(self.mapping) == 0:
            self.errors.append("Could not match in WoRMS _any_ classification in this project")
            return ret
        # Produce the coverage
        for _an_id, a_worms_entry in self.mapping.items():
            assert a_worms_entry is not None, "None for %d" % _an_id
            rank = a_worms_entry.rank
            value = a_worms_entry.scientificname
            assert rank is not None, "No name for %d" % _an_id
            ret.append(EMLTaxonomicClassification(taxonRankName=rank,
                                                  taxonRankValue=value))
        return ret

    @staticmethod
    def geo_to_txt(lat_or_lon: float) -> str:
        # Round coordinates to ~ 110mm
        return "%.6f" % lat_or_lon

    def add_events(self, arch: DwC_Archive):
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
                latitude = self.geo_to_txt(a_sample.latitude)
                longitude = self.geo_to_txt(a_sample.longitude)
                evt = DwC_Event(eventID=event_id,
                                type=evt_type,
                                institutionCode=self.institution_code,
                                datasetName=ds_name,
                                eventDate=evt_date,
                                decimalLatitude=latitude,
                                decimalLongitude=longitude,
                                minimumDepthInMeters=str(summ[2]),
                                maximumDepthInMeters=str(summ[3])
                                )
                events.add(evt)
                nb_added = self.add_occurences(sample=a_sample, arch=arch, event_id=event_id)
                self.add_eMoFs_for_sample(sample=a_sample, arch=arch, event_id=event_id)
                if nb_added == 0:
                    self.warnings.append("No occurrence added for sample '%s' in %d" % (a_sample.orig_id, a_prj_id))

    nine_nine_re = re.compile("999+.0$")

    # noinspection PyPep8Naming
    def add_eMoFs_for_sample(self, sample: Sample, arch: DwC_Archive, event_id: str):
        """
            Add eMoF instances, for given sample, i.e. event, into the archive.
        """
        # emof = SamplingSpeed(event_id, "2")
        # arch.emofs.add(emof)
        try:
            sample_volume = SampleBO.get_computed_var(sample, DefaultVars.volume_sampled)
        except TypeError as _e:
            pass
        else:
            if self.nine_nine_re.match(str(sample_volume)):
                self.suspicious_vals.setdefault("sample_volume", []).append(
                    str(sample_volume) + " in " + sample.orig_id)
            # Add sampled water volume
            if sample_volume > 0:
                arch.emofs.add(SampleVolumeInCubicMeters(event_id, str(sample_volume)))

        # Get the net features from the sample
        try:
            net_type, net_mesh, net_surf = SampleBO.get_free_fields(sample, ["net_type", "net_mesh", "net_surf"],
                                                                    [str, float, float],
                                                                    ["", -1, -1])
        except TypeError as e:
            self.warnings.append("Could not extract sampling net name and features from sample %s (%s)."
                                 % (sample.orig_id, str(e)))
        else:
            if net_type == "bongo":
                # TODO: There could be more specific, a dozen of bongos are there:
                #  http://vocab.nerc.ac.uk/collection/L22/current/
                ins = SamplingInstrumentName(event_id, "Bongo net",
                                             "http://vocab.nerc.ac.uk/collection/L22/current/NETT0176/")
                arch.emofs.add(ins)
                arch.emofs.add(SamplingNetMeshSizeInMicrons(event_id, str(net_mesh)))
                arch.emofs.add(SampleDeviceApertureAreaInSquareMeters(event_id, str(net_surf)))
            elif net_type in ("wp2",  # There are several species of this one
                              "jb",  # Juday-bogorov
                              "regent"
                              ):
                ins = SamplingInstrumentName(event_id, "plankton nets",
                                             "http://vocab.nerc.ac.uk/collection/L05/current/22/")
                arch.emofs.add(ins)
                arch.emofs.add(SamplingNetMeshSizeInMicrons(event_id, str(net_mesh)))
                arch.emofs.add(SampleDeviceApertureAreaInSquareMeters(event_id, str(net_surf)))
            else:
                self.unknown_nets.setdefault(net_type, []).append(sample.orig_id)

    # Simplest structure with literal names. No bloody dict.
    @dataclass()
    class AggregForTaxon:
        abundance: int
        concentration: Optional[float]
        biovolume: Optional[float]

    def aggregate_for_sample(self, sample: Sample) -> Dict[ClassifIDT, AggregForTaxon]:
        """
            Do the aggregations for the sample for each taxon and return them, they will become emofs
                - 'Abundance' -> CountOfBiologicalEntity -> count of objects group by taxon
                - 'Concentration' -> AbundancePerUnitVolumeOfTheWaterBody
                    -> sum(individual_concentration) group by taxon
                        with individual_concentration = 1 / subsample_coef / total_water_volume
                - 'Biovolume' -> BiovolumeOfBiologicalEntity -> sum(individual_biovolume) group by taxon
                    with individual_biovolume = individual_volume / subsample_coef / total_water_volume
            The abundance can always be computed. The 2 other ones depend on availability of values
            for the project and the configuration variable.
        """
        # We return all per taxon.
        ret: Dict[ClassifIDT, EMODnetExport.AggregForTaxon] = {}

        count_per_taxon_per_acquis: Dict[AcquisitionIDT, Dict[ClassifIDT, int]] = {}

        # Start with abundances, simple count and giving its keys to the returned dict.
        acquis_for_sample = SampleBO.get_acquisitions(self.session, sample)
        for an_acquis in acquis_for_sample:
            # Get counts for acquisition (subsample)
            count_per_taxon_for_acquis = AcquisitionBO.get_sums_by_taxon(self.session, an_acquis.acquisid)
            if self.auto_morpho:
                self.add_morpho_counts(count_per_taxon_for_acquis)
            count_per_taxon_per_acquis[an_acquis.acquisid] = count_per_taxon_for_acquis
            for an_id, count_4_acquis in count_per_taxon_for_acquis.items():
                aggreg_for_taxon = ret.get(an_id)
                if aggreg_for_taxon is None:
                    ret[an_id] = self.AggregForTaxon(count_4_acquis, None, None)
                else:
                    aggreg_for_taxon.abundance += count_4_acquis

        if not self.with_computations:
            return ret

        # Enrich with concentrations
        subsampling_coeff_per_acquis: Dict[AcquisitionIDT, float] = {}
        try:
            # Fetch calculation data at sample level
            sample_volume = SampleBO.get_computed_var(sample, DefaultVars.volume_sampled)
        except TypeError as e:
            self.warnings.append("Could not compute volume sampled from sample %s (%s),"
                                 " no concentration or biovolume will be computed." % (sample.orig_id, str(e)))
            sample_volume = -1
        if sample_volume > 0:
            # Cumulate for subsamples AKA acquisitions
            for an_acquis in acquis_for_sample:
                try:
                    subsampling_coefficient = AcquisitionBO.get_computed_var(an_acquis, DefaultVars.subsample_coeff)
                    subsampling_coeff_per_acquis[an_acquis.acquisid] = subsampling_coefficient
                except TypeError as e:
                    self.warnings.append("Could not compute subsampling coefficient from acquisition %s (%s),"
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
                    acq_object_ids = AcquisitionBO.get_all_object_ids(session=self.session,
                                                                      acquis_id=an_acquis.acquisid,
                                                                      classif_ids=list(ret.keys()))
                with CodeTimer("Objects for '%s': " % an_acquis.orig_id, logger):
                    objects = ObjectBOSet(self.ro_session, acq_object_ids, mapping.object_mappings)
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

    def add_morpho_counts(self, count_per_taxon_for_acquis):
        # If there are Morpho taxa with counts, cumulate and wipe them out
        for an_id, count_4_acquis in dict(count_per_taxon_for_acquis).items():
            phylo_id = self.morpho2phylo.get(an_id)
            if phylo_id is not None:
                del count_per_taxon_for_acquis[an_id]
                if phylo_id in count_per_taxon_for_acquis:
                    # Accumulate in parent count
                    count_per_taxon_for_acquis[phylo_id] += count_4_acquis
                else:
                    # Create the parent
                    count_per_taxon_for_acquis[phylo_id] = count_4_acquis

    def add_occurences(self, sample: Sample, arch: DwC_Archive, event_id: str) -> int:
        """
            Add DwC occurences, for given sample, into the archive.
        """
        aggregs = self.aggregate_for_sample(sample)

        # To see
        # print()
        # print("Concentrations in sample '%s':%s" % (sample.orig_id, str(concentration_per_taxon)))
        nb_added_occurences = 0
        ids = list(aggregs.keys())
        # Sort per abundance desc
        ids.sort(key=lambda i: aggregs[i].abundance, reverse=True)
        # Record production for this sample
        self.taxa_per_sample[event_id] = set()
        # Loop over _present_ taxa
        for an_id in ids:
            aggreg_for_taxon = aggregs[an_id]
            # print("%s conc %f" % (worms.scientificname, conc_for_taxon))
            #     self.keep_stats(worms, count_4_sample)
            individual_count = aggreg_for_taxon.abundance
            try:
                worms = self.mapping[an_id]
            except KeyError:
                # Mapping failed, count how many of them
                if an_id in self.ignored_count:
                    self.ignored_count[an_id] += individual_count
                else:
                    self.ignored_morpho += individual_count
                continue
            self.produced_count += individual_count
            # Take the original taxo ID to build an occurence
            occurrence_id = event_id + "_" + str(an_id)
            occ = DwC_Occurrence(eventID=event_id,
                                 occurrenceID=occurrence_id,
                                 individualCount=individual_count,
                                 scientificName=worms.scientificname,
                                 scientificNameID=worms.lsid,
                                 kingdom=worms.kingdom,
                                 occurrenceStatus=OccurrenceStatusEnum.present,
                                 basisOfRecord=BasisOfRecordEnum.machineObservation)
            arch.occurences.add(occ)
            nb_added_occurences += 1
            # Add eMoFs if possible and required, but the decision is made inside the def
            self.add_eMoFs_for_occurence(arch=arch,
                                         event_id=event_id,
                                         occurrence_id=occurrence_id,
                                         values=aggreg_for_taxon)
            if self.with_zeroes:
                # Record the production of an occurence 'present' for this taxon
                self.taxa_per_sample[event_id].add(an_id)
        return nb_added_occurences

    @staticmethod
    def add_eMoFs_for_occurence(arch: DwC_Archive, event_id: str, occurrence_id: str, values: AggregForTaxon):
        """
            Add eMoF instances, for given occurence, into the archive.
            Conditions are: - the value exists
                            - the value was required by the call
        """
        if values.concentration is not None:
            value = round(values.concentration, 6)
            emof = AbundancePerUnitVolumeOfTheWaterBody(event_id, occurrence_id, str(value))
            arch.emofs.add(emof)
        if values.biovolume is not None:
            value = round(values.biovolume, 6)
            emof2 = BiovolumeOfBiologicalEntity(event_id, occurrence_id, str(value))
            arch.emofs.add(emof2)

    @staticmethod
    def event_date(min_date, max_date) -> str:
        """
            Return a date range if dates are different, otherwise the date. Separator is "/"
        """
        if min_date != max_date:
            return timestamp_to_str(min_date) + "/" + timestamp_to_str(max_date)
        else:
            return timestamp_to_str(min_date)

    @staticmethod
    def sanitize_title(title) -> str:
        """
            So far, nothing.
        """
        return title

    def keep_stats(self, taxon_info: WoRMS, count: int):
        """
            Keep statistics per various entries.
        """
        assert taxon_info.rank is not None
        stats = self.stats_per_rank.setdefault(taxon_info.rank, {"cnt": 0, "nms": set()})
        stats["cnt"] += count
        stats["nms"].add(taxon_info.scientificname)

    def log_stats(self):
        not_produced = sum(self.ignored_count.values())
        self.warnings.append("Stats: validated:%d produced to zip:%d not produced (M):%d not produced (P):%d"
                             % (self.validated_count, self.produced_count, self.ignored_morpho, not_produced))
        if len(self.ignored_count) > 0:
            unmatched = []
            ids = list(self.ignored_count.keys())
            ids.sort(key=lambda i: self.ignored_count[i], reverse=True)
            for an_id in ids:
                unmatched.append(str({self.ignored_count[an_id]: self.ignored_taxa[an_id]}))
            self.warnings.append(
                "Not produced due to non-match in WoRMS, format is {number:taxon}: %s" % ", ".join(unmatched))
        if len(self.unknown_nets) > 0:
            for a_net, sample_ids in self.unknown_nets.items():
                self.warnings.append(
                    "Net type '%s' is not mapped to a BODC term. It is used in %s" % (a_net, str(sample_ids)))
        if len(self.empty_samples) > 0:
            self.warnings.append("Empty samples found, format is (project ID, sample ID): %s" % str(self.empty_samples))
        if len(self.suspicious_vals) > 0:
            self.warnings.append(
                "Suspicious values found, format is (variable, values): %s" % str(self.suspicious_vals))
        ranks_asc = sorted(self.stats_per_rank.keys())
        for a_rank in ranks_asc:
            logger.info("rank '%s' stats %s", str(a_rank), self.stats_per_rank.get(a_rank))

    def update_db_stats(self):
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
        for a_stat in ProjectBO.read_taxo_stats(self.session, project_ids):
            self.validated_count += a_stat.nb_validated
