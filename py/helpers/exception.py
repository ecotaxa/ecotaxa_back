import sys
import traceback
from typing import List


def format_exception(exc: Exception) -> List[str]:
    """
    Return the full stack, including current one + the cause.
    """
    exception_list = traceback.format_stack()
    exception_list = exception_list[:-2]
    exception_list.extend(traceback.format_tb(sys.exc_info()[2]))
    exception_list.extend(
        traceback.format_exception_only(sys.exc_info()[0], sys.exc_info()[1])
    )

    # exception_str = "Traceback (most recent call last):\n"
    # exception_str += "".join(exception_list)
    # # Removing the last \n
    # exception_str = exception_str[:-1]

    return exception_list
