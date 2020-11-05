# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import date
from typing import Dict, List, Optional, Tuple, cast

from API_models.exports import EMODnetExportRsp
from BO.Collection import CollectionIDT, CollectionBO
from BO.DataLicense import LicenseEnum, DataLicense
from BO.Project import ProjectBO, ProjectIDListT
from BO.Rights import RightsBO
from BO.Sample import SampleIDT, SampleBO
from BO.Taxonomy import WoRMSSetFromTaxaSet
from DB import User, Taxonomy, WoRMS, Collection, Role
from DB.Project import ProjectTaxoStat
from DB.Sample import Sample
from DB.helpers.ORM import Query
from DB.helpers.Postgres import timestamp_to_str
from formats.EMODnet.Archive import DwC_Archive
from formats.EMODnet.DatasetMeta import DatasetMetadata
from formats.EMODnet.MoF import SamplingSpeed, AbundancePerUnitAreaOfTheBed, SamplingInstrumentName, \
    SamplingNetMeshSize, SampleDeviceDiameter
from formats.EMODnet.models import DwC_Event, RecordTypeEnum, DwC_Occurrence, OccurrenceStatusEnum, \
    BasisOfRecordEnum, EMLGeoCoverage, EMLTemporalCoverage, EMLMeta, EMLTitle, EMLPerson, EMLProject, EMLKeywordSet, \
    EMLTaxonomicClassification, EMLAdditionalMeta
from helpers.DynamicLogs import get_logger
from .Countries import countries_by_name
# TODO: Move somewhere else
from .TaxaUtils import RANKS_BY_ID
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

    def __init__(self, collection_id: CollectionIDT, dry_run: bool):
        super().__init__(task_type="TaskExportTxt")
        # Input
        self.dry_run = dry_run
        self.collection = self.session.query(Collection).get(collection_id)
        assert self.collection is not None, "Invalid collection ID"
        # During processing
        self.mapping: Dict[int, WoRMS] = {}
        # Output
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # Summary for logging issues
        self.stats_per_rank: Dict[str, Dict] = {}

    DWC_ZIP_NAME = "dwca.zip"

    def run(self, current_user_id: int) -> EMODnetExportRsp:
        # Security check
        # TODO, for now only admins
        _user = RightsBO.user_has_role(self.session, current_user_id, Role.APP_ADMINISTRATOR)
        # Adjust the task
        self.set_task_params(current_user_id, self.DWC_ZIP_NAME)
        # Do the job
        logger.info("------------ starting --------------")
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
        self.add_events(arch)
        # Produced the zip
        arch.build()
        self.log_stats()
        ret.errors = self.errors
        ret.warnings = self.warnings
        if len(ret.errors) == 0:
            ret.task_id = self.task_id
        return ret

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
            except ValueError:
                problems.append(
                    "Cannot determine short organization from %s org: '%s' (need a - )." % (
                        for_messages, user.organisation))

        # TODO: Organization should fit from https://edmo.seadatanet.org/search

        try:
            name, sur_name = user.name.strip().split(" ")
        except ZeroDivisionError:
            problems.append(
                "Cannot determine name+surname from %s name: %s." % (for_messages, user.name))
        else:
            name, sur_name = name.capitalize(), sur_name.capitalize()

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

    MIN_ABSTRACT_CHARS = 256
    """ Minimum size of a 'quality' abstract """

    OK_LICENSES = [LicenseEnum.CC0, LicenseEnum.CC_BY, LicenseEnum.CC_BY_NC]

    def build_meta(self) -> Optional[EMLMeta]:
        """
            Various queries/copies on/from the projects for getting metadata.
        """
        ret = None
        the_collection: CollectionBO = CollectionBO(self.collection).enrich()

        title = EMLTitle(title=the_collection.title)

        creators: List[EMLPerson] = []
        for a_user in the_collection.creator_users:
            person, errs = self.user_to_eml_person(a_user, "creator %d" % a_user.id)
            if errs:
                self.errors.extend(errs)
            else:
                assert person is not None
                creators.append(person)
        for an_org in the_collection.creator_organisations:
            creators.append(EMLPerson(organizationName=an_org))

        contact, errs = self.user_to_eml_person(the_collection.contact_user, "contact")

        provider, errs = self.user_to_eml_person(the_collection.provider_user, "provider")

        associates: List[EMLPerson] = []
        for a_user in the_collection.associate_users:
            person, errs = self.user_to_eml_person(a_user, "associated person %d" % a_user.id)
            if errs:
                self.errors.extend(errs)
            else:
                assert person is not None
                associates.append(person)
        for an_org in the_collection.associate_organisations:
            associates.append(EMLPerson(organizationName=an_org))

        # TODO if needed
        # EMLAssociatedPerson = EMLPerson + specific role

        # Ensure that the geography is OK propagated upwards from objects, for all projects inside the collection
        for a_prj_id in the_collection.project_ids:
            Sample.propagate_geo(self.session, a_prj_id)

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

        publication_date = date.today().strftime("%Y-%m-%d")

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
            lic_url = DataLicense.EXPLANATIONS[coll_license] + "legalcode"
            lix_txt = DataLicense.NAMES[coll_license]
            licence = "This work is licensed under a <ulink url=\"%s\"><citetitle>%s</citetitle></ulink>." % (
                lic_url, lix_txt)

        # Preferably one of https://www.emodnet-biology.eu/contribute?page=list&subject=thestdas&SpColID=552&showall=1#P
        keywords = EMLKeywordSet(keywords=["Plankton",
                                           "Imaging", "EcoTaxa"  # Not in list above
                                           # "Ligurian sea" TODO: Geo area?
                                           ],
                                 keywordThesaurus="GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml")

        taxo_cov = self.get_taxo_coverage(the_collection.project_ids)

        meta_plus = EMLAdditionalMeta(dateStamp=date.today().strftime("%Y-%m-%d"))

        if len(self.errors) == 0:
            # The research project
            # noinspection PyUnboundLocalVariable
            project = EMLProject(title=the_collection.title,
                                 personnel=[])  # TODO: Unsure about duplicated information with metadata
            # noinspection PyUnboundLocalVariable
            ret = EMLMeta(titles=[title],
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
                          project=project,
                          maintenance="periodic review of origin data",
                          maintenanceUpdateFrequency="1M",
                          additionalMetadata=meta_plus)
        return ret

    def get_taxo_coverage(self, project_ids: ProjectIDListT) -> List[EMLTaxonomicClassification]:
        """
            Taxonomic coverage is the list of taxa which can be found in the project.

        """
        ret = []
        # Ensure the stats are OK
        for a_project_id in project_ids:
            ProjectBO.update_taxo_stats(self.session, projid=a_project_id)
        # Fetch the used taxa in the project
        taxo_qry: Query = self.session.query(ProjectTaxoStat.id, Taxonomy.name).distinct()
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.id == Taxonomy.id)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.nbr > 0)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.projid.in_(project_ids))
        used_taxa = {an_id: a_name for (an_id, a_name) in taxo_qry.all()}
        # Map them to WoRMS
        mapping = WoRMSSetFromTaxaSet(self.session, list(used_taxa.keys()))
        self.mapping = mapping.res
        # Warnings for non-matches
        for an_id, a_name in used_taxa.items():
            if an_id not in self.mapping:
                self.warnings.append("Classification %s (with id %d) could not be matched in WoRMS" %
                                     (a_name, an_id))
        # TODO: Temporary until the whole system has a WoRMS taxo tree
        # Error out if nothing at all
        if len(self.mapping) == 0:
            self.errors.append("Could not match in WoRMS _any_ classification in this project")
        # Produce the coverage
        for _an_id, a_worms_entry in self.mapping.items():
            rank = a_worms_entry.rank
            value = a_worms_entry.scientificname
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

        institution_code = "IMEV"
        ds_name = self.sanitize_title(self.collection.title)
        for a_prj_id in the_collection.project_ids:
            samples = Sample.get_orig_id_and_model(self.session, prj_id=a_prj_id)
            a_sample: Sample
            events = arch.events
            for orig_id, a_sample in samples.items():
                event_id = orig_id
                evt_type = RecordTypeEnum.sample
                summ = Sample.get_sample_summary(self.session, a_sample.sampleid)
                assert a_sample.latitude is not None and a_sample.longitude is not None
                evt_date = self.event_date(summ[0], summ[1])
                latitude = self.geo_to_txt(a_sample.latitude)
                longitude = self.geo_to_txt(a_sample.longitude)
                evt = DwC_Event(eventID=event_id,
                                type=evt_type,
                                institutionCode=institution_code,
                                datasetName=ds_name,
                                eventDate=evt_date,
                                decimalLatitude=latitude,
                                decimalLongitude=longitude,
                                minimumDepthInMeters=str(summ[2]),
                                maximumDepthInMeters=str(summ[3])
                                )
                events.add(evt)
                self.add_occurences(arch=arch, event_id=event_id, sample_id=a_sample.sampleid)
                self.add_eMoFs_for_sample(arch=arch, event_id=event_id)

    # noinspection PyPep8Naming
    @staticmethod
    def add_eMoFs_for_sample(arch: DwC_Archive, event_id: str):
        """
            Add eMoF instances, for given sample, i.e. event, into the archive.
        """
        emof = SamplingSpeed(event_id, "2")
        arch.emofs.add(emof)
        # TODO: Not the right one
        ins = SamplingInstrumentName(event_id, "Modified Juday net - Aksnes and Magnesen (1983)",
                                     "http://vocab.nerc.ac.uk/collection/L22/current/NETT0079/")
        arch.emofs.add(ins)
        arch.emofs.add(SamplingNetMeshSize(event_id, "0.38"))
        arch.emofs.add(SampleDeviceDiameter(event_id, "0.5"))

    def add_occurences(self, arch: DwC_Archive, event_id: str, sample_id: SampleIDT):
        """
            Add DwC occurences, for given sample, into the archive.
        """
        occurences = arch.occurences
        # Fetch data from DB
        count_per_taxon = SampleBO.get_sums_by_taxon(self.session, sample_id)
        # Output
        for an_id, count_4_sample in count_per_taxon.items():
            try:
                worms = self.mapping[an_id]
            except KeyError:
                # Mapping failed, it was signalled in warnings
                continue
            self.keep_stats(worms, count_4_sample)
            occurrence_id = event_id + "_" + str(an_id)
            individual_count = str(count_4_sample)
            # tot_vol
            # sub_part pour 497 (dans acquisition) -> homogène au niveau acq
            """
Pour chaque objet, unit_concentration = 1 * subsampling_rate / volume
Puis, pour un subsample ou un sample, concentration = sum(unit_concentration)
Donc il faut identifier les infos de subsampling (parfois inexistant) et de volume.

Le volume c'est http://vocab.nerc.ac.uk/collection/P01/current/VOLWBSMP/

-> EmOF
            """
            occ = DwC_Occurrence(eventID=event_id,
                                 occurrenceID=occurrence_id,
                                 individualCount=individual_count,
                                 scientificName=worms.scientificname,
                                 scientificNameID=worms.url,
                                 occurrenceStatus=OccurrenceStatusEnum.present,
                                 basisOfRecord=BasisOfRecordEnum.machineObservation)
            occurences.add(occ)
            self.add_eMoFs_for_occurence(arch=arch, event_id=event_id, occurrence_id=occurrence_id)

    @staticmethod
    def add_eMoFs_for_occurence(arch: DwC_Archive, event_id: str, occurrence_id: str):
        """
            Add eMoF instances, for given occurence, into the archive.
        """
        emof = AbundancePerUnitAreaOfTheBed(event_id, occurrence_id, "452")
        arch.emofs.add(emof)

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
        ranks_asc = sorted(self.stats_per_rank.keys())
        for a_rank in ranks_asc:
            logger.info("rank '%s' stats %s", RANKS_BY_ID.get(a_rank), self.stats_per_rank.get(a_rank))
