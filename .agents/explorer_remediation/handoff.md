# HANDOFF REPORT: REMEDIATION STRATEGY (ITERATION 2)

**Agente Emisor:** Remediation Explorer (Iteración 2)  
**Agente Receptor:** Worker 2 / Orchestrator Parent (`7113e5ec-e138-4537-a946-a3b08ebfac68`)  
**Fecha:** 12 de septiembre de 2026  
**Tipo de Handoff:** Hard (Tarea de Investigación y Estrategia de Remediación Completada)

---

## 1. OBSERVATION (Observaciones Empíricas Directas)

Se inspeccionó directamente el documento objetivo `plan_de_implementacion_fases.md` (1,311 líneas) y los informes de auditoría adversarial:

1. **Consulta SQL GeoJSON (Sección 2.3, Líneas 122-143):**
   ```sql
   SELECT json_build_object(
       'type', 'FeatureCollection',
       'features', COALESCE(json_agg(...), '[]'::json)
   ) AS geojson_output
   FROM silver_crashes
   WHERE geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
   LIMIT 5000;
   ```
   *Observación:* `LIMIT 5000` se aplica sobre el resultado del `SELECT`, el cual, al usar `json_agg` sin `GROUP BY`, colapsa todas las filas a exactamente 1 sola fila. La agregación procesa la totalidad de siniestros coincidentes (>850,000 tuplas si el BBOX es amplio), causando un consumo de memoria masivo y riesgo de OOM en PostgreSQL.

2. **Permisos de Volumen DuckDB en `backend/Dockerfile` (Sección 4.2, Líneas 426-435 y Sección 4.5 Línea 636):**
   *Observación:* `backend/Dockerfile` crea `appuser` (UID 10001) y hace `USER appuser`. No pre-crea `/data/duckdb`. En `docker-compose.yml`, se monta el volumen `duckdb_data:/data/duckdb`. Docker inicializa este directorio como `root:root` (0755), provocando `PermissionError: [Errno 13] Permission denied` cuando DuckDB intenta escribir `chicago_olap.duckdb`.

3. **Ciclo de Vida de FastAPI y Bloqueo de Arranque por Modelo ML Ausente (Sección 4.1 Línea 364, Sección 4.5 Línea 633, Líneas 1074 y 1198-1200):**
   *Observación:* `main.py` ejecuta `joblib.load(settings.MODEL_PATH)` en el `lifespan`. En un despliegue inicial o clonación limpia, `chicago_risk_xgboost.joblib` no existe (se entrena en la Fase 3). Uvicorn aborta con `FileNotFoundError`, el contenedor backend falla su healthcheck (`curl http://localhost:8000/api/v1/health`), y el frontend nunca inicia por la compuerta `depends_on: backend: condition: service_healthy`.

4. **Desincronización de Migraciones Alembic (Sección 4.1 Línea 363 vs Sección 4.2 Línea 441):**
   *Observación:* Sección 4.1 estipula que el backend ejecuta `alembic upgrade head`, pero el Dockerfile especifica directamente `CMD ["uvicorn", ...]`, careciendo de un script `entrypoint.sh`. En despliegues automatizados las tablas no se crean.

5. **Parámetro Inadecuado en PostgreSQL (Sección 4.5 Línea 601 y Fase 1 Línea 877):**
   *Observación:* `command: >` incluye `-c shared_preload_libraries=postgis-3`. PostGIS es una extensión de enlace dinámico (`CREATE EXTENSION postgis;`) que no debe registrarse en `shared_preload_libraries`. En PostgreSQL 16 esto puede arrojar `FATAL: could not load library "postgis-3"`.

6. **Omisión de `scipy` en `backend/requirements.txt` (Sección 3.1 Líneas 238-246):**
   *Observación:* `scikit-learn==1.6.1` y `xgboost==2.1.4` requieren `scipy`, pero no está fijado en el manifiesto.

7. **Escaneo Secuencial en Cruce Espacial (Fase 2, Líneas 958-970):**
   *Observación:* `ST_DWithin(ST_Transform(c.geom, 3435), ST_Transform(p.geom, 3435), 820.21)` envuelve la columna indexada en una función de transformación, impidiendo el uso del índice espacial GiST estándar y forzando un Sequential Scan sobre 850k registros.

8. **Carrera Asíncrona en `useMapLibre` (Sección 2.6 Líneas 174-183 y Fase 5 Líneas 1137-1140):**
   *Observación:* En React 18 StrictMode, el componente se monta, desmonta y vuelve a montar. Si `map.on('load')` se resuelve tras el desmontaje (`map.remove()`), `setMapInstance(map)` almacena una instancia destruida en Zustand, disparando `Error: Map has been removed` y fugas de memoria GPU.

9. **Omisión de Manejadores de Contexto WebGL y Verificación de Hardware (Sección 2.5 Línea 164 y Sección 2.6 Línea 181):**
   *Observación:* No existían listeners para `webglcontextlost` ni `webglcontextrestored`, ni validación de `maplibregl.supported()`, produciendo pantallas negras ante suspensión de GPU y pantalla blanca fatal ante falta de soporte WebGL2.

10. **Content Security Policy Incompleta en Nginx (Sección 4.4 Línea 517):**
    *Observación:* `connect-src` omite `https://*.openstreetmap.org` y `https://demotiles.maplibre.org`, bloqueando peticiones `fetch()` de teselas vectoriales y estilos.

11. **Discrepancia en BBOX de Limpieza (Fase 2 Línea 947):**
    *Observación:* El rango `[-88.10, 41.60]` a `[-87.40, 42.10]` abarca 13.5 km fuera de los límites de Chicago, aceptando incidentes de DuPage County y del Lago Michigan.

12. **Omisiones en Herramientas de Node (Sección 3.2 Líneas 264-308 y Fase 5 Línea 1167):**
    *Observación:* El comando CLI de Fase 5 omitió `@types/react` y `@types/react-dom`; `package.json` carece de runner de testing (`vitest`, `@testing-library/react`) y del script `"test"`.

---

## 2. LOGIC CHAIN (Cadena Lógica de Razonamiento)

1. **Premisa 1 (SQL):** Una consulta `SELECT agg_func(...) ... LIMIT N` evalúa el `LIMIT` sobre la fila singular resultante de la agregación, no sobre las filas de entrada de la tabla base.  
   *Inferencia 1:* La única forma matemáticamente rigurosa de restringir la agregación de `json_agg` a 5,000 registros es filtrar y acotar mediante una CTE `WITH limited_crashes AS (SELECT ... LIMIT 5000)` o subconsulta `FROM (SELECT ... LIMIT 5000) AS sub`.

2. **Premisa 2 (Docker & Linux Permissions):** Los volúmenes montados en Docker pertenecen por defecto al creador del directorio destino en la imagen base (`root:root` si no fue creado previamente con otro usuario).  
   *Inferencia 2:* La instrucción `RUN mkdir -p /data/duckdb && chown -R appuser:appgroup /data/duckdb` antes de `USER appuser` en la etapa runner garantiza que el usuario con UID 10001 tenga permisos de lectura/escritura sobre el volumen persistente montado.

3. **Premisa 3 (Orquestación & CI/CD):** En un pipeline desacoplado, los servicios deben poder arrancar independientemente de si los artefactos de etapas posteriores ya fueron producidos.  
   *Inferencia 3:* El manejador `lifespan` de FastAPI debe verificar `os.path.exists(settings.MODEL_PATH)`; si no existe, debe registrar una advertencia y habilitar un estimador heurístico baseline, garantizando que el healthcheck responda 200 OK y no detenga la inicialización del frontend.

4. **Premisa 4 (PostgreSQL Extensions):** `shared_preload_libraries` solo es requerida por librerías que enganchan el proceso postmaster. PostGIS 3.4 se carga dinámicamente mediante `CREATE EXTENSION`.  
   *Inferencia 4:* La remoción de `-c shared_preload_libraries=postgis-3` elimina el riesgo de fallo de inicialización del cluster sin afectar en absoluto la funcionalidad de PostGIS.

5. **Premisa 5 (Ciclo de Vida React 18 & WebGL):** En React 18, `useEffect` puede ejecutarse y limpiarse en milisegundos mientras llamadas de red asíncronas siguen pendientes en el fondo.  
   *Inferencia 5:* Una bandera booleana mutable `isMounted = true` que se torna `false` en la función de retorno, combinada con `map.off('load', handleLoad)`, es la única garantía de que callbacks asíncronos tardíos no modifiquen el estado ni asignen punteros huérfanos.

6. **Premisa 6 (Geodesia y Calidad de Datos):** La limpieza de datos para análisis policial y vial de Chicago debe limitarse a su jurisdicción administrativa real.  
   *Inferencia 6:* Distinguir entre la caja de navegación de cámara (`maxBounds`) y la caja de validación administrativa ($41.644^\circ - 42.023^\circ$ N, $-87.940^\circ - -87.524^\circ$ W) preserva la calidad analítica sin degradar la experiencia de usuario.

---

## 3. CAVEATS (Salvedades y Supuestos)

1. **Entorno de Ejecución Local de DuckDB:** DuckDB opera en modo mono-proceso embebido. Si múltiples workers de Uvicorn intentan escribir concurrentemente en el mismo archivo `.duckdb`, DuckDB bloqueará las escrituras concurrentes. Se recomienda en el plan que DuckDB opere en modo de solo lectura para el backend si se escalan los workers de Uvicorn, o que las escrituras se centralicen en un proceso ETL batch.
2. **Volumetría de Descarga SODA:** La cuota pública de SODA sin token de aplicación está limitada por IP. El plan ya incluye `SOCRATA_APP_TOKEN` en `.env.example`, lo cual mitiga este riesgo si se requiere procesar el histórico completo (>850k filas).
3. **Versión de Scipy:** Se seleccionó `scipy==1.15.2` en estricto apego al mandato de la solicitud y compatibilidad con `scikit-learn==1.6.1` y `numpy<2.0.0`.

---

## 4. CONCLUSION (Conclusión y Dictamen Técnico)

La investigación adversarial y la síntesis técnica demuestran que las objeciones formuladas por **Challenger 1**, **Challenger 2** y **Reviewer 2** son **100% fundadas, críticas y reproducibles**.

Se ha formulado y documentado exhaustivamente en `report.md` la estrategia de remediación paso a paso para que **Worker 2** actualice `plan_de_implementacion_fases.md`. Una vez aplicadas estas modificaciones:
- El plan eliminará completamente los riesgos de OOM en PostgreSQL.
- Se garantizará la inicialización exitosa de DuckDB con usuario no-root.
- FastAPI podrá arrancar limpiamente en instalaciones nuevas sin fallos de healthcheck.
- El ciclo de vida de MapLibre en React 18 quedará blindado contra fugas de memoria y carreras en StrictMode.
- La política CSP de Nginx permitirá la descarga de tiles y estilos sin restricciones.

---

## 5. VERIFICATION METHOD (Método de Verificación Independiente)

Para verificar independientemente la validez técnica de la remediación:

1. **Inspección de Artefactos Producidos:**
   - Consultar `report.md` en `.agents/explorer_remediation/report.md` para revisar el texto exacto, líneas de código y antes/después de cada una de las 17 remediaciones.
2. **Verificación de Sintaxis SQL Anti-OOM en PostgreSQL:**
   ```sql
   EXPLAIN ANALYZE
   WITH limited_crashes AS (
       SELECT crash_record_id, geom, crash_date, posted_speed_limit, injuries_total, injuries_fatal, risk_score
       FROM silver_crashes
       LIMIT 5000
   )
   SELECT json_build_object('type', 'FeatureCollection', 'features', json_agg(crash_record_id))
   FROM limited_crashes;
   ```
   *Condición de Validación:* El planificador debe mostrar un nodo `Limit (cost=... rows=5000)` como hijo directo del `Aggregate`, confirmando que solo 5,000 tuplas entran a memoria.
3. **Verificación de Permisos Docker DuckDB:**
   Verificar que en la imagen construida:
   `docker run --rm <image_backend> ls -ld /data/duckdb` reporte propietario `appuser:appgroup` (10001:10001).
4. **Verificación de Tipos TypeScript y Pruebas Frontend:**
   `npm run typecheck` (`tsc --noEmit`) y `npm test` (`vitest run`) deben ejecutar sin errores.
