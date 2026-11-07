import { useState } from "react";
import { MousePointerClick } from "lucide-react";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { Card, cn, fmtNumber, fmtPct } from "@/components/ui";
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
  const { focus, selectedSegment, selectSegment } = useUiStore();
  const layers = useMapStore((s) => s.layers);
  const toggleLayer = useMapStore((s) => s.toggleLayer);

  if (metrics.isError) return <p className="text-xs text-slate-400">Aún no se ha entrenado el modelo por tramo.</p>;
  const m = metrics.data;
  const top = segments.data?.features.slice(0, expanded ? TOP_LIST : TOP_SHORT) ?? [];
  const win = m ? m.comparison[m.winner] : null;

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
            <p className="text-[15px] font-medium leading-snug text-slate-100">
              El <b>10% de las cuadras</b> que señaló el modelo concentró el{" "}
              <span className="hud-kpi text-2xl font-semibold tabular-nums text-red-300">{fmtPct(win.top10_capture_severe, 0)}</span>{" "}
              de los siniestros graves de 2025: {win.top10_lift.toLocaleString("es", { maximumFractionDigits: 1 })} veces lo esperado
              si se eligieran al azar. Ahí conviene intervenir primero.
            </p>
          ) : (
            <p className="text-xs text-slate-500">{metrics.isLoading ? "Cargando…" : "Sin métricas del modelo."}</p>
          )}
          <p className="mt-2 flex items-start gap-2 text-[12px] leading-snug text-slate-400">
            <MousePointerClick size={15} className="mt-0.5 shrink-0 text-cyan-300" />
            <span>
              Haz clic en una cuadra del mapa o de la lista para ver por qué es prioritaria.
              {!layers.segments && (
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
        {(segments.data?.features.length ?? 0) > TOP_SHORT && (
          <button onClick={() => setExpanded((v) => !v)} className="mt-1 text-[10px] text-cyan-300 hover:underline">
            {expanded ? `ver sólo las ${TOP_SHORT} primeras` : `ver las ${TOP_LIST} primeras`}
          </button>
        )}
      </Card>
    </div>
  );
}
