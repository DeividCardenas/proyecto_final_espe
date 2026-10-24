import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { Card } from "@/components/ui";
import { tooltipStyleFor } from "./HourlyDistribution";
import { useTheme } from "@/stores/useThemeStore";

export function MonthlyTrend() {
  const t = useTheme();
  const tooltipStyle = tooltipStyleFor(t);
  const f = useQueryFilters();
  const { data = [] } = useQuery({
    queryKey: ["monthly", f],
    queryFn: () => crashService.monthly(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  return (
    <Card title="Tendencia mensual">
      <div className="h-32">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <AreaChart data={data} margin={{ left: -18, right: 4, top: 4 }}>
            <defs>
              <linearGradient id="gCrash" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor={t.chart.primary} stopOpacity={0.6} />
                <stop offset="100%" stopColor={t.chart.primary} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke={t.chart.grid} vertical={false} />
            <XAxis dataKey="month" tick={{ fill: t.chart.axis, fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fill: t.chart.axis, fontSize: 10 }} />
            <Tooltip {...tooltipStyle} formatter={(v: number, n: string) => [v.toLocaleString("es"), n === "crashes" ? "Siniestros" : "Críticos"]} />
            <Area type="monotone" dataKey="crashes" stroke={t.chart.primary} fill="url(#gCrash)" strokeWidth={1.5} />
            <Area type="monotone" dataKey="critical" stroke={t.chart.critical} fill="none" strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
