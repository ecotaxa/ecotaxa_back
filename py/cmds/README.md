You will find here a few command-line utilities, for some functions which are not triggered by a FastAPI call.

You can either execute the commands below in a `venv` or prepend with proper environment setup as shown.

### Database migration scripts

See https://alembic.sqlalchemy.org/en/latest/autogenerate.html for background

* As a dev:

To generate diff script for upgrade:
- Current Directory : `<ECO_TAXA_BACK>/py/cmds`
- Create file `script.py.mako`
<details>

```
"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision}
Create Date: ${create_date}

"""

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}

from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

def upgrade():
    ${upgrades if upgrades else "pass"}


def downgrade():
    ${downgrades if downgrades else "pass"}
```

</details>
- `PATH=../venv38/bin PYTHONPATH=.. APP_CONFIG=../config.ini alembic revision --autogenerate -m "say something"`

Then check the newly appeared .py script in py/cmds/db_upg/versions which should contain the commands to upgrade the DB. It's often the case that
some manually generated tables appear there, so adjust manually the content.

Add the new script to the local git repo.

Next step is to generate SQL for DB creation giant SQL in QA directory:

`PATH=../venv38/bin PYTHONPATH=.. APP_CONFIG=../config.ini alembic upgrade --sql head
`

Copy/paste the last section (signalled by "-- Running upgrade...") at the end of `upgrade_prod.sql`.

Finally upgrade your local DB:

`PATH=../venv38/bin PYTHONPATH=.. APP_CONFIG=../config.ini alembic upgrade head
`

* As an operator, to upgrade a production DB, from docker shell:

```
docker exec -it ecotaxaback /bin/bash

I have no name!@5e55ec7508c5:/app$ cd cmds/

I have no name!@d2637e5ae89c:/app/cmds$ PYTHONPATH=.. alembic upgrade head
```

If new tables were created, and the read-only role is present, you will have to grant the right manually:

`ecotaxa=# GRANT SELECT ON ALL TABLES IN SCHEMA public TO readerole;
`

### Database related scripts

* This will create default admin user and roles.

`PATH=../venv38/bin PYTHONPATH=.. APP_CONFIG=../config.ini python manage.py db init-security
`

* This will recompute DB sequences, should they have been damaged somehow.

`PATH=../venv38/bin PYTHONPATH=.. APP_CONFIG=../config.ini python manage.py db reset-sequences
`
