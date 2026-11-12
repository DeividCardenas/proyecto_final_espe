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

    def where(self, alias: str = "c", start_index: int = 1, dialect: str = "postgis") -> tuple[str, list]:
        """Cláusula WHERE parametrizada y su lista de parámetros.

        * ``postgis``: placeholders asyncpg (``$1``, ``$2``...) sobre ``silver_crashes``;
          la ventana usa ``ST_Intersects`` para aprovechar el índice GiST.
        * ``duckdb``: placeholders ``?`` sobre ``gold_crash_facts`` (columnas lon/lat).

        Ambos dialectos comparten la misma semántica: ``end_date`` incluido, rango
        horario que puede cruzar medianoche (``hour_from=22, hour_to=3``) y severidad
        como lista de clases.
        """
        if dialect not in ("postgis", "duckdb"):
            raise ValueError(f"Dialecto no soportado: {dialect}")
        pg = dialect == "postgis"
        a = f"{alias}." if alias else ""
        counter = iter(range(start_index, 10_000))

        def ph() -> str:
            return f"${next(counter)}" if pg else "?"

        params: list = []
        clauses: list[str] = []

        def add(template: str, *values) -> None:
            clauses.append(template.format(*[ph() for _ in values]))
            params.extend(values)

        if pg:
            add(f"ST_Intersects({a}geom, ST_MakeEnvelope({{}}, {{}}, {{}}, {{}}, 4326))",
                self.min_lon, self.min_lat, self.max_lon, self.max_lat)
        else:
            add(f"{a}longitude BETWEEN {{}} AND {{}}", self.min_lon, self.max_lon)
            add(f"{a}latitude BETWEEN {{}} AND {{}}", self.min_lat, self.max_lat)
        if self.start_date:
            add(f"{a}crash_date >= {{}}", self.start_date)
        if self.end_date:
            add(f"{a}crash_date < ({{}}::date + 1)" if pg else f"{a}crash_date < {{}}::DATE + 1", self.end_date)
        if self.hour_from > 0 or self.hour_to < 23:
            if self.hour_from <= self.hour_to:
                add(f"{a}crash_hour BETWEEN {{}} AND {{}}", self.hour_from, self.hour_to)
            else:  # rango nocturno que cruza medianoche
                add(f"({a}crash_hour >= {{}} OR {a}crash_hour <= {{}})", self.hour_from, self.hour_to)
        if self.severity:
            if pg:
                add(f"{a}severity = ANY({{}}::int[])", list(self.severity))
            else:
                marks = ", ".join("{}" for _ in self.severity)
                add(f"{a}severity IN ({marks})", *self.severity)
        if self.workzone_only:
            clauses.append(f"{a}active_workzone")
        return " AND ".join(clauses), params


def crash_filters(
    min_lon: float = Query(METRO_BOUNDS["min_lon"], ge=-180, le=180),
    min_lat: float = Query(METRO_BOUNDS["min_lat"], ge=-90, le=90),
    max_lon: float = Query(METRO_BOUNDS["max_lon"], ge=-180, le=180),
    max_lat: float = Query(METRO_BOUNDS["max_lat"], ge=-90, le=90),
    start_date: date | None = Query(None, description="Fecha inicial (incluida) YYYY-MM-DD"),
    end_date: date | None = Query(None, description="Fecha final (incluida) YYYY-MM-DD"),
    severity: list[int] = Query([], max_length=3, description="Clases de severidad 0, 1, 2 (repetible)"),
    hour_from: int = Query(0, ge=0, le=23, description="Hora inicial (0-23)"),
    hour_to: int = Query(23, ge=0, le=23,
                         description="Hora final (0-23); si es menor que hour_from el rango cruza medianoche"),
    workzone_only: bool = Query(False),
) -> CrashFilters:
    if min_lon >= max_lon or min_lat >= max_lat:
        raise HTTPException(status_code=422, detail="BBOX inválido: min debe ser menor que max")
    if any(s not in (0, 1, 2) for s in severity):
        raise HTTPException(status_code=422, detail="severity sólo admite 0, 1 o 2")
    if start_date and end_date and start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date debe ser <= end_date")
    return CrashFilters(min_lon, min_lat, max_lon, max_lat, start_date, end_date, sorted(set(severity)),
                        hour_from, hour_to, workzone_only)
