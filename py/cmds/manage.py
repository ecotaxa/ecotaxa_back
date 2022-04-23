# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

import typer

from API_operations.helpers.Service import Service
from BO.Rights import RightsBO, Action
from DB.Instrument import Instrument
from DB.User import Role, User, Country
from DB.Views import views_creation_queries, views_deletion_queries
from cmds.db_upg.db_conn import app_config  # type:ignore
from data.Countries import countries_by_name
from data.Instruments import DEFAULT_INSTRUMENTS

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
    for role_id, role in enumerate(Role.ALL_ROLES, 1):
        db_role = sess.query(Role).get(role_id)
        if db_role is None:
            typer.echo("Adding role '%s'" % role)
            # noinspection PyArgumentList
            sess.add(Role(id=role_id, name=role))
            sess.commit()
    # This is _not_ a full method of upgrading or restoring a damaged admin
    the_admin = sess.query(User).filter(User.email == THE_ADMIN).all()
    if len(the_admin) == 0:
        typer.echo("Adding user '%s'" % THE_ADMIN)
        # noinspection PyArgumentList
        adm_user = User(email=THE_ADMIN, password=THE_ADMIN_PASSWORD, name="Application Administrator")
        all_roles = {a_role.name: a_role for a_role in sess.query(Role)}
        RightsBO.set_allowed_actions(adm_user, [Action.ADMINISTRATE_APP], all_roles)
        sess.add(adm_user)
        # TODO: The below needs the RO (read-only) connection, which is not created yet during build-from-scratch
        # with LoginService() as sce:
        #     # Encrypt the password right away
        #     sce.verify_and_update_password(THE_ADMIN_PASSWORD, adm_user)
        sess.commit()
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
    # Countries
    for a_country in countries_by_name.keys():
        db_country = sess.query(Country).get(a_country)
        if db_country is None:
            typer.echo("Adding country '%s'" % a_country)
            # noinspection PyArgumentList
            sess.add(Country(countryname=a_country))
    # Instruments
    # Note: Should do nothing just after table creation, as instruments
    # are loaded then (@see hook in DB/Instrument.py).
    for ins, nam, url in DEFAULT_INSTRUMENTS:
        db_ins = sess.query(Instrument).get(ins)
        if db_ins is None:
            typer.echo("Adding instrument '%s'" % ins)
            db_ins = Instrument()
            db_ins.instrument_id = ins
            db_ins.name = nam
            db_ins.bodc_url = url
            sess.add(db_ins)
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
    db_create_sql = CREATE_DB_SQL % (db_name, app_config.get_cnf("DB_USER"))
    super_conn.exec_outside_transaction(db_create_sql)


@db_app.command(help="Completely drop the DB.")
def drop(user: str = "postgres", password: str = "", db_name: str = ""):
    super_conn = Service.build_super_connection(app_config, user, password)
    db_drop_sql = "DROP DATABASE IF EXISTS %s ( FORCE )" % db_name
    super_conn.exec_outside_transaction(db_drop_sql)


@db_app.command(help="Full DB build, the DB should be usable when done.")
def build():
    conn = Service.build_connection(app_config)
    sess = conn.get_session()
    from DB import Project

    # It's the same metadata object for the whole app, so pick one
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
