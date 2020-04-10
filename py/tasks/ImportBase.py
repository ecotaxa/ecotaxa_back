# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import datetime
import json
from os.path import join
from typing import Union

from BO.Mappings import ProjectMapping
from db.Project import Project
from db.Task import Task
from framework.Service import Service
from fs.TempTaskDir import TempTaskDir
from fs.Vault import Vault


# noinspection PyProtectedMember


class ImportBase(Service):
    """
        Common methods and data for import task steps.
    """

    def __init__(self):
        super().__init__()
        # From legacy code, vault and temptask are in src directory
        self.vault = Vault(join(self.link_src, 'vault'))
        self.temptask = TempTaskDir(join(self.link_src, 'temptask'))
        # Parameters
        self.prj_id: int = -1
        self.task_id: int = -1
        self.custom_mapping: Union[ProjectMapping, None] = None
        self.taxo_mapping: dict = {}
        self.taxo_found = {}
        self.found_users = {}
        self.skip_object_duplicate: str = "N"
        self.skip_already_loaded_file: str = "N"
        self.ignore_duplicates: str = "N"
        self.source_dir_or_zip: str = ""
        # Work vars
        self.prj: Union[Project, None] = None
        self.task: Union[Task, None] = None

    def update_param(self):
        if hasattr(self, 'param'):
            self.task.inputparam = json.dumps(self.param.__dict__)
        self.task.lastupdate = datetime.datetime.now()
        self.session.commit()

    def update_progress(self, percent: int, message: str):
        self.task.progresspct = percent
        self.task.progressmsg = message
        self.update_param()

    @staticmethod
    def log_for_user(msg: str):
        # TODO
        print(msg)
        pass

    def prepare_run(self):
        """
            Load what's needed for run.
        """
        self.prj = self.session.query(Project).filter_by(projid=self.prj_id).first()
        self.task = self.session.query(Task).filter_by(id=self.task_id).first()
