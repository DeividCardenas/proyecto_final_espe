import type { ExpressionSpecification, GeoJSONSource, Map as MLMap } from "maplibre-gl";
import type { FeatureCollection, Point } from "geojson";
import type { SegmentProps } from "@/types/api";
import type { ThemeDef } from "@/theme/themes";

export const SEGMENT_SOURCE = "segments";
export const SEGMENT_LAYER = "segment-circles";
/** Halo difuso bajo el top 1 %: hace que lo crítico «brille» sobre el mapa oscuro */
export const SEGMENT_GLOW_LAYER = "segment-glow";
/** Anillo animado sobre las 10 primeras cuadras */
export const SEGMENT_PULSE_LAYER = "segment-pulse";
export const SEGMENT_LAYERS = [SEGMENT_GLOW_LAYER, SEGMENT_PULSE_LAYER, SEGMENT_LAYER];

/** Cortes de prioridad (fracción de cuadras de la ciudad, ordenadas por P(Alto)). */
export const PRIORITY_BREAKS = [0.01, 0.03, 0.1] as const;
const TOP_PULSE = 10;

/**
 * Colores por prioridad, no por P(Alto) absoluta: dentro del top 10 % las probabilidades
 * van de ~0,4 a ~0,6 y una rampa absoluta las pintaba casi todas iguales (grises).
 * Rojo del tema = top 1 %, ámbar = top 3 %, acento = resto del top 10 %.
 */
export function segmentColors(theme: ThemeDef): [string, string, string] {
  if (theme.id === "classic") return ["#ef4444", "#f59e0b", "#22d3ee"];
  const amber = theme.id === "tron" ? "#ffc27a" : theme.severity[1];
  // Si el acento del tema coincide con el ámbar (Night City, NERV), el resto usa el color «bajo»
  const rest = theme.swatch[1].toLowerCase() === amber.toLowerCase() ? theme.severity[0] : theme.swatch[1];
  return [theme.severity[2], amber, rest];
}

const colorExpr = ([top1, top3, top10]: [string, string, string]): ExpressionSpecification =>
  ["step", ["get", "priority_pct"], top1, PRIORITY_BREAKS[0], top3, PRIORITY_BREAKS[1], top10];

const tier = (a: number, b: number, c: number): ExpressionSpecification =>
  ["case", ["<=", ["get", "priority_pct"], PRIORITY_BREAKS[0]], a, ["<=", ["get", "priority_pct"], PRIORITY_BREAKS[1]], b, c];

export function addSegmentLayer(map: MLMap) {
  if (map.getSource(SEGMENT_SOURCE)) return;
  const colors: [string, string, string] = ["#ef4444", "#f59e0b", "#22d3ee"];
  map.addSource(SEGMENT_SOURCE, { type: "geojson", data: { type: "FeatureCollection", features: [] } });
  map.addLayer({
    id: SEGMENT_GLOW_LAYER,
    type: "circle",
    source: SEGMENT_SOURCE,
    filter: ["<=", ["get", "priority_pct"], PRIORITY_BREAKS[1]],
    layout: { visibility: "none" },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, tier(13, 7, 0), 15, tier(34, 18, 0)],
      "circle-color": colorExpr(colors),
      "circle-blur": 1,
      "circle-opacity": tier(0.5, 0.22, 0),
    },
  });
  map.addLayer({
    id: SEGMENT_PULSE_LAYER,
    type: "circle",
    source: SEGMENT_SOURCE,
    filter: ["<=", ["get", "priority_rank"], TOP_PULSE],
    layout: { visibility: "none" },
    paint: {
      "circle-radius": 8,
      "circle-color": "rgba(0,0,0,0)",
      "circle-stroke-color": colors[0],
      "circle-stroke-width": 2,
      "circle-stroke-opacity": 0.8,
    },
  });
  map.addLayer({
    id: SEGMENT_LAYER,
    type: "circle",
    source: SEGMENT_SOURCE,
    layout: { visibility: "none", "circle-sort-key": ["-", 0, ["get", "priority_pct"]] },
    paint: {
      "circle-radius": ["interpolate", ["linear"], ["zoom"], 10, tier(4.2, 3, 2.1), 15, tier(11, 8, 6)],
      "circle-color": colorExpr(colors),
      "circle-stroke-color": "#020617",
      "circle-stroke-width": tier(1.2, 1, 0.6),
      "circle-opacity": tier(1, 0.95, 0.8),
    },
  });
}

/** Recolorea las cuadras con la paleta del tema. */
export function applySegmentTheme(map: MLMap, theme: ThemeDef) {
  if (!map.getLayer(SEGMENT_LAYER)) return;
  const colors = segmentColors(theme);
  map.setPaintProperty(SEGMENT_LAYER, "circle-color", colorExpr(colors));
  map.setPaintProperty(SEGMENT_LAYER, "circle-stroke-color", theme.map.background || "#020617");
  map.setPaintProperty(SEGMENT_GLOW_LAYER, "circle-color", colorExpr(colors));
  map.setPaintProperty(SEGMENT_PULSE_LAYER, "circle-stroke-color", colors[0]);
}

/**
 * Anima el anillo de las 10 primeras cuadras (radio y opacidad). Devuelve la función que
 * lo detiene. Respeta «reducir movimiento»: en ese caso queda un anillo fijo.
 */
export function startSegmentPulse(map: MLMap): () => void {
  if (typeof window === "undefined" || window.matchMedia?.("(prefers-reduced-motion: reduce)").matches) return () => {};
  let raf = 0;
  let last = 0;
  const t0 = performance.now();
  const tick = (now: number) => {
    raf = requestAnimationFrame(tick);
    if (now - last < 33) return; // ~30 fps: suficiente para un pulso y barato para la GPU
    last = now;
    if (!map.getLayer(SEGMENT_PULSE_LAYER) || map.getLayoutProperty(SEGMENT_PULSE_LAYER, "visibility") === "none") return;
    const k = ((now - t0) % 2000) / 2000;
    const z = map.getZoom();
    const base = z < 12 ? 6 : 10;
    map.setPaintProperty(SEGMENT_PULSE_LAYER, "circle-radius", base + k * (z < 12 ? 22 : 34));
    map.setPaintProperty(SEGMENT_PULSE_LAYER, "circle-stroke-opacity", 0.9 * (1 - k));
  };
  raf = requestAnimationFrame(tick);
  return () => cancelAnimationFrame(raf);
}

export function setSegmentData(map: MLMap, data: FeatureCollection<Point, SegmentProps>) {
  (map.getSource(SEGMENT_SOURCE) as GeoJSONSource | undefined)?.setData(data);
}
