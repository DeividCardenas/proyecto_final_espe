from logging.config import fileConfig
from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context
from geoalchemy2 import alembic_helpers
import os

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
from app.core.config import settings
from app.core.database import Base
from app.models.silver import *  # noqa: F401,F403 - registra todos los modelos
target_metadata = Base.metadata

# La URL síncrona (psycopg3) proviene del entorno; alembic.ini sólo es fallback.
config.set_main_option(
    "sqlalchemy.url",
    os.getenv("SYNC_DATABASE_URL", settings.SYNC_DATABASE_URL).replace("%", "%%"),
)

MANAGED_TABLE_PREFIXES = ("silver_", "crashes_quarantine")


def include_object(object, name, type_, reflected, compare_to):
    # Proteger tablas de catálogo PostGIS (spatial_ref_sys, topology, tiger...)
    if type_ == "table" and not name.startswith(MANAGED_TABLE_PREFIXES):
        return False
    return alembic_helpers.include_object(object, name, type_, reflected, compare_to)


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
        process_revision_directives=alembic_helpers.writer,
        render_item=alembic_helpers.render_item,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
            process_revision_directives=alembic_helpers.writer,
            render_item=alembic_helpers.render_item,
            compare_type=True
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
