import importlib

from sqlalchemy import select
from typer.testing import CliRunner

from API_operations.helpers.Service import Service
from DB.Job import Job, DBJobStateEnum
from tests.credentials import ADMIN_USER_ID, ORDINARY_USER_USER_ID

runner = CliRunner()


def get_app():
    # cmds.db_upg.db_conn and cmds.manage instantiate Config() and establish a DB connection
    # at module import time. We reload them here so they evaluate under the active test environment
    # configuration (e.g., APP_CONFIG set by pytest fixtures) rather than default/cached settings.
    import cmds.db_upg.db_conn

    importlib.reload(cmds.db_upg.db_conn)
    import cmds.manage

    importlib.reload(cmds.manage)
    return cmds.manage.app


def test_manage_help(config):
    app = get_app()
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "run-nightly" in result.output
    assert "db" in result.output


def test_manage_run_nightly_help(config):
    app = get_app()
    result = runner.invoke(app, ["run-nightly", "--help"])
    assert result.exit_code == 0
    assert "--user-id" in result.output
    assert "-u" in result.output


def test_manage_run_nightly_missing_user_id(config):
    app = get_app()
    result = runner.invoke(app, ["run-nightly"])
    assert result.exit_code != 0
    assert "Missing option" in result.output or "user-id" in result.output


def test_manage_run_nightly_explicit_admin_user_id(database):
    app = get_app()
    result = runner.invoke(app, ["run-nightly", "--user-id", str(ADMIN_USER_ID)])
    assert result.exit_code == 0
    assert (
        f"Starting NightlyMaintenance job for admin user #{ADMIN_USER_ID}..."
        in result.output
    )
    assert "Executing maintenance tasks..." in result.output
    assert "finished successfully." in result.output

    # Verify in DB that job was executed and finished
    with Service() as sce:
        qry = select(Job).filter_by(type="NightlyMaintenance").order_by(Job.id.desc())
        job = sce.session.scalar(qry)
        assert job is not None
        assert job.state == DBJobStateEnum.Finished
        assert job.owner_id == ADMIN_USER_ID

    # Verify short option -u also works
    result_short = runner.invoke(app, ["run-nightly", "-u", str(ADMIN_USER_ID)])
    assert result_short.exit_code == 0
    assert (
        f"Starting NightlyMaintenance job for admin user #{ADMIN_USER_ID}..."
        in result_short.output
    )
    assert "finished successfully." in result_short.output


def test_manage_run_nightly_non_admin_user_id(database):
    app = get_app()
    result = runner.invoke(
        app, ["run-nightly", "--user-id", str(ORDINARY_USER_USER_ID)]
    )
    assert result.exit_code != 0


def test_manage_run_nightly_job_failure(database, monkeypatch):
    from API_operations.helpers.JobService import JobServiceBase

    app = get_app()

    def mock_run_in_background(self):
        # Set job state to Error in DB to simulate job failure
        with Service() as service:
            job = service.session.get(Job, self.job_id)
            if job:
                job.state = DBJobStateEnum.Error
                job.progress_msg = "Simulated failure"
                service.session.commit()

    monkeypatch.setattr(JobServiceBase, "run_in_background", mock_run_in_background)

    result = runner.invoke(app, ["run-nightly", "-u", str(ADMIN_USER_ID)])
    assert result.exit_code == 1
    assert "failed: Simulated failure" in result.output
