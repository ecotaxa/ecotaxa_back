# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import os
import sys
from logging import INFO
from typing import Any

THE_APP = "main:app"
APP_PORT = "5000"

# Overload port if provided from env.
if "APP_PORT" in os.environ:
    APP_PORT = os.environ["APP_PORT"]


def run_uvicorn() -> None:
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG
    config = LOGGING_CONFIG
    # No need to log the requester, all comes from legacy app
    config["formatters"]["access"]["fmt"] = '%(levelprefix)s "%(request_line)s" %(status_code)s'
    # Configure the root logger
    # config["loggers"][""] = {"handlers": ["default"], "level": "INFO"}

    # If reload is True then a single worker is spawned
    # Otherwise, several (multiprocess) processes are forked
    # Note that, unlike Gunicorn below, it's a fresh process from 0 which is created
    # uvicorn.run(THE_APP, workers=4, log_level=INFO )
    uvicorn.run(THE_APP, log_level=INFO, port=int(APP_PORT), reload=True)


def run_gunicorn() -> None:
    from gunicorn.app.base import BaseApplication
    # The import below makes the module variable for logging being computed.
    # Unlike simple uvicorn above, the processes are forked from Master (present one)
    # so all logging configuration is inherited.
    from main import app

    class EcotaxaApplication(BaseApplication):
        """Our Gunicorn application."""

        def init(self, parser, opts, args):
            pass

        def __init__(self) -> None:
            self.options = {
                # Refers to site-packages/uvicorn/workers.py
                "worker_class": "uvicorn.workers.UvicornWorker",
                'bind': '%s:%s' % ('0.0.0.0', APP_PORT),
                # Use WEB_CONCURRENCY env. var
                # 'workers': 16,
                # https://docs.gunicorn.org/en/stable/settings.html#workers
                # Below is only for gthread workers type
                # 'threads': 2,
                'timeout': 600,
                # Keep gunicorn silent after start sequence
                # "accesslog": "-",
                # "errorlog": "-",
                "log_level": "error"
            }
            self.application = app
            super().__init__()

        def load_config(self) -> None:
            config = {
                key: value for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self) -> Any:
            return self.application

    EcotaxaApplication().run()


if __name__ == '__main__':
    the_arg = sys.argv[1] if len(sys.argv) == 2 else ""
    if the_arg == "uvicorn":
        run_uvicorn()
    elif the_arg == "gunicorn":
        run_gunicorn()
