## 2026-09-12T14:15:13Z
Your working directory is: c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\worker_2\
Read the original user request at: c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\ORIGINAL_REQUEST.md

You are Worker 2 (Lead Technical Architect & Implementation Refiner).

INPUTS TO READ:
1. Target master plan to refine: c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md
2. Remediation Strategy Report: c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\explorer_remediation\report.md
3. Challenger 1 report: c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\challenger_1\report.md
4. Challenger 2 report: c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\challenger_2\report.md

TASK:
Apply the 16 exact, drop-in technical remediations formulated by `explorer_remediation` to:
`c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md`

SUMMARY OF KEY MODIFICATIONS:
1. Section 2.3: Wrap SQL `json_agg` query inside a CTE/subquery `(SELECT ... LIMIT 5000) AS sub` before `json_agg` so LIMIT actually restricts rows before aggregation, eradicating PostgreSQL OOM risks.
2. Section 4.2: In `backend/Dockerfile` runner stage, add `RUN mkdir -p /data/duckdb && chown -R appuser:appgroup /data/duckdb` before `USER appuser` to prevent DuckDB PermissionError (Errno 13).
3. Section 4.1, 4.2 & Phase 4/6: In FastAPI lifespan, make `chicago_risk_xgboost.joblib` loading resilient: if model file does not exist, log warning and set fallback heuristic score so healthchecks pass on first boot before Phase 3 training.
4. Section 4.2 & Phase 4: Add `backend/entrypoint.sh` with `alembic upgrade head && exec "$@"` and update Dockerfile ENTRYPOINT/CMD so migrations run automatically on container startup.
5. Section 4.5: Remove `-c shared_preload_libraries=postgis-3` from `docker-compose.yml`.
6. Section 3.1: Add `scipy==1.15.2` in `requirements.txt`.
7. Phase 2 (Spatial Enrichment): Add functional index recommendations for `ST_Transform(geom, 3435)` to accelerate spatial buffer joins.
8. Section 2.6 & Phase 5: In `useMapLibre.ts`, add `isMounted` ref guard inside `map.on('load')` to prevent async race condition during React 18 StrictMode unmount/mount.
9. Section 2.6 & Phase 5: In `useMapLibre.ts`, add `webglcontextlost` (with `e.preventDefault()`) and `webglcontextrestored` event listeners.
10. Section 2.6 & Phase 5: Add `maplibregl.supported()` hardware check.
11. Section 4.4: In Nginx CSP, expand `connect-src` to include `https://*.openstreetmap.org` and `https://demotiles.maplibre.org`.
12. Phase 2: In `data_cleaner.py`, calibrate Chicago BBOX to municipal boundaries (`41.644` to `42.023` N, `-87.940` to `-87.524` W).
13. Phase 5: Add `@types/react@18.3.10` and `@types/react-dom@18.3.0` to npm devDependencies and CLI install command.
14. Section 3.2 & Section 7.1: Add `vitest`, `@testing-library/react` and `"test": "vitest run"` script to `package.json`.
15. Section 2.6: Decouple Zustand store to keep only serializable state.
16. Phase 5: Recharts `<ResponsiveContainer minWidth={0}>` dimension collapse guard.

WRITE OWNERSHIP:
You have exclusive write ownership of `c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md` and `.agents/worker_2/`.
