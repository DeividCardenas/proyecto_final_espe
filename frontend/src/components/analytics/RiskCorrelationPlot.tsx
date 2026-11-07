import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { Scatter } from "@/components/charts/d3";

/** Volumen vehicular (AADT, por decil) frente a tasa de siniestros críticos. */
export function RiskCorrelationPlot() {
  const { rateFilters: f, scope, localRates, composed } = useKpis();
  const query = useQuery({
    queryKey: ["aadt-severity", f],
    queryFn: ({ signal }) => crashService.aadtSeverity(f, signal),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const data = query.data ?? [];
  const overall = localRates.data?.critical_rate ?? null;
  const lo = data[0];
  const hi = data[data.length - 1];
  return (
    <Card
      title="¿Más tráfico, más gravedad?"
      className="col-span-2"
      error={query.isError}
      onRetry={() => void query.refetch()}
      takeaway={lo && hi && data.length > 1 && (
        <>Decil de menos tráfico: {fmtPct(lo.critical_rate, 2)} críticos; decil de más tráfico: {fmtPct(hi.critical_rate, 2)}.</>
      )}
      context={`Cada punto es un decil de siniestros con aforo AADT a < 500 m (aforos de 2006)${composed ? " · tasas sin filtros de severidad ni obra" : ""} · ${scope}`}
    >
      <Scatter
        ariaLabel="Tráfico diario frente a tasa de siniestros críticos"
        points={data.map((d) => ({
          x: d.mean_aadt, y: d.critical_rate,
          label: `Decil ${d.decile}: AADT ${fmtNumber(d.mean_aadt)} · ${fmtPct(d.critical_rate, 2)} críticos · ${fmtNumber(d.crashes)} siniestros`,
        }))}
        xFormat={(v) => `${Math.round(v / 1000)}k`}
        yFormat={(v) => fmtPct(v, 1)}
        xLabel="vehículos / día"
        yLabel="% críticos"
        reference={overall ? { value: overall, label: `global ${fmtPct(overall, 2)}` } : undefined}
      />
    </Card>
  );
}
