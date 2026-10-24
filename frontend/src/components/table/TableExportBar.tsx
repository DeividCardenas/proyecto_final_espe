import { Download } from "lucide-react";
import type { CrashFeature } from "@/types/api";
import { absoluteApiUrl } from "@/services/api";
import { toParams, type QueryFilters } from "@/services/crashService";

function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.click();
  URL.revokeObjectURL(url);
}

export function toCsv(rows: CrashFeature[]): string {
  const cols = ["id", "date", "severity", "injuries", "fatal", "weather", "lighting", "speed", "cause", "street", "crash_type", "workzone", "aadt"] as const;
  const esc = (v: unknown) => {
    const s = v === null || v === undefined ? "" : String(v);
    return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = rows.map((r) => [...cols.map((c) => esc(r.properties[c])), r.geometry.coordinates[0], r.geometry.coordinates[1]].join(","));
  return [[...cols, "lon", "lat"].join(","), ...lines].join("\n");
}

export function TableExportBar({ rows, filters }: { rows: CrashFeature[]; filters: QueryFilters }) {
  const btn = "flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800";
  const ndjson = () => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(toParams(filters))) {
      for (const item of Array.isArray(v) ? v : [v]) qs.append(k, String(item));
    }
    window.open(absoluteApiUrl(`/crashes/stream?${qs.toString()}`), "_blank");
  };
  return (
    <div className="flex items-center gap-2">
      <button className={btn} onClick={() => download("siniestros_chicago.csv", toCsv(rows), "text/csv")}><Download size={12} />CSV</button>
      <button className={btn} onClick={() => download("siniestros_chicago.geojson", JSON.stringify({ type: "FeatureCollection", features: rows }), "application/geo+json")}>
        <Download size={12} />GeoJSON
      </button>
      <button className={btn} onClick={ndjson} title="Exportación masiva desde el servidor (streaming)"><Download size={12} />NDJSON completo</button>
    </div>
  );
}
