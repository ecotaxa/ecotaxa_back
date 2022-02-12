# -*- coding: utf-8 -*-
# This file is part of Ecotaxa, see license.md in the application root directory for license informations.
# Copyright (C) 2015-2022  Picheral, Colin, Irisson (UPMC-CNRS)
#

import typer

from DB.User import Role, User
from db_upg.db_conn import conn
from helpers.login import LoginService

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
    sess = conn.get_session()
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
        with LoginService() as sce:
            # Encrypt the password right away
            sce.verify_and_update_password(THE_ADMIN_PASSWORD, adm_user)
        sess.commit()
    else:
        typer.echo("User '%s' is present" % THE_ADMIN)
    sess.close()


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
    sess = conn.get_session()
    # Recompute them
    with typer.progressbar(seqs) as progress:
        for tbl, col, seq in progress:
            sql = f"SELECT setval('{seq}', (SELECT max({col}) FROM {tbl}), true)"
            sess.execute(sql)
    sess.commit()
    sess.close()


if __name__ == "__main__":
    app()
