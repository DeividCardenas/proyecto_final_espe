import { useQuery } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { Card, cn, fmtNumber, fmtPct } from "@/components/ui";

const MODEL_LABELS: Record<string, string> = {
  logistic_regression: "Regresión logística (base)",
  random_forest: "Random Forest",
  xgboost: "XGBoost",
};

/** Modelo por tramo vial: comparación de algoritmos y lista de cuadras a priorizar. */
export function SegmentPriorityPanel() {
  const metrics = useQuery({ queryKey: ["segment-metrics"], queryFn: crashService.segmentMetrics, staleTime: Infinity });
  const segments = useQuery({ queryKey: ["segments"], queryFn: () => crashService.segments(), staleTime: Infinity });
  const focus = useUiStore((s) => s.focus);
  const layers = useMapStore((s) => s.layers);
  const toggleLayer = useMapStore((s) => s.toggleLayer);

  if (metrics.isError) return <p className="text-xs text-slate-400">Aún no se ha entrenado el modelo por tramo.</p>;
  const m = metrics.data;
  const top = segments.data?.features.slice(0, 25) ?? [];
  const win = m ? m.comparison[m.winner] : null;

  return (
    <div className="space-y-3" data-testid="segment-panel">
      {m && win && (
        <Card title="Riesgo anticipado por tramo (cuadra)">
          <p className="text-[11px] leading-snug text-slate-400">
            Con la historia de 12 meses de cada cuadra se anticipa su riesgo de los 12 meses siguientes.
            Validado fuera de tiempo ({m.windows.test}) y con bloques espaciales de ~2 km.
          </p>
          <div className="mt-2 grid grid-cols-3 gap-2 text-center">
            {[
              ["AUC año siguiente", win.auc_roc_ovr_macro.toFixed(3)],
              ["Recall tramo Alto", win.recall_high.toFixed(2)],
              ["Top 10% capta", fmtPct(win.top10_capture_severe, 0)],
            ].map(([k, v]) => (
              <div key={k} className="rounded bg-slate-800/80 py-1.5">
                <p className="text-[10px] text-slate-500">{k}</p>
                <p className="text-base font-semibold tabular-nums text-slate-100">{v}</p>
              </div>
            ))}
          </div>
          <p className="mt-2 text-[10px] leading-snug text-slate-500">
            Interviniendo el 10% de cuadras priorizadas se cubre el {fmtPct(win.top10_capture_severe, 0)} de los
            siniestros graves del año siguiente ({win.top10_lift.toFixed(1)}× lo esperado al azar).
          </p>
        </Card>
      )}

      {m && (
        <Card title="Comparativa de algoritmos (test 2025)">
          <table className="w-full text-[11px] tabular-nums">
            <thead>
              <tr className="text-slate-500">
                <th className="text-left">modelo</th><th>AUC</th><th>CV esp.</th><th>Recall</th><th>Top10%</th>
              </tr>
            </thead>
            <tbody>
              {Object.entries(m.comparison).map(([k, v]) => (
                <tr key={k} className={cn("text-center text-slate-300", k === m.winner && "text-cyan-200")}>
                  <td className="text-left">{MODEL_LABELS[k] ?? k}{k === m.winner && " ★"}</td>
                  <td>{v.auc_roc_ovr_macro.toFixed(3)}</td>
                  <td>{v.spatial_cv_auc.toFixed(3)}</td>
                  <td>{v.recall_high.toFixed(2)}</td>
                  <td>{fmtPct(v.top10_capture_severe, 0)}</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="mt-1 text-[10px] text-slate-500">★ elegido por captura de siniestros graves en el top 10%.</p>
        </Card>
      )}

      <Card
        title="Cuadras prioritarias"
        right={
          <button onClick={() => toggleLayer("segments")} className="text-[10px] text-cyan-300 hover:underline">
            {layers.segments ? "ocultar en mapa" : "ver en mapa"}
          </button>
        }
      >
        {segments.isLoading && <p className="text-xs text-slate-500">Cargando…</p>}
        <ol className="space-y-1">
          {top.map((f) => {
            const p = f.properties;
            return (
              <li key={p.segment_id}>
                <button
                  onClick={() => {
                    if (!layers.segments) toggleLayer("segments");
                    focus(f.geometry.coordinates as [number, number]);
                  }}
                  className="flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[11px] text-slate-300 hover:bg-slate-800"
                >
                  <span className="w-6 shrink-0 tabular-nums text-slate-500">{p.priority_rank}</span>
                  <span className="min-w-0 flex-1 truncate" title={p.segment_id}>{p.segment_id}</span>
                  <span className="shrink-0 tabular-nums text-slate-500">{fmtNumber(p.crashes)} sin.</span>
                  <span className="w-11 shrink-0 text-right font-semibold tabular-nums text-red-300">{fmtPct(p.p_alto, 0)}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}
