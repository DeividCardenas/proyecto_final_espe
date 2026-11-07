import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { RiskGrid } from "@/types/api";

export const RISK_SOURCE = "risk-grid";
export const RISK_LAYER = "risk-grid-fill";
export const RISK_OUTLINE_LAYER = "risk-grid-outline";

export const RISK_COLORS = { low: "#16a34a", lowMid: "#84cc16", mid: "#facc15", high: "#b91c1c" } as const;

/** Rejilla de 500 m coloreada por riesgo crítico medio predicho (rampa interpolada en GPU). */
export function addRiskLayer(map: MLMap, beforeId?: string) {
  if (!map.getSource(RISK_SOURCE)) {
    map.addSource(RISK_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  }
  if (!map.getLayer(RISK_LAYER)) {
    map.addLayer(
      {
        id: RISK_LAYER,
        type: "fill",
        source: RISK_SOURCE,
        layout: { visibility: "none" },
        paint: {
          "fill-color": "#16a34a",
          "fill-opacity": ["interpolate", ["linear"], ["zoom"], 10, 0.55, 15, 0.3],
        },
      },
      beforeId,
    );
    map.addLayer(
      {
        id: RISK_OUTLINE_LAYER,
        type: "line",
        source: RISK_SOURCE,
        layout: { visibility: "none" },
        paint: { "line-color": "#0f172a", "line-width": 0.4, "line-opacity": 0.6 },
      },
      beforeId,
    );
  }
}

/**
 * Paradas de la rampa (bajo, p50, p80, p95) en orden estrictamente creciente: MapLibre
 * rechaza un «interpolate» con paradas repetidas, y con p50 = 0 o p50 = p80 (habitual en
 * el modo empírico, con muchas celdas sin siniestros críticos) la capa quedaba de un color.
 */
export function riskStops(breaks: Record<string, number> | undefined): [number, number, number, number] {
  const { p50 = 0, p80 = 0, p95 = 0 } = breaks ?? {};
  const eps = Math.max(1e-6, Math.abs(p95) * 1e-6);
  const s0 = p50 * 0.5;
  const s1 = Math.max(p50, s0 + eps);
  const s2 = Math.max(p80, s1 + eps);
  const s3 = Math.max(p95, s2 + eps);
  return [s0, s1, s2, s3];
}

export function setRiskData(map: MLMap, grid: RiskGrid) {
  (map.getSource(RISK_SOURCE) as GeoJSONSource | undefined)?.setData(grid);
  const [s0, s1, s2, s3] = riskStops(grid.breaks);
  map.setPaintProperty(RISK_LAYER, "fill-color", [
    "interpolate", ["linear"], ["get", "risk"],
    s0, RISK_COLORS.low,
    s1, RISK_COLORS.lowMid,
    s2, RISK_COLORS.mid,
    s3, RISK_COLORS.high,
  ]);
}
