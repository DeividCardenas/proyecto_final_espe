"""Definición única de la variable objetivo de severidad (target ordinal 0/1/2).

* 0 Bajo:      sin lesiones y daños materiales <= $1,500.
* 1 Moderado:  lesiones leves / posibles, o daños > $1,500 sin lesiones graves.
* 2 Crítico:   lesiones incapacitantes o fatalidades.
"""

SEVERITY_LABELS = {0: "Bajo", 1: "Moderado", 2: "Crítico"}

SEVERITY_SQL = """
CASE
    WHEN coalesce(injuries_fatal, 0) > 0 OR coalesce(injuries_incapacitating, 0) > 0 THEN 2
    WHEN coalesce(injuries_non_incapacitating, 0) > 0
      OR coalesce(injuries_reported_not_evident, 0) > 0
      OR damage = 'OVER $1,500' THEN 1
    ELSE 0
END
"""

# Celda de rejilla de 500 m en EPSG:3435 (pies de topógrafo)
GRID_SIZE_FT = 1640.42
