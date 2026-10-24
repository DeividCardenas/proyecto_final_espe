import { useMapStore } from "@/stores/useMapStore";
import { useTheme } from "@/stores/useThemeStore";
import { RISK_COLORS } from "./layers/RiskChoroplethLayer";

export function MapLegend() {
  const theme = useTheme();
  const SEVERITY_COLORS = theme.severity;
  const layers = useMapStore((s) => s.layers);
  const zoom = useMapStore((s) => s.zoom);
  return (
    <div className="hud-panel absolute bottom-6 left-3 w-56 space-y-2 rounded-xl border border-slate-800 bg-slate-900/90 p-3 text-[11px] text-slate-300 backdrop-blur">
      {layers.heatmap && (
        <div>
          <p className="mb-1 font-semibold text-slate-200">Densidad ponderada por severidad</p>
          <div className="h-2 rounded" style={{ background: `linear-gradient(to right, ${theme.heatmap.join(", ")})` }} />
          <div className="flex justify-between text-slate-500"><span>baja</span><span>alta</span></div>
        </div>
      )}
      {layers.points && (
        <div>
          <p className="mb-1 font-semibold text-slate-200">Siniestros {zoom < 13 && <span className="text-slate-500">(zoom ≥ 13)</span>}</p>
          {(["Bajo", "Moderado", "Crítico"] as const).map((l, i) => (
            <span key={l} className="mr-2 inline-flex items-center gap-1">
              <i className="inline-block h-2.5 w-2.5 rounded-full" style={{ background: SEVERITY_COLORS[i] }} />{l}
            </span>
          ))}
        </div>
      )}
      {layers.risk && (
        <div>
          <p className="mb-1 font-semibold text-slate-200">Riesgo crítico predicho (celda 500 m)</p>
          <div className="h-2 rounded" style={{ background: `linear-gradient(to right, ${RISK_COLORS.low}, #84cc16, ${RISK_COLORS.mid}, ${RISK_COLORS.high})` }} />
          <div className="flex justify-between text-slate-500"><span>bajo</span><span>p80</span><span>p95+</span></div>
        </div>
      )}
      {layers.segments && (
        <div>
          <p className="mb-1 font-semibold text-slate-200">Tramo: P(riesgo Alto) próximos 12 meses</p>
          <div className="h-2 rounded bg-gradient-to-r from-green-600 via-yellow-400 to-red-700" />
          <p className="text-slate-500">Círculos grandes = top 1% y top 10% prioritarios</p>
        </div>
      )}
      {layers.permits && <p><span className="mr-1 inline-block h-2.5 w-4 border border-dashed border-orange-400 bg-orange-500/30 align-middle" />Obra CDOT con cierre + buffer 250 m</p>}
      {layers.hotspots && <p><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-red-500/70 align-middle" />Punto caliente DBSCAN (40 m)</p>}
      {layers.aadt && <p><span className="mr-1 inline-block h-2.5 w-2.5 rounded-full bg-cyan-400/60 align-middle" />Aforo vehicular AADT (2006)</p>}
    </div>
  );
}
