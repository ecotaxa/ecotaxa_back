## EcoTaxa back-end: Setting up a development environment

The environment consists mainly of a Postgres database and some directories.

### I. Postgres

As of the writing, version 13.6 is used in main production site (https://ecotaxa.obs-vlfr.fr).

#### I.1 Using docker

See https://hub.docker.com/_/postgres/ for in-depth details.

We need a PG docker accessible from the host, persisting its data in a given directory.   
It would result e.g. in:

    ecotaxa_back$ docker run -d -p 5432:5432 --name ecotaxa_db -e POSTGRES_PASSWORD=mysecretpassword -e PGDATA=/var/lib/postgresql/data/pgdata -v `pwd`/pg_data:/var/lib/postgresql/data postgres:13.6

Then, to check:

    ecotaxa_back$ docker logs ecotaxa_db
    ...
    LOG:  starting PostgreSQL 13.6 (Debian 13.6-1.pgdg110+1) on x86_64-pc-linux-gnu, compiled by gcc (Debian 10.2.1-6) 10.2.1 20210110, 64-bit
    LOG:  listening on IPv4 address "0.0.0.0", port 5432
    LOG:  listening on IPv6 address "::", port 5432
    LOG:  listening on Unix socket "/var/run/postgresql/.s.PGSQL.5432"
    LOG:  database system was shut down at 2022-04-20 15:34:35 UTC
    LOG:  database system is ready to accept connections

So our small DB is now running on port 5432 (standard one) and persists in the current local directory.

**Note**: It's generally useful to follow Postgres logs by issuing:

    docker logs -f ecotaxa_db

In a dedicated shell.

#### I.2 Local PG installation

For the braves only.

### II Python

Source code is in `py` directory. The back-end needs python3.8, the installation is quite classical as there is
a `requirements.txt`.

    ecotaxa_back/py$ python3.8  
    Python 3.8.0 (default, Dec 9 2021, 17:53:27)  
    quit()
    
    ecotaxa_back/py$ python3.8 -m venv myvenv
    
    ecotaxa_back/py$ source myvenv/bin/activate

The pip and wheel upgrade might be needed depending on your python, but it doesn't hurt.

    (myvenv) ecotaxa_back/py$ pip3 install --upgrade pip wheel
    ...
    Successfully installed pip-22.0.4 wheel-0.37.1

Of course the packages and version numbers below are for illustration.

    (myvenv) ecotaxa_back/py$ pip3 install -r requirements.txt
    ...
    Successfully installed Mako-1.2.0 MarkupSafe-2.1.1 Pillow-8.1.0 SQLAlchemy-1.4.31 aiofiles-0.7.0 alembic-1.7.5
    anyio-3.5.0 asgiref-3.5.0 astral-2.2 certifi-2021.10.8 charset-normalizer-2.0.12 click-8.1.2 colorama-0.4.4
    et-xmlfile-1.1.0 fastapi-0.73.0 fastapi-utils-0.2.1 greenlet-1.1.2 gunicorn-20.1.0 h11-0.12.0 httpcore-0.13.7
    httptools-0.2.0 httpx-0.18.1 idna-3.3 importlib-metadata-4.11.3 importlib-resources-5.7.1 itsdangerous-2.0.1
    jinja2-3.0.1 joblib-1.1.0 lxml-4.6.3 lxml-stubs-0.2.0 mypy-0.940 mypy-extensions-0.4.3 numpy-1.19.5 openpyxl-3.0.9
    openpyxl-stubs-0.1.21 orjson-3.6.6 passlib-1.7.4 psycopg2-binary-2.9.3 pydantic-1.9.0 python-multipart-0.0.5 pytz-2021.1
    requests-2.26.0 rfc3986-1.5.0 scikit-learn-1.0 scipy-1.8.0 shellingham-1.4.0 six-1.16.0 sniffio-1.2.0
    sqlalchemy2-stubs-0.0.2a22 sqlalchemy_views-0.3.1 starlette-0.17.1 threadpoolctl-3.1.0 tomli-2.0.1 typer-0.4.0
    types-orjson-3.6.2 types-pytz-2021.1.2 types-requests-2.25.6 typing-extensions-4.2.0 urllib3-1.26.9 uvicorn-0.17.4
    uvloop-0.16.0 zipp-3.8.0

### III Configuration

The configuration file is named `config.ini` and is a customized version of `config.ini.template`.

Important entries, at this stage, might look like:

    [default]
    
    [conf]
    # DB connectivity, the user must be able to read/write every PG object there
    DB_USER = postgres
    DB_PASSWORD = mysecretpassword
    DB_HOST = localhost
    DB_PORT = 5432
    DB_DATABASE = ecotaxa
    # Read-only user, to same or other DB, the user must be able to read tables there
    ;RO_DB_USER = readerole
    ;RO_DB_PASSWORD = xxxxxxxx
    ;RO_DB_HOST = localhost
    ;RO_DB_PORT = 5435
    ;RO_DB_DATABASE = ecotaxa4
    
    ...

    my_dir = ..
    # Where all images are stored. r/w by the back-end.
    VAULT_DIR = %(my_dir)s/vault
    # One subdirectory here per job. r/w by the back-end.
    JOBS_DIR = %(my_dir)s/temptask
    # The directory where files can be read by everyone. ro by the back-end.
    SERVERLOADAREA = %(my_dir)s/srv_fics
    # Sub-directory of previous (or not), for exports. r/w by the back-end.
    FTPEXPORTAREA = %(my_dir)s/ftp
    # CNN models. ro by the back-end.
    MODELSAREA = %(my_dir)s/models

Naturally, the pointed-at directories must exist.

### IV Initial DB build

This command will create an empty database:

    (myvenv) ecotaxa_back/py$ PYTHONPATH=. python cmds/manage.py db create --password mysecretpassword --db-name ecotaxa
    ...

**Note**: The command does not read the config.ini for rights. Creating a DB might be different, from rights point of
view, than using it R/W. Still the `--db-name` option needs to be equal to the config.ini `DB_DATABASE` entry.

Next command will build DB tables, this time using the rights from .ini:

    (myvenv) ecotaxa_back/py$ PYTHONPATH=. python cmds/manage.py db build
    Creating role 'Application Administrator'
    Creating role 'Users Administrator'
    Creating role 'Project creator'
    ...
    Adding country 'South Africa'
    Adding country 'Zambia'
    Adding country 'Zimbabwe'

### V Launch & check

The development server is on uvicorn and launches with command:

    (myvenv) ecotaxa_back/py$ python run.py uvicorn  
    ...  
    INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)  
    INFO:     Started reloader process [29028] using statreload  
    INFO:     Started server process [29030]  
    INFO:     Waiting for application startup.  
    INFO:     Application startup complete.  
    ...  

It can be checked that the server is OK by issuing an unauthenticated API call:

    curl localhost:8000/constants

For more complex operations, some python is needed, e.g. EcoTaxa front-end (https://github.com/ecotaxa/ecotaxa).

PS: _The_ created Administrator login is in `manage.py` source code.