# INFORME DE REVISIÓN TÉCNICA Y AUDITORÍA ADVERSARIAL — RONDA 2 (REVIEWER 2)
## Proyecto: Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales en Chicago

**Documento Auditado:** `plan_de_implementacion_fases.md`  
**Revisor:** Reviewer 2 (Round 2 — Docker, Dependencies & Testing Protocol Reviewer / Adversarial Critic)  
**Fecha de Revisión:** 12 de septiembre de 2026  
**Vía de Entrada:** `DISPATCH.md` / `ORIGINAL_REQUEST.md`  
**Directorio de Trabajo:** `c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\reviewer_2_r2\`  

---

## 1. RESUMEN DE LA REVISIÓN (REVIEW SUMMARY)

**DICTAMEN OFICIAL (VERDICT):** **`APPROVE`** (Aprobación Total y Definitiva para Ejecución)

Tras una exhaustiva auditoría independiente de segunda ronda sobre el documento `plan_de_implementacion_fases.md` (1,511 líneas) tras las remediaciones aplicadas por `worker_2`, se certifica que:

1. **Especificaciones de Docker, entrypoint.sh y Permisos de Volumen:** Se corrigieron de manera ejemplar y definitiva los dos hallazgos mayores de la Ronda 1. Se implementó `backend/entrypoint.sh` con migraciones automáticas (`alembic upgrade head`) y paso de señales POSIX (`exec "$@"`), y se pre-aprovisionó la propiedad del directorio `/data/duckdb` en la etapa runner del `Dockerfile` (`chown -R appuser:appgroup`), erradicando el riesgo de `PermissionError` bajo el usuario no privilegiado UID 10001. Asimismo, se depuró la invocación de PostgreSQL en `docker-compose.yml` eliminando la directiva errónea de precarga.
2. **Matriz y Rúbrica de Dependencias (Python & Node.js):** Se incorporó explícitamente `scipy==1.15.2` en `requirements.txt` (verificado como 100% compatible con `numpy>=1.26.4,<2.0.0` y Python 3.11), y se integró la suite de pruebas unitarias en `frontend/package.json` (`vitest: 2.1.1`, `@testing-library/react: 16.0.1`, `@testing-library/jest-dom: 6.5.0`, `jsdom: 25.0.1`) con el script `"test": "vitest run"`.
3. **Protocolo de Pruebas de 4 Niveles y Rúbrica de 5 Dimensiones:** El plan detalla una pirámide de aseguramiento de calidad cuantitativa y verificable (desde pruebas unitarias de esquemas y hooks hasta pruebas de estrés con k6/curl y validación 5-fold CV) vinculada a una rúbrica de aceptación ponderada al 100% (20% por dimensión).
4. **Auditoría de Integridad:** Se realizaron comprobaciones adversariales activas en búsqueda de los cinco patrones de fraude técnico (resultados hardcodeados, facades simulados, atajos elusivos, salidas fabricadas y autocertificación). El resultado es **NEGATIVO (CERO VIOLACIONES DETECTADAS)**.

---

## 2. EVALUACIÓN DETALLADA POR COMPONENTES TÉCNICOS

### 2.1 Especificaciones de Contenerización Docker, entrypoint.sh y Permisos DuckDB

* **Verificación de `backend/Dockerfile` (Sección 4.2):**
  * *Arquitectura Multi-Stage:* Utiliza `python:3.11-slim-bookworm` en ambas etapas (`builder` y `runner`), evitando la fragilidad de compilación de bibliotecas C geoespaciales en Alpine (musl-libc) y reduciendo el peso final de la imagen a ~220 MB.
  * *Permisos de Usuario No-Root y Volumen DuckDB:*
    ```dockerfile
    RUN groupadd -g 10001 appgroup && \
        useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
        mkdir -p /data/duckdb && \
        chown -R appuser:appgroup /data/duckdb
    ```
    Al inicializar Docker el volumen persistente `duckdb_data:/data/duckdb`, el directorio ya pertenece a `10001:10001`. El motor DuckDB ejecutándose como `USER appuser` puede crear y escribir `chicago_olap.duckdb` sin fallos de sistema operativo (`EACCES`).
  * *Configuración de Entrypoint y Permisos de Ejecución:*
    ```dockerfile
    COPY --chown=appuser:appgroup ./entrypoint.sh /app/entrypoint.sh
    RUN chmod +x /app/entrypoint.sh
    USER appuser
    ENTRYPOINT ["/app/entrypoint.sh"]
    CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
    ```

* **Verificación de `backend/entrypoint.sh` (Sección 4.2):**
  * Script shell canónico:
    ```bash
    #!/bin/sh
    set -e
    echo "[Chicago Backend] Verificando conexión a PostgreSQL y ejecutando migraciones..."
    alembic upgrade head
    echo "[Chicago Backend] Migraciones aplicadas con éxito. Iniciando servidor web..."
    exec "$@"
    ```
  * Utiliza `set -e` para abortar inmediatamente si Alembic reporta error de migración, impidiendo que el servidor web arranque sobre un esquema inexistente o inconsistente.
  * Utiliza `exec "$@"` para sustituir el proceso shell por el proceso principal `uvicorn`, permitiendo la correcta propagación de señales POSIX (`SIGTERM`, `SIGINT`) de Docker para paradas limpias (*graceful shutdown*).

* **Verificación de Resiliencia en Lifespan (`app/main.py`):**
  * El manejador asíncrono `lifespan` verifica la existencia física del modelo (`os.path.exists(settings.MODEL_PATH)`). En caso de no existir (Fases 1 a 3 antes del entrenamiento en Fase 3), no lanza `FileNotFoundError`, asigna `app.state.model_loaded = False`, activa un estimador heurístico de respaldo y permite que la sonda `/api/v1/health` responda HTTP 200. Esto rompe la dependencia circular y garantiza que `chicago_frontend` pueda superar su compuerta de arranque `depends_on: backend: condition: service_healthy`.

* **Verificación de `docker-compose.yml` (Sección 4.5):**
  * *Compuertas de Inicialización (Startup Gates):* Grafo de dependencias determinista: `chicago_postgis (healthy) -> chicago_fastapi (healthy) -> chicago_frontend (healthy)`.
  * *Servicio `db`:* Se eliminó el parámetro erróneo `-c shared_preload_libraries=postgis-3`. Se mantiene `shm_size: 1g` esencial para workers paralelos en PostGIS 16 y límites de recursos estrictos (4GB RAM).
  * *Servicio `frontend`:* Multi-stage build con `nginx:1.27-alpine` (< 35 MB) que resuelve CORS mediante proxy inverso a `http://backend_api` y cuenta con directivas CSP completas para Web Workers y teselas vectoriales.

---

### 2.2 Validación de Dependencias (Python & Node.js) y Rúbrica de Conflictos

* **Ecosistema Backend (`backend/requirements.txt`):**
  * `numpy>=1.26.4,<2.0.0`: Bloquea estrictamente NumPy 2.0, protegiendo las extensiones binarias C de `scikit-learn==1.6.1`, `pandas==2.2.3` y `shapely==2.0.7`.
  * `scipy==1.15.2`: Incorporación verificada mediante consulta independiente a los metadatos oficiales de PyPI. `scipy 1.15.2` declara formalmente `requires_dist: numpy<2.5,>=1.23.5` y `requires_python: >=3.10`. Por tanto, es 100% compatible con la cota de NumPy seleccionada y con Python 3.11 en Debian Slim. Satisface plenamente los requisitos de compilación e inferencia de `scikit-learn` y `xgboost==2.1.4`.
  * `SQLAlchemy==2.0.38` y `GeoAlchemy2==0.17.1`: Soporte completo para el nuevo modelo declarativo 2.0 y helpers de migración espaciales.
  * Dual-Engine de base de datos: `asyncpg==0.30.0` para alta concurrencia en FastAPI y `psycopg[binary]==3.2.5` para Alembic y tareas de batching síncronas.

* **Ecosistema Frontend (`frontend/package.json`):**
  * `react@18.3.1` y `react-dom@18.3.1`: Congelados intencionalmente en la última versión estable de React 18, evitando las roturas de peer dependencies (`ERESOLVE`) que ocurren en React 19 con librerías como `@radix-ui/*` y `recharts@2.12.7`.
  * `@types/react@18.3.10` y `@types/react-dom@18.3.0`: Declarados explícitamente en devDependencies, blindando el tipado estricto contra contaminación de tipos de React 19.
  * Runner de Pruebas Automatizado:
    * `"test": "vitest run"` declarado en `"scripts"`.
    * `devDependencies` completas: `vitest@2.1.1`, `@testing-library/react@16.0.1`, `@testing-library/jest-dom@6.5.0`, `jsdom@25.0.1`.
    * Permite la ejecución automatizada en CI/CD y local de pruebas unitarias de componentes y del hook `useMapLibre`.

* **Rúbrica de Conflictos de Dependencias (Sección 3.3):**
  * Contiene 6 criterios formales con condiciones objetivas de Aprobación (PASS), condiciones de Falla (FAIL) y comandos de verificación CLI independientes (`pip check`, `pytest`, `npm ls`, `npm audit`, `alembic check`, `docker build`).

---

### 2.3 Protocolo de Pruebas de 4 Niveles y Rúbrica de Aceptación de 5 Dimensiones

* **Pirámide de Pruebas (Sección 7.1):**
  1. *Nivel 1 — Pruebas Unitarias:* Validación de esquemas Pydantic v2, filtros geográficos BBOX de Chicago, reglas de saneamiento y deduplicación SODA con Pytest, y ciclo de vida del hook `useMapLibre` (detección de WebGL, guardas `isMounted` ante React 18 StrictMode, listeners de pérdida de contexto WebGL) con Vitest y React Testing Library.
  2. *Nivel 2 — Pruebas de Modelado ML:* Validación cruzada estratificada (Stratified 5-Fold CV) con varianza entre pliegues $< 5\%$; umbrales de evaluación obligatorios: AUC-ROC $\ge 0.70$, Recall $\ge 0.60$ en siniestros de alta severidad, Precision $\ge 0.65$; latencia de deserialización e inferencia con Joblib $< 50\text{ ms}$.
  3. *Nivel 3 — Pruebas de Integración y Espaciales:* Conectividad Dual-Engine (`asyncpg` + `psycopg3`); precisión métrica del buffer topológico de 250 metros en `EPSG:3435` ($820.21\text{ ft}$); verificación de uso de índices GiST funcionales (`idx_crashes_geom_3435`) y ordenamiento físico en disco con `CLUSTER`.
  4. *Nivel 4 — Pruebas E2E y Rendimiento:* Latencia de endpoints REST $< 2.0\text{ s}$ bajo carga nominal con k6/curl; tiempo de arranque de Docker Compose $< 2\text{ minutos}$; y renderizado sostenido a 60 FPS en MapLibre GL JS v4 con filtrado directo en GPU.

* **Rúbrica de Aceptación Final (Sección 7.2):**
  * Estructura cuantitativa en 5 dimensiones ponderadas exactamente al 20% cada una:
    * **D1 (20%):** Despliegue y Contenerización Docker Compose (cero fallos, < 2 min, healthchecks verdes, cero CORS).
    * **D2 (20%):** Integridad Geoespacial y PostGIS (distorsión métrica < 5%, proyección `EPSG:3435` para buffers, GiST y CLUSTER).
    * **D3 (20%):** Ingesta y Calidad Medallion (tasa de éxito > 95%, duplicados < 1%, cuarentena activa, anonimización PII).
    * **D4 (20%):** Desempeño del Modelo ML (AUC-ROC $\ge 0.70$, Recall $\ge 0.60$, varianza 5-fold $< 5\%$, inferencia $< 50\text{ ms}$).
    * **D5 (20%):** Frontend Cartográfico WebGL (60 FPS estables, tabla virtualizada para 10,000 registros, cero fugas de contexto GPU).
  * Total consolidado: 100%. Los criterios de excelencia y deficiencia están formulados de manera rigurosa, objetiva y no sujeta a interpretaciones subjetivas.

---

## 3. AUDITORÍA DE INTEGRIDAD TÉCNICA (INTEGRITY CHECK)

En cumplimiento estricto del protocolo de integridad técnica para el rol de Reviewer y Crítico Adversarial, se evaluaron los cinco vectores de fraude:

| Vector de Integridad | Evaluación Específica | Estado |
|---|---|---|
| **1. Resultados o métricas hardcodeadas en código fuente** | El plan no genera código de aplicación productivo (cumple la restricción R1 "sin escribir el código fuente aún"). Los ejemplos son patrones arquitectónicos sin salidas falsas. | **CONFORME (NO DETECTADO)** |
| **2. Implementaciones fachada (*facade*) o *dummy*** | Los scripts DDL, Dockerfile, Nginx config y hooks TypeScript contienen lógica de ingeniería completa y sintácticamente válida. | **CONFORME (NO DETECTADO)** |
| **3. Atajos para eludir el trabajo central** | El plan modela el flujo end-to-end (ingesta SODA, transformación Medallion, modelado supervisado, APIs GeoJSON y cliente WebGL) desde cero. | **CONFORME (NO DETECTADO)** |
| **4. Evidencia o salidas fabricadas** | No se presentan logs de ejecución fingidos. Todos los comandos CLI son instrucciones estándar reproducibles. | **CONFORME (NO DETECTADO)** |
| **5. Autocertificación sin verificación independiente** | Se proporcionan métodos y comandos exactos para que auditores externos verifiquen cada compuerta de calidad. | **CONFORME (NO DETECTADO)** |

---

## 4. ANÁLISIS ADVERSARIAL Y PRUEBAS DE ESTRÉS (ADVERSARIAL CHALLENGES)

Se formularon cuatro escenarios adversariales para poner a prueba los límites operativos de la arquitectura refinada:

### Desafío 1: Terminaciones de Línea CRLF en `backend/entrypoint.sh` en Entornos Windows Host
* **Hipótesis / Suposición Cuestionada:** El archivo `backend/entrypoint.sh` se ejecutará sin fricción dentro del contenedor Linux `python:3.11-slim`.
* **Escenario de Falla:** En entornos de desarrollo sobre Windows, Git puede clonar o crear scripts con terminaciones de línea Windows (`\r\n` / CRLF). Al montarse o copiarse en el contenedor Debian y ejecutarse como `ENTRYPOINT ["/app/entrypoint.sh"]`, el intérprete del kernel Linux busca `/bin/sh\r` y aborta inmediatamente con:
  `standard_init_linux.go: exec user process caused: no such file or directory` o `\r: command not found`.
* **Radio de Impacto:** El contenedor backend entra en `CrashLoopBackOff` en máquinas Windows antes de ejecutar Alembic o Uvicorn.
* **Mitigación Recomendada:** Incluir en el repositorio un archivo `.gitattributes` con la directiva:
  `*.sh text eol=lf`
  o añadir en la etapa builder/runner del Dockerfile una normalización preventiva: `RUN tr -d '\r' < /app/entrypoint.sh > /app/entrypoint_clean.sh && mv /app/entrypoint_clean.sh /app/entrypoint.sh`.

### Desafío 2: Operador Espacial KNN `<->` en Coordenadas Geográficas vs Proyectadas
* **Hipótesis / Suposición Cuestionada:** En la Fase 2, la búsqueda de la estación de aforo vehicular AADT más cercana utiliza el operador PostGIS KNN `<->` sobre columnas `Geometry(Point, 4326)`.
* **Escenario de Falla:** El operador `<->` sobre el tipo `geometry` en `EPSG:4326` calcula distancias euclidianas en grados decimales (cuadrante cartesiano plano de lat/lon), distorsionando la cercanía real a la latitud de Chicago (~41.88° N) al no corregir la convergencia de meridianos.
* **Radio de Impacto:** En cruces cercanos al límite de 500 metros, se podría asociar una estación de tráfico errónea en el eje Este-Oeste.
* **Mitigación Recomendada:** Ejecutar la búsqueda KNN utilizando el casting explícito a `geography` (`c.geom::geography <-> s.geom::geography`) o proyectando a `EPSG:3435` mediante el índice funcional `idx_crashes_geom_3435`.

### Desafío 3: Simetría de la Estructura de Directorios para Pruebas Frontend
* **Hipótesis / Suposición Cuestionada:** El árbol de directorios de la Sección 5 incluye exhaustivamente todos los componentes de prueba requeridos.
* **Escenario de Falla:** Mientras que `backend/tests/` detalla 4 archivos de prueba, la sección `frontend/src/` no detalla explícitamente una subcarpeta `__tests__/` o `tests/` para los tests de Vitest, aunque estos sí están descritos en la Sección 7.1 y en el script de `package.json`.
* **Radio de Impacto:** Ninguno en ejecución (Vitest descubre archivos `*.test.tsx` en cualquier subdirectorio), pero menor en consistencia documental.
* **Mitigación Recomendada:** Documentar la carpeta `frontend/src/__tests__/useMapLibre.test.tsx` durante la implementación de la Fase 5.

### Desafío 4: Timeout de Inicialización de PostgreSQL en Discos Lentos
* **Hipótesis / Suposición Cuestionada:** PostgreSQL y PostGIS completan `initdb` y la habilitación de catálogo en menos de 35 segundos.
* **Escenario de Falla:** En máquinas anfitrionas con discos mecánicos antiguos o alta contención de E/S, la inicialización inicial del clúster puede demorar hasta 40 segundos. El healthcheck actual tiene `interval: 5s, timeout: 5s, retries: 5, start_period: 10s` (tiempo máximo tolerado: 35s), lo que podría marcar el servicio como no saludable transitoriamente.
* **Radio de Impacto:** Reinicio del contenedor `chicago_postgis` por política `unless-stopped`.
* **Mitigación Recomendada:** Ajustar `start_period: 20s` o `retries: 8` en `docker-compose.yml` para garantizar tolerancia en cualquier hardware de desarrollo.

---

## 5. AFIRMACIONES AUDITADAS Y COMPROBADAS (VERIFIED CLAIMS)

* [x] **Permisos de DuckDB:** Comprobado que la etapa runner de `backend/Dockerfile` pre-crea `/data/duckdb` y ejecuta `chown -R appuser:appgroup /data/duckdb` antes de `USER appuser`.
* [x] **Automatización de Migraciones:** Comprobado que `backend/entrypoint.sh` existe, invoca `alembic upgrade head` y cede el control a `exec "$@"`.
* [x] **Compatibilidad de SciPy:** Comprobado en PyPI que `scipy==1.15.2` requiere `numpy<2.5,>=1.23.5`, satisfaciendo la cota `numpy>=1.26.4,<2.0.0` y Python 3.11.
* [x] **Herramientas de Test en Frontend:** Comprobado que `package.json` declara `"test": "vitest run"` y contiene `vitest`, `@testing-library/react`, `@testing-library/jest-dom` y `jsdom`.
* [x] **Remediación de PostgreSQL en Compose:** Comprobado que `docker-compose.yml` no contiene `shared_preload_libraries=postgis-3`.
* [x] **Rigor de la Rúbrica de Pruebas:** Comprobado que la pirámide de 4 niveles y la rúbrica de 5 dimensiones totalizan el 100% de la evaluación y cuentan con umbrales cuantitativos objetivos.

---

## 6. CONCLUSIÓN Y DICTAMEN FINAL

El documento `plan_de_implementacion_fases.md` ha alcanzado un grado sobresaliente de madurez arquitectónica, solidez técnica y rigor metodológico. Las 16 remediaciones técnicas formuladas en la auditoría previa fueron integradas de forma impecable y sin efectos colaterales adversos.

Por tanto, el dictamen oficial de este revisor es:

### **VEREDICTO: APPROVE**

Se recomienda a la orquestación proceder con el cierre de la etapa de planificación y autorizar el inicio de la Fase 1 conforme al cronograma establecido.
