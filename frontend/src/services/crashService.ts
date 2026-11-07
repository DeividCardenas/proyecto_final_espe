import type { FeatureCollection, Point, Polygon } from "geojson";
import { api, absoluteApiUrl } from "./api";
import type { Bounds } from "@/stores/useMapStore";
import type {
  AadtRow, CauseRow, CrashCollection, CrashDetail, HotspotProps, HourlyRow, Kpis, ModelMetrics, MonthlyRow,
  PermitProps, RiskGrid, SegmentExplanation, SegmentModelMetrics, SegmentProps, Severity, WeatherRow,
} from "@/types/api";

export interface QueryFilters {
  bounds?: Bounds | null;
  startDate?: string | null;
  endDate?: string | null;
  hourRange?: [number, number];
  severities?: Severity[];
  workzoneOnly?: boolean;
}

/** Decimales de los límites del mapa (~1 m): misma precisión en la clave de caché y en la petición. */
export const BOUNDS_DECIMALS = 5;

export const roundBounds = (b: Bounds): Bounds =>
  b.map((v) => Number(v.toFixed(BOUNDS_DECIMALS))) as Bounds;

export function toParams(f: QueryFilters): Record<string, unknown> {
  const p: Record<string, unknown> = {};
  if (f.bounds) {
    [p.min_lon, p.min_lat, p.max_lon, p.max_lat] = roundBounds(f.bounds);
  }
  if (f.startDate) p.start_date = f.startDate;
  if (f.endDate) p.end_date = f.endDate;
  if (f.hourRange && (f.hourRange[0] > 0 || f.hourRange[1] < 23)) {
    p.hour_from = f.hourRange[0];
    p.hour_to = f.hourRange[1];
  }
  if (f.severities && f.severities.length < 3) p.severity = f.severities;
  if (f.workzoneOnly) p.workzone_only = true;
  return p;
}

/**
 * Cada función acepta el AbortSignal de React Query: al mover el mapa, las consultas de
 * la ventana anterior se cancelan en vez de seguir ocupando el backend.
 */
type Sig = AbortSignal | undefined;
const get = <T>(url: string, params?: Record<string, unknown>, signal?: Sig) =>
  api.get<T>(url, { params, signal }).then((r) => r.data);

export const crashService = {
  geojson: (f: QueryFilters, limit = 10_000, signal?: Sig) =>
    get<CrashCollection>("/crashes/geojson", { ...toParams(f), limit }, signal),
  detail: (id: string, signal?: Sig) => get<CrashDetail>(`/crashes/${encodeURIComponent(id)}`, undefined, signal),
  hotspots: (f: QueryFilters, signal?: Sig) =>
    get<FeatureCollection<Point, HotspotProps>>("/crashes/clusters", toParams(f), signal),
  permits: (bounds: Bounds | null, date?: string | null, signal?: Sig) =>
    get<FeatureCollection<Polygon, PermitProps>>("/permits/active", { ...toParams({ bounds }), ...(date ? { date } : {}) }, signal),
  aadt: (signal?: Sig) => get<FeatureCollection<Point, { volume: number; street: string }>>("/traffic/stations", undefined, signal),
  riskGrid: (signal?: Sig) => get<RiskGrid>("/risk/grid", undefined, signal),
  segments: (limit = 5000, signal?: Sig) =>
    get<FeatureCollection<Point, SegmentProps>>("/risk/segments", { limit }, signal),
  segmentExplain: (segmentId: string, signal?: Sig) =>
    get<SegmentExplanation>("/risk/segment-explain", { segment_id: segmentId }, signal),
  segmentDistribution: (signal?: Sig) =>
    get<{ segments_total: number; step: number; p_alto: number[] }>("/risk/segment-distribution", undefined, signal),
  segmentMetrics: (signal?: Sig) => get<SegmentModelMetrics>("/risk/segment-model-metrics", undefined, signal),
  modelMetrics: (signal?: Sig) => get<ModelMetrics>("/risk/model-metrics", undefined, signal),
  kpis: (f: QueryFilters, signal?: Sig) => get<Kpis>("/analytics/kpis", toParams(f), signal),
  hourly: (f: QueryFilters, signal?: Sig) => get<HourlyRow[]>("/analytics/hourly-distribution", toParams(f), signal),
  weather: (f: QueryFilters, signal?: Sig) => get<WeatherRow[]>("/analytics/weather-impact", toParams(f), signal),
  monthly: (f: QueryFilters, signal?: Sig) => get<MonthlyRow[]>("/analytics/monthly-trend", toParams(f), signal),
  // Límite máximo de la API (cubre todas las causas): el total sin causa determinada debe ser completo
  causes: (f: QueryFilters, signal?: Sig) => get<CauseRow[]>("/analytics/top-causes", { ...toParams(f), limit: 40 }, signal),
  aadtSeverity: (f: QueryFilters, signal?: Sig) => get<AadtRow[]>("/analytics/aadt-severity", toParams(f), signal),
  /** Plantilla de teselas MVT: fechas y «sólo zona de obra» se filtran en el servidor (todos los zooms). */
  tileUrl: (startDate: string | null, endDate: string | null, workzoneOnly = false) => {
    const qs = new URLSearchParams();
    if (startDate) qs.set("start_date", startDate);
    if (endDate) qs.set("end_date", endDate);
    if (workzoneOnly) qs.set("workzone_only", "true");
    const q = qs.toString();
    return absoluteApiUrl(`/tiles/crashes/{z}/{x}/{y}.pbf${q ? `?${q}` : ""}`);
  },
};
