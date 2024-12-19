from typing import Final
from enum import Enum


class FieldListType(str, Enum):
    default: Final = "*default"
    all: Final = "*all"
    summary: Final = "*summary"
