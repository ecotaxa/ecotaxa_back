# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import abc
import logging
from abc import ABC
from threading import get_ident

LOGGING_FORMAT = '%(process)d:%(threadName)s:%(asctime)s:%(name)s:%(levelname)s %(message)s'
ALT_LOGGING_FORMAT = '%(asctime)s:%(name)s:%(levelname)s %(message)s'
LOG_FILE_TEMPLATE = "ecotaxa_back_%d.log"
LOG_FILE = LOG_FILE_TEMPLATE % 0  # os.getpid()


class PerThreadHandler(logging.Handler):
    """
        A constant Handler to a switching destination.
        It acts as a simple relay to another handler.
    """

    def __init__(self, handler):
        super().__init__()
        self.handler = handler
        self.alt_handlers = {}
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
        alt_handler.setFormatter(logging.Formatter(ALT_LOGGING_FORMAT))
        self.alt_handlers[get_ident()] = alt_handler

    def stop_switch(self):
        alt_handler = self.alt_handlers.get(get_ident())
        if alt_handler:
            alt_handler.close()
            del self.alt_handlers[get_ident()]


# Singleton handler per process
_the_handler = PerThreadHandler(logging.FileHandler(LOG_FILE))
_the_handler.handler.setFormatter(logging.Formatter(LOGGING_FORMAT))


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

    def switch(self):
        switch_to = self.emitter.log_file_path()
        if switch_to is not None:
            # Log the fact that we switch to a new file, to current log file.
            logging.log(logging.INFO, "Switching logs to %s", switch_to)
            _the_handler.switch_to(switch_to)

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.emitter.log_file_path():
            _the_handler.stop_switch()
