# -*- coding: utf-8 -*-
# ProjectBOSet loading: derived fields and number of SQL queries
from contextlib import contextmanager

from sqlalchemy import event

from API_operations.CRUD.Projects import ProjectsService
from API_operations.CRUD.Users import UserService
from BO.Project import ProjectBOSet, ProjectBO, CollectionProjectBOSet
from DB.Project import Project
from DB.ProjectPrivilege import ProjectPrivilege
from DB.User import User
from tests.credentials import ADMIN_USER_ID
from tests.test_import import create_project
from tests.test_users_with_validation import create_db_user


@contextmanager
def _counting_queries(session):
    engine = session.get_bind()
    statements = []

    def count(conn, cursor, statement, *args):
        statements.append(statement)

    event.listen(engine, "before_cursor_execute", count)
    try:
        yield statements
    finally:
        event.remove(engine, "before_cursor_execute", count)


def _add_members(prj_id, prefix):
    """Add 2 annotators, one without organization. Return the other's organization."""
    # Existing organization only, not to shift organizations ids expected by other tests
    with UserService() as sce:
        admin_org = sce.session.get(User, ADMIN_USER_ID).organisation
    no_org_id = create_db_user(
        email=prefix + "_no_org@test.org", name=prefix + " No Org", organisation=None
    )
    org_id = create_db_user(
        email=prefix + "_org@test.org", name=prefix + " Org", organisation=admin_org
    )
    with ProjectsService() as sce:
        for usr_id in (no_org_id, org_id):
            priv = ProjectPrivilege()
            priv.projid = prj_id
            priv.member = usr_id
            priv.privilege = "Annotate"
            sce.session.add(priv)
        sce.session.commit()
    return admin_org


def test_project_bo_set_all_fields(database):
    prj_id = create_project(ADMIN_USER_ID, "BO set derived fields", instrument="UVP6")
    admin_org = _add_members(prj_id, "bo_set")
    with ProjectsService() as sce:
        with _counting_queries(sce.ro_session) as statements:
            # default fields: *all
            prj = ProjectBOSet(sce.ro_session, [prj_id]).as_list()[0]
            # touch every derived field, as the serializer would
            members = prj.managers + prj.annotators + prj.viewers
            orgs = [m.organisation for m in members]
            _ = (prj.obj_free_cols, prj.sample_free_cols, prj.acquisition_free_cols)
            _ = (prj.process_free_cols, prj.init_classif_list, prj.instrument_url)
    # No crash for the member without organization
    assert "" in orgs
    assert admin_org in orgs
    # Project + instrument, then privileges + users + organizations:
    # derived fields columns are loaded with the project, not lazily one by one
    assert len(statements) == 2, len(statements)


def test_project_bo_enrich(database):
    # Single project enrichment (used by stats) shares the ProjectBOSet logic
    prj_id = create_project(ADMIN_USER_ID, "BO enrich members", instrument="UVP6")
    admin_org = _add_members(prj_id, "bo_enrich")
    with ProjectsService() as sce:
        prj = ProjectBO(sce.session.get(Project, prj_id)).enrich()
        orgs = [m.organisation for m in prj.annotators]
        assert prj.instrument_url is not None
    assert sorted(orgs) == sorted(["", admin_org])


def _aggregate_counting_queries(prj_ids):
    # What Collections.aggregated_from_projects reads from the projects set
    with ProjectsService() as sce:
        with _counting_queries(sce.ro_session) as statements:
            projectset = CollectionProjectBOSet(session=sce.ro_session, prj_ids=prj_ids)
            projectset.get_initclassiflist_from_projects()
            projectset.get_classiffieldlist_from_projects()
            projectset.get_privileges_from_projects()
            projectset.get_access_from_projects()
            projectset.get_status_from_projects()
            for column in ["cnn_network_id", "instrument"]:
                projectset.get_common_attr_from_projects(column)
            projectset.get_mapping_from_projects()
    return len(statements)


def test_collection_project_bo_set_queries(database):
    prj_ids = [
        create_project(ADMIN_USER_ID, "Aggregated %d" % i, instrument="UVP6")
        for i in range(3)
    ]
    # Same number of queries whatever the number of projects: no lazy load per project
    assert _aggregate_counting_queries(prj_ids[:1]) == _aggregate_counting_queries(
        prj_ids
    )
