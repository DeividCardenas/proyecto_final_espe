import { useQuery } from "@tanstack/react-query";
import { X } from "lucide-react";
import { crashService } from "@/services/crashService";
import { useUiStore, type SelectedSegment } from "@/stores/useUiStore";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { DivergingBars, StripPlot } from "@/components/charts/d3";
import type { SegmentFactor } from "@/types/api";

const TOP_FACTORS = 6;

function describe(f: SegmentFactor): string | undefined {
  if (f.feature === "location") return "zona de la ciudad";
  if (typeof f.value === "string") return f.value.toLowerCase();
  if (f.value === null) return "sin dato";
  const share = f.unit === "proporción";
  const v = share ? fmtPct(f.value, 0) : fmtNumber(f.value, f.value < 10 && f.value % 1 ? 1 : 0);
  const typ = f.city_mean === null ? "" : share ? fmtPct(f.city_mean, 0) : fmtNumber(f.city_mean, f.city_mean < 10 ? 1 : 0);
  return `${v}${share || !f.unit ? "" : ` ${f.unit}`}${typ ? ` · típica ${typ}` : ""}`;
}

/** «a, b y c» */
function joinEs(items: string[]) {
  return items.length <= 1 ? items.join("") : `${items.slice(0, -1).join(", ")} y ${items[items.length - 1]}`;
}

/** Predicción de una cuadra: probabilidad, comparación con la ciudad y variables que la explican. */
export function SegmentExplainCard({ segment }: { segment: SelectedSegment }) {
  const close = useUiStore((s) => s.selectSegment);
  const explain = useQuery({
    queryKey: ["segment-explain", segment.segment_id],
    queryFn: () => crashService.segmentExplain(segment.segment_id),
    staleTime: Infinity,
  });
  const dist = useQuery({ queryKey: ["segment-distribution"], queryFn: crashService.segmentDistribution, staleTime: Infinity });

  const e = explain.data;
  const pAlto = e?.probabilities.Alto ?? segment.p_alto;
  const base = e?.base_rate_high;
  const total = dist.data?.segments_total;
  const factors = e?.factors.slice(0, TOP_FACTORS) ?? [];
  const rest = e ? e.factors.slice(TOP_FACTORS).reduce((a, f) => a + f.contribution, 0) : 0;
  // Lectura en lenguaje llano: qué sube y qué baja el riesgo en esta cuadra
  const ups = factors.filter((f) => f.contribution > 0).slice(0, 3).map((f) => f.label.toLowerCase());
  const downs = factors.filter((f) => f.contribution < 0).slice(0, 2).map((f) => f.label.toLowerCase());

  return (
    <Card
      title="Predicción de la cuadra seleccionada"
      className="col-span-2 border-cyan-700/60"
      right={<button onClick={() => close(null)} aria-label="Cerrar predicción" className="text-slate-500 hover:text-slate-200"><X size={14} /></button>}
      takeaway={
        <>
          <span className="block text-sm font-semibold">{segment.segment_id}</span>
          <span className="text-2xl font-semibold tabular-nums text-red-300">{fmtPct(pAlto, 0)}</span>{" "}
          de probabilidad de riesgo Alto en los próximos 12 meses
          {base ? <>, <b>{(pAlto / base).toLocaleString("es", { maximumFractionDigits: 1 })}×</b> la tasa base de Chicago ({fmtPct(base, 1)}).</> : "."}
        </>
      }
      context={e && (
        <>
          Cómo se calcula: regresión logística (modelo por tramo) con la historia {e.history_window.replace("->", "a")}. Cada
          barra es el aporte de una variable al log-odds de Alto frente a Bajo respecto a una cuadra típica; exacto para
          variables numéricas y aproximado para las categóricas. Las otras {e.factors.length - factors.length} variables suman{" "}
          {rest >= 0 ? "+" : ""}{rest.toFixed(2)}. P(Medio) {fmtPct(e.probabilities.Medio, 0)} · P(Bajo){" "}
          {fmtPct(e.probabilities.Bajo, 0)}.
        </>
      )}
    >
      <p className="text-[11px] text-slate-400">
        Prioridad <b className="text-slate-200">#{fmtNumber(segment.priority_rank)}</b>
        {total ? <> de {fmtNumber(total)} cuadras (top {fmtPct(segment.priority_pct, segment.priority_pct < 0.01 ? 2 : 1)})</> : null}
        {" · "}{fmtNumber(segment.crashes)} siniestros y {fmtNumber(segment.severe_crashes)} graves en 12 meses
      </p>

      <p className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">Dónde queda frente a las demás cuadras</p>
      {dist.data ? (
        <StripPlot
          ariaLabel="Distribución de la probabilidad de riesgo Alto en todas las cuadras"
          values={dist.data.p_alto}
          marker={pAlto}
          reference={base ? { value: base, label: `tasa base ${fmtPct(base, 0)}` } : undefined}
          format={(v) => fmtPct(v, 0)}
        />
      ) : (
        <div className="h-16" />
      )}

      <p className="mt-2 text-[10px] uppercase tracking-wide text-slate-500">Por qué</p>
      {(ups.length > 0 || downs.length > 0) && (
        <p className="mb-1 text-[12px] leading-snug text-slate-200" data-testid="plain-explanation">
          {ups.length > 0 && <>Lo que más sube el riesgo aquí: <b>{joinEs(ups)}</b>. </>}
          {downs.length > 0 && <>Lo que lo baja: {joinEs(downs)}.</>}
        </p>
      )}
      {explain.isLoading && <p className="text-xs text-slate-500">Calculando…</p>}
      {explain.isError && <p className="text-xs text-slate-400">No se pudo explicar esta cuadra.</p>}
      {e && (
        <>
          <DivergingBars
            ariaLabel="Aporte de cada variable al log-odds de riesgo Alto frente a Bajo"
            leftLabel="baja el riesgo"
            rightLabel="sube el riesgo"
            data={factors.map((f) => ({ label: f.label, value: f.contribution, detail: describe(f) }))}
          />
        </>
      )}
    </Card>
  );
}
