import logging

# noinspection PyUnusedImports
from API_operations.imports import Import  # To have the logger installed

# noinspection PyUnusedImports
from DB.helpers import DBWriter  # To have the logger installed

IMPORT_JOB_LOG = "API_operations.imports.Import"
DBWRITER_LOG = "DB.helpers.DBWriter"

import pytest


@pytest.fixture
def logspy(mocker):
    # Target your specific job logger
    logger = logging.getLogger(None)  # IMPORT_JOB_LOG)

    # Spy on the 'handle' method - this is the entry point for all log levels
    spy = mocker.spy(Import.logger, "handle")
    Import.logger.setLevel(logging.DEBUG)

    # Return a helper object that feels like caplog
    class LogChecker:
        @property
        def records(self):
            # Extract the LogRecord object from the spy's call arguments
            return [call.args[0] for call in spy.call_args_list]

        @property
        def messages(self):
            return [
                (
                    call.args[0].message % call.args[0].args
                    if len(call.args[0].args) > 1
                    else call.args[0].message
                )
                for call in spy.call_args_list
            ]

        def clear(self):
            spy.call_args_list.clear()

    return LogChecker()
