"""Parámetros espaciales/temporales compartidos y su traducción a SQL parametrizado."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from fastapi import HTTPException, Query


# Caja metropolitana holgada (misma que maxBounds del mapa)
METRO_BOUNDS = {"min_lon": -88.10, "max_lon": -87.40, "min_lat": 41.60, "max_lat": 42.10}


@dataclass
class CrashFilters:
    min_lon: float = METRO_BOUNDS["min_lon"]
    min_lat: float = METRO_BOUNDS["min_lat"]
    max_lon: float = METRO_BOUNDS["max_lon"]
    max_lat: float = METRO_BOUNDS["max_lat"]
    start_date: date | None = None
    end_date: date | None = None
    severity: list[int] = field(default_factory=list)
    hour_from: int = 0
    hour_to: int = 23
    workzone_only: bool = False

    def where(self, alias: str = "c", start_index: int = 1) -> tuple[str, list]:
        """Devuelve la cláusula WHERE con placeholders asyncpg ($1, $2...)."""
        a = alias
        params: list = [self.min_lon, self.min_lat, self.max_lon, self.max_lat]
        i = start_index
        clauses = [f"ST_Intersects({a}.geom, ST_MakeEnvelope(${i}, ${i+1}, ${i+2}, ${i+3}, 4326))"]
        i += 4
        if self.start_date:
            clauses.append(f"{a}.crash_date >= ${i}")
            params.append(self.start_date)
            i += 1
        if self.end_date:
            clauses.append(f"{a}.crash_date < (${i}::date + 1)")
            params.append(self.end_date)
            i += 1
        if self.hour_from > 0 or self.hour_to < 23:
            clauses.append(f"{a}.crash_hour BETWEEN ${i} AND ${i+1}")
            params += [self.hour_from, self.hour_to]
            i += 2
        if self.severity:
            clauses.append(f"{a}.severity = ANY(${i}::int[])")
            params.append(self.severity)
            i += 1
        if self.workzone_only:
            clauses.append(f"{a}.active_workzone")
        return " AND ".join(clauses), params


def crash_filters(
    min_lon: float = Query(METRO_BOUNDS["min_lon"], ge=-180, le=180),
    min_lat: float = Query(METRO_BOUNDS["min_lat"], ge=-90, le=90),
    max_lon: float = Query(METRO_BOUNDS["max_lon"], ge=-180, le=180),
    max_lat: float = Query(METRO_BOUNDS["max_lat"], ge=-90, le=90),
    start_date: date | None = Query(None, description="Fecha inicial (incluida) YYYY-MM-DD"),
    end_date: date | None = Query(None, description="Fecha final (incluida) YYYY-MM-DD"),
    severity: list[int] = Query([], description="Clases de severidad 0, 1, 2 (repetible)"),
    hour_from: int = Query(0, ge=0, le=23),
    hour_to: int = Query(23, ge=0, le=23),
    workzone_only: bool = Query(False),
) -> CrashFilters:
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="BBOX inválido: min debe ser menor que max")
    if any(s not in (0, 1, 2) for s in severity):
        raise HTTPException(status_code=422, detail="severity sólo admite 0, 1 o 2")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date debe ser <= end_date")
    return CrashFilters(min_lon, min_lat, max_lon, max_lat, start_date, end_date, severity, hour_from, hour_to,
                        workzone_only)
