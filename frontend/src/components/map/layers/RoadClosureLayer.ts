import type { GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { FeatureCollection, Polygon } from "geojson";
import type { PermitProps } from "@/types/api";

export const PERMIT_SOURCE = "permits";
export const PERMIT_FILL_LAYER = "permits-fill";
export const PERMIT_LINE_LAYER = "permits-line";
const HATCH_IMAGE = "hatch-orange";

/** Patrón tramado generado en canvas (sin dependencias de sprites externos). */
function hatchImage(size = 16): ImageData {
  const canvas = document.createElement("canvas");
  canvas.width = canvas.height = size;
  const ctx = canvas.getContext("2d")!;
  ctx.strokeStyle = "rgba(249,115,22,0.85)";
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let o = -size; o <= size; o += size / 2) {
    ctx.moveTo(o, size);
    ctx.lineTo(o + size, 0);
  }
  ctx.stroke();
  return ctx.getImageData(0, 0, size, size);
}

export function addRoadClosureLayers(map: MLMap) {
  if (!map.hasImage(HATCH_IMAGE)) {
    try {
      map.addImage(HATCH_IMAGE, hatchImage());
    } catch {
      /* jsdom / entornos sin canvas */
    }
  }
  if (!map.getSource(PERMIT_SOURCE)) {
    map.addSource(PERMIT_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  }
  if (!map.getLayer(PERMIT_FILL_LAYER)) {
    map.addLayer({
      id: PERMIT_FILL_LAYER,
      type: "fill",
      source: PERMIT_SOURCE,
      layout: { visibility: "none" },
      paint: map.hasImage(HATCH_IMAGE)
        ? { "fill-pattern": HATCH_IMAGE, "fill-opacity": 0.55 }
        : { "fill-color": "#f97316", "fill-opacity": 0.2 },
    });
    map.addLayer({
      id: PERMIT_LINE_LAYER,
      type: "line",
      source: PERMIT_SOURCE,
      layout: { visibility: "none" },
      paint: {
        "line-color": ["match", ["get", "closure"], "Full", "#ef4444", "#f97316"],
        "line-width": 1.2,
        "line-dasharray": [2, 1.5],
      },
    });
  }
}

export function setPermitData(map: MLMap, data: FeatureCollection<Polygon, PermitProps>) {
  (map.getSource(PERMIT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}
