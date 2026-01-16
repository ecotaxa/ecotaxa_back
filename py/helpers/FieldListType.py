from enum import Enum


class FieldListType(str, Enum):
    default = "*default"
    all = "*all"
    summary = "*summary"
