import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { Card } from "@/components/ui";
import { tooltipStyle } from "./HourlyDistribution";

export function MonthlyTrend() {
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
                <stop offset="0%" stopColor="#0ea5e9" stopOpacity={0.6} />
                <stop offset="100%" stopColor="#0ea5e9" stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1e293b" vertical={false} />
            <XAxis dataKey="month" tick={{ fill: "#64748b", fontSize: 10 }} minTickGap={24} />
            <YAxis tick={{ fill: "#64748b", fontSize: 10 }} />
            <Tooltip {...tooltipStyle} formatter={(v: number, n: string) => [v.toLocaleString("es"), n === "crashes" ? "Siniestros" : "Críticos"]} />
            <Area type="monotone" dataKey="crashes" stroke="#0ea5e9" fill="url(#gCrash)" strokeWidth={1.5} />
            <Area type="monotone" dataKey="critical" stroke="#dc2626" fill="none" strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
}
