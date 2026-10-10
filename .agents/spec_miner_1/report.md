# INFORME EXHAUSTIVO DE MINERÍA DE ESPECIFICACIONES TÉCNICAS Y REQUERIMIENTOS
**Proyecto:** Arquitectura de Big Data y Modelado Predictivo Geoespacial de Riesgos Viales y Movilidad Urbana  
**Fecha de Análisis:** 12 de septiembre de 2026  
**Documentos Fuente Analizados:**
- `c:\Users\Lab Creacion Digital\Documents\proyecto espe\FichaDeProyecto_EspBigData_Completada.docx` (Documento Canónico Final v1.0)
- `c:\Users\Lab Creacion Digital\Documents\proyecto espe\FichaDeProyecto_EspBigData (2).docx` (Borrador de Trabajo previo)
- `c:\Users\Lab Creacion Digital\Documents\proyecto espe\.agents\ORIGINAL_REQUEST.md` (Directriz de Implementación y Arquitectura Objetivo)

---

## 1. RESUMEN EJECUTIVO Y OBJETIVO GENERAL DEL PROYECTO

### 1.1 Naturaleza del Proyecto
El proyecto consiste en el diseño, desarrollo y despliegue de una **plataforma analítica integral de código abierto, contenerizada con Docker**, basada en una **arquitectura de Big Data geoespacial (Arquitectura Medallón: Bronze, Silver, Gold)** y modelos de **Machine Learning supervisado**.

Su propósito central es unificar, cruzar y analizar tres fuentes de datos tradicionalmente aisladas de la **Ciudad de Chicago (EE.UU.)**:
1. **Siniestralidad Vial (E-Crash):** Registros históricos y detallados de colisiones, vehículos y personas involucradas.
2. **Volumen de Tráfico (AADT):** Conteos de tráfico promedio diario en puntos estratégicos de la red vial.
3. **Intervenciones en la Vía Pública (CDOT Permits):** Permisos de cierre total o parcial de calles y aceras por obras de construcción o mantenimiento.

El objetivo final es superar el enfoque tradicional de gestión reactiva del tráfico, permitiendo clasificar y anticipar tramos viales de alto riesgo mediante modelado predictivo, y visualizar dichos riesgos a través de un mapa de calor y panel interactivo para la toma de decisiones informada por parte de las autoridades de tránsito y planificadores urbanos.

### 1.2 Pregunta Problema y Pregunta de Decisión
* **Pregunta Problema:**  
  *¿En qué medida los patrones temporales, las características del flujo vehicular y la presencia de alteraciones viales por obras inciden en la probabilidad y severidad de los siniestros de tránsito en la red urbana de Chicago, y con qué nivel de precisión pueden anticiparse los segmentos de alto riesgo mediante modelos de aprendizaje automático?*
* **Pregunta de Decisión:**  
  *¿Cómo deben priorizarse y asignarse las intervenciones preventivas (control operativo de velocidad, señalización y adecuación de infraestructura) en los tramos críticos clasificados por el modelo, para maximizar la mitigación de siniestros graves y fatales bajo restricciones presupuestales?*

### 1.3 Casos de Éxito de Referencia
El proyecto adopta como marcos metodológicos e inspiracionales:
1. **Vision Zero (Ciudad de Nueva York):** Programa enfocado en eliminar fatalidades viales mediante análisis de puntos negros e ingeniería vial priorizada con datos.
2. **Crash Analysis System - CAS (Nueva Zelanda):** Sistema nacional geoespacial que cruza accidentes con inventario de infraestructura.
3. **iRAP (International Road Assessment Programme):** Metodología estandarizada global de clasificación de estrellas de riesgo vial según flujo, accidentalidad y geometría.

---

## 2. STAKEHOLDERS, ROLES Y USUARIOS OBJETIVO

### 2.1 Equipo del Proyecto y Asignación de Roles
De acuerdo con la versión completada de la Ficha de Proyecto (`FichaDeProyecto_EspBigData_Completada.docx`), el equipo está estructurado en los siguientes roles funcionales:

| Integrante | Rol Oficial Asignado | Responsabilidades Clave |
|---|---|---|
| **Deivid Julian Cardenas Melo** | **Ingeniero de Datos / Líder del Proyecto** | Diseño del modelo de base de datos relacional y dimensional; construcción de pipelines ETL automáticos de extracción (SODA API), transformación y carga; garantía de integridad referencial y conectividad de datos. |
| **Dillan Alexander Cardenas Melo** | **Científico de Datos / Modelador Predictivo** | Análisis Exploratorio de Datos (EDA); depuración avanzada; análisis espacial y buffers topológicos; ingeniería de características; entrenamiento, ajuste y evaluación de modelos de ML. |
| **Camilo Escandón Romero** | **Desarrollador Web / Especialista en BI & Validación** | Desarrollo del frontend cartográfico y dashboard analítico interactivo; integración de mapas de calor (Leaflet/MapLibre); pruebas funcionales de extremo a extremo, aseguramiento de calidad (QA) y documentación. |

### 2.2 Tutor y Sponsor Académico
* **Tutor / Docente a cargo:** Mag. José Camilo Eraso
* **Institución:** UNICESMAG (Universidad Cesmag)

### 2.3 Usuarios Destinatarios y Casos de Uso
1. **Autoridades de Tránsito y Secretarías de Movilidad (ej. CDOT / CPD):**  
   - Priorizar patrullajes, operativos de control de velocidad y cámaras de fotomulta en tramos clasificados como de alto riesgo.
   - Planificar señalización vial horizontal y vertical basada en evidencia empírica.
2. **Planificadores Urbanos e Ingenieros de Transporte:**  
   - Evaluar el impacto de desvíos y cierres viales programados sobre la accidentalidad de vías alternas.
   - Diseñar intervenciones de infraestructura física (reductores, iluminación, cruces peatonales protegidos).
3. **Investigadores Académicos en Seguridad Vial y Movilidad Urbana:**  
   - Consumir datasets limpios, curados y enriquecidos espacialmente para investigaciones longitudinales.
4. **Ciudadanía General:**  
   - Conocer de forma transparente las zonas de mayor riesgo y las intervenciones activas de seguridad vial.

---

## 3. ARQUITECTURA DE DATOS, INGESTA Y ATRIBUTOS GEOESPACIALES

### 3.1 Justificación en las 5 V's del Big Data
* **Volumen:** Consolidación de más de **4.5 millones de registros históricos**:
  * > 850,000 colisiones viales acumuladas.
  * > 1,700,000 registros de vehículos involucrados.
  * > 2,000,000 de registros de personas/víctimas.
  * Decenas de miles de aforos de tráfico y permisos de obras activas.
* **Variedad:** Tablas estructuradas relacionales, descripciones textuales de informes policiales, atributos temporales continuos, y geometrías espaciales (puntos de colisión, ubicaciones de aforo, geometrías de obras viales).
* **Velocidad:** Ingesta periódica automatizada e incremental desde la API pública SODA.
* **Veracidad:** Protocolos de validación de calidad, detección de anomalías, saneamiento del 5% al 10% de registros con coordenadas nulas/erróneas e integridad referencial forzada.
* **Valor:** Generación de un score de riesgo predictivo accionable para salvar vidas mediante intervenciones viales preventivas.

### 3.2 Catálogo de Fuentes de Datos (City of Chicago Open Data Portal)

| Dataset | Identificador / SODA Endpoint | Responsable | Granularidad & Variables Principales | Calidad / Particularidades |
|---|---|---|---|---|
| **Traffic Crashes — Crashes** | `85ca-t3if` | Chicago Police Dept (CPD) | Nivel: Accidente individual.<br>`CRASH_RECORD_ID`, `CRASH_DATE`, `POSTED_SPEED_LIMIT`, `TRAFFIC_CONTROL_DEVICE`, `WEATHER_CONDITION`, `LIGHTING_CONDITION`, `FIRST_CRASH_TYPE`, `TRAFFICWAY_TYPE`, `ROAD_DEFECT`, `CRASH_TYPE`, `DAMAGE`, `INJURIES_TOTAL`, `INJURIES_FATAL`, `LATITUDE`, `LONGITUDE`. | ~5-10% de coordenadas nulas que requieren filtrado; >100,000 registros/año. |
| **Traffic Crashes — Vehicles** | `68nd-jvt3` | Chicago Police Dept (CPD) | Nivel: Vehículo involucrado.<br>`CRASH_RECORD_ID`, `VEHICLE_ID`, `MAKE`, `MODEL`, `VEHICLE_YEAR`, `VEHICLE_TYPE`, `MANEUVER`, `OCCUPANT_CNT`. | Relación 1:N con Crashes. Permite caracterizar tipos de vehículo y maniobra previa. |
| **Traffic Crashes — People** | `u6pd-qa9d` | Chicago Police Dept (CPD) | Nivel: Persona/Pasajero/Peatón.<br>`PERSON_ID`, `PERSON_TYPE`, `CRASH_RECORD_ID`, `VEHICLE_ID`, `SEX`, `AGE`, `INJURY_CLASSIFICATION`, `SAFETY_EQUIPMENT`. | Relación 1:N con Crashes/Vehicles. **Estricta anonimización**: sin nombres ni PII. |
| **Average Daily Traffic Counts (AADT)** | `pfsx-4n4m` | CDOT | Nivel: Estación de aforo vial.<br>`ID`, `TRAFFIC_VOLUME_COUNT_LOCATION_ADDRESS`, `STREET`, `DATE_OF_COUNT`, `TOTAL_PASSING_VEHICLE_VOLUME`, `LATITUDE`, `LONGITUDE`. | Conteos volumétricos georreferenciados para calcular exposición al riesgo. |
| **CDOT Road Closure Permits** | `eka9-q4gf` | CDOT | Nivel: Permiso de obra/cierre.<br>`PERMIT_ID`, `STREET_NAME`, `START_DATE`, `END_DATE`, `WORK_TYPE`, `CLOSURE_TYPE`. | Temporalidad de fechas de inicio/fin para determinar obras activas al momento del siniestro. |
| **Speed Limits (Complementaria)** | `rvmx-4bpt` | CDOT | Red vial y límites de velocidad reglamentarios. | Validación de exceso de velocidad y clasificación de vía. |
| **Red Light Cameras (Complementaria)** | `thvf-6diy` | CDOT | Ubicación espacial de cámaras de semáforo en rojo. | Medida de control y fiscalización existente. |

### 3.3 Sistemas de Referencia Espacial (CRS) y Análisis Topológico
* **Almacenamiento y Salida Web:** **WGS84 (EPSG:4326)** con latitud/longitud decimal.
* **Cálculo Métrico y Proximidad:** **Illinois State Plane East (EPSG:3435)** (proyección cónica conformal de Lambert en pies de EE.UU. / metros) necesaria para calcular distancias euclidianas exactas en el área urbana de Chicago sin distorsión esférica.
* **Criterio de Asociación Topológica:** Se define un **radio de influencia (Buffer) de 250 metros** alrededor de:
  1. Estaciones de conteo vehicular (AADT): para asociar el volumen de tráfico al siniestro más próximo.
  2. Obras viales activas: para evaluar si un accidente ocurrió bajo la zona de influencia temporal y espacial del cierre de vía.
* **Funciones PostGIS Clave:** `ST_MakePoint`, `ST_SetSRID`, `ST_Transform`, `ST_Buffer`, `ST_DWithin`, indexación espacial mediante índices **GiST**.

### 3.4 Arquitectura por Capas (Medallion Architecture)
* **Capa Bronze (Raw Data):** Ingesta cruda directa desde la API SODA mediante scripts en Python (`requests`, `sodapy`), guardada en Parquet y tablas crudas sin procesar.
* **Capa Silver (Staged / Cleaned / Enriched Data):** Limpieza de tipos, imputación, deduplicación, reproyección geográfica y cruce topológico de proximidad (buffer 250m). Almacenada en PostgreSQL 16 + PostGIS 3.4.
* **Capa Gold (Analytical / Feature Store Data):** Vistas analíticas y tablas agregadas por tramo vial y ventana temporal, matriz de variables para entrenamiento de Machine Learning y capas optimizadas GeoJSON para el servicio API.

---

## 4. REQUERIMIENTOS FUNCIONALES (RF)

| ID | Nombre | Descripción de Funcionalidad | Entrada | Salida | Reglas / Criterios de Aceptación |
|---|---|---|---|---|---|
| **RF-01** | Ingesta Automática SODA | Módulo que se conecta a los endpoints de Socrata (data.cityofchicago.org) y descarga los registros de manera paginada e incremental. | Parámetros de API, app_token, límites de fecha. | Archivos JSON/Parquet crudos en Capa Bronze. | Debe manejar paginación (offset/limit) y reconexión automática ante timeouts. |
| **RF-02** | Depuración y Calidad de Datos | Limpieza y saneamiento de registros crudos: eliminación de nulos críticos, normalización de formatos de fecha (`CRASH_DATE`), deduplicación por ID único. | Tablas crudas de Bronze. | Tablas depuradas en Silver; log de auditoría de calidad. | Registros sin latitud/longitud válidas son depurados; completitud en campos clave ≥ 95%; duplicados < 1%. |
| **RF-03** | Reproyección y Creación Geométrica | Generación de geometrías espaciales PostGIS a partir de coordenadas decimales y reproyección a EPSG:3435 para cálculos métricos. | Coordenadas `LATITUDE`, `LONGITUDE` en EPSG:4326. | Columna `geometry(Point, 4326)` con índice espacial GiST. | 100% de registros en Silver deben contar con geometrías válidas y verificadas dentro del bounding box de Chicago. |
| **RF-04** | Cruce Topológico por Proximidad | Asociación de siniestros viales con la estación AADT más cercana y con permisos de cierre de obra activos en un radio de 250 metros. | Puntos de accidentes, estaciones AADT, geometrías/puntos de obras y fechas. | Tabla enriquecida con `traffic_volume` y flag `active_roadwork`. | Unión espaciotemporal: la obra debe haber estado activa en la fecha del siniestro (`CRASH_DATE` entre `START_DATE` y `END_DATE`). |
| **RF-05** | Ingeniería de Características (Feature Store) | Extracción de variables predictivas: hora del día, día de la semana, estación climática, condición de luz, superficie vial, volumen vehicular y densidad de obras. | Tablas Silver enriquecidas. | Matriz de características (dataset Gold) dividida en 80% train / 20% test. | Variables estandarizadas y codificadas (One-Hot / Ordinal Encoding) listas para scikit-learn. |
| **RF-06** | Entrenamiento y Validación de Modelos | Entrenamiento supervisado de al menos dos algoritmos (Random Forest y Gradient Boosting / XGBoost) para clasificar el nivel de riesgo de los tramos viales. | Dataset de entrenamiento (80%). | Modelos entrenados, matriz de confusión, reporte de métricas y curvas ROC. | Validación cruzada 5-fold (varianza < 5%); AUC-ROC ≥ 0.70; Recall ≥ 0.60 para alta severidad; Precision ≥ 0.65 para alto riesgo. |
| **RF-07** | Serialización y Empaquetado del Modelo | Guardado persistente del pipeline del modelo óptimo (preprocesador + clasificador) para inferencia en producción. | Objeto modelo entrenado. | Archivo binario serializado `.joblib`. | El artefacto debe ser autocontenido y cargable por el servicio FastAPI sin reentrenar. |
| **RF-08** | API REST de Consulta y Predicción | Servicio web backend con endpoints para servir capas espaciales GeoJSON, datos agregados y realizar inferencias de riesgo en tiempo real. | Solicitudes HTTP GET con filtros (fechas, tipo de siniestro, coordenadas Bounding Box). | Respuestas JSON / GeoJSON estándar; documentación interactiva OpenAPI/Swagger. | Tiempo de respuesta < 2 segundos por consulta; endpoints RESTful bien versionados (`/api/v1/...`). |
| **RF-09** | Panel Visual y Cartografía Interactiva | Frontend web con mapa interactivo que renderiza capas de calor (heatmaps) de riesgo vial, marcadores agrupados (clusters) de accidentes y polígonos de obras. | GeoJSON provisto por el backend FastAPI. | Interfaz web responsiva con controles de capas y gráficos analíticos. | Mapa interactivo (Leaflet.js / MapLibre GL JS) + gráficos estadísticos (Chart.js); filtros reactivos por zona, severidad y fecha. |

---

## 5. REQUERIMIENTOS NO FUNCIONALES (RNF)

### 5.1 Rendimiento y Eficiencia
* **RNF-01 (Tiempo de Respuesta):** Las consultas de la API para capas cartográficas y métricas deben resolverse en **menos de 2 segundos** bajo carga nominal.
* **RNF-02 (Procesamiento Acelerado):** Uso de **DuckDB y formato columnar Apache Parquet** para agregaciones analíticas complejas en memoria, aliviando la carga transaccional del motor principal.
* **RNF-03 (Tasa de Procesamiento ETL):** El pipeline de ingesta y transformación debe mantener una **tasa de éxito superior al 95%** de registros procesados sin fallas bloqueantes.

### 5.2 Arquitectura, Portabilidad y Despliegue
* **RNF-04 (100% Código Abierto):** Toda la solución debe construirse exclusivamente sobre herramientas de software libre, **sin dependencia de servicios en la nube pagos ni licencias comerciales**.
* **RNF-05 (Contenerización Total con Docker Compose):** La base de datos geoespacial, el backend API y el frontend deben estar orquestados mediante `docker-compose.yml`, logrando un despliegue operativo completo en **menos de 2 minutos**.
* **RNF-06 (Multiplataforma):** Ejecución reproducible garantizada en Windows, Linux y macOS sin modificaciones en los scripts base.

### 5.3 Calidad, Integridad y Gobernanza de Datos
* **RNF-07 (Completitud de Atributos Críticos):** ≥ 95% de campos indispensables sin valores nulos tras la fase de curación.
* **RNF-08 (Unicidad y Deduplicación):** Tasa de duplicados menor al 1% en tablas de Capa Silver y Gold.
* **RNF-09 (Integridad Referencial Estricta):** 100% de los registros en las tablas de `vehicles` y `people` deben vincularse a un `CRASH_RECORD_ID` válido en la tabla `crashes`.
* **RNF-10 (Estandarización Cartográfica):** 100% de geometrías normalizadas en WGS84 (EPSG:4326) e indexadas espacialmente con índices GiST.

### 5.4 Desempeño del Modelo Predictivo
* **RNF-11 (Capacidad de Discriminación):** AUC-ROC global ≥ 0.70.
* **RNF-12 (Sensibilidad a Siniestros Graves):** Recall ≥ 0.60 en la predicción de tramos con siniestros de alta severidad (lesiones incapacitantes y fatales).
* **RNF-13 (Precisión en Riesgo Crítico):** Precision ≥ 0.65 para la clase "Riesgo Alto".
* **RNF-14 (Estabilidad Estadística):** Varianza menor al 5% entre los 5 pliegues de validación cruzada (5-fold cross validation).

### 5.5 Seguridad, Privacidad y Ética
* **RNF-15 (Anonimización de Datos Personales):** Estricta eliminación de PII (Personally Identifiable Information). Solo se admiten campos demográficos agregados (rango etario, género, clasificación médica general de la lesión).
* **RNF-16 (Segregación de Secretos):** Manejo de credenciales de base de datos y tokens de API mediante variables de entorno en archivo `.env` nunca versionado en Git.

---

## 6. RESTRICCIONES, HITOS Y CRONOGRAMA DE TRABAJO (EDT)

### 6.1 Restricciones del Proyecto
* **Tiempo:** Horizonte estricto de **13 semanas** académicas (Inicio: **15 de agosto de 2026**; Finalización: **15 y 16 de noviembre de 2026**). Carga estimada: **~270 horas totales** (~20 horas/semana de trabajo en equipo).
* **Acceso a Datos:** Dependencia exclusiva de la API pública SODA del portal de la Ciudad de Chicago; el pipeline debe ser tolerante a esquemas dinámicos o variaciones de tipo.
* **Infraestructura:** Prohibido el uso de infraestructura cloud de pago; entorno local 100% autocontenido en Docker.
* **Alcance Geográfico:** Exclusivamente la zona metropolitana de la Ciudad de Chicago.
* **Exclusiones Explícitas (Out-of-Scope):**
  - No incluye visión artificial ni análisis de video de cámaras de tráfico en vivo.
  - No incluye sensores IoT ni compra de hardware físico.
  - No incluye aplicaciones móviles nativas (iOS/Android); se enfoca en aplicación web responsiva.

### 6.2 Estructura de Desglose de Trabajo (EDT / WBS)

```
PROYECTO: ARQUITECTURA DE BIG DATA Y MODELADO PREDICTIVO GEOESPACIAL DE RIESGOS VIALES
│
├── FASE 1: INGENIERÍA DE DATOS Y BASE DE DATOS GEOESPACIAL (OE1) [Semanas 1-4 | ~55 horas]
│   ├── 1.1 Análisis estructural y perfilamiento de archivos fuentes
│   ├── 1.2 Modelado relacional y dimensional (Entidad-Relación y Medallion)
│   ├── 1.3 Creación de tablas, claves primarias/foráneas y restricciones
│   ├── 1.4 Configuración de extensiones PostGIS e índices espaciales GiST (WGS84)
│   └── 1.5 Pruebas de integridad referencial y consultas espaciales iniciales
│
├── FASE 2: PIPELINE ETL Y ENRIQUECIMIENTO GEOESPACIAL (OE2) [Semanas 3-7 | ~80 horas]
│   ├── 2.1 Desarrollo de scripts de ingesta automatizada e incremental (SODA API)
│   ├── 2.2 Módulo de depuración, saneamiento de nulos y deduplicación
│   ├── 2.3 Módulo de transformación geográfica (EPSG:4326 <-> EPSG:3435)
│   ├── 2.4 Algoritmo de cruce topológico por radio de influencia (Buffer 250 m)
│   ├── 2.5 Carga masiva en PostgreSQL/PostGIS y DuckDB
│   └── 2.6 Validación de métricas de calidad (Tasa de éxito > 95%)
│
├── FASE 3: INGENIERÍA DE CARACTERÍSTICAS Y MODELADO PREDICTIVO (OE3) [Semanas 7-12 | ~65 horas]
│   ├── 3.1 Feature engineering (temporales, climáticas, flujo AADT, obras cercanas)
│   ├── 3.2 Partición de datos (80% Train / 20% Test) y balanceo de clases
│   ├── 3.3 Entrenamiento de algoritmos supervisados (Random Forest, XGBoost / Gradient Boosting)
│   ├── 3.4 Ajuste de hiperparámetros mediante GridSearchCV y validación cruzada (5-fold)
│   ├── 3.5 Evaluación de métricas de desempeño (AUC-ROC >= 0.70, Recall >= 0.60)
│   ├── 3.6 Serialización del modelo ganador (.joblib)
│   └── 3.7 Generación del mapa de riesgo basado en predicciones
│
├── FASE 4: SERVICIOS BACKEND API Y DASHBOARD CARTOGRÁFICO (OE4) [Semanas 10-13 | ~45 horas]
│   ├── 4.1 Desarrollo de API REST con FastAPI (endpoints GeoJSON y predicción en vivo)
│   ├── 4.2 Documentación interactiva de la API con OpenAPI / Swagger
│   ├── 4.3 Construcción del Frontend cartográfico interactivo (Leaflet.js / MapLibre GL)
│   ├── 4.4 Integración de mapas de calor, clusters y capas de obras
│   ├── 4.5 Componentes analíticos y gráficos interactivos (Chart.js)
│   └── 4.6 Redacción de manuales técnicos y de despliegue
│
└── FASE 5: INTEGRACIÓN TOTAL, PRUEBAS Y CIERRE (OE1-OE4) [Semanas 12-13 | ~25 horas]
    ├── 5.1 Orquestación unificada con Docker Compose (levantamiento < 2 min)
    ├── 5.2 Pruebas de estrés y latencia de consultas (< 2 seg)
    ├── 5.3 Elaboración del informe técnico final con recomendaciones viales
    └── 5.4 Sustentación y defensa final ante evaluadores
```

### 6.3 Entregables Formales por Objetivo

| Objetivo | Entregable Oficial | Descripción y Artefactos Asociados |
|---|---|---|
| **OE1** | **Repositorio de Datos Geoespacial Contenerizado** | Imagen y volumen Docker de PostgreSQL + PostGIS con modelo relacional estructurado, claves primarias y foráneas, índices espaciales GiST y geometrías estandarizadas en WGS84 (EPSG:4326). |
| **OE2** | **Pipeline ETL y Dataset Curado** | Scripts modulares en Python para la descarga vía API SODA, limpieza, deduplicación y cruce topológico espacial (buffers de 250 m), junto con su reporte automatizado de métricas de calidad de datos. |
| **OE3** | **Modelos Predictivos Serializados y Evaluación** | Modelos de Machine Learning supervisados (Random Forest / XGBoost) serializados (`.joblib`), acompañados del reporte técnico con curvas ROC, matrices de confusión y métricas de desempeño (AUC-ROC ≥ 0.70, Recall ≥ 0.60). |
| **OE4** | **Plataforma Web Analítica Desplegable** | Código fuente de la API REST (FastAPI) y la interfaz cartográfica interactiva (Web con Leaflet.js / MapLibre GL), junto con el archivo `docker-compose.yml` que permite levantar todo el sistema con un solo comando. |

---

## 7. MATRIZ DE MINERÍA DE CARACTERÍSTICAS (FEATURES DISCOVERED)

A continuación se detalla la extracción exhaustiva de todas las características identificadas en la documentación:

### 7.1 Features Discovered
| # | Categoría | Característica (Feature) | Descripción | Entradas | Salidas | Comportamiento ante Errores | Descubierto Vía |
|---|---|---|---|---|---|---|---|
| 1 | Ingesta | Conector SODA API (`sodapy`) | Conexión HTTP REST a los 5 datasets de Chicago con soporte de paginación por bloques (limit/offset). | Endpoint URL, App Token, limit, offset, filtros SoQL. | DataFrames crudos / archivos Parquet. | Reintento automático con backoff exponencial ante error 429/500; validación de esquema si la API altera columnas. | Ficha Completada (Row 25, 27) |
| 2 | Ingesta | Ingesta Incremental | Descarga de colisiones y permisos nuevos basada en marca de tiempo (`CRASH_DATE` / `START_DATE`). | Última fecha de registro en BD. | Nuevos registros a procesar en Bronze. | Si la fecha es inválida o nula, ejecuta fallback a descarga completa de la última ventana temporal. | Ficha Completada (Row 21, 27) |
| 3 | Calidad | Depuración de Coordenadas Nulas | Filtro estricto que descarta registros de choques sin georreferenciación válida (~5-10% de registros crudos). | `LATITUDE`, `LONGITUDE`. | Registros con coordenadas no nulas y válidas dentro de Chicago; log de descartes. | Registros sin coordenadas son archivados en tabla de auditoría `crashes_unlocated` para métricas. | Ficha Completada (Row 11, 25, 27) |
| 4 | Calidad | Validación de Integridad Referencial | Enlace estricto de tablas hijas (`vehicles`, `people`) hacia la tabla padre (`crashes`) mediante `CRASH_RECORD_ID`. | `CRASH_RECORD_ID` de tablas hijas y padre. | Registros enlazados al 100%; registros huérfanos aislados. | Registros huérfanos se registran en log de inconsistencia y se omiten de la capa Silver analítica. | Ficha Completada (Row 29) |
| 5 | Calidad | Anonimización y Cumplimiento Ético | Eliminación o enmascaramiento de datos personales de las víctimas de choques; conservación exclusiva de variables demográficas agregadas. | Datos de personas (`people`). | Columnas preservadas: `AGE`, `SEX`, `INJURY_CLASSIFICATION`, `SAFETY_EQUIPMENT`; cero PII. | Si se detectan campos de texto libre con nombres/teléfonos, se suprimen en la etapa de transformación. | Ficha Completada (Row 11, 25, 35) |
| 6 | Espacial | Reproyección Cartográfica Dual | Transformación de coordenadas de WGS84 (EPSG:4326) a Illinois State Plane East (EPSG:3435) para cálculo métrico y retorno a 4326 para publicación web. | Puntos y polígonos geométricos. | Geometrías proyectadas en pies/metros o grados decimales. | Coordenadas fuera de rango disparan alerta espacial y descarte de fila. | Ficha Completada (Row 27) |
| 7 | Espacial | Buffer de Proximidad de 250 Metros | Creación de áreas de influencia circulares de 250 metros alrededor de estaciones AADT y zonas de obras viales. | Puntos de aforo, polígonos/puntos de permisos CDOT. | Capa de geometrías buffer (`ST_Buffer(geom, 250)`). | Geometría inválida es reparada con `ST_MakeValid` o descartada. | Ficha Completada (Row 19, 21, 27) |
| 8 | Espacial | Cruce Topológico Espaciotemporal | Asociación entre siniestros viales y obras viales activas si el accidente ocurre dentro del buffer de 250m y durante las fechas del permiso. | Geometría de choque, fecha del choque, buffer de obra, rango de fechas del permiso. | Atributo booleano `has_nearby_work` y conteo de obras cercanas. | Si las fechas del permiso son ambiguas, se asigna valor neutro/imputado con flag de advertencia. | Ficha Completada (Row 19, 21, 27) |
| 9 | Espacial | Indexación GiST | Creación de índices espaciales GiST en columnas geométricas de PostgreSQL/PostGIS para acelerar consultas topológicas. | Tablas espaciales en PostgreSQL. | Índices espaciales GiST activos. | Fallo en creación de índice dispara revisión de coordenadas nulas o corrompidas. | Ficha Completada (Row 19, 27, 33) |
| 10 | Motor Analítico | Motor OLAP DuckDB + Parquet | Procesamiento analítico acelerado en memoria y transformaciones vectorizadas antes de la carga a PostgreSQL. | Archivos Parquet de Capa Silver. | Tablas agregadas Gold optimizadas. | Fallo de memoria en DuckDB redirige el flujo de agregación a procesamiento por lotes o directamente a PostgreSQL. | Ficha Completada (Row 27) |
| 11 | ML | Feature Engineering Espaciotemporal | Generación de variables derivadas: hora del día, día de la semana, estación, condición meteorológica agrupada, iluminación, volumen AADT y obras cercanas. | Tablas Silver cruzadas. | Vector de características numéricas y categóricas codificadas. | Valores ausentes se imputan según moda (categóricas) o mediana (numéricas). | Ficha Completada (Row 23, 27) |
| 12 | ML | Modelado Random Forest | Algoritmo ensemble basado en árboles de decisión para clasificación de severidad y probabilidad de siniestro vial. | Matriz X_train, vector y_train (80%). | Modelo Random Forest ajustado, feature importances. | Manejo de desbalanceo de clases mediante `class_weight='balanced'`. | Ficha Completada (Row 19, 23, 27, 33) |
| 13 | ML | Modelado Gradient Boosting / XGBoost | Algoritmo de boosting supervisado optimizado para clasificación de tramos de alto riesgo. | Matriz X_train, vector y_train (80%). | Modelo Gradient Boosting / XGBoost ajustado. | Control de overfitting mediante regularización y early stopping. | Ficha Completada (Row 19, 23, 27, 33) |
| 14 | ML | Optimización de Hiperparámetros | Búsqueda sistemática de hiperparámetros mediante `GridSearchCV` con 5-fold cross validation. | Espacio de hiperparámetros, folds=5. | Mejores hiperparámetros y reporte de varianza (< 5%). | Si la varianza entre folds supera el 5%, se amplía la regularización o se simplifica el modelo. | Ficha Completada (Row 27, 29) |
| 15 | ML | Serialización con Joblib | Almacenamiento binario del pipeline de predicción completo en archivo `.joblib` para consumo desacoplado en FastAPI. | Pipeline scikit-learn entrenado. | Archivo `model_v1.joblib` empaquetado. | Excepción de serialización si existen lambdas no serializables; reemplazo por clases estándar de sklearn. | Ficha Completada (Row 27, 33) |
| 16 | Backend | API REST Asíncrona (FastAPI) | Servicio web en Python con soporte asíncrono que expone endpoints REST documentados vía Swagger/OpenAPI. | Peticiones HTTP de clientes web. | Respuestas JSON estructuradas con códigos HTTP estándar. | Manejo de excepciones globales con códigos 400, 404, 422, 500 y mensajes legibles. | Ficha Completada (Row 19, 21, 27, 33) |
| 17 | Backend | Servicio de Geometrías GeoJSON | Endpoint que serializa datos espaciales de PostGIS a formato estándar RFC 7946 (GeoJSON FeatureCollections). | Parámetros de consulta (BBox, fechas, severidad). | GeoJSON FeatureCollection con geometrías y propiedades. | Si la consulta retorna > 50,000 puntos, aplica clustering o muestreo para prevenir desborde de memoria en el navegador. | Ficha Completada (Row 27) |
| 18 | Backend | Endpoint de Predicción de Riesgo en Vivo | Endpoint `/api/v1/predict-risk` que recibe atributos de un tramo vial y retorna el nivel de riesgo predicho por el modelo ML. | JSON con `posted_speed`, `weather`, `traffic_volume`, `active_work`, etc. | JSON con `risk_level` ("Bajo", "Medio", "Alto"), probabilidad y factores determinantes. | Validación de esquema mediante Pydantic; rechazo automático (422) ante variables ausentes o tipos inválidos. | Ficha Completada (Row 19, 27, 33) |
| 19 | Frontend | Mapa Interactivo de Calor (Heatmap) | Capa cartográfica web que renderiza densidad de siniestros viales con gradiente visual de calor. | Coordenadas e intensidad de siniestros. | Capa ráster de calor dinámica en el mapa. | Reducción de resolución o degradación elegante si la GPU del cliente tiene rendimiento limitado. | Ficha Completada (Row 19, 21, 27, 31) |
| 20 | Frontend | Capa de Obras e Intervenciones Viales | Visualización de puntos y polígonos de cierres viales por permisos CDOT sobre el mapa interactivo. | Datos GeoJSON de permisos CDOT. | Marcadores poligonales interactivos con popup de información (fechas y tipo de obra). | Marcador especial de advertencia si la obra tiene fechas vencidas o inconsistentes. | Ficha Completada (Row 27, 31) |
| 21 | Frontend | Panel Analítico y Métricas (Chart.js) | Gráficos estadísticos de tendencias temporales (por hora, día, mes), distribución por tipo de choque y severidad. | Datos tabulares y agregados de la API. | Gráficos interactivos de barras, líneas y sectores. | Muestra estado "No hay datos para el filtro seleccionado" sin romper el dashboard. | Ficha Completada (Row 27, 31) |
| 22 | Frontend | Filtrado Dinámico Multidimensional | Controles de interfaz para filtrar simultáneamente por rango de fechas, condición climática, tipo de vía y nivel de riesgo. | Selección de usuario en dropdowns, sliders y datepickers. | Actualización reactiva del mapa y las gráficas en tiempo real. | Bloqueo de combinaciones de filtros imposibles y reseteo a valores por defecto. | Ficha Completada (Row 19, 21, 26, 31) |
| 23 | Despliegue | Orquestación Docker Compose | Configuración unificada multicontenedor (`docker-compose.yml`) que enlaza PostgreSQL/PostGIS, FastAPI backend y Frontend web. | Archivos Dockerfile, `docker-compose.yml`, `.env`. | Red de contenedores enlazada y servicios operativos en < 2 minutos. | Reinicio automático (`restart: on-failure`) y healthchecks para asegurar que PostgreSQL esté listo antes de iniciar FastAPI. | Ficha Completada (Row 19, 21, 27, 33) |

---

### 7.2 Casos de Borde (Edge Cases) Observados en la Especificación

| # | Característica | Entrada / Situación Extrema | Comportamiento Esperado y Mitigación |
|---|---|---|---|
| 1 | Ingesta SODA | Cambio de nombres de columnas o tipos de datos por parte de la Ciudad de Chicago en la API pública. | El pipeline cuenta con validación de tipos y mapeador de esquemas en Python para mitigar inconsistencias sin abortar el proceso. |
| 2 | Ingesta SODA | Fallo o corte temporal de conexión a Internet durante la descarga de lotes masivos (>100,000 filas). | Paginación por bloques con guardado de checkpoint/cursor (`offset`), permitiendo reanudar la ingesta en el punto de interrupción. |
| 3 | Calidad Espacial | Coordenadas en (0.0, 0.0) o fuera del cuadrante geográfico de Chicago (lat: 41.6 to 42.1, lon: -87.9 to -87.5). | Reglas de validación en Python descartan las filas corruptas, enviándolas a una tabla de auditoría sin romper la ingesta general. |
| 4 | Asociación Espacial | Accidente vial ocurrido a más de 250 metros de cualquier estación de conteo vehicular AADT. | Se imputa el valor de tráfico promedio distrital o se asigna categoría especial de "tráfico desconocido / no censado", evitando registros nulos en el modelo. |
| 5 | Asociación Espacial | Múltiples permisos de obras concurrentes dentro del mismo radio de 250 metros del siniestro. | Se calcula una variable de "densidad de obras cercanas" (conteo entero) y se toma la obra de mayor severidad o mayor duración de cierre. |
| 6 | Integridad Referencial | Registros de colisión con `INJURIES_TOTAL > 0` pero sin registros de personas asociadas en la tabla `people`. | El pipeline registra la inconsistencia en el informe de calidad, pero preserva el accidente en la capa Silver usando los totales reportados en el reporte principal. |
| 7 | Machine Learning | Gran desbalance de clases (los accidentes fatales/graves son una minoría estadística < 5% respecto a daños materiales leves). | Aplicación de técnicas de balanceo (ponderación de pesos de clase en Random Forest/XGBoost `scale_pos_weight` y métrica de evaluación centrada en Recall y AUC-ROC en lugar de simple Accuracy). |
| 8 | Despliegue Docker | Intento del backend FastAPI de conectarse a PostgreSQL antes de que el contenedor de PostGIS haya completado su inicialización de extensiones. | Uso de `depends_on` con condición `condition: service_healthy` y script de espera activa (`wait-for-it` o reintentos en SQLAlchemy/GeoAlchemy2). |
| 9 | Visualización Web | Petición de renderizado de más de 100,000 puntos individuales en el navegador del cliente al quitar todos los filtros. | El backend implementa agregación por cuadrícula espacial (grid binning / hexbin) o clustering dinámico para nunca sobrecargar el DOM con más de 2,000 entidades simultáneas. |

---

## 8. ANÁLISIS COMPARATIVO DE DOCUMENTOS FUENTE Y EVOLUCIÓN DE LA ESPECIFICACIÓN

Al cotejar los archivos presentes en el espacio de trabajo, se determinan las siguientes conclusiones de trazabilidad:

1. **`FichaDeProyecto_EspBigData_Completada.docx` vs `FichaDeProyecto_EspBigData (2).docx`:**
   - La estructura general de ambas fichas es idéntica en el 98% de su contenido.
   - **Diferencia Crítica 1 (Fila 15 - Equipo y Roles):** En el archivo `(2)`, los nombres de los integrantes aparecían listados sin la asignación individualizada de su rol. En la versión `Completada`, se mapea explícitamente:
     - Deivid Julian Cardenas Melo -> Ingeniero de Datos / Líder del Proyecto.
     - Dillan Alexander Cardenas Melo -> Científico de Datos / Modelador Predictivo.
     - Camilo Escandón Romero -> Desarrollador Web / Especialista en BI & Validación.
   - **Diferencia Crítica 2 (Fila 33 - Entregables Oficiales):** En el archivo `(2)`, la celda de entregables finales por objetivo estaba vacía. En la versión `Completada`, se definen con máxima precisión técnica los 4 entregables formales (Repositorio PostGIS contenerizado, Pipeline ETL + Dataset Curado, Modelos Serializados `.joblib` con evaluación ROC/Recall, y Plataforma Web Desplegable FastAPI + Leaflet con `docker-compose.yml`).
   - **Conclusión:** `FichaDeProyecto_EspBigData_Completada.docx` es el documento canónico de referencia que debe gobernar la planificación y validación.

2. **Ficha de Proyecto vs `ORIGINAL_REQUEST.md` (Alineación Arquitectónica):**
   - La Ficha de Proyecto menciona a nivel de frontend "Leaflet.js / MapLibre GL", mientras que `ORIGINAL_REQUEST.md` precisa: **PostgreSQL 16, PostGIS 3.4, GeoAlchemy2, FastAPI, React, MapLibre GL JS**.
   - Esta precisión es totalmente compatible y representa la maduración técnica del diseño: la Ficha establece los requerimientos funcionales y de negocio (código abierto, mapa interactivo, FastAPI, contenedores), mientras que la directriz de ingeniería concreta el stack moderno a React 18+ y MapLibre GL JS con renderizado WebGL vectorial acelerado por hardware, ideal para visualizar grandes volúmenes geoespaciales como los >850k choques de Chicago.

---

## 9. REFERENCIAS Y FUENTES OFICIALES CITADAS

1. **City of Chicago Data Portal:**  
   - Traffic Crashes (Crashes): `https://data.cityofchicago.org/Transportation/Traffic-Crashes-Crashes/85ca-t3if`  
   - Traffic Crashes (Vehicles): `https://data.cityofchicago.org/Transportation/Traffic-Crashes-Vehicles/68nd-jvt3`  
   - Traffic Crashes (People): `https://data.cityofchicago.org/Transportation/Traffic-Crashes-People/u6pd-qa9d`  
   - Average Daily Traffic Counts: `https://data.cityofchicago.org/Transportation/Average-Daily-Traffic-Counts/pfsx-4n4m`  
   - CDOT Road Closure Permits: `https://data.cityofchicago.org/Transportation/CDOT-Road-Closure-Permits/eka9-q4gf`  
   - Speed Limits: `https://data.cityofchicago.org/Transportation/Speed-Limits/rvmx-4bpt`  
   - Red Light Camera Locations: `https://data.cityofchicago.org/Transportation/Red-Light-Camera-Locations/thvf-6diy`  
2. **Organizaciones Internacionales y Normativa de Seguridad Vial:**  
   - Organización Mundial de la Salud (OMS) — Informes sobre la Situación Mundial de la Seguridad Vial.  
   - National Highway Traffic Safety Administration (NHTSA) — Multimodal crash prediction guidelines.  
   - Illinois Department of Transportation (IDOT) — Crash reporting & AADT measurement manuals.  
   - International Road Assessment Programme (iRAP) — Star Rating protocols.  
3. **Estándares Cartográficos y de Datos:**  
   - EPSG:4326 — World Geodetic System 1984 (WGS84).  
   - EPSG:3435 — NAD83 / Illinois East (ftUS).  
   - SODA API — Socrata Open Data API Specification.  
   - RFC 7946 — The GeoJSON Format Specification.  

---
*Fin del Informe de Minería de Especificaciones — spec_miner_1*
