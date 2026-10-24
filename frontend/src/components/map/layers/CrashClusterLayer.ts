import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { CrashCollection } from "@/types/api";

export const CLUSTER_SOURCE = "crashes-viewport";
export const CLUSTER_LAYER = "crash-clusters";
export const CLUSTER_COUNT_LAYER = "crash-cluster-count";
export const HIGHLIGHT_SOURCE = "crash-highlight";
export const HIGHLIGHT_LAYER = "crash-highlight";

const EMPTY: CrashCollection = { type: "FeatureCollection", features: [] };

/** Agrupamiento dinámico en el cliente (Supercluster integrado en MapLibre). */
export function addClusterLayers(map: MLMap) {
  if (!map.getSource(CLUSTER_SOURCE)) {
    map.addSource(CLUSTER_SOURCE, {
      type: "geojson",
      data: EMPTY,
      cluster: true,
      clusterRadius: 50,
      clusterMaxZoom: 15,
      clusterProperties: { critical: ["+", ["case", ["==", ["get", "severity"], 2], 1, 0]] },
    });
  }
  if (!map.getLayer(CLUSTER_LAYER)) {
    map.addLayer({
      id: CLUSTER_LAYER,
      type: "circle",
      source: CLUSTER_SOURCE,
      filter: ["has", "point_count"],
      paint: {
        "circle-color": ["step", ["get", "point_count"], "#0ea5e9", 50, "#8b5cf6", 250, "#ec4899", 1000, "#f97316"],
        "circle-radius": ["step", ["get", "point_count"], 14, 50, 20, 250, 28, 1000, 36],
        "circle-opacity": 0.8,
        "circle-stroke-color": "#f8fafc",
        "circle-stroke-width": 1.5,
      },
    });
  }
  if (!map.getLayer(CLUSTER_COUNT_LAYER)) {
    map.addLayer({
      id: CLUSTER_COUNT_LAYER,
      type: "symbol",
      source: CLUSTER_SOURCE,
      filter: ["has", "point_count"],
      layout: {
        "text-field": ["get", "point_count_abbreviated"],
        "text-font": ["Montserrat Medium", "Open Sans Bold"],
        "text-size": 12,
        "text-allow-overlap": true,
      },
      paint: { "text-color": "#ffffff" },
    });
  }
  if (!map.getSource(HIGHLIGHT_SOURCE)) {
    map.addSource(HIGHLIGHT_SOURCE, { type: "geojson", data: EMPTY });
    map.addLayer({
      id: HIGHLIGHT_LAYER,
      type: "circle",
      source: HIGHLIGHT_SOURCE,
      paint: {
        "circle-radius": 14,
        "circle-color": "rgba(0,0,0,0)",
        "circle-stroke-color": "#22d3ee",
        "circle-stroke-width": 3,
      },
    });
  }
}

export function setClusterData(map: MLMap, data: CrashCollection) {
  (map.getSource(CLUSTER_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}

export function setHighlight(map: MLMap, coords: [number, number] | null) {
  (map.getSource(HIGHLIGHT_SOURCE) as GeoJSONSource | undefined)?.setData(
    coords
      ? { type: "FeatureCollection", features: [{ type: "Feature", properties: {}, geometry: { type: "Point", coordinates: coords } }] }
      : EMPTY,
  );
}
