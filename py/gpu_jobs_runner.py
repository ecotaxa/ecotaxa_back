# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2021  Picheral, Colin, Irisson (UPMC-CNRS)
#
# A job runner dedicated to (even if only sometimes) GPU-needing operations
#
from API_operations.GPU_Prediction import GPUPredictForProject
from BG_operations.JobScheduler import JobScheduler

if __name__ == '__main__':
    JobScheduler.INCLUDE = [GPUPredictForProject.JOB_TYPE]
    JobScheduler.launch_at_interval(1)
