# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# After SQL alchemy models are defined individually, setup the relations b/w them
#
from typing import List, Set, Dict, Tuple

from BO.Classification import ClassifIDCollT, ClassifIDT, ClassifIDListT
from DB import ResultProxy, Taxonomy
from DB.helpers.ORM import Session, any_, case, func, text, select
from helpers.DynamicLogs import get_logger

ClassifSetInfoT = Dict[ClassifIDT, Tuple[str, str]]

logger = get_logger(__name__)


class TaxonBO(object):
    """
        Holder fo a leaf of the tree.
    """

    def __init__(self, taxon_id: ClassifIDT, display_name: str, lineage: List[str]):
        self.id = taxon_id
        self.display_name = display_name
        self.lineage = lineage


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
    def names_for(session: Session, id_list: List[int]) -> Dict[int, str]:
        """
            Get taxa names from id list.
        """
        ret = {}
        res: ResultProxy = session.execute(
            """SELECT t.id, t.name
                 FROM taxonomy t
                WHERE t.id = ANY(:ids) """,
            {"ids": id_list})
        for rec_taxon in res:
            ret[rec_taxon['id']] = rec_taxon['name']
        return ret

    @staticmethod
    def names_with_parent_for(session: Session, id_coll: ClassifIDCollT) -> ClassifSetInfoT:
        """
            Get taxa names from id list.
        """
        ret = {}
        res: ResultProxy = session.execute(
            """SELECT t.id, t.name, p.name AS parent_name
                 FROM taxonomy t
                LEFT JOIN taxonomy p ON t.parent_id = p.id
                WHERE t.id = ANY(:ids) """,
            {"ids": list(id_coll)})
        for rec_taxon in res:
            ret[rec_taxon['id']] = (rec_taxon['name'], rec_taxon['parent_name'])
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

    @staticmethod
    def parents_of(session: Session, taxon_id: int) -> List[Tuple[int, str]]:
        """
            Get id parent taxa (id+name) for given id.
        """
        res: ResultProxy = session.execute(
            """WITH RECURSIVE rq(id) 
                AS (SELECT id, parent_id, name
                      FROM taxonomy 
                     WHERE id = :tid
                     UNION
                    SELECT t.id, t.parent_id, t.name
                      FROM rq 
                      JOIN taxonomy t ON t.id = rq.parent_id )
               SELECT id, name FROM rq """,
            {"tid": taxon_id})
        return [(r['id'], r['name']) for r in res]

    MAX_MATCHES = 200
    MAX_TAXONOMY_LEVELS = 15

    @classmethod
    def query(cls, session: Session,
              restrict_to: ClassifIDListT, priority_set: ClassifIDListT,
              display_name_filter: str, name_filters: List[str]):
        """
        :param session:
        :param restrict_to: If not None, limit the query to given IDs.
        :param priority_set: Regardless of MAX_MATCHES, these IDs must appear in the result if they match.
        :param display_name_filter:
        :param name_filters:
        :return:
        """
        tf = Taxonomy.__table__.alias('tf')
        # bind = None  # For portable SQL, no 'ilike'
        bind = session.get_bind()
        # noinspection PyTypeChecker
        priority = case([(tf.c.id == any_(priority_set), text('0'))], else_=text('1')).label('prio')
        qry = select([tf.c.id, tf.c.display_name, priority], bind=bind)
        if len(name_filters) > 0:
            # Inject a query on names and hierarchy
            # Produced SQL looks like:
            #       left join taxonomy t1 on tf.parent_id=t1.id
            #       left join taxonomy t2 on t1.parent_id=t2.id
            # ...
            #       left join taxonomy t14 on t13.parent_id=t14.id
            lineage_sep = text("'<'")
            lev_alias = Taxonomy.__table__.alias('t1')
            # Chain outer joins on Taxonomy
            # hook the first OJ to main select
            chained_joins = tf.join(lev_alias, lev_alias.c.id == tf.c.parent_id, isouter=True)
            concat_all = [tf.c.name, lineage_sep, lev_alias.c.name]
            prev_alias = lev_alias
            for level in range(2, cls.MAX_TAXONOMY_LEVELS):
                lev_alias = Taxonomy.__table__.alias('t%d' % level)
                # hook each following OJ to previous one
                chained_joins = chained_joins.join(lev_alias, lev_alias.c.id == prev_alias.c.parent_id, isouter=True)
                # Collect expressions
                concat_all.extend([lineage_sep, lev_alias.c.name])
                prev_alias = lev_alias
            qry = qry.select_from(chained_joins)
            # Below is quite expensive
            taxo_lineage = func.concat(*concat_all)
            name_filter = "%<" + "".join(name_filters)  # i.e. anywhere consecutively in the lineage
            qry = qry.where(taxo_lineage.ilike(name_filter))
        if restrict_to is not None:
            qry = qry.where(tf.c.id == any_(restrict_to))
        # We have index IS_TaxonomyDispNameLow so this lower() is for free
        qry = qry.where(func.lower(tf.c.display_name).like(display_name_filter))
        qry = qry.order_by(priority, func.lower(tf.c.display_name))
        qry = qry.limit(cls.MAX_MATCHES)
        logger.info("Taxo query: %s with params %s and %s ", qry, display_name_filter, name_filters)
        res: ResultProxy = session.execute(qry)
        return res.fetchall()


class TaxonBOSet(object):
    """
        Many taxa.
    """

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        tf = Taxonomy.__table__.alias('tf')
        # bind = None  # For portable SQL, no 'ilike'
        bind = session.get_bind()
        select_list = [tf.c.id, tf.c.display_name, tf.c.name]
        select_list.extend([text("t%d.name" % level)  # type:ignore
                            for level in range(1, TaxonomyBO.MAX_TAXONOMY_LEVELS)])
        qry = select(select_list, bind=bind)
        # Inject a query on names and hierarchy
        # Produced SQL looks like:
        #       left join taxonomy t1 on tf.parent_id=t1.id
        #       left join taxonomy t2 on t1.parent_id=t2.id
        # ...
        #       left join taxonomy t14 on t13.parent_id=t14.id
        lev_alias = Taxonomy.__table__.alias('t1')
        # Chain outer joins on Taxonomy, for parents
        # hook the first OJ to main select
        chained_joins = tf.join(lev_alias, lev_alias.c.id == tf.c.parent_id, isouter=True)
        prev_alias = lev_alias
        for level in range(2, TaxonomyBO.MAX_TAXONOMY_LEVELS):
            lev_alias = Taxonomy.__table__.alias('t%d' % level)
            # hook each following OJ to previous one
            chained_joins = chained_joins.join(lev_alias, lev_alias.c.id == prev_alias.c.parent_id, isouter=True)
            # Collect expressions
            prev_alias = lev_alias
        qry = qry.select_from(chained_joins)
        qry = qry.where(tf.c.id == any_(taxon_ids))
        logger.info("Taxo query: %s with IDs %s", qry, taxon_ids)
        res: ResultProxy = session.execute(qry)
        self.taxa = []
        for a_rec in res.fetchall():
            lst_rec = list(a_rec)
            an_id, display_name = lst_rec.pop(0), lst_rec.pop(0)
            lineage = [name for name in lst_rec if name]
            self.taxa.append(TaxonBO(an_id, display_name, lineage))  # type:ignore

    def as_list(self) -> List[TaxonBO]:
        return self.taxa
