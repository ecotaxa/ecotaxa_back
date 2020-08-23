# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#
from typing import List, Set

from DB import ResultProxy, Session


class TaxonomyBO(object):
    """
        Holder for methods on taxonomy tree.
    """

    @staticmethod
    def find_ids(session: Session, classif_id_seen: List):
        """
            Return input IDs for the existing ones.
        """
        res: ResultProxy = session.execute(
            "SELECT id "
            "  FROM taxonomy "
            " WHERE id = ANY (:een)",
            {"een": list(classif_id_seen)})
        return {int(r['id']) for r in res}

    @staticmethod
    def resolve_taxa(session: Session, taxo_found, taxon_lower_list):
        """
            Match taxa in taxon_lower_list and return the matched ones in taxo_found.
        """
        res: ResultProxy = session.execute(
            """SELECT t.id, lower(t.name) AS name, lower(t.display_name) AS display_name, 
                      lower(t.name)||'<'||lower(p.name) AS computedchevronname 
                FROM taxonomy t
                LEFT JOIN taxonomy p on t.parent_id = p.id
                WHERE lower(t.name) = ANY(:nms) OR lower(t.display_name) = ANY(:dms) 
                    OR lower(t.name)||'<'||lower(p.name) = ANY(:chv) """,
            {"nms": taxon_lower_list, "dms": taxon_lower_list, "chv": taxon_lower_list})
        for rec_taxon in res:
            for found_k, found_v in taxo_found.items():
                if ((found_k == rec_taxon['name'])
                        or (found_k == rec_taxon['display_name'])
                        or (found_k == rec_taxon['computedchevronname'])
                        or (('alterdisplayname' in found_v) and (
                                found_v['alterdisplayname'] == rec_taxon['display_name']))):
                    taxo_found[found_k]['nbr'] += 1
                    taxo_found[found_k]['id'] = rec_taxon['id']

    @staticmethod
    def names_for(session: Session, id_list: List[int]):
        """
            Get taxa names from id list.
        """
        ret = {}
        res: ResultProxy = session.execute(
            """SELECT t.id, t.name
                FROM taxonomy t
                LEFT JOIN taxonomy p on t.parent_id = p.id
                WHERE t.id = ANY(:ids) """,
            {"ids": id_list})
        for rec_taxon in res:
            ret[rec_taxon['id']] = rec_taxon['name']
        return ret

    @staticmethod
    def children_of(session: Session, id_list: List[int]) -> Set[int]:
        """
            Get id and children taxa ids for given id.
        """
        res: ResultProxy = session.execute(
            """WITH RECURSIVE rq(id) 
                AS (SELECT id 
                      FROM taxonomy 
                     WHERE id = ANY(:ids)
                     UNION
                    SELECT t.id 
                      FROM rq 
                      JOIN taxonomy t ON rq.id = t.parent_id )
               SELECT id FROM rq """,
            {"ids": id_list})
        return {int(r['id']) for r in res}
