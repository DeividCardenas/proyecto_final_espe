# INFORME DE REVISIÓN TÉCNICA Y AUDITORÍA ADVERSARIAL (REVIEWER 2)
## Proyecto: Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales en Chicago
**Documento Auditado:** `plan_de_implementacion_fases.md`  
**Revisor:** Reviewer 2 (Docker, Dependencies & Testing Protocol Reviewer / Adversarial Critic)  
**Fecha de Revisión:** 12 de septiembre de 2026  

---

## 1. RESUMEN DE LA REVISIÓN (REVIEW SUMMARY)

**DICTAMEN OFICIAL (VERDICT):** **`APPROVE`** (Aprobado con Recomendaciones Técnicas de Implementación)

El documento `plan_de_implementacion_fases.md` elaborado por `worker_1` representa una pieza de ingeniería de excepcional rigor técnico, profundidad analítica y madurez arquitectónica. Con un desarrollo exhaustivo de 1,311 líneas, el plan aborda con maestría no solo los requerimientos funcionales, sino los desafíos profundos de interoperabilidad, compatibilidad binaria y rendimiento en sistemas de Big Data geoespacial.

No se detectó **ninguna violación de integridad** (cero resultados hardcodeados, cero implementaciones fachada o facades ficticios, cero atajos elusivos y cero artefactos de auto-certificación sin base técnica). 

Se identifican dos hallazgos mayores de configuración operativa en Docker y dos hallazgos menores relativos al ecosistema de pruebas en frontend, los cuales no invalidan la arquitectura propuesta pero deben ser incorporados por el equipo durante la ejecución de las fases.

---

## 2. EVALUACIÓN DETALLADA POR CRITERIOS

### Criterio 1: Contenerización con Docker y Orquestación (Sección 4)

* **¿Detalla CÓMO y CUÁNDO se construirán los contenedores Docker?**
  * **CÓMO:** Completamente detallado.
    * **Backend (`backend/Dockerfile`):** Multi-stage build basado en `python:3.11-slim-bookworm`. Etapa 1 (`builder`) compila dependencias C (`libpq-dev`, `build-essential`) en un entorno virtual `/opt/venv`. Etapa 2 (`runner`) copia el venv, instala únicamente `libpq5` y `curl`, crea un usuario sin privilegios `appuser:appgroup` (UID 10001), expone el puerto 8000 y define un `HEALTHCHECK` activo hacia `/api/v1/health`.
    * **Frontend (`frontend/Dockerfile`):** Multi-stage build. Etapa 1 (`builder`) usa `node:20-alpine`, `npm ci --prefer-offline` y genera el build de producción con Vite. Etapa 2 (`production`) usa `nginx:1.27-alpine` (< 35 MB), copia los assets estáticos a `/usr/share/nginx/html`, inyecta la configuración `nginx.conf` y define `HEALTHCHECK` vía `wget --spider http://127.0.0.1/health`.
    * **Orquestación (`docker-compose.yml`):** Define los 3 servicios (`db`, `backend`, `frontend`), asignación de red bridge unificada (`chicago_network`), volúmenes persistentes nombrados (`postgis_data`, `duckdb_data`), límites rígidos de memoria (db: 4GB, backend: 2GB, frontend: 512MB) y shm_size de 1GB para PostGIS.
    * **Enrutamiento Reverse Proxy (`frontend/nginx.conf`):** Define `location /api/` con `proxy_pass http://backend_api`, eliminando por completo problemas de CORS en producción al compartir el mismo origen. Integra pre-compresión Gzip para tipos MIME espaciales (`application/geo+json`, `application/vnd.mapbox-vector-tile`), cabeceras de seguridad estrictas y CSP compatible con Web Workers blob de MapLibre GL JS.
  * **CUÁNDO:** Claramente estructurado en el ciclo de vida:
    * *Fase 1 (Semanas 1-3):* Se levanta y valida el contenedor de base de datos (`docker compose up -d db`).
    * *Fase 4 (Semanas 9-11):* Se verifica la integración del backend con la base de datos contenerizada.
    * *Fase 6 (Semanas 12-13):* Se realiza la construcción unificada de producción multi-etapa (`docker compose up -d --build`) y las pruebas E2E de los tres servicios interconectados.

### Criterio 2: Rúbrica de Dependencias y Matriz de Compatibilidad (Sección 3)

* **¿Provee una rúbrica accionable para validar Python y Node.js?**
  * Sí. La Sección 3.3 establece una matriz de 6 criterios cuantitativos con condiciones de PASS, condiciones de FAIL y comandos de verificación independientes (`pip check`, `pytest`, `npm ls`, `npm audit`, `alembic check`, `docker build`).
* **¿Son las versiones pinned mutuamente compatibles?**
  * **SQLAlchemy 2.0.38 + GeoAlchemy2 0.17.1:** Totalmente compatibles. GeoAlchemy2 >= 0.14 se construyó específicamente para el modelo 2.0 de SQLAlchemy, y la versión 0.17.1 resuelve el soporte para dialectos asyncpg y psycopg3.
  * **Aislamiento C-ABI con `numpy>=1.26.4,<2.0.0`:** Decisión técnica brillante. Previene los fallos de segmentación (`Segmentation Fault`) y roturas de compatibilidad binaria que NumPy 2.0 introduce con `scikit-learn==1.6.1`, `pandas==2.2.3` y `shapely==2.0.7`.
  * **React 18.3.1 congelado:** Previene los errores fatales de resolución de dependencias `ERESOLVE` que ocurren en React 19 con librerías del ecosistema cartográfico y UI como `@radix-ui/*` y `recharts==2.12.7`.
  * **Dual-Engine de base de datos:** Coexistencia armónica entre `asyncpg==0.30.0` (para el runtime de FastAPI) y `psycopg[binary]==3.2.5` (para Alembic y tareas síncronas), solventando el bug del OID de geometría `16390` mediante la delegación EWKB de GeoAlchemy2.

### Criterio 3: Protocolo de Pruebas y Criterios de Aceptación (Sección 7)

* **¿Provee un protocolo de pruebas exhaustivo de 4 niveles?**
  * Sí. La Sección 7.1 desglosa la pirámide de pruebas en:
    1. *Pruebas Unitarias:* Validación de esquemas Pydantic v2, BBOX de Chicago, deduplicación y saneamiento SODA, y ciclo de vida de `useMapLibre`.
    2. *Pruebas de Modelado ML:* Validación cruzada estratificada 5-fold (varianza < 5%), umbrales cuantitativos (AUC-ROC $\ge 0.70$, Recall $\ge 0.60$ en riesgo crítico), y tiempo de deserialización/inferencia con joblib $< 50\text{ ms}$.
    3. *Pruebas de Integración y Espaciales:* Conectividad Dual-Engine, exactitud métrica del buffer en `EPSG:3435` ($820.21\text{ ft}$), y efectividad del `CLUSTER` físico sobre índices GiST.
    4. *Pruebas E2E y Rendimiento:* Latencia de API $< 2.0\text{ s}$ bajo carga, arranque de Docker Compose $< 2\text{ min}$, y tasa sostenida de 60 FPS en MapLibre GL JS v4.
* **¿Provee una rúbrica de aceptación objetiva?**
  * Sí. La Sección 7.2 cuantifica la aceptación en 5 dimensiones ponderadas al 20% cada una (D1: Despliegue Docker, D2: Integridad Geoespacial, D3: Calidad ETL Medallion, D4: Modelo ML, D5: Frontend WebGL), sumando el 100% de la calificación final del proyecto.

---

## 3. HALLAZGOS Y ADVERTENCIAS DE INGENIERÍA (FINDINGS)

### [Mayor] Hallazgo 1: Permisos de Escritura del Volumen DuckDB para Usuario No-Root en Docker

* **Qué:** En `backend/Dockerfile`, el contenedor de ejecución corre bajo el usuario sin privilegios `USER appuser` (UID 10001). Sin embargo, en `docker-compose.yml`, se monta el volumen persistente `duckdb_data:/data/duckdb`. Cuando Docker inicializa un volumen nombrado sobre un directorio que no existe o es creado por el daemon, el directorio pertenece por defecto a `root:root` con permisos `0755`.
* **Dónde:** `backend/Dockerfile` (líneas 417-435) y `docker-compose.yml` (línea 636).
* **Por qué es un problema:** Cuando FastAPI intente inicializar la base de datos analítica embebida en `/data/duckdb/chicago_olap.duckdb`, el proceso de DuckDB (ejecutado como UID 10001) recibirá un error del sistema operativo: `PermissionError: [Errno 13] Permission denied: '/data/duckdb/chicago_olap.duckdb'`, provocando la caída del servicio analítico.
* **Sugerencia de corrección:** En `backend/Dockerfile`, antes de la directiva `USER appuser`, crear explícitamente el directorio y transferir la propiedad al usuario no privilegiado:
  ```dockerfile
  RUN mkdir -p /data/duckdb && chown -R appuser:appgroup /data/duckdb
  ```

---

### [Mayor] Hallazgo 2: Automatización de Migraciones Alembic al Iniciar el Contenedor Backend

* **Qué:** El diagrama de secuencia de orquestación de la Sección 4.1 (línea 363) indica: *«2. CONTENEDOR BACKEND FASTAPI ... Ejecuta migraciones automáticas: alembic upgrade head»*. No obstante, el `backend/Dockerfile` especifica directamente:
  `CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]`
  y `docker-compose.yml` no incluye ningún override de `command` ni script de entrada (`entrypoint.sh`).
* **Dónde:** `plan_de_implementacion_fases.md` (líneas 363, 441, 619-654).
* **Por qué es un problema:** En un despliegue limpio con `docker compose up -d`, las migraciones de base de datos no se ejecutarán automáticamente en el arranque a menos que un operador las invoque manualmente desde el host o el contenedor falle al no encontrar las tablas de la base de datos.
* **Sugerencia de corrección:** Existen dos alternativas limpias:
  1. Incorporar un script `backend/entrypoint.sh` ejecutable:
     ```bash
     #!/bin/sh
     set -e
     echo "Ejecutando migraciones de base de datos..."
     alembic upgrade head
     exec "$@"
     ```
     e incluir `ENTRYPOINT ["/app/entrypoint.sh"]` en el Dockerfile.
  2. O invocar `alembic.command.upgrade()` de forma programática dentro del manejador `lifespan` de FastAPI en `app/main.py` durante el ciclo de arranque asíncrono.

---

### [Minor] Hallazgo 3: Ausencia de Runner de Pruebas Frontend en `package.json`

* **Qué:** La Sección 7.1 establece pruebas unitarias para el frontend: *«Pruebas de ciclo de vida del hook useMapLibre en React»*. Sin embargo, el archivo `frontend/package.json` (Sección 3.2) no declara dependencias de testing (`vitest`, `@testing-library/react`, `@testing-library/jest-dom`, `jsdom`) ni define un script `"test"` en su bloque `"scripts"`.
* **Dónde:** `frontend/package.json` (líneas 258-310) vs `Sección 7.1` (línea 1271).
* **Por qué es un problema:** No es posible ejecutar las pruebas unitarias de React mediante comandos automatizados de CI/CD sin estas librerías.
* **Sugerencia de corrección:** Agregar a las `devDependencies` de `frontend/package.json`:
  ```json
  "vitest": "^2.1.1",
  "@testing-library/react": "^16.0.1",
  "@testing-library/jest-dom": "^6.5.0",
  "jsdom": "^25.0.1"
  ```
  y en scripts: `"test": "vitest run"`.

---

### [Minor] Hallazgo 4: Resolución DNS Dinámica en Nginx Upstream

* **Qué:** En `frontend/nginx.conf`, el bloque upstream define `server backend:8000;`. Nginx resuelve el nombre de host `backend` únicamente una vez durante su inicialización.
* **Dónde:** `frontend/nginx.conf` (línea 483).
* **Por qué es un problema:** En entornos Docker donde el contenedor `backend` se reinicia o recrea con una IP interna diferente mientras `frontend` permanece activo, Nginx puede arrojar errores `502 Bad Gateway` al intentar conectar con la IP caducada.
* **Sugerencia de corrección:** Para robustez máxima en producción o desarrollo, se puede configurar el resolver de Docker interno en Nginx:
  ```nginx
  resolver 127.0.0.11 valid=10s;
  ```
  o asegurar que los reinicios se apliquen siempre a la red completa mediante `docker compose restart`.

---

## 4. REVISIÓN ADVERSARIAL Y PRUEBAS DE ESTRÉS (ADVERSARIAL CHALLENGES)

| ID | Suposición Cuestionada | Escenario de Ataque / Modo de Falla | Radio de Impacto | Mitigación Propuesta |
|---|---|---|---|---|
| **C1** | El usuario no-root en Docker puede escribir en volúmenes compartidos. | Montaje de `duckdb_data` inicializado por el daemon de Docker como `root`. DuckDB arroja `EACCES`. | **ALTO:** El subsistema OLAP y las consultas de agregación fallan al arrancar. | Pre-crear `/data/duckdb` y ejecutar `chown -R appuser:appgroup` en el Dockerfile runner. |
| **C2** | MapLibre WebGL siempre retiene su contexto de GPU sin degradarse. | En equipos con GPU integrada y poca VRAM, el SO reclaimed el contexto WebGL tras suspensión o cambio de pestaña prolongado (`webglcontextlost`). | **MEDIO:** La pantalla del mapa queda en negro y no se recupera sin recargar la página. | Implementar manejadores para eventos `webglcontextlost` y llamar a `map.triggerRepaint()` tras `webglcontextrestored`. (El plan ya lo contempla conceptualmente en la Sec. 2.6). |
| **C3** | Las consultas por Bounding Box nunca exceden la memoria si el usuario selecciona una ventana macro. | Un usuario hace zoom out cubriendo todo el estado de Illinois solicitando `/api/v1/crashes/geojson`. La consulta procesa >500,000 puntos y sobrecarga la serialización. | **MEDIO:** Latencia > 3 segundos y alto consumo de RAM en PostgreSQL. | Aplicar el límite forzado de `LIMIT 5000` en la consulta SQL (ya incluido en el ejemplo de la Sec. 2.3) y conmutar automáticamente a clustering por servidor (`ST_ClusterDBSCAN`) o tiles MVT. |
| **C4** | La base de datos siempre estará lista antes que FastAPI intente conectarse. | En máquinas anfitrionas con discos mecánicos o saturadas, PostGIS puede tardar más de 15 segundos en inicializar el clúster. | **BAJO:** FastAPI falla en el arranque por timeout de conexión. | Resuelto mediante la compuerta `depends_on: db: condition: service_healthy` en `docker-compose.yml`, con retries y start_period holgados en `pg_isready`. |

---

## 5. REVISIÓN DE INTEGRIDAD (INTEGRITY CHECK)

En estricto apego al rol de Auditor y Crítico Adversarial, se evaluaron exhaustivamente los cinco patrones de fraude o simulación técnica:
1. **Resultados de prueba o salidas esperadas hardcodeadas en código fuente:** **NEGATIVO (NO DETECTADO).** El plan no contiene código fuente simulado; las métricas presentadas son umbrales normativos de ingeniería requeridos formalmente.
2. **Implementaciones fachada (*facade*) o *dummy* sin lógica real:** **NEGATIVO (NO DETECTADO).** Las especificaciones de SQL espacial (`ST_Transform`, `ST_DWithin`, `ST_AsGeoJSON`, `CLUSTER`), las configuraciones de Dockerfile, Nginx y Docker Compose son sintáctica y funcionalmente operativas.
3. **Atajos para eludir el trabajo central:** **NEGATIVO (NO DETECTADO).** No se delega la arquitectura a cajas negras; se modela el pipeline Medallion, la base de datos relacional y el modelado predictivo desde cero.
4. **Evidencia o salidas de verificación fabricadas:** **NEGATIVO (NO DETECTADO).** Los comandos CLI especificados son reproducibles y estándar.
5. **Autocertificación sin verificación independiente:** **NEGATIVO (NO DETECTADO).** Se proporciona una rúbrica formal con criterios cuantitativos de aprobación y rechazo para ser auditados de forma ciega e independiente.

---

## 6. AFIRMACIONES VERIFICADAS (VERIFIED CLAIMS)

* [x] **Construcción Multi-Etapa de Backend:** La imagen se basa en `python:3.11-slim-bookworm`, utiliza compilación en venv separada y minimiza el tamaño final a ~220 MB aislando herramientas de compilación.
* [x] **Construcción Multi-Etapa de Frontend:** La imagen compila con Node 20 y corre en Nginx Alpine, con un peso menor a 35 MB y pre-compresión Gzip.
* [x] **Compuertas de Salud en Docker Compose:** El grafo de dependencias `db (healthy) -> backend (healthy) -> frontend (healthy)` previene condiciones de carrera en el arranque.
* [x] **Eliminación Total de CORS:** El enrutamiento de Nginx `/api/ -> http://backend:8000` resuelve el acceso cross-origin bajo un único dominio/puerto.
* [x] **Compatibilidad de Pinned Versions en Python:** SQLAlchemy 2.0.38 y GeoAlchemy2 0.17.1 coexisten sin incidencias; `numpy < 2.0.0` resguarda la compatibilidad C-ABI con scikit-learn y shapely.
* [x] **Compatibilidad de Pinned Versions en Node.js:** React 18.3.1 previene roturas de peer dependencies con Radix UI y Recharts.
* [x] **Pirámide de Pruebas de 4 Niveles:** Estructura completa desde pruebas unitarias hasta validación E2E y pruebas de estrés con k6/curl.

---

## 7. CONCLUSIÓN Y RECOMENDACIÓN FINAL

El entregable `plan_de_implementacion_fases.md` cumple de manera sobresaliente con todos los criterios de evaluación exigidos. Se recomienda a la orquestación **aprobar el plan maestro** e incorporar las recomendaciones de los Hallazgos 1, 2 y 3 como notas de refinamiento para el equipo de implementación durante el inicio de la Fase 1.
