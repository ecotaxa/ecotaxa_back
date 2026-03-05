# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import abc
import logging
import time
from abc import ABC
from logging import Logger, Handler
from threading import get_ident
from typing import Dict

LOGGING_FORMAT = (
    "%(process)d:%(threadName)s:%(asctime)s:%(name)s:%(levelname)s %(message)s"
)
ALT_LOGGING_FORMAT = "%(asctime)s:%(name)s:%(levelname)s %(message)s"
LOG_FILE_TEMPLATE = "ecotaxa_back_%d.log"
LOG_FILE = LOG_FILE_TEMPLATE % 0  # os.getpid()


class UTCFormatter(logging.Formatter):
    converter = time.gmtime


class PerThreadHandler(Handler):
    """
    A constant Handler to a switching destination.
    It acts as a simple relay to another handler.
    """

    def __init__(self, handler: Handler):
        super().__init__()
        self.handler = handler
        self.alt_handlers: Dict[int, Handler] = {}
        self.level = handler.level

    def emit(self, record):
        alt_handler = self.alt_handlers.get(get_ident())
        if alt_handler:
            alt_handler.emit(record)
        else:
            self.handler.emit(record)

    def switch_to(self, new_filename_or_stream):
        alt_handler = logging.FileHandler(new_filename_or_stream)
        alt_handler.setLevel(self.level)
        alt_handler.setFormatter(UTCFormatter(ALT_LOGGING_FORMAT))
        self.alt_handlers[get_ident()] = alt_handler

    def stop_switch(self):
        alt_handler = self.alt_handlers.get(get_ident())
        if alt_handler:
            alt_handler.close()
            del self.alt_handlers[get_ident()]


# Singleton handler per process
_the_handler = PerThreadHandler(logging.FileHandler(LOG_FILE))
_the_handler.handler.setFormatter(UTCFormatter(LOGGING_FORMAT))


def logger_nullify_after_fork():
    """Remove log handlers after a fork.
    We could replace them with more fresh handler but this is enough
    to prevent artificial sync b/w forked processes"""
    Logger.manager.root.handlers.clear()
    for _name, a_logger in Logger.manager.loggerDict.items():
        if isinstance(a_logger, Logger):
            if len(a_logger.handlers) > 0:
                a_logger.handlers.clear()
        elif isinstance(a_logger, logging.PlaceHolder):
            a_logger.loggerMap.clear()
    global _the_handler
    _the_handler = PerThreadHandler(logging.FileHandler(LOG_FILE))
    _the_handler.handler.setFormatter(UTCFormatter(LOGGING_FORMAT))


def get_logger(name) -> logging.Logger:
    ret = logging.getLogger(name)
    ret.addHandler(_the_handler)
    ret.setLevel(logging.INFO)
    return ret


class LogEmitter(ABC):
    """
    Just to force presence of the right primitive for log emitter classes, and add a member to the switcher.
    """

    @abc.abstractmethod
    def log_file_path(self) -> str: ...

    def __init__(self):
        self.switcher = None


class LogsSwitcher(object):
    """
    Redirect logs to the file provided by the log-emitting object.
    """

    def __init__(self, log_emitter: LogEmitter):
        self.emitter = log_emitter
        self.emitter.switcher = self

    def __enter__(self):
        self.switch()
        return self

    def switch(self) -> None:
        switch_to: str = self.emitter.log_file_path()
        if switch_to is not None:
            # Log the fact that we switch to a new file, to current log file.
            logging.log(logging.INFO, "Switching logs to %s", switch_to)
            _the_handler.switch_to(switch_to)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.emitter.log_file_path():
            _the_handler.stop_switch()


MONITOR_LOG_PATH = "ecotaxa_api_calls.log"


def get_api_logger():
    """Return a logger to a dedicated file for knowing what happens in some endpoints"""
    api_logger = logging.getLogger("API")
    api_logger.setLevel(logging.INFO)
    api_file_handler = logging.FileHandler(MONITOR_LOG_PATH)
    api_file_handler.setLevel(logging.INFO)
    api_file_handler.setFormatter(UTCFormatter("%(message)s #AT %(asctime)-15s"))
    api_logger.addHandler(api_file_handler)
    return api_logger
