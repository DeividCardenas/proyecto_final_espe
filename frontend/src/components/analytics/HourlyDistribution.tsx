import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { useFilterStore } from "@/stores/useFilterStore";
import { Card, fmtNumber } from "@/components/ui";
import { ColumnChart } from "@/components/charts/d3";

/** Distribución por hora: se resalta la hora pico y se compara con la hora promedio. */
export function HourlyDistribution({ hero = false }: { hero?: boolean }) {
  const { filters: f, scope } = useKpis();
  const setHourRange = useFilterStore((s) => s.setHourRange);
  // La distribución horaria ignora el filtro de horas para mostrar el contexto completo
  const q = { ...f, hourRange: [0, 23] as [number, number] };
  const { data = [] } = useQuery({
    queryKey: ["hourly", q],
    queryFn: () => crashService.hourly(q),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const total = data.reduce((a, d) => a + d.crashes, 0);
  const avg = total / 24;
  const peak = data.reduce<(typeof data)[number] | null>((a, d) => (!a || d.crashes > a.crashes ? d : a), null);
  return (
    <Card
      hero={hero}
      title="¿A qué hora?"
      className="col-span-2"
      right={<span className="text-[10px] text-slate-500">clic = filtrar hora</span>}
      takeaway={peak && avg > 0 && (
        <>Pico a las <b>{peak.hour}:00</b>: {fmtNumber(peak.crashes)} siniestros, {(peak.crashes / avg).toLocaleString("es", { maximumFractionDigits: 1 })}× la hora promedio.</>
      )}
      context={`Siniestros por hora de inicio · ${scope}`}
    >
      <ColumnChart
        ariaLabel="Siniestros por hora del día"
        data={data.map((d) => ({ key: d.hour, label: `${d.hour}h`, value: d.crashes }))}
        highlight={peak?.hour}
        reference={avg > 0 ? { value: avg, label: `promedio ${fmtNumber(avg)}` } : undefined}
        onSelect={(h) => setHourRange([Number(h), Number(h)])}
      />
    </Card>
  );
}
