import os
import sys
import time
from unittest.mock import patch

# Add the parent directory to sys.path to allow importing from the 'py' directory
sys.path.append(
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "py"))
)

# Set the APP_CONFIG environment variable to point to the dev config
os.environ["APP_CONFIG"] = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "py", "config.ini")
)

os.environ["PROTOCOL_BUFFERS_PYTHON_IMPLEMENTATION"] = "python"

from API_operations.GPU_Prediction import GPUPredictForProject
from API_models.prediction import PredictionReq
from API_models.filters import ProjectFilters


def try_real_prediction():
    params = {
        "project_id": 337,
        "source_project_ids": [302, 1040],
        "learning_limit": 3000,
        "features": [
            "fre.%area",
            "fre.angle",
            "fre.area",
            "fre.area_exc",
            "fre.bx",
            "fre.by",
            "fre.cdexc",
            "fre.centroids",
            "fre.circ.",
            "fre.circex",
            "fre.convarea",
            "fre.convperim",
            "fre.cv",
            "obj.depth_max",
            "obj.depth_min",
            "fre.elongation",
            "fre.esd",
            "fre.fcons",
            "fre.feret",
            "fre.feretareaexc",
            "fre.fractal",
            "fre.height",
            "fre.histcum1",
            "fre.histcum2",
            "fre.histcum3",
            "fre.intden",
            "fre.kurt",
            "fre.major",
            "fre.max",
            "fre.mean",
            "fre.meanpos",
            "fre.median",
            "fre.min",
            "fre.minor",
            "fre.mode",
            "fre.nb1",
            "fre.nb2",
            "fre.nb3",
            "fre.perim.",
            "fre.perimareaexc",
            "fre.perimferet",
            "fre.perimmajor",
            "fre.range",
            "fre.skelarea",
            "fre.skew",
            "fre.slope",
            "fre.sr",
            "fre.stddev",
            "fre.symetrieh",
            "fre.symetriehc",
            "fre.symetriev",
            "fre.symetrievc",
            "fre.thickr",
            "fre.width",
            "fre.x",
            "fre.xm",
            "fre.xmg5",
            "fre.xstart",
            "fre.y",
            "fre.ym",
            "fre.ymg5",
            "fre.ystart",
        ],
        "categories": [
            84963,
            45074,
            62005,
            61996,
            11514,
            13333,
            85008,
            85076,
            85061,
            61993,
            25828,
            25932,
            81941,
            84976,
            82399,
            78426,
            25824,
            85115,
            61990,
            78418,
            61973,
            85185,
            25942,
            85060,
            26524,
            85078,
            25930,
            92239,
            84997,
            25944,
            84980,
            61991,
            12908,
            85067,
            30815,
            85004,
            85117,
            12865,
            84993,
            92238,
            85116,
            84989,
            11518,
            84977,
            56693,
            84968,
            85003,
            92039,
            84991,
            5,
            45054,
            92068,
            85079,
            84970,
            78412,
            85193,
            85044,
            45071,
            26525,
            85069,
            92012,
            25943,
            72431,
            13381,
            84995,
            61982,
            92112,
            84974,
            11758,
            84975,
            84965,
            81977,
            11509,
        ],
        "use_scn": True,
        "pre_mapping": {},
    }
    req = PredictionReq(**params)
    filters = ProjectFilters().base()
    with patch(
        "API_operations.GPU_Prediction.GPUPredictForProject._get_owner_id",
        return_value=760,
    ), patch(
        "API_operations.helpers.JobService.JobServiceBase.update_progress",
        return_value=None,
    ), patch(
        "API_operations.helpers.JobService.JobServiceBase.set_job_result",
        return_value=None,
    ):
        with GPUPredictForProject(req, filters) as job:
            print("Starting prediction...")
            start_time = time.time()
            job.do_prediction()  # If you want to run it
            end_time = time.time()
            print(f"Prediction finished in {end_time - start_time:.2f} seconds")
            return job


if __name__ == "__main__":
    try_real_prediction()
