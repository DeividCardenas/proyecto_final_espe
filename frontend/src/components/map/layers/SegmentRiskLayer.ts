import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { SegmentProps } from "@/types/api";

export const SEGMENT_SOURCE = "segments";
export const SEGMENT_LAYER = "segment-circles";

/**
 * Rampa secuencial sobre el rango que muestra el mapa (top 10%, P(Alto) ≥ ~0,4):
 * tonos apagados para la mayoría y rojo saturado sólo para las cuadras más críticas.
 */
export const SEGMENT_STOPS: [number, string][] = [[0.45, "#64748b"], [0.6, "#cbd5e1"], [0.7, "#f87171"], [0.85, "#b91c1c"]];

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
      "circle-color": ["interpolate", ["linear"], ["get", "p_alto"], ...SEGMENT_STOPS.flat()],
      "circle-stroke-color": "#0f172a",
      "circle-stroke-width": 0.8,
      "circle-opacity": 0.9,
    },
  });
}

export function setSegmentData(map: MLMap, data: FeatureCollection<Point, SegmentProps>) {
  (map.getSource(SEGMENT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}
