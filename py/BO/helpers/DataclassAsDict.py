# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#  Pretend a dataclass is a dict, for pydantic to loop over fields and serialize during API calls.
#
# Note: This breaks (a bit) isolation between layers, this is linked to Web layer
import dataclasses
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

    # noinspection PyMissingConstructor,PyUnresolvedReferences
    def __init__(self, rec):
        flds = self.__dataclass_fields__
        assert len(flds) == len(rec)
        for a_field, a_val in zip(flds, rec):
            setattr(self, a_field, a_val)

    def __iter__(self, *args, **kwargs):
        """ In the protocol, first step, pretend that self cannot iterate """
        pass

    def keys(self):
        """ In the protocol, second step, provide keys """
        # noinspection PyDataclass
        dataclasses.asdict(self, dict_factory=super().__init__)
        return super().keys()

    # def __getitem__(self, y):
    #     """ Third step, the caller asks for key values, they are (now) in our base class, i.e. dict """
    #     return self.as_dict.__getitem__(y)
