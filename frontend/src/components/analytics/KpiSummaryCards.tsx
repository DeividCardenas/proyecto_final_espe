import { useKpis } from "@/hooks/useKpis";
import { cn, fmtNumber, fmtPct } from "@/components/ui";

/** Cuatro cifras clave, cada una con su comparación (interanual o frente a Chicago). */
export function KpiSummaryCards() {
  const { local, city } = useKpis();
  const k = local.data;
  const c = city.data;
  const yoy = k?.yoy_change ?? null;
  const rateRatio = k?.critical_rate && c?.critical_rate ? k.critical_rate / c.critical_rate : null;
  const wzShare = k && k.total_crashes ? (k.workzone_crashes ?? 0) / k.total_crashes : null;
  const cityWzShare = c && c.total_crashes ? (c.workzone_crashes ?? 0) / c.total_crashes : null;
  const fatalPer1k = k && k.total_crashes ? ((k.fatalities ?? 0) / k.total_crashes) * 1000 : null;
  const cityFatalPer1k = c && c.total_crashes ? ((c.fatalities ?? 0) / c.total_crashes) * 1000 : null;

  const items: { label: string; value: string; compare: string; tone?: "up" | "down" }[] = [
    {
      label: "Siniestros",
      value: fmtNumber(k?.total_crashes),
      compare: yoy === null ? "sin año previo para comparar" : `${yoy > 0 ? "+" : ""}${fmtPct(yoy)} vs. 12 meses previos`,
      tone: yoy === null ? undefined : yoy > 0 ? "up" : "down",
    },
    {
      label: "Tasa de siniestros críticos",
      value: fmtPct(k?.critical_rate, 2),
      compare: rateRatio === null ? "—" : `${rateRatio.toLocaleString("es", { maximumFractionDigits: 1 })}× la de Chicago (${fmtPct(c?.critical_rate, 2)})`,
      tone: rateRatio === null ? undefined : rateRatio > 1.05 ? "up" : rateRatio < 0.95 ? "down" : undefined,
    },
    {
      label: "Fallecidos",
      value: fmtNumber(k?.fatalities),
      compare: fatalPer1k === null ? "—" : `${fmtNumber(fatalPer1k, 1)} por 1.000 siniestros (Chicago ${fmtNumber(cityFatalPer1k, 1)})`,
    },
    {
      label: "En zona de obra",
      value: fmtPct(wzShare, 1),
      compare: `de los siniestros (Chicago ${fmtPct(cityWzShare, 1)})`,
    },
  ];
  return (
    <div className={cn("col-span-2 grid grid-cols-2 gap-2", local.isLoading && "opacity-60")} data-testid="kpi-cards">
      {items.map((it) => (
        <div key={it.label} className="hud-panel rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">{it.label}</p>
          <p className="hud-kpi text-xl font-semibold tabular-nums text-slate-100">{it.value}</p>
          <p className={cn("text-[10px] leading-snug text-slate-400", it.tone === "up" && "text-red-300", it.tone === "down" && "text-emerald-300")}>
            {it.compare}
          </p>
        </div>
      ))}
    </div>
  );
}
