# noinspection PyPackageRequirements
from BO.helpers.TSVHelpers import convert_degree_minute_float_to_decimal_degree


def test_CoordsConversions():
    # Textual to numeric coordinates conversion
    examples = {"1.5": 1.5,
                "-1.5": -1.5,
                "-45.6846": -45.6846,
                "1°30 00": 1.5,
                "-1°30 00": -1.5,
                "1°30 1": 1.5002777777777778,
                "-1°30 1": -1.5002777777777778,
                "-1°30 60": -1.5166666666666666,  # Hum
                "-1°31 0": -1.5166666666666666,
                "-1°30 600": -1.6666666666666665,  # Hum hum
                "-1°40 0": -1.6666666666666665,
                }
    for strFmt, expected in examples.items():
        assert convert_degree_minute_float_to_decimal_degree(strFmt) == expected, "Failed for " + strFmt
