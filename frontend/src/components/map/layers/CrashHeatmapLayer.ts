import type { ExpressionSpecification, Map as MLMap } from "maplibre-gl";

export const CRASH_TILE_SOURCE = "crashes-mvt";
export const HEATMAP_LAYER = "crash-heatmap";
export const POINTS_LAYER = "crash-points";
export const DETAIL_ZOOM = 13;

export const SEVERITY_COLORS = ["#38bdf8", "#facc15", "#dc2626"] as const;

// Severidad crítica pesa 6 veces más que un siniestro leve en la densidad
const severityWeight: ExpressionSpecification = ["match", ["get", "severity"], 2, 6, 1, 1.5, 0.6];

// Última plantilla aplicada por mapa (MapLibre no expone la actual de forma pública)
const currentTileUrl = new WeakMap<MLMap, string>();

export function addCrashTileLayers(map: MLMap, tileUrl: string) {
  currentTileUrl.set(map, tileUrl);
  if (!map.getSource(CRASH_TILE_SOURCE)) {
    map.addSource(CRASH_TILE_SOURCE, { type: "vector", tiles: [tileUrl], minzoom: 9, maxzoom: 15 });
  }
  if (!map.getLayer(HEATMAP_LAYER)) {
    map.addLayer({
      id: HEATMAP_LAYER,
      type: "heatmap",
      source: CRASH_TILE_SOURCE,
      "source-layer": "crashes",
      maxzoom: 16,
      paint: {
        // ln(1+n): las celdas agregadas de zoom bajo no saturan la rampa de densidad
        "heatmap-weight": ["*", ["ln", ["+", 1, ["coalesce", ["get", "count"], 1]]], severityWeight, 0.12],
        "heatmap-intensity": ["interpolate", ["linear"], ["zoom"], 9, 0.25, 12, 0.6, 15, 1.2],
        "heatmap-radius": ["interpolate", ["linear"], ["zoom"], 9, 9, 13, 14, 16, 22],
        "heatmap-opacity": ["interpolate", ["linear"], ["zoom"], 13, 0.85, 16, 0.25],
        "heatmap-color": [
          "interpolate", ["linear"], ["heatmap-density"],
          0, "rgba(0,0,0,0)",
          0.15, "#1e3a8a",
          0.35, "#7c3aed",
          0.55, "#db2777",
          0.75, "#f97316",
          1, "#fde047",
        ],
      },
    });
  }
  if (!map.getLayer(POINTS_LAYER)) {
    map.addLayer({
      id: POINTS_LAYER,
      type: "circle",
      source: CRASH_TILE_SOURCE,
      "source-layer": "crashes",
      minzoom: DETAIL_ZOOM,
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["zoom"], 13, ["match", ["get", "severity"], 2, 5, 3],
          17, ["match", ["get", "severity"], 2, 10, 6]],
        "circle-color": ["match", ["get", "severity"], 2, SEVERITY_COLORS[2], 1, SEVERITY_COLORS[1],
          SEVERITY_COLORS[0]],
        "circle-stroke-color": "#0f172a",
        "circle-stroke-width": 1,
        "circle-opacity": 0.9,
      },
    });
  }
}

/** Cambia el rango de fechas reemplazando la plantilla de teselas (filtro en servidor). */
export function setCrashTileUrl(map: MLMap, tileUrl: string) {
  const src = map.getSource(CRASH_TILE_SOURCE) as { setTiles?: (t: string[]) => void } | undefined;
  if (!src || currentTileUrl.get(map) === tileUrl) return; // evita abortar las teselas en curso
  currentTileUrl.set(map, tileUrl);
  src.setTiles?.([tileUrl]);
}
