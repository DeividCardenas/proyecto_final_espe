# Validación de los modelos y cómo reentrenar

Este documento describe el diseño de validación vigente de los dos modelos y qué cambia respecto al entrenamiento del 24 de octubre de 2026, cuyas cifras están en `INFORME_RESULTADOS.md`. Esas cifras se deben actualizar después de reentrenar.

## Cómo reentrenar (en el PC con Docker)

```bash
# 1. Actualizar datos (incremental: nuevos y modificados desde la última descarga)
docker compose run --rm etl python -m app.services.etl.pipeline --incremental

# 2. Reentrenar los dos modelos y regenerar la Capa Gold
docker compose run --rm etl sh -c "python -m app.ml.feature_engineering && python -m app.ml.train && python -m app.ml.segment_model && python -m app.services.olap.duckdb_engine --export"

# (Equivalente en un solo paso: pipeline --incremental --train)
docker compose run --rm etl python -m app.services.etl.pipeline --incremental --train

# 3. Pruebas
docker compose run --rm etl pytest -q
```

Sin datos ingeridos desde al menos 36 meses antes del último siniestro, el modelo por cuadra se detiene con un mensaje claro. Con la ingesta por defecto (`--since 2023-01-01`) alcanza. Para fijar las ventanas de la tesis y que el resultado sea reproducible, usa `python -m app.ml.segment_model --anchor-date 2026-10-24`.

**Primera corrida incremental.** La marca de agua antigua no tiene `:updated_at`, así que se vuelven a bajar los últimos 90 días por fecha del siniestro (`--lookback-days`). A partir de ahí se usa `:updated_at`. Para partir limpio, haz una carga completa (sin `--incremental`).

## Modelo por siniestro (`app/ml/train.py`)

| Antes | Ahora |
|---|---|
| Partición aleatoria estratificada 80/20 | Partición **temporal**: train, validación (6 meses) y test (últimos 12 meses) |
| `grid_density` contada sobre todo el periodo, futuro incluido | Contada solo con el pasado de cada partición (`add_grid_density`) |
| Hiperparámetros con 5-fold aleatorio | Elegidos en la ventana de validación |
| Umbral F1 elegido **en test** | Umbral elegido **en validación**, para recall Crítico ≥ 0,60 |
| Ganador elegido por AUC **en test** | Ganador elegido por AUC **en validación** |
| Pesos de clase "balanced": probabilidades infladas | Sin pesos: probabilidades calibradas, con Brier, ECE y curva de fiabilidad en el informe |
| Gate de precisión ≥ 0,65 (inalcanzable con 1,6 %) | Gate de **lift** ≥ 3 sobre la tasa base |
| Estabilidad con 5-fold aleatorio | GroupKFold espacial por bloques de ~2 km |
| Mapa `gold_grid_ml` con predicciones dentro de la muestra | Predicciones **fuera de pliegue espacial** |
| — | **Ablación**: AUC sin las variables del mecanismo del siniestro |
| `intersection_related` nula imputada con la mediana (= 1) | Nula = 0 |

El modelo publicado se reentrena con todos los datos, usando los hiperparámetros y el umbral elegidos en validación.

**Qué esperar al reentrenar:**
- **AUC macro y AUC Crítico:** probablemente bajen algunas centésimas, porque se elimina la fuga temporal de `grid_density` y la partición deja de ser aleatoria.
- **Decisión por argmax:** casi no predecirá "Crítico", porque las probabilidades ahora son reales (~1,6 %). Eso es correcto. La regla publicada es el umbral (`test_decision`), con recall cercano a 0,60 por construcción.
- **`mean_p_critical` del mapa:** baja a valores del orden de la tasa real; deja de estar inflado.
- **Ablación:** se espera un AUC cercano a 0,61, como ya documenta el informe.

## Modelo por cuadra (`app/ml/segment_model.py`)

| Antes | Ahora |
|---|---|
| Ventanas fijas en el código (2023→2024 y 2024→2025) | Ventanas derivadas del último siniestro (`--anchor-date`) |
| Ganador elegido por captura **en test** | Elegido por captura **fuera de pliegue** (CV espacial en train), con regla de 1 error estándar a favor del modelo más simple |
| Sin comparación con la regla obvia | Líneas base: ordenar por siniestros, graves o con lesionados del año anterior |
| Captura sin incertidumbre | IC 95 % bootstrap para cada modelo y línea base, y diferencia pareada ganador – mejor línea base |
| Pesos balanceados + argmax (19 % "Alto" vs 6 % real) | Sin pesos + umbral F1 fuera de pliegue para "Alto"; se reporta `predicted_high_share` |
| Siniestros sin número de calle agrupados como la calle entera | Excluidos |

**Qué esperar al reentrenar:**
- **Cuadras "Alto":** el número baja y queda más cerca de la tasa real.
- **Ventanas:** cambian de años calendario a años móviles terminados en el último siniestro.
- **Línea base:** es posible que la regla "más siniestros el año pasado" capte casi lo mismo que el modelo. En ese caso, `winner_vs_best_baseline.significant = false`, y esa es la conclusión honesta para la tesis: el valor del modelo es la probabilidad calibrada y la explicación por variable, no una captura mucho mayor.

## Nuevas claves en los informes JSON

Las claves anteriores se mantienen, así que la API y el frontend siguen funcionando. Estas son las nuevas:

- `model_report.json`: `windows`, `n_val`, `selection_metric`, `models.*.validation`, `models.*.test_decision`, `models.*.calibration_critical`, `ablation_pre_crash_only`, `spatial_oof`, `provenance`.
- `segment_model_report.json`: `anchor_date`, `selection`, `baselines`, `bootstrap_top10_capture`, `winner_vs_best_baseline`, `models.*.calibration_high`, `models.*.temporal_test.predicted_high_share`, `provenance`.
- Metadatos del artefacto: `critical_threshold` (el que usa la API), `grid_density_years`, `grid_density_window` y `provenance` (commit, versiones de librerías, huella de los datos).

## Ingesta (`app/services/etl`)

- **Incremental por `:updated_at`** en lugar de `crash_date > marca`: recupera los choques reportados tarde y los registros corregidos.
- **Carga completa atómica:** se descarga a `<dataset>.tmp` y solo al terminar reemplaza Bronze.
- **Deduplicación:** gana la descarga más reciente. Antes ganaban las filas con `date_police_notified` nulo.
- **Límite de velocidad 0** = no registrado (NA).
- **Quality Gate:** mide aparte la tasa de `UNKNOWN` (`unknown_critical_rate` < 15 %).
