# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
from typing import List, Dict, Any, Type, Set, Optional, Tuple

from API_models.helpers import BaseModel as PydanticModel


class TxtFileWithModel(object):
    """
    Holder class for a set of pydantic model derived instances, which can then be output as
    a txt file, which is fact a TSV one.
        Format is explained at: https://dwc.tdwg.org/text/
    """

    MODEL_TYPES = {
        "Event": "core",
        "Occurrence": "extension",
        "ExtendedMeasurementOrFact": "extension",
    }

    def __init__(self, model: Type[PydanticModel], name: str):
        """
        :param model: DwC class
        :param name: the file name where information will be written
        """
        self.model = model
        self.id_col_name, self.must_duplicate_id = self.id_col_from_model(model)
        self.name = name
        # All starts with "Dwc"
        self.model_name = model.__name__[3:]
        assert self.model_name in self.MODEL_TYPES
        self.namespace = (
            "http://rs.iobis.org/obis/terms"
            if "Measurement" in self.model_name
            else "http://rs.tdwg.org/dwc/terms"
        )
        self.fields: Set[str] = set()
        """ the set of fields for which we have at least one value """
        self.all: List[Dict[str, Any]] = []
        """ the dict-transformed values """

    @staticmethod
    def id_col_from_model(model) -> Tuple[Optional[str], bool]:
        model_fields = model.__fields__
        ret = None, True
        for a_field_name, a_field in model_fields.items():
            field_extra = a_field.field_info.extra
            if field_extra.get("is_id"):
                ret = a_field_name, field_extra.get("dup_id")
                break
        return ret

    def add_entity(self, an_entity):
        # Strip the pydantic model to the minimum.
        entity_dict = an_entity.dict(
            exclude_unset=True, exclude_none=True, exclude_defaults=True
        )
        # If the id is provided...
        if self.id_col_name in entity_dict:
            # ...copy it
            entity_dict["id"] = entity_dict[self.id_col_name]
            if not self.must_duplicate_id:
                # ...and remove original if not a duplication
                del entity_dict[self.id_col_name]
        # Add (eventually amended) entity
        self.fields.update(entity_dict.keys())
        self.all.append(entity_dict)

    def count(self) -> int:
        return len(self.all)

    def _sorted_fields(self):
        ret = []
        model_fields = self.model.__fields__
        # Loop over fields in the model order, with id first
        for a_field_name in ["id"] + list(model_fields.keys()):
            if a_field_name not in self.fields:
                # Unused
                continue
            ret.append(a_field_name)
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
    </files> """ % (
            self.MODEL_TYPES[self.model_name],
            self.namespace,
            self.model_name,
            self.name,
        )

    def meta_end(self):
        return "  </%s>" % self.MODEL_TYPES[self.model_name]

    def meta(self) -> str:
        blocks = [self.meta_start()]
        fields = self._sorted_fields()
        if self.model_name == "Event":
            # Event: first field is the id column, but sill output the origin ID column
            id_block = '    <id index="0"/>'
        else:
            # Extension: Core is _implicitely_ referenced via index 0
            id_block = '    <coreid index="0"/>'
        blocks.append(id_block)
        # Next fields start at 1
        field_start = 1 if self.id_col_name is not None else 0
        model_fields = self.model.__fields__
        for ndx, a_field in enumerate(fields[field_start:], field_start):
            field_desc = model_fields[a_field]
            term = field_desc.field_info.extra.get("term")
            blocks.append('    <field index="%d" term="%s"/>' % (ndx, term))
        blocks.append(self.meta_end())
        return self.LINE_SEP.join(blocks)

    def is_empty(self):
        return len(self.all) == 0
