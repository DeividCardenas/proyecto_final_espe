# Chicago Road Risk: Big Data y modelado predictivo geoespacial de riesgo vial

Plataforma open source y contenerizada para analizar y predecir la severidad de los siniestros viales de la Ciudad de Chicago. Integra los datasets abiertos de siniestros, vehículos, personas, aforos vehiculares (AADT) y permisos de obra de CDOT. Los datos pasan por una arquitectura Medallion (Bronze, Silver y Gold) y se exploran en un mapa WebGL con un simulador de riesgo en vivo.

El plan de implementación por fases está en [plan_de_implementacion_fases.md](plan_de_implementacion_fases.md). Las métricas y los hallazgos del proyecto están en [docs/INFORME_RESULTADOS.md](docs/INFORME_RESULTADOS.md).

## Arquitectura

```
 Chicago Open Data (SODA API)
            │  soda_client.py: paginado, backoff exponencial, marca de agua incremental
            ▼
 BRONZE  data/raw/<dataset>/*.parquet          (Parquet + Snappy)
            │  data_cleaner.py: envolvente municipal, cuarentena, deduplicación, anonimización PII
            ▼
 SILVER  PostgreSQL 16 + PostGIS 3.4           (EPSG:4326 + EPSG:3435, GiST, CLUSTER)
            │  spatial_enrichment.py: AADT por KNN (500 m) y obras activas (buffer de 250 m)
            ▼
 GOLD    DuckDB  data/duckdb/chicago_olap.duckdb  (hechos + agregados + rejilla de riesgo ML)
            │
            ├── ML: feature_engineering.py → train.py (RF vs XGBoost, 5-fold) → .joblib
            ▼
 FastAPI (asyncpg) ── GeoJSON · MVT (ST_AsMVT) · DBSCAN · NDJSON · KPIs · /predict
            ▼
 Nginx (proxy /api, caché de teselas, CSP) ── React 18 + MapLibre GL JS (WebGL2)
```

| Servicio | Contenedor | Puerto | Imagen |
|---|---|---|---|
| Base de datos espacial | `chicago_postgis` | 5432 | `postgis/postgis:16-3.4` |
| API + ML | `chicago_fastapi` | 8000 | `python:3.11-slim-bookworm` (multi-stage) |
| Web + proxy | `chicago_frontend` | 80 | `node:20-alpine` → `nginx:1.27-alpine` |
| Trabajos ETL/ML | `etl` (perfil `jobs`) | — | misma imagen del backend |

## Puesta en marcha

Requisitos: Docker Desktop (o Docker Engine con Compose v2) y unos 6 GB de RAM libres.

```bash
cp .env.example .env
```

```bash
docker compose up -d db
```

```bash
docker compose run --rm etl python -m app.services.etl.pipeline --since 2023-01-01
```

```bash
docker compose run --rm etl sh -c "python -m app.ml.feature_engineering && python -m app.ml.train && python -m app.ml.segment_model"
```

```bash
docker compose up -d --build
```

Después de eso:

* Aplicación web: http://localhost
* Documentación de la API (Swagger): http://localhost:8000/docs (ReDoc en `/redoc`)
* Salud: http://localhost/health y http://localhost/api/v1/health

`docker compose run --rm etl ...` monta el código del repositorio en vivo y ejecuta `alembic upgrade head` antes de cada comando, así que el esquema siempre está al día. La primera carga desde 2023 descarga unos 2,6 millones de filas y en un equipo doméstico tarda alrededor de 10 minutos.

### Pasos individuales del pipeline

```bash
docker compose run --rm etl python -m app.services.etl.soda_client --dataset crashes --since 2023-01-01
```

```bash
docker compose run --rm etl python -m app.services.etl.soda_client --dataset crashes --incremental
```

```bash
docker compose run --rm etl python -m app.services.etl.data_cleaner --verify-integrity
```

```bash
docker compose run --rm etl python -m app.services.etl.spatial_enrichment --buffer-meters 250
```

```bash
docker compose run --rm etl python -m app.services.olap.duckdb_engine --export
```

Los datasets disponibles para `--dataset` son `crashes`, `vehicles`, `people`, `aadt`, `permits` y `all`. Cada paso deja sus métricas en `data/processed/quality_report.json`.

## Pruebas

```bash
docker compose run --rm etl pytest -q -p no:cacheprovider tests
```

```bash
docker compose run --rm etl python tests/load_test.py --base http://frontend --requests 500 --concurrency 50
```

```bash
cd frontend && npm ci && npm run typecheck && npm test
```

* **Backend (pytest, 25 pruebas):** sonda de salud, OpenAPI y CORS; BBOX exacto por debajo de 100 ms; uso del índice GiST; ausencia de índices duplicados; integridad referencial; precisión métrica del buffer de 250 m en EPSG:3435; cuarentena y deduplicación; contrato y validación 422 de `/predict`; tamaño y latencia del modelo.
* **Frontend (Vitest, 18 pruebas):** ciclo de vida de `useMapLibre` (StrictMode, `map.remove()`, pérdida y restauración del contexto WebGL, ausencia de WebGL2); la tabla virtualizada renderiza 40 filas o menos de 10.000; expresiones de filtro GPU; exportación CSV; tasas sin filtros de composición; temas; filtros plegados al entrar; guía de uso (invitación de primera visita y recorrido).

## Guía de uso dentro de la aplicación

El menú **Ayuda** de la cabecera ofrece un recorrido completo (cada parte de la plataforma: qué hace, qué significa y cómo se hizo), la guía de la sección abierta y unos puntos de ayuda opcionales. En la primera visita sólo aparece una invitación discreta que se puede descartar. Se implementó con [Driver.js](https://driverjs.com) (MIT, sin dependencias) y el contenido está en `frontend/src/components/tour/guideContent.ts`.

## Endpoints principales (`/api/v1`)

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/health` | Estado de la base de datos, PostGIS, el modelo y DuckDB |
| GET | `/crashes/geojson` | FeatureCollection por BBOX, fechas, horas, severidad y obras (generado en SQL) |
| GET | `/tiles/crashes/{z}/{x}/{y}.pbf` | Teselas vectoriales MVT (`ST_AsMVT`), agregadas por debajo del zoom 13 |
| GET | `/crashes/clusters` | Puntos calientes con `ST_ClusterDBSCAN` (eps de 40 m) |
| GET | `/crashes/stream` | Exportación masiva NDJSON en streaming |
| GET | `/crashes/{id}` | Detalle de un siniestro con vehículos y personas anonimizadas |
| GET | `/permits/active` | Obras CDOT con cierre de calzada y su buffer métrico |
| GET | `/traffic/stations` | Estaciones de aforo AADT |
| GET | `/analytics/kpis`, `/hourly-distribution`, `/weather-impact`, `/monthly-trend`, `/top-causes`, `/aadt-severity` | Agregaciones OLAP en DuckDB |
| GET | `/risk/grid` | Rejilla de 500 m con el riesgo crítico medio predicho |
| GET | `/risk/model-metrics` | Métricas del modelo entrenado |
| GET | `/risk/segments` | Cuadras con riesgo anticipado para 12 meses, ordenadas por prioridad |
| GET | `/risk/segment-model-metrics` | Comparativa logística/RF/XGBoost con validación temporal y espacial |
| GET | `/risk/segment-explain?segment_id=` | P(riesgo Alto) de una cuadra y aporte de cada variable (log-odds frente a una cuadra típica) |
| GET | `/risk/segment-distribution` | Muestra sistemática de P(riesgo Alto) de todas las cuadras, para comparar una con el resto |
| POST | `/predict/segment-risk` | Riesgo de un tramo (Bajo, Moderado o Crítico), probabilidades y factores SHAP |

Ejemplo de predicción:

```bash
curl -X POST http://localhost/api/v1/predict/segment-risk -H "Content-Type: application/json" -d '{"coordinates": [-87.6298, 41.8781], "posted_speed_limit": 30, "weather_condition": "RAIN", "lighting_condition": "DARKNESS", "active_workzone": true}'
```

## Estado de las fases

| Fase | Contenido | Estado |
|---|---|---|
| 1 | Docker PostGIS, modelos Silver, Alembic con helpers de GeoAlchemy2 | Completa |
| 2 | Ingesta SODA, saneamiento, cuarentena, enriquecimiento AADT y obras, CLUSTER, DuckDB | Completa (Quality Gate aprobado) |
| 3 | Modelo por siniestro (RF vs XGBoost) y modelo por tramo vial (logística/RF/XGBoost, validación temporal y espacial) | Completa (ver el informe) |
| 4 | API FastAPI asíncrona, GeoJSON, MVT, DBSCAN, NDJSON, KPIs y predicción | Completa |
| 5 | React 18 + MapLibre GL JS, capas GPU, analítica, simulador y tabla virtualizada | Completa |
| 6 | Orquestación completa, prueba de carga, auditoría y documentación | Completa |

## Estructura

```
backend/
  alembic/versions/       0001 PostGIS · 0002 tablas · 0003 enriquecimiento/PII/GiST · 0004 severidad
  app/core/               config (Pydantic Settings), database (asyncpg + psycopg3), severity
  app/services/etl/       soda_client, data_cleaner, spatial_enrichment, pipeline
  app/services/olap/      duckdb_engine (capa Gold)
  app/ml/                 feature_engineering, train, segment_model, predictor, models/*.joblib
  app/api/v1/endpoints/   health, crashes, tiles, permits, traffic, analytics, risk, predict
  tests/                  pytest + load_test.py
frontend/
  src/hooks/              useMapLibre, useSpatialFilters, useViewportCrashes, useDebounce
  src/components/map/     MapContainer, MapPopup, MapLegend, MapControls, layers/*
  src/components/         layout, analytics, simulator, table
  src/components/tour/    guía de uso con Driver.js: recorrido completo, guía por sección y puntos de ayuda
  nginx.conf              proxy /api, caché MVT, gzip_static, CSP
data/                     raw (Bronze) · processed (Silver/Gold Parquet, reportes) · duckdb
```
