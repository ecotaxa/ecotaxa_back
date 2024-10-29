# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A job runner dedicated to (even if only sometimes) GPU-needing operations
#
import os

# We set this one in env. and anyway TF is not working without it
os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

import time

from API_operations.GPU_Prediction import GPUPredictForProject
from BG_operations.JobScheduler import JobScheduler
from DB.helpers.Connection import Connection


def main():
    Connection.APP_NAME = "ecotaxa_gpu_back"
    JobScheduler.INCLUDE = [GPUPredictForProject.JOB_TYPE]
    # As soon as something is running, exit and free all resources
    # the 'exit' will wait for the thread, i.e. job, to finish.
    while JobScheduler.the_runner is None:
        with JobScheduler() as sce:
            sce._run_one()
        time.sleep(10)


if __name__ == "__main__":
    main()
