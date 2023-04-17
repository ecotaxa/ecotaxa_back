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
from DB.Taxonomy import TaxonomyTreeInfo, Taxonomy
from DB.WoRMs import WoRMS
from DB.helpers import Result
from DB.helpers.ORM import Session, any_, case, func, text, select, Label
from helpers.DynamicLogs import get_logger

ClassifSetInfoT = Dict[ClassifIDT, Tuple[str, str]]

logger = get_logger(__name__)


class TaxonBO(object):
    """
    Holder of a node of the taxonomy tree.
    """

    __slots__ = [
        "type",
        "id",
        "renm_id",
        "name",
        "nb_objects",
        "nb_children_objects",
        "display_name",
        "lineage",
        "id_lineage",
        "children",
    ]

    def __init__(
            self,
            cat_type: str,
            display_name: str,
            nb_objects: int,
            nb_children_objects: int,
            lineage: List[str],
            id_lineage: List[ClassifIDT],
            children: Optional[List[ClassifIDT]] = None,
            rename_id: Optional[int] = None,
    ):
        assert cat_type in ("P", "M")
        self.type = cat_type
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
        self.children = children

    def top_down_lineage(self, sep: str = ">"):
        return sep.join(reversed(self.lineage))


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
                   AS (SELECT id, name, parent_id, 1 AS rank 
                         FROM taxonomy 
                        WHERE id = {0}
                       UNION
                       SELECT txpr.id, txpr.name, txpr.parent_id, rank+1 AS rank 
                         FROM rq 
                         JOIN taxonomy txpr ON txpr.id = rq.parent_id)
                    SELECT string_agg(name,'>') 
                      FROM (SELECT name 
                              FROM rq 
                          ORDER BY rank desc) q)""".format(
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
            [tf.c.taxotype, tf.c.id, tf.c.rename_to, tf.c.display_name, priority],
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
        TaxonomyBO.get_tree_status(
            session
        ).lastserverversioncheck_datetime = datetime.now()
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


class TaxonBOSet(object):
    """
    Many taxa.
    """

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        tf = Taxonomy.__table__.alias("tf")
        # bind = None  # For portable SQL, no 'ilike'
        bind = session.get_bind()
        select_list = [
            tf.c.taxotype,
            tf.c.nbrobj,
            tf.c.nbrobjcum,
            tf.c.display_name,
            tf.c.rename_to,
            tf.c.id,
            tf.c.name,
        ]
        select_list.extend(
            [
                text("t%d.id, t%d.name" % (level, level))  # type:ignore
                for level in range(1, TaxonomyBO.MAX_TAXONOMY_LEVELS)
            ]
        )
        qry = select(select_list, bind=bind)
        # Inject the recursive query, for getting parents
        _dumm, qry = TaxonomyBO._add_recursive_query(qry, tf, do_concat=False)
        qry = qry.where(tf.c.id == any_(taxon_ids))
        # Add another join for getting children
        logger.info("Taxo query: %s with IDs %s", qry, taxon_ids)
        res: Result = session.execute(qry)
        self.taxa: List[TaxonBO] = []
        for a_rec in res.fetchall():
            lst_rec = list(a_rec)
            cat_type, nbobj1, nbobj2, display_name, rename_id = (
                lst_rec.pop(0),
                lst_rec.pop(0),
                lst_rec.pop(0),
                lst_rec.pop(0),
                lst_rec.pop(0),
            )
            lineage_id = [an_id for an_id in lst_rec[0::2] if an_id]
            lineage = [name for name in lst_rec[1::2] if name]
            # assert lineage_id[-1] in (1, 84960, 84959), "Unexpected root %s" % str(lineage_id[-1])
            self.taxa.append(
                TaxonBO(
                    cat_type,
                    display_name,
                    nbobj1,
                    nbobj2,  # type:ignore
                    lineage,
                    lineage_id,  # type:ignore
                    rename_id=rename_id,
                )
            )
        self.get_children(session)
        self.get_cardinalities(session)

    def get_children(self, session: Session) -> None:
        # Enrich TaxonBOs with children
        bos_per_id = {a_bo.id: a_bo for a_bo in self.taxa}
        tch = Taxonomy.__table__.alias("tch")
        qry = session.query(Taxonomy.id, tch.c.id)
        qry = qry.join(tch, tch.c.parent_id == Taxonomy.id)
        qry = qry.filter(Taxonomy.id == any_(list(bos_per_id.keys())))
        for an_id, a_child_id in qry:
            bos_per_id[an_id].children.append(a_child_id)

    def get_cardinalities(self, session: Session):
        # Enrich TaxonBOs with number of objects. Due to ecotaxa/ecotaxa_dev#648, pick data from projects stats.
        bos_per_id = {a_bo.id: a_bo for a_bo in self.taxa}
        qry = session.query(ProjectTaxoStat.id, func.sum(ProjectTaxoStat.nbr_v))
        qry = qry.filter(ProjectTaxoStat.id == any_(list(bos_per_id.keys())))
        qry = qry.group_by(ProjectTaxoStat.id)
        for an_id, a_sum in qry:
            bos_per_id[an_id].nb_objects = a_sum

    def as_list(self) -> List[TaxonBO]:
        return self.taxa


class TaxonBOSetFromWoRMS(object):
    """
    Many taxa from WoRMS table, with lineage.
    """

    MAX_TAXONOMY_LEVELS: Final = 20

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        tf = WoRMS.__table__.alias("tf")
        # bind = None  # Uncomment for portable SQL, no 'ilike'
        bind = session.get_bind()
        select_list = [tf.c.aphia_id, tf.c.scientificname]
        select_list.extend(
            [
                text("t%d.aphia_id, t%d.scientificname" % (level, level))  # type:ignore
                for level in range(1, TaxonBOSetFromWoRMS.MAX_TAXONOMY_LEVELS)
            ]
        )
        qry = select(select_list, bind=bind)
        # Inject a query on names and hierarchy
        # Produced SQL looks like:
        #       left join worms t1 on tf.parent_name_usage_id=t1.aphia_id
        #       left join worms t2 on t1.parent_name_usage_id=t2.aphia_id
        # ...
        #       left join worms t14 on t13.parent_name_usage_id=t14.aphia_id
        lev_alias = WoRMS.__table__.alias("t1")
        # Chain outer joins on Taxonomy, for parents
        # hook the first OJ to main select
        chained_joins = tf.join(
            lev_alias, lev_alias.c.aphia_id == tf.c.parent_name_usage_id, isouter=True
        )
        prev_alias = lev_alias
        for level in range(2, self.MAX_TAXONOMY_LEVELS):
            lev_alias = WoRMS.__table__.alias("t%d" % level)
            # hook each following OJ to previous one
            chained_joins = chained_joins.join(
                lev_alias,
                lev_alias.c.aphia_id == prev_alias.c.parent_name_usage_id,
                isouter=True,
            )
            # Collect expressions
            prev_alias = lev_alias
        qry = qry.select_from(chained_joins)
        qry = qry.where(tf.c.aphia_id == any_(taxon_ids))
        logger.info("Taxo query: %s with IDs %s", qry, taxon_ids)
        res: Result = session.execute(qry)
        self.taxa = []
        for a_rec in res.fetchall():
            lst_rec = list(a_rec)
            lineage_id = [an_id for an_id in lst_rec[0::2] if an_id]
            lineage = [name for name in lst_rec[1::2] if name]
            biota_pos = lineage.index("Biota") + 1
            lineage = lineage[:biota_pos]
            lineage_id = lineage_id[:biota_pos]
            self.taxa.append(
                TaxonBO("P", lineage[0], 0, 0, lineage, lineage_id)
            )  # type:ignore
        self.get_children(session, self.taxa)

    def get_children(self, session: Session, taxa_list: List[TaxonBO]):
        # Enrich TaxonBOs with children
        bos_per_id = {a_bo.id: a_bo for a_bo in taxa_list}
        tch = WoRMS.__table__.alias("tch")
        qry = session.query(WoRMS.aphia_id, tch.c.aphia_id)
        qry = qry.join(tch, tch.c.parent_name_usage_id == WoRMS.aphia_id)
        qry = qry.filter(WoRMS.aphia_id == any_(list(bos_per_id.keys())))
        for an_id, a_child_id in qry:
            bos_per_id[an_id].children.append(a_child_id)

    def as_list(self) -> List[TaxonBO]:
        return self.taxa


class WoRMSSetFromTaxaSet(object):
    """
    Many taxa from WoRMS table, with lineage.
    """

    def __init__(self, session: Session, taxon_ids: ClassifIDListT):
        # TODO: It's not clean to import a sce from a BO
        from API_operations.TaxoManager import TaxonomyChangeService

        # Do the matching right away, most strict way
        match = TaxonomyChangeService.strict_match(session, taxon_ids)
        # Format result
        self.res = {}
        for taxo, worms in match:
            self.res[taxo.id] = worms
