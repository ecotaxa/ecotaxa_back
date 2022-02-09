You will find here a few command-line utilities, for some functions which are not triggered by a FastAPI call.

As a first step, you have to evaluate the python venv:


### Database migration scripts

* As a dev:

To generate diff script for upgrade:

See https://alembic.sqlalchemy.org/en/latest/autogenerate.html

`PATH=../venv38/bin PYTHONPATH=.. alembic revision --autogenerate
`
* As an operator, to upgrade a production DB, from docker shell:

```
docker exec -it ecotaxaback /bin/bash

I have no name!@5e55ec7508c5:/app$ cd cmds/

I have no name!@5e55ec7508c5:/app/cmds$ ls

I have no name!@d2637e5ae89c:/app/cmds$ PYTHONPATH=.. alembic upgrade
```