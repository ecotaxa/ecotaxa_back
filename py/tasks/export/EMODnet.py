# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from os.path import join
from typing import Dict

from api.exports import EMODNetExportReq, EMODNetExportRsp
from db.Project import Project
from db.Sample import Sample
from db.Utils import timestamp_to_str
from formats.EMODnet.Archive import DwC_Archive
from formats.EMODnet.DatasetMeta import DatasetMetadata
from formats.EMODnet.MoF import SamplingSpeed, Abundance
from formats.EMODnet.models import DwC_Event, RecordTypeEnum, DwC_Occurrence, OccurrenceStatusEnum, BasisOfRecordEnum
from framework.Service import Service
from fs.TempDirForTasks import TempDirForTasks
from tasks.export.TaxaUtils import TaxaCache, TaxonInfoForSample, TaxonInfo, RANKS_BY_ID
from tech.DynamicLogs import get_logger, switch_log_to_file

logger = get_logger(__name__)


class EMODNetExport(Service):
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

    def __init__(self, req: EMODNetExportReq):
        super().__init__()
        self.req = req
        self.task_id = 9999
        # Get a temp directory
        self.temp_for_task = TempDirForTasks(join(self.link_src, 'temptask'))
        self.temp_dir = self.temp_for_task.base_dir_for(self.task_id)
        # Redirect logging
        log_file = self.temp_dir / 'TaskLogBack.txt'
        switch_log_to_file(str(log_file))
        # Summary for logging issues
        self.filtered_taxa: Dict[int, str]
        self.stats_per_rank: Dict[int, Dict] = {}

    DWC_ZIP_NAME = "dwca.zip"
    taxa_cache = TaxaCache()

    def run(self) -> EMODNetExportRsp:
        logger.info("------------ starting --------------")
        ret = EMODNetExportRsp(task_id=0)
        self.taxa_cache.load()
        # Create a container
        arch = DwC_Archive(DatasetMetadata(self.req.meta), self.temp_dir / self.DWC_ZIP_NAME)
        # Add data from DB
        self.add_events(arch)
        # Produced the zip
        arch.build()
        self.taxa_cache.save()
        self.log_stats()
        return ret

    def add_events(self, arch: DwC_Archive):
        """
            Add DwC events into the archive.
                We produce sample-type events.
        """
        institution_code = "IMEV"
        prj_id = self.req.project_ids[0]
        prj = self.session.query(Project).filter_by(projid=prj_id).first()
        assert prj is not None, "Project %d not found" % prj_id
        ds_name = self.sanitize_title(prj.title)
        samples = Sample.get_orig_id_and_pk(self.session, prj_id=prj_id)
        a_sample: Sample
        events = arch.events
        for orig_id, a_sample in samples.items():
            event_id = orig_id
            evt_type = RecordTypeEnum.sample
            summ = Sample.get_sample_summary(self.session, a_sample.sampleid)
            evt_date = self.event_date(summ[0], summ[1])
            # Round coordinates to ~ 110mm
            latitude = "%.6f" % a_sample.latitude
            longitude = "%.6f" % a_sample.longitude
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

    @staticmethod
    def add_eMoFs_for_sample(arch: DwC_Archive, event_id: str):
        """
            Add eMoF instances, for given sample, i.e. event, into the archive.
        """
        # TODO: it's just an example
        emof = SamplingSpeed(event_id, "2")
        arch.emofs.add(emof)

    def add_occurences(self, arch: DwC_Archive, event_id: str, sample_id: int):
        """
            Add DwC occurences, for given sample, into the archive.
        """
        occurences = arch.occurences
        # Fetch data from DB
        db_per_taxon = Sample.get_sums_by_taxon(self.session, sample_id)
        # Build a dict taxon_id -> info
        per_taxon: Dict[int, TaxonInfoForSample] = {a_sum[0]: TaxonInfoForSample(a_sum[1]) for a_sum in db_per_taxon}
        self.enrich_taxa(per_taxon)
        # Output
        for an_id, taxon_4_sample in per_taxon.items():
            taxon_info = taxon_4_sample.taxon_info
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
        emof = Abundance(event_id, occurrence_id, "452")
        arch.emofs.add(emof)

    def enrich_taxa(self, taxa_dict: Dict[int, TaxonInfoForSample]):
        """
            For each taxon_id in taxa_dict keys, gather name & aphiaID
        """
        taxa_cache = self.taxa_cache
        taxa_cache.gather_names_for(self.session, taxa_dict.keys())
        taxa_cache.collect_worms_for(taxa_dict.keys())
        # Link TaxonInfo after lookups
        for an_id, taxon_4_sample in taxa_dict.items():
            taxon_4_sample.taxon_info = taxa_cache.get(an_id)

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
            logger.info("rank '%s' stats %s", RANKS_BY_ID[a_rank], self.stats_per_rank[a_rank])
