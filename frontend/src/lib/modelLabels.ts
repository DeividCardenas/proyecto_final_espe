/** Nombres legibles de los algoritmos que devuelve la API. */
export const MODEL_LABELS: Record<string, string> = {
  logistic_regression: "Regresión logística",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
  lightgbm: "LightGBM",
};

export const modelLabel = (k: string | null | undefined) => (k ? MODEL_LABELS[k] ?? k : "—");

/** Año evaluado a partir de la ventana del reporte («historia 2024 -> riesgo 2025» → "2025"). */
export function targetYear(window: string | null | undefined): string | null {
  const years = window?.match(/\d{4}/g);
  return years?.length ? years[years.length - 1] : null;
}

/** Reglas sin modelo con las que se compara el modelo por cuadra. */
export const BASELINE_LABELS: Record<string, string> = {
  historial_siniestros: "Regla: más siniestros el año previo",
  historial_graves: "Regla: más graves el año previo",
  historial_lesionados: "Regla: más lesionados el año previo",
};
