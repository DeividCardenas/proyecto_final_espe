import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { cn, fmtNumber, fmtPct } from "@/components/ui";

export function KpiSummaryCards() {
  const f = useQueryFilters();
  const { data, isLoading } = useQuery({
    queryKey: ["kpis", f],
    queryFn: () => crashService.kpis(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const yoy = data?.yoy_change ?? null;
  const items = [
    { label: "Siniestros", value: fmtNumber(data?.total_crashes) },
    { label: "Lesionados", value: fmtNumber(data?.total_injuries) },
    { label: "Fatalidades", value: fmtNumber(data?.fatalities), accent: "text-red-400" },
    { label: "Lesiones incapacitantes", value: fmtNumber(data?.incapacitating), accent: "text-orange-300" },
    { label: "Tasa crítica", value: fmtPct(data?.critical_rate, 2) },
    { label: "Celdas de alto riesgo", value: fmtNumber(data?.high_risk_cells), accent: "text-yellow-300" },
    { label: "En zona de obra", value: fmtNumber(data?.workzone_crashes) },
    {
      label: "Variación interanual",
      value: yoy === null ? "—" : `${yoy > 0 ? "+" : ""}${fmtPct(yoy)}`,
      accent: yoy === null ? "" : yoy > 0 ? "text-red-400" : "text-emerald-400",
    },
  ];
  return (
    <div className={cn("grid grid-cols-2 gap-2", isLoading && "opacity-60")} data-testid="kpi-cards">
      {items.map((it) => (
        <div key={it.label} className="hud-panel rounded-lg border border-slate-800 bg-slate-900/80 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">{it.label}</p>
          <p className={cn("hud-kpi text-lg font-semibold tabular-nums text-slate-100", it.accent)}>{it.value}</p>
        </div>
      ))}
    </div>
  );
}
