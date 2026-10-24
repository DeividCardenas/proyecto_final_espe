import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { RiskGrid } from "@/types/api";

export const RISK_SOURCE = "risk-grid";
export const RISK_LAYER = "risk-grid-fill";
export const RISK_OUTLINE_LAYER = "risk-grid-outline";

export const RISK_COLORS = { low: "#16a34a", mid: "#facc15", high: "#b91c1c" } as const;

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

export function setRiskData(map: MLMap, grid: RiskGrid) {
  (map.getSource(RISK_SOURCE) as GeoJSONSource | undefined)?.setData(grid);
  const { p50 = 0, p80 = 0, p95 = 0 } = grid.breaks ?? {};
  const lo = Math.min(p50, p80 - 1e-6);
  map.setPaintProperty(RISK_LAYER, "fill-color", [
    "interpolate", ["linear"], ["get", "risk"],
    lo * 0.5, RISK_COLORS.low,
    p50, "#84cc16",
    p80, RISK_COLORS.mid,
    Math.max(p95, p80 + 1e-6), RISK_COLORS.high,
  ]);
}
