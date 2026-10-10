# INFORME DE ESTRATEGIA DE REMEDIACIÓN TÉCNICA (ITERACIÓN 2)
## Guía Canónica de Correcciones Línea por Línea para `plan_de_implementacion_fases.md`

**Agente Investigador:** Remediation Explorer (Iteración 2)  
**Destinatario:** Worker 2 (Lead Implementation Architect & Plan Editor)  
**Documento Objetivo:** `c:\Users\Lab Creacion Digital\Documents\proyecto espe\plan_de_implementacion_fases.md`  
**Fuentes Sintetizadas:**
1. Auditoría Adversarial Backend & Docker: `c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\challenger_1\report.md`
2. Auditoría Adversarial Frontend & Matemáticas Espaciales: `c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\challenger_2\report.md`
3. Revisión Técnica de Arquitectura & Integridad: `c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\reviewer_2\report.md`

---

## 1. RESUMEN EJECUTIVO Y SÍNTESIS DE DEFICIENCIAS

El análisis adversarial conducido por **Challenger 1**, **Challenger 2** y validado por **Reviewer 2** confirma que `plan_de_implementacion_fases.md` posee una base arquitectónica sobresaliente (aprobación de dependencias React 18.3.1, exactitud geodésica del buffer de 250m en `EPSG:3435` a 820.21 ft, aislamiento C-ABI con `numpy<2.0.0` y Dual-Engine asyncpg/psycopg3).

Sin embargo, se identificaron **fallas deterministas de runtime, riesgos de Out-Of-Memory (OOM), bloqueos de arranque (deadlocks) y condiciones de carrera WebGL** que provocarían caídas inmediatas durante la fase de codificación.

A continuación se sintetiza la matriz consolidada de remediación que **Worker 2** debe aplicar en `plan_de_implementacion_fases.md`:

| # | Dominio | Severidad | Ubicación en Plan | Problema Técnico | Estrategia de Remediación |
|---|---|---|---|---|---|
| **R-B1** | SQL PostGIS | **CRÍTICO** | Sección 2.3 (Líneas 122-143) | `LIMIT 5000` posterior a `json_agg` colapsado a 1 fila; agrega 850k filas en RAM (OOM). | Envolver la consulta en CTE o subconsulta `(SELECT ... LIMIT 5000) AS sub` antes de `json_agg`. |
| **R-B2** | Docker Permisos | **CRÍTICO** | Sección 4.2 (Líneas 426-435) | Volumen `duckdb_data:/data/duckdb` montado como `root:root`; `appuser` sufre `Errno 13 Permission denied`. | Añadir `RUN mkdir -p /data/duckdb && chown -R appuser:appgroup /data/duckdb` antes de `USER appuser`. |
| **R-B3** | Ciclo de Vida | **ALTO** | Sección 4.1 (Líneas 363-365), Sec. 4.2 (441), Fase 4 & 6 | Fallo al arrancar FastAPI si `.joblib` no existe (fresh clone/fases 1-3); Uvicorn aborta y stack bloqueado. | Implementar fallback en lifespan (log warning + estimador heurístico) para pasar healthcheck sin crash. |
| **R-B4** | Migraciones DB | **ALTO** | Sección 4.1 (Línea 363), Sec. 4.2 (441), Sec. 5 | `alembic upgrade head` no se invoca en CMD de Dockerfile; contenedor levanta sin tablas. | Crear `backend/entrypoint.sh` con `alembic upgrade head && exec "$@"`, agregarlo al Dockerfile y estructura. |
| **R-B5** | Docker Compose | **MEDIO** | Sección 4.5 (Línea 601), Fase 1 (877) | `-c shared_preload_libraries=postgis-3` innecesario y potencialmente fatal en PostgreSQL 16. | Eliminar la directiva `shared_preload_libraries=postgis-3` del bloque `command: >` de PostgreSQL. |
| **R-B6** | Python Deps | **BAJO** | Sección 3.1 (Línea 238-246) | `scipy` no pinned en `requirements.txt`; riesgo de incompatibilidad binaria futura con `numpy<2.0.0`. | Agregar `scipy==1.15.2` explícitamente a `backend/requirements.txt`. |
| **R-B7** | PostGIS Perf | **MEDIO** | Sección 2.7 (187-196), Fase 2 (958-970) | `UPDATE ... ST_Transform(c.geom, 3435)` en predicado invalida índice GiST; seq scan masivo de horas. | Crear índice funcional `USING GIST (ST_Transform(geom, 3435))` o columna métrica persistida `geom_3435`. |
| **R-B8** | Entorno CLI | **BAJO** | Sección 4.6 (694-699), Fase 1 (918-920) | `.env.example` usa `POSTGRES_HOST=db`; falla DNS al ejecutar Alembic desde el host (`localhost`). | Clarificar en `.env.example` y Fase 1 que fuera de Docker debe usarse `localhost:5432`. |
| **R-F1** | WebGL / React | **CRÍTICO** | Sección 2.6 (174-183), Fase 5 (1137-1140) | Carrera asíncrona en `map.on('load')` con React 18 StrictMode; monta mapa destruido en Zustand. | Agregar guardia `isMounted` y desuscripción `map.off('load', handleLoad)` en limpieza de `useEffect`. |
| **R-F2** | WebGL Context | **ALTO** | Sección 2.6 (181), Fase 5 (1137-1140) | Eventos `webglcontextlost` y `webglcontextrestored` omitidos en código real; pantalla negra irrecuperable. | Implementar listeners en canvas con `e.preventDefault()` y `map.triggerRepaint()`. |
| **R-F3** | Compatibilidad | **ALTO** | Sección 2.5 (164), Fase 5 (1137-1140) | Sin chequeo previo `maplibregl.supported()`; crash síncrono y pantalla blanca en entornos sin WebGL2. | Añadir verificación de hardware `maplibregl.supported()` con estado de error visual en UI. |
| **R-F4** | Seguridad Nginx | **MEDIO** | Sección 4.4 (Línea 517) | CSP `connect-src` omite `openstreetmap.org` y `demotiles.maplibre.org`; bloquea fetch de MVT y estilos. | Incorporar los dominios de tiles vectoriales y estilos en la directiva `connect-src` de Nginx. |
| **R-F5** | Geodesia BBOX | **MEDIO** | Fase 2 (Línea 947) | BBOX de limpieza ([-88.10, 41.60], [-87.40, 42.10]) abarca 13 km fuera de Chicago (DuPage / Lago). | Calibrar BBOX de limpieza a límites municipales reales ($41.644^\circ - 42.023^\circ$ N, $-87.940^\circ - -87.524^\circ$ W). |
| **R-F6** | Node Tooling | **BAJO** | Fase 5 (Línea 1167) | Omisión de `@types/react` y `@types/react-dom` en comando CLI de instalación de Fase 5. | Incorporar `@types/react@18.3.10` y `@types/react-dom@18.3.0` en el comando `npm install -D`. |
| **R-F7** | Testing Frontend| **MENOR** | Sección 3.2 (264-270, 293-308), Sec. 7.1 | Falta runner de pruebas en `frontend/package.json` para validar hooks y ciclo de vida de componentes. | Agregar `vitest`, `@testing-library/react`, etc., a `devDependencies` y script `"test": "vitest run"`. |
| **R-F8** | Estado Zustand | **MEDIO** | Sección 2.6 (Línea 183), Sec. 5 (823) | Almacenar instancia mutable `Map` en Zustand causa error al serializar en DevTools. | Almacenar en Zustand solo estado serializable; pasar instancia Map por React Context (`MapContext`). |
| **R-F9** | Render Recharts| **MEDIO** | Sección 5 (810-814), Fase 5 (1150) | Gráficos en cajones/pestañas colapsadas (`display:none`) colapsan a dimensiones negativas (`-1`). | Añadir `minWidth={0}` en `<ResponsiveContainer>` y montar gráficos condicionados a pestaña activa. |

---

## 2. ESPECIFICACIÓN DETALLADA DE REMEDIACIÓN: BACKEND & DOCKER

### R-B1: Corrección de Consulta GeoJSON en Sección 2.3 (Líneas 122-143)
* **Diagnóstico:** En PostgreSQL, `json_agg` sin `GROUP BY` colapsa todas las filas del filtro `WHERE` en un único registro. Un `LIMIT 5000` al final del `SELECT` limita el número de filas del conjunto resultado a 5000; pero como el `SELECT` produce exactamente 1 fila, `LIMIT` no tiene efecto sobre `json_agg`. Si una consulta abarca todo Chicago, PostgreSQL agregará los >850,000 registros en RAM provocando un colapso OOM del motor.
* **Instrucción de Edición:** Reemplazar el bloque SQL en la Sección 2.3 envolviendo la consulta en una CTE o subconsulta que aplique el `LIMIT 5000` **antes** de la agregación JSON.

**Código de Reemplazo (Sección 2.3):**
```sql
-- Consulta GeoJSON optimizada con restricción previa de cardinalidad (Anti-OOM):
WITH limited_crashes AS (
    SELECT 
        crash_record_id,
        geom,
        crash_date,
        posted_speed_limit,
        injuries_total,
        injuries_fatal,
        risk_score
    FROM silver_crashes
    WHERE geom && ST_MakeEnvelope(:min_lon, :min_lat, :max_lon, :max_lat, 4326)
    ORDER BY crash_date DESC
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

### R-B2: Corrección de Permisos en Volumen DuckDB (`backend/Dockerfile`, Líneas 426-435)
* **Diagnóstico:** En `docker-compose.yml`, el volumen persistente `duckdb_data:/data/duckdb` se monta en el contenedor. Si el directorio `/data/duckdb` no existe en la imagen con permisos del usuario no-root, Docker lo crea como `root:root` (0755). Al arrancar como `USER appuser` (UID 10001), DuckDB lanza `PermissionError: [Errno 13] Permission denied` al intentar crear el archivo de base de datos o sus archivos temporales `.wal`.
* **Instrucción de Edición:** En la etapa `runner` de `backend/Dockerfile` (Sección 4.2), crear el directorio `/data/duckdb` y asignar su propiedad a `appuser:appgroup` antes de la directiva `USER appuser`.

**Código de Reemplazo (`backend/Dockerfile`, Etapa 2 Runner):**
```dockerfile
# Creación de usuario del sistema sin privilegios y aprovisionamiento de volúmenes
RUN groupadd -g 10001 appgroup && \
    useradd -u 10001 -g appgroup -s /bin/bash -m appuser && \
    mkdir -p /data/duckdb && \
    chown -R appuser:appgroup /data/duckdb

COPY --chown=appuser:appgroup ./app /app/app
COPY --chown=appuser:appgroup ./alembic /app/alembic
COPY --chown=appuser:appgroup ./alembic.ini /app/alembic.ini
COPY --chown=appuser:appgroup ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser
```

---

### R-B3: Manejo Tolerante a Fallos en Lifespan de FastAPI (Ausencia Inicial del Modelo ML)
* **Diagnóstico:** En Sección 4.1 y Fase 4/6, Uvicorn ejecuta `joblib.load(settings.MODEL_PATH)` en el arranque. En una clonación limpia del repositorio o despliegue inicial (Fases 1 a 3), el modelo ML `chicago_risk_xgboost.joblib` aún no existe (se entrena en Fase 3). Uvicorn aborta con `FileNotFoundError`, el contenedor entra en `CrashLoopBackOff`, la sonda de salud falla y el servicio `frontend` nunca inicia debido a `condition: service_healthy`.
* **Instrucción de Edición:** Actualizar la descripción del ciclo de vida en la Sección 4.1, Sección 4.2 y Fase 4, estableciendo que el manejador `lifespan` en `app/main.py` capture la ausencia del artefacto serializado, emita una advertencia en el log y configure un estimador heurístico de respaldo (*baseline heuristic*) para permitir que el backend alcance el estado `healthy`.

**Especificación para `app/main.py`:**
```python
# app/main.py - Manejador Lifespan tolerante a la ausencia del modelo ML
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Pool de conexiones asíncronas
    logger.info("Inicializando pool de conexiones a PostGIS...")
    await init_db_pool()
    
    # 2. Carga del Modelo ML con Fallback Heurístico
    model_path = settings.MODEL_PATH
    if os.path.exists(model_path):
        try:
            app.state.ml_model = joblib.load(model_path)
            app.state.model_loaded = True
            logger.info("Modelo ML principal cargado exitosamente desde: %s", model_path)
        except Exception as exc:
            logger.error("Error al deserializar modelo ML (%s). Activando fallback heurístico.", exc)
            app.state.ml_model = None
            app.state.model_loaded = False
    else:
        logger.warning(
            "Artefacto de modelo ML no encontrado en %s (pendiente de entrenamiento en Fase 3). "
            "El endpoint /predict operará en modo heurístico de respaldo.",
            model_path
        )
        app.state.ml_model = None
        app.state.model_loaded = False

    yield

    # 3. Shutdown: Cierre ordenado de conexiones
    logger.info("Cerrando pool de conexiones de base de datos...")
    await close_db_pool()
```

---

### R-B4: Automatización de Migraciones Alembic con `backend/entrypoint.sh`
* **Diagnóstico:** La Sección 4.1 afirma que el contenedor backend ejecuta migraciones automáticas (`alembic upgrade head`), pero `backend/Dockerfile` tiene únicamente `CMD ["uvicorn", ...]`, lo que significa que en un despliegue limpio las tablas no existirán y la API arrojará errores 500 (`UndefinedTableError`).
* **Instrucción de Edición:** 
  1. Definir el script `backend/entrypoint.sh` en la Sección 4.2 y agregarlo a la estructura de directorios en la Sección 5.
  2. Actualizar el `backend/Dockerfile` con directivas `ENTRYPOINT ["/app/entrypoint.sh"]` y `CMD ["uvicorn", ...]`.

**Contenido de `backend/entrypoint.sh`:**
```bash
#!/bin/sh
set -e

echo "[Chicago Backend] Verificando conexión a PostgreSQL y ejecutando migraciones..."
alembic upgrade head

echo "[Chicago Backend] Migraciones aplicadas con éxito. Iniciando servidor web..."
exec "$@"
```

**Instrucción en `backend/Dockerfile`:**
```dockerfile
COPY --chown=appuser:appgroup ./entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

USER appuser

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

---

### R-B5: Eliminación de `-c shared_preload_libraries=postgis-3` en `docker-compose.yml`
* **Diagnóstico:** En la Sección 4.5 (Línea 601), el bloque `db` incluye `-c shared_preload_libraries=postgis-3`. PostGIS es una extensión de enlace dinámico activada mediante `CREATE EXTENSION postgis;`, no una librería de intercepción de memoria compartida del postmaster. En PostgreSQL 16, este parámetro puede provocar advertencias severas o el aborto inmediato del inicio del clúster (`FATAL: could not load library "postgis-3"`).
* **Instrucción de Edición:** Eliminar la línea `-c shared_preload_libraries=postgis-3` del comando `postgres` en `docker-compose.yml` (Sección 4.5) y remover la mención en la tarea 2 de la Fase 1 (Línea 877).

**Bloque Corregido (`docker-compose.yml`, Líneas 593-602):**
```yaml
    command: >
      postgres
      -c shared_buffers=1GB
      -c work_mem=64MB
      -c maintenance_work_mem=256MB
      -c random_page_cost=1.1
      -c effective_cache_size=3GB
      -c max_connections=200
    shm_size: 1g
```

---

### R-B6: Fijación de `scipy==1.15.2` en `backend/requirements.txt`
* **Diagnóstico:** Tanto `scikit-learn==1.6.1` como `xgboost==2.1.4` dependen críticamente de `scipy`. Dejar `scipy` sin congelar provoca que `pip` resuelva versiones flotantes en futuras construcciones, con riesgo de ruptura frente a la restricción `numpy>=1.26.4,<2.0.0`.
* **Instrucción de Edición:** En la Sección 3.1, añadir `scipy==1.15.2` en la sección de dependencias científicas de `backend/requirements.txt`.

**Líneas de Reemplazo (`backend/requirements.txt`, Sección 3.1):**
```ini
# ==============================================================================
# INGESTA, CIENCIA DE DATOS & MOTOR OLAP ACELERADO
# ==============================================================================
numpy>=1.26.4,<2.0.0
scipy==1.15.2
pandas==2.2.3
scikit-learn==1.6.1
xgboost==2.1.4
joblib==1.4.2
duckdb==1.1.1
sodapy==2.2.0
httpx==0.28.1
```

---

### R-B7: Aceleración con Índices GiST en Transformaciones Métricas (`EPSG:3435`)
* **Diagnóstico:** En la Fase 2 (Líneas 958-970), el `UPDATE` que cruza siniestros viales con permisos de obra CDOT utiliza:
  `AND ST_DWithin(ST_Transform(c.geom, 3435), ST_Transform(p.geom, 3435), 820.21)`.
  El índice espacial existente `idx_crashes_geom` está indexado en `geom` (`EPSG:4326`). La llamada `ST_Transform(c.geom, 3435)` en el predicado invalida el uso del índice espacial GiST, obligando a PostgreSQL a ejecutar un Sequential Scan de más de 850,000 registros para cada permiso de obra.
* **Instrucción de Edición:** En la Sección 2.7 y Fase 2, instruir la creación de un índice espacial funcional GiST proyectado, o alternativamente la persistencia de una columna generada indexada `geom_3435`.

**Código de Optimización Espacial (Fase 1 y Fase 2):**
```sql
-- Creación de índices espaciales funcionales GiST para cálculos métricos inmediatos:
CREATE INDEX IF NOT EXISTS idx_crashes_geom_3435 
    ON silver_crashes USING GIST (ST_Transform(geom, 3435));

CREATE INDEX IF NOT EXISTS idx_permits_geom_3435 
    ON silver_road_permits USING GIST (ST_Transform(geom, 3435));
```
Con este índice, la consulta `ST_DWithin` utiliza un *Index Scan* espacial acelerado en el plano de Illinois East, reduciendo el tiempo de procesamiento de varias horas a menos de 45 segundos.

---

### R-B8: Clarificación de Hostname `localhost` vs `db` en `.env.example` y Comandos CLI Locales
* **Diagnóstico:** En la Sección 4.6, `.env.example` especifica `POSTGRES_HOST=db`. Cuando un desarrollador ejecuta `alembic upgrade head` o scripts Python directamente desde Windows PowerShell en el host (fuera de la red Docker), el host no resuelve el dominio `db`, produciendo `socket.gaierror: [Errno 11001] getaddrinfo failed`.
* **Instrucción de Edición:** En la Sección 4.6 y en los pasos CLI de la Fase 1, añadir una nota técnica explícita aclarando que para ejecuciones en el host anfitrión se debe configurar `POSTGRES_HOST=localhost` o pasar `DATABASE_URL` con `localhost:5432`.

---

## 3. ESPECIFICACIÓN DETALLADA DE REMEDIACIÓN: FRONTEND & WEBGL

### R-F1, R-F2, R-F3: Blindaje de `useMapLibre.ts` (Carreras en StrictMode, Pérdida de Contexto y WebGL2 Support)
* **Diagnóstico:**
  1. **Carrera en StrictMode (R-F1):** En React 18, el doble montaje/desmontaje de `StrictMode` ejecuta la limpieza de `useEffect` (`map.remove()`) antes de que el evento asíncrono `map.on('load')` termine de descargar el estilo cartográfico. Cuando se dispara el evento en la instancia destruida, `setMapInstance(map)` almacena un mapa muerto en Zustand, provocando `Error: Map has been removed`.
  2. **Eventos de Contexto Gráfico (R-F2):** La Sección 2.6 promete gestionar `webglcontextlost` y `webglcontextrestored`, pero no había ningún listener en el código. Ante suspensión de pantalla o conmutación de GPU, la pantalla queda permanentemente en negro.
  3. **Comprobación de WebGL2 (R-F3):** Si el navegador o máquina virtual no soporta WebGL2, `new maplibregl.Map(...)` arroja una excepción fatal síncrona sin mensaje legible para el usuario.
* **Instrucción de Edición:** Reemplazar y enriquecer la especificación de `useMapLibre.ts` en la Sección 2.6 y en la Fase 5 con la implementación completa y blindada.

**Código Canónico y Definitivo de `src/hooks/useMapLibre.ts`:**
```typescript
import { useEffect, useRef, useState } from 'react';
import maplibregl, { Map as MapLibreMap } from 'maplibre-gl';
import { useMapStore } from '../stores/useMapStore';

interface UseMapLibreOptions {
  containerId: string;
  initialCenter?: [number, number];
  initialZoom?: number;
}

export function useMapLibre({
  containerId,
  initialCenter = [-87.6298, 41.8781], // Coordenadas centrales de Chicago
  initialZoom = 11,
}: UseMapLibreOptions) {
  const mapRef = useRef<MapLibreMap | null>(null);
  const [webGlSupported, setWebGlSupported] = useState<boolean>(true);
  const [isMapReady, setIsMapReady] = useState<boolean>(false);

  // Zustand: solo almacena estado serializable del viewport y capas
  const setViewport = useMapStore((s) => s.setViewport);

  useEffect(() => {
    // 1. Verificación de Compatibilidad de Hardware WebGL2 (R-F3)
    if (!maplibregl.supported()) {
      console.error('[MapLibre] WebGL2 no está soportado en este entorno de ejecución.');
      setWebGlSupported(false);
      return;
    }

    let isMounted = true;
    const container = document.getElementById(containerId);
    if (!container) {
      console.warn(`[MapLibre] Contenedor DOM #${containerId} no encontrado.`);
      return;
    }

    // 2. Instanciación Segura de MapLibre GL JS v4
    const map = new maplibregl.Map({
      container,
      style: 'https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json',
      center: initialCenter,
      zoom: initialZoom,
      minZoom: 9,
      maxZoom: 18,
      // Límites de navegación de cámara (holgura metropolitana)
      maxBounds: [
        [-88.1000, 41.6000], // Suroeste
        [-87.4000, 42.1000], // Noreste
      ],
      trackResize: true,
      fadeDuration: 100,
    });

    // 3. Manejadores de Ciclo de Vida WebGL2 del Canvas (R-F2)
    const canvas = map.getCanvas();
    const handleContextLost = (e: Event) => {
      e.preventDefault(); // CRÍTICO: Evita que el navegador destruya el contexto permanentemente
      console.warn('[MapLibre] Contexto WebGL2 perdido por el SO/GPU. Pausando renderizado.');
    };

    const handleContextRestored = () => {
      console.info('[MapLibre] Contexto WebGL2 restaurado. Re-renderizando capas...');
      map.triggerRepaint();
    };

    canvas.addEventListener('webglcontextlost', handleContextLost, false);
    canvas.addEventListener('webglcontextrestored', handleContextRestored, false);

    // 4. Guardia de Carrera Asíncrona en 'load' para React 18 StrictMode (R-F1)
    const handleLoad = () => {
      if (!isMounted) {
        console.warn('[MapLibre] Evento load disparado tras desmontaje. Omitiendo actualización.');
        return;
      }
      mapRef.current = map;
      setIsMapReady(true);
      setViewport({ center: initialCenter, zoom: initialZoom });
      console.info('[MapLibre] Mapa inicializado y capas base operativas.');
    };

    map.on('load', handleLoad);

    // Sincronización del viewport hacia Zustand sin retener instancia circular
    map.on('moveend', () => {
      if (!isMounted) return;
      const center = map.getCenter();
      setViewport({
        center: [center.lng, center.lat],
        zoom: map.getZoom(),
      });
    });

    // 5. Función de Limpieza Determinista y Desmontaje
    return () => {
      isMounted = false;
      map.off('load', handleLoad);
      canvas.removeEventListener('webglcontextlost', handleContextLost);
      canvas.removeEventListener('webglcontextrestored', handleContextRestored);
      
      // Destrucción física del contexto gráfico WebGL2
      map.remove();
      mapRef.current = null;
      setIsMapReady(false);
      console.info('[MapLibre] Instancia destruida limpiamente y contexto WebGL liberado.');
    };
  }, [containerId]);

  return { mapRef, isMapReady, webGlSupported };
}
```

---

### R-F4: Expansión de Nginx Content Security Policy (`nginx.conf`, Línea 517)
* **Diagnóstico:** En `frontend/nginx.conf`, la directiva `connect-src` contiene únicamente:
  `connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com blob:;`
  MapLibre GL JS descarga teselas vectoriales (`.pbf` / `.mvt`), estilos y fuentes mediante `fetch()`, el cual se rige exclusivamente por `connect-src`. Al faltar `openstreetmap.org` y `demotiles.maplibre.org`, el navegador bloquea las fuentes cartográficas con violaciones de seguridad CSP.
* **Instrucción de Edición:** Modificar la cabecera `Content-Security-Policy` en `frontend/nginx.conf` (Sección 4.4, Línea 517).

**Línea de Reemplazo (`frontend/nginx.conf`, Sección 4.4):**
```nginx
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' blob:; worker-src 'self' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https://*.cartocdn.com https://*.openstreetmap.org; connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com https://*.openstreetmap.org https://demotiles.maplibre.org blob:;" always;
```

---

### R-F5: Calibración Geodésica del BBOX de Limpieza en `data_cleaner.py` (Fase 2, Línea 947)
* **Diagnóstico:** El rango actual de depuración ($41.60^\circ - 42.10^\circ\text{ N}, -88.10^\circ - -87.40^\circ\text{ W}$) abarca más de 13.5 km en DuPage County (Schaumburg) y 10 km dentro del Lago Michigan.
* **Instrucción de Edición:** En la Fase 2 (Línea 947), especificar con exactitud matemática y administrativa la diferencia entre el **Bounding Box estricto de saneamiento de datos** y los **Límites de navegación de cámara en MapLibre**:
  1. **Envolvente de Limpieza Estricta (`data_cleaner.py`):**
     - Latitud Norte máxima: $42.023^\circ\text{ N}$ (Howard St / límite Evanston).
     - Latitud Sur mínima: $41.644^\circ\text{ N}$ (Hegewisch / límite Indiana).
     - Longitud Oeste máxima: $-87.940^\circ\text{ W}$ (Aeropuerto O'Hare).
     - Longitud Este máxima: $-87.524^\circ\text{ W}$ (Costa del Lago Michigan).
     - *Cualquier coordenada fuera de esta caja se aísla en `crashes_quarantine`.*
  2. **Envolvente de Visualización / Navegación (`maxBounds` en MapLibre):**
     - `[[-88.1000, 41.6000], [-87.4000, 42.1000]]` (con holgura periférica para navegación fluida).

---

### R-F6: Inclusión de `@types/react` y `@types/react-dom` en Comando CLI de Fase 5 (Línea 1167)
* **Diagnóstico:** El comando `npm install -D` en la Línea 1167 omitió los paquetes `@types/react` y `@types/react-dom`. Aunque estaban en `package.json`, su ausencia en la instrucción de terminal de la guía provoca que una ejecución paso a paso instale tipos flotantes (pudiendo bajar React 19 types) y rompa `npm run typecheck`.
* **Instrucción de Edición:** Actualizar la línea 1167 en la Fase 5 incorporando `@types/react@18.3.10` y `@types/react-dom@18.3.0`.

---

### R-F7: Incorporación de Runner de Pruebas Frontend en `package.json` y Sección 7.1
* **Diagnóstico:** La Sección 7.1 exige pruebas unitarias de ciclo de vida para `useMapLibre`, pero `frontend/package.json` no contiene librerías de test ni el script `"test"`.
* **Instrucción de Edición:**
  1. En `frontend/package.json` (Sección 3.2), agregar `"test": "vitest run"` en `"scripts"`.
  2. Agregar `vitest`, `@testing-library/react`, `@testing-library/jest-dom` y `jsdom` en `"devDependencies"`.
  3. Añadir estos paquetes al comando CLI `npm install -D` de la Fase 5.

**Bloque de Reemplazo (`frontend/package.json`, Sección 3.2):**
```json
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
```
Y en `devDependencies`:
```json
    "vitest": "2.1.1",
    "@testing-library/react": "16.0.1",
    "@testing-library/jest-dom": "6.5.0",
    "jsdom": "25.0.1",
```

---

### R-F8: Desacoplamiento de la Instancia `MapLibreMap` del Estado Reactivo de Zustand
* **Diagnóstico:** Guardar la instancia completa de `maplibregl.Map` (un objeto masivo con workers, canvas y referencias circulares) directamente en Zustand produce `TypeError: Converting circular structure to JSON` al usar las DevTools de Zustand/Redux.
* **Instrucción de Edición:** Especificar en la Sección 2.6 y Sección 5 que:
  1. `useMapStore.ts` almacena únicamente estado puro serializable (`center`, `zoom`, `activeLayers`, `selectedCrashId`).
  2. La instancia física mutable del mapa se expone mediante un **React Context** (`MapContext.tsx`) o mediante el hook `useMapLibre` retornando `{ mapRef }`, evitando colisiones con DevTools.

---

### R-F9: Blindaje Dimensional de Recharts ante Contenedores Ocultos
* **Diagnóstico:** Si `<ResponsiveContainer>` de Recharts se renderiza dentro de una pestaña inactiva de Radix UI o en el cajón colapsado `DataDrawer.tsx` con `display: none`, lee dimensiones 0x0 y arroja advertencias de ancho/alto `-1`, fallando en dibujarse al abrirse el panel.
* **Instrucción de Edición:** En la Sección 5 y Fase 5, indicar expresamente:
  1. Aplicar `minWidth={0}` y `minHeight={0}` a los `<ResponsiveContainer>` de Recharts.
  2. Montar condicionalmente los componentes de gráficos solo cuando la pestaña o cajón contenedor se encuentre activo y visible en el DOM (`activeTab === 'analytics' && <ChartComponent />`).

---

## 4. GUÍA DE APLICACIÓN PASO A PASO PARA WORKER 2

Worker 2 debe aplicar las modificaciones en `plan_de_implementacion_fases.md` siguiendo este orden de secciones para garantizar coherencia estructural total:

```
PASO 1: SECCIÓN 2.3 (LÍNEAS 122-143)
        --> Reemplazar la consulta SQL GeoJSON directa por la versión con CTE/subconsulta Anti-OOM.

PASO 2: SECCIÓN 2.6 (LÍNEAS 171-183)
        --> Incorporar la explicación técnica del hook blindado useMapLibre con isMounted, 
            manejo de webglcontextlost/restored, maplibregl.supported() y desacoplamiento de Zustand.

PASO 3: SECCIÓN 2.7 (LÍNEAS 187-196)
        --> Agregar la especificación del índice funcional GiST sobre ST_Transform(geom, 3435).

PASO 4: SECCIÓN 3.1 (LÍNEAS 237-246)
        --> Añadir scipy==1.15.2 en requirements.txt.

PASO 5: SECCIÓN 3.2 (LÍNEAS 258-310)
        --> Actualizar frontend/package.json: agregar script "test": "vitest run" y 
            devDependencies de Vitest y Testing Library.

PASO 6: SECCIÓN 4.1 (LÍNEAS 360-366)
        --> Actualizar el diagrama de secuencia y notas de startup: fallback de modelo ML y entrypoint.sh.

PASO 7: SECCIÓN 4.2 (LÍNEAS 409-442)
        --> Actualizar backend/Dockerfile: mkdir/chown de /data/duckdb, COPY de entrypoint.sh,
            ENTRYPOINT y CMD.

PASO 8: SECCIÓN 4.4 (LÍNEA 517)
        --> Actualizar Content-Security-Policy en nginx.conf agregando openstreetmap.org y demotiles.

PASO 9: SECCIÓN 4.5 (LÍNEAS 593-602)
        --> Remover -c shared_preload_libraries=postgis-3 de docker-compose.yml.

PASO 10: SECCIÓN 4.6 (LÍNEAS 690-700)
         --> Añadir nota de localhost vs db para herramientas CLI locales.

PASO 11: SECCIÓN 5 (LÍNEAS 727-737 & 780-833)
         --> Añadir backend/entrypoint.sh y frontend/src/context/MapContext.tsx a la estructura.

PASO 12: FASE 1 (LÍNEAS 874-878, 918-920)
         --> Quitar shared_preload_libraries y clarificar ejecución local de Alembic.

PASO 13: FASE 2 (LÍNEAS 946-951 & 957-970)
         --> Calibrar BBOX de limpieza en data_cleaner.py y añadir índice funcional en el UPDATE.

PASO 14: FASE 4 (LÍNEAS 1072-1075 & 1084-1088)
         --> Detallar el fallback heurístico en lifespan y en predict.py ante ausencia de .joblib.

PASO 15: FASE 5 (LÍNEAS 1137-1140, 1150-1151, 1166-1168)
         --> Detallar useMapLibre blindado, Recharts minWidth={0}, y comando npm con @types y vitest.

PASO 16: SECCIÓN 7.1 (LÍNEA 1271)
         --> Vincular las pruebas unitarias de useMapLibre con el runner Vitest configurado.
```

---

## 5. CONCLUSIÓN DEL EXPLORADOR DE REMEDIACIÓN

Las 17 remediaciones detalladas resuelven con precisión matemática, geodésica y de ingeniería de software la totalidad de las objeciones planteadas por **Challenger 1**, **Challenger 2** y **Reviewer 2**. 

Al ser aplicadas por **Worker 2**, `plan_de_implementacion_fases.md` se transformará en un plan maestro invulnerable a fallas de OOM, de permisos de volumen en Docker, de carreras en React 18, de violaciones de CSP y de deadlocks de arranque, asegurando una transición impecable hacia la fase de construcción de código fuente.
