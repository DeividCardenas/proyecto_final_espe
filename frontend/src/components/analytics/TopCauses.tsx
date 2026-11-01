import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { RankChart } from "@/components/charts/d3";

// "UNKNOWN" es el valor con el que la API marca una causa ausente
const UNDETERMINED = new Set(["UNABLE TO DETERMINE", "NOT APPLICABLE", "UNKNOWN"]);

/** Ranking de causas contributivas (barras desde cero; la tasa crítica va como nota). */
export function TopCauses() {
  const { filters: f, scope, local } = useKpis();
  const { data = [] } = useQuery({
    queryKey: ["causes", f],
    queryFn: () => crashService.causes(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const total = local.data?.total_crashes ?? 0;
  const known = data.filter((d) => !UNDETERMINED.has(d.cause));
  const undetermined = data.filter((d) => UNDETERMINED.has(d.cause)).reduce((a, d) => a + d.crashes, 0);
  const first = known[0];
  const label = (s: string) => {
    const l = s.toLowerCase();
    return l.length > 46 ? `${l.slice(0, 45)}…` : l;
  };
  return (
    <Card
      title="¿Por qué ocurren?"
      className="col-span-2"
      takeaway={first && total > 0 && (
        <>La causa identificada más frecuente es <b>{first.cause.toLowerCase()}</b> ({fmtPct(first.crashes / total, 0)} del total).</>
      )}
      context={`Causa contributiva principal; ${total > 0 ? `${fmtPct(undetermined / total, 0)} sin causa determinada (excluidos)` : ""} · ${scope}`}
    >
      <RankChart
        ariaLabel="Causas contributivas más frecuentes"
        data={known.slice(0, 6).map((d) => ({
          label: label(d.cause),
          value: d.crashes,
          note: `${fmtPct(d.critical_rate, 1)} críticos`,
        }))}
        format={(v) => fmtNumber(v)}
      />
    </Card>
  );
}
