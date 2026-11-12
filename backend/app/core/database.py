"""Motores de base de datos (patrón Dual-Engine).

* ``engine`` / ``SessionLocal``: SQLAlchemy síncrono sobre psycopg3 (Alembic, ETL, ML).
* ``init_db_pool`` / ``get_pool``: pool asyncpg nativo para la API FastAPI.
"""
from __future__ import annotations

import asyncio
import logging
import os
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import asyncpg
import psycopg
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.core.config import settings
from app.core.errors import ServiceUnavailableError

logger = logging.getLogger("app.database")

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
# Tiempo máximo esperando una conexión libre del pool: si se agota (p. ej. varias
# exportaciones lentas a la vez), la petición falla rápido con 503 en lugar de colgarse.
POOL_ACQUIRE_TIMEOUT_S = float(os.getenv("DB_ACQUIRE_TIMEOUT", "5"))
COMMAND_TIMEOUT_S = float(os.getenv("DB_COMMAND_TIMEOUT", "30"))

_pool: asyncpg.Pool | None = None
_pool_lock = asyncio.Lock()


async def init_db_pool() -> asyncpg.Pool:
    """Crea el pool (idempotente). Lanza la excepción de conexión si la BD no responde."""
    global _pool
    async with _pool_lock:
        if _pool is None:
            _pool = await asyncpg.create_pool(
                dsn=settings.asyncpg_dsn,
                min_size=settings.DB_POOL_MIN,
                max_size=settings.DB_POOL_MAX,
                command_timeout=COMMAND_TIMEOUT_S,
                timeout=POOL_ACQUIRE_TIMEOUT_S,  # timeout de conexión de cada socket nuevo
            )
    return _pool


async def close_db_pool() -> None:
    global _pool
    if _pool is not None:
        await _pool.close()
        _pool = None


def get_pool() -> asyncpg.Pool:
    if _pool is None:
        raise ServiceUnavailableError("Base de datos espacial no disponible (pool sin inicializar)")
    return _pool


async def ensure_pool() -> asyncpg.Pool:
    """Pool listo para usar; si la BD no estaba disponible al arrancar, reintenta ahora."""
    if _pool is not None:
        return _pool
    try:
        return await init_db_pool()
    except Exception as exc:  # BD caída, DNS, credenciales...
        logger.warning("No se pudo conectar a PostgreSQL: %s", exc)
        raise ServiceUnavailableError("Base de datos espacial no disponible temporalmente") from exc


@asynccontextmanager
async def connection(timeout: float | None = None) -> AsyncIterator[asyncpg.Connection]:
    """Conexión del pool con espera acotada.

    * Pool sin inicializar: se intenta crear (la API arranca aunque la BD no esté lista).
    * Pool agotado durante más de ``timeout`` segundos: ``ServiceUnavailableError`` (503).
    """
    pool = await ensure_pool()
    try:
        conn = await pool.acquire(timeout=POOL_ACQUIRE_TIMEOUT_S if timeout is None else timeout)
    except asyncio.TimeoutError as exc:
        raise ServiceUnavailableError("Servidor ocupado: no hay conexiones libres a la base de datos") from exc
    try:
        yield conn
    finally:
        await pool.release(conn)
