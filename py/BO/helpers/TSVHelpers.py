import re
from typing import Optional


def clean_value(value: str, is_numeric: bool = False):
    """
        Remove spaces and map 2 special values to empty string, which is _accepted_ like an empty column.
    """
    if value is None:
        return ''
    value = value.strip()
    #    if len(value) < 4 and value.lower() in ('nan', 'na'):
    # TODO: Use RE and benchmark
    if is_numeric and value.lower() in ('nan', 'na'):
        return ''
    return value


def clean_value_and_none(value: Optional[str], is_numeric: bool = False):
    """
        Like previous but accept None as well.
    """
    if value is None:
        return ''
    return clean_value(value, is_numeric)


_minus_inf = float("-inf")


def to_float(value: str):
    """
    Convert input str to a python float, excluding -inf.
    :param value:
    :return:
    """
    if value == '':
        return None
    try:
        ret = float(value)
        if ret == _minus_inf:
            return None
        return ret
    except ValueError:
        return None


def none_to_empty(value: Optional[str]):
    """
    Map None to empty string or just return input value.
    :param value: None or any string
    :return:
    """
    if value is None:
        return ''
    return value


def convert_degree_minute_float_to_decimal_degree(v):
    m = re.search(r"(-?\d+)°(\d+) (\d+)", v)
    if m:  # data in format DDD°MM SSS
        parts = [float(x) for x in m.group(1, 2, 3)]
        parts[1] += parts[2] / 60  # on ajoute les secondes en fraction des minutes
        parts[0] += parts[1] / 60  # on ajoute les minutes en fraction des degrés
        return parts[0]
    else:  # decimal part was in minutes
        # Bug in 2.2 @see https://github.com/oceanomics/ecotaxa_dev/issues/340
        v = to_float(v)
        return v
