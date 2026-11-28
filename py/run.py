# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
import argparse
from logging import INFO
from pathlib import Path
from typing import Any, Optional, Sequence

from helpers.AppConfig import Config

THE_APP = "main:app"
APP_PORT = str(Config().get_app_port())


def run_uvicorn() -> None:
    import uvicorn
    from uvicorn.config import LOGGING_CONFIG

    # Only the application tree needs to be watched for changes.
    app_dir = str(Path(__file__).resolve().parent)

    config = LOGGING_CONFIG
    # No need to log the requester, all comes from legacy app
    config["formatters"]["access"][
        "fmt"
    ] = '%(levelprefix)s "%(request_line)s" %(status_code)s'
    # Configure the root logger
    # config["loggers"][""] = {"handlers": ["default"], "level": "INFO"}

    # If reload is True then a single worker is spawned
    # Otherwise, several (multiprocess) processes are forked
    # Note that, unlike Gunicorn below, it's a fresh process from 0 which is created
    # uvicorn.run(THE_APP, workers=4, log_level=INFO )
    uvicorn.run(
        THE_APP,
        log_level=INFO,
        port=Config().get_app_port(),
        reload=True,
        reload_dirs=[app_dir],
        access_log=False,  # No reporting of HTTP requests and status
    )


def run_gunicorn(with_bg_worker: bool = False) -> None:
    from gunicorn.app.base import BaseApplication
    from uvicorn.workers import UvicornWorker

    class StandaloneUvicornWorker(UvicornWorker):
        def __init__(self, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.cfg.set("logconfig_dict", {})
            self.CONFIG_KWARGS["log_config"] = None

    # The import below makes the module variable for logging being computed.
    # Unlike simple uvicorn above, the processes are forked from Master (present one)
    # so all logging configuration is inherited.
    from main import app
    from BG_operations.BackgroundWorker import BackgroundWorker

    class EcotaxaApplication(BaseApplication):
        """Our Gunicorn application."""

        def init(self, parser, opts, args):
            pass

        def __init__(self) -> None:
            self.background_worker: Optional[BackgroundWorker] = None
            self.options = {
                "worker_class": StandaloneUvicornWorker,
                "bind": "%s:%s" % ("0.0.0.0", APP_PORT),
                # Use WEB_CONCURRENCY env. var
                # 'workers': 16,
                # https://docs.gunicorn.org/en/stable/settings.html#workers
                # Below is only for gthread workers type
                # 'threads': 2,
                # "timeout" is misnamed, it's in fact the maximum time for a worker to reply to a request
                # https://stackoverflow.com/questions/54832771/gunicorn-doesnt-kill-worker-even-after-timeout
                # We have quite long occasional queries so increase from default value of 30 (sec)
                "timeout": 180,
                # Kill workers after this number of requests received. Good and simple concept but killing the worker
                # means eventually killing the running task inside. Idea can be recycled but inside the app itself.
                # "max_requests": 1024,
                # "graceful_timeout": 10,
                # Keep gunicorn silent after start sequence
                # "accesslog": "-",
                # "errorlog": "-",
                "log_level": "error",
                # To enable, but it gives a weird warning about missing /var/www rights
                # as we run under this account on prod'.
                # I guess it's $HOME from /etc/passwd for the guest. Whatever.
                "control_socket_disable": True,
                # Keep uvicorn loggers
                "disable_existing_loggers": False,
                "when_ready": self.when_ready,
                "post_fork": self.post_fork,
                "on_exit": self.on_exit,
            }
            self.application = app
            super().__init__()

        def load_config(self) -> None:
            config = {
                key: value
                for key, value in self.options.items()
                if key in self.cfg.settings and value is not None
            }
            for key, value in config.items():
                self.cfg.set(key.lower(), value)

        def load(self) -> Any:
            return self.application

        def when_ready(self, server: Any) -> None:
            """In master process"""
            if with_bg_worker:
                self.background_worker = BackgroundWorker()

        def post_fork(self, server: Any, worker: Any) -> None:
            from API_operations.helpers.Service import Service

            self.background_worker = None  # Safety
            Service.close_connections(close=False)

        def on_exit(self, server: Any) -> None:
            """In master process"""
            if self.background_worker is not None:
                self.background_worker.shutdown()

    app = EcotaxaApplication()
    app.run()


def main(argv: Optional[Sequence[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Run EcoTaxa backend server.")
    subparsers = parser.add_subparsers(dest="server")

    subparsers.add_parser("uvicorn", help="Run development server with uvicorn.")
    gunicorn_parser = subparsers.add_parser(
        "gunicorn", help="Run production server with gunicorn."
    )
    gunicorn_parser.add_argument(
        "--with-bg-worker",
        action="store_true",
        help="Start an in-process BackgroundWorker alongside Gunicorn.",
    )

    args = parser.parse_args(argv)
    if args.server == "uvicorn":
        run_uvicorn()
    elif args.server == "gunicorn":
        run_gunicorn(with_bg_worker=args.with_bg_worker)


if __name__ == "__main__":
    main()
