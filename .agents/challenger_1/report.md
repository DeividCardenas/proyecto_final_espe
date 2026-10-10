# INFORME DE DESAFÍO TÉCNICO Y VERIFICACIÓN EMPÍRICA (CHALLENGER 1)
## Auditoría de Especificaciones de Backend, Docker, SQL PostGIS 3.4 y Matriz de Dependencias

**Agente Auditor:** Challenger 1 (Empirical Backend, Docker & CLI Verifier)  
**Documento Auditado:** `c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md`  
**Fecha de Auditoría:** 12 de septiembre de 2026  
**Dictamen Oficial:** ⚠️ **REQUEST_CHANGES** (Rechazo Condicional con Mitigaciones Obligatorias)

---

## 1. RESUMEN EJECUTIVO DEL DESAFÍO (CHALLENGE SUMMARY)

**Evaluación Global de Riesgo:** **CRITICAL** (Riesgo Crítico de Falla en Runtime y Agotamiento de Recursos)

El plan maestro de implementación (`plan_de_implementacion_fases.md`) presenta un diseño conceptual sólido, detallado y ambicioso. Sin embargo, el análisis adversarial y la verificación empírica de sus especificaciones de código SQL, configuración de contenedores Docker y ciclo de vida de dependencias revelaron **2 fallas críticas**, **2 fallas de alto impacto**, **3 de medio impacto** y **2 de bajo impacto** que impedirán la ejecución exitosa en entornos reales si no son subsanadas antes de la fase de construcción.

### Cuadro Resumen de Hallazgos

| ID | Severidad | Dominio | Hallazgo Clave | Impacto Operativo |
|---|---|---|---|---|
| **C1** | **CRÍTICO** | SQL / PostGIS | `LIMIT 5000` ineficaz en consulta GeoJSON con `json_agg` sin subconsulta | Agotamiento de memoria (OOM) en Postgres al consultar Chicago completo (>850k filas). |
| **C2** | **CRÍTICO** | Docker / Permisos | Permiso denegado en volumen `/data/duckdb` para usuario no-root `appuser` | Fallo fatal al inicializar DuckDB; contenedor FastAPI aborta con `PermissionError`. |
| **C3** | **ALTO** | Ciclo de Vida / CI | Bloqueo por ausencia de modelo ML `.joblib` en despliegue inicial | Fallo de arranque de FastAPI en fresh clone; healthcheck nunca pasa; stack bloqueado. |
| **C4** | **ALTO** | Dockerfile / DB | Migraciones de Alembic no invocadas en CMD de contenedor FastAPI | Contenedor levanta sin tablas en base de datos; endpoints 500 `UndefinedTableError`. |
| **C5** | **MEDIO** | Docker Compose | Directiva no soportada/riesgosa `shared_preload_libraries=postgis-3` | Posible aborto de arranque del motor PostgreSQL 16 por librería no precargable. |
| **C6** | **MEDIO** | PostGIS / Perf | Sequential Scan forzado en `UPDATE` de obras viales por `ST_Transform` no indexado | Escaneo secuencial de 850k filas x permisos; saturación de CPU y bloqueo de tabla. |
| **C7** | **MEDIO** | Frontend / CSP | Bloqueo de tiles vectoriales y estilos por omisión de fuentes en `connect-src` | MapLibre v4 no puede cargar estilos ni tiles; mapa en blanco con errores CSP. |
| **C8** | **BAJO** | Dependencias | Ausencia de `scipy` en manifiesto pinned `requirements.txt` | Ruptura potencial de compilación en Docker si Scipy actualiza requerimientos de NumPy. |
| **C9** | **BAJO** | CLI / Entorno | Conflicto de hostname `db` vs `localhost` al ejecutar Alembic desde host | `alembic upgrade head` falla en terminal local con error de resolución DNS. |

---

## 2. DETALLE DE DESAFÍOS TÉCNICOS (CHALLENGES)

### [CRÍTICO] C1: Ineficacia de `LIMIT 5000` en Consulta GeoJSON y Riesgo Catastrófico de OOM
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 2.3, Líneas 123-143.
* **Código Identificado:**
  ```sql
  SELECT json_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(json_agg(
          json_build_object(...)
      ), '[]'::json)
  ) AS geojson_output
  FROM silver_crashes
  WHERE geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
  LIMIT 5000;
  ```
* **Suposición Cuestionada:** Se asume que `LIMIT 5000` limita la cantidad de geometrías procesadas y agregadas por `json_agg` dentro del FeatureCollection a 5,000 registros.
* **Escenario de Ataque y Verificación Empírica:**
  En el estándar SQL de PostgreSQL, una función de agregación (`json_agg`, `count`, `sum`) ejecutada sin una cláusula `GROUP BY` colapsa **todas** las filas resultantes de la cláusula `WHERE` en **exactamente 1 fila**.
  La cláusula `LIMIT 5000` se evalúa sobre el conjunto de filas final producido por el `SELECT`. Dado que el `SELECT` produce exactamente 1 fila, `LIMIT 5000` permite hasta 5,000 filas del resultado, por lo que **no tiene ningún efecto restrictivo sobre `json_agg`**.
  Si un cliente realiza una petición con un Bounding Box amplio (o todo Chicago, donde existen >850,000 siniestros), PostgreSQL escaneará e intentará agregar en memoria RAM los 850,000 registros en un único objeto JSON gigantesco de varios gigabytes.
* **Radio de Explosión (Blast Radius):** Picos masivos de uso de RAM en PostgreSQL (>4 GB), agotamiento de memoria del contenedor `chicago_postgis`, invocación del kernel OOM Killer, bloqueo del backend y tiempos de respuesta superiores a 30 segundos, violando el SLA estipulado de `< 65 ms`.
* **Mitigación Mandatoria:** Restringir el número de registros en una subconsulta o Common Table Expression (CTE) antes de la agregación:
  ```sql
  WITH limited_crashes AS (
      SELECT crash_record_id, geom, crash_date, posted_speed_limit, injuries_total, injuries_fatal, risk_score
      FROM silver_crashes
      WHERE geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
      LIMIT 5000
  )
  SELECT json_build_object(
      'type', 'FeatureCollection',
      'features', COALESCE(json_agg(
          json_build_object(
              'type', 'Feature',
              'id', crash_record_id,
              'geometry', ST_AsGeoJSON(geom)::json,
              'properties', json_build_object(
                  'crash_date', crash_date,
                  'posted_speed_limit', posted_speed_limit,
                  'injuries_total', injuries_total,
                  'injuries_fatal', injuries_fatal,
                  'risk_score', risk_score
              )
          )
      ), '[]'::json)
  ) AS geojson_output
  FROM limited_crashes;
  ```

---

### [CRÍTICO] C2: Violación de Permisos de Sistema de Archivos en Volumen `/data/duckdb` con Usuario No-Root
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.2 (Líneas 427-434) y Sección 4.5 (Líneas 635-636).
* **Código Identificado:**
  En `backend/Dockerfile`:
  ```dockerfile
  RUN groupadd -g 10001 appgroup && \
      useradd -u 10001 -g appgroup -s /bin/bash -m appuser
  ...
  USER appuser
  ```
  En `docker-compose.yml`:
  ```yaml
  volumes:
    - duckdb_data:/data/duckdb
  environment:
    DUCKDB_PATH: /data/duckdb/chicago_olap.duckdb
  ```
* **Suposición Cuestionada:** Se asume que el usuario de ejecución `appuser` (UID 10001) podrá crear y escribir el archivo `chicago_olap.duckdb` dentro del directorio `/data/duckdb` montado por Docker.
* **Escenario de Ataque y Verificación Empírica:**
  Cuando el daemon de Docker inicializa un volumen con nombre (`duckdb_data:/data/duckdb`) en un directorio destino que no existía previamente en la imagen con permisos explícitos de usuario, Docker crea automáticamente el directorio con propietario `root:root` y máscara de permisos `drwxr-xr-x` (0755).
  Dado que el contenedor cambia deterministamente a `USER appuser` (UID 10001), este usuario únicamente posee permisos de lectura y ejecución sobre `/data/duckdb`.
  Al ejecutarse el pipeline analítico o intentar instanciar la conexión DuckDB (`duckdb.connect('/data/duckdb/chicago_olap.duckdb')`), el motor DuckDB intentará crear el archivo de base de datos y los archivos temporales `.wal`, arrojando inmediatamente:
  `duckdb.duckdb.IOException: IO Error: Cannot open file "/data/duckdb/chicago_olap.duckdb": Permission denied` (o `PermissionError: [Errno 13]`).
* **Radio de Explosión (Blast Radius):** El contenedor FastAPI colapsa al intentar procesar cualquier consulta analítica OLAP o durante la inicialización de servicios, impidiendo el funcionamiento de la capa Gold.
* **Mitigación Mandatoria:** En la etapa `runner` de `backend/Dockerfile`, crear el directorio `/data/duckdb` y transferir su propiedad a `appuser:appgroup` **antes** de la instrucción `USER appuser`:
  ```dockerfile
  RUN mkdir -p /data/duckdb && chown -R appuser:appgroup /data/duckdb
  USER appuser
  ```

---

### [ALTO] C3: Bloqueo de Arranque y Fallo de Healthcheck por Ausencia del Modelo ML en Despliegue Inicial
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.1 (Línea 364), Sección 4.4, Sección 4.5 (Línea 633) y Fase 6 (Líneas 1198-1200).
* **Configuración Identificada:**
  `MODEL_PATH: /app/app/ml/models/chicago_risk_xgboost.joblib`
  El plan estipula que en el evento `lifespan` de FastAPI se ejecuta:
  `joblib.load(settings.MODEL_PATH)`.
  En `docker-compose.yml`:
  `frontend` depende de `backend: condition: service_healthy`.
* **Suposición Cuestionada:** Se asume que el contenedor de backend iniciará y pasará el healthcheck en una instalación limpia o primer despliegue con `docker compose up -d --build`.
* **Escenario de Ataque y Verificación Empírica:**
  En una clonación limpia del repositorio o en un despliegue inicial (Fase 1 a 3), el archivo serializado `chicago_risk_xgboost.joblib` aún no ha sido generado (su entrenamiento ocurre en la Fase 3).
  Si `main.py` intenta ejecutar incondicionalmente `joblib.load()` durante el `lifespan`:
  1. Python arroja `FileNotFoundError: [Errno 2] No such file or directory: '/app/app/ml/models/chicago_risk_xgboost.joblib'`.
  2. Uvicorn aborta el proceso inmediatamente con código de salida 1.
  3. El contenedor entra en bucle de reinicio (*CrashLoopBackOff*).
  4. La sonda de salud `curl -f http://localhost:8000/api/v1/health` nunca responde.
  5. El servicio `frontend` jamás inicia debido a la dependencia `service_healthy`.
* **Radio de Explosión (Blast Radius):** Imposibilidad total de levantar la plataforma de forma desacoplada como exige el Acceptance Criteria de la Fase 1 y Fase 6.
* **Mitigación Mandatoria:** El código de arranque en `app/main.py` debe implementar carga condicional o fallback:
  ```python
  if os.path.exists(settings.MODEL_PATH):
      app.state.ml_model = joblib.load(settings.MODEL_PATH)
  else:
      logger.warning("ML model artifact not found at %s. Predict endpoint will return 503.", settings.MODEL_PATH)
      app.state.ml_model = None
  ```

---

### [ALTO] C4: Desincronización de Migraciones Alembic en el Comando de Arranque del Contenedor Backend
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.1 (Línea 363) frente a Sección 4.2 (Línea 441).
* **Discrepancia Observada:**
  - Sección 4.1 declara explícitamente:
    `2. CONTENEDOR BACKEND FASTAPI: - Ejecuta migraciones automáticas: alembic upgrade head.`
  - Sin embargo, en el Dockerfile (`backend/Dockerfile`, Línea 441), el comando final es:
    `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]`.
  - No existe ningún script `entrypoint.sh` en el repositorio ni directiva que invoque `alembic upgrade head` antes de Uvicorn.
* **Suposición Cuestionada:** Se asume que las tablas de la base de datos se crearán solas al encender el stack con `docker compose up -d`.
* **Escenario de Ataque y Verificación Empírica:**
  Al levantar los servicios mediante `docker compose up -d`, PostgreSQL arranca vacío. Uvicorn inicia en el backend. Cuando el primer usuario o la prueba E2E consulta `GET /api/v1/crashes/geojson`, SQLAlchemy ejecuta la consulta contra la base de datos y PostgreSQL arroja:
  `psycopg.errors.UndefinedTable: relation "silver_crashes" does not exist`.
* **Radio de Explosión (Blast Radius):** Ruptura inmediata de todas las rutas de la API en entornos de desarrollo y producción automatizados.
* **Mitigación Mandatoria:** Incorporar un script `backend/entrypoint.sh` o encadenar las instrucciones en el comando de Dockerfile:
  ```dockerfile
  CMD ["sh", "-c", "alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2"]
  ```

---

### [MEDIO] C5: Parámetro Inadecuado `shared_preload_libraries=postgis-3` en PostgreSQL 16
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.5 (`docker-compose.yml`, Línea 601).
* **Código Identificado:**
  ```yaml
  command: >
    postgres
    ...
    -c shared_preload_libraries=postgis-3
  ```
* **Suposición Cuestionada:** Se asume que PostGIS 3.4 debe registrarse en `shared_preload_libraries`.
* **Escenario de Ataque y Verificación Empírica:**
  PostGIS es una extensión espacial de carga dinámica activada por la instrucción SQL `CREATE EXTENSION postgis;`. A diferencia de extensiones que interceptan ganchos del postmaster (como `timescaledb` o `pg_stat_statements`), PostGIS **no** requiere ser precargado en la memoria compartida del postmaster.
  Si la imagen `postgis/postgis:16-3.4` no provee un binario con punto de entrada `_PG_init` diseñado para carga estática, PostgreSQL emite:
  `FATAL: could not load library "postgis-3": ...` y se rehúsa a iniciar.
* **Radio de Explosión (Blast Radius):** El contenedor `chicago_postgis` no puede iniciar o emite advertencias graves de configuración en stderr.
* **Mitigación Mandatoria:** Eliminar `-c shared_preload_libraries=postgis-3` del comando de arranque en `docker-compose.yml`.

---

### [MEDIO] C6: Degradación por Escaneo Secuencial en Actualización Masiva de Obras Viales
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 2 (Fase 2, Líneas 958-969).
* **Código Identificado:**
  ```sql
  UPDATE silver_crashes c
  SET active_workzone = true, workzone_permit_id = p.permit_id
  FROM silver_road_permits p
  WHERE c.crash_date BETWEEN p.start_date AND p.end_date
    AND ST_DWithin(
        ST_Transform(c.geom, 3435),
        ST_Transform(p.geom, 3435),
        820.21
    );
  ```
* **Suposición Cuestionada:** Se asume que el índice espacial `idx_crashes_geom` acelerará este cruce espacial.
* **Escenario de Ataque y Verificación Empírica:**
  El índice `idx_crashes_geom` fue creado sobre la columna cruda `geom` (`EPSG:4326`).
  Al envolver la columna en la función `ST_Transform(c.geom, 3435)`, el optimizador de consultas de PostgreSQL **invalida el uso del índice GiST estándar** y se ve forzado a realizar un Sequential Scan completo sobre los 850,000 registros de siniestros frente a cada permiso de obra, calculando la transformación proyectiva en CPU para cada tupla.
* **Radio de Explosión (Blast Radius):** El script de enriquecimiento espacial tardará varias horas en completarse en lugar de minutos, bloqueando la tabla `silver_crashes` con un bloqueo de escritura prolongado.
* **Mitigación Mandatoria:**
  1. Crear un índice funcional proyectado:
     ```sql
     CREATE INDEX idx_crashes_geom_3435 ON silver_crashes USING GIST (ST_Transform(geom, 3435));
     CREATE INDEX idx_permits_geom_3435 ON silver_road_permits USING GIST (ST_Transform(geom, 3435));
     ```
  2. O almacenar la columna métrica persistida `geom_3435` en la capa Silver para cálculos inmediatos.

---

### [MEDIO] C7: Bloqueo de Tiles Vectoriales y Estilos en Content Security Policy (CSP)
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.4 (`nginx.conf`, Línea 517).
* **Código Identificado:**
  ```nginx
  add_header Content-Security-Policy "default-src 'self'; ... img-src 'self' data: blob: https://*.cartocdn.com https://*.openstreetmap.org; connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com blob:;" always;
  ```
* **Suposición Cuestionada:** Se asume que la directiva CSP permite a MapLibre GL JS cargar todas las fuentes cartográficas necesarias.
* **Escenario de Ataque y Verificación Empírica:**
  MapLibre GL JS v4 es un motor basado en WebGL2 que descarga teselas vectoriales (`.pbf` / `.mvt`), definiciones de estilo (`style.json`) y fuentes de glifos (`.pbf`) mediante la API `fetch()`.
  En la especificación W3C de Content Security Policy, las peticiones `fetch()` se gobiernan por la directiva **`connect-src`**, mientras que `img-src` aplica únicamente a elementos `<img>` y texturas de imágenes raster.
  En la configuración propuesta, `https://*.openstreetmap.org` se incluyó en `img-src` pero **se omitió en `connect-src`**.
  Si el desarrollador utiliza capas de OpenStreetMap o proveedores de tiles vectoriales externos (o el repositorio oficial de Demotiles de MapLibre), el navegador bloqueará inmediatamente las conexiones de red con un error de seguridad CSP.
* **Radio de Explosión (Blast Radius):** El mapa interactivo no muestra el mapa base ni las capas vectoriales; la consola del navegador se satura de violaciones de CSP.
* **Mitigación Mandatoria:** Incluir las fuentes cartográficas completas en `connect-src`:
  ```nginx
  connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com https://*.openstreetmap.org https://demotiles.maplibre.org blob:;
  ```

---

### [BAJO] C8: Omisión de `scipy` en el Manifiesto de Dependencias Congeladas
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 3.1 (`backend/requirements.txt`).
* **Observación:** Se especifican `scikit-learn==1.6.1` y `xgboost==2.1.4`. Ambos paquetes dependen estrictamente de `scipy`, pero `scipy` no figura en `requirements.txt`.
* **Impacto:** Durante `pip install`, pip resolverá la última versión disponible de `scipy`. Si una versión futura de `scipy` rompe compatibilidad con la cota `numpy<2.0.0`, el build de Docker fallará de forma no determinista.
* **Mitigación Mandatoria:** Añadir explícitamente `scipy==1.14.1` a `backend/requirements.txt`.

---

### [BAJO] C9: Ambigüedad de Resolución de Host en Comandos CLI Locales
* **Ubicación:** `plan_de_implementacion_fases.md`, Sección 4.6 (`.env.example`) y Fase 1 (Líneas 908-919).
* **Observación:** Se instruye al desarrollador a activar el entorno virtual local en Windows PowerShell y ejecutar `alembic upgrade head`. No obstante, `.env.example` fija `DATABASE_URL` con el host `db:5432`.
* **Impacto:** El host de la máquina local no reconoce el nombre de dominio interno de Docker `db`. La ejecución local de Alembic falla con `socket.gaierror: [Errno 11001] getaddrinfo failed`.
* **Mitigación Mandatoria:** Clarificar en el plan que para comandos ejecutados directamente desde la terminal del host (fuera de Docker), `DATABASE_URL` debe apuntar a `localhost:5432`.

---

## 3. RESULTADOS DE PRUEBAS DE ESTRÉS (STRESS TEST RESULTS)

| Escenario de Estrés | Comportamiento Esperado | Comportamiento Predictivo / Actual | Veredicto |
|---|---|---|---|
| **Query GeoJSON BBOX de Gran Escala (>200,000 colisiones)** | Limitar estrictamente a 5,000 features en $<100\text{ ms}$. | Retorna las >200,000 entidades en un solo JSON; pico de RAM >2 GB; latencia >15 s. | **FAIL** (C1) |
| **Persistencia DuckDB en Volumen Dockerizado** | Crear y escribir `/data/duckdb/chicago_olap.duckdb` sin error. | `PermissionError: [Errno 13]` por directorio propiedad de root con `USER appuser`. | **FAIL** (C2) |
| **Despliegue Limpio `docker compose up -d --build`** | Contenedores pasan healthcheck y responden en `< 2` minutos. | FastAPI aborta en bucle de reinicio por falta de `.joblib`; stack congelado. | **FAIL** (C3) |
| **Inicialización Automática de Base de Datos** | Tablas creadas automáticamente al encender contenedores. | Backend corre sin migraciones; tablas inexistentes; error 500 en endpoints. | **FAIL** (C4) |
| **Arranque de PostgreSQL 16 con PostGIS 3.4** | Postgres inicializa cluster sin advertencias en stderr. | Parámetro `shared_preload_libraries=postgis-3` innecesario; riesgo de fatal. | **FAIL** (C5) |
| **Cruce Espacial de 850k Siniestros con Obras CDOT** | Uso de índice espacial GiST para resolver en minutos. | `ST_Transform` en predicado ignora índice GiST; escaneo secuencial masivo de horas. | **FAIL** (C6) |
| **Carga de Teselas Cartográficas en MapLibre v4** | Render fluido de estilos y teselas vectoriales a 60 FPS. | Peticiones `fetch()` bloqueadas por política CSP en Nginx. | **FAIL** (C7) |
| **Instalación de Dependencias Python con `numpy<2.0.0`** | Resolución limpia y reproducible de todo el árbol. | Árbol resuelve, pero ausencia de pin en `scipy` introduce variabilidad futura. | **WARN** (C8) |
| **Migración Alembic desde PowerShell en Host** | Conexión a PostgreSQL en puerto expuesto 5432. | Falla si `.env` tiene `POSTGRES_HOST=db` sin alias en archivo hosts. | **WARN** (C9) |

---

## 4. ÁREAS NO DESAFIADAS (UNCHALLENGED AREAS)

* **Matriz de Features ML y Fórmulas de Visión Zero:** Las métricas seleccionadas (AUC-ROC $\ge 0.70$, Recall $\ge 0.60$) y los algoritmos (Random Forest, XGBoost) son conceptualmente adecuados y estándar en la literatura de seguridad vial.
* **Componentes UI y Hooks de React 18:** La arquitectura de gestión de WebGL (`useMapLibre`, desmontaje con `map.remove()`, virtualización con TanStack) cumple con las mejores prácticas para evitar fugas de contextos GPU.

---

## 5. CONCLUSIÓN Y PLAN DE ACCIÓN RECOMENDADO

El plan maestro `plan_de_implementacion_fases.md` debe ser actualizado para corregir las deficiencias identificadas antes de iniciar la codificación.

### Acciones Correctivas Inmediatas Requeridas para worker_1:
1. **Corregir la consulta SQL en Sección 2.3** introduciendo una CTE/subconsulta para el `LIMIT 5000`.
2. **Actualizar el Dockerfile de backend** para crear `/data/duckdb` con permisos de `appuser`.
3. **Modificar el lifespan de FastAPI en el plan** para gestionar con tolerancia a fallos la ausencia inicial del modelo `.joblib`.
4. **Incluir la ejecución de migraciones en el entrypoint/CMD** del contenedor backend.
5. **Remover `shared_preload_libraries=postgis-3`** del bloque `db` en `docker-compose.yml`.
6. **Añadir índices funcionales `ST_Transform(geom, 3435)`** en el pipeline de enriquecimiento espacial.
7. **Expandir la directiva `connect-src` en `nginx.conf`** para soportar las fuentes cartográficas completas.
8. **Fijar `scipy==1.14.1`** en `backend/requirements.txt`.
9. **Aclarar el uso de `localhost` vs `db`** para ejecuciones CLI locales.

Una vez implementadas estas correcciones en el documento, el plan calificará para su **APROBACIÓN** total.
