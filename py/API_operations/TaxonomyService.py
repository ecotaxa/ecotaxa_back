# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# End-user services around taxonomy tree.
#
from datetime import datetime
from typing import List, Optional, Dict, Any

from API_models.taxonomy import TaxaSearchRsp
from API_operations.helpers.Service import Service
from BO.Classification import ClassifIDT, ClassifIDListT
from BO.Project import ProjectBOSet
from BO.ReClassifyLog import ReClassificationBO
from BO.Taxonomy import TaxonomyBO, TaxonBO, TaxonBOSet
from BO.User import UserIDT, UserBO
from DB.Project import ProjectTaxoStat, Project, ProjectIDT
from DB.Taxonomy import Taxonomy
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class TaxonomyService(Service):
    """ """

    def __init__(self) -> None:
        super().__init__()

    def status(self, _current_user_id: UserIDT) -> Optional[datetime]:
        """
        Return the freshness status of the taxonomy tree.
        Fresh == recently updated from the Taxonomy server.
        """
        tree_info = TaxonomyBO.get_tree_status(self.session)
        # The column is NULL-able so this can happen:
        # tree_info.lastserverversioncheck_datetime is None
        return tree_info.lastserverversioncheck_datetime

    def search(
        self, current_user_id: Optional[UserIDT], prj_id: Optional[int], query: str
    ) -> List[TaxaSearchRsp]:
        """
        See caller doctext for specifications.
        """
        query_len = len(query)
        # Arrange query
        query = query.lower()
        # " " and "*" mean "any chars"
        query = query.replace("*", "%").replace(" ", "%")
        # Old sophisticated version which allowed lineage search using '<' separator
        # It's possible to ask for both child & parent at the same time, using "<"
        # So "<" is kind of operator "descending of"
        # terms = [sub + r"%" if (not sub or sub[-1] != '%') else sub  # Semantic is 'start with'
        #          for sub in query.split("<")]
        # Conventionally, the first term is a filter on display_name
        display_name_term = query + "%"  # terms[0]
        name_terms: List[str] = []  # terms[1:]

        # Compose the query from different case
        limit_ids_to = None
        include_ids = []
        return_order = {}
        # Get preset list, to favor in result order
        preset = set()
        if prj_id is not None:
            the_prj = ProjectBOSet.get_one(self.ro_session, prj_id)
            if the_prj is not None:
                include_ids = the_prj.get_preset()
                preset = set(include_ids)
        if current_user_id is None:
            # Unauthenticated call
            if query_len < 3:
                limit_ids_to = []  # No MRU, no output whatever filters
        else:
            # Authenticated call
            if query_len < 3 and prj_id is not None:
                # The query will limit to mru list, if 0 length then it's % i.e. all
                limit_ids_to = UserBO.get_mru(self.session, current_user_id, prj_id)
                # And arrange they are in first
                return_order = {cl_id: num for num, cl_id in enumerate(limit_ids_to)}
        # Do the query
        res = TaxonomyBO.query(
            self.ro_session, limit_ids_to, include_ids, display_name_term, name_terms
        )
        mru_ret = []
        preset_ret = []
        others_ret = []
        # Carefully order the result
        for a_rec in res:
            classif_id = a_rec["id"]
            renm_id = a_rec["rename_to"]
            is_preset = 1 if classif_id in preset else 0
            to_add = TaxaSearchRsp(
                id=classif_id, renm_id=renm_id, text=a_rec["display_name"], pr=is_preset
            )
            if classif_id in return_order:
                mru_ret.append(to_add)
            elif is_preset:
                preset_ret.append(to_add)
            else:
                others_ret.append(to_add)
        mru_ret.sort(key=lambda r: return_order[r.id])
        return mru_ret + preset_ret + others_ret

    def query_roots(self) -> List[TaxonBO]:
        """
        Return root (no parents) categories/taxa.
        """
        qry = self.ro_session.query(Taxonomy.id)
        qry = qry.filter(Taxonomy.parent_id.is_(None))
        root_ids = [taxon_id for taxon_id, in qry]
        return self.query_set(root_ids)

    def query(self, taxon_id: ClassifIDT) -> Optional[TaxonBO]:
        ret = self.query_set([taxon_id])
        if not ret:
            return None
        else:
            return ret[0]

    def query_usage(self, taxon_id: ClassifIDT) -> List[Dict[str, Any]]:
        taxo_and_prjs_qry = self.session.query(
            ProjectTaxoStat.nbr_v, Project.projid, Project.title
        )
        taxo_and_prjs_qry = taxo_and_prjs_qry.filter(
            (Project.projid == ProjectTaxoStat.projid)
            & (ProjectTaxoStat.nbr_v > 0)
            & (ProjectTaxoStat.id == taxon_id)
        )
        taxo_and_prjs_qry = taxo_and_prjs_qry.order_by(ProjectTaxoStat.nbr_v.desc())
        logger.info("qry:%s", taxo_and_prjs_qry)
        ret = [
            {"projid": projid, "title": title, "nb_validated": nbr_v}
            for nbr_v, projid, title in taxo_and_prjs_qry
        ]
        return ret

    def query_set(self, taxon_ids: ClassifIDListT) -> List[TaxonBO]:
        ret = TaxonBOSet(self.ro_session, taxon_ids)
        return ret.as_list()

    def most_used_non_advised(
        self, _current_user_id: Optional[UserIDT], taxon_ids: ClassifIDListT
    ) -> List[TaxonBO]:
        prev_choices = ReClassificationBO.previous_choices(self.ro_session, taxon_ids)
        ret_taxa = []
        for a_taxon_id in taxon_ids:
            # If no relevant previous choice, return source
            found_choice = prev_choices.get(a_taxon_id, a_taxon_id)
            ret_taxa.append(found_choice)
        # Index as we need exact order
        ret_dict = {
            a_taxon.id: a_taxon
            for a_taxon in TaxonBOSet(self.ro_session, ret_taxa).taxa
        }
        return [ret_dict[txid] for txid in ret_taxa]

    def reclassification_history(
        self, _current_user_id: Optional[UserIDT], project_id: ProjectIDT
    ) -> List[Dict[str, Any]]:
        history = ReClassificationBO.history_for_project(self.ro_session, project_id)
        return history
