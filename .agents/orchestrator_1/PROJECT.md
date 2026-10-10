# Project: Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales y Movilidad Urbana

## Architecture Overview
A full-stack, containerized open-source Big Data & Geospatial analytics platform designed for the City of Chicago road safety datasets (>4.5M records across Crashes, Vehicles, People, Traffic Counts, and Road Closure Permits).
- **Architecture Pattern**: Medallion Data Architecture (Bronze -> Silver -> Gold)
- **Database / GIS**: PostgreSQL 16 + PostGIS 3.4 (WGS84 EPSG:4326 storage, Illinois State Plane East EPSG:3435 metric projections, GiST indexes, functional indexes, Table Clustering)
- **Data Engineering / OLAP**: Python 3.11, SODA API, DuckDB in-memory OLAP & Apache Parquet for accelerated analytical queries
- **Backend API**: FastAPI (asyncpg for high-concurrency async REST API, psycopg3 for Alembic & ETL), GeoAlchemy2 0.17.1, SQLAlchemy 2.0.38, Pydantic v2, Alembic with geoalchemy2 helpers, automated migrations via entrypoint.sh, resilient lifespan model fallback
- **Machine Learning**: Scikit-Learn, XGBoost, Random Forest, Scipy 1.15.2, Joblib serialization (target: AUC-ROC >= 0.70, Recall >= 0.60, Precision >= 0.65)
- **Frontend & GIS Visualization**: React 18.3.1, TypeScript 5.6.2, Vite 5.4.6, MapLibre GL JS v4 (WebGL2 hardware acceleration, custom useMapLibre hook with isMounted guard and WebGL context loss recovery, MapContext decoupling, Vitest suite, 3-tier data rendering: GeoJSON / Supercluster / MVT Vector Tiles, GPU-level map.setFilter() expressions)
- **Containerization**: Multi-service Docker & Docker Compose (postgis/postgis:16-3.4, python:3.11-slim-bookworm backend with pre-provisioned DuckDB volume permissions, node:20-alpine -> nginx:1.27-alpine multi-stage frontend with expanded CSP and reverse proxy to /api/)

## Milestones & Sprints
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M0 | Survey & Architecture Validation | In-depth exploration of docx, backend, frontend, dependencies | none | DONE |
| M1 | Master Implementation Plan Drafting | Authoring plan_de_implementacion_fases.md in workspace root | M0 | DONE |
| M2 | Review, Challenge & Audit Gating | Independent reviews, adversarial tests, and forensic audit | M1 | DONE (PASS) |
| M3 | Project Handoff to Sentinel | Final synthesis, packaging, and report to Sentinel | M2 | IN_PROGRESS |

## Primary Deliverable
- Target deliverable: `c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md`
- Size: 103,556 bytes, 1,511 lines.
- Status: Fully audited, verified, and APPROVED by 2 Reviewers, 2 Challengers, and Forensic Auditor (CLEAN).
