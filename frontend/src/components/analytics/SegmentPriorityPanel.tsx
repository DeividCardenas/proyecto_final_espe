import { MousePointerClick } from "lucide-react";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { Card, cn, fmtNumber, fmtPct } from "@/components/ui";
import { SegmentExplainCard } from "./SegmentExplainCard";

const TOP_LIST = 10;

/** Modelo por tramo vial: predicción explicada de la cuadra elegida y lista de cuadras a priorizar. */
export function SegmentPriorityPanel() {
  const { metrics, segments, limit } = useTopSegments();
  const { focus, selectedSegment, selectSegment } = useUiStore();
  const layers = useMapStore((s) => s.layers);
  const toggleLayer = useMapStore((s) => s.toggleLayer);

  if (metrics.isError) return <p className="text-xs text-slate-400">Aún no se ha entrenado el modelo por tramo.</p>;
  const m = metrics.data;
  const top = segments.data?.features.slice(0, TOP_LIST) ?? [];
  const win = m ? m.comparison[m.winner] : null;

  return (
    <div className="grid grid-cols-2 gap-2" data-testid="segment-panel">
      {selectedSegment ? (
        <SegmentExplainCard segment={selectedSegment} />
      ) : (
        <Card className="col-span-2 border-dashed">
          <p className="flex items-start gap-2 text-[12px] leading-snug text-slate-300">
            <MousePointerClick size={16} className="mt-0.5 shrink-0 text-cyan-300" />
            <span>
              Haz clic en una cuadra del mapa (o en la lista) para ver su probabilidad de riesgo Alto, cómo se compara
              con el resto de la ciudad y qué variables la explican.
              {!layers.segments && (
                <button onClick={() => toggleLayer("segments")} className="ml-1 text-cyan-300 hover:underline">Mostrar cuadras en el mapa</button>
              )}
            </span>
          </p>
        </Card>
      )}

      {m && win && (
        <>
          <div className="hud-panel rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-slate-500">Top 10% de cuadras capta</p>
            <p className="hud-kpi text-xl font-semibold tabular-nums text-slate-100">{fmtPct(win.top10_capture_severe, 0)}</p>
            <p className="text-[10px] leading-snug text-slate-400">de los siniestros graves de 2025 ({win.top10_lift.toLocaleString("es", { maximumFractionDigits: 1 })}× el 10% esperado al azar)</p>
          </div>
          <div className="hud-panel rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2">
            <p className="text-[10px] uppercase tracking-wide text-slate-500">AUC año siguiente</p>
            <p className="hud-kpi text-xl font-semibold tabular-nums text-slate-100">{win.auc_roc_ovr_macro.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}</p>
            <p className="text-[10px] leading-snug text-slate-400">0,5 = azar · CV espacial {win.spatial_cv_auc.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 })} (bloques de ~2 km)</p>
          </div>
        </>
      )}

      <Card
        title={`Las ${TOP_LIST} cuadras prioritarias`}
        className="col-span-2"
        right={
          <button onClick={() => toggleLayer("segments")} className="text-[10px] text-cyan-300 hover:underline">
            {layers.segments ? "ocultar en mapa" : "ver en mapa"}
          </button>
        }
        context={m && `Ordenadas por P(riesgo Alto) en los 12 meses siguientes a ${m.forecast.history_window.split("->")[1]?.trim()} · el mapa muestra el top 10% (${fmtNumber(limit)} de ${fmtNumber(m.forecast.segments_scored)} cuadras)`}
      >
        {segments.isLoading && <p className="text-xs text-slate-500">Cargando…</p>}
        <ol className="space-y-0.5">
          {top.map((f) => {
            const p = f.properties;
            const coords = f.geometry.coordinates as [number, number];
            const active = selectedSegment?.segment_id === p.segment_id;
            return (
              <li key={p.segment_id}>
                <button
                  onClick={() => {
                    if (!layers.segments) toggleLayer("segments");
                    selectSegment({ ...p, coordinates: coords });
                    focus(coords);
                  }}
                  className={cn("flex w-full items-center gap-2 rounded px-1.5 py-1 text-left text-[11px] text-slate-300 hover:bg-slate-800",
                    active && "bg-slate-800 text-slate-100")}
                >
                  <span className="w-5 shrink-0 tabular-nums text-slate-500">{p.priority_rank}</span>
                  <span className="min-w-0 flex-1 truncate" title={p.segment_id}>{p.segment_id}</span>
                  <span className="shrink-0 tabular-nums text-slate-500">{fmtNumber(p.crashes)} sin.</span>
                  <span className="w-10 shrink-0 text-right font-semibold tabular-nums text-slate-100">{fmtPct(p.p_alto, 0)}</span>
                </button>
              </li>
            );
          })}
        </ol>
      </Card>
    </div>
  );
}
