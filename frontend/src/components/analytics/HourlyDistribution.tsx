import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { useFilterStore } from "@/stores/useFilterStore";
import { Card } from "@/components/ui";

export const tooltipStyle = {
  contentStyle: { background: "#0f172a", border: "1px solid #334155", borderRadius: 8, fontSize: 11 },
  labelStyle: { color: "#e2e8f0" },
};

export function HourlyDistribution() {
  const f = useQueryFilters();
  const setHourRange = useFilterStore((s) => s.setHourRange);
  // La distribución horaria ignora el filtro de horas para mostrar el contexto completo
  const q = { ...f, hourRange: [0, 23] as [number, number] };
  const { data = [] } = useQuery({
    queryKey: ["hourly", q],
    queryFn: () => crashService.hourly(q),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  return (
    <Card title="Siniestros por hora del día" right={<span className="text-[10px] text-slate-500">clic = filtrar hora</span>}>
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <BarChart data={data} margin={{ left: -18, right: 4, top: 4 }}>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="hour" tick={{ fill: "#64748b", fontSize: 10 }} interval={2} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
            <Tooltip {...tooltipStyle} formatter={(v: number, n: string) => [v.toLocaleString("es"), n === "crashes" ? "Siniestros" : "Críticos"]}
              labelFormatter={(h) => `${h}:00`} />
            <Bar dataKey="crashes" fill="#0ea5e9" radius={[2, 2, 0, 0]}
              onClick={(d: { hour?: number }) => d.hour !== undefined && setHourRange([d.hour, d.hour])} cursor="pointer" />
            <Bar dataKey="critical" fill="#dc2626" radius={[2, 2, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
