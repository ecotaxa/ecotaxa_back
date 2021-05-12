# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# Business object on top of job.
# The idea is to keep here the DB details, namely the fact that many fields are JSON-encoded.
#
from datetime import datetime
from json import loads as json_loads, dumps as json_dumps
from typing import Dict, Optional, Any, List

from BO.User import UserIDT
from DB import Job, Session
from DB.Job import JobIDT, DBJobStateEnum
from helpers.DynamicLogs import get_logger

logger = get_logger(__name__)


class JobBO(object):
    """
        Thin wrapper over DB job.
    """
    # Pending message
    PENDING_MESSAGE = "Waiting for a slot"
    # An ack of Asking state
    REPLIED_MESSAGE = "Proceeding"
    # An ack of Restart action
    RESTARTING_MESSAGE = "Restarting"
    # An ack of Kill action
    KILLED_MESSAGE = "Killed"

    __slots__ = ['_job', '_session', 'params', 'result', 'errors', 'question', 'reply', 'inside']

    def __init__(self, db_job: Job):
        self._job = db_job
        self._session: Optional[Session] = None
        # Deserialize what we store in JSON
        self.params = self.deser(db_job.params, {})
        self.result = self.deser(db_job.result, {})
        self.errors = self.deser(db_job.messages, [])
        self.question = self.deser(db_job.question, {})
        self.inside = self.deser(db_job.inside, {})
        self.reply = self.deser(db_job.reply, {})

    @staticmethod
    def deser(value, fallback):
        if value:
            return json_loads(value)
        else:
            return fallback

    def update_inside(self, to_save: Dict):
        self.inside.update(to_save)
        self._job.inside = json_dumps(self.inside)

    def set_result(self, result: Any):
        self.result = result
        self._job.result = json_dumps(result)

    def set_reply(self, reply: Dict):
        self.reply = reply
        self._job.reply = json_dumps(reply)

    def set_messages(self, messages: List):
        self.errors = messages
        self._job.messages = json_dumps(messages)

    def set_question(self, question: Dict):
        self.question = question
        self._job.question = json_dumps(question)

    def __getattr__(self, item):
        """ Fallback for 'not found' field after the C getattr() call.
            If we did not enrich a Job field somehow then return it """
        return getattr(self._job, item)

    def __setattr__(self, item, value):
        """ Set the attribute in the underlying DB object """
        if item in self.__slots__:
            super().__setattr__(item, value)
        else:
            setattr(self._job, item, value)

    @classmethod
    def get_one(cls, session: Session, job_id: JobIDT) -> Optional[Job]:
        job = session.query(Job).get(job_id)
        return job

    @classmethod
    def get_for_update(cls, session: Session, job_id: JobIDT) -> 'JobBO':
        """
            Return a single JobBO. If used in a 'with' context, the session will commit on exit.
            Note: it's not only the Job which will be committed, but the _whole_ session.
        """
        job = cls.get_one(session, job_id)
        if job is None:
            raise ValueError
        job.updated_on = datetime.now()
        ret = JobBO(job)
        ret._session = session
        return ret

    def delete(self):
        self._session.delete(self._job)

    def __enter__(self):
        assert self._session is not None
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self._session.commit()
        self._session = None

    @classmethod
    def create_job(cls, session: Session, user_id: UserIDT, job_type: str, args: Dict) -> Job:
        job = Job()
        job.state = DBJobStateEnum.Pending
        job.progress_msg = cls.PENDING_MESSAGE
        job.creation_date = job.updated_on = datetime.now()
        job.type = job_type
        job.owner_id = user_id
        job.params = json_dumps(args)
        job.inside = job.reply = json_dumps({})
        job.messages = json_dumps([])
        session.add(job)
        session.commit()
        return job
