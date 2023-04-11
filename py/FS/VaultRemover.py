# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2020  Picheral, Colin, Irisson (UPMC-CNRS)
#
#
# A thread for removing files in the background
#
from logging import Logger
from os import unlink
from queue import Queue
from threading import Thread
from typing import List, Optional

from helpers.AppConfig import Config
from helpers.Timer import CodeTimer
from .Vault import Vault


class VaultRemover(Thread):
    """
    Classical usage of a Queue to spool the job to a background task.
    """

    def __init__(self, config: Config, logger: Logger):
        super().__init__(name="Vault remover")
        self.vault = Vault(config.vault_dir())
        # TODO: a collection.deque is faster
        # TODO: or store the file lists, e.g. in chunks of 10, instead of filling the queue with individual items
        self.files_queue: Queue[Optional[str]] = Queue()
        self.logger = logger

    def do_start(self) -> "VaultRemover":
        """
        Start and return self for nice one-line syntax :)
        """
        super().start()
        return self

    def add_files(self, files: List[str]) -> None:
        """
        Add more files for processing.
        """
        for a_file in files:
            self.files_queue.put(a_file)

    def run(self) -> None:
        """
        As long as the queue is not signalled empty, process one file.
        """
        queue = self.files_queue
        problems = []
        while True:
            a_file = queue.get()
            if a_file is None:
                break
            file_in_vault = self.vault.image_path(a_file)
            try:
                unlink(file_in_vault)
            except FileNotFoundError:
                problems.append(a_file)
                if len(problems) > 10:
                    self.logger.error("Could not remove files %s", ",".join(problems))
                    problems.clear()
        if len(problems) > 0:
            self.logger.error("Could not remove file(s) %s", ",".join(problems))

    def wait_for_done(self) -> None:
        """
        Signal the thread that we have no more files, and wait for the job done.
        """
        self.logger.info(
            "Approximately %d files in deletion queue", self.files_queue.qsize()
        )
        self.files_queue.put(None)
        with CodeTimer("Wait for files removal: ", self.logger):
            self.join()
