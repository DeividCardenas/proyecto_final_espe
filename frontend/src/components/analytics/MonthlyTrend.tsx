import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { LineChart } from "@/components/charts/d3";

/** Evolución mensual frente a la media del periodo; el mes en curso (incompleto) se excluye. */
export function MonthlyTrend() {
  const { filters: f, scope, local } = useKpis();
  const { data = [] } = useQuery({
    queryKey: ["monthly", f],
    queryFn: () => crashService.monthly(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const lastDate = local.data?.last_date ? new Date(local.data.last_date) : null;
  const series = data.map((d) => ({ date: new Date(d.month), value: d.crashes }));
  // Un mes cuyo último dato no llega al día 28 está incompleto y sesgaría la comparación
  const partial = !!lastDate && lastDate.getDate() < 28 && series.length > 0
    && series[series.length - 1].date.getMonth() === lastDate.getMonth()
    && series[series.length - 1].date.getFullYear() === lastDate.getFullYear();
  const full = partial ? series.slice(0, -1) : series;
  const mean = full.length ? full.reduce((a, d) => a + d.value, 0) / full.length : 0;
  const last = full[full.length - 1];
  return (
    <Card
      title="¿Cómo evoluciona?"
      className="col-span-2"
      takeaway={last && mean > 0 && (
        <>{last.date.toLocaleDateString("es", { month: "long", year: "numeric" })}: {fmtNumber(last.value)} siniestros, {" "}
          {last.value >= mean ? "+" : ""}{fmtPct(last.value / mean - 1, 0)} frente al mes promedio.</>
      )}
      context={`Siniestros por mes${partial ? " (mes en curso excluido por incompleto)" : ""} · ${scope}`}
    >
      <LineChart
        ariaLabel="Siniestros por mes"
        data={full}
        reference={mean > 0 ? { value: mean, label: `promedio ${fmtNumber(mean)}` } : undefined}
      />
    </Card>
  );
}
