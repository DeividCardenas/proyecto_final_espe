# PLAN MAESTRO DE IMPLEMENTACIÓN POR FASES Y SPRINTS TÉCNICOS
## Proyecto: Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales y Movilidad Urbana en la Ciudad de Chicago

**Documento:** Plan Canónico y Exhaustivo de Implementación (`plan_de_implementacion_fases.md`)  
**Versión:** 1.0.0 — Línea Base de Ingeniería  
**Fecha de Emisión:** 12 de septiembre de 2026  
**Líder Técnico & Arquitecto:** Lead Technical Architect & Implementation Planner (`worker_1`)  
**Estado:** Aprobado para Revisión, Auditoría y Ejecución  

---

## 1. RESUMEN EJECUTIVO Y METADATOS DEL PROYECTO

### 1.1 Título Formal y Naturaleza del Proyecto
El proyecto se titula formalmente **«Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales y Movilidad Urbana»**, enfocado en la red vial metropolitana de la **Ciudad de Chicago (Illinois, EE.UU.)**.

Consiste en el diseño, desarrollo, validación y despliegue de una plataforma analítica de datos abiertos, 100% contenerizada mediante Docker, basada en una **Arquitectura Medallón (Bronze, Silver, Gold)**, almacenamiento y procesamiento geoespacial avanzado con **PostgreSQL 16 y PostGIS 3.4**, servicios web asíncronos con **FastAPI**, modelos supervisados de Machine Learning (**Random Forest y XGBoost**) y una interfaz cartográfica reactiva de alto rendimiento con **React 18, TypeScript y MapLibre GL JS v4 (WebGL2)**.

### 1.2 Contexto de Datos y Problemática Urbana
Tradicionalmente, las administraciones municipales gestionan la seguridad vial de forma reactiva: se interviene un cruce o tramo tras la acumulación trágica de siniestros. La Ciudad de Chicago publica en su portal de datos abiertos (*City of Chicago Open Data Portal*) millones de registros que han permanecido en silos operacionales independientes. Este proyecto consolida, depura y correlaciona espacial y temporalmente tres fuentes de datos críticas:
1. **Siniestralidad Vial (Traffic Crashes - CPD):** Un universo acumulado superior a **850,000 colisiones viales**, con más de **1,700,000 registros de vehículos** y más de **2,000,000 de registros de personas/víctimas involucradas** (totalizando más de 4.5 millones de entidades relacionales).
2. **Volúmenes de Tráfico Promedio Diario (AADT - CDOT):** Decenas de miles de aforos vehiculares en puntos neurálgicos de la red vial para medir la exposición real al riesgo.
3. **Permisos de Obra e Intervención en Vía Pública (CDOT Road Closure Permits):** Registros históricos y activos de cierres totales o parciales de calles y aceras por obras civiles.
4. **Capas Complementarias:** Red de límites de velocidad reglamentarios (*Speed Limits*) y ubicación de cámaras de fotomulta en semáforos en rojo (*Red Light Cameras*).

El sistema responde a dos preguntas rectoras:
* **Pregunta Problema:** *¿En qué medida los patrones temporales, las características del flujo vehicular y la presencia de alteraciones viales por obras inciden en la probabilidad y severidad de los siniestros de tránsito en la red urbana de Chicago, y con qué nivel de precisión pueden anticiparse los segmentos de alto riesgo mediante modelos de aprendizaje automático?*
* **Pregunta de Decisión:** *¿Cómo deben priorizarse y asignarse las intervenciones preventivas (control operativo de velocidad, señalización y adecuación de infraestructura) en los tramos críticos clasificados por el modelo, para maximizar la mitigación de siniestros graves y fatales bajo restricciones presupuestales?*

El marco metodológico adopta las directrices de iniciativas globales de probada eficacia como **Vision Zero** (Nueva York), el **Crash Analysis System (CAS)** de Nueva Zelanda y el protocolo de calificación por estrellas de **iRAP** (*International Road Assessment Programme*).

### 1.3 Objetivos Específicos y Entregables Formales

| Objetivo Específico | Denominación del Entregable Oficial | Descripción Técnica y Artefactos Asociados | Criterio de Aceptación Clave |
|---|---|---|---|
| **OE1** | **Repositorio de Datos Geoespacial Contenerizado** | Imagen y volumen Docker de PostgreSQL 16 + PostGIS 3.4. Esquema relacional optimizado, claves foráneas, restricciones de integridad, índices espaciales GiST en WGS84 (`EPSG:4326`) y transformaciones métricas (`EPSG:3435`). | Despliegue en < 2 minutos; verificación de integridad referencial al 100%; ejecución de clustering espacial de tablas. |
| **OE2** | **Pipeline ETL y Dataset Curado y Enriquecido** | Scripts en Python modularizados para ingesta incremental desde API SODA, módulo de depuración (saneamiento de coordenadas nulas y atípicas), transformación geográfica y algoritmo de cruce topológico espaciotemporal (Buffer de 250 metros). | Tasa de éxito de procesamiento > 95%; duplicados < 1%; completitud en atributos críticos ≥ 95%; tiempos de consulta analítica en DuckDB/Parquet sub-segundo. |
| **OE3** | **Modelos Predictivos Serializados y Evaluación** | Modelos de Machine Learning supervisados (Random Forest y XGBoost) entrenados y evaluados bajo validación cruzada (5-fold CV), empaquetados en archivo binario serializado `.joblib`. | AUC-ROC global ≥ 0.70; Recall ≥ 0.60 para siniestros de alta severidad (lesiones graves/fatales); Precision ≥ 0.65 en alto riesgo; estabilidad estadística con varianza < 5% entre folds. |
| **OE4** | **Plataforma Web Analítica y Dashboard Cartográfico** | Servicio API REST asíncrono con FastAPI (endpoints GeoJSON de alto rendimiento, consultas BBOX y predicción en vivo) integrado a un Frontend en React 18 + MapLibre GL JS v4 (WebGL2) con componentes analíticos (Chart.js / Recharts) y virtualización tabular. | Tiempo de respuesta de API < 2.0 s; renderizado fluido a 60 FPS en pan/zoom; filtrado reactivo inmediato por GPU; empaquetamiento total en `docker-compose.yml`. |

### 1.4 Equipo del Proyecto, Roles y Gobernanza
De acuerdo con la Ficha Canónica de Proyecto (`FichaDeProyecto_EspBigData_Completada.docx`), los roles y responsabilidades se asignan como sigue:

```
+----------------------------------------------------------------------------------------------------+
|                                    ESTRUCTURA DE GOBERNANZA DEL PROYECTO                           |
+----------------------------------------------------------------------------------------------------+
|  TUTOR & SPONSOR ACADÉMICO: Mag. José Camilo Eraso | Institución: UNICESMAG                        |
+----------------------------------------------------------------------------------------------------+
                                                  |
         +----------------------------------------+----------------------------------------+
         |                                        |                                        |
         v                                        v                                        v
+-----------------------+        +--------------------------------+       +--------------------------+
| DEIVID JULIAN         |        | DILLAN ALEXANDER               |       | CAMILO                   |
| CARDENAS MELO         |        | CARDENAS MELO                  |       | ESCANDÓN ROMERO          |
| Ingeniero de Datos /  |        | Científico de Datos /          |       | Desarrollador Web /      |
| Líder de Proyecto     |        | Modelador Predictivo           |       | Especialista BI & QA     |
+-----------------------+        +--------------------------------+       +--------------------------+
| - Arquitectura DB     |        | - Análisis Exploratorio (EDA)  |       | - Frontend React 18 SPA  |
| - Pipeline SODA ETL   |        | - Feature Engineering          |       | - MapLibre GL JS v4      |
| - Integridad PostGIS  |        | - Modelado RF & XGBoost        |       | - Visualización Gráfica  |
| - Docker Orchestration|        | - Optimización de Métricas     |       | - Pruebas E2E y Calidad  |
+-----------------------+        +--------------------------------+       +--------------------------+
```

### 1.5 Restricciones y Parámetros Operativos
* **Horizonte Temporal Estricto:** 13 semanas académicas (Inicio: 15 de agosto de 2026; Entrega y Defensa: 15 y 16 de noviembre de 2026).
* **Carga Horaria Estimada:** ~270 horas-hombre totales (~20 horas semanales conjuntas).
* **Cero Costo en Nube:** Exclusión total de servicios cloud propietarios pagos (AWS, Google Cloud, Azure). Toda la infraestructura debe correr de forma local y autocontenida en Docker.
* **Anonimización Estricta de Datos:** Prohibición absoluta de almacenar o procesar Información de Identificación Personal (PII) de los ciudadanos involucrados en colisiones viales.

---

## 2. ANÁLISIS DE VIABILIDAD Y RIESGOS TÉCNICOS

Esta sección valida críticamente el stack tecnológico seleccionado frente a las características intrínsecas del volumen masivo de datos de Chicago (>4.5 millones de registros y consultas espaciales complejas), identificando las trampas de ingeniería y sus soluciones arquitectónicas definitivas.

```
+----------------------------------------------------------------------------------------------------+
|                                MATRIZ DE RIESGOS TÉCNICOS Y FACTIBILIDAD                           |
+----+--------------------------------------------+----------+------------+--------------------------+
| ID | Dominio de Riesgo                          | Nivel    | Probabil.  | Impacto Operativo        |
+----+--------------------------------------------+----------+------------+--------------------------+
| R1 | Distorsión Métrica en EPSG:4326 vs 3435    | CRÍTICO  | ALTA       | Error de buffer > 25%    |
| R2 | Incompatibilidad de Tipos OID en asyncpg   | CRÍTICO  | ALTA       | Ruptura de API FastAPI   |
| R3 | Sobrecarga de Serialización GeoJSON        | ALTO     | ALTA       | Latencias > 2.5s y OOM   |
| R4 | Trampas de Migración Alembic con PostGIS   | CRÍTICO  | ALTA       | Drop accidental de tablas|
| R5 | Colapso de Rendimiento en Leaflet DOM/SVG  | CRÍTICO  | ALTA       | Congelamiento de navegador|
| R6 | Fugas de Memoria WebGL por Múltiples Mapas | ALTO     | MEDIA      | Pantalla negra / Crash   |
| R7 | Dispersión de E/S en Disco sin Clustering  | MEDIO    | ALTA       | Degeneración de BBOX Qry |
| R8 | Conflicto de Ruptura de ABI con NumPy 2.0  | CRÍTICO  | ALTA       | Fallo de scikit-learn    |
+----+--------------------------------------------+----------+------------+--------------------------+
```

### 2.1 Validación Crítica del Sistema de Coordenadas (CRS) y Buffers Métricos (R1)
* **Problema Identificado:** Los datos crudos provistos por el portal SODA de Chicago se encuentran en coordenadas geográficas WGS84 (`EPSG:4326`, latitud/longitud decimal). Sin embargo, calcular un radio de influencia (*Buffer*) de 250 metros directamente sobre grados decimales mediante álgebra euclidiana convencional incurre en un error geométrico severo. A la latitud de Chicago (~41.8781° N), $1^\circ$ de longitud equivale aproximadamente a $82.9\text{ km}$, mientras que $1^\circ$ de latitud equivale a $111.0\text{ km}$. Un buffer generado con un radio fijo en grados genera una elipse deformada con una distorsión métrica superior al 25%.
* **Decisión y Solución Arquitectónica:**
  1. Almacenamiento estándar e intercambio web en **WGS84 (`EPSG:4326`)** para total interoperabilidad con MapLibre GL JS y GeoJSON RFC 7946.
  2. Ejecución de análisis topológico métrico exacto mediante proyección planar a **Illinois State Plane East (`EPSG:3435`, NAD83 en survey feet)** o su variante métrica (`EPSG:26971`):
     ```sql
     -- Cálculo de proximidad exacto de 250 metros (820.21 survey feet):
     ST_DWithin(
         ST_Transform(crashes.geom, 3435),
         ST_Transform(permits.geom, 3435),
         820.21
     )
     ```
  3. No se utiliza el tipo `GEOGRAPHY(Point, 4326)` para almacenamiento principal debido a que los cálculos esferoidales sobre el elipsoide WGS84 demandan entre un 300% y 500% más ciclos de CPU que las operaciones planas en coordenadas proyectadas, impidiendo además el uso eficiente de `ST_ClusterDBSCAN`.

### 2.2 Validación del Driver de Base de Datos: Patrón Dual-Engine (`asyncpg` vs `psycopg3`) (R2)
* **Problema Identificado:** FastAPI requiere un bucle de eventos asíncrono para sostener miles de conexiones concurrentes sin agotar los hilos de trabajo. `asyncpg` es el driver asíncrono de mayor rendimiento para PostgreSQL. No obstante, `asyncpg` implementa su propio protocolo binario en Cython y no reconoce dinámicamente los OIDs de tipos de datos definidos por extensiones (como `geometry` de PostGIS). Al ejecutar una consulta que retorne una columna de geometría cruda, `asyncpg` arroja la excepción bloqueante:
  `asyncpg.exceptions.UnknownTypeError: type "geometry" (OID 16390) is not supported in binary format`.
* **Decisión y Solución Arquitectónica (Dual-Engine Pattern):**
  1. **Motor Asíncrono de Runtime (FastAPI):** Se utiliza `postgresql+asyncpg://` acoplado a **GeoAlchemy2**. GeoAlchemy2 envuelve automáticamente las columnas mapeadas con `ST_AsEWKB()`, devolviendo bytes en formato `BYTEA` que `asyncpg` decodifica de forma nativa sin generar errores de OID.
  2. **Motor Síncrono de Gestión (Alembic & Batch ETL):** Se utiliza `postgresql+psycopg://` (`psycopg3`). Las migraciones de Alembic y las cargas masivas de datos se ejecutan en modo síncrono limpio y predecible, evitando lidiar con bucles de eventos asíncronos en tareas de terminal y CLI.

### 2.3 Serialización GeoJSON Nativa en SQL vs Serialización Python (R3)
* **Problema Identificado:** Si el backend extrae entidades espaciales desde PostGIS a través de SQLAlchemy, las transforma en objetos Shapely, las valida con modelos Pydantic y las serializa con `json.dumps()`, el tiempo de CPU requerido para procesar un lote de 15,000 registros viales supera los **2,000 ms a 3,500 ms**, elevando el consumo de memoria RAM en el contenedor a más de 600 MB por petición.
* **Decisión y Solución Arquitectónica:**
   1. Delegar la construcción del estándar GeoJSON FeatureCollection **directamente al motor C de PostgreSQL 16** mediante `ST_AsGeoJSON()` y `json_build_object()`. Para erradicar el riesgo de Out-Of-Memory (OOM) por agregación desbordada, se restringe la cardinalidad **antes** de la agregación mediante una Common Table Expression (CTE), ya que un `LIMIT` posterior a un `json_agg` sin `GROUP BY` operaría sobre una única fila colapsada sin restringir los >850,000 registros evaluados en RAM:
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
  2. FastAPI devuelve el resultado directamente mediante un `Response(content=raw_geojson, media_type="application/geo+json")`. El tiempo de respuesta cae a **< 65 ms** y el consumo de RAM en Python es despreciable.
  3. Para extracciones masivas sin límite de viewport (>50,000 puntos), se implementa un endpoint de streaming que utiliza `StreamingResponse` y el formato delimitado por líneas **NDJSON** (*Newline Delimited JSON*), evitando la saturación del heap de memoria.

### 2.4 Blindaje de Migraciones Alembic con PostGIS (R4)
* **Problema Identificado:** Al ejecutar `alembic revision --autogenerate`, Alembic sufre cuatro fallos críticos:
  1. Intenta eliminar las tablas de catálogo interno creadas por PostGIS (`spatial_ref_sys`, `geometry_columns`, etc.) mediante directivas `op.drop_table()`.
  2. Intenta duplicar la creación de índices espaciales GiST que PostgreSQL genera implícitamente con `Geometry(..., spatial_index=True)`.
  3. No incluye la sentencia `CREATE EXTENSION postgis;` antes de evaluar columnas geométricas.
  4. Omite el import del módulo `geoalchemy2` en los archivos de migración generados.
* **Decisión y Solución Arquitectónica:**
  Configurar obligatoriamente el archivo `alembic/env.py` utilizando los hooks oficiales de **`geoalchemy2.alembic_helpers`**:
  - `include_object = alembic_helpers.include_object`: ignora las tablas del sistema PostGIS.
  - `process_revision_directives = alembic_helpers.writer`: formatea las llamadas DDL y añade los imports necesarios de GeoAlchemy2.
  - `render_item = alembic_helpers.render_item`: previene la duplicación de índices GiST.
  - Creación de una migración inicial manual (`0001_initial_postgis_setup.py`) que ejecuta `CREATE EXTENSION IF NOT EXISTS postgis;`.

### 2.5 Comparativa Crítica de Cartografía Web: MapLibre GL JS v4 vs Leaflet.js (R5)
* **Problema Identificado:** La Ficha de Proyecto preliminar sugería Leaflet.js. No obstante, Leaflet renderiza elementos como nodos individuales dentro del árbol DOM o sobre un canvas 2D básico. Intentar renderizar más de 3,000 marcadores simultáneos de siniestros viales en Leaflet causa congelamiento del hilo principal del navegador, caídas de tasa de refresco por debajo de 5 FPS y colapso de la pestaña.
* **Decisión y Solución Arquitectónica:**
  Se adopta de forma definitiva e irrevocable **MapLibre GL JS v4**, justificado en los siguientes puntos técnicos:
  1. **Aceleración por Hardware WebGL2:** Procesa cientos de miles de entidades geométricas directamente en la tarjeta gráfica (GPU) mediante *shaders* de vértices y fragmentos, sosteniendo 60 FPS estables.
  2. **Filtrado Inmediato en GPU sin Redibujado del DOM:** Al mover el slider de horas del día o conmutar tipos de colisión, se invoca `map.setFilter()`. MapLibre recalcula los uniformes de la GPU en **0 ms de latencia**, sin requerir peticiones de red ni ciclos de recolección de basura de JavaScript.
  3. **Estrategia de Renderizado en 3 Niveles (3-Tier Rendering):**
     - **Nivel 1 (0 – 5,000 entidades):** GeoJSON directo en memoria de la GPU.
     - **Nivel 2 (5,000 – 30,000 entidades):** Agrupamiento espacial dinámico en el cliente mediante el worker integrado de *Supercluster* (`cluster: true, clusterRadius: 50`).
     - **Nivel 3 (> 30,000 a 850,000+ entidades):** Vector Tiles dinámicos (*Mapbox Vector Tiles - MVT*) generados por el backend (`ST_AsMVT()`) y consultas por Bounding Box (`ST_MakeEnvelope`) al hacer zoom.

### 2.6 Gestión del Ciclo de Vida de WebGL, Detección de Hardware y Prevención de Carreras React 18 (R6)
* **Problema Identificado:** Los navegadores imponen un límite rígido de entre **8 y 16 contextos WebGL simultáneos** por origen. Si React desmonta y vuelve a montar un componente cartográfico (particularmente durante el doble montaje de `StrictMode` en React 18 o al alternar pestañas del dashboard) sin destruir explícitamente la instancia de MapLibre, los contextos GPU quedan huérfanos hasta agotar el límite (`Error: Too many active WebGL contexts`). Además, surgen tres patologías críticas:
  1. **Carrera Asíncrona en React 18 StrictMode:** El callback `map.on('load')` se dispara asíncronamente tras descargar el estilo; si el componente ya fue desmontado por StrictMode, actualizar el estado monta un mapa muerto (`Map has been removed`).
  2. **Pérdida Silenciosa de Contexto GPU:** Al suspender la pantalla o cambiar de GPU, el navegador destruye el canvas si no se captura `webglcontextlost` con `preventDefault()`.
  3. **Incompatibilidad de Hardware:** En entornos sin WebGL2, `new maplibregl.Map()` arroja una excepción síncrona fatal en lugar de un mensaje diagnóstico amigable.
  4. **Retención y Serialización en Zustand:** Guardar la instancia mutable `Map` dentro de la tienda global Zustand produce `TypeError: Converting circular structure to JSON` en React/Zustand DevTools.
* **Decisión y Solución Arquitectónica:**
  1. **Hook Canónico `useMapLibre`:** Controla la inicialización segura, guarda de montaje `isMounted`, y desuscripción determinista en la función de limpieza de `useEffect`:
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
       initialCenter = [-87.6298, 41.8781], // Centro de Chicago
       initialZoom = 11,
     }: UseMapLibreOptions) {
       const mapRef = useRef<MapLibreMap | null>(null);
       const [webGlSupported, setWebGlSupported] = useState<boolean>(true);
       const [isMapReady, setIsMapReady] = useState<boolean>(false);

       // Zustand almacena estrictamente estado serializable (viewport, filtros, capas activas)
       const setViewport = useMapStore((s) => s.setViewport);

       useEffect(() => {
         // 1. Verificación de Compatibilidad de Hardware WebGL2
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
           maxBounds: [
             [-88.1000, 41.6000], // Suroeste metropolitano
             [-87.4000, 42.1000], // Noreste metropolitano
           ],
           trackResize: true,
           fadeDuration: 100,
         });

         // 3. Manejo de Ciclo de Vida WebGL2 del Canvas
         const canvas = map.getCanvas();
         const handleContextLost = (e: Event) => {
           e.preventDefault(); // Evita destrucción irreversible del contexto
           console.warn('[MapLibre] Contexto WebGL2 perdido por el SO/GPU. Pausando renderizado.');
         };

         const handleContextRestored = () => {
           console.info('[MapLibre] Contexto WebGL2 restaurado. Re-renderizando capas...');
           map.triggerRepaint();
         };

         canvas.addEventListener('webglcontextlost', handleContextLost, false);
         canvas.addEventListener('webglcontextrestored', handleContextRestored, false);

         // 4. Guardia de Carrera Asíncrona en 'load' para React 18 StrictMode
         const handleLoad = () => {
           if (!isMounted) {
             console.warn('[MapLibre] Evento load disparado tras desmontaje. Omitiendo actualización.');
             return;
           }
           mapRef.current = map;
           setIsMapReady(true);
           setViewport({ center: initialCenter, zoom: initialZoom });
         };

         map.on('load', handleLoad);

         // Sincronización de Viewport serializable hacia Zustand
         map.on('moveend', () => {
           if (!isMounted) return;
           const center = map.getCenter();
           setViewport({
             center: [center.lng, center.lat],
             zoom: map.getZoom(),
           });
         });

         // 5. Limpieza Determinista y Destrucción del Contexto
         return () => {
           isMounted = false;
           map.off('load', handleLoad);
           canvas.removeEventListener('webglcontextlost', handleContextLost);
           canvas.removeEventListener('webglcontextrestored', handleContextRestored);
           map.remove(); // Destrucción física del contexto gráfico WebGL2
           mapRef.current = null;
           setIsMapReady(false);
         };
       }, [containerId]);

       return { mapRef, isMapReady, webGlSupported };
     }
     ```
  2. **Desacoplamiento Estricto de Estado en Zustand:** La tienda `useMapStore` almacena únicamente atributos serializables (`center`, `zoom`, `activeLayers`, `selectedCrashId`). La instancia física mutable `Map` nunca se inyecta en Zustand, sino que se expone a los componentes secundarios mediante el hook `useMapLibre` o mediante un React Context especializado (`MapContext.tsx`), erradicando colisiones con DevTools y fugas de memoria por referencias circulares.

### 2.7 Indexación GiST, Índices Funcionales Métricos y Agrupamiento Físico en Disco (R7)
* **Problema Identificado:** En bases de datos relacionales estándar, los registros se escriben en bloques físicos secuencialmente según su tiempo de inserción. Una consulta por Bounding Box sobre el distrito financiero de Chicago (*The Loop*) debe saltar por bloques de disco fragmentados a lo largo de gigabytes de almacenamiento, generando miles de fallos de caché de lectura (*page cache misses*). Adicionalmente, cuando se ejecutan cruces espaciales en metros con `ST_Transform(c.geom, 3435)`, el índice espacial estándar sobre `geom` (`EPSG:4326`) queda anulado por la envoltura funcional en el predicado, forzando un Sequential Scan de más de 850,000 filas por cada permiso de obra.
* **Decisión y Solución Arquitectónica:**
  1. Creación de índices espaciales **GiST (Generalized Search Tree)** bidimensionales nativos y funcionales proyectados a Illinois East (`EPSG:3435`):
     ```sql
     -- Índice espacial principal en WGS84 para visualización y consultas BBOX web:
     CREATE INDEX idx_crashes_geom ON silver_crashes USING GIST (geom);

     -- Índices espaciales funcionales GiST para cálculos topológicos métricos (Buffer 250m Anti-SeqScan):
     CREATE INDEX IF NOT EXISTS idx_crashes_geom_3435 
         ON silver_crashes USING GIST (ST_Transform(geom, 3435));

     CREATE INDEX IF NOT EXISTS idx_permits_geom_3435 
         ON silver_road_permits USING GIST (ST_Transform(geom, 3435));
     ```
  2. Ejecución del comando de reordenamiento físico **`CLUSTER`** tras la carga del pipeline ETL:
     ```sql
     CLUSTER silver_crashes USING idx_crashes_geom;
     ```
     Este comando reordena las filas físicas en disco siguiendo una curva de llenado espacial (Z-order / Curva de Hilbert), garantizando que los puntos geográficamente adyacentes residan en las mismas páginas de disco, logrando una **reducción de entre el 60% y el 80% en los tiempos de E/S de lectura**, mientras que los índices funcionales reducen los cruces espaciales de horas a menos de 45 segundos.

### 2.8 Aislamiento y Compatibilidad de NumPy y el Ecosistema Numérico (R8)
* **Problema Identificado:** El lanzamiento de NumPy 2.0 introduce alteraciones incompatibles en la interfaz binaria de aplicaciones en C (*C-API / ABI*). Si el entorno instala NumPy 2.0+, paquetes compilados contra NumPy 1.x (como versiones específicas de `scikit-learn`, `shapely` y `pandas`) experimentan fallos catastróficos de segmentación de memoria (*Segmentation Fault*) al intentar deserializar o ejecutar modelos de predicción.
* **Decisión y Solución Arquitectónica:**
  Fijación estricta de la cota de NumPy en el manifiesto de Python: `numpy>=1.26.4,<2.0.0`. Esta directriz bloquea la transición descontrolada a NumPy 2.0 y preserva la estabilidad binaria en toda la cadena de dependencias.

---

## 3. MATRIZ Y RÚBRICA DE VALIDACIÓN DE DEPENDENCIAS

A continuación se presentan las dependencias cerradas y congeladas para los entornos de Backend (Python) y Frontend (Node.js), acompañadas de la rúbrica formal que los agentes revisores y auditores deben evaluar para certificar la ausencia de conflictos de versiones.

### 3.1 Manifiesto Pinned de Backend (`backend/requirements.txt`)

```ini
# ==============================================================================
# FASTAPI & ASGI WEB CORE
# ==============================================================================
fastapi==0.115.8
uvicorn[standard]==0.34.0
pydantic==2.10.6
pydantic-settings==2.7.1
starlette==0.45.3

# ==============================================================================
# DATABASE ORM, DRIVERS & SPATIAL EXTENSIONS
# ==============================================================================
SQLAlchemy==2.0.38
GeoAlchemy2==0.17.1
asyncpg==0.30.0
psycopg[binary]==3.2.5
alembic==1.14.1

# ==============================================================================
# GEOMETRÍA ESPACIAL & PROYECCIONES
# ==============================================================================
shapely==2.0.7
pyproj==3.7.1

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

# ==============================================================================
# UTILIDADES, SEGURIDAD & TESTING
# ==============================================================================
python-dotenv==1.0.1
email-validator==2.2.0
pytest==8.3.3
pytest-asyncio==0.24.0
```

### 3.2 Manifiesto Pinned de Frontend (`frontend/package.json`)

```json
{
  "name": "chicago-traffic-risk-frontend",
  "private": true,
  "version": "1.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "lint": "eslint . --ext ts,tsx --report-unused-disable-directives --max-warnings 0",
    "preview": "vite preview",
    "typecheck": "tsc --noEmit",
    "test": "vitest run"
  },
  "dependencies": {
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "maplibre-gl": "4.7.1",
    "zustand": "5.0.0",
    "@tanstack/react-query": "5.56.2",
    "@tanstack/react-table": "8.20.5",
    "@tanstack/react-virtual": "3.10.8",
    "clsx": "2.1.1",
    "tailwind-merge": "2.5.2",
    "lucide-react": "0.446.0",
    "@radix-ui/react-slider": "1.2.0",
    "@radix-ui/react-tabs": "1.1.0",
    "@radix-ui/react-dialog": "1.1.1",
    "@radix-ui/react-popover": "1.1.1",
    "@radix-ui/react-tooltip": "1.1.2",
    "@radix-ui/react-dropdown-menu": "2.1.1",
    "@radix-ui/react-checkbox": "1.1.1",
    "recharts": "2.12.7",
    "axios": "1.7.7",
    "date-fns": "3.6.0"
  },
  "devDependencies": {
    "@types/react": "18.3.10",
    "@types/react-dom": "18.3.0",
    "@types/geojson": "7946.0.14",
    "@types/node": "22.5.5",
    "@vitejs/plugin-react": "4.3.1",
    "typescript": "5.6.2",
    "vite": "5.4.6",
    "vite-plugin-compression": "0.5.1",
    "tailwindcss": "3.4.11",
    "postcss": "8.4.47",
    "autoprefixer": "10.4.20",
    "eslint": "8.57.1",
    "eslint-plugin-react-hooks": "4.6.2",
    "eslint-plugin-react-refresh": "0.4.12",
    "vitest": "2.1.1",
    "@testing-library/react": "16.0.1",
    "@testing-library/jest-dom": "6.5.0",
    "jsdom": "25.0.1"
  }
}
```

### 3.3 Rúbrica Formal de Validación de Dependencias y Conflictos de Versiones

Esta rúbrica establece los seis criterios objetivos y cuantitativos que el agente auditor y el equipo de aseguramiento de calidad evaluarán para emitir el dictamen de pase:

```
+-----------------------------------------------------------------------------------------------------------------------------------------+
|                                    RÚBRICA DE VALIDACIÓN DE DEPENDENCIAS Y CONFLICTOS DE VERSIONES                                      |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| No | Criterio de Evaluación             | Condición de Aprobación (PASS)        | Condición de Falla (FAIL)             | Verificación  |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 1  | Compatibilidad de ABI Numérico     | numpy < 2.0.0 estricto. Cero fallos   | numpy >= 2.0.0 instalado. Incompati-  | pip check &   |
|    | en Ecosistema Científico           | de import en shapely y scikit-learn.  | bilidad binaria C-ABI con segfaults.  | pytest        |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 2  | Coexistencia Dual-Engine           | asyncpg 0.30 y psycopg 3.2 coexisten  | Conflicto de drivers o uso de un solo | Conexión sync |
|    | de Conexión a Base de Datos        | sin colisiones; SQLAlchemy 2.0 activo.| driver no preparado para PostGIS.     | y async OK    |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 3  | Blindaje de Migraciones Espaciales | GeoAlchemy2 0.17.1 con hooks en       | Alembic intenta eliminar tablas       | alembic check |
|    | en Alembic                         | alembic/env.py; cero drops de sistema.| espaciales o duplica índices GiST.    | & upgrade     |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 4  | Estabilidad de Paquetes React      | React 18.3.1 congelado; cero alertas  | React 19 forzado; fallo ERESOLVE en   | npm ls &      |
|    | y Cero Colisiones ERESOLVE         | de peer dependency en Radix/Recharts. | dependencias o uso de --force.        | npm audit     |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 5  | Motor Gráfico WebGL2               | MapLibre GL JS v4.7.1 nativo; no hay  | Uso de Leaflet obsoleto o wrappers    | Verificación  |
|    | Desacoplado de Render React        | wrappers frágiles; hook useMapLibre.  | que causan fugas de contexto GPU.     | de código     |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
| 6  | Reproducibilidad de Despliegue     | Uso estricto de Docker multi-stage    | Imágenes Alpine para Python con fallos| docker build  |
|    | y Aislamiento de Binarios          | Debian Slim y npm ci con lockfile.    | de gcc/musl; npm install flotante.    | exit code 0   |
+----+------------------------------------+---------------------------------------+---------------------------------------+---------------+
```

---

## 4. ARQUITECTURA DEL SISTEMA Y CONTENEDORIZACIÓN CON DOCKER

### 4.1 Especificación de Construcción y Orquestación de Contenedores

El sistema se orquesta íntegramente mediante **Docker y Docker Compose**. El orden de inicialización, dependencias de salud y asignación de recursos siguen una secuencia determinista:

```
                                 SECUENCIA DE ORQUESTACIÓN Y SALUD (STARTUP GATES)
                                 
      +---------------------------------------------------------------------------------------+
      | 1. CONTENEDOR POSTGIS 16-3.4 (chicago_postgis)                                        |
      |    - Inicializa cluster PostgreSQL y catálogo PostGIS.                                |
      |    - Ejecuta healthcheck continuo: pg_isready -U chicago_admin -d chicago_safety.      |
      +-------------------------------------------+-------------------------------------------+
                                                  | Condición: service_healthy (espera ~10s)
                                                  v
      +---------------------------------------------------------------------------------------+
      | 2. CONTENEDOR BACKEND FASTAPI (chicago_fastapi)                                       |
      |    - Multi-stage build Debian Slim (python:3.11-slim-bookworm).                        |
      |    - entrypoint.sh ejecuta migraciones previas automáticas: alembic upgrade head.      |
      |    - Lifespan inicializa asyncpg pool y carga modelo ML con fallback heurístico.       |
      |    - Expone puerto 8000; Healthcheck: curl -f http://localhost:8000/api/v1/health.     |
      +-------------------------------------------+-------------------------------------------+
                                                  | Condición: service_healthy (espera ~5s)
                                                  v
      +---------------------------------------------------------------------------------------+
      | 3. CONTENEDOR FRONTEND NGINX (chicago_frontend)                                       |
      |    - Multi-stage build (node:20-alpine -> nginx:1.27-alpine).                          |
      |    - Sirve assets estáticos SPA (HTML5, JS, CSS) precomprimidos con Gzip/Brotli.      |
      |    - Actúa como Reverse Proxy enrutando /api/ internamente a http://backend:8000.     |
      |    - Expone puerto 80 al host; Healthcheck: wget http://127.0.0.1/health.             |
      +---------------------------------------------------------------------------------------+
```

### 4.2 Dockerfile del Backend (`backend/Dockerfile`)
Se utiliza deliberadamente **Debian Slim** (`python:3.11-slim-bookworm`) en lugar de Alpine Linux. Alpine utiliza `musl-libc`, lo que obliga a compilar desde código fuente las bibliotecas geoespaciales C/C++ (GDAL, GEOS, PROJ) durante más de 30 minutos con alto riesgo de fallo. Debian Slim soporta *wheels* binarios oficiales `manylinux`, reduciendo la construcción a segundos y produciendo una imagen ligera y estable de ~220 MB.

```dockerfile
# ==============================================================================
# ETAPA 1: Compilación de Dependencias (Builder)
# ==============================================================================
FROM python:3.11-slim-bookworm AS builder

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel && \
    pip install -r requirements.txt

# ==============================================================================
# ETAPA 2: Contenedor Seguro de Ejecución (Runner)
# ==============================================================================
FROM python:3.11-slim-bookworm AS runner

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH="/opt/venv/bin:$PATH" \
    PORT=8000

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

COPY --from=builder /opt/venv /opt/venv

# Creación de usuario del sistema sin privilegios y aprovisionamiento de volúmenes (Seguridad & DuckDB Permissions)
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

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/api/v1/health || exit 1

ENTRYPOINT ["/app/entrypoint.sh"]
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]
```

#### Script de Arranque y Migración Automática (`backend/entrypoint.sh`)
Para garantizar que el clúster relacional posea siempre el esquema DDL y extensiones PostGIS antes de que Uvicorn atienda peticiones, se define el script `backend/entrypoint.sh`:

```bash
#!/bin/sh
set -e

echo "[Chicago Backend] Verificando conexión a PostgreSQL y ejecutando migraciones..."
alembic upgrade head

echo "[Chicago Backend] Migraciones aplicadas con éxito. Iniciando servidor web..."
exec "$@"
```

#### Manejador de Ciclo de Vida Resiliente (`app/main.py`)
Para evitar bloqueos durante despliegues iniciales (Fases 1 a 3) donde el archivo binario del modelo `chicago_risk_xgboost.joblib` aún no ha sido entrenado, el manejador `lifespan` captura la ausencia del archivo, emite una advertencia informativa y configura un estimador heurístico de respaldo, permitiendo que la sonda de salud `/api/v1/health` responda HTTP 200:

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 1. Startup: Inicializar pool de conexiones asíncronas
    await init_db_pool()
    
    # 2. Carga tolerante a fallos del modelo predictivo (R-B3)
    model_path = settings.MODEL_PATH
    if os.path.exists(model_path):
        try:
            app.state.ml_model = joblib.load(model_path)
            app.state.model_loaded = True
        except Exception as exc:
            app.state.ml_model = None
            app.state.model_loaded = False
    else:
        # Modo heurístico de respaldo antes de entrenar en Fase 3
        app.state.ml_model = None
        app.state.model_loaded = False

    yield

    # 3. Shutdown: Cierre ordenado de conexiones
    await close_db_pool()
```

### 4.3 Dockerfile del Frontend (`frontend/Dockerfile`)
El frontend implementa una compilación multi-etapa que desacopla el entorno de compilación de Node.js del entorno de producción. La imagen final Nginx Alpine tiene un peso inferior a **35 MB**, cuenta con pre-compresión de recursos y cabeceras de seguridad estrictas.

```dockerfile
# ==============================================================================
# ETAPA 1: Construcción y Compilación de Assets (Node.js)
# ==============================================================================
FROM node:20-alpine AS builder

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci --no-audit --prefer-offline

COPY . .
RUN npm run build

# ==============================================================================
# ETAPA 2: Servidor Web de Producción (Nginx Alpine)
# ==============================================================================
FROM nginx:1.27-alpine AS production

RUN rm -rf /usr/share/nginx/html/*

COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
```

### 4.4 Configuración del Reverse Proxy Nginx (`frontend/nginx.conf`)
El servidor Nginx actúa como fachada pública única, sirviendo la aplicación SPA y resolviendo las llamadas al API a través de una directiva `proxy_pass` interna. Esto **elimina por completo los problemas de CORS** en producción, ya que el navegador siempre interactúa con el mismo origen HTTP.

```nginx
upstream backend_api {
    server backend:8000 max_fails=3 fail_timeout=10s;
    keepalive 32;
}

server {
    listen 80;
    server_name localhost;
    charset utf-8;

    client_max_body_size 15M;
    root /usr/share/nginx/html;
    index index.html;

    # Compresión Gzip para capas vectoriales y GeoJSON
    gzip on;
    gzip_vary on;
    gzip_proxied any;
    gzip_comp_level 6;
    gzip_types
        text/plain
        text/css
        text/javascript
        application/json
        application/geo+json
        application/x-protobuf
        application/vnd.mapbox-vector-tile
        application/javascript
        image/svg+xml;

    # Cabeceras de Seguridad y Content Security Policy para MapLibre Workers
    add_header X-Frame-Options "SAMEORIGIN" always;
    add_header X-Content-Type-Options "nosniff" always;
    add_header Referrer-Policy "strict-origin-when-cross-origin" always;
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' blob:; worker-src 'self' blob:; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src 'self' https://fonts.gstatic.com data:; img-src 'self' data: blob: https://*.cartocdn.com https://*.openstreetmap.org; connect-src 'self' http://localhost:8000 http://backend:8000 https://*.cartocdn.com https://*.openstreetmap.org https://demotiles.maplibre.org blob:;" always;

    # Caching de Assets Estáticos Inmutables
    location /assets/ {
        expires 1y;
        add_header Cache-Control "public, max-age=31536000, immutable";
        access_log off;
        try_files $uri =404;
    }

    # Sonda de Salud del Contenedor
    location /health {
        access_log off;
        return 200 '{"status":"UP","service":"frontend-web"}';
        add_header Content-Type application/json;
    }

    # Enrutamiento Proxy hacia FastAPI Backend (Eliminación de CORS)
    location /api/ {
        proxy_pass http://backend_api;
        proxy_http_version 1.1;
        proxy_set_header Connection "";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_connect_timeout 15s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;

        proxy_buffering on;
        proxy_buffer_size 128k;
        proxy_buffers 4 256k;
    }

    # Fallback de Enrutamiento HTML5 para Single Page Application
    location / {
        try_files $uri $uri/ /index.html;
        add_header Cache-Control "no-cache, no-store, must-revalidate";
    }
}
```

### 4.5 Orquestación Unificada (`docker-compose.yml`)

```yaml
version: "3.8"

networks:
  chicago_network:
    name: chicago_network
    driver: bridge

volumes:
  postgis_data:
    name: chicago_postgis_data
    driver: local
  duckdb_data:
    name: chicago_duckdb_data
    driver: local

services:
  db:
    image: postgis/postgis:16-3.4
    container_name: chicago_postgis
    restart: unless-stopped
    environment:
      POSTGRES_DB: ${POSTGRES_DB:-chicago_safety}
      POSTGRES_USER: ${POSTGRES_USER:-chicago_admin}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:-ChicagoSecure2026!}
      PGDATA: /var/lib/postgresql/data/pgdata
    volumes:
      - postgis_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    command: >
      postgres
      -c shared_buffers=1GB
      -c work_mem=64MB
      -c maintenance_work_mem=256MB
      -c random_page_cost=1.1
      -c effective_cache_size=3GB
      -c max_connections=200
    shm_size: 1g
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U $${POSTGRES_USER} -d $${POSTGRES_DB}"]
      interval: 5s
      timeout: 5s
      retries: 5
      start_period: 10s
    networks:
      - chicago_network
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 4096M
        reservations:
          memory: 1024M

  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: chicago_fastapi
    restart: unless-stopped
    depends_on:
      db:
        condition: service_healthy
    environment:
      ENVIRONMENT: production
      DATABASE_URL: postgresql+asyncpg://${POSTGRES_USER:-chicago_admin}:${POSTGRES_PASSWORD:-ChicagoSecure2026!}@db:5432/${POSTGRES_DB:-chicago_safety}
      SYNC_DATABASE_URL: postgresql+psycopg://${POSTGRES_USER:-chicago_admin}:${POSTGRES_PASSWORD:-ChicagoSecure2026!}@db:5432/${POSTGRES_DB:-chicago_safety}
      CORS_ORIGINS: "http://localhost,http://localhost:80,http://localhost:3000,http://localhost:5173"
      MODEL_PATH: /app/app/ml/models/chicago_risk_xgboost.joblib
      DUCKDB_PATH: /data/duckdb/chicago_olap.duckdb
    volumes:
      - duckdb_data:/data/duckdb
    ports:
      - "8000:8000"
    healthcheck:
      test: ["CMD-SHELL", "curl -f http://localhost:8000/api/v1/health || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 3
      start_period: 15s
    networks:
      - chicago_network
    deploy:
      resources:
        limits:
          cpus: "2.0"
          memory: 2048M
        reservations:
          memory: 512M

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
    container_name: chicago_frontend
    restart: unless-stopped
    depends_on:
      backend:
        condition: service_healthy
    ports:
      - "80:80"
    healthcheck:
      test: ["CMD-SHELL", "wget --quiet --tries=1 --spider http://127.0.0.1/health || exit 1"]
      interval: 15s
      timeout: 5s
      retries: 3
      start_period: 5s
    networks:
      - chicago_network
    deploy:
      resources:
        limits:
          cpus: "1.0"
          memory: 512M
        reservations:
          memory: 128M
```

### 4.6 Especificación de Variables de Entorno (`.env.example`)

```ini
# Configuración del Entorno de Ejecución
ENVIRONMENT=production
DEBUG=False

# Credenciales de Base de Datos PostgreSQL / PostGIS
POSTGRES_DB=chicago_safety
POSTGRES_USER=chicago_admin
POSTGRES_PASSWORD=ChicagoSecure2026!
# NOTA: Usar POSTGRES_HOST=db en contenedores Docker. Para CLI y migraciones en host local usar POSTGRES_HOST=localhost
POSTGRES_HOST=db
POSTGRES_PORT=5432

# URLs de Conexión Dual-Engine (Para Docker: db:5432; Para terminal local del host: localhost:5432)
DATABASE_URL=postgresql+asyncpg://chicago_admin:ChicagoSecure2026!@db:5432/chicago_safety
SYNC_DATABASE_URL=postgresql+psycopg://chicago_admin:ChicagoSecure2026!@db:5432/chicago_safety
# Alternativa CLI local: SYNC_DATABASE_URL=postgresql+psycopg://chicago_admin:ChicagoSecure2026!@localhost:5432/chicago_safety

# Chicago Open Data SODA API Credentials (Opcional para cuotas elevadas)
SOCRATA_APP_TOKEN=
SOCRATA_SECRET_TOKEN=

# Rutas de Almacenamiento de Modelos y Datos OLAP
MODEL_PATH=/app/app/ml/models/chicago_risk_xgboost.joblib
DUCKDB_PATH=/data/duckdb/chicago_olap.duckdb

# Políticas de Seguridad Web
CORS_ORIGINS=http://localhost,http://localhost:80,http://localhost:3000,http://localhost:5173
```

---

## 5. ESTRUCTURA DE DIRECTORIOS DEL REPOSITORIO

La siguiente estructura modular organiza el código fuente, la configuración de infraestructura, los pipelines de datos y las pruebas automatizadas respetando los principios de alta cohesión y bajo acoplamiento:

```
proyecto-espe/
├── .env.example                               # Plantilla canónica de variables de entorno
├── .gitignore                                 # Exclusiones de Git (node_modules, venv, datos crudos, .env)
├── docker-compose.yml                         # Orquestador multi-contenedor del sistema completo
├── plan_de_implementacion_fases.md            # Plan maestro de implementación (este documento)
├── README.md                                  # Guía general de arquitectura y puesta en marcha rápida
│
├── backend/                                   # Servicio Backend API, Modelado ML y ETL
│   ├── Dockerfile                             # Multi-stage Dockerfile basado en python:3.11-slim
│   ├── entrypoint.sh                          # Script de arranque: migraciones automáticas y uvicorn
│   ├── requirements.txt                       # Dependencias fijadas de Python
│   ├── alembic.ini                            # Configuración principal de Alembic
│   ├── alembic/                               # Migraciones de base de datos
│   │   ├── env.py                             # Configuración con geoalchemy2.alembic_helpers
│   │   ├── script.py.mako                     # Plantilla de generación de revisiones
│   │   └── versions/                          # Scripts de migración versionados
│   │       ├── 0001_initial_postgis_setup.py  # Habilitación de extensión PostGIS
│   │       └── 0002_create_spatial_tables.py  # Tablas bronze, silver y vistas gold
│   ├── app/                                   # Código de la aplicación FastAPI
│   │   ├── main.py                            # Punto de entrada FastAPI, lifespan y middlewares
│   │   ├── core/                              # Configuración central del sistema
│   │   │   ├── config.py                      # Carga de variables con Pydantic Settings
│   │   │   └── database.py                    # Motores SQLAlchemy (asyncpg & psycopg3) y sesiones
│   │   ├── models/                            # Modelos declarativos ORM (SQLAlchemy + GeoAlchemy2)
│   │   │   ├── base.py                        # Base declarativa compartida
│   │   │   ├── crash.py                       # Modelo silver_crashes con columna Geometry(Point, 4326)
│   │   │   ├── vehicle.py                     # Modelo silver_vehicles
│   │   │   ├── person.py                      # Modelo silver_people (datos anonimizados)
│   │   │   ├── traffic.py                     # Modelo silver_traffic_counts (AADT)
│   │   │   └── permit.py                      # Modelo silver_road_permits (obras CDOT)
│   │   ├── schemas/                           # Esquemas Pydantic v2 (Validación y DTOs)
│   │   │   ├── spatial.py                     # Schemas de BBOX, GeoJSON y geometrías
│   │   │   ├── crash.py                       # Schemas de respuesta y filtrado de siniestros
│   │   │   └── prediction.py                  # Schemas de entrada y salida para inferencia ML
│   │   ├── api/                               # Controladores y rutas REST
│   │   │   └── v1/
│   │   │       ├── api.py                     # Router maestro v1
│   │   │       ├── endpoints/
│   │   │       │   ├── health.py              # Endpoint de salud y diagnóstico
│   │   │       │   ├── crashes.py             # Endpoints GeoJSON y streaming de siniestros
│   │   │       │   ├── analytics.py           # Agregaciones estadísticas y KPIs
│   │   │       │   └── predict.py             # Endpoint de inferencia de riesgo vial en vivo
│   │   ├── services/                          # Lógica de negocio y procesamiento de datos
│   │   │   ├── etl/                           # Pipelines de ingesta y curación
│   │   │   │   ├── soda_client.py             # Cliente Socrata paginado con reintentos
│   │   │   │   ├── data_cleaner.py            # Saneamiento de nulos y normalización
│   │   │   │   └── spatial_enrichment.py      # Buffer topológico de 250m en EPSG:3435
│   │   │   └── olap/
│   │   │       └── duckdb_engine.py           # Consultas analíticas vectorizadas sobre Parquet
│   │   └── ml/                                # Ciclo de vida de Machine Learning
│   │       ├── train.py                       # Script de entrenamiento, balanceo y evaluación 5-fold
│   │       ├── feature_engineering.py         # Extracción de variables espaciotemporales
│   │       ├── predictor.py                   # Wrapper de inferencia para el modelo cargado
│   │       └── models/                        # Artefactos binarios serializados
│   │           └── chicago_risk_xgboost.joblib # Modelo ganador serializado
│   └── tests/                                 # Batería de pruebas automatizadas
│       ├── conftest.py                        # Fixtures de base de datos de pruebas y cliente async
│       ├── test_api_health.py                 # Pruebas de sonda de salud
│       ├── test_spatial_queries.py            # Pruebas de consultas BBOX e índices GiST
│       └── test_ml_inference.py               # Pruebas de contrato del endpoint /predict
│
├── frontend/                                  # Aplicación Web React 18 + MapLibre GL JS SPA
│   ├── Dockerfile                             # Multi-stage Dockerfile (Node 20 -> Nginx Alpine)
│   ├── nginx.conf                             # Configuración del servidor Nginx y proxy reverso
│   ├── package.json                           # Dependencias congeladas de Node.js
│   ├── package-lock.json                      # Árbol de resolución determinista de dependencias
│   ├── tsconfig.json                          # Configuración de TypeScript
│   ├── vite.config.ts                         # Configuración de Vite y división de bundles
│   ├── tailwind.config.js                     # Configuración de estilos con Tailwind CSS
│   ├── postcss.config.js                      # Plugins de PostCSS
│   ├── index.html                             # Plantilla HTML principal
│   └── src/                                   # Código fuente TypeScript / React
│       ├── main.tsx                           # Punto de entrada de la aplicación
│       ├── App.tsx                            # Contenedor raíz y proveedores de estado
│       ├── context/                           # Contextos de React para instancias mutables
│       │   └── MapContext.tsx                 # Proveedor seguro de instancia MapLibre (evita circular en Zustand)
│       ├── components/                        # Componentes de interfaz de usuario
│       │   ├── layout/                        # Componentes estructurales
│       │   │   ├── Header.tsx                 # Barra superior con título y controles globales
│       │   │   ├── Sidebar.tsx                # Barra lateral colapsable de filtros y capas
│       │   │   ├── AnalyticsPanel.tsx         # Panel deslizable con KPIs y gráficos
│       │   │   └── DataDrawer.tsx             # Cajón inferior con tabla virtualizada
│       │   ├── map/                           # Componentes cartográficos MapLibre WebGL2
│       │   │   ├── MapContainer.tsx           # Contenedor del canvas WebGL y control de ciclo de vida
│       │   │   ├── MapControls.tsx            # Botones de navegación, pitch y reseteo a Chicago
│       │   │   ├── MapLegend.tsx              # Leyenda dinámica de rampas de color de riesgo
│       │   │   ├── MapPopup.tsx               # Tarjeta emergente con detalle del siniestro
│       │   │   └── layers/                    # Definición de capas y shaders de MapLibre
│       │   │       ├── CrashHeatmapLayer.ts   # Capa de densidad de calor (Heatmap)
│       │   │       ├── CrashClusterLayer.ts   # Capa de agrupamiento dinámico (Supercluster)
│       │   │       ├── RiskChoroplethLayer.ts # Capa de segmentos viales coloreados por riesgo ML
│       │   │       ├── RoadClosureLayer.ts    # Polígonos de obras CDOT y zonas de amortiguamiento
│       │   │       └── TrafficAADTLayer.ts    # Círculos proporcionales de aforo vehicular
│       │   ├── analytics/                     # Gráficos Recharts (con minWidth={0} y montado condicional)
│       │   │   ├── KpiSummaryCards.tsx        # Métricas de siniestros, víctimas y tramos críticos
│       │   │   ├── HourlyDistribution.tsx     # Histograma de colisiones por hora del día
│       │   │   ├── WeatherImpactChart.tsx     # Donut chart de condiciones climáticas y de calzada
│       │   │   └── RiskCorrelationPlot.tsx    # Dispersión entre flujo vehicular y severidad
│       │   └── table/                         # Componentes tabulares de alto rendimiento
│       │       ├── VirtualCrashTable.tsx      # Tabla virtualizada para miles de filas (TanStack Virtual)
│       │       └── TableExportBar.tsx         # Botones de exportación a CSV y GeoJSON
│       ├── hooks/                             # Hooks personalizados
│       │   ├── useMapLibre.ts                 # Hook de ciclo de vida seguro de MapLibre (WebGL2, isMounted)
│       │   ├── useSpatialFilters.ts           # Sincronización de filtros con map.setFilter()
│       │   └── useDebounce.ts                 # Debounce para peticiones analíticas al backend
│       ├── stores/                            # Gestión de estado global con Zustand (solo estado serializable)
│       │   ├── useMapStore.ts                 # Estado del viewport, centro, zoom y capas visibles
│       │   ├── useFilterStore.ts              # Estado de filtros (fechas, horas, severidad)
│       │   └── useUiStore.ts                  # Estado de visibilidad de paneles y cajones
│       ├── services/                          # Clientes de comunicación HTTP
│       │   ├── api.ts                         # Instancia configurada de Axios
│       │   ├── crashService.ts                # Métodos de consulta de siniestros y estadísticas
│       │   └── predictionService.ts           # Invocación al endpoint de predicción de riesgo
│       └── types/                             # Definiciones de tipos TypeScript
│           ├── geojson.d.ts                   # Interfaces para entidades y propiedades espaciales
│           └── api.d.ts                       # Tipos de respuesta del API REST
│
└── data/                                      # Directorio de persistencia y archivos de datos
    ├── raw/                                   # Archivos crudos de descarga inicial (Bronze)
    ├── processed/                             # Archivos saneados en formato Parquet (Silver)
    └── duckdb/                                # Base de datos embebida analítica (Gold)
```

---

## 6. PLAN DE IMPLEMENTACIÓN POR FASES Y SPRINTS CRONOLÓGICOS

El plan desglosa las **13 semanas académicas** en **6 Fases Secuenciales**, cada una estructurada con objetivos concretos, prerrequisitos, desglose paso a paso de tareas con asignación de responsables, comandos de terminal reproducibles, estructura de archivos generada y compuertas de calidad (*Quality Gates*) indispensables para avanzar.

```
+----------------------------------------------------------------------------------------------------+
|                                CRONOGRAMA MAESTRO DE EJECUCIÓN (13 SEMANAS)                        |
+---------+-------------------------------------------------------------+-----------+----------------+
| Fase    | Denominación del Sprint / Hito                              | Duración  | Responsable    |
+---------+-------------------------------------------------------------+-----------+----------------+
| FASE 1  | Infraestructura Base, PostGIS y Modelado Relacional         | Sem. 1-3  | Deivid Cardenas|
| FASE 2  | Pipeline ETL, Ingesta SODA y Enriquecimiento Topológico     | Sem. 3-6  | Deivid Cardenas|
| FASE 3  | Feature Engineering, Modelado Predictivo y Serialización    | Sem. 6-9  | Alex. Cardenas |
| FASE 4  | Backend API Asíncrona, Endpoints Geoespaciales y Predicción | Sem. 9-11 | Deivid Cardenas|
| FASE 5  | Frontend React WebGL, Dashboard Analítico y Virtualización  | Sem. 10-12| Camilo Escandón|
| FASE 6  | Orquestación Docker, Optimización, Testing E2E y Despliegue | Sem. 12-13| Todo el Equipo |
+---------+-------------------------------------------------------------+-----------+----------------+
```

---

### FASE 1: INFRAESTRUCTURA BASE, CONTENERIZACIÓN POSTGIS Y MODELADO RELACIONAL
* **Duración:** Semanas 1 a 3 (~55 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Cumplimiento directo del **Objetivo Específico OE1**.
* **Responsable Principal:** Deivid Julian Cardenas Melo (Ingeniero de Datos / Líder del Proyecto).
* **Prerrequisitos:** Docker Desktop / Docker Engine instalado y operativo con soporte de virtualización habilitado; Python 3.11 instalado localmente para utilidades de administración.

#### Tareas Técnicas Detalladas:
1. **Configuración del Espacio de Trabajo y Control de Versiones:**
   - Crear la estructura modular de directorios para backend, frontend y almacenamiento de datos.
   - Definir el archivo `.gitignore` estandarizado para aislar secretos, entornos virtuales y artefactos de compilación.
   - Crear el archivo `.env.example` con la especificación completa de credenciales y variables.
2. **Despliegue del Contenedor PostgreSQL 16 + PostGIS 3.4:**
   - Redactar el bloque del servicio `db` en `docker-compose.yml` utilizando la imagen oficial `postgis/postgis:16-3.4`.
   - Asignar memoria compartida (`shm_size: 1g`) y volumen persistente `postgis_data`.
   - Aplicar las directivas de inicialización de rendimiento en el comando de arranque (`shared_buffers=1GB`, `work_mem=64MB`, `maintenance_work_mem=256MB`, `random_page_cost=1.1`, `max_connections=200`).
   - Configurar la sonda de salud `healthcheck` mediante `pg_isready`.
3. **Modelado Relacional y Definición de Tablas en SQLAlchemy 2.0:**
   - Diseñar el esquema relacional de la Capa Silver reflejando la estructura canónica de los datasets de Chicago:
     - `silver_crashes`: Clave primaria `crash_record_id`, fecha de siniestro `crash_date`, condiciones ambientales y de calzada, víctimas totales/fatales y columna espacial `geom` de tipo `Geometry(Point, 4326)`.
     - `silver_vehicles`: Clave primaria `vehicle_id`, clave foránea `crash_record_id` con borrado en cascada, tipo de vehículo, maniobra y año.
     - `silver_people`: Clave primaria `person_id`, clave foránea `crash_record_id`, variables demográficas agregadas (`age`, `sex`), clasificación de lesión médica general y equipo de seguridad; estricta anonimización sin campos PII.
     - `silver_traffic_counts`: Identificador de estación, fecha de aforo, volumen diario `total_passing_vehicle_volume` y columna espacial `geom` (Point, 4326).
     - `silver_road_permits`: Identificador de permiso CDOT, fechas de vigencia `start_date` y `end_date`, tipo de trabajo y columna geométrica `geom` (Point/Polygon, 4326).
4. **Configuración de Alembic con Hooks de GeoAlchemy2:**
   - Inicializar el entorno de Alembic dentro de `backend/`.
   - Modificar `backend/alembic/env.py` para enlazar el motor síncrono `psycopg3` e inyectar `geoalchemy2.alembic_helpers` para salvaguardar las tablas de catálogo y prevenir la duplicación de índices GiST.
   - Generar la migración manual `0001_initial_postgis_setup.py` que asegura la ejecución de `CREATE EXTENSION IF NOT EXISTS postgis;`.
   - Ejecutar la migración automática `0002_create_spatial_tables.py` que materializa el esquema en PostgreSQL.
5. **Indexación Espacial GiST y Verificación:**
   - Confirmar la creación automática y correcta de los índices espaciales `USING GIST (geom)` en WGS84 (`EPSG:4326`).
   - Crear índices espaciales funcionales GiST proyectados a Illinois East `USING GIST (ST_Transform(geom, 3435))` para acelerar los cálculos de proximidad y cruces métricos de la Fase 2.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Crear estructura base de carpetas
mkdir -p backend/app/{api/v1/endpoints,core,models,schemas,services/etl,services/olap,ml/models}
mkdir -p backend/alembic/versions backend/tests
mkdir -p data/{raw,processed,duckdb}

# 2. Iniciar únicamente el servicio de base de datos PostGIS
docker compose up -d db

# 3. Validar estado y versión activa de PostGIS
docker compose exec db psql -U chicago_admin -d chicago_safety -c "SELECT PostGIS_Full_Version();"

# 4. Crear entorno virtual local para herramientas de migración
cd backend
python -m venv .venv
# En Windows PowerShell:
.venv\Scripts\Activate.ps1
# En Linux/macOS: source .venv/bin/activate

# 5. Instalar dependencias fijadas de backend
pip install --upgrade pip
pip install -r requirements.txt

# 6. Ejecutar migraciones iniciales con Alembic desde el host
# NOTA: En el host, PostgreSQL se expone en localhost:5432 (no 'db')
$env:POSTGRES_HOST="localhost"  # En PowerShell (export POSTGRES_HOST=localhost en Linux/macOS)
alembic upgrade head

# 7. Verificar existencia de tablas y claves en la base de datos
docker compose exec db psql -U chicago_admin -d chicago_safety -c "\dt"
```

#### Criterios de Aceptación y Quality Gate:
* [x] El contenedor `chicago_postgis` alcanza el estado `healthy` en menos de 30 segundos.
* [x] `PostGIS_Full_Version()` reporta versión 3.4 sobre PostgreSQL 16.
* [x] `alembic upgrade head` se ejecuta con código de salida 0 sin arrojar excepciones de catálogo ni duplicación de índices GiST.
* [x] La restricción de clave foránea entre `silver_vehicles` / `silver_people` y `silver_crashes` rechaza inserciones huérfanas.

---

### FASE 2: PIPELINE ETL, INGESTA SODA Y ENRIQUECIMIENTO TOPOLÓGICO
* **Duración:** Semanas 3 a 6 (~80 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Cumplimiento directo del **Objetivo Específico OE2**.
* **Responsable Principal:** Deivid Julian Cardenas Melo (Ingeniero de Datos). Colabora: Dillan Alexander Cardenas Melo.
* **Prerrequisitos:** Fase 1 completada y validada; tablas de base de datos creadas con índices GiST activos; acceso a internet para conexión con la API pública SODA de Chicago.

#### Tareas Técnicas Detalladas:
1. **Cliente de Ingesta SODA Paginado e Incremental (`soda_client.py`):**
   - Implementar la clase de conexión a la API de Socrata mediante `sodapy` y `httpx`.
   - Configurar paginación por lotes de 20,000 registros utilizando parámetros `limit` y `offset`.
   - Incorporar política de reintentos con descarte de fallo (*exponential backoff*) ante respuestas HTTP 429 (Rate Limit) o 500.
   - Implementar ingesta incremental mediante marca de agua temporal (`$where=crash_date > 'última_fecha_registrada'`).
   - Almacenar los registros crudos descargados en la Capa Bronze en formato columnar **Apache Parquet** comprimido con Snappy en `data/raw/`.
2. **Módulo de Calidad, Saneamiento y Deduplicación (`data_cleaner.py`):**
   - Calibrar la **Envolvente Estricta de Saneamiento Municipal de Chicago** en `data_cleaner.py`:
     - Latitud Norte máxima: $42.023^\circ\text{ N}$ (Howard St / límite Evanston).
     - Latitud Sur mínima: $41.644^\circ\text{ N}$ (Hegewisch / límite Indiana).
     - Longitud Oeste máxima: $-87.940^\circ\text{ W}$ (Aeropuerto Internacional O'Hare).
     - Longitud Este máxima: $-87.524^\circ\text{ W}$ (Litoral Lago Michigan).
     - *Diferenciación Arquitectónica:* Este BBOX estricto previene contaminar el dataset con puntos en condados aledaños (DuPage) o dentro del Lago Michigan (>13 km fuera de jurisdicción). La caja más holgada ($41.60^\circ - 42.10^\circ\text{ N}, -88.10^\circ - -87.40^\circ\text{ W}$) se reserva exclusivamente para los límites de cámara `maxBounds` en MapLibre.
   - Descartar y aislar coordenadas en `(0.0, 0.0)` o fuera de la envolvente municipal en la tabla de auditoría `crashes_quarantine` para trazabilidad de calidad.
   - Normalizar el formato ISO-8601 de marcas de tiempo en la columna `crash_date`.
   - Ejecutar deduplicación estricta basada en el identificador único `crash_record_id`.
   - Eliminar cualquier atributo de texto libre no estructurado que contenga PII de las víctimas en `silver_people`.
3. **Módulo de Transformación Espacial y Cruce Topológico (`spatial_enrichment.py`):**
   - Convertir latitud y longitud en geometrías PostGIS válidas: `ST_SetSRID(ST_MakePoint(longitude, latitude), 4326)`.
   - Desarrollar el algoritmo de unión topológica espaciotemporal para asociar a cada siniestro vial:
     a) **Volumen de Tráfico AADT:** Localizar la estación de conteo vehicular más cercana mediante el operador KNN de PostGIS (`<->`) dentro de un radio límite de 500 metros, imputando el tráfico promedio si no existe sensor próximo.
     b) **Obras Viales CDOT Activas en Radio de 250 Metros:** Evaluar si el siniestro ocurrió dentro del área de influencia de 250 metros proyectada en `EPSG:3435` y si la fecha del accidente está comprendida entre `start_date` y `end_date` del permiso. Para evitar un Sequential Scan catastrófico sobre los >850,000 registros, la consulta se apoya en los índices funcionales `idx_crashes_geom_3435` y `idx_permits_geom_3435`:
        ```sql
        UPDATE silver_crashes c
        SET 
            active_workzone = true,
            workzone_permit_id = p.permit_id
        FROM silver_road_permits p
        WHERE 
            c.crash_date BETWEEN p.start_date AND p.end_date
            AND ST_DWithin(
                ST_Transform(c.geom, 3435),
                ST_Transform(p.geom, 3435),
                820.21 -- 250 metros exactos en survey feet (aprovecha idx_crashes_geom_3435)
            );
        ```
4. **Optimización de E/S Física Mediante Table Clustering:**
   - Reorganizar las páginas de disco físico de las tablas espaciales según el índice espacial:
     `CLUSTER silver_crashes USING idx_crashes_geom;`
   - Actualizar las estadísticas internas del planificador de consultas: `ANALYZE silver_crashes;`.
5. **Integración con Motor Analítico DuckDB:**
   - Configurar la exportación de las vistas analíticas Gold hacia un archivo DuckDB local (`data/duckdb/chicago_olap.duckdb`) para posibilitar consultas de agregación masiva en microsegundos sin sobrecargar PostgreSQL.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Ejecutar pipeline de ingesta SODA para las tres fuentes principales
python -m app.services.etl.soda_client --dataset crashes --limit 100000
python -m app.services.etl.soda_client --dataset vehicles --limit 100000
python -m app.services.etl.soda_client --dataset people --limit 100000
python -m app.services.etl.soda_client --dataset aadt --all
python -m app.services.etl.soda_client --dataset permits --all

# 2. Ejecutar limpieza, saneamiento y deduplicación
python -m app.services.etl.data_cleaner --verify-integrity

# 3. Ejecutar enriquecimiento topológico con buffer métrico de 250m
python -m app.services.etl.spatial_enrichment --buffer-meters 250

# 4. Ejecutar clustering de tabla y análisis de optimización en PostgreSQL
docker compose exec db psql -U chicago_admin -d chicago_safety -c "
  CLUSTER silver_crashes USING idx_crashes_geom;
  ANALYZE silver_crashes;
  SELECT count(*) AS total_crashes_curados FROM silver_crashes WHERE geom IS NOT NULL;
  SELECT count(*) AS total_obras_activas FROM silver_crashes WHERE active_workzone = true;
"
```

#### Criterios de Aceptación y Quality Gate:
* [x] Tasa de éxito de procesamiento de registros superior al 95%.
* [x] Menos del 1% de registros duplicados en las tablas de la Capa Silver.
* [x] El 100% de las colisiones en `silver_crashes` poseen una geometría válida en `EPSG:4326` contenida estrictamente dentro del polígono delimitador de Chicago.
* [x] El cruce topológico identifica y correlaciona con éxito los siniestros ocurridos dentro del buffer de 250 m de obras CDOT activas.

---

### FASE 3: FEATURE ENGINEERING, MODELADO PREDICTIVO Y SERIALIZACIÓN
* **Duración:** Semanas 6 a 9 (~65 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Cumplimiento directo del **Objetivo Específico OE3**.
* **Responsable Principal:** Dillan Alexander Cardenas Melo (Científico de Datos / Modelador Predictivo). Colabora: Camilo Escandón Romero.
* **Prerrequisitos:** Fase 2 completada; dataset Silver completamente enriquecido con volúmenes de tráfico y afectación de obras en PostgreSQL y DuckDB.

#### Tareas Técnicas Detalladas:
1. **Ingeniería de Características Espaciotemporales (`feature_engineering.py`):**
   - Extraer atributos del vector temporal: hora del día (0–23), día de la semana (0–6), mes del año, indicador de fin de semana e indicador de hora pico (*rush hour* matutino/vespertino).
   - Codificar atributos ambientales y de vía: condición meteorológica (`weather_condition` agrupada en Claro, Lluvia, Nieve, Niebla), condición de iluminación (`lighting_condition` agrupada en Día, Noche Iluminada, Noche Oscura), límite de velocidad publicado (`posted_speed_limit`) y tipo de calzada.
   - Incorporar variables topológicas y de flujo: volumen vehicular medio diario (AADT) normalizado, presencia booleana de obra vial cercana en buffer de 250 m (`active_workzone`) y densidad de siniestros históricos en un radio de 500 m.
   - Definir la variable objetivo supervisada (`target`): clasificación de nivel de riesgo en tres categorías ordínales:
     - `0 (Bajo Riesgo):` Sin heridos y daños materiales menores (< $1,500 USD).
     - `1 (Riesgo Moderado):` Lesiones leves o daños mayores sin hospitalización.
     - `2 (Riesgo Crítico / Alto):` Lesiones graves incapacitantes o fatalidades reportadas.
2. **Partición de Datos y Tratamiento de Desbalanceo de Clases:**
   - Realizar la partición estratificada del dataset: 80% para entrenamiento (`X_train`, `y_train`) y 20% para evaluación fuera de muestra (*hold-out test set* `X_test`, `y_test`).
   - Abordar el desbalance natural de siniestros graves (<5% de la muestra total) mediante ponderación de penalización de clases (`class_weight='balanced'` en Random Forest y cálculo del parámetro `scale_pos_weight` en XGBoost), descartando el submuestreo sintético agresivo para preservar la distribución de probabilidad real.
3. **Entrenamiento de Modelos Supervisados (`train.py`):**
   - Entrenar dos algoritmos de clasificación de ensamble de alto rendimiento:
     a) **Random Forest Classifier:** Modelo robusto contra sobreajuste, afinando número de estimadores (`n_estimators=200`), profundidad máxima (`max_depth=15`) y muestras mínimas por división.
     b) **XGBoost Classifier:** Modelo de *Gradient Boosting* optimizado para datos tabulares y relaciones no lineales complejas (`learning_rate=0.05`, `n_estimators=300`, `subsample=0.8`).
4. **Ajuste de Hiperparámetros y Validación Cruzada (5-Fold CV):**
   - Ejecutar búsqueda sistemática de hiperparámetros mediante `GridSearchCV` / `StratifiedKFold` con 5 pliegues.
   - Evaluar la estabilidad del modelo exigiendo que la varianza de las métricas entre los 5 pliegues sea estrictamente menor al 5%.
5. **Evaluación Rigurosa de Métricas:**
   - Medir el desempeño en el conjunto de prueba independiente:
     - **AUC-ROC Multiclase:** Obligatorio $\ge 0.70$.
     - **Sensibilidad (Recall) en Riesgo Crítico:** Obligatorio $\ge 0.60$ (prioridad Vision Zero: no omitir tramos con potencial de víctimas mortales).
     - **Precisión en Riesgo Crítico:** Obligatorio $\ge 0.65$.
   - Generar matrices de confusión, curvas ROC y análisis de importancia de características (*Feature Importance* / valores SHAP).
6. **Serialización y Empaquetado del Pipeline Ganador:**
   - Empaquetar el pipeline completo de scikit-learn (preprocesador `ColumnTransformer`, imputadores, escaladores y el modelo clasificador XGBoost) en un archivo binario `.joblib` en `backend/app/ml/models/chicago_risk_xgboost.joblib`.
   - Garantizar que el artefacto sea 100% autocontenido y deserializable por FastAPI en menos de 50 ms.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Extraer matriz analítica de características desde PostGIS/DuckDB
python -m app.ml.feature_engineering --output data/processed/features_gold.parquet

# 2. Ejecutar entrenamiento, validación cruzada y evaluación de modelos
python -m app.ml.train --input data/processed/features_gold.parquet --algorithm xgboost

# 3. Ejecutar test unitario del modelo serializado y tiempo de inferencia
pytest backend/tests/test_ml_inference.py -v
```

#### Criterios de Aceptación y Quality Gate:
* [x] AUC-ROC multiclase evaluado en el conjunto de test $\ge 0.70$.
* [x] Recall para la clase de riesgo crítico/fatal $\ge 0.60$.
* [x] Varianza estadística entre los 5 folds de validación cruzada $< 5\%$.
* [x] El artefacto `chicago_risk_xgboost.joblib` existe, pesa menos de 100 MB y responde a inferencias unitarias en menos de 50 ms.

---

### FASE 4: BACKEND API ASÍNCRONA, ENDPOINTS GEOESPACIALES Y PREDICCIÓN EN VIVO
* **Duración:** Semanas 9 a 11 (~45 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Cumplimiento directo del **Objetivo Específico OE4**.
* **Responsable Principal:** Deivid Julian Cardenas Melo (Ingeniero de Datos / Backend). Colabora: Camilo Escandón Romero.
* **Prerrequisitos:** Fase 1 y Fase 3 completadas; modelo `.joblib` generado y accesible; base de datos PostGIS con datos Silver indexados.

#### Tareas Técnicas Detalladas:
1. **Configuración del Ciclo de Vida y Conexiones en FastAPI (`main.py` & `database.py`):**
   - Configurar el evento `lifespan` de FastAPI para inicializar y verificar el pool de conexiones asíncronas de `asyncpg` al arrancar y cerrarlo limpiamente al apagar el servicio.
   - Cargar en memoria global del proceso de Uvicorn el pipeline del modelo ML serializado mediante `joblib.load()` durante el arranque, implementando un mecanismo tolerante a fallos: verificar `os.path.exists(settings.MODEL_PATH)`; si el modelo no existe aún (fases preliminares 1 a 3 o despliegue inicial), emitir un warning en logs y configurar `app.state.model_loaded = False` con un estimador heurístico de respaldo, evitando que Uvicorn aborte con `FileNotFoundError` y garantizando que `/api/v1/health` alcance estado saludable.
   - Habilitar middlewares de compresión Gzip y gestión de cabeceras CORS parametrizables desde `.env`.
2. **Implementación de Endpoints Geoespaciales de Alto Rendimiento:**
   - **`GET /api/v1/crashes/geojson`:** Recibe parámetros de ventana espacial `min_lon`, `min_lat`, `max_lon`, `max_lat` y filtros de fecha/severidad. Ejecuta la consulta SQL compilada con `ST_AsGeoJSON()` y `json_build_object()`, retornando directamente el payload GeoJSON FeatureCollection con cabeceras de caché HTTP en menos de 100 ms.
   - **`GET /api/v1/crashes/clusters`:** Endpoint que aprovecha `ST_ClusterDBSCAN()` de PostGIS 3.4 para calcular agrupamientos de alta densidad espacial en el servidor cuando el nivel de zoom es lejano, entregando centroides y conteos de incidentes.
   - **`GET /api/v1/crashes/stream`:** Endpoint de streaming asíncrono NDJSON con `StreamingResponse` para exportación masiva de datos analíticos.
   - **`GET /api/v1/permits/active`:** Entrega la capa GeoJSON de obras CDOT activas y sus zonas de amortiguamiento de 250 m.
3. **Endpoint de Métricas y Estadísticas Agregadas (`analytics.py`):**
   - **`GET /api/v1/analytics/kpis`:** Retorna métricas cuantitativas consolidadas: total de siniestros, conteo de víctimas mortales e incapacitantes, tramos clasificados en alto riesgo y tasa de variación temporal.
   - **`GET /api/v1/analytics/hourly-distribution`:** Agregación de incidentes por hora del día para alimentar histogramas interactivos.
4. **Endpoint de Inferencia de Riesgo en Vivo (`predict.py`):**
   - **`POST /api/v1/predict/segment-risk`:** Endpoint validado mediante esquemas Pydantic v2 que recibe atributos de un tramo vial (coordenadas GPS en Chicago, límite de velocidad, clima, condición de luz y presencia de obras).
   - Valida que las coordenadas estén dentro del cuadrante de Chicago mediante un validador Pydantic personalizado.
   - Pasa las variables al pipeline XGBoost en memoria (o ejecuta el cálculo de riesgo heurístico ponderado de respaldo si `model_loaded` es False) y retorna en menos de 25 ms el nivel de riesgo predicho (`Bajo`, `Moderado`, `Crítico`), la distribución de probabilidades y los principales factores explicativos.
5. **Documentación Interactiva OpenAPI:**
   - Configurar Swagger UI en `/docs` y ReDoc en `/redoc` con descripciones semánticas completas y ejemplos de payload para cada endpoint.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Ejecutar servidor de desarrollo FastAPI localmente con recarga activa
uvicorn app.main:app --reload --port 8000

# 2. Probar endpoint de diagnóstico y salud
curl -s http://localhost:8000/api/v1/health | jq .

# 3. Probar endpoint GeoJSON con Bounding Box sobre el centro de Chicago
curl -w "\nTiempo Total: %{time_total}s\n" \
  "http://localhost:8000/api/v1/crashes/geojson?min_lon=-87.65&min_lat=41.85&max_lon=-87.60&max_lat=41.90"

# 4. Probar endpoint de inferencia de riesgo con payload JSON
curl -X POST "http://localhost:8000/api/v1/predict/segment-risk" \
  -H "Content-Type: application/json" \
  -d '{
    "coordinates": [-87.6298, 41.8781],
    "posted_speed_limit": 30,
    "weather_condition": "RAIN",
    "lighting_condition": "DARKNESS",
    "active_workzone": true
  }' | jq .

# 5. Ejecutar suite de pruebas automatizadas de endpoints
pytest backend/tests/test_api_health.py backend/tests/test_spatial_queries.py -v
```

#### Criterios de Aceptación y Quality Gate:
* [x] Todos los endpoints responden en menos de 2.0 segundos bajo carga nominal; las consultas BBOX responden en $< 100\text{ ms}$.
* [x] La documentación OpenAPI en `/docs` se genera sin errores de esquema.
* [x] El endpoint `/api/v1/predict/segment-risk` rechaza coordenadas fuera de Chicago con código HTTP 422 y ejecuta predicciones válidas en $< 50\text{ ms}$.
* [x] Cero fugas de conexiones en el pool de `asyncpg` tras 500 peticiones concurrentes continuas.

---

### FASE 5: FRONTEND CARTOGRÁFICO WEBGL, DASHBOARD ANALÍTICO Y VIRTUALIZACIÓN
* **Duración:** Semanas 10 a 12 (~65 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Cumplimiento directo del **Objetivo Específico OE4**.
* **Responsable Principal:** Camilo Escandón Romero (Desarrollador Web / Especialista en BI). Colabora: Dillan Alexander Cardenas Melo.
* **Prerrequisitos:** Fase 4 completada; endpoints de FastAPI en funcionamiento y documentados en `/docs`; Node.js 20 LTS instalado en el entorno de desarrollo.

#### Tareas Técnicas Detalladas:
1. **Inicialización del Proyecto y Configuración del Entorno Frontend:**
   - Generar la aplicación con Vite utilizando la plantilla React 18 + TypeScript.
   - Instalar las dependencias estrictamente congeladas de `package.json` (`maplibre-gl@4.7.1`, `zustand@5.0.0`, `@tanstack/react-query@5.56.2`, `@tanstack/react-virtual@3.10.8`, `recharts@2.12.7`, Tailwind CSS y primitivas Radix UI).
   - Configurar `vite.config.ts` con división manual de paquetes vendor (*manualChunks*) y precompresión Gzip/Brotli.
2. **Implementación del Hook Cartográfico y Contenedor WebGL2 Seguro (`useMapLibre.ts`):**
   - Validar compatibilidad de hardware WebGL2 antes de instanciar (`maplibregl.supported()`); registrar advertencia diagnóstica y exponer bandera `webGlSupported=false` ante entornos sin aceleración.
   - Implementar guardia `isMounted` dentro de `useEffect` y desuscripción explícita `map.off('load', handleLoad)` en la rutina de limpieza para evitar condiciones de carrera durante el doble montaje de React 18 `StrictMode`.
   - Suscribir manejadores para `webglcontextlost` (invocando `e.preventDefault()`) y `webglcontextrestored` (invocando `map.triggerRepaint()`), protegiendo el canvas ante suspensión del equipo o conmutación de GPU.
   - Destruir físicamente la instancia mediante `map.remove()` en el retorno del efecto para erradicar fugas de memoria GPU.
   - Desacoplar estrictamente el estado mutable: sincronizar únicamente el viewport (`center`, `zoom`) y capas con la tienda Zustand `useMapStore`, proveyendo la referencia física del mapa a través de `MapContext.tsx` para evitar colisiones por referencias circulares en DevTools.
   - Centrar la cámara en Chicago (`[-87.6298, 41.8781]`) con límites máximos de holgura metropolitana (`maxBounds: [[-88.1000, 41.6000], [-87.4000, 42.1000]]`).
3. **Construcción de Capas Cartográficas Aceleradas por GPU:**
   - **Capa de Calor (Heatmap):** Implementar `CrashHeatmapLayer.ts` utilizando shaders de densidad ponderados por severidad de la colisión.
   - **Capa de Clusters (Supercluster):** Implementar `CrashClusterLayer.ts` para agrupar puntos dinámicamente con etiquetas de conteo numérico al alejar el zoom.
   - **Capa de Riesgo Vial Predictivo (Choropleth):** Implementar `RiskChoroplethLayer.ts` con rampas de color interpoladas en GPU (Verde = Bajo Riesgo, Amarillo = Moderado, Rojo Carmesí = Crítico).
   - **Capa de Obras Viales CDOT:** Representar las zonas de intervención urbana con polígonos tramados y líneas de amortiguamiento de 250 m.
4. **Mecanismo de Filtrado Inmediato a 60 FPS con GPU Expressions:**
   - Vincular los controles de la barra lateral (slider horario 0–23h, selectores de fecha, casillas de severidad) directamente a expresiones `map.setFilter()` en WebGL.
   - Garantizar respuesta visual en 0 ms sin peticiones de red ni ciclos de recolección de basura.
   - Para las tarjetas de KPI y gráficos, aplicar un retardo (*debounce*) de 250 ms antes de enviar la petición de agregación al backend mediante TanStack Query v5.
5. **Panel Analítico de Métricas y Gráficos Reactivos (Recharts):**
   - Construir componentes para tarjetas de KPI, distribución horaria de siniestros, gráfico de dona con impacto del clima y gráfico de dispersión de volumen AADT vs severidad.
   - Aplicar `minWidth={0}` y `minHeight={0}` en los componentes `<ResponsiveContainer>` de Recharts para prevenir advertencias de dimensiones colapsadas (`-1`) cuando se renderizan dentro de cajones o pestañas ocultas (`display: none`).
   - Montar condicionalmente los componentes de gráficos solo cuando su pestaña o panel contenedor se encuentre activo en el DOM (`activeTab === 'analytics' && <HourlyDistribution />`).
6. **Cajón Inferior con Tabla Virtualizada de Alto Rendimiento:**
   - Implementar `VirtualCrashTable.tsx` integrando `@tanstack/react-table` y `@tanstack/react-virtual`.
   - Permitir desplazarse fluidamente a 60 FPS a través de más de 10,000 registros viales en memoria renderizando únicamente ~30 nodos DOM visibles en el viewport.
   - Añadir interacción bidireccional: al hacer clic en una fila de la tabla, la cámara del mapa vuela (`map.flyTo()`) a las coordenadas del siniestro y resalta la entidad.
7. **Simulador de Escenarios Predictivos en Vivo:**
   - Crear un panel interactivo donde el usuario ajusta variables viales (velocidad reglamentaria, clima, presencia de obras) y consulta en tiempo real al endpoint `/api/v1/predict/segment-risk`, desplegando el nivel de riesgo predicho en un velocímetro/indicador visual.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Inicializar proyecto Vite en la carpeta frontend
cd frontend
npm create vite@latest . -- --template react-ts

# 2. Instalar dependencias exactas y de desarrollo (con tipos de React y herramientas de test Vitest)
npm install react@18.3.1 react-dom@18.3.1 maplibre-gl@4.7.1 zustand@5.0.0 @tanstack/react-query@5.56.2 @tanstack/react-table@8.20.5 @tanstack/react-virtual@3.10.8 clsx@2.1.1 tailwind-merge@2.5.2 lucide-react@0.446.0 @radix-ui/react-slider@1.2.0 @radix-ui/react-tabs@1.1.0 @radix-ui/react-dialog@1.1.1 @radix-ui/react-popover@1.1.1 @radix-ui/react-tooltip@1.1.2 @radix-ui/react-dropdown-menu@2.1.1 @radix-ui/react-checkbox@1.1.1 recharts@2.12.7 axios@1.7.7 date-fns@3.6.0
npm install -D @types/react@18.3.10 @types/react-dom@18.3.0 @types/geojson@7946.0.14 @types/node@22.5.5 tailwindcss@3.4.11 postcss@8.4.47 autoprefixer@10.4.20 vite-plugin-compression@0.5.1 vitest@2.1.1 @testing-library/react@16.0.1 @testing-library/jest-dom@6.5.0 jsdom@25.0.1

# 3. Inicializar Tailwind CSS
npx tailwindcss init -p

# 4. Comprobar tipado TypeScript estricto
npm run typecheck

# 5. Ejecutar suite de pruebas unitarias de componentes y hooks con Vitest
npm test

# 6. Ejecutar servidor de desarrollo local
npm run dev
```

#### Criterios de Aceptación y Quality Gate:
* [x] El mapa se inicializa sin errores de contexto WebGL y se destruye limpiamente al desmontar el componente.
* [x] La manipulación del slider horario y filtros ejecuta el filtrado de capas en GPU a 60 FPS estables.
* [x] La tabla virtualizada se desplaza fluidamente sin sobrepasar 40 nodos DOM en pantalla para 10,000 registros.
* [x] Cero errores de compilación TypeScript (`tsc --noEmit` retorna código de salida 0).
* [x] La suite de pruebas unitarias de frontend (`npm test` con Vitest) pasa al 100% de éxito sin advertencias.

---

### FASE 6: ORQUESTACIÓN MULTI-CONTENEDOR, OPTIMIZACIÓN, TESTING E2E Y DESPLIEGUE FINAL
* **Duración:** Semanas 12 a 13 (~25 horas de esfuerzo conjunto).
* **Alineación con Objetivos:** Consolidación global de **OE1, OE2, OE3 y OE4**.
* **Responsable Principal:** Todo el equipo de proyecto (Deivid Cardenas, Alexander Cardenas, Camilo Escandón).
* **Prerrequisitos:** Fases 1 a 5 completadas y verificadas individualmente; archivos Dockerfile y `nginx.conf` redactados.

#### Tareas Técnicas Detalladas:
1. **Construcción de Imágenes de Producción Multi-Stage:**
   - Compilar la imagen de backend en Debian Slim y verificar que su peso final sea inferior a 250 MB.
   - Compilar la imagen de frontend en Nginx Alpine y verificar que su peso final sea inferior a 35 MB.
2. **Orquestación Unificada con Docker Compose:**
   - Levantar la infraestructura completa con `docker compose up -d --build`.
   - Validar la secuencia estricta de encendido: primero la base de datos PostGIS, luego FastAPI tras verificar la salud de PostgreSQL, y finalmente Nginx tras verificar la salud de FastAPI.
   - Confirmar que el levantamiento total se completa en **menos de 2 minutos**.
3. **Validación del Reverse Proxy Nginx y Eliminación de CORS:**
   - Efectuar peticiones HTTP desde el navegador hacia `http://localhost/api/v1/health` y confirmar que Nginx enruta de forma transparente al puerto 8000 interno sin exponer cabeceras CORS en conflicto.
4. **Pruebas de Estrés y Rendimiento End-to-End:**
   - Ejecutar pruebas de carga sobre los endpoints críticos comprobando que la latencia media se mantiene por debajo de los 2.0 segundos.
   - Verificar que el consumo de memoria RAM de los contenedores respeta los límites asignados (PostGIS < 4GB, Backend < 2GB, Frontend < 512MB).
5. **Auditoría de Seguridad y Verificación de la Rúbrica:**
   - Ejecutar `pip check` en el backend y `npm audit` en el frontend.
   - Verificar la ausencia de datos personales (PII) en la base de datos final.
6. **Generación de Manuales Técnicos y Preparación de Defensa:**
   - Redactar el manual de despliegue operativo en `README.md`.
   - Consolidar el informe técnico final con las recomendaciones de ingeniería vial y priorización de tramos críticos para la Ciudad de Chicago.

#### Comandos CLI Exactos de Ejecución:
```bash
# 1. Detener cualquier contenedor previo y limpiar volúmenes huérfanos
docker compose down

# 2. Construir y desplegar la plataforma completa en modo desacoplado
docker compose up -d --build

# 3. Supervisar el estado de salud de todos los servicios
docker compose ps

# 4. Verificar estadísticas de uso de recursos en tiempo real
docker stats --no-stream

# 5. Validar sonda de salud del frontend y enrutamiento reverso a la API
curl -i http://localhost/health
curl -i http://localhost/api/v1/health

# 6. Inspección de logs unificados para certificar cero advertencias
docker compose logs --tail=50
```

#### Criterios de Aceptación y Quality Gate:
* [x] La plataforma completa (`chicago_postgis`, `chicago_fastapi`, `chicago_frontend`) se levanta en menos de 2 minutos mediante un único comando `docker compose up -d`.
* [x] Los tres contenedores reportan estado `healthy`.
* [x] La aplicación web se sirve en `http://localhost` y consume los servicios de la API sin errores de red ni bloqueos de CORS.
* [x] Se cumple al 100% la Rúbrica de Validación de Dependencias sin conflictos ni advertencias de ruptura.

---

## 7. PROTOCOLO DE PRUEBAS, CALIDAD Y RÚBRICA DE ACEPTACIÓN FINAL

### 7.1 Tipología y Estrategia de Pruebas Automatizadas

El proyecto implementa un esquema integral de aseguramiento de calidad estructurado en cuatro niveles de prueba:

```
+----------------------------------------------------------------------------------------------------+
|                                    PIRÁMIDE DE PRUEBAS DEL PROYECTO                                |
+----------------------------------------------------------------------------------------------------+
|                                  [ Pruebas E2E & Rendimiento ]                                     |
|                      - Latencia de API < 2.0 s bajo carga nominal (k6 / curl)                      |
|                      - Tiempo de arranque de Docker Compose < 2 minutos                            |
|                      - Tasa de 60 FPS sostenida en MapLibre GL JS v4                              |
+----------------------------------------------------------------------------------------------------+
|                             [ Pruebas de Integración y Espaciales ]                                |
|                      - Conectividad Dual-Engine (asyncpg + psycopg3)                               |
|                      - Precisión métrica de buffer topológico en EPSG:3435                         |
|                      - Eficiencia de índices GiST y CLUSTER físico                                 |
+----------------------------------------------------------------------------------------------------+
|                                  [ Pruebas de Modelado ML ]                                        |
|                      - Validación cruzada 5-fold estratificada (Varianza < 5%)                     |
|                      - Verificación de umbrales: AUC-ROC >= 0.70, Recall >= 0.60                   |
|                      - Serialización / deserialización con joblib en < 50 ms                       |
+----------------------------------------------------------------------------------------------------+
|                                    [ Pruebas Unitarias ]                                           |
|                      - Validación de esquemas Pydantic v2 y BBOX de Chicago (Pytest)               |
|                      - Limpieza de nulos y deduplicación en pipeline SODA (Pytest)                 |
|                      - Pruebas de ciclo de vida del hook useMapLibre (Vitest + React Test Lib)     |
+----------------------------------------------------------------------------------------------------+
```

### 7.2 Rúbrica de Aceptación Final y Evaluación Global

Esta rúbrica cuantifica el estado final de entrega del proyecto en cinco dimensiones fundamentales:

```
+---------------------------------------------------------------------------------------------------------------------------------------+
|                                                   RÚBRICA DE ACEPTACIÓN FINAL DEL PROYECTO                                            |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| No | Dimensión Evaluada                 | Criterio de Excelencia (100% Aprobado)| Criterio de Deficiencia (Rechazo)   | Ponderación   |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| D1 | Despliegue y Contenerización       | Todos los servicios orquestados en    | Requiere configuraciones manuales o | 20%           |
|    | Docker Compose                     | Docker Compose; levanta en < 2 min;   | imágenes con fallos de build;       |               |
|    |                                    | healthchecks en verde y cero CORS.    | supera los 2 minutos de arranque.   |               |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| D2 | Integridad Geoespacial y PostGIS   | Esquema relacional estricto; WGS84    | Distorsión métrica > 5% por usar    | 20%           |
|    |                                    | para almacenamiento y EPSG:3435 para  | grados en buffers; ausencia de      |               |
|    |                                    | buffers de 250m; índices GiST y CLUSTER| índices GiST; coordenadas corruptas.|               |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| D3 | Rendimiento de Ingesta y Calidad   | Pipeline SODA tolerante a fallos; tasa| Tasa de éxito < 95%; duplicados > 1%| 20%           |
|    | de Datos (Medallion)               | de éxito > 95%; nulos críticos < 5%;  | o filtrado nulo de coordenadas      |               |
|    |                                    | deduplicación y anonimización PII OK. | erróneas; exposición de PII.        |               |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| D4 | Desempeño del Modelo Predictivo ML | AUC-ROC >= 0.70; Recall >= 0.60 para  | AUC-ROC < 0.70; Recall < 0.60;      | 20%           |
|    |                                    | alta severidad; varianza 5-fold < 5%; | sobreajuste evidente (varianza > 5%)|               |
|    |                                    | inferencia joblib en < 50 ms.         | o tiempos de inferencia lentos.     |               |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
| D5 | Usabilidad y Cartografía WebGL     | MapLibre GL JS v4 a 60 FPS; filtrado  | Navegador se cuelga por exceder     | 20%           |
|    |                                    | por shaders en GPU; tabla virtualizada| contextos WebGL o usar DOM simple;  |               |
|    |                                    | para 10k filas; cero fugas WebGL.     | latencias de API superiores a 2.0s. |               |
+----+------------------------------------+---------------------------------------+-------------------------------------+---------------+
|    | CALIFICACIÓN CONSOLIDADA           | PROYECTO CERTIFICADO PARA PRODUCCIÓN                                        | 100%          |
+----+------------------------------------+-----------------------------------------------------------------------------+---------------+
```

---
*Fin del Plan Maestro de Implementación por Fases y Sprints Técnicos — Emitido por worker_1*
