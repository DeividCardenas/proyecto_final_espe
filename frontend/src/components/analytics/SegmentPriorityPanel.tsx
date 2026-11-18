import { useState } from "react";
import { MousePointerClick } from "lucide-react";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { useShallow } from "zustand/react/shallow";
import { targetYear } from "@/lib/modelLabels";
import { Card, cn, fmtNumber, fmtPct, QueryError } from "@/components/ui";
import { SegmentExplainCard } from "./SegmentExplainCard";

/** Cuadras visibles de entrada y al desplegar la lista. */
const TOP_SHORT = 5;
const TOP_LIST = 10;

/**
 * Pantalla de entrada: una pregunta («¿dónde intervenir primero?») y su respuesta.
 * Arriba el hallazgo principal del modelo; debajo las cuadras a priorizar; al elegir una,
 * su predicción explicada ocupa el lugar del hallazgo.
 */
export function SegmentPriorityPanel() {
  const [expanded, setExpanded] = useState(false);
  const { metrics, segments, limit } = useTopSegments();
  const { focus, selectedSegment, selectSegment } = useUiStore(
    useShallow((s) => ({ focus: s.focus, selectedSegment: s.selectedSegment, selectSegment: s.selectSegment })),
  );
  const showOnMap = useMapStore((s) => s.layers.segments);
  const toggleLayer = useMapStore((s) => s.toggleLayer);

  if (metrics.isError) return <p className="text-xs text-slate-400">Aún no se ha entrenado el modelo por tramo.</p>;
  const m = metrics.data;
  const top = segments.data?.features.slice(0, expanded ? TOP_LIST : TOP_SHORT) ?? [];
  const win = m?.comparison?.[m.winner] ?? null;
  const year = targetYear(m?.windows?.test);

  return (
    <div className="grid grid-cols-2 gap-2" data-testid="segment-panel">
      {selectedSegment ? (
        <SegmentExplainCard segment={selectedSegment} />
      ) : (
        <Card hero tourId="priority-hero" className="col-span-2"
          context={m && win && (
            <>Validación con el año siguiente al entrenamiento: AUC{" "}
              {win.auc_roc_ovr_macro.toLocaleString("es", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}, donde 0,5 es azar.
              Detalle en la sección Modelo.</>
          )}
        >
          {win ? (
            <div data-testid="priority-headline">
              <p className="text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-300">Dónde intervenir primero</p>
              <div className="mt-2 flex items-end gap-3">
                <span className="hud-kpi hud-title priority-big text-[56px] font-bold leading-none tabular-nums">{fmtPct(win.top10_capture_severe, 0)}</span>
                <span className="mb-1 rounded-full border border-slate-700 bg-slate-950/60 px-2.5 py-1 text-[13px] font-semibold tabular-nums text-slate-100">
                  {win.top10_lift.toLocaleString("es", { maximumFractionDigits: 1 })}× el azar
                </span>
              </div>
              <p className="mt-2 text-[15px] font-medium leading-snug text-slate-100">
                de los siniestros graves {year ? `de ${year}` : "del año evaluado"} ocurrió en el <b>10{"\u00a0"}% de las cuadras</b> que señaló el modelo.
              </p>
            </div>
          ) : (
            <p className="text-xs text-slate-400">{metrics.isLoading ? "Cargando…" : "Sin métricas del modelo."}</p>
          )}
          <p className="mt-2 flex items-start gap-2 text-[12px] leading-snug text-slate-400">
            <MousePointerClick size={15} className="mt-0.5 shrink-0 text-cyan-300" />
            <span>
              Haz clic en una cuadra del mapa o de la lista para ver por qué es prioritaria.
              {!showOnMap && (
                <button onClick={() => toggleLayer("segments")} className="ml-1 text-cyan-300 hover:underline">Mostrar cuadras en el mapa</button>
              )}
            </span>
          </p>
        </Card>
      )}

      <Card
        tourId="priority-list"
        title={`Las ${expanded ? TOP_LIST : TOP_SHORT} cuadras prioritarias`}
        className="col-span-2"
        right={
          <button onClick={() => toggleLayer("segments")} className="text-[10px] text-cyan-300 hover:underline">
            {showOnMap ? "ocultar en mapa" : "ver en mapa"}
          </button>
        }
        context={m && `Ordenadas por P(riesgo Alto) en los 12 meses siguientes a ${m.forecast.history_window.split("->")[1]?.trim()} · el mapa muestra el top 10% (${fmtNumber(limit)} de ${fmtNumber(m.forecast.segments_scored)} cuadras)`}
      >
        {segments.isLoading && <p className="text-xs text-slate-400">Cargando…</p>}
        {segments.isError && <QueryError what="las cuadras prioritarias" onRetry={() => void segments.refetch()} />}
        <ol className="space-y-0.5">
          {top.map((f) => {
            const p = f.properties;
            const coords = f.geometry.coordinates as [number, number];
            const active = selectedSegment?.segment_id === p.segment_id;
            return (
              <li key={p.segment_id}>
                <button
                  onClick={() => {
                    if (!showOnMap) toggleLayer("segments");
                    selectSegment({ ...p, coordinates: coords });
                    focus(coords);
                  }}
                  className={cn("flex w-full items-center gap-2 rounded-lg px-1.5 py-1.5 text-left text-[11px] text-slate-300 hover:bg-slate-800",
                    active && "bg-slate-800 text-slate-100")}
                >
                  <span className={cn("grid h-5 w-5 shrink-0 place-items-center rounded-full text-[10px] font-bold tabular-nums",
                    p.priority_pct <= 0.01 ? "priority-rank-hot" : "bg-slate-800 text-slate-300")}>{p.priority_rank}</span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate" title={p.segment_id}>{p.segment_id}</span>
                    <span className="mt-0.5 block h-1 overflow-hidden rounded-full bg-slate-800">
                      <span className="priority-bar block h-full rounded-full" style={{ width: `${Math.round(p.p_alto * 100)}%` }} />
                    </span>
                  </span>
                  <span className="shrink-0 tabular-nums text-slate-400">{fmtNumber(p.crashes)} sin.</span>
                  <span className="w-10 shrink-0 text-right text-[13px] font-semibold tabular-nums text-slate-100">{fmtPct(p.p_alto, 0)}</span>
                </button>
              </li>
            );
          })}
        </ol>
        {(segments.data?.features.length ?? 0) > TOP_SHORT && (
          <button onClick={() => setExpanded((v) => !v)} className="mt-1 text-[10px] text-cyan-300 hover:underline">
            {expanded ? `ver sólo las ${TOP_SHORT} primeras` : `ver las ${TOP_LIST} primeras`}
          </button>
        )}
      </Card>
    </div>
  );
}
