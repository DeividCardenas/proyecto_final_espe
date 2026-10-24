"""KPIs y agregaciones estadísticas servidas desde la capa Gold (DuckDB OLAP)."""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from starlette.concurrency import run_in_threadpool

from app.schemas.spatial import CrashFilters, crash_filters
from app.services.olap import duckdb_engine

router = APIRouter()


def _where(f: CrashFilters) -> tuple[str, list]:
    clauses = ["longitude BETWEEN ? AND ?", "latitude BETWEEN ? AND ?"]
    params: list = [f.min_lon, f.max_lon, f.min_lat, f.max_lat]
    if f.start_date:
        clauses.append("crash_date >= ?")
        params.append(f.start_date)
    if f.end_date:
        clauses.append("crash_date < ?::DATE + 1")
        params.append(f.end_date)
    if f.hour_from > 0 or f.hour_to < 23:
        clauses.append("crash_hour BETWEEN ? AND ?")
        params += [f.hour_from, f.hour_to]
    if f.severity:
        clauses.append(f"severity IN ({', '.join('?' for _ in f.severity)})")
        params += f.severity
    if f.workzone_only:
        clauses.append("active_workzone")
    return " AND ".join(clauses), params


async def _q(sql: str, params: list) -> list[dict]:
    try:
        return await run_in_threadpool(duckdb_engine.query, sql, params)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Capa Gold (DuckDB) no disponible: ejecute el pipeline ETL")


@router.get("/kpis", summary="Métricas consolidadas de siniestralidad")
async def kpis(f: CrashFilters = Depends(crash_filters)) -> dict:
    where, params = _where(f)
    rows = await _q(f"""
        SELECT count(*) AS total_crashes,
               sum(injuries_total) AS total_injuries,
               sum(injuries_fatal) AS fatalities,
               sum(injuries_incapacitating) AS incapacitating,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical_crashes,
               avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END) AS critical_rate,
               sum(CASE WHEN active_workzone THEN 1 ELSE 0 END) AS workzone_crashes,
               min(crash_date) AS first_date, max(crash_date) AS last_date
        FROM gold_crash_facts WHERE {where}
    """, params)
    k = rows[0]
    # Variación interanual: últimos 365 días frente a los 365 anteriores dentro del filtro
    trend = await _q(f"""
        WITH m AS (SELECT max(crash_date) AS mx FROM gold_crash_facts WHERE {where})
        SELECT sum(CASE WHEN crash_date > mx - INTERVAL 365 DAY THEN 1 ELSE 0 END) AS last_year,
               sum(CASE WHEN crash_date <= mx - INTERVAL 365 DAY AND crash_date > mx - INTERVAL 730 DAY
                        THEN 1 ELSE 0 END) AS prev_year
        FROM gold_crash_facts, m WHERE {where}
    """, params + params)
    t = trend[0]
    k["yoy_change"] = (round((t["last_year"] - t["prev_year"]) / t["prev_year"], 4)
                       if t["prev_year"] else None)
    hot = await _q(f"""
        SELECT count(*) AS n FROM (
            SELECT grid_x, grid_y FROM gold_crash_facts WHERE {where}
            GROUP BY grid_x, grid_y
            HAVING count(*) >= 30 AND avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END) >= 0.03
        )
    """, params)
    k["high_risk_cells"] = hot[0]["n"]
    return k


@router.get("/hourly-distribution", summary="Siniestros por hora del día")
async def hourly(f: CrashFilters = Depends(crash_filters)) -> list[dict]:
    where, params = _where(f)
    return await _q(f"""
        SELECT crash_hour AS hour, count(*) AS crashes,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical
        FROM gold_crash_facts WHERE {where} GROUP BY 1 ORDER BY 1
    """, params)


@router.get("/weather-impact", summary="Siniestros y tasa crítica por condición climática")
async def weather(f: CrashFilters = Depends(crash_filters)) -> list[dict]:
    where, params = _where(f)
    return await _q(f"""
        SELECT coalesce(weather_condition, 'UNKNOWN') AS weather, count(*) AS crashes,
               round(avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END), 4) AS critical_rate
        FROM gold_crash_facts WHERE {where} GROUP BY 1 ORDER BY crashes DESC
    """, params)


@router.get("/monthly-trend", summary="Serie mensual de siniestros")
async def monthly(f: CrashFilters = Depends(crash_filters)) -> list[dict]:
    where, params = _where(f)
    return await _q(f"""
        SELECT strftime(date_trunc('month', crash_date), '%Y-%m') AS month, count(*) AS crashes,
               sum(CASE WHEN severity = 2 THEN 1 ELSE 0 END) AS critical, sum(injuries_fatal) AS fatalities
        FROM gold_crash_facts WHERE {where} GROUP BY 1 ORDER BY 1
    """, params)


@router.get("/top-causes", summary="Causas contributivas principales")
async def causes(f: CrashFilters = Depends(crash_filters), limit: int = Query(10, ge=1, le=40)) -> list[dict]:
    where, params = _where(f)
    return await _q(f"""
        SELECT coalesce(prim_contributory_cause, 'UNKNOWN') AS cause, count(*) AS crashes,
               round(avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END), 4) AS critical_rate
        FROM gold_crash_facts WHERE {where} GROUP BY 1 ORDER BY crashes DESC LIMIT ?
    """, params + [limit])


@router.get("/aadt-severity", summary="Volumen de tráfico AADT frente a severidad (deciles)")
async def aadt_severity(f: CrashFilters = Depends(crash_filters)) -> list[dict]:
    where, params = _where(f)
    return await _q(f"""
        WITH b AS (
            SELECT aadt_volume, severity, ntile(10) OVER (ORDER BY aadt_volume) AS decile
            FROM gold_crash_facts WHERE {where} AND NOT coalesce(aadt_imputed, true)
        )
        SELECT decile, round(avg(aadt_volume)) AS mean_aadt, count(*) AS crashes,
               round(avg(CASE WHEN severity = 2 THEN 1.0 ELSE 0.0 END), 4) AS critical_rate,
               round(avg(severity), 4) AS mean_severity
        FROM b GROUP BY decile ORDER BY decile
    """, params)
