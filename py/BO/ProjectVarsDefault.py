"""
    The most common, i.e. from ZooProcess, formulae.
"""

from .ProjectVars import VariableValidity, ProjectVar
from .Vocabulary import Vocabulary, Units

not_lots_of_nines = VariableValidity("Not 999999", excluded_val=999999.0)
# Volumes are in m^3 already
# TODO: Still used in DwCA export, but shouldn't
volume_sampled = ProjectVar(
    "tot_vol", Vocabulary.volume_sampled, Units.cubic_metres, not_lots_of_nines
)
