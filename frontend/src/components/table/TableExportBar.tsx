import { Download } from "lucide-react";
import type { CrashFeature } from "@/types/api";
import { absoluteApiUrl } from "@/services/api";
import { toParams, type QueryFilters } from "@/services/crashService";

/** Descarga un archivo generado en el navegador. */
export function download(name: string, content: string, type: string) {
  const url = URL.createObjectURL(new Blob([content], { type }));
  const a = document.createElement("a");
  a.href = url;
  a.download = name;
  a.rel = "noopener";
  document.body.appendChild(a);
  a.click();
  a.remove();
  // Firefox y Safari cancelan la descarga si el blob se revoca en el mismo tick del clic
  setTimeout(() => URL.revokeObjectURL(url), 30_000);
}

/** BOM UTF-8: sin él, Excel en español abre el CSV como ANSI y rompe tildes y eñes. */
export const CSV_BOM = "﻿";

/**
 * Celda CSV segura: comillas cuando hace falta (coma, comilla, salto de línea) y un
 * apóstrofo delante de =, +, -, @ o tabulador para que Excel no la interprete como
 * fórmula (inyección CSV con texto de datos abiertos). Los números se dejan tal cual.
 */
export function csvCell(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "number" || typeof v === "boolean") return String(v);
  let s = String(v);
  if (/^[=+\-@\t\r]/.test(s)) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function toCsv(rows: CrashFeature[]): string {
  const cols = ["id", "date", "severity", "injuries", "fatal", "weather", "lighting", "speed", "cause", "street", "crash_type", "workzone", "aadt"] as const;
  const lines = rows.map((r) => [...cols.map((c) => csvCell(r.properties[c])), r.geometry.coordinates[0], r.geometry.coordinates[1]].join(","));
  return CSV_BOM + [[...cols, "lon", "lat"].join(","), ...lines].join("\r\n");
}

export function TableExportBar({ rows, filters }: { rows: CrashFeature[]; filters: QueryFilters }) {
  const btn = "flex items-center gap-1 rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800 disabled:opacity-40";
  const empty = rows.length === 0;
  const ndjson = () => {
    const qs = new URLSearchParams();
    for (const [k, v] of Object.entries(toParams(filters))) {
      for (const item of Array.isArray(v) ? v : [v]) qs.append(k, String(item));
    }
    window.open(absoluteApiUrl(`/crashes/stream?${qs.toString()}`), "_blank", "noopener");
  };
  return (
    <div className="flex items-center gap-2">
      <button className={btn} disabled={empty} title="Filas de la tabla, listas para Excel"
        onClick={() => download("siniestros_chicago.csv", toCsv(rows), "text/csv;charset=utf-8")}><Download size={12} />CSV</button>
      <button className={btn} disabled={empty} title="Filas de la tabla con su geometría"
        onClick={() => download("siniestros_chicago.geojson", JSON.stringify({ type: "FeatureCollection", features: rows }), "application/geo+json")}>
        <Download size={12} />GeoJSON
      </button>
      <button className={btn} onClick={ndjson} title="Todos los siniestros de la zona y los filtros, sin el límite de la tabla (streaming desde el servidor)">
        <Download size={12} />NDJSON completo
      </button>
    </div>
  );
}
