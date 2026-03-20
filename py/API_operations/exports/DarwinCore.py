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
import json
from collections import OrderedDict
from functools import lru_cache
from typing import Dict, List, Optional, Tuple, cast, Set, Any, Iterable
from urllib.parse import quote_plus
from fastapi import HTTPException
from starlette.status import HTTP_422_UNPROCESSABLE_ENTITY

import BO.ProjectVarsDefault as DefaultVars
from API_models.exports import ExportRsp, SciExportTypeEnum
from BO.Acquisition import AcquisitionIDT
from BO.Classification import ClassifIDT, ClassifIDListT, ClassifIDSetT
from BO.Collection import (
    CollectionIDT,
    CollectionBO,
    creators_key,
    associates_key,
    user_order_type,
)
from BO.CommonObjectSets import CommonObjectSets
from BO.DataLicense import LicenseEnum, DataLicense
from BO.ObjectSet import DescribedObjectSet
from BO.ObjectSetQueryPlus import (
    ResultGrouping,
    TaxoRemappingT,
    ObjectSetQueryPlus,
)
from BO.Project import ProjectBO, ProjectTaxoStats, ProjectIDListT
from BO.ProjectSet import PermissionConsistentProjectSet
from BO.Sample import SampleBO, SampleAggregForTaxon
from BO.Vocabulary import Vocabulary, Units
from BO.WoRMSification import WoRMSifier, WoRMSBO, create_worms_bo
from BO.Taxonomy import TaxonBOSet
from BO.User import UserIDT
from DB.Collection import Collection
from DB.Project import ProjectTaxoStat, Project
from DB.Sample import Sample
from DB.TaxoRecast import TaxoRecast, RecastOperation
from DB.Taxonomy import Taxonomy
from DB.User import User, Organization
from DB.helpers import Session
from DB.helpers.Direct import text
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
    AnalyticalInstrumentName,
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
from providers.NERC import NERCFetcher
from ..helpers.JobService import JobServiceBase, ArgsDict

logger = get_logger(__name__)

AbundancePerAcquisitionT = Dict[AcquisitionIDT, Dict[ClassifIDT, int]]
LsidT = str  # Life Science Identifier @see https://en.wikipedia.org/wiki/LSID
OccIDT = str  # An occurenceId, sampleid+taxon ID
WoRMSAggregT = Dict[LsidT, Tuple[OccIDT, SampleAggregForTaxon, WoRMSBO]]
ROLE_FOR_ASSOCIATE = "originator"


def get_scientific_name_id(worms) -> str:
    return "urn:lsid:marinespecies.org:taxname:" + str(worms.aphia_id)


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
    OCCURENCE_REPORT_EVERY = 10
    PUBLISHER_ECOTAXA = "EcoTaxa"

    def init_args(self, args: ArgsDict) -> ArgsDict:
        # A bit unusual to find a method before init(), but here we can visually ensure
        # that arg lists are identical.
        args.update(
            {
                "collection_id": self.collection.id,
                "dry_run": self.dry_run,
                "include_predicted": self.include_predicted,
                "with_absent": self.with_absent,
                "with_computations": self.with_computations,
                "formulae": self.formulae,
                "extra_xml": self.extra_xml,
                "current_user_id": self.current_user_id,
            }
        )
        return args

    def __init__(
        self,
        collection_id: CollectionIDT,
        dry_run: bool,
        include_predicted: bool,
        with_absent: bool,
        with_computations: List[SciExportTypeEnum],
        formulae: Dict[str, str],
        extra_xml: List[str],
        current_user_id: UserIDT,
    ):
        super().__init__()
        # Input params
        collection = self.ro_session.query(Collection).get(collection_id)
        assert collection is not None, "Invalid collection ID"
        self.collection: Collection = collection
        self.the_collection: CollectionBO = CollectionBO(self.collection).enrich()
        self.dry_run: bool = dry_run
        self.include_predicted: bool = include_predicted
        # Output params
        self.with_absent: bool = with_absent
        self.with_computations: List[SciExportTypeEnum] = with_computations
        if len(formulae) == 0 and len(with_computations) > 0:
            assert False, "Need formulae for " + str(with_computations)
        # TODO: We have all this at project level now, but how to mix with API?
        self.formulae: Dict[str, str] = formulae
        # TODO: Some sanity check on XML
        self.extra_xml: List[str] = extra_xml
        self.current_user_id = current_user_id
        #
        # During processing
        self.computations_occurrence: TaxoRemappingT = {}
        self.computations_emof: TaxoRemappingT = {}
        self.coverage_taxa: Dict[ClassifIDT, WoRMSBO] = {}
        #
        # Output
        self.errors: List[str] = []
        self.warnings: List[str] = []
        # Summary, for human sanity checks and logging issues
        self.validated_count = 0  # Validated objects in projects
        self.predicted_count = 0  # Predicted objects in projects
        self.produced_count = 0
        self.ignored_count: Dict[ClassifIDT, int] = {}
        self.ignored_morpho: int = 0
        self.ignored_taxa: Dict[ClassifIDT, Tuple[ClassifIDT, str]] = {}
        self.unknown_nets: Dict[str, List[str]] = {}
        self.empty_samples: List[str] = []
        self.stats_per_rank: Dict[str, Dict[str, Any]] = {}
        self.suspicious_vals: Dict[str, List[str]] = {}

    DWC_ZIP_NAME = "dwca.zip"
    PRODUCED_FILE_NAME = DWC_ZIP_NAME

    def run(self) -> ExportRsp:
        """
        Initial run, basically just create the job, after permission check.
        """
        project_ids = [a_project.projid for a_project in self.collection.projects]
        PermissionConsistentProjectSet(
            self.session, project_ids
        ).can_be_administered_by(self.current_user_id)
        # Security OK, create pending job
        self.create_job(self.JOB_TYPE, self.current_user_id)
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
        # Update DB statistics to ensure correctness of geo in produced output
        self.update_db_stats()
        # 2 taxonomic mappings/spaces need to be used
        self.compute_taxo_spaces()
        # Build metadata with what comes from the collection
        meta, institution_code = self.build_meta()
        if meta is None:
            # If we can't have meta there has to be reasons
            assert len(self.errors) > 0
            self.set_job_result(self.errors, {"wrns": self.warnings})
            return
        # Create a container
        arch = DwC_Archive(
            DatasetMetadata(meta, self.extra_xml),
            self.temp_for_jobs.base_dir_for(self.job_id) / self.DWC_ZIP_NAME,
        )
        # Add data from DB
        self.fill_archive(arch, institution_code)

        # OK we issue warning in case of individual issue, but if there is no content at all
        # then it's an _error_.
        if (
            arch.events.count() == 0
            and arch.occurrences.count() == 0
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
        logger.info("------------ produce zip -------------- %s", self.DWC_ZIP_NAME)
        done_infos = {
            "collection_id": self.collection.id,
            "out_file": self.DWC_ZIP_NAME,
        }
        done_infos.update({"wrns": self.warnings})
        self.set_job_result(self.errors, infos=done_infos)

    def add_absent_occurrences(
        self, taxa_per_sample: Dict[str, Set[ClassifIDT]], arch: DwcArchive
    ) -> None:
        """
        Second pass, occurrence creations for absent taxa.
        """
        all_taxa = self.compute_all_seen_taxa(taxa_per_sample)
        occurrence_targets: Dict[int, WoRMSBO] = {}
        for k, v in self.computations_occurrence.items():
            if v is not None:
                occurrence_targets.update({int(k): self.coverage_taxa[v]})
        # For what's missing, issue an 'absent' record
        for an_event_id, an_id_set in taxa_per_sample.items():
            missing_for_sample = all_taxa.difference(an_id_set)
            for a_missing_id in missing_for_sample:
                occurrence_id = an_event_id + "_" + str(a_missing_id)
                # No need to catch any exception here, the lookup worked during the
                # "present" records generation.
                worms = occurrence_targets[a_missing_id]
                occ = DwC_Occurrence(
                    eventID=an_event_id,
                    occurrenceID=occurrence_id,
                    scientificName=worms.name,  # ETS stores scientificname as name,
                    scientificNameID=get_scientific_name_id(worms),
                    kingdom=worms.kingdom,
                    occurrenceStatus=OccurrenceStatusEnum.absent,
                    basisOfRecord=BasisOfRecordEnum.machineObservation,
                )
                arch.occurrences.add(occ)

    @staticmethod
    def compute_all_seen_taxa(
        taxa_per_sample: Dict[str, Set[ClassifIDT]],
    ) -> ClassifIDSetT:
        # Cumulate all categories
        all_taxa: ClassifIDSetT = set()
        for an_id_set in taxa_per_sample.values():
            all_taxa.update(an_id_set)
        return all_taxa

    @staticmethod
    def organisation_to_eml_person(an_org: Organization) -> EMLPerson:
        # an_org name for the moment - then will be edmo data in directories field
        return EMLPerson(organizationName=an_org.name)

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
                "%s user '%s' has no organization." % (for_messages, user.name)
            )
        else:
            orgacr = CollectionBO.get_institution_code(user.organisation.strip())
            if orgacr == "?":
                problems.append(
                    "Cannot determine short organization from %s org: '%s' (need at least a - or () )."
                    % (for_messages, user.organisation)
                )
                return ret, problems
            orgname = user.organisation.strip().split("-")[:-1]
            orgname = [o.strip() for o in orgname]
            organization = " - ".join(orgname) + " (" + orgacr.strip() + ")"
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
    MIN_CITATION_CHARS = 128
    MAX_ABSTRACT_CHARS = 1000
    """ Maximum size of a 'quality' description """
    """ Minimum size of a 'quality' citation """
    OK_LICENSES = [LicenseEnum.CC0, LicenseEnum.CC_BY, LicenseEnum.CC_BY_NC]

    def build_meta(self) -> Tuple[Optional[EMLMeta], str]:
        """
        Various queries/copies on/from the projects for getting metadata.
        Also extract the institutionCode from the collection.
        """
        identifier = EMLIdentifier(
            packageId=self.the_collection.external_id,
            system=self.the_collection.external_id_system,
        )

        title = EMLTitle(title=self.the_collection.title)

        creators: List[EMLPerson] = []
        creators_by_id: Dict[str, Any] = {
            str(a_user.id) + "_u": a_user
            for a_user in self.the_collection.creator_users
        }
        creators_by_id.update(
            {
                str(an_org.id) + "_o": an_org
                for an_org in self.the_collection.creator_organisations
            }
        )
        for an_id in self.the_collection.display_order[creators_key]:
            a_creator = creators_by_id[an_id]
            if an_id[-1] == user_order_type:
                person, errs = self.user_to_eml_person(
                    a_creator, "creator '%s'" % a_creator.name
                )
                if errs:
                    self.warnings.extend(errs)
                else:
                    assert person is not None
                    creators.append(person)
            else:
                creators.append(self.organisation_to_eml_person(a_creator))

        associates: List[EMLAssociatedPerson] = []
        associates_by_id: Dict[str, Any] = {
            str(a_user.id) + "_u": a_user
            for a_user in self.the_collection.associate_users
        }
        associates_by_id.update(
            {
                str(an_org.id) + "_o": an_org
                for an_org in self.the_collection.associate_organisations
            }
        )
        for an_id in self.the_collection.display_order[associates_key]:
            an_associate = associates_by_id[an_id]
            if an_id[-1] == user_order_type:
                person, errs = self.user_to_eml_person(
                    an_associate, "associated person %d" % an_associate.id
                )
                if errs:
                    self.warnings.extend(errs)
                else:
                    assert person is not None
                    associates.append(
                        self.eml_person_to_associated_person(person, ROLE_FOR_ASSOCIATE)
                    )
            else:
                person_from_org = self.organisation_to_eml_person(an_associate)
                role = ROLE_FOR_ASSOCIATE
                if an_associate == self.the_collection.code_provider_org:
                    role = "custody"
                associates.append(
                    self.eml_person_to_associated_person(person_from_org, role)
                )
        # TODO if needed
        # EMLAssociatedPerson = EMLPerson + specific role
        if len(creators) == 0:
            self.errors.append(
                "No valid data creator (user or organisation) found for EML metadata."
            )
        contact, errs = self.user_to_eml_person(
            self.the_collection.contact_user, "contact"
        )
        if contact is None:
            self.errors.append("No valid contact user found for EML metadata.")
            self.warnings.extend(errs)
        provider, errs = self.user_to_eml_person(
            self.the_collection.provider_user, "provider"
        )
        if provider is None:
            self.errors.append(
                "No valid metadata provider user found for EML metadata."
            )
            self.warnings.extend(errs)

        publication_date = now_time().date().isoformat()
        # the abstract appears as description in the ITP but it is the abstract field of the collection
        abstract = self.the_collection.abstract
        if not abstract:
            self.errors.append("Collection 'abstract' field is empty")
        elif len(abstract) < self.MIN_ABSTRACT_CHARS:
            self.errors.append(
                "Collection 'abstract' field is too short (%d chars) to make a good EMLMeta abstract. Minimum is %d"
                % (len(abstract), self.MIN_ABSTRACT_CHARS)
            )
        elif len(abstract) > self.MAX_ABSTRACT_CHARS:
            self.errors.append(
                "Collection 'abstract' field is too long (%d chars) to make a good EMLMeta abstract. Maximum is %d"
                % (len(abstract), self.MAX_ABSTRACT_CHARS)
            )
        citation = self.the_collection.citation
        if not citation:
            self.errors.append("Collection 'citation' field is empty")
        # elif len(citation) < self.MIN_CITATION_CHARS:
        #    self.errors.append(
        #        "Collection 'citation' field is too short (%d chars) to make a good EMLMeta citation. Minimum is %d"
        #        % (len(citation), self.MIN_CITATION_CHARS)
        #    )
        # the description is the collection description field and is stored in EML additional_info
        description = self.the_collection.description
        # temporary add description in additional_info
        additional_info = description  # Just to see if it goes through QC
        # additional_info = """  marine, harvested by iOBIS.
        # The OOV supported the financial effort of the survey.
        # We are grateful to the crew of the research boat at OOV that collected plankton during the temporal survey."""

        coll_license: LicenseEnum = cast(LicenseEnum, self.the_collection.license)
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
        publisher = self.PUBLISHER_ECOTAXA
        # Preferably one of https://www.emodnet-biology.eu/contribute?page=list&subject=thestdas&SpColID=552&showall=1#P
        keywords = EMLKeywordSet(
            keywords=[
                "Plankton",
                "Imaging",
                "EcoTaxa",  # Not in list above
                # "Ligurian sea" TODO: Geo area?
                # TODO: ZooProcess (from projects)
            ],
            keywordThesaurus="GBIF Dataset Type Vocabulary: "
            "http://rs.gbif.org/vocabulary/gbif/dataset_type.xml",
        )

        now = now_time().replace(microsecond=0)
        meta_plus = EMLAdditionalMeta(dateStamp=now.isoformat(), citation=citation)

        coll_title = self.the_collection.title
        info_url = (
            "https://ecotaxa.obs-vlfr.fr/api/collections/by_title?q=%s"
            % quote_plus(coll_title)
        )

        if len(self.errors) != 0:
            # Exit early, in case of problem, before moving to long operations
            return None, "?"

        # TODO: a marine regions substitute
        # Note: below can be very long for big projects
        (min_lat, max_lat, min_lon, max_lon) = ProjectBO.get_bounding_geo(
            self.session, self.the_collection.project_ids
        )
        geo_cov = EMLGeoCoverage(
            geographicDescription="See coordinates",
            westBoundingCoordinate=self.geo_to_txt(min_lon),
            eastBoundingCoordinate=self.geo_to_txt(max_lon),
            northBoundingCoordinate=self.geo_to_txt(min_lat),
            southBoundingCoordinate=self.geo_to_txt(max_lat),
        )

        # Note: below can be very long for big projects
        (min_date, max_date) = ProjectBO.get_date_range(
            self.session, self.the_collection.project_ids
        )
        time_cov = EMLTemporalCoverage(
            beginDate=timestamp_to_str(min_date), endDate=timestamp_to_str(max_date)
        )

        taxo_cov = self.get_taxo_coverage()

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
            description=[description],
            keywordSet=keywords,
            additionalInfo=additional_info,
            geographicCoverage=geo_cov,
            temporalCoverage=time_cov,
            taxonomicCoverage=taxo_cov,
            intellectualRights=licence,
            publisher=publisher,
            # project=project,
            maintenance="periodic review of origin data",
            maintenanceUpdateFrequency="unknown",  # From XSD
            additionalMetadata=meta_plus,
            informationUrl=info_url,
        )
        return ret, self.the_collection.get_institution_code(
            str(self.the_collection.code_provider_org)
        )

    def get_taxo_coverage(self) -> List[EMLTaxonomicClassification]:
        """
        Taxonomic coverage is the list of taxa which can be found in the projects, regardless
        of their validation state.
        """
        ret: List[EMLTaxonomicClassification] = []
        # Coverage is from recast "space", the biggest one
        worms_targets = list(self.coverage_taxa.values())
        # Error out if nothing at all
        if len(worms_targets) == 0:
            self.errors.append(
                "Could not match in WoRMS _any_ classification in this project"
            )
            return ret
        # Produce the coverage
        produced = set()
        for a_worms_entry in sorted(worms_targets, key=lambda t: t.name):
            rank = a_worms_entry.rank
            value = a_worms_entry.name
            assert rank is not None, "No rank for %s" % str(a_worms_entry)
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

    @classmethod
    def _sample_ref_for_message(cls, sample: Sample) -> str:
        """Always include project number for humans, it will allow location of sample"""
        return "'%s' (in #%d)" % (sample.orig_id, sample.projid)

    def fill_archive(self, arch: DwC_Archive, institution_code: str) -> None:
        """
        Add DwC files into the archive: events, occurrences, eMoFs
            We produce sample-type events.
        """
        dataset_name = self.sanitize_title(self.the_collection.title)
        samples_in_several_prjs = self.the_collection.homonym_samples(self.ro_session)
        if len(samples_in_several_prjs) > 0:
            logger.info("Homonym samples: %s", samples_in_several_prjs)
        # Per_sample taxa, in plain taxo "space"
        taxa_per_sample: Dict[str, Set[ClassifIDT]] = {}
        nb_sample = 0
        sample_count = self._get_fast_count(self.the_collection.project_ids)
        progress_range = 99
        for a_prj_id in self.the_collection.project_ids:
            samples = Sample.get_orig_id_and_model(self.ro_session, prj_id=a_prj_id)
            a_sample: Sample
            events = arch.events
            for _unused, a_sample in samples.items():
                assert a_sample.latitude is not None and a_sample.longitude is not None
                prfx = (
                    str(a_prj_id) + "_"
                    if a_sample.orig_id in samples_in_several_prjs
                    else ""
                )
                event_id = prfx + a_sample.orig_id
                evt_type = RecordTypeEnum.sample
                summ = Sample.get_sample_summary(self.session, a_sample.sampleid)
                if summ[0] is None or summ[1] is None:
                    self.empty_samples.append(self._sample_ref_for_message(a_sample))
                    continue
                assert a_sample.latitude is not None and a_sample.longitude is not None
                evt_date = self.event_date(summ[0], summ[1])
                latitude = self.geo_to_txt(float(a_sample.latitude))
                longitude = self.geo_to_txt(float(a_sample.longitude))
                evt = DwC_Event(
                    eventID=event_id,
                    type=evt_type,
                    institutionCode=institution_code,
                    datasetName=dataset_name,
                    eventDate=evt_date,
                    decimalLatitude=latitude,
                    decimalLongitude=longitude,
                    minimumDepthInMeters=str(summ[2]),
                    maximumDepthInMeters=str(summ[3]),
                )
                events.add(evt)
                self.add_eMoFs_about_sample(
                    sample=a_sample, arch=arch, event_id=event_id
                )
                # Humans first :)
                added_occurences = self.add_occurrences_for_sample(
                    sample=a_sample, arch=arch, event_id=event_id, predicted=False
                )
                taxa_per_sample[event_id] = {
                    val[1].taxo_id for val in added_occurences.values()
                }
                nb_added = len(added_occurences)
                if self.include_predicted:
                    by_ml_added_occurences = self.add_occurrences_for_sample(
                        sample=a_sample, arch=arch, event_id=event_id, predicted=True
                    )
                    nb_added += len(by_ml_added_occurences)
                    taxa_per_sample[event_id].update(
                        {val[1].taxo_id for val in by_ml_added_occurences.values()}
                    )
                if nb_added == 0:
                    self.warnings.append(
                        "No occurrence added for sample %s"
                        % self._sample_ref_for_message(a_sample)
                    )
                nb_sample += 1

                if nb_sample % self.OCCURENCE_REPORT_EVERY == 0:
                    msg = "Occurences %d of max %d" % (nb_sample, sample_count)
                    logger.info(msg)
                    self.update_progress(
                        int(1 + progress_range / sample_count * nb_sample), msg
                    )
                # Taxa-level eMoFs
                added_emofs = self.add_occurrence_eMoFs_for_sample(
                    sample=a_sample, arch=arch, event_id=event_id, predicted=False
                )
                if self.include_predicted:
                    _ = self.add_occurrence_eMoFs_for_sample(
                        sample=a_sample, arch=arch, event_id=event_id, predicted=True
                    )
                # Ensure EMOFs (in recast space) are also covered in occurrences (so far in raw space)
                self.cover_EMOF_in_occurrences(
                    arch, event_id, added_occurences, added_emofs
                )
                # Sample-level eMoFs
                self.add_instrument_eMoFs_about_sample(
                    sample=a_sample, arch=arch, event_id=event_id
                )

        # Loop over _absent_ data
        # For https://github.com/ecotaxa/ecotaxa_dev/issues/603
        # Loop over taxa which are in the collection but not in present sample
        if self.with_absent:
            self.add_absent_occurrences(taxa_per_sample, arch)

    nine_nine_re = re.compile("999+.0$")

    # The nets in dataset but no official BODC definition
    bodc_unknown_nets = {
        "jb": "Juday-Bogorov net",
        "regent": "Regent net",
        "rg": "Regent net",
    }

    # noinspection PyPep8Naming
    def add_eMoFs_about_sample(
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
                    str(total_water_volume)
                    + " in "
                    + self._sample_ref_for_message(sample)
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
                "Could not extract sampling net name and features from sample %s: %s."
                % (self._sample_ref_for_message(sample), str(e))
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
                self.unknown_nets.setdefault(net_type, []).append(
                    self._sample_ref_for_message(sample)
                )
            if ins is not None:
                arch.emofs.add(ins)
            # Produce net traits even if no net
            arch.emofs.add(SamplingNetMeshSizeInMicrons(event_id, str(net_mesh)))
            arch.emofs.add(
                SampleDeviceApertureAreaInSquareMeters(event_id, str(net_surf))
            )

    def _get_fast_count(self, project_ids: ProjectIDListT) -> int:
        # Get a fast count of the maximum of what to do
        count_sql = "SELECT COUNT(*) FROM samples WHERE projid IN :prjs"
        res = self.ro_session.execute(text(count_sql), {"prjs": tuple(project_ids)})
        sample_count = res.one()[0]
        return sample_count

    @lru_cache(maxsize=None)
    def _get_instrument_url_and_label(
        self, project: Project
    ) -> Optional[Tuple[str, str]]:
        """Cache projects' instrument URL, and looked up label"""
        url = project.instrument.bodc_url
        if url is None:
            self.warnings.append(
                "Project %s instrument does not have an associated BODC term."
                % (project.projid,)
            )
            return None
        label = NERCFetcher.get_preferred_name(url)
        return url, label

    def add_instrument_eMoFs_about_sample(
        self, sample: Sample, arch: DwC_Archive, event_id: str
    ) -> None:
        """
        Add imaging instrument eMoF. Unsure at which level the event should be, so kept separated.
        """
        instrument_url_and_label = self._get_instrument_url_and_label(sample.project)
        if instrument_url_and_label is not None:
            ins = AnalyticalInstrumentName(
                event_id=event_id,
                value_id=instrument_url_and_label[0],
                value=instrument_url_and_label[1],
            )
            arch.emofs.add(ins)

    @classmethod
    def _aggregate_for_sample(
        cls,
        ro_session: Session,
        sample: Sample,
        recast_occurrences: TaxoRemappingT,
        with_computations: List[SciExportTypeEnum],
        formulae: Dict[str, str],
        predicted: bool,
        warnings: List[str],
    ) -> Dict[ClassifIDT, SampleAggregForTaxon]:
        """
        :param sample: The Sample for which computations needs to be done.
        :param with_computations: Computations to do.
        :param morpho2phylo: The Morpho taxa to their nearest Phylo parent.

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
            object_set = CommonObjectSets.predictedInSample(ro_session, sample)
        else:
            object_set = CommonObjectSets.validatedInSample(ro_session, sample)

        # Abundances, 'simple' count but eventually with remapping
        counts = cls.abundances_for_sample(
            ro_session, object_set, recast_occurrences, warnings
        )

        for a_count in counts:
            txo_id, count = a_count["txo_id"], a_count["count"]
            ret[txo_id] = SampleAggregForTaxon(txo_id, count, None, None)

        if SciExportTypeEnum.concentrations in with_computations:
            # Enrich with concentrations
            concentrations = cls.concentrations_for_sample(
                ro_session,
                formulae,
                object_set,
                recast_occurrences,
                warnings,
            )
            conc_wrn_txos = []
            for a_conc in concentrations:
                txo_id, conc = a_conc["txo_id"], a_conc["conc"]
                if conc == conc:  # not-a-NaN test
                    ret[txo_id].concentration = conc
                else:
                    conc_wrn_txos.append(txo_id)
            if len(conc_wrn_txos) > 0:
                wrn = "Sample {} taxo(s) #{}: Computed concentration is NaN, input data is missing or incorrect"
                wrn = wrn.format(cls._sample_ref_for_message(sample), conc_wrn_txos)
                warnings.append(wrn)

        if SciExportTypeEnum.biovols in with_computations:
            # Enrich with biovolumes, note that we need previous formulae for scaling
            biovolumes = cls.biovolumes_for_sample(
                ro_session,
                formulae,
                object_set,
                recast_occurrences,
                warnings,
            )
            biovol_wrn_txos = []
            for a_biovol in biovolumes:
                txo_id, biovol = a_biovol["txo_id"], a_biovol["biovol"]
                if biovol == biovol:  # NaN test
                    ret[txo_id].biovolume = biovol
                else:
                    biovol_wrn_txos.append(txo_id)
            if len(biovol_wrn_txos) > 0:
                wrn = "Sample {} taxo(s) #{}: Computed biovolume is NaN, input data is missing or incorrect"
                wrn = wrn.format(cls._sample_ref_for_message(sample), biovol_wrn_txos)
                warnings.append(wrn)

        return ret

    @classmethod
    def abundances_for_sample(
        cls,
        ro_session: Session,
        obj_set: DescribedObjectSet,
        morpho2phylo: TaxoRemappingT,
        warnings: List[str],
    ) -> List[Dict[str, Any]]:
        """
        Compute abundances (count) for given sample.
        No zero count is produced, so this also acts like a "present" filter.
        """
        aug_qry = ObjectSetQueryPlus(obj_set)
        aug_qry.remap_categories(morpho2phylo)
        aug_qry.add_selects(["txo.id", aug_qry.COUNT_STAR])
        aug_qry.set_aliases(
            {"txo.id": "txo_id", aug_qry.COUNT_STAR: "count"}
        ).set_grouping(ResultGrouping.BY_TAXO)
        return aug_qry.get_result(ro_session, lambda e: warnings.append(e))

    @classmethod
    def concentrations_for_sample(
        cls,
        ro_session: Session,
        formulae: Dict[str, str],
        obj_set: DescribedObjectSet,
        morpho2phylo: TaxoRemappingT,
        warnings: List[str],
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
        return aug_qry.get_result(ro_session, lambda e: warnings.append(e))

    @classmethod
    def biovolumes_for_sample(
        cls,
        ro_session: Session,
        formulae: Dict[str, str],
        obj_set: DescribedObjectSet,
        morpho2phylo: TaxoRemappingT,
        warnings: List[str],
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
        return aug_qry.get_result(ro_session, lambda e: warnings.append(e))

    def add_occurrences_for_sample(
        self, sample: Sample, arch: DwC_Archive, event_id: str, predicted: bool
    ) -> WoRMSAggregT:
        """
        Add DwC occurrences, for given sample, into the archive.
        A single line per WoRMS taxon, for each taxon having at least one object.
        If 'predicted' is set, do the counts on predicted (but not validated) objects.
            Otherwise, use human-validated objects.
        """
        aggregs = self._aggregate_for_sample(
            ro_session=self.ro_session,
            sample=sample,
            recast_occurrences=self.computations_occurrence,
            with_computations=[SciExportTypeEnum.abundances],
            # SciExportTypeEnum.abundances is needed for production of per aphia_id in present def.
            formulae=dict(),  # Nothing to compute
            predicted=predicted,
            warnings=self.warnings,
        )
        mapping: Dict[ClassifIDT, WoRMSBO] = {}
        for k, v in self.computations_occurrence.items():
            if v is not None:
                mapping.update({int(k): self.coverage_taxa[v]})

        by_abundance_desc, not_found = self._occurrences_from_aggregations(
            aggregs, mapping, event_id, predicted, self.warnings
        )
        for an_id in not_found:
            # Mapping failed, count how many of them
            if an_id in self.ignored_count:
                self.ignored_count[an_id] += aggregs[an_id].abundance
            else:
                # Sanity check, there should be no morpho left
                # TODO: Not relevant anymore, find another sanity check (e.g. no dest is a source?)
                # if self.auto_morpho:
                #     assert an_id not in self.morpho2phylo
                self.ignored_morpho += aggregs[an_id].abundance

        # Loop over WoRMS taxa
        for a_lsid, for_lsid in by_abundance_desc.items():
            occurrence_id, aggreg_for_lsid, worms = for_lsid
            self.produced_count += aggreg_for_lsid.abundance
            occ = DwC_Occurrence(
                eventID=event_id,
                occurrenceID=occurrence_id,
                # Below is better as an EMOF @see CountOfBiologicalEntity
                # individualCount=individual_count,
                scientificName=worms.name,  # scientificname,
                scientificNameID=get_scientific_name_id(worms),
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
            arch.occurrences.add(occ)
        return by_abundance_desc

    @staticmethod
    def _occurrences_from_aggregations(
        aggregs: Dict[ClassifIDT, SampleAggregForTaxon],
        phylo2worms: Dict[ClassifIDT, WoRMSBO],
        event_id: str,
        predicted: bool,
        warnings: List[str],
    ) -> Tuple[WoRMSAggregT, ClassifIDSetT]:
        """Mix aggregations from a set of EcoTaxa taxa and produce data for the equivalent DwCA record."""
        # Group by lsid, which is mostly an aphia_id, in order to have a single occurrence line even if several taxa
        # map to same WoRMS.
        by_lsid: WoRMSAggregT = {}
        not_found: ClassifIDSetT = set()
        for an_id, an_aggreg in sorted(
            aggregs.items(), reverse=True
        ):  # The order influences composition output
            assert an_aggreg is not None, "Unexpected None aggreg' in %s" % str(aggregs)
            worms = phylo2worms.get(an_id)
            if worms is None:
                not_found.add(an_id)
                continue
            worms_lsid = str(worms.aphia_id)
            assert worms_lsid is not None
            if worms_lsid not in by_lsid:
                # Take the original taxo ID to build an occurrence ID
                # It's unique because it's based on the sample ID, and we append the taxon EcoTaxa ID
                occurrence_id = (
                    event_id + ("_P" if predicted else "") + "_" + str(an_id)
                )
                by_lsid[worms_lsid] = (occurrence_id, an_aggreg, worms)
            else:
                # Manage here the grouping, i.e. the mapping of _several_ EcoTaxa taxa to a _single_ Worms entry.
                # e.g. in jb20140319_72396_92230
                #      both 72396 (Diphyidae) and 92230 (Diphyidae>bract)
                #      become Diphyidae 135338 (https://www.marinespecies.org/aphia.php?p=taxdetails&id=135338)
                occurrence_id, aggreg_for_lsid, _worms = by_lsid[worms_lsid]
                # Accumulate aggregation
                try:
                    aggreg_for_lsid = aggreg_for_lsid + an_aggreg
                except AssertionError:
                    warnings.append(
                        "Cannot accumulate %s into %s for lsid %s"
                        % (str(an_aggreg), str(aggreg_for_lsid), worms_lsid)
                    )
                # Add the new taxon ID to complete the occurrence ID
                occurrence_id += "_" + str(an_id)
                by_lsid[worms_lsid] = (occurrence_id, aggreg_for_lsid, worms)

        # Sort for order predictability
        by_lsid_sorted = sorted(
            by_lsid.items(),
            key=lambda itm: (
                -itm[1][1].abundance,  # Aggreg abundance, desc
                itm[1][2].aphia_id,  # To disambiguate
            ),
        )
        ret = OrderedDict(by_lsid_sorted)
        # if "urn:lsid:marinespecies.org:taxname:104081" in ret:
        #     logger.info("ret:", ret)
        return ret, not_found

    def add_occurrence_eMoFs_for_sample(
        self, sample: Sample, arch: DwC_Archive, event_id: str, predicted: bool
    ) -> WoRMSAggregT:
        """
        Add DwC occurrence eMoFs, for given sample, into the archive. A single line per WoRMS taxon.
        Note: We're in recast-ed taxo "space".
        If 'predicted' is set, do the computations on predicted (but not validated) objects.
        Otherwise, use human-validated objects.
        """
        aggregs = self._aggregate_for_sample(
            ro_session=self.ro_session,
            sample=sample,
            recast_occurrences=self.computations_emof,
            with_computations=self.with_computations,
            formulae=self.formulae,
            predicted=predicted,
            warnings=self.warnings,
        )
        mapping: Dict[ClassifIDT, WoRMSBO] = {}
        for k, v in self.computations_occurrence.items():
            if v is not None:
                mapping.update({int(k): self.coverage_taxa[v]})

        by_abundance_desc, not_found = self._occurrences_from_aggregations(
            aggregs,
            mapping,
            event_id,
            predicted,
            self.warnings,
        )

        # Loop over WoRMS taxa
        for a_lsid, for_lsid in by_abundance_desc.items():
            occurrence_id, aggreg_for_lsid, worms = for_lsid
            self.add_eMoFs_for_occurrence(
                arch=arch,
                event_id=event_id,
                occurrence_id=occurrence_id,
                values=aggreg_for_lsid,
            )
        return by_abundance_desc

    @staticmethod
    def round_but_no_zero(number: float, ndigits: int) -> float:
        while (ret := round(number, ndigits)) == 0:
            ndigits += 1
        return ret

    @staticmethod
    def add_eMoFs_for_occurrence(
        arch: DwC_Archive,
        event_id: str,
        occurrence_id: OccIDT,
        values: SampleAggregForTaxon,
    ) -> None:
        """
        Add eMoF instances, for given occurrence and existing values, into the archive.
        """
        cnt_emof = CountOfBiologicalEntity(
            event_id, occurrence_id, str(values.abundance)
        )
        arch.emofs.add(cnt_emof)
        if values.concentration is not None:
            value = DarwinCoreExport.round_but_no_zero(values.concentration, 6)
            emof = AbundancePerUnitVolumeOfTheWaterBody(
                event_id, occurrence_id, str(value)
            )
            arch.emofs.add(emof)
        if values.biovolume is not None:
            value = DarwinCoreExport.round_but_no_zero(values.biovolume, 6)
            emof2 = BiovolumeOfBiologicalEntity(event_id, occurrence_id, str(value))
            arch.emofs.add(emof2)

    @staticmethod
    def cover_EMOF_in_occurrences(
        arch: DwC_Archive,
        event_id: str,
        raw_occurrences: WoRMSAggregT,
        recast_occurrences: WoRMSAggregT,
    ):
        present_occ_ids = set([t[0] for t in raw_occurrences.values()])
        for a_lsid, for_lsid in recast_occurrences.items():
            occurrence_id, aggreg_for_lsid, worms = for_lsid
            if occurrence_id in present_occ_ids:
                continue
            occ = DwC_Occurrence(
                eventID=event_id,
                occurrenceID=occurrence_id,
                scientificName=worms.name,
                scientificNameID=get_scientific_name_id(worms),
                kingdom=worms.kingdom,
                occurrenceStatus=OccurrenceStatusEnum.present,
                basisOfRecord=BasisOfRecordEnum.machineObservation,
            )
            arch.occurrences.add(occ)

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

    def keep_stats(self, taxon_info: WoRMSBO, count: int) -> None:
        """
        Keep statistics per various entries.
        """
        assert taxon_info.rank is not None
        stats = self.stats_per_rank.setdefault(
            taxon_info.rank, {"cnt": 0, "nms": set()}
        )
        stats["cnt"] += count
        stats["nms"].add(taxon_info.name)

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
            self.warnings.append("Empty samples found: %s" % str(self.empty_samples))
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

    def compute_taxo_spaces(self):
        """
        We have occurrence and emof  "spaces"
        """
        res = self.query_taxo_mapping(RecastOperation.dwca_export_occurrence)
        if res is None:
            raise HTTPException(
                status_code=HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Taxonomy renames is required. see Taxonomy recast",
            )
        renames_occurrence = res
        # Args are serialized in JSON -> keys have become str and 0 val becomes None
        self.computations_occurrence = {
            int(k): v if v != 0 else None for k, v in renames_occurrence.items()
        }
        res = self.query_taxo_mapping(RecastOperation.dwca_export_emof)
        if res is None:
            renames_emof = renames_occurrence
        else:
            renames_emof = res
        self.computations_emof = {
            int(k): v if v != 0 else None for k, v in renames_emof.items()
        }
        coverage_taxa = list(self.computations_occurrence.copy().values())
        coverage_taxa.extend(list(self.computations_emof.copy().values()))
        self.coverage_taxa = WoRMSifier.do_wormsify(
            self.ro_session, list(coverage_taxa)
        )

        # Prepare warnings for non-matches

        for an_id in self.unreferenced_ids(
            list(set(self.coverage_taxa.keys())), list(set(coverage_taxa))
        ):
            taxon = self.session.get(Taxonomy, an_id)
            assert taxon is not None
            self.ignored_taxa[an_id] = (an_id, taxon.name)
            self.ignored_count[an_id] = 0

    def query_taxo_mapping(
        self,
        operation: RecastOperation,
    ) -> Optional[TaxoRemappingT]:
        res = WoRMSifier.query_recast(
            self.ro_session,
            self.current_user_id,
            self.collection.id,
            operation,
            True,
            for_update=False,
        ).all()
        if res is None or len(res) != 1:
            return None
        the_one: TaxoRecast = res[0]
        return json.loads(str(the_one.transforms))

    def get_worms_targets(self, recastids: List[int]) -> List[WoRMSBO]:
        taxa = TaxonBOSet(self.ro_session, recastids)
        targets: List[WoRMSBO] = [create_worms_bo(taxon) for taxon in taxa.as_list()]
        return targets

    @staticmethod
    def unreferenced_ids(
        ids: Iterable[ClassifIDT], refids: Iterable[ClassifIDT]
    ) -> ClassifIDListT:
        """Return the taxa from ids, not known in self"""
        return [an_id for an_id in ids if an_id not in refids]

    @staticmethod
    def apply_recast(
        recast: TaxoRemappingT, present_morpho2phylo: TaxoRemappingT
    ) -> TaxoRemappingT:
        recast = recast.copy()  # We destroy it, protect the arg

        def end_of_chain(recast_idx: ClassifIDT) -> Optional[ClassifIDT]:
            ret = recast[recast_idx]
            if ret in recast:
                ret = end_of_chain(ret)  # Infinite loop ->stack issue
            return ret

        # e.g. m2p: { 84974: 83278, 84975: 83278 }
        # recast: { 83278: 72398 }
        # present_morpho2phylo: TaxoRemappingT = self.morpho2phylo.copy()
        for from_, to_ in present_morpho2phylo.items():
            if from_ in recast:
                # The _source_ (morpho) is a recast source e.g. 84975 -> 83278 but 84975 -> 72398
                # Override with recast so become e.g. 84975 -> 72398
                present_morpho2phylo[from_] = end_of_chain(from_)
                # Note: if new_to None then drop it's OK
                continue
            if to_ in recast:
                # The _target_ (phylo) is a recast source e.g. 92012 -> 83278 and 83278 -> 72398
                # Compose the recast so become e.g. 92012 -> 72398
                present_morpho2phylo[from_] = end_of_chain(to_)
                # Note: new_to might be None, so the taxon is dropped
        # Inject recasts but don't override rules applications
        for from_ in set(recast.keys()).intersection(present_morpho2phylo.keys()):
            del recast[from_]
        present_morpho2phylo.update(recast)
        return present_morpho2phylo

    def get_automatic_worms_taxo(self) -> TaxoRemappingT:
        # TODO: This could be expressed directly in a join in below query
        project_ids = [a_project.projid for a_project in self.collection.projects]
        # Fetch the used taxa in the projects
        taxo_qry = self.session.query(ProjectTaxoStat.id).distinct()
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.nbr > 0)
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.id > 0)  # Exclude unclassified
        taxo_qry = taxo_qry.filter(ProjectTaxoStat.projid.in_(project_ids))
        used_taxa = [an_id for an_id, in taxo_qry]
        # Note: Not _All_ used taxa will appear in occurrences, recast does not
        # impact occurrences output, @see def add_occurrences_for_sample.
        # OTOH, the recast target taxa will (likely) appear in coverage as it comes
        # from computed quantities.
        wormsifier = WoRMSifier()
        wormsifier.do_match(self.ro_session, used_taxa)
        worms_auto = wormsifier.phylo2worms.copy()
        worms_auto.update(wormsifier.morpho2phylo.copy())
        return worms_auto
