# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Taxon/Category/Classification
#
from datetime import datetime
from typing import List, Set, Dict, Tuple, Optional, Final, Any

from BO.Classification import ClassifIDCollT, ClassifIDT, ClassifIDListT
from DB.Project import ProjectTaxoStat
from DB.Taxonomy import (
    TaxonomyTreeInfo,
    Taxonomy,
    TaxoType,
    TaxoStatus,
)
from DB.helpers import Result
from DB.helpers.ORM import Session, any_, case, func, text, select, Label
from helpers import DateTime
from helpers.DynamicLogs import get_logger
from helpers.Timer import CodeTimer

# import logging

# logging.basicConfig()
# logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

ClassifSetInfoT = Dict[ClassifIDT, Tuple[str, str]]

logger = get_logger(__name__)


class TaxonBO(object):
    """
    Holder of a node of a taxonomy tree. Used for Unieuk tree and for WoRMS one.
    """

    __slots__ = [
        "id",
        "name",
        "type",
        "status",
        "display_name",
        "lineage",
        "id_lineage",
        "lineage_status",
        "renm_id",
        "nb_objects",
        "nb_children_objects",
        "aphia_id",
        "rank",
        "children",
    ]

    def __init__(
        self,
        cat_type: str,
        cat_status: str,
        display_name: str,
        nb_objects: int,
        nb_children_objects: int,
        lineage: List[str],
        id_lineage: List[ClassifIDT],
        lineage_status: str,
        aphia_id: Optional[int] = None,
        rank: Optional[str] = None,
        children: Optional[List[ClassifIDT]] = None,
        rename_id: Optional[int] = None,
    ):
        assert cat_type in TaxoType.list()
        self.type = cat_type
        assert cat_status in TaxoStatus.list()
        self.status = cat_status
        if children is None:
            children = []
        else:
            assert isinstance(children, list), "Not a list: %s" % children
        self.id: int = id_lineage[0]
        self.renm_id = rename_id
        self.name = lineage[0]
        self.nb_objects: int = nb_objects if nb_objects is not None else 0
        self.nb_children_objects = (
            nb_children_objects if nb_children_objects is not None else 0
        )
        self.display_name = display_name
        self.lineage = lineage
        self.id_lineage = id_lineage
        self.lineage_status = lineage_status
        self.aphia_id = aphia_id
        self.rank = rank
        self.children = children

    def top_down_lineage(self, sep: str = ">"):
        return sep.join(reversed(self.lineage))

    def __repr__(self):
        return f"{self.__class__.__name__}({self.id}: {self.display_name})"


class TaxonomyBO(object):
    """
    Holder for methods on taxonomy tree.
    """

    @staticmethod
    def find_ids(session: Session, classif_id_seen: List):
        """
        Return input IDs for the existing ones.
        """
        sql = text("SELECT id " "  FROM taxonomy " " WHERE id = ANY (:een)")
        res: Result = session.execute(sql, {"een": list(classif_id_seen)})
        return {an_id for an_id, in res}

    @staticmethod
    def keep_phylo(session: Session, classif_id_seen: ClassifIDListT):
        """
        Return input IDs, for the existing ones with 'P' type.
        """
        sql = text(
            "SELECT id " "  FROM taxonomy " " WHERE id = ANY (:een) AND taxotype = 'P'"
        )
        res: Result = session.execute(sql, {"een": list(classif_id_seen)})
        return {an_id for an_id, in res}

    @staticmethod
    def resolve_taxa(
        session: Session, taxo_lookup: Dict[str, Dict[str, Any]], taxon_lower_list
    ):
        """
        Match taxa in taxon_lower_list and return the matched ones in taxo_found.
        """
        sql = text(
            """SELECT t.id, lower(t.name) AS name, lower(t.display_name) AS display_name, 
                      lower(t.name)||'<'||lower(p.name) AS computedchevronname 
                 FROM taxonomy t
                LEFT JOIN taxonomy p on t.parent_id = p.id
                WHERE lower(t.name) = ANY(:nms) OR lower(t.display_name) = ANY(:dms) 
                    OR lower(t.name)||'<'||lower(p.name) = ANY(:chv) """
        )
        res: Result = session.execute(
            sql,
            {"nms": taxon_lower_list, "dms": taxon_lower_list, "chv": taxon_lower_list},
        )
        for rec_taxon in res.mappings():
            for found_k, found_v in taxo_lookup.items():
                if (
                    (found_k == rec_taxon["name"])
                    or (found_k == rec_taxon["display_name"])
                    or (found_k == rec_taxon["computedchevronname"])
                    or (
                        ("alterdisplayname" in found_v)
                        and (found_v["alterdisplayname"] == rec_taxon["display_name"])
                    )
                ):
                    taxo_lookup[found_k]["nbr"] += 1
                    taxo_lookup[found_k]["id"] = rec_taxon["id"]

    @staticmethod
    def names_with_parent_for(
        session: Session, id_coll: ClassifIDCollT
    ) -> ClassifSetInfoT:
        """
        Get taxa names from id list.
        """
        ret = {}
        sql = text(
            """SELECT t.id, t.name, p.name AS parent_name
                 FROM taxonomy t
                LEFT JOIN taxonomy p ON t.parent_id = p.id
                WHERE t.id = ANY(:ids) """
        )
        res: Result = session.execute(sql, {"ids": list(id_coll)})
        for rec_taxon in res.mappings():
            ret[rec_taxon["id"]] = (rec_taxon["name"], rec_taxon["parent_name"])
        return ret

    RQ_CHILDREN: Final = """WITH RECURSIVE rq(id) 
                    AS (SELECT id 
                          FROM taxonomy 
                         WHERE id = ANY(:ids)
                         UNION
                        SELECT t.id 
                          FROM rq 
                          JOIN taxonomy t ON rq.id = t.parent_id )
                   SELECT id FROM rq """

    @staticmethod
    def children_of(session: Session, id_list: List[int]) -> Set[int]:
        """
        Get id and children taxa ids for given ids.
        """
        sql = text(TaxonomyBO.RQ_CHILDREN)
        res: Result = session.execute(sql, {"ids": id_list})
        return {int(r["id"]) for r in res.mappings()}

    @staticmethod
    def parents_sql(ref_obj_id: str) -> str:
        """
        SQL for recursive '>'-separated names of parents.
        """
        sql = """(WITH RECURSIVE rq(id, name, parent_id) 
                   AS (SELECT id, name, parent_id, 1 AS rrank 
                         FROM taxonomy 
                        WHERE id = {0}
                       UNION
                       SELECT txpr.id, txpr.name, txpr.parent_id, rrank+1 AS rrank 
                         FROM rq 
                         JOIN taxonomy txpr ON txpr.id = rq.parent_id)
                    SELECT string_agg(name,'>') 
                      FROM (SELECT name 
                              FROM rq 
                          ORDER BY rrank desc) q)""".format(
            ref_obj_id
        )
        return sql

    @staticmethod
    def lineage_cte() -> str:
        """
        SQL for (again) recursive '>'-separated names of parents, but as a CTE
        so no constraint on providing a specific ID.
        TODO: Use instead of previous one.
        """
        sql = """(WITH RECURSIVE rq(leaf_id, lineage, root_id, parent_id) 
                 AS (SELECT id, name||'', id, parent_id
                      FROM taxonomy
                     UNION
                    SELECT rq.leaf_id , txpr.name||'>'||rq.lineage, txpr.id, txpr.parent_id
                      FROM rq 
                      JOIN taxonomy txpr ON txpr.id = rq.parent_id)
                SELECT * FROM rq WHERE parent_id IS NULL)"""
        return sql

    MAX_MATCHES: Final = 200
    MAX_TAXONOMY_LEVELS: Final = 20

    @classmethod
    def query(
        cls,
        session: Session,
        restrict_to: ClassifIDListT,
        priority_set: ClassifIDListT,
        display_name_filter: str,
        name_filters: List[str],
    ):
        """
        :param session:
        :param restrict_to: If not None, limit the query to given IDs.
        :param priority_set: Regardless of MAX_MATCHES, these IDs must appear in the result if they match.
        :param display_name_filter:
        :param name_filters:
        :return:
        """
        tf = Taxonomy.__table__.alias("tf")
        # bind = None  # For portable SQL, no 'ilike'
        bind = session.get_bind()
        priority: Label = case(
            [(tf.c.id == any_(priority_set), text("0"))], else_=text("1")
        ).label("prio")
        qry = select(
            [
                tf.c.taxotype,
                tf.c.id,
                tf.c.aphia_id,
                tf.c.rename_to,
                tf.c.display_name,
                tf.c.taxostatus,
                priority,
            ],
            bind=bind,
        )
        if len(name_filters) > 0:
            # Add to the query enough to get the full hierarchy for filtering
            concat_all, qry = cls._add_recursive_query(qry, tf, do_concat=True)
            # Below is quite expensive
            taxo_lineage = func.concat(*concat_all)
            name_filter = "%<" + "".join(
                name_filters
            )  # i.e. anywhere consecutively in the lineage
            qry = qry.where(taxo_lineage.ilike(name_filter))
        if restrict_to is not None:
            qry = qry.where(tf.c.id == any_(restrict_to))
        # We have index IS_TaxonomyDispNameLow so this lower() is for free
        qry = qry.where(func.lower(tf.c.display_name).like(display_name_filter))
        qry = qry.order_by(priority, func.lower(tf.c.display_name))
        qry = qry.limit(cls.MAX_MATCHES)
        logger.info(
            "Taxo query: %s with params %s and %s ",
            qry,
            display_name_filter,
            name_filters,
        )

        res: Result = session.execute(qry)
        return res.fetchall()

    @classmethod
    def _add_recursive_query(cls, qry, tf, do_concat):
        # Build a query on names and hierarchy
        # Produced SQL looks like:
        #       left join taxonomy t1 on tf.parent_id=t1.id
        #       left join taxonomy t2 on t1.parent_id=t2.id
        # ...
        #       left join taxonomy t14 on t13.parent_id=t14.id
        lev_alias = Taxonomy.__table__.alias("t1")
        # Evntually, also build a concat to get e.g. a < b < c < d string
        if do_concat:
            lineage_sep = text("'<'")
            concat_all = [tf.c.name, lineage_sep, lev_alias.c.name]
        else:
            lineage_sep = None
            concat_all = None
        # Chain outer joins on Taxonomy
        # hook the first OJ to main select
        chained_joins = tf.join(
            lev_alias, lev_alias.c.id == tf.c.parent_id, isouter=True
        )
        prev_alias = lev_alias
        for level in range(2, cls.MAX_TAXONOMY_LEVELS):
            lev_alias = Taxonomy.__table__.alias("t%d" % level)
            # hook each following OJ to previous one
            chained_joins = chained_joins.join(
                lev_alias, lev_alias.c.id == prev_alias.c.parent_id, isouter=True
            )
            if concat_all:
                # Collect expressions
                concat_all.extend([lineage_sep, lev_alias.c.name])
            prev_alias = lev_alias
        qry = qry.select_from(chained_joins)
        return concat_all, qry

    @classmethod
    def compute_stats(cls, session: Session):
        """
        Update fields nbrobj and nbrobjcum with usage statistics
        nbrobj is the number of validated objects in the category, nbrobjcum is the sum
        of nbrobj for all children recursively.
        """
        sql = text(
            """
        -- Reset all
        UPDATE taxonomy 
           SET nbrobj=0, nbrobjcum=NULL 
         WHERE nbrobj IS NULL or nbrobj != 0 or nbrobjcum IS NOT NULL;
        -- Set per-category number
        WITH tsp as (SELECT id AS classif_id, sum(nbr_v) AS nbr
                       FROM projects_taxo_stat pts
                     -- historical: JOIN projects prj ON pts.projid=prj.projid AND prj.visible=true
                      WHERE nbr_v>0 GROUP BY id)
        UPDATE taxonomy
           SET nbrobj=tsp.nbr
          FROM tsp
         WHERE taxonomy.id = tsp.classif_id;
        -- Set cumulated number, i.e. sum of numbers under a given node
        WITH cml AS (WITH RECURSIVE rq(id, nbrobj, parent_id) 
                     AS (SELECT id, nbrobj, parent_id, id as root
                           FROM taxonomy
                          UNION
                         SELECT txpr.id, txpr.nbrobj, txpr.parent_id, rq.root
                           FROM rq 
                           JOIN taxonomy txpr ON txpr.parent_id = rq.id)
                     SELECT root AS classif_id, sum(nbrobj) as nbr
                       FROM rq
                      GROUP BY root)
        UPDATE taxonomy
           SET nbrobjcum=cml.nbr
          FROM cml
         WHERE taxonomy.id = cml.classif_id;"""
        )
        session.execute(sql)

    @staticmethod
    def get_full_stats(session: Session) -> Dict[ClassifIDT, int]:
        # Get usage statistics for all taxa, as a dict category_id -> number
        qry = session.query(ProjectTaxoStat.id, func.sum(ProjectTaxoStat.nbr))
        qry = qry.group_by(ProjectTaxoStat.id)
        ret = {an_id: a_sum for an_id, a_sum in qry}
        return ret

    @staticmethod
    def get_tree_status(session: Session) -> TaxonomyTreeInfo:
        """
        Return, creating it if needed, the DB line with status of the taxonomy tree.
        """
        tree_info = session.query(TaxonomyTreeInfo).one_or_none()
        if tree_info is None:
            # No DB line at all, create it. We need exactly one.
            tree_info = TaxonomyTreeInfo()
            tree_info.id = 1
            session.add(tree_info)
            session.commit()
        return tree_info

    @staticmethod
    def update_tree_status(session: Session):
        """
        Update the DB line with status of the taxonomy tree.
        """
        TaxonomyBO.get_tree_status(session).lastserverversioncheck_datetime = (
            DateTime.now_time()
        )
        session.commit()

    @staticmethod
    def get_latest_update(session: Session) -> Optional[datetime]:
        """
        Get the date/time at which a taxon was latest updated.
        """
        max_upd_qry = session.query(func.max(Taxonomy.lastupdate_datetime))
        (max_upd,) = max_upd_qry.one()
        return max_upd

    @staticmethod
    def do_renames(session: Session, to_rename: Dict[ClassifIDT, ClassifIDT]):
        """
        Do renames (i.e. remaps) from one classification to another.

        Just a copy/paste/comment out of the historical code.
        The semantic of "renaming" is quite unclear, for example it could be mandatory to
        deprecate a taxon before renaming (or at the same time).

        """
        # SELECT * FROM (VALUES (1, 2), (3, 4)) AS q (col1, col2)
        # sqlbase = "with taxorename as (select id, rename_to from taxonomy where rename_to is not null) "
        # sql = sqlbase + """select distinct obj.projid from objects obj join taxorename tr on obj.classif_id=tr.id """
        # ProjetsToRecalc = database.GetAll(sql)
        #
        # sql = sqlbase + """update obj_head obh set classif_id=tr.rename_to
        #       from taxorename tr  where obh.classif_id=tr.id """
        # NbrRenamedObjects = ExecSQL(sql)
        # sql = sqlbase + """update obj_head obh set classif_auto_id=tr.rename_to
        #       from taxorename tr  where obh.classif_auto_id=tr.id """
        # ExecSQL(sql)
        # sql = sqlbase + """update objectsclassifhisto och set classif_id=tr.rename_to
        #       from taxorename tr  where och.classif_id=tr.id """
        # ExecSQL(sql)
        # # on efface les taxon qui doivent être renommés car ils l'ont normalement été
        # #sql = """delete from taxonomy where rename_to is not null """
        # #ExecSQL(sql)
        # sql = """delete from taxonomy t where taxostatus='D'
        #           and not exists(select 1 from projects_taxo_stat where id=t.id) """
        # ExecSQL(sql)
        # # il faut recalculer projects_taxo_stat et part_histocat,part_histocat_lst pour ceux qui referencaient un
        # # taxon renomé et donc disparu
        # if NbrRenamedObjects > 0:
        #     # cron.RefreshTaxoStat() operation trés longue (env 5 minutes en prod, il faut être plus selectif)
        #     # permet de recalculer projects_taxo_stat
        #     for Projet in ProjetsToRecalc:
        #         RecalcProjectTaxoStat(Projet['projid'])
        #     # recalcul part_histocat,part_histocat_lst

        #     !!!! ECOPART LINK !!!!
        #     appli.part.prj.GlobalTaxoCompute()

    @classmethod
    def do_deletes(cls, session: Session, to_delete: List[ClassifIDT]) -> None:
        #### Direct Foreign Keys to `taxonomy.id`
        # 1.  **`obj_head.classif_id`**: Points to `taxonomy.id`. This represents the current classification of an object.
        # 2.  **`objectsclassifhisto.classif_id`**: Points to `taxonomy.id` (with `ondelete="CASCADE"`). This stores the history of classifications for an object.
        # 3.  **`taxo_change_log.to_id`**: Points to `taxonomy.id` (with `ondelete="CASCADE"`). This logs the target taxon in a mass classification change.
        # 4.  **`taxo_change_log.from_id`**: Points to `taxonomy.id` (with `ondelete="CASCADE"`). This logs the original taxon in a mass classification change.
        # 5.  **`prediction.classif_id`**: Points to `taxonomy.id` (with `ondelete="CASCADE"`). This stores the predicted taxon for an object.
        # 6.  **`prediction_histo.classif_id`**: Points to `taxonomy.id` (with `ondelete="CASCADE"`). This stores the history of predicted taxa.
        #### Other Implicit Relations
        # *   **`taxonomy.parent_id`**: Although not explicitly defined with a `ForeignKey` constraint in the SQLAlchemy model (it is a simple `INTEGER` column), it logically points to `taxonomy.id` to represent the taxonomic tree structure.
        # *   **`taxonomy.rename_to`**: Similarly, this `INTEGER` column is used to store an "advised" target taxon for mass category changes, logically referring to another `taxonomy.id`.
        # *   **`taxo_recast.transforms`**: This `JSONB` column stores mapping in the form `{from:to}`, where both values are taxonomic IDs, though they are not enforced by database-level foreign key constraints.
        sql = text("SELECT DISTINCT id FROM taxonomy")
        res: Result = session.execute(sql, {"een": list(to_delete)})
        present = {an_id for an_id, in res}
        final_delete = sorted(list(present.intersection(to_delete)))
        # We want to protect 1. and 2.
        sql = text("SELECT DISTINCT objid FROM obj_head WHERE classif_id = ANY (:een)")
        res2: Result = session.execute(sql, {"een": list(final_delete)})
        prevent_obj_head = {an_id for an_id, in res2}
        if len(prevent_obj_head) > 0:
            logger.error("Unsafe deletion due to objects %s", prevent_obj_head)
        sql = text(
            "SELECT DISTINCT objid FROM objectsclassifhisto WHERE classif_id = ANY (:een)"
        )
        res3: Result = session.execute(sql, {"een": list(final_delete)})
        prevent_obj_histo = {an_id for an_id, in res3}
        if len(prevent_obj_histo) > 0:
            logger.error("Unsafe deletion due to objects history %s", prevent_obj_histo)
        # assert len(prevent_obj_head) == 0 and len(prevent_obj_histo) == 0, "Cannot achieve safe deletion"
        logger.info("deleting categories")
        session.execute(text("alter table taxonomy disable trigger all"))
        for i in range(0, len(final_delete), 20):
            logger.info("Taxo delete, list: %s", final_delete[i : i + 20])
        try:
            for a_taxon in final_delete:
                taxon = session.query(Taxonomy).get(a_taxon)
                session.delete(taxon)
        finally:
            session.execute(text("alter table taxonomy enable trigger all"))


class TaxonBOSet(object):
    """
    Many taxa.
    """

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        tf = Taxonomy.__table__.alias("tf")
        # bind = None  # For portable SQL, no 'ilike'
        bind = session.get_bind()
        select_list = [
            tf.c.nbrobj,
            tf.c.nbrobjcum,
            tf.c.display_name,
            tf.c.id,
            tf.c.name,
            tf.c.aphia_id,
            tf.c.taxotype,
            tf.c.taxostatus,
            tf.c.rank,
            tf.c.rename_to,
        ]
        select_list.extend(
            [
                text(
                    "t%d.id, t%d.name, t%d.aphia_id, t%d.taxotype, t%d.taxostatus, t%d.rank, t%d.rename_to"
                    % (level, level, level, level, level, level, level)
                )  # type:ignore
                for level in range(1, TaxonomyBO.MAX_TAXONOMY_LEVELS)
            ]
        )
        qry = select(select_list, bind=bind)

        # Inject the recursive query, for getting parents
        _dumm, qry = TaxonomyBO._add_recursive_query(qry, tf, do_concat=False)
        qry = qry.where(tf.c.id == any_(taxon_ids))
        # Add another join for getting children
        logger.info("TaxonBOSet query: %s with IDs %s", qry, taxon_ids)
        with CodeTimer("TaxonBOSet query for %d IDs: " % len(taxon_ids), logger):
            res: Result = session.execute(qry)
        self.taxa: List[TaxonBO] = []
        for a_rec in res.fetchall():
            lst_rec = list(a_rec)
            (
                nbobj1,
                nbobj2,
                display_name,
            ) = (
                lst_rec.pop(0),
                lst_rec.pop(0),
                lst_rec.pop(0),
            )
            aphia_id: Optional[int] = lst_rec[2]
            cat_type = lst_rec[3]
            cat_status = lst_rec[4]
            rank: Optional[str] = lst_rec[5]
            rename_id = lst_rec[6]
            numf = 7  # Number of fields in a block, i.e. a taxon
            # Loop over self + parents to get ancestors' fields. Not the clearest code in the world.
            lineage_id = [an_id for an_id in lst_rec[0::numf] if an_id is not None]
            lineage_status = "".join(
                [a_status for a_status in lst_rec[4::numf] if a_status is not None]
            )
            lineage = [name for name in lst_rec[1::numf] if name is not None]
            # assert lineage_id[-1] in (1, 84960, 84959), "Unexpected root %s" % str(lineage_id[-1])
            taxon_bo = TaxonBO(
                cat_type,
                cat_status,
                display_name,
                nbobj1,
                nbobj2,  # type:ignore
                lineage,
                lineage_id,  # type:ignore
                lineage_status,
                rename_id=rename_id,
                aphia_id=aphia_id,
                rank=rank,
            )
            self.taxa.append(taxon_bo)
        self.bos_per_id = {a_bo.id: a_bo for a_bo in self.taxa}
        self.get_children(session)
        self.get_cardinalities(session)

    def get_children(self, session: Session) -> None:
        # Enrich TaxonBOs with children
        tch = Taxonomy.__table__.alias("tch")
        qry = session.query(Taxonomy.id, tch.c.id)
        qry = qry.join(tch, tch.c.parent_id == Taxonomy.id)
        qry = qry.filter(Taxonomy.id == any_(list(self.bos_per_id.keys())))
        for an_id, a_child_id in qry:
            self.bos_per_id[an_id].children.append(a_child_id)

    def get_cardinalities(self, session: Session):
        # Enrich TaxonBOs with number of objects. Due to ecotaxa/ecotaxa_dev#648, pick data from projects stats.
        qry = session.query(ProjectTaxoStat.id, func.sum(ProjectTaxoStat.nbr_v))
        qry = qry.filter(ProjectTaxoStat.id == any_(list(self.bos_per_id.keys())))
        qry = qry.group_by(ProjectTaxoStat.id)
        for an_id, a_sum in qry:
            self.bos_per_id[an_id].nb_objects = a_sum

    def as_list(self) -> List[TaxonBO]:
        return self.taxa

    def get_by_id(self, taxon_id: ClassifIDT) -> TaxonBO:
        return self.bos_per_id[taxon_id]
