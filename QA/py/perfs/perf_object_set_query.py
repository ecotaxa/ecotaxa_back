#
# Compare /object_set/query between a git reference (e.g. master) and the working copy,
# directly at ObjectManager level, on the DB of py/config.ini (RO_DB_* entries).
#
# Read-only: everything runs in a READ ONLY transaction, rights checks are stubbed to the
# project read in that transaction, and no Service (which opens a read-write session) is created.
# For each scenario it prints both timings and checks that the API output is identical.
#
# Usage, from repository root:
#   py/myvenv/bin/python3.14 QA/py/perfs/perf_object_set_query.py --old-ref master \
#       --project 17399 --samples 17399000008,17399000002,17399000001 [scenario name filters...]
#
import argparse
import configparser
import importlib.util
import subprocess
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from types import SimpleNamespace

REPO = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO / "py"))

import orjson  # noqa: E402
import sqlalchemy  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.orm import Session  # noqa: E402

from BO.Rights import RightsBO  # noqa: E402
from DB.Project import Project  # noqa: E402
from API_operations import ObjectManager as new_om  # noqa: E402

PAGE_FIELDS = [
    "obj.objid",
    "obj.imgcount",
    "img.file_name",
    "img.width",
    "img.height",
    "img.thumb_file_name",
    "img.thumb_width",
    "txo.display_name",
]
SAMPLE_FIELDS = ["obj.classif_id", "obj.classif_qual", "obj.depth_min"]


def ro_session() -> Session:
    cfg = configparser.ConfigParser()
    cfg.read(REPO / "py" / "config.ini")
    c = cfg["conf"]
    url = "postgresql+psycopg://{}:{}@{}:{}/{}".format(
        c["RO_DB_USER"],
        urllib.parse.quote(c["RO_DB_PASSWORD"]),
        c["RO_DB_HOST"],
        c["RO_DB_PORT"],
        c["RO_DB_DATABASE"],
    )
    session = Session(bind=sqlalchemy.create_engine(url))
    session.execute(text("SET TRANSACTION READ ONLY"))
    session.execute(text("SET statement_timeout = '300s'"))
    return session


def old_object_manager(ref: str):
    """ObjectManager module as of the given git reference."""
    src = subprocess.check_output(
        ["git", "-C", str(REPO), "show", f"{ref}:py/API_operations/ObjectManager.py"],
        text=True,
    ).replace(
        "from .helpers.Service import Service",
        "from API_operations.helpers.Service import Service",
    )
    tmp = Path(tempfile.mkdtemp()) / "old_object_manager.py"
    tmp.write_text(src)
    spec = importlib.util.spec_from_file_location("old_object_manager", tmp)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore
    return module


def scenarios(prj: int, samples: list):
    ret = []
    for a_sample in samples:
        ret.append((f"sample {a_sample}", prj, {"samples": a_sample}, SAMPLE_FIELDS, "obj.objid", 0, 50000))
    if samples:
        ret.append((f"no window {samples[-1]}", prj, {"samples": samples[-1]}, ["obj.classif_id"], None, None, None))
    ret += [
        ("page no sort", prj, {}, PAGE_FIELDS, None, 0, 100),
        ("page V", prj, {"statusfilter": "V"}, PAGE_FIELDS, None, 0, 100),
        ("page objid", prj, {}, PAGE_FIELDS, "obj.objid", 0, 100),
        ("page -objid p500", prj, {}, PAGE_FIELDS, "-obj.objid", 50000, 100),
        ("page V objid", prj, {"statusfilter": "V"}, PAGE_FIELDS, "obj.objid", 0, 100),
        ("page orig_id", prj, {}, PAGE_FIELDS, "obj.orig_id", 0, 100),
    ]
    return ret


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--old-ref", default="master")
    parser.add_argument("--project", type=int, required=True)
    parser.add_argument("--samples", default="", help="comma-separated sample ids")
    parser.add_argument("only", nargs="*", help="run only scenarios containing these words")
    args = parser.parse_args()

    session = ro_session()
    RightsBO.user_wants = staticmethod(  # type: ignore
        lambda _sess, user_id, _action, prj_id: (
            SimpleNamespace(id=user_id),
            session.get(Project, prj_id),
        )
    )

    def instance(cls):
        ret = cls.__new__(cls)
        ret.session = session
        ret.ro_session = session
        return ret

    old = instance(old_object_manager(args.old_ref).ObjectManager)
    new = instance(new_om.ObjectManager)

    def run_old(prj, *qry):
        ids, details, total = old.query(1, prj, *qry)
        return {
            "object_ids": [w[0] for w in ids],
            "acquisition_ids": [w[1] for w in ids],
            "sample_ids": [w[2] for w in ids],
            "project_ids": [w[3] for w in ids],
            "details": details,
            "total_ids": total,
        }

    def run_new(prj, *qry):
        res = new.query_columns(1, prj, *qry)
        return {
            "object_ids": res.object_ids,
            "acquisition_ids": res.acquisition_ids,
            "sample_ids": res.sample_ids,
            "project_ids": [prj] * len(res.object_ids),
            "details": res.details,
            "total_ids": res.total,
        }

    samples = [s for s in args.samples.split(",") if s]
    for name, prj, flt, fields, order, start, size in scenarios(args.project, samples):
        if args.only and not any(word in name for word in args.only):
            continue
        qry = (dict(flt), fields, order, start, size)
        run_old(prj, *qry)  # Warm up caches
        timings = {}
        outputs = {}
        for label, fct in (("old", run_old), ("new", run_new)):
            before = time.perf_counter()
            outputs[label] = fct(prj, *qry)
            timings[label] = (time.perf_counter() - before) * 1000
        same = orjson.dumps(outputs["old"], default=str) == orjson.dumps(
            outputs["new"], default=str
        )
        print(
            f"{name:28s} rows={len(outputs['new']['object_ids']):>6} "
            f"total={outputs['new']['total_ids']:>9} same={same} "
            f"old={timings['old']:7.0f}ms new={timings['new']:7.0f}ms "
            f"({(timings['new'] - timings['old']) / timings['old'] * 100:+4.0f}%)",
            flush=True,
        )
    session.rollback()
    # Not created in a with(), Service.__del__ would complain about the sessions
    for a_service in (old, new):
        a_service.session = a_service.ro_session = None


if __name__ == "__main__":
    main()
