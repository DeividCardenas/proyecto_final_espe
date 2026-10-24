import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { SegmentProps } from "@/types/api";

export const SEGMENT_SOURCE = "segments";
export const SEGMENT_LAYER = "segment-circles";

/** Cuadras con riesgo anticipado: color = P(Alto), tamaño = prioridad (top primero). */
export function addSegmentLayer(map: MLMap) {
  if (map.getSource(SEGMENT_SOURCE)) return;
  map.addSource(SEGMENT_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addLayer({
    id: SEGMENT_LAYER,
    type: "circle",
    source: SEGMENT_SOURCE,
    layout: { visibility: "none", "circle-sort-key": ["get", "p_alto"] },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"],
        10, ["case", ["<=", ["get", "priority_pct"], 0.01], 5, ["<=", ["get", "priority_pct"], 0.1], 3, 1.5],
        15, ["case", ["<=", ["get", "priority_pct"], 0.01], 12, ["<=", ["get", "priority_pct"], 0.1], 8, 4]],
      "circle-color": ["interpolate", ["linear"], ["get", "p_alto"],
        0.1, "#16a34a", 0.35, "#facc15", 0.6, "#f97316", 0.8, "#b91c1c"],
      "circle-stroke-color": "#0f172a",
      "circle-stroke-width": 0.8,
      "circle-opacity": 0.9,
    },
  });
}

export function setSegmentData(map: MLMap, data: FeatureCollection<Point, SegmentProps>) {
  (map.getSource(SEGMENT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}
