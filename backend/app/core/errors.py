"""Errores de dominio y su traducción a respuestas HTTP JSON coherentes.

Toda falla de infraestructura (PostGIS caído, pool agotado, consulta que excede
el tiempo, archivo DuckDB bloqueado o ausente) se devuelve como JSON
``{"detail": ...}`` con 503/504 en lugar de un 500 genérico, y queda registrada
en el log con la ruta que la provocó.
"""
from __future__ import annotations

import asyncio
import logging

import asyncpg
import duckdb
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

logger = logging.getLogger("app.errors")


class ServiceUnavailableError(RuntimeError):
    """Una dependencia (BD, capa Gold, modelo) no está disponible en este momento."""

    status_code = 503

    def __init__(self, detail: str, retry_after: int | None = 5):
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after


class OlapUnavailableError(ServiceUnavailableError):
    """La capa Gold (DuckDB) no existe todavía o está siendo reemplazada."""


class TooManyRequestsError(RuntimeError):
    """Se superó el número de operaciones pesadas simultáneas permitidas."""

    def __init__(self, detail: str, retry_after: int = 10):
        super().__init__(detail)
        self.detail = detail
        self.retry_after = retry_after


def _json(status: int, detail: str, retry_after: int | None = None) -> JSONResponse:
    headers = {"Retry-After": str(retry_after)} if retry_after else None
    return JSONResponse(status_code=status, content={"detail": detail}, headers=headers)


def _log(request: Request, exc: BaseException, level: int = logging.WARNING) -> None:
    logger.log(level, "%s %s -> %s: %s", request.method, request.url.path, type(exc).__name__, exc)


async def _service_unavailable(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    _log(request, exc)
    return _json(exc.status_code, exc.detail, exc.retry_after)


async def _too_many(request: Request, exc: TooManyRequestsError) -> JSONResponse:
    _log(request, exc, logging.INFO)
    return _json(429, exc.detail, exc.retry_after)


async def _query_timeout(request: Request, exc: Exception) -> JSONResponse:
    _log(request, exc)
    return _json(504, "La consulta tardó demasiado; reduzca el área o el rango de fechas", 5)


async def _db_unavailable(request: Request, exc: Exception) -> JSONResponse:
    _log(request, exc)
    return _json(503, "Base de datos espacial no disponible temporalmente", 5)


async def _duckdb_io(request: Request, exc: Exception) -> JSONResponse:
    _log(request, exc)
    return _json(503, "Capa Gold (DuckDB) ocupada o no disponible; reintente en unos segundos", 5)


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(ServiceUnavailableError, _service_unavailable)
    app.add_exception_handler(TooManyRequestsError, _too_many)
    # Consulta cancelada por command_timeout (cliente) o statement_timeout (servidor).
    # El pool agotado no llega aquí: database.connection() lo convierte en ServiceUnavailableError.
    app.add_exception_handler(asyncpg.QueryCanceledError, _query_timeout)
    app.add_exception_handler(asyncio.TimeoutError, _query_timeout)
    app.add_exception_handler(asyncpg.CannotConnectNowError, _db_unavailable)
    app.add_exception_handler(asyncpg.ConnectionDoesNotExistError, _db_unavailable)
    app.add_exception_handler(asyncpg.InterfaceError, _db_unavailable)
    app.add_exception_handler(ConnectionError, _db_unavailable)
    app.add_exception_handler(duckdb.IOException, _duckdb_io)
