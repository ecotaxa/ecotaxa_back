# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A job runner dedicated to (even if only sometimes) GPU-needing operations
#
import time

from API_operations.GPU_Prediction import GPUPredictForProject
from BG_operations.JobScheduler import JobScheduler


def main():
    JobScheduler.INCLUDE = [GPUPredictForProject.JOB_TYPE]
    with JobScheduler() as sce:
        # As soon as something is running, exit and free all resources
        # the 'exit' will wait for the thread, i.e. job, to finish.
        while sce.the_runner is None:
            sce.run_one()
            time.sleep(10)


if __name__ == '__main__':
    main()
