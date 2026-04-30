import re
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config
from sqlalchemy import pool

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.

config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
assert config.config_file_name
fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
from DB.Project import Project

target_metadata = Project.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


from cmds.db_upg.db_conn import conn  # type: ignore

config.set_main_option("sqlalchemy.url", str(conn.url))


def include_object(obj, name, type_, reflected, compare_to):
    is_partition_suffix = re.compile(r"_(default|\d+(_\d+)*)$")
    partitioned_bases = ("obj_head", "obj_field")

    def is_partition(table_name):
        return table_name.startswith(partitioned_bases) and is_partition_suffix.search(
            table_name
        )

    if type_ == "table":
        return not is_partition(name)

    if type_ == "foreign_key_constraint":
        if is_partition(obj.table.name):
            return False
        try:
            referred_table = obj.referred_table.name
            if is_partition(referred_table):
                return False
        except AttributeError:
            pass

    if type_ in ("index", "unique_constraint"):
        if is_partition(obj.table.name):
            return False

    return True


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        transaction_per_migration=True,
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            transaction_per_migration=True,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
