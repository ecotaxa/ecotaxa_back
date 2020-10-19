# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# End-user services around taxonomy tree.
#
from typing import List, Optional

from API_models.taxonomy import TaxaSearchRsp
from API_operations.helpers.Service import Service
from BO.Classification import ClassifIDT, ClassifIDListT
from BO.Project import ProjectBOSet
from BO.Taxonomy import TaxonomyBO, TaxonBO, TaxonBOSet
from BO.User import UserIDT, UserBO


class TaxonomyService(Service):
    """

    """

    def __init__(self):
        super().__init__()

    def search(self, current_user_id: Optional[UserIDT],
               prj_id: Optional[int],
               query: str) -> List[TaxaSearchRsp]:
        """
            See caller doctext for specifications.
        """
        query_len = len(query)
        # Arrange query
        query = query.lower()
        # " " and "*" mean "any chars"
        query = query.replace("*", "%").replace(" ", "%")
        # It's possible to ask for both child & parent at the same time, using "<"
        # So "<" is kind of operator "descending of"
        terms = [sub + r"%" if (not sub or sub[-1] != '%') else sub  # Semantic is 'start with'
                 for sub in query.split("<")]
        # Conventionally, the first term is a filter on display_name
        display_name_term = terms[0]
        name_terms = terms[1:]

        # Compose the query from different case
        limit_ids_to = None
        include_ids = []
        return_order = {}
        # Get preset list, to favor in result order
        preset = set()
        if prj_id is not None:
            the_prj = ProjectBOSet.get_one(self.session, prj_id)
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
        res = TaxonomyBO.query(self.session, limit_ids_to, include_ids, display_name_term, name_terms)
        mru_ret = []
        preset_ret = []
        others_ret = []
        # Carefully order the result
        for a_rec in res:
            classif_id = a_rec['id']
            is_preset = 1 if classif_id in preset else 0
            to_add = TaxaSearchRsp(id=classif_id,
                                   text=a_rec['display_name'],
                                   pr=is_preset)
            if classif_id in return_order:
                mru_ret.append(to_add)
            elif is_preset:
                preset_ret.append(to_add)
            else:
                others_ret.append(to_add)
        mru_ret.sort(key=lambda r: return_order[r.id])
        return mru_ret + preset_ret + others_ret

    def query(self, taxon_id: ClassifIDT) -> Optional[TaxonBO]:
        ret = self.query_set([taxon_id])
        if not ret:
            return None
        else:
            return ret[0]

    def query_set(self, taxon_ids: ClassifIDListT) -> List[TaxonBO]:
        ret = TaxonBOSet(self.session, taxon_ids)
        return ret.taxa
