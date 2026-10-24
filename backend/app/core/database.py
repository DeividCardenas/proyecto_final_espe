"""Motores de base de datos (patrón Dual-Engine).

* ``engine`` / ``SessionLocal``: SQLAlchemy síncrono sobre psycopg3 (Alembic, ETL, ML).
* ``init_db_pool`` / ``get_pool``: pool asyncpg nativo para la API FastAPI.
"""
from __future__ import annotations

import asyncpg
import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings

engine = create_engine(settings.SYNC_DATABASE_URL, echo=False, future=True, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def raw_connection(autocommit: bool = False) -> psycopg.Connection:
    """Conexión psycopg3 directa, usada por el ETL para COPY masivo."""
    return psycopg.connect(settings.psycopg_dsn, autocommit=autocommit)


# ------------------------------------------------------------------------------
# Pool asíncrono asyncpg (API)
# ------------------------------------------------------------------------------
_pool: asyncpg.Pool | None = None


async def init_db_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(
            dsn=settings.asyncpg_dsn,
            min_size=settings.DB_POOL_MIN,
            max_size=settings.DB_POOL_MAX,
            command_timeout=30,
        )
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise RuntimeError("El pool de asyncpg no ha sido inicializado")
    return _pool
