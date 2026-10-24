import { useQuery } from "@tanstack/react-query";
import { Bar, BarChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { crashService } from "@/services/crashService";
import { Card, cn, fmtNumber, fmtPct } from "@/components/ui";
import { tooltipStyle } from "./HourlyDistribution";

const GATE_LABELS: Record<string, string> = {
  auc_roc: "AUC-ROC multiclase ≥ 0.70",
  recall_critical: "Recall clase crítica ≥ 0.60",
  precision_critical: "Precisión clase crítica ≥ 0.65",
  cv_variance: "Variación 5-fold < 5%",
};

export function ModelMetricsPanel() {
  const { data, isError } = useQuery({ queryKey: ["model-metrics"], queryFn: crashService.modelMetrics, staleTime: Infinity });
  if (isError) return <p className="text-xs text-slate-400">Aún no hay un modelo entrenado.</p>;
  if (!data) return <p className="text-xs text-slate-500">Cargando métricas…</p>;
  const labels = ["Bajo", "Moderado", "Crítico"];
  const importance = data.feature_importance.slice(0, 10).map((f) => ({
    name: f.feature.replace(/^(num|cat)__/, "").replace(/_/g, " ").toLowerCase().slice(0, 28),
    value: f.importance,
  }));
  return (
    <div className="space-y-3">
      <Card title={`Modelo ganador · ${data.winner}`}>
        <p className="text-[11px] text-slate-400">
          Entrenado con {fmtNumber(data.n_rows)} siniestros · artefacto {data.artifact.size_mb} MB · carga {data.artifact.load_ms} ms · inferencia {data.artifact.single_inference_ms} ms
        </p>
        <div className="mt-2 grid grid-cols-3 gap-2 text-center">
          {[
            ["AUC macro", data.test.auc_roc_ovr_macro],
            ["AUC crítico", data.test.auc_roc_critical_vs_rest],
            ["Recall crítico", data.test.recall_critical],
          ].map(([k, v]) => (
            <div key={k as string} className="rounded bg-slate-800/80 py-1.5">
              <p className="text-[10px] text-slate-500">{k}</p>
              <p className="text-base font-semibold tabular-nums text-slate-100">{(v as number).toFixed(3)}</p>
            </div>
          ))}
        </div>
      </Card>
      <Card title="Quality gates del plan">
        <ul className="space-y-1 text-[11px]">
          {Object.entries(data.gates).map(([k, ok]) => (
            <li key={k} className="flex items-center justify-between">
              <span className="text-slate-300">{GATE_LABELS[k] ?? k}</span>
              <span className={cn("rounded px-1.5 py-0.5 font-semibold", ok ? "bg-emerald-600/30 text-emerald-300" : "bg-red-600/30 text-red-300")}>{ok ? "CUMPLE" : "NO CUMPLE"}</span>
            </li>
          ))}
        </ul>
        <p className="mt-2 text-[10px] leading-snug text-slate-500">
          Precisión crítica {fmtPct(data.test.precision_critical)} con decisión argmax; con umbral F1 óptimo ({data.test_f1_threshold.threshold.toFixed(2)}) sube a {fmtPct(data.test_f1_threshold.precision_critical)} y el recall baja a {fmtPct(data.test_f1_threshold.recall_critical)}. La clase crítica representa {fmtPct(data.class_distribution["Crítico"] ?? data.class_distribution["Crítico"], 1)} de los siniestros.
        </p>
      </Card>
      <Card title="Matriz de confusión (test)">
        <table className="w-full text-center text-[11px] tabular-nums">
          <thead><tr><th className="text-left text-slate-500">real \ pred</th>{labels.map((l) => <th key={l} className="text-slate-400">{l}</th>)}</tr></thead>
          <tbody>
            {data.confusion_matrix.map((row, i) => {
              const total = row.reduce((a, b) => a + b, 0) || 1;
              return (
                <tr key={i}>
                  <td className="text-left text-slate-400">{labels[i]}</td>
                  {row.map((v, j) => (
                    <td key={j} className="p-0.5">
                      <div className="rounded py-1" style={{ background: `rgba(14,165,233,${(v / total) * 0.85})` }}>{fmtNumber(v)}</div>
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </Card>
      <Card title="Importancia de variables">
        <div className="h-56">
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <BarChart data={importance} layout="vertical" margin={{ left: 0, right: 8 }}>
              <XAxis type="number" hide />
              <YAxis type="category" dataKey="name" width={120} tick={{ fill: "#94a3b8", fontSize: 9 }} />
              <Tooltip {...tooltipStyle} formatter={(v: number) => v.toFixed(4)} />
              <Bar dataKey="value" fill="#a78bfa" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>
      <Card title="Comparativa de algoritmos">
        <table className="w-full text-[11px] tabular-nums">
          <thead><tr className="text-slate-500"><th className="text-left">modelo</th><th>AUC</th><th>Recall</th><th>Precisión</th></tr></thead>
          <tbody>
            {Object.entries(data.comparison).map(([k, m]) => (
              <tr key={k} className="text-center text-slate-300">
                <td className="text-left">{k}</td><td>{m.auc_roc_ovr_macro.toFixed(3)}</td><td>{m.recall_critical.toFixed(3)}</td><td>{m.precision_critical.toFixed(3)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </Card>
    </div>
  );
}
