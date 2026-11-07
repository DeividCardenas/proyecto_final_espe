import { useMemo } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { useFilterStore } from "@/stores/useFilterStore";
import { Card, fmtNumber } from "@/components/ui";
import { ColumnChart } from "@/components/charts/d3";
import type { HourlyRow } from "@/types/api";

/** Las 24 horas siempre presentes: una hora sin siniestros se ve como barra en cero, no desaparece. */
export function fillHours(rows: HourlyRow[]): HourlyRow[] {
  const byHour = new Map(rows.map((r) => [r.hour, r]));
  return Array.from({ length: 24 }, (_, hour) => byHour.get(hour) ?? { hour, crashes: 0, critical: 0 });
}

/** Distribución por hora: se resalta la hora pico y se compara con la hora promedio. */
export function HourlyDistribution({ hero = false }: { hero?: boolean }) {
  const { filters: f, scope } = useKpis();
  const setHourRange = useFilterStore((s) => s.setHourRange);
  const hourRange = useFilterStore((s) => s.hourRange);
  // La distribución horaria ignora el filtro de horas para mostrar el contexto completo
  const q = useMemo(() => ({ ...f, hourRange: [0, 23] as [number, number] }), [f]);
  const query = useQuery({
    queryKey: ["hourly", q],
    queryFn: ({ signal }) => crashService.hourly(q, signal),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const data = useMemo(() => (query.data ? fillHours(query.data) : []), [query.data]);
  const total = data.reduce((a, d) => a + d.crashes, 0);
  const avg = total / 24;
  const peak = data.reduce<HourlyRow | null>((a, d) => (!a || d.crashes > a.crashes ? d : a), null);
  const single = hourRange[0] === hourRange[1];
  return (
    <Card
      hero={hero}
      tourId="analytics-hero"
      title="¿A qué hora?"
      className="col-span-2"
      error={query.isError}
      onRetry={() => void query.refetch()}
      right={
        single ? (
          <button onClick={() => setHourRange([0, 23])} className="text-[10px] text-cyan-300 hover:underline">
            quitar filtro {hourRange[0]}:00
          </button>
        ) : <span className="text-[10px] text-slate-400">clic = filtrar hora</span>
      }
      takeaway={peak && avg > 0 && (
        <>Pico a las <b>{peak.hour}:00</b>: {fmtNumber(peak.crashes)} siniestros, {(peak.crashes / avg).toLocaleString("es", { maximumFractionDigits: 1 })}× la hora promedio.</>
      )}
      context={`Siniestros por hora de inicio · ${scope}`}
    >
      <ColumnChart
        ariaLabel="Siniestros por hora del día"
        data={data.map((d) => ({ key: d.hour, label: `${d.hour}h`, value: d.crashes }))}
        highlight={single ? hourRange[0] : peak?.hour}
        reference={avg > 0 ? { value: avg, label: `promedio ${fmtNumber(avg)}` } : undefined}
        onSelect={(h) => setHourRange([Number(h), Number(h)])}
      />
    </Card>
  );
}
