import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { CartesianGrid, ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis } from "recharts";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "@/hooks/useViewportCrashes";
import { Card } from "@/components/ui";
import { tooltipStyleFor } from "./HourlyDistribution";
import { useTheme } from "@/stores/useThemeStore";

/** Volumen vehicular (AADT, por decil) frente a tasa de siniestros críticos. */
export function RiskCorrelationPlot() {
  const t = useTheme();
  const tooltipStyle = tooltipStyleFor(t);
  const f = useQueryFilters();
  const { data = [] } = useQuery({
    queryKey: ["aadt-severity", f],
    queryFn: () => crashService.aadtSeverity(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const points = data.map((d) => ({ ...d, critical_pct: d.critical_rate * 100 }));
  return (
    <Card title="Flujo vehicular AADT vs severidad">
      <div className="h-40">
        <ResponsiveContainer width="100%" height="100%" minWidth={0} minHeight={0}>
          <ScatterChart margin={{ left: -14, right: 8, top: 6 }}>
            <CartesianGrid stroke={t.chart.grid} />
            <XAxis type="number" dataKey="mean_aadt" name="AADT" tick={{ fill: t.chart.axis, fontSize: 10 }}
              tickFormatter={(v: number) => `${Math.round(v / 1000)}k`} domain={["auto", "auto"]} />
            <YAxis type="number" dataKey="critical_pct" name="% críticos" unit="%" tick={{ fill: t.chart.axis, fontSize: 10 }} />
            <ZAxis type="number" dataKey="crashes" range={[40, 220]} name="Siniestros" />
            <Tooltip {...tooltipStyle} cursor={{ strokeDasharray: "3 3" }}
              formatter={(v: number, n: string) => [n === "% críticos" ? `${v.toFixed(2)}%` : v.toLocaleString("es"), n]} />
            <Scatter data={points} fill={t.chart.series[3]} />
          </ScatterChart>
        </ResponsiveContainer>
      </div>
      <p className="text-[10px] text-slate-500">Deciles de siniestros con estación de aforo a menos de 500 m</p>
    </Card>
  );
}
