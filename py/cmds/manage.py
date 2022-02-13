# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

import typer

from API_operations.helpers.Service import Service
from DB.User import Role, User, Country
from DB.Views import views_creation_queries, views_deletion_queries
from cmds.db_upg.db_conn import app_config
from data.Countries import countries_by_name

DEFAULT_ROLES = [Role.APP_ADMINISTRATOR, Role.USERS_ADMINISTRATOR, Role.PROJECT_CREATOR]
THE_ADMIN = "administrator"
THE_ADMIN_PASSWORD = "ecotaxa"

app = typer.Typer()
db_app = typer.Typer()
app.add_typer(db_app, name="db")


@db_app.command(help="Initialize default security, roles and an administrator")
def init_security():
    """
    Create default security in the DB
    """
    sess = Service.build_connection(app_config).get_session()
    _init_security(sess)
    sess.close()


def _init_security(sess):
    for role_id, role in enumerate(DEFAULT_ROLES, 1):
        db_role = sess.query(Role).get(role_id)
        if db_role is None:
            typer.echo("Creating role '%s'" % role)
            # noinspection PyArgumentList
            sess.add(Role(id=role_id, name=role))
            sess.commit()
        else:
            typer.echo("Role '%s' is present" % role)
    # This is _not_ a full method of upgrading or restoring a damaged admin
    the_admin = sess.query(User).filter(User.email == THE_ADMIN).all()
    if len(the_admin) == 0:
        typer.echo("Creating user '%s'" % THE_ADMIN)
        # noinspection PyArgumentList
        adm_user = User(email=THE_ADMIN, password=THE_ADMIN_PASSWORD, name="Application Administrator")
        sess.add(adm_user)
        # TODO: The below needs the RO (read-only) connection, which is not created yet during build-from-scratch
        # with LoginService() as sce:
        #     # Encrypt the password right away
        #     sce.verify_and_update_password(THE_ADMIN_PASSWORD, adm_user)
        sess.commit()
    else:
        typer.echo("User '%s' is present" % THE_ADMIN)
    sess.commit()


@db_app.command(help="Recreate PG sequences with the right values")
def reset_sequences():
    from DB import Project
    from DB.helpers.DDL import Sequence

    target_metadata = Project.metadata
    # Collect the sequences and their bindings
    seqs = []
    for a_table in target_metadata.sorted_tables:
        for a_col in a_table.columns:
            if isinstance(a_col.default, Sequence):
                seqs.append([a_table.name, a_col.name, a_col.default.name])
    sess = Service.build_connection(app_config).get_session()
    # Recompute them
    with typer.progressbar(seqs) as progress:
        for tbl, col, seq in progress:
            sql = f"SELECT setval('{seq}', (SELECT max({col}) FROM {tbl}), true)"
            sess.execute(sql)
    sess.commit()
    sess.close()


@db_app.command(help="Ensure that static data is present")
def do_static():
    sess = Service.build_connection(app_config).get_session()
    _do_static(sess)
    sess.close()


def _do_static(sess):
    for a_country in countries_by_name.keys():
        db_country = sess.query(Country).get(a_country)
        if db_country is None:
            # noinspection PyArgumentList
            sess.add(Country(countryname=a_country))
            typer.echo("Adding country '%s'" % a_country)
    sess.commit()


CREATE_DB_SQL = """
create DATABASE %s
WITH ENCODING='UTF8'
OWNER=%s
TEMPLATE=template0 LC_CTYPE='C' LC_COLLATE='C' CONNECTION LIMIT=-1;
"""


@db_app.command(help="Create the DB, i.e. empty shell with no table inside.")
def create(user: str = "postgres", password: str = "", db_name: str = ""):
    super_conn = Service.build_super_connection(app_config, user, password)
    db_create_sql = CREATE_DB_SQL % (db_name, app_config.get("DB_USER"))
    super_conn.exec_outside_transaction(db_create_sql)


@db_app.command(help="Create the DB, i.e. empty shell with no table inside.")
def drop(user: str = "postgres", password: str = "", db_name: str = ""):
    super_conn = Service.build_super_connection(app_config, user, password)
    db_drop_sql = "DROP DATABASE IF EXISTS %s ( FORCE )" % db_name
    super_conn.exec_outside_transaction(db_drop_sql)


@db_app.command(help="Full DB build, the DB should be usable when done.")
def build():
    conn = Service.build_connection(app_config)
    sess = conn.get_session()
    from DB import Project

    meta = Project.metadata

    # Create the tables
    meta.create_all(bind=conn.engine)
    # Create the views
    for a_def in views_deletion_queries(meta):
        sess.execute(a_def)
    for a_def in views_creation_queries(meta):
        sess.execute(a_def)
    # Load static data
    _init_security(sess)
    _do_static(sess)


if __name__ == "__main__":
    app()
