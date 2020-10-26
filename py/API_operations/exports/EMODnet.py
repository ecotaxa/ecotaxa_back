# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from datetime import date
from typing import Dict, List, Optional, Tuple

from API_models.exports import EMODnetExportReq, EMODnetExportRsp
from BO.DataLicense import LicenseEnum, DataLicense
from BO.Project import ProjectBO
from BO.ProjectPrivilege import ProjectPrivilegeBO
from BO.Rights import RightsBO, Action
from BO.Taxonomy import TaxonomyBO
from DB import User
from DB.Project import Project
from DB.Sample import Sample
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
from .ExportBase import ExportServiceBase
# TODO: Move somewhere else
from .TaxaUtils import TaxaCache, TaxonInfoForSample, TaxonInfo, RANKS_BY_ID

logger = get_logger(__name__)


class EMODnetExport(ExportServiceBase):
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

    def __init__(self, req: EMODnetExportReq, dry_run: bool):
        super().__init__(req.project_ids)
        # self.req = req
        # Input
        self.dry_run = dry_run
        # Output
        self.errors: List[str] = []
        # Summary for logging issues
        self.filtered_taxa: Dict[int, str]
        self.stats_per_rank: Dict[int, Dict] = {}

    DWC_ZIP_NAME = "dwca.zip"

    def run(self, current_user_id: int) -> EMODnetExportRsp:
        # Security check
        assert len(self.project_ids) == 1
        prj_id = self.project_ids[0]
        RightsBO.user_wants(self.session, current_user_id, Action.ADMINISTRATE, prj_id)
        # Load origin project
        src_project = self.session.query(Project).get(prj_id)
        assert src_project is not None, "Project %d not found" % prj_id
        # OK
        logger.info("------------ starting --------------")
        ret = EMODnetExportRsp()
        # Build metadata with what comes from the project
        meta = self.build_meta(src_project)
        if meta is None:
            # If we can't have meta there has to be reasons
            assert len(self.errors) > 0
            ret.errors = self.errors
            return ret
        # Create a container
        arch = DwC_Archive(DatasetMetadata(meta), self.temp_dir / self.DWC_ZIP_NAME)
        # Add data from DB
        self.add_events(src_project, arch)
        # Produced the zip
        arch.build()
        self.log_stats()
        return ret

    @staticmethod
    def user_to_eml_person(user: User, for_messages: str) -> Tuple[Optional[EMLPerson], List[str]]:
        """
            Build & return an EMLPerson entity from a DB User one.
        """
        problems = []
        ret = None

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

    OK_LICENSES = {LicenseEnum.CC0, LicenseEnum.CC_BY, LicenseEnum.CC_BY_NC}

    def build_meta(self, prj: Project) -> Optional[EMLMeta]:
        """
            Various queries/copies on/from the project for getting metadata.
        """
        ret = None
        title = EMLTitle(title=prj.title)

        # TODO: Pick project owner instead
        first_manager: Optional[User] = None
        for a_priv in list(prj.privs_for_members):
            if a_priv.privilege == ProjectPrivilegeBO.MANAGE:
                first_manager = a_priv.user
        if first_manager is None:
            self.errors.append("No manager in the project.")
        else:
            person1, errs = self.user_to_eml_person(first_manager, "first manager")
            if errs:
                self.errors.extend(errs)

        # TODO if needed
        # EMLAssociatedPerson = EMLPerson + specific role

        # Ensure that the geography is OK propagated upwards from objects
        Sample.propagate_geo(self.session, prj.projid)
        (min_lat, max_lat, min_lon, max_lon) = ProjectBO.get_bounding_geo(self.session, prj.projid)
        geo_cov = EMLGeoCoverage(geographicDescription="See coordinates",
                                 westBoundingCoordinate=self.geo_to_txt(min_lon),
                                 eastBoundingCoordinate=self.geo_to_txt(max_lon),
                                 northBoundingCoordinate=self.geo_to_txt(min_lat),
                                 southBoundingCoordinate=self.geo_to_txt(max_lat))

        (min_date, max_date) = ProjectBO.get_date_range(self.session, prj.projid)
        time_cov = EMLTemporalCoverage(beginDate=timestamp_to_str(min_date),
                                       endDate=timestamp_to_str(max_date))

        publication_date = date.today().strftime("%Y-%m-%d")

        if not prj.comments:
            self.errors.append(
                "Project 'Comments' field must contain an abstract. Minimum length is %d"
                % self.MIN_ABSTRACT_CHARS)
        elif len(prj.comments) < self.MIN_ABSTRACT_CHARS:
            self.errors.append(
                "Project 'Comments' field is too short (%d chars) to make a good EMLMeta abstract. Minimum is %d"
                % (len(prj.comments), self.MIN_ABSTRACT_CHARS))
        else:
            abstract = prj.comments

        additional_info = None  # Just to see if it goes thru QC
        # additional_info = """  marine, harvested by iOBIS.
        # The OOV supported the financial effort of the survey.
        # We are grateful to the crew of the research boat at OOV that collected plankton during the temporal survey."""

        # TODO: Remove the ignore below
        prj_license: LicenseEnum = prj.license  # type:ignore
        if prj_license not in self.OK_LICENSES:
            self.errors.append(
                "Project license should be one of %s to be accepted, not %s."
                % (self.OK_LICENSES, prj_license))
        else:
            lic_url = DataLicense.EXPLANATIONS[prj_license] + "legalcode"
            lix_txt = DataLicense.NAMES[prj_license]
            licence = "This work is licensed under a <ulink url=\"%s\"><citetitle>%s</citetitle></ulink>." % (
                lic_url, lix_txt)

        # Preferably one of https://www.emodnet-biology.eu/contribute?page=list&subject=thestdas&SpColID=552&showall=1#P
        keywords = EMLKeywordSet(keywords=["Plankton",
                                           "Imaging", "EcoTaxa"  # Not in list above
                                           # "Ligurian sea" TODO: Geo area?
                                           ],
                                 keywordThesaurus="GBIF Dataset Type Vocabulary: http://rs.gbif.org/vocabulary/gbif/dataset_type.xml")

        taxo_cov = [EMLTaxonomicClassification(taxonRankName="phylum",
                                               taxonRankValue="Arthropoda"),
                    EMLTaxonomicClassification(taxonRankName="phylum",
                                               taxonRankValue="Chaetognatha"),
                    ]

        meta_plus = EMLAdditionalMeta(dateStamp="2021-06-24")

        if len(self.errors) == 0:
            # The research project
            # noinspection PyUnboundLocalVariable
            project = EMLProject(title=prj.title,
                                 personnel=[person1])
            # noinspection PyUnboundLocalVariable
            ret = EMLMeta(titles=[title],
                          creators=[person1],
                          contacts=[person1],
                          metadataProviders=[person1],
                          associatedParties=[person1],
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

    @staticmethod
    def geo_to_txt(lat_or_lon: float) -> str:
        # Round coordinates to ~ 110mm
        return "%.6f" % lat_or_lon

    def add_events(self, prj: Project, arch: DwC_Archive):
        """
            Add DwC events into the archive.
                We produce sample-type events.
        """
        institution_code = "IMEV"
        ds_name = self.sanitize_title(prj.title)
        samples = Sample.get_orig_id_and_model(self.session, prj_id=prj.projid)
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

    def add_occurences(self, arch: DwC_Archive, event_id: str, sample_id: int):
        """
            Add DwC occurences, for given sample, into the archive.
        """
        occurences = arch.occurences
        # Fetch data from DB
        db_per_taxon = Sample.get_sums_by_taxon(self.session, sample_id)
        # Build a dict taxon_id -> info
        per_taxon: Dict[int, TaxonInfoForSample] = {a_sum[0]: TaxonInfoForSample(a_sum[1])
                                                    for a_sum in db_per_taxon}
        self.enrich_taxa(per_taxon)
        # Output
        for an_id, taxon_4_sample in per_taxon.items():
            taxon_info = taxon_4_sample.taxon_info
            assert taxon_info is not None
            aphia_id = taxon_info.aphia_id
            if not taxon_info.is_valid():
                # TODO: Log problems during resolve
                continue
            self.keep_stats(taxon_info, taxon_4_sample.count)
            occurrence_id = event_id + "_" + str(an_id)
            individual_count = str(taxon_4_sample.count)
            scientific_name = taxon_info.name
            scientific_name_id = "urn:lsid:marinespecies.org:taxname:" + str(aphia_id)
            occ = DwC_Occurrence(eventID=event_id,
                                 occurrenceID=occurrence_id,
                                 individualCount=individual_count,
                                 scientificName=scientific_name,
                                 scientificNameID=scientific_name_id,
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

    def enrich_taxa(self, taxa_dict: Dict[int, TaxonInfoForSample]):
        """
            For each taxon_id in taxa_dict keys, gather name & aphiaID
        """
        taxa_id_list = list(taxa_dict.keys())
        names = TaxonomyBO.names_for(self.session, taxa_id_list)
        assert len(names) == len(taxa_id_list)
        taxo_infos = TaxaCache.collect_worms_for(self.session, names)
        # Link TaxonInfo after lookups
        for an_id, taxon_4_sample in taxa_dict.items():
            taxon_4_sample.taxon_info = taxo_infos.get(an_id)

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

    def keep_stats(self, taxon_info: TaxonInfo, count: int):
        """
            Keep statistics per various entries.
        """
        stats = self.stats_per_rank.setdefault(taxon_info.rank, {"cnt": 0, "nms": set()})
        stats["cnt"] += count
        stats["nms"].add(taxon_info.name)

    def log_stats(self):
        ranks_asc = sorted(self.stats_per_rank.keys())
        for a_rank in ranks_asc:
            logger.info("rank '%s' stats %s", RANKS_BY_ID.get(a_rank), self.stats_per_rank.get(a_rank))
