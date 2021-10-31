# noinspection PyUnresolvedReferences
from API_operations.Prediction import PredictForProject
from BG_operations.JobScheduler import JobScheduler

if __name__ == '__main__':
    JobScheduler.launch_at_interval(1)