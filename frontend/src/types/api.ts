import type { Feature, FeatureCollection, Point, Polygon } from "geojson";

export type Severity = 0 | 1 | 2;

export interface CrashProperties {
  id: string;
  date: string;
  hour: number;
  dow: number;
  severity: Severity;
  injuries: number;
  fatal: number;
  weather: string | null;
  lighting: string | null;
  speed: number | null;
  cause: string | null;
  street: string;
  crash_type: string | null;
  workzone: boolean;
  aadt: number | null;
}

export type CrashFeature = Feature<Point, CrashProperties>;
export type CrashCollection = FeatureCollection<Point, CrashProperties>;

export interface CrashDetail extends CrashProperties {
  lon: number;
  lat: number;
  damage: string | null;
  surface: string | null;
  trafficway: string | null;
  permit: string | null;
  aadt_distance_m: number | null;
  vehicles: { unit_type: string | null; vehicle_type: string | null; maneuver: string | null; vehicle_year: number | null }[];
  people: { person_type: string | null; sex: string | null; age: number | null; injury_classification: string | null; safety_equipment: string | null }[];
}

export interface Kpis {
  total_crashes: number;
  total_injuries: number | null;
  fatalities: number | null;
  incapacitating: number | null;
  critical_crashes: number | null;
  critical_rate: number | null;
  workzone_crashes: number | null;
  first_date: string | null;
  last_date: string | null;
  yoy_change: number | null;
  high_risk_cells: number;
}

export interface HourlyRow { hour: number; crashes: number; critical: number }
export interface WeatherRow { weather: string; crashes: number; critical_rate: number }
export interface MonthlyRow { month: string; crashes: number; critical: number; fatalities: number }
export interface AadtRow { decile: number; mean_aadt: number; crashes: number; critical_rate: number; mean_severity: number }
export interface CauseRow { cause: string; crashes: number; critical_rate: number }

export interface RiskCellProps {
  risk: number;
  risk_level: Severity;
  crashes: number;
  observed_critical_rate: number;
  fatalities: number;
  mean_aadt: number | null;
}
export type RiskGrid = FeatureCollection<Polygon, RiskCellProps> & { source: string; breaks: Record<string, number> };

export interface PermitProps {
  permit: string;
  work_type: string | null;
  description: string | null;
  closure: string | null;
  street: string;
  start: string;
  end: string;
}

export interface HotspotProps { cluster_id: number; count: number; critical: number; fatalities: number }

export type WeatherInput = "CLEAR" | "RAIN" | "SNOW" | "FOG" | "OTHER";
export type LightingInput = "DAY" | "DARK_LIGHTED" | "DARK" | "DUSK_DAWN";

export interface SegmentRiskRequest {
  coordinates: [number, number];
  posted_speed_limit: number;
  weather_condition: WeatherInput;
  lighting_condition: LightingInput;
  active_workzone: boolean;
  first_crash_type?: string | null;
  when?: string | null;
}

export interface SegmentRiskResponse {
  risk_level: "Bajo" | "Moderado" | "Crítico";
  risk_class: Severity;
  probabilities: Record<string, number>;
  critical_score: number;
  critical_alert: boolean;
  top_factors: { feature: string; contribution: number; direction: "aumenta" | "reduce" }[];
  context: Record<string, unknown>;
  model: { mode: string; algorithm: string | null; trained_at: string | null };
  inference_ms: number;
}

export interface ModelMetrics {
  winner: string;
  trained_at: string;
  n_rows: number;
  class_distribution: Record<string, number>;
  gates: Record<string, boolean>;
  thresholds_required: Record<string, number>;
  test: Record<string, number>;
  test_f1_threshold: Record<string, number>;
  cv: { auc_mean: number; auc_std: number; auc_cv_variation: number };
  confusion_matrix: number[][];
  feature_importance: { feature: string; importance: number }[];
  comparison: Record<string, Record<string, number>>;
  artifact: { size_mb: number; load_ms: number; single_inference_ms: number };
}
