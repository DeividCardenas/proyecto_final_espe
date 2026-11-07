import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { useFilterStore } from "@/stores/useFilterStore";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { LineChart } from "@/components/charts/d3";

/** "YYYY-MM" como fecha local (new Date() lo leería en UTC y en Chicago caería en el mes anterior). */
const monthDate = (s: string) => {
  const [y, m] = s.split("-").map(Number);
  return new Date(y, m - 1, 1);
};
/** "YYYY-MM-DD..." como fecha local, por el mismo motivo. */
const dayDate = (s: string) => {
  const [y, m, d] = s.slice(0, 10).split("-").map(Number);
  return new Date(y, m - 1, d);
};
const daysInMonth = (d: Date) => new Date(d.getFullYear(), d.getMonth() + 1, 0).getDate();

/** Evolución mensual frente a la media del periodo; el último mes se excluye si los datos no lo cubren entero. */
export function MonthlyTrend() {
  const { filters: f, scope, city } = useKpis();
  const endDate = useFilterStore((s) => s.endDate);
  const query = useQuery({
    queryKey: ["monthly", f],
    queryFn: ({ signal }) => crashService.monthly(f, signal),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const data = query.data ?? [];
  const series = data.map((d) => ({ date: monthDate(d.month), value: d.crashes }));
  // Corte de cobertura: último dato de toda la ciudad (no el de la ventana visible)
  // o la fecha final del filtro, lo que llegue antes
  const cityLast = city.data?.last_date ? dayDate(city.data.last_date) : null;
  const filterEnd = endDate ? dayDate(endDate) : null;
  const cutoff = cityLast && filterEnd ? (filterEnd < cityLast ? filterEnd : cityLast) : cityLast ?? filterEnd;
  const lastBucket = series[series.length - 1];
  const partial = !!cutoff && !!lastBucket
    && lastBucket.date.getFullYear() === cutoff.getFullYear() && lastBucket.date.getMonth() === cutoff.getMonth()
    && cutoff.getDate() < daysInMonth(cutoff);
  const full = partial ? series.slice(0, -1) : series;
  const mean = full.length ? full.reduce((a, d) => a + d.value, 0) / full.length : 0;
  const last = full[full.length - 1];
  return (
    <Card
      title="¿Cómo evoluciona?"
      className="col-span-2"
      error={query.isError}
      onRetry={() => void query.refetch()}
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
