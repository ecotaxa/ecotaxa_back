# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Any, Type

# noinspection PyPackageRequirements
from pydantic import BaseModel as PydanticModel


class TxtFileWithModel(object):
    """
        Holder class for a set of pydantic model derived instances, which can then be output as
        a txt file, which is fact a TSV one.
            Format is explained at: https://dwc.tdwg.org/text/
    """

    def __init__(self, model: Type[PydanticModel], name: str):
        """
            :param model: DwC class
            :param name: the file name where information will be written
        """
        self.model = model
        self.name = name
        # All starts with "Dwc"
        self.model_name = model.__name__[3:]
        self.core_or_ext = "core" if self.model_name == "Event" else "extension"
        self.namespace = "http://rs.iobis.org/obis/terms" if 'Measurement' in self.model_name \
            else "http://rs.tdwg.org/dwc/terms"
        self.fields = set()
        """ the set of fields for which we have at least one value """
        self.all: List[Dict[str, Any]] = []
        """ the dict-transformed values """

    def add_entity(self, an_entity):
        # Strip the pydantic model to the minimum.
        entity_dict = an_entity.dict(exclude_unset=True, exclude_none=True, exclude_defaults=True)
        self.fields.update(entity_dict.keys())
        self.all.append(entity_dict)

    def _sorted_fields(self):
        ret = sorted(self.fields)
        model_fields = self.model.__fields__
        for ndx in range(len(ret)):
            field_extra = model_fields[ret[ndx]].field_info.extra
            if field_extra.get("is_id"):
                # Move ID first
                ret.insert(0, ret.pop(ndx))
                break
        return ret

    def content(self) -> str:
        sorted_fields = self._sorted_fields()
        # write header,
        hdr = self.FIELD_SEP.join(sorted_fields)
        lines = [hdr]
        for an_obj in self.all:
            lines.append(self.model_to_line(an_obj, sorted_fields))
        return self.LINE_SEP.join(lines)

    def model_to_line(self, an_obj: Dict, fields: List[str]) -> str:
        values = [an_obj.get(a_field, "") for a_field in fields]
        return self.FIELD_SEP.join(values)

    FIELD_SEP = "\t"  # corresponds to 'fieldsTerminatedBy="\t"' in the metadata
    LINE_SEP = "\n"  # corresponds to 'linesTerminatedBy="\n"' in the metadata

    def meta_start(self):
        return r"""
  <%s encoding="UTF-8" fieldsTerminatedBy="\t" linesTerminatedBy="\n" fieldsEnclosedBy="" 
        ignoreHeaderLines="1" rowType="%s/%s">
    <files>
      <location>%s</location>
    </files> """ % (self.core_or_ext, self.namespace, self.model_name, self.name)

    def meta_end(self):
        return "  </%s>" % self.core_or_ext

    def meta(self) -> str:
        blocks = [self.meta_start()]
        fields = self._sorted_fields()
        if self.core_or_ext == "core":
            # Core: first field is the id column
            id_block = '    <id index="0"/>'
            field_start = 0
        else:
            # Extension: Core is _implicitely_ referenced via index 0
            id_block = '    <coreid index="0"/>'
            field_start = 1
        blocks.append(id_block)
        # Next fields start at 1
        for ndx, a_field in enumerate(fields[field_start:], field_start):
            field_desc = self.model.__fields__[a_field]
            term = field_desc.field_info.extra.get("term")
            blocks.append('    <field index="%d" term="%s"/>' % (ndx, term))
        blocks.append(self.meta_end())
        return self.LINE_SEP.join(blocks)

    def is_empty(self):
        return len(self.all) == 0
