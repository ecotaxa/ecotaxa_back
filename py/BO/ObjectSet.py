# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#

#
# A set of Object as seen by the user, e.g. on classification page.
#
# The set comprises all objects from a Project, except the ones filtered by a set of criteria.
#
from typing import Tuple

from sqlalchemy.orm import Session

from BO.Taxonomy import TaxonomyBO
from DB.helpers.SQL import WhereClause, SQLParamDict


class ObjectSet(object):
    """
        A (potentially large) set of objects.
    """

    def __init__(self, session: Session, prj_id: int, filters: dict):
        self.prj_id = prj_id
        self.filters = ObjectSetFilter(session, filters)

    def get_sql(self, user_id: int) -> Tuple[WhereClause, SQLParamDict]:
        """
            Construct SQL parts for getting the IDs of objects.
            :return:
        """
        where = WhereClause()
        where *= " o.projid = :projid "
        params: SQLParamDict = {"projid": self.prj_id}
        self.filters.get_sql_filter(where, params, user_id)
        return where, params


class ObjectSetFilter(object):
    """
        A filter for reducing an object set.
    """

    def __init__(self, session: Session, filters: dict):
        """
            Init from a dictionary with all fields.
        """
        self.session = session
        # Now to the filters
        self.taxo: str = filters.get("taxo", "")
        self.taxo_child: bool = filters.get("taxochild", "") == "Y"
        self.statusfilter: str = filters.get("statusfilter", "")
        self.MapN: str = filters.get("MapN", '')
        self.MapW: str = filters.get("MapW", '')
        self.MapE: str = filters.get("MapE", '')
        self.MapS: str = filters.get("MapS", '')
        self.depth_min: str = filters.get("depthmin", '')
        self.depth_max: str = filters.get("depthmax", '')
        # A coma-separated list of numerical sample ids
        self.samples: str = filters.get("samples", '')
        self.instrument: str = filters.get("instrum", '')
        # A coma-separated list of sunpos values
        #  D for Day, U for Dusk, N for Night, A for Dawn (Aube in French)
        self.daytime: str = filters.get("daytime", "")
        # A coma-separated list of month numbers
        self.months: str = filters.get("month", "")
        self.from_date: str = filters.get("fromdate", '')
        self.to_date: str = filters.get("todate", '')
        # Time (in day) filters
        self.from_time: str = filters.get("fromtime", '')
        self.to_time: str = filters.get("totime", '')
        self.invert_time: bool = filters.get("inverttime", '') == "1"
        # Validation date filters
        self.validated_from: str = filters.get("validfromdate", '')
        self.validated_to: str = filters.get("validtodate", '')
        # Free fields AKA features filtering
        self.free_num: str = filters.get("freenum", '')
        self.free_num_start: str = filters.get("freenumst", '')
        self.free_num_end: str = filters.get("freenumend", '')
        # Free text filtering
        self.free_text: str = filters.get("freetxt", '')
        self.free_text_val: str = filters.get("freetxtval", "")
        # A coma-separated list of numerical user ids
        self.annotators: str = filters.get('filt_annot', '')

    def get_sql_filter(self, where_clause: WhereClause,
                       params: SQLParamDict, user_id: int) -> None:
        """
        :param where_clause:
        :param params:
        :param user_id: For filtering validators.
        :return:
        """

        if self.taxo:
            if self.taxo_child:
                where_clause *= " o.classif_id = any (:taxo) "
                # TODO: Cache if used
                params['taxo'] = list(TaxonomyBO.children_of(self.session, [int(self.taxo)]))
            else:
                where_clause *= " o.classif_id = :taxo "
                params['taxo'] = self.taxo

        if self.statusfilter:
            if self.statusfilter == "NV":
                where_clause *= " (o.classif_qual != 'V' or o.classif_qual is null) "
            elif self.statusfilter == "PV":
                where_clause *= " o.classif_qual in ('V','P') "
            elif self.statusfilter == "NVM":
                where_clause *= " o.classif_qual = 'V' "
                where_clause *= " o.classif_who != " + str(user_id) + " "
            elif self.statusfilter == "VM":
                where_clause *= " o.classif_qual= 'V' "
                where_clause *= " o.classif_who = " + str(user_id) + " "
            elif self.statusfilter == "U":
                where_clause *= " o.classif_qual is null "
            else:
                where_clause *= " o.classif_qual = '" + self.statusfilter + "' "

        if self.MapN and self.MapW and self.MapE and self.MapS:
            where_clause *= " o.latitude between :MapS and :MapN "
            where_clause *= " o.longitude between :MapW and :MapE "
            params['MapN'] = self.MapN
            params['MapW'] = self.MapW
            params['MapE'] = self.MapE
            params['MapS'] = self.MapS

        if self.depth_min and self.depth_max:
            where_clause *= " o.depth_min between :depthmin and :depthmax "
            where_clause *= " o.depth_max between :depthmin and :depthmax "
            params['depthmin'] = self.depth_min
            params['depthmax'] = self.depth_max

        if self.samples:
            where_clause *= " o.sampleid = any (:samples) "
            params['samples'] = [int(x) for x in self.samples.split(',')]

        if self.instrument:
            where_clause *= " o.acquisid in (select acquisid " \
                            "                  from acquisitions " \
                            "                 where instrument ilike :instrum " \
                            "                   and projid = :projid ) "
            params['instrum'] = '%' + self.instrument + '%'

        if self.daytime:
            where_clause *= " o.sunpos = any (:daytime) "
            params['daytime'] = [x for x in self.daytime.split(',')]

        if self.months:
            where_clause *= " extract(month from o.objdate) = any (:month) "
            params['month'] = [int(x) for x in self.months.split(',')]

        if self.from_date:
            where_clause *= " o.objdate >= to_date(:fromdate,'YYYY-MM-DD') "
            params['fromdate'] = self.from_date

        if self.to_date:
            where_clause *= " o.objdate <= to_date(:todate,'YYYY-MM-DD') "
            params['todate'] = self.to_date

        if self.invert_time:
            if self.from_time and self.to_time:
                where_clause *= " (o.objtime <= time :fromtime or o.objtime >= time :totime) "
                params['fromtime'] = self.from_time
                params['totime'] = self.to_time
        else:
            if self.from_time:
                where_clause *= " o.objtime >= time :fromtime "
                params['fromtime'] = self.from_time
            if self.to_time:
                where_clause *= " o.objtime <= time :totime "
                params['totime'] = self.to_time

        if self.validated_from:
            where_clause *= " o.classif_when >= to_timestamp(:validfromdate,'YYYY-MM-DD HH24:MI') "
            params['validfromdate'] = self.validated_from

        if self.validated_to:
            where_clause *= " o.classif_when <= to_timestamp(:validtodate,'YYYY-MM-DD HH24:MI') "
            params['validtodate'] = self.validated_to

        if self.free_num and self.free_num_start:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= " o." + criteria_col + " >= :freenumst "
            params['freenumst'] = self.free_num_start

        if self.free_num and self.free_num_end:
            criteria_col = "n%02d" % int(self.free_num[2:])
            where_clause *= " o." + criteria_col + " <= :freenumend "
            params['freenumend'] = self.free_num_end

        if self.free_text and self.free_text_val:
            criteria_tbl = self.free_text[0]
            criteria_col = "t%02d" % int(self.free_text[2:])
            if criteria_tbl == 'o':
                where_clause *= " o." + criteria_col + " ilike :freetxtval "
            elif criteria_tbl == 'a':
                where_clause *= " o.acquisid in (select acquisid from acquisitions s " \
                                "                 where " + criteria_col + " ilike :freetxtval " + \
                                "                   and projid = :projid ) "
            elif criteria_tbl == 's':
                where_clause *= " o.sampleid in (select sampleid from samples s " \
                                "                 where " + criteria_col + " ilike :freetxtval " + \
                                "                   and projid = :projid ) "
            elif criteria_tbl == 'p':
                where_clause *= " o.processid in (select processid from process s " \
                                "                  where " + criteria_col + " ilike :freetxtval " + \
                                "                    and projid = :projid ) "
            params['freetxtval'] = '%' + self.free_text_val + '%'

        if self.annotators:
            where_clause *= " (o.classif_who = any (:filt_annot) " \
                            "  or exists (select classif_who " \
                            "               from objectsclassifhisto oh " \
                            "              where oh.objid = o.objid " \
                            "                and classif_who = any (:filt_annot) ) ) "
            params['filt_annot'] = [int(x) for x in self.annotators.split(',')]
