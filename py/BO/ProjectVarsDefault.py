"""
    The most common, i.e. from Zooprocess, formulae.
"""

from .ProjectVars import VariableValidity, ProjectVar
from .Vocabulary import Vocabulary, Units

zero_excluded_to_one_included = VariableValidity("]0,1]", min_val=0, max_val=1)

# Stored as the fraction denominator in zooprocess projects, and 'should be' a power of 2
# See e.g. https://aquaticbiotechnology.com/en/plankton-examination/plankton-sample-dividers
# Or search the Web for 'motoda'
subsample_coeff = ProjectVar("1/sub_part",
                             Vocabulary.subsampling_coefficient,
                             Units.dimensionless,
                             zero_excluded_to_one_included)

not_lots_of_nines = VariableValidity("Not 999999", excluded_val=999999.0)
# Volumes are in m^3 already
volume_sampled = ProjectVar("tot_vol",
                            Vocabulary.volume_sampled,
                            Units.cubic_metres,
                            not_lots_of_nines)

# TODO: Unused, the result is overriden with -1 in @see BO.Sample.aggregate_for_sample
equivalent_ellipsoidal_volume = ProjectVar("4.0/3.0*math.pi*(major/2*pixel_size)*(minor/2*pixel_size)**2",
                                           Vocabulary.biovolume,
                                           Units.cubic_millimetres_per_cubic_metre)

equivalent_spherical_volume = ProjectVar("4.0/3.0*math.pi*(math.sqrt(area/math.pi)*pixel_size)**3",
                                         Vocabulary.biovolume,
                                         Units.cubic_millimetres_per_cubic_metre)
