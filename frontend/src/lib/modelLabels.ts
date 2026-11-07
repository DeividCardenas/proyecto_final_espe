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
