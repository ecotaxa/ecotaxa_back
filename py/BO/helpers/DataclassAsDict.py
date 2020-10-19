# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Pretend a dataclass is a dict, for pydantic to loop over fields and serialize during API calls.
#
# Note: This breaks (a bit) isolation between layers, this is linked to Web layer
# noinspection PyUnresolvedReferences
from dataclasses import dataclass


class DataclassAsDict(dict):
    """
        When converting a plain object to a Model, pydantic tries to call dict(obj).
            See in pydantic/main.py
            @classmethod
                def validate(cls: Type['Model'], value: Any) -> 'Model':
        The below is enough to fool dict() into iterating over the dataclass fields.
    """

    def __init__(self, rec):
        # noinspection PyUnresolvedReferences
        flds = self.__dataclass_fields__
        assert len(flds) == len(rec)
        super().__init__(zip(flds, rec))

    def __getattr__(self, item):
        """ Redirect to dict for dataclass fields access """
        return self[item]
