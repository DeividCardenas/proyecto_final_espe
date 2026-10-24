import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { HotspotProps } from "@/types/api";

export const AADT_SOURCE = "aadt-stations";
export const AADT_LAYER = "aadt-circles";
export const HOTSPOT_SOURCE = "hotspots";
export const HOTSPOT_LAYER = "hotspot-circles";

/** Círculos proporcionales (área ∝ volumen diario) de las estaciones de aforo. */
export function addTrafficLayers(map: MLMap) {
  if (!map.getSource(AADT_SOURCE)) {
    map.addSource(AADT_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({
      id: AADT_LAYER,
      type: "circle",
      source: AADT_SOURCE,
      layout: { visibility: "none" },
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["sqrt", ["get", "volume"]], 30, 2, 100, 6, 300, 16],
        "circle-color": "#22d3ee",
        "circle-opacity": 0.35,
        "circle-stroke-color": "#67e8f9",
        "circle-stroke-width": 1,
      },
    });
  }
  if (!map.getSource(HOTSPOT_SOURCE)) {
    map.addSource(HOTSPOT_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
    map.addLayer({
      id: HOTSPOT_LAYER,
      type: "circle",
      source: HOTSPOT_SOURCE,
      layout: { visibility: "none" },
      paint: {
        "circle-radius": ["interpolate", ["linear"], ["sqrt", ["get", "count"]], 4, 6, 15, 18, 30, 30],
        "circle-color": ["interpolate", ["linear"], ["/", ["get", "critical"], ["get", "count"]], 0, "#facc15", 0.05, "#dc2626"],
        "circle-opacity": 0.55,
        "circle-stroke-color": "#fef08a",
        "circle-stroke-width": 1.5,
      },
    });
  }
}

export function setAadtData(map: MLMap, data: FeatureCollection<Point>) {
  (map.getSource(AADT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}

export function setHotspotData(map: MLMap, data: FeatureCollection<Point, HotspotProps>) {
  (map.getSource(HOTSPOT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}
