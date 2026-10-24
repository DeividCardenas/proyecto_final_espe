# Informe técnico de resultados

Este informe resume la ejecución de las Fases 2 a 6 del plan sobre los datos abiertos de Chicago descargados el 23 de octubre de 2026. Cubre siniestros ocurridos entre el 1 de enero de 2023 y el 23 de octubre de 2026. Las cifras salen de `data/processed/quality_report.json` y de `backend/app/ml/models/model_report.json`, y son reproducibles con los comandos del README.

## 1. Datos ingeridos (Capa Bronze → Silver)

| Dataset | ID SODA | Descargados | Cargados en Silver | Observación |
|---|---|---|---|---|
| Siniestros | `85ca-t3if` | 422.626 | 418.170 | 4.456 en cuarentena (4.419 sin coordenadas, 37 en (0,0)) |
| Vehículos | `68nd-jvt3` | 862.107 | 853.359 | Se descartan las unidades cuyo siniestro está en cuarentena |
| Personas | `u6pd-qa9d` | 928.839 | 919.337 | Sin `city`, `zipcode`, hospital ni datos de EMS (PII) |
| Permisos CDOT | `pubx-yq2d` | 373.657 | 257.506 | Se excluyen mudanzas, rodajes, eventos, cancelados y duplicados |
| Aforos AADT | `pfsx-4n4m` | 1.279 | 1.279 | Único dataset de aforos con coordenadas: estudio de 2006 |

Quality Gate de la Fase 2: aprobado.

* Tasa de éxito del procesamiento: 98,9% (el mínimo era 95%).
* Duplicados en `silver_crashes`: 0%.
* Geometrías inválidas o fuera de la envolvente municipal: 0.
* Nulos en variables críticas: 0%.
* Columnas PII presentes: ninguna.
* Índices GiST: un índice canónico por columna geométrica (los duplicados que había dejado la Fase 1 se renombraron en la migración 0003).

## 2. Enriquecimiento topológico

* **AADT:** el 100% de los siniestros recibió la estación de aforo más cercana mediante KNN sobre GiST en EPSG:3435. En el 15,2% no había estación a menos de 500 m, así que se imputó el promedio (19.466 vehículos por día).
* **Obras CDOT a menos de 250 m** (820,21 pies de topógrafo en EPSG:3435, error medido menor al 1%):
  * Con todos los permisos, el 88,8% de los siniestros caía "en zona de obra". Esa variable estaba saturada y no discriminaba nada, porque la mayoría de los permisos son aperturas de servicios públicos y ocupación de acera.
  * Con solo permisos de cierre de calzada (`Full` o `Partial`), la proporción baja al 29,3%. Este es el criterio que se dejó.
  * Contraste con la bandera policial `WORK_ZONE_I`: de los 1.281 siniestros que la policía marcó como zona de obra, 569 (44%) coinciden con un permiso de cierre vigente.
* **Optimización física:** `CLUSTER` de las tres tablas espaciales por su índice GiST, seguido de `ANALYZE`. El enriquecimiento completo tarda unos 70 segundos.

## 3. Modelo predictivo (Fase 3)

Variable objetivo con tres clases: 0 Bajo (24,4%), 1 Moderado (74,0%) y 2 Crítico (1,6%, fatalidades o lesiones incapacitantes). La partición es estratificada 80/20, con ponderación balanceada de clases y una búsqueda en rejilla con StratifiedKFold de 5 pliegues.

| Métrica (conjunto de test) | Random Forest | **XGBoost (ganador)** | Umbral del plan | ¿Cumple? |
|---|---|---|---|---|
| AUC-ROC multiclase (OvR macro) | 0,693 | **0,708** | ≥ 0,70 | Sí |
| AUC-ROC Crítico frente al resto | 0,859 | **0,863** | — | — |
| Recall de la clase Crítica | 0,630 | **0,668** | ≥ 0,60 | Sí |
| Precisión de la clase Crítica | 0,084 | **0,074** | ≥ 0,65 | **No** |
| Variación del AUC entre los 5 pliegues | — | **0,6%** | < 5% | Sí |
| Tamaño, carga e inferencia del artefacto | — | 2 MB / 66 ms / 5 ms | < 100 MB, < 50 ms | Sí |

### Hallazgos sobre el modelo

1. **Solo con las condiciones previas al choque, el AUC se queda en 0,61.** Esas condiciones son la hora, el clima, la luz, la velocidad, el AADT, las obras, la densidad histórica y la ubicación. El AUC supera 0,70 únicamente al agregar el mecanismo del siniestro: tipo de colisión, causa contributiva, número de unidades, fuga y presencia de peatón, ciclista o motocicleta. Para evaluar un tramo sin un siniestro concreto, la API promedia la predicción sobre los 80 mecanismos históricamente más frecuentes, ponderados por su frecuencia. Esto equivale a calcular el valor esperado de la severidad condicionado a que ocurra un siniestro en ese lugar y momento.
2. **La meta de precisión de 0,65 en la clase crítica no es alcanzable con estos datos**, porque esa clase es el 1,6% de los casos. Con el umbral que maximiza F1 (0,75), la precisión sube a 0,159 y el recall baja a 0,349. Se recomienda redefinir esa meta como lift sobre la tasa base: 0,074 frente a 0,016 es 4,7 veces mejor que elegir al azar.
3. **Las variables más importantes son, en orden:** peatón involucrado, ciclista, colisión tipo PEDESTRIAN, motocicleta y luego el resto de tipos de colisión. El horario nocturno es la primera variable ambiental del ranking.

## 4. Hallazgos para la ingeniería vial (Vision Zero)

* **Usuarios vulnerables.** El 14,4% de los atropellos a peatones y el 8,0% de los siniestros con ciclistas terminan en lesión grave o muerte. La media general es 1,6%, así que el riesgo es 9 y 5 veces mayor.
* **Velocidad.** La tasa crítica crece de forma monótona con el límite señalizado: 0,7% a 15 mph, 1,2% a 25 mph, 1,6% a 30 mph, 2,4% a 35 mph y 3,5% a 40 mph. Bajar de 30 a 25 mph en los corredores de mayor riesgo es la palanca con más evidencia en estos datos.
* **Oscuridad.** En noche con vía iluminada la tasa crítica es 2,45%, frente a 1,38% de día. Hay más velocidad y más usuarios vulnerables de noche.
* **Corredores prioritarios por número de siniestros críticos (2023 a 2026):**

  | Corredor | Siniestros críticos | Fatalidades |
  |---|---|---|
  | Western Ave | 200 | 13 |
  | Pulaski Rd | 176 | 17 |
  | Cicero Ave | 176 | 13 |
  | Halsted St | 154 | 20 |
  | Ashland Ave | 144 | 12 |

  Halsted St destaca por su número de fatalidades.
* **Obras viales.** En los datos no aparece asociación entre obras con cierre de calzada y severidad: la tasa crítica es 1,51% con obra y 1,60% sin ella. Las obras se asocian a una mayor frecuencia de siniestros por su ubicación céntrica, pero no a una mayor gravedad.
* **Celdas de alto riesgo.** La capa "Riesgo predictivo ML" del mapa muestra 256 celdas de 500 m con al menos 30 siniestros y una tasa crítica igual o mayor al 3%. Son candidatas a auditorías de seguridad vial.

## 5. Desempeño de la plataforma (Fase 6)

| Prueba | Resultado | Criterio |
|---|---|---|
| Arranque en frío de `docker compose up -d` hasta tres contenedores `healthy` | 19 s | < 2 min |
| BBOX GeoJSON del Loop con 1.000 entidades, en caliente | < 100 ms (pytest) | < 100 ms |
| Teselas MVT (zoom 14) | 31 a 68 ms de media; la caché de Nginx devuelve HIT | — |
| Carga: 500 peticiones con 50 concurrentes, 5 endpoints, a través de Nginx | 0 errores, latencia media de 0,76 s, 59 req/s | media < 2 s |
| Conexiones a PostgreSQL tras la carga | 41, acotadas por el pool (4 workers × 10) | sin fugas |
| Memoria: PostGIS, API y Nginx | 1,2 GB / 0,78 GB / 16 MB | < 4 GB / < 2 GB / < 512 MB |
| `pip check` | Sin dependencias rotas; numpy 1.26.4 (< 2.0) | Rúbrica 1 |
| `npm audit --omit=dev` | 0 vulnerabilidades | Rúbrica 4 |

### Desviaciones respecto al plan

* **MapLibre GL JS pasó de 4.7.1 a 6.15.0 y axios de 1.7.7 a 1.20.0.** Las versiones fijadas tenían vulnerabilidades: XSS en `DOM.sanitize` en MapLibre (crítica) y SSRF en axios (alta). La versión 6 exige registrar el Web Worker con `setWorkerUrl`, que Vite empaqueta como chunk propio. `maplibregl.supported()` ya no existe, así que la detección de WebGL2 se hace a mano.
* **La imagen del backend ocupa 1,2 GB, no 250 MB.** El stack científico (XGBoost, SciPy, PyArrow, DuckDB y scikit-learn) no cabe en 250 MB. Usar `xgboost-cpu` en vez de `xgboost` quitó unos 800 MB de binarios CUDA y NCCL.
* **La API usa 4 workers de Uvicorn con un límite de 4 CPU.** La configuración del plan (2 workers y 2 CPU) dejaba en 4 s la latencia de `/predict` bajo carga, porque la inferencia está limitada por CPU.
* **DBSCAN no sirve para agrupar a escala de ciudad.** Con radios de kilómetros, la densidad de Chicago encadena toda la ciudad en un único cluster. `/crashes/clusters` detecta puntos calientes de 40 m y la agrupación por zoom se resuelve en el cliente con Supercluster.
* **Se usan teselas vectoriales MVT además de GeoJSON.** Permiten dibujar los 418 mil siniestros. Por debajo del zoom 13 se agregan por celda, hora y severidad, de modo que el filtrado en GPU sigue funcionando.
* Las dependencias de desarrollo (vite 5, vitest 2) tienen avisos de `npm audit` que no llegan a la imagen de producción.
