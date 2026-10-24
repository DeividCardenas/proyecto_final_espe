import type { Map as MLMap } from "maplibre-gl";
import type { ThemeDef } from "./themes";
import { HEATMAP_LAYER, POINTS_LAYER } from "@/components/map/layers/CrashHeatmapLayer";
import { CLUSTER_LAYER } from "@/components/map/layers/CrashClusterLayer";

type PaintProp =
  | "background-color" | "fill-color" | "fill-opacity" | "line-color" | "line-opacity" | "text-color" | "text-halo-color";

// Valores originales del mapa base, para poder volver al tema Clásico
const originals = new WeakMap<MLMap, Map<string, unknown>>();

function setPaint(map: MLMap, layerId: string, prop: PaintProp, value: unknown) {
  let store = originals.get(map);
  if (!store) {
    store = new Map();
    originals.set(map, store);
  }
  const key = `${layerId}|${prop}`;
  if (!store.has(key)) store.set(key, map.getPaintProperty(layerId, prop as never) ?? null);
  map.setPaintProperty(layerId, prop, value as never);
}

function restore(map: MLMap) {
  const store = originals.get(map);
  if (!store) return;
  for (const [key, value] of store) {
    const [layerId, prop] = key.split("|");
    if (map.getLayer(layerId)) map.setPaintProperty(layerId, prop as never, value as never);
  }
}

const MAJOR = /_(pri|sec|trunk|mot)_/;

/** Recolorea el mapa base vectorial de CARTO y las capas de datos según el tema. */
export function applyMapTheme(map: MLMap, theme: ThemeDef) {
  const style = map.getStyle();
  if (!style?.layers) return;

  if (theme.id === "classic") {
    restore(map);
  } else {
    const m = theme.map;
    for (const layer of style.layers) {
      const id = layer.id;
      if (layer.type === "background") setPaint(map, id, "background-color", m.background);
      else if (layer.type === "fill") {
        if (id.startsWith("water")) setPaint(map, id, "fill-color", m.water);
        else if (id.startsWith("building")) setPaint(map, id, "fill-color", m.building);
        else if (/^(landcover|landuse|park)/.test(id)) setPaint(map, id, "fill-color", m.land);
      } else if (layer.type === "line") {
        if (id.startsWith("boundary")) {
          setPaint(map, id, "line-color", m.boundary);
          setPaint(map, id, "line-opacity", 0.35);
        } else if (id === "waterway") {
          setPaint(map, id, "line-color", m.water);
        } else if (id.endsWith("_case") || id.includes("_case_")) {
          setPaint(map, id, "line-color", m.background);
        } else if (/^(road|tunnel|bridge|aeroway|rail)/.test(id)) {
          setPaint(map, id, "line-color", MAJOR.test(id) ? m.roadMajor : m.roadMinor);
          setPaint(map, id, "line-opacity", MAJOR.test(id) ? m.roadOpacity : Math.min(1, m.roadOpacity + 0.2));
        }
      } else if (layer.type === "symbol") {
        setPaint(map, id, "text-color", m.label);
        setPaint(map, id, "text-halo-color", m.labelHalo);
      }
    }
  }

  // Capas de datos del proyecto
  const [s0, s1, s2] = theme.severity;
  if (map.getLayer(POINTS_LAYER)) {
    map.setPaintProperty(POINTS_LAYER, "circle-color", ["match", ["get", "severity"], 2, s2, 1, s1, s0]);
    map.setPaintProperty(POINTS_LAYER, "circle-stroke-color", m0(theme));
  }
  if (map.getLayer(HEATMAP_LAYER)) {
    const h = theme.heatmap;
    map.setPaintProperty(HEATMAP_LAYER, "heatmap-color", [
      "interpolate", ["linear"], ["heatmap-density"],
      0, "rgba(0,0,0,0)", 0.15, h[0], 0.35, h[1], 0.55, h[2], 0.75, h[3], 1, h[4],
    ]);
  }
  if (map.getLayer(CLUSTER_LAYER)) {
    const c = theme.cluster;
    map.setPaintProperty(CLUSTER_LAYER, "circle-color",
      ["step", ["get", "point_count"], c[0], 50, c[1], 250, c[2], 1000, c[3]]);
    map.setPaintProperty(CLUSTER_LAYER, "circle-stroke-color", theme.swatch[1]);
  }
}

function m0(theme: ThemeDef) {
  return theme.map.background || "#0f172a";
}
