# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# Dig into a project 'big' data part
#
from collections import OrderedDict
from decimal import Decimal
from typing import List, Dict, Tuple, Union

from API_operations.helpers.Service import Service
from BO.Acquisition import AcquisitionIDT
from BO.Project import ProjectBO
from BO.Rights import Action, RightsBO
from helpers.DynamicLogs import LogsSwitcher, LogEmitter


class AcquisitionStats(object):
    """
    Small stats for an acquisition of a free column values inside.
    - min/max of values
    - distribution of != values
    - mode, i.e. freq of most frequent value
    """

    def __init__(self, acquis_orig_id: str, acquis_id: AcquisitionIDT):
        self.acquis_orig_id = acquis_orig_id
        self.acquis_id = acquis_id
        self.minima: List[Decimal] = []
        self.maxima: List[Decimal] = []
        self.first = True
        self.nb_objs = 0
        self.distribs: List[Dict[Decimal, int]] = []
        # The mode i.e. most used value
        self.modes: List[int] = []

    def add_values(self, values: List[Decimal]) -> None:
        if self.first:
            self.minima = values.copy()
            self.maxima = values.copy()
            self.distribs = [{a_val: 1} for a_val in values]
            self.first = False
        else:
            self.minima = [
                Decimal.min(new, pres) for new, pres in zip(values, self.minima)
            ]
            self.maxima = [
                Decimal.max(new, pres) for new, pres in zip(values, self.maxima)
            ]
            for a_distrib, a_val in zip(self.distribs, values):
                if a_val in a_distrib:
                    a_distrib[a_val] += 1
                else:
                    a_distrib[a_val] = 1
        self.nb_objs += 1

    @staticmethod
    def remove_exponent(d: Decimal) -> Decimal:
        return d.quantize(Decimal(1)) if d == d.to_integral() else d.normalize()

    def aggregate(self) -> None:
        a_distrib: Dict
        modes = self.modes
        for a_distrib in self.distribs:
            mode_for_val = max(a_distrib.values())
            modes.append(mode_for_val)

    def sums(self) -> Tuple[int, Union[Decimal, int]]:
        return self.nb_objs * len(self.minima), sum(self.modes)

    def __str__(self) -> str:
        ret = "%s (%d): " % (self.acquis_orig_id, self.nb_objs)
        ret += ",".join(
            [
                "[%s,%s,#%d,u%s]"
                % (
                    self.remove_exponent(min_val),
                    self.remove_exponent(max_val),
                    len(distrib),
                    a_mode,
                )
                for min_val, max_val, distrib, a_mode in zip(
                    self.minima, self.maxima, self.distribs, self.modes
                )
            ]
        )
        return ret


class ProjectStatsFetcher(Service, LogEmitter):
    def __init__(self, prj_id: int):
        super().__init__()
        self.prj_id = prj_id

    def log_file_path(self) -> str:
        return "stats_%d.log" % self.prj_id

    def run(self, current_user_id: int) -> List[str]:
        with LogsSwitcher(self):
            return self.do_run(current_user_id)

    def do_run(self, current_user_id: int) -> List[str]:
        # Security check
        _user, project = RightsBO.user_wants(
            self.session, current_user_id, Action.READ, self.prj_id
        )
        # OK
        proj_bo = ProjectBO(project).enrich()
        ret = []
        # TODO: Permissions
        ret.append(proj_bo.title)
        ret.append(str(OrderedDict(proj_bo.obj_free_cols)))  # Just for fixing a test
        free_cols_vals = proj_bo.get_all_num_columns_values(self.session)
        acquis_stats: AcquisitionStats = AcquisitionStats("", 0)
        for a_row in free_cols_vals:
            acquis_id, acquis_orig_id, objid, acquis_id_in_obf, *free_vals = a_row
            free_vals = [
                a_val if a_val is not None else Decimal("nan") for a_val in free_vals
            ]
            if acquis_id == acquis_stats.acquis_id:
                # Same acquisition
                pass
            else:
                # New acquisition, close previous one
                self.output_acq(acquis_stats, ret)
                # And start new one
                acquis_stats = AcquisitionStats(acquis_orig_id, acquis_id)
            acquis_stats.add_values(free_vals)
        self.output_acq(acquis_stats, ret)
        return ret

    def output_acq(self, acquis_stats: AcquisitionStats, ret: List[str]) -> None:
        acquis_stats.aggregate()
        ret.append(str(acquis_stats))
        ret.append("Total: %d values, dup %d values" % acquis_stats.sums())
