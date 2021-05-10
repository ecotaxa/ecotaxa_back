# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
# SQLAlchemy primtives for defining schema, i.e. columns and types
#
# noinspection PyUnresolvedReferences
from sqlalchemy import Column, ForeignKey, Sequence, Index
# noinspection PyUnresolvedReferences
from sqlalchemy import Integer, String, Boolean, DateTime, SmallInteger, func