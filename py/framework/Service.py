# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import copy
import json
from abc import abstractmethod, ABC
from typing import Dict, Union

# noinspection PyPackageRequirements
from sqlalchemy.orm import Session

from db.Connection import Connection, check_sqlalchemy_version
from link import read_config, read_link


class BaseService(object):
    """
        A service, i.e. a stateless object which lives only for the time it does its job.
    """

    @classmethod
    def call(cls, json_params: Union[str, Dict]):
        assert cls != BaseService
        # Create the subclass instance
        instance: BaseService = cls()
        # Decode the params
        params = json_params
        was_json = False
        if isinstance(json_params, str):
            params: Dict = json.loads(json_params)
            was_json = True
        # Assign default values, gathering internal IDs
        by_id = {}
        cls._set_defaults(instance, by_id)
        # Assign members with input vars
        # noinspection PyUnresolvedReferences
        msg_descrip = cls.MSG_IN
        cls._set_params(instance, params, msg_descrip, by_id)
        # Run the service
        ret = instance.run()
        # If no explicit reply, serialize input
        if ret is None:
            ret = {}
            for p_name, p_val_id in msg_descrip.items():
                p_val = getattr(instance, by_id[p_val_id])
                ret[p_name] = p_val
        # Reply using the same dialect as request
        if was_json:
            ret = json.dumps(ret)
        return ret

    @classmethod
    def _set_params(cls, instance, params, msg_descrip, by_id):
        """
            For given instance, set attributes from runtime parameters.
        """
        for p_name, p_val_id in msg_descrip.items():
            try:
                p_val = params[p_name]
            except KeyError:
                # Not a big deal is a MSG field is not provided
                # TODO: Introspect the field to see if it's a Union with None
                continue
            try:
                setattr(instance, by_id[p_val_id], p_val)
            except KeyError:
                raise AttributeError("Could not find addr for %s, by_id: %s" % (p_name, by_id))

    @classmethod
    def _set_defaults(cls, instance, by_id):
        """
            For given instance, set attributes to their default value, i.e. the ones from class and ancestors.
        """
        # noinspection PyTypeChecker
        for a_class in (cls,) + cls.__bases__:
            s_name: str
            for s_name in vars(a_class):
                if s_name[0] == "_":
                    # Don't clone private attributes
                    continue
                s_val = getattr(cls, s_name)
                if callable(s_val):
                    # Don't clone methods
                    continue
                if s_name.lower() != s_name:
                    # Don't clone constants
                    continue
                setattr(instance, s_name, copy.deepcopy(s_val))
                by_id[id(getattr(cls, s_name))] = s_name

    @abstractmethod
    def run(self) -> Dict:
        """ Should not be called """


class Service(BaseService, ABC):
    """
        A service for EcoTaxa. Supplies common useful features like a DB session and filesystem conventions.
    """

    def __init__(self):
        check_sqlalchemy_version()
        config = read_config()
        conn = Connection(host=config['DB_HOST'], port=config['DB_PORT'], db=config['DB_DATABASE'],
                          user=config['DB_USER'], password=config['DB_PASSWORD'])
        self.session: Session = conn.sess
        self.config = config
        self.link_src = read_link()[0]
