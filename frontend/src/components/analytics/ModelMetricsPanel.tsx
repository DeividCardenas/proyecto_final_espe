import { useQuery } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { Card, cn, fmtNumber, fmtPct } from "@/components/ui";
import { RankChart } from "@/components/charts/d3";
import { modelLabel, targetYear } from "@/lib/modelLabels";

const GATE_LABELS: Record<string, string> = {
  auc_roc: "AUC-ROC multiclase ≥ 0.70",
  recall_critical: "Recall clase crítica ≥ 0.60",
  precision_critical: "Precisión clase crítica ≥ 0.65",
  cv_variance: "Variación CV espacial < 5%",
  lift_critical: "Lift clase crítica ≥ 3×",
};

/** Modelo principal (por tramo) y, plegado, el modelo por siniestro. */
export function ModelMetricsPanel() {
  return (
    <div className="grid grid-cols-2 gap-2">
      <SegmentModelSection />
      <CrashModelSection />
    </div>
  );
}

function SegmentModelSection() {
  const { data: m, isError } = useQuery({ queryKey: ["segment-metrics"], queryFn: ({ signal }) => crashService.segmentMetrics(signal), staleTime: Infinity });
  if (isError) return <p className="col-span-2 text-xs text-slate-400">Aún no se ha entrenado el modelo por tramo.</p>;
  if (!m) return <p className="col-span-2 text-xs text-slate-400">Cargando métricas…</p>;
  const win = m.comparison?.[m.winner];
  if (!win) return <p className="col-span-2 text-xs text-slate-400">El reporte del modelo por tramo está incompleto.</p>;
  const rows = Object.entries(m.comparison);
  // El año evaluado sale del reporte: si se reentrena con otra ventana, el texto se actualiza solo
  const year = targetYear(m.windows?.test);
  return (
    <>
      <Card
        tourId="model-main"
        title="Modelo principal · riesgo por cuadra"
        className="col-span-2"
        takeaway={<>{modelLabel(m.winner)}: interviniendo el 10% de cuadras priorizadas se cubre el{" "}
          <b>{fmtPct(win.top10_capture_severe, 0)}</b> de los siniestros graves del año siguiente.</>}
        context={`Test fuera de tiempo (${m.windows?.test ?? "—"}) con ${fmtNumber(m.n_test)} cuadras. La línea discontinua es lo que captaría elegir el 10% al azar.`}
      >
        <RankChart
          ariaLabel="Captura de siniestros graves en el top 10% por algoritmo"
          data={rows.map(([k, v]) => ({ label: modelLabel(k), value: v.top10_capture_severe, highlight: k === m.winner,
            note: k === m.winner ? "elegido" : undefined }))}
          format={(v) => fmtPct(v, 0)}
          reference={{ value: 0.1, label: "azar 10%" }}
        />
      </Card>
      <Card title="Comparativa completa" className="col-span-2"
        context="AUC: 0,5 = azar, 1 = perfecto. CV espacial con bloques de ~2 km (cuadras vecinas nunca en train y validación a la vez).">
        <table className="w-full text-[11px] tabular-nums">
          <thead>
            <tr className="text-slate-400">
              <th className="text-left font-normal">modelo</th><th className="font-normal">{year ? `AUC ${year}` : "AUC test"}</th><th className="font-normal">CV esp.</th><th className="font-normal">Recall Alto</th>
            </tr>
          </thead>
          <tbody>
            {rows.map(([k, v]) => (
              <tr key={k} className={cn("text-center text-slate-400", k === m.winner && "text-slate-100")}>
                <td className="text-left">{modelLabel(k)}</td>
                <td>{fmtNumber(v.auc_roc_ovr_macro, 3)}</td>
                <td>{fmtNumber(v.spatial_cv_auc, 3)}</td>
                <td>{fmtNumber(v.recall_high, 2)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </>
  );
}

function CrashModelSection() {
  const { data, isError } = useQuery({ queryKey: ["model-metrics"], queryFn: ({ signal }) => crashService.modelMetrics(signal), staleTime: Infinity });
  if (isError || !data?.test || !data.confusion_matrix) return null;
  const labels = ["Bajo", "Moderado", "Crítico"];
  const importance = (data.feature_importance ?? []).slice(0, 8).map((f) => ({
    label: f.feature.replace(/^(num|cat)__/, "").replace(/_/g, " ").toLowerCase().slice(0, 40),
    value: f.importance,
  }));
  const critShare = data.class_distribution?.["Crítico"] ?? null;
  // Con probabilidades calibradas el argmax casi nunca elige «Crítico»: si la API publica la
  // regla de decisión (umbral), el recall que se muestra es el de esa regla
  const decision = data.test_decision;
  return (
    <details className="col-span-2 rounded-xl border border-slate-800 bg-slate-900/60 p-3 [&_summary]:cursor-pointer">
      <summary className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">
        Modelo secundario · severidad por siniestro ({modelLabel(data.winner)})
      </summary>
      <div className="mt-2 grid grid-cols-2 gap-2">
        <Card className="col-span-2"
          takeaway={<>AUC macro {fmtNumber(data.test.auc_roc_ovr_macro, 2)}; detecta el {fmtPct(decision?.recall_critical ?? data.test.recall_critical, 0)} de los siniestros
            críticos{critShare !== null && <>, que son sólo el {fmtPct(critShare, 1)} del total</>}
            {decision?.threshold !== undefined && <> (umbral {fmtNumber(decision.threshold, 2)}{decision.lift !== undefined && <>, lift {fmtNumber(decision.lift, 1)}×</>})</>}.</>}
          context={`Entrenado con ${fmtNumber(data.n_rows)} siniestros · inferencia ${data.artifact?.single_inference_ms ?? "—"} ms`}>
          <ul className="space-y-1 text-[11px]">
            {Object.entries(data.gates ?? {}).map(([k, ok]) => (
              <li key={k} className="flex items-center justify-between">
                <span className="text-slate-300">{GATE_LABELS[k] ?? k}</span>
                <span className={cn("rounded px-1.5 py-0.5 font-semibold", ok ? "bg-emerald-600/30 text-emerald-300" : "bg-red-600/30 text-red-300")}>{ok ? "CUMPLE" : "NO CUMPLE"}</span>
              </li>
            ))}
          </ul>
          {data.test_f1_threshold?.threshold !== undefined && (
            <p className="mt-2 text-[10px] leading-snug text-slate-400">
              Precisión crítica {fmtPct(data.test.precision_critical)} con decisión argmax; con umbral F1 óptimo ({fmtNumber(data.test_f1_threshold.threshold, 2)}) sube a {fmtPct(data.test_f1_threshold.precision_critical)} y el recall baja a {fmtPct(data.test_f1_threshold.recall_critical)}.
            </p>
          )}
        </Card>
        <Card title="Matriz de confusión (test)" className="col-span-2" context="Color = % de cada fila real.">
          <table className="w-full text-center text-[11px] tabular-nums">
            <thead><tr><th className="text-left font-normal text-slate-400">real \ pred</th>{labels.map((l) => <th key={l} className="font-normal text-slate-400">{l}</th>)}</tr></thead>
            <tbody>
              {data.confusion_matrix.map((row, i) => {
                const total = row.reduce((a, b) => a + b, 0) || 1;
                return (
                  <tr key={i}>
                    <td className="text-left text-slate-400">{labels[i]}</td>
                    {row.map((v, j) => (
                      <td key={j} className="p-0.5">
                        <div className="rounded py-1" style={{ background: `rgb(var(--slate-400) / ${(v / total) * 0.6})` }}>{fmtNumber(v)}</div>
                      </td>
                    ))}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </Card>
        <Card title="Variables más influyentes" className="col-span-2" context={`Importancia relativa en el modelo ${modelLabel(data.winner)} (sin unidad; sólo comparable entre variables).`}>
          <RankChart ariaLabel="Importancia de variables del modelo por siniestro" data={importance} format={(v) => fmtNumber(v, 3)} />
        </Card>
      </div>
    </details>
  );
}
