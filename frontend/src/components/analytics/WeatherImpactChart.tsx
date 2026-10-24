import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { Card, fmtPct } from "@/components/ui";
import { tooltipStyleFor } from "./HourlyDistribution";
import { useTheme } from "@/stores/useThemeStore";


export function WeatherImpactChart() {
  const t = useTheme();
  const tooltipStyle = tooltipStyleFor(t);
  const COLORS = t.chart.series;
  const f = useQueryFilters();
  const { data = [] } = useQuery({
    queryKey: ["weather", f],
    queryFn: () => crashService.weather(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const top = data.slice(0, 6);
  const rest = data.slice(6).reduce((a, r) => a + r.crashes, 0);
  const slices = rest > 0 ? [...top, { weather: "OTROS", crashes: rest, critical_rate: NaN }] : top;
  const total = slices.reduce((a, r) => a + r.crashes, 0) || 1;
  return (
    <Card title="Impacto del clima">
      <div className="flex items-center gap-2">
        <div className="h-36 w-36 shrink-0">
          <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
            <PieChart>
              <Pie data={slices} dataKey="crashes" nameKey="weather" innerRadius={38} outerRadius={64} paddingAngle={1} stroke="none">
                {slices.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
              </Pie>
              <Tooltip {...tooltipStyle} formatter={(v: number) => v.toLocaleString("es")} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <ul className="min-w-0 flex-1 space-y-1 text-[11px]">
          {slices.map((s, i) => (
            <li key={s.weather} className="flex items-center gap-1.5 text-slate-300">
              <i className="h-2 w-2 shrink-0 rounded-full" style={{ background: COLORS[i % COLORS.length] }} />
              <span className="truncate" title={s.weather}>{s.weather}</span>
              <span className="ml-auto tabular-nums text-slate-400">{fmtPct(s.crashes / total, 0)}</span>
              {!Number.isNaN(s.critical_rate) && (
                <span className="w-12 text-right tabular-nums text-red-300" title="Tasa de siniestros críticos">{fmtPct(s.critical_rate, 1)}</span>
              )}
            </li>
          ))}
        </ul>
      </div>
    </Card>
  );
}
