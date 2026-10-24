import type { FeatureCollection, Point, Polygon } from "geojson";
import { api, absoluteApiUrl } from "./api";
import type { Bounds } from "@/stores/useMapStore";
import type {
  AadtRow, CauseRow, CrashCollection, CrashDetail, HotspotProps, HourlyRow, Kpis, ModelMetrics, MonthlyRow,
  PermitProps, RiskGrid, Severity, WeatherRow,
} from "@/types/api";

export interface QueryFilters {
  bounds?: Bounds | null;
  startDate?: string | null;
  endDate?: string | null;
  hourRange?: [number, number];
  severities?: Severity[];
  workzoneOnly?: boolean;
}

export function toParams(f: QueryFilters): Record<string, unknown> {
  const p: Record<string, unknown> = {};
  if (f.bounds) {
    [p.min_lon, p.min_lat, p.max_lon, p.max_lat] = f.bounds.map((v) => Number(v.toFixed(5)));
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

export const crashService = {
  geojson: (f: QueryFilters, limit = 10_000) =>
    api.get<CrashCollection>("/crashes/geojson", { params: { ...toParams(f), limit } }).then((r) => r.data),
  detail: (id: string) => api.get<CrashDetail>(`/crashes/${encodeURIComponent(id)}`).then((r) => r.data),
  hotspots: (f: QueryFilters) =>
    api.get<FeatureCollection<Point, HotspotProps>>("/crashes/clusters", { params: toParams(f) }).then((r) => r.data),
  permits: (bounds: Bounds | null, date?: string | null) =>
    api
      .get<FeatureCollection<Polygon, PermitProps>>("/permits/active", {
        params: { ...toParams({ bounds }), ...(date ? { date } : {}) },
      })
      .then((r) => r.data),
  aadt: () => api.get<FeatureCollection<Point, { volume: number; street: string }>>("/traffic/stations").then((r) => r.data),
  riskGrid: () => api.get<RiskGrid>("/risk/grid").then((r) => r.data),
  modelMetrics: () => api.get<ModelMetrics>("/risk/model-metrics").then((r) => r.data),
  kpis: (f: QueryFilters) => api.get<Kpis>("/analytics/kpis", { params: toParams(f) }).then((r) => r.data),
  hourly: (f: QueryFilters) =>
    api.get<HourlyRow[]>("/analytics/hourly-distribution", { params: toParams(f) }).then((r) => r.data),
  weather: (f: QueryFilters) =>
    api.get<WeatherRow[]>("/analytics/weather-impact", { params: toParams(f) }).then((r) => r.data),
  monthly: (f: QueryFilters) =>
    api.get<MonthlyRow[]>("/analytics/monthly-trend", { params: toParams(f) }).then((r) => r.data),
  causes: (f: QueryFilters) =>
    api.get<CauseRow[]>("/analytics/top-causes", { params: { ...toParams(f), limit: 8 } }).then((r) => r.data),
  aadtSeverity: (f: QueryFilters) =>
    api.get<AadtRow[]>("/analytics/aadt-severity", { params: toParams(f) }).then((r) => r.data),
  tileUrl: (startDate: string | null, endDate: string | null) => {
    const qs = new URLSearchParams();
    if (startDate) qs.set("start_date", startDate);
    if (endDate) qs.set("end_date", endDate);
    const q = qs.toString();
    return absoluteApiUrl(`/tiles/crashes/{z}/{x}/{y}.pbf${q ? `?${q}` : ""}`);
  },
};
