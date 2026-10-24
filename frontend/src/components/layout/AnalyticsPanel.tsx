import * as Tabs from "@radix-ui/react-tabs";
import { useUiStore, type PanelTab } from "@/stores/useUiStore";
import { KpiSummaryCards } from "@/components/analytics/KpiSummaryCards";
import { HourlyDistribution } from "@/components/analytics/HourlyDistribution";
import { WeatherImpactChart } from "@/components/analytics/WeatherImpactChart";
import { RiskCorrelationPlot } from "@/components/analytics/RiskCorrelationPlot";
import { MonthlyTrend } from "@/components/analytics/MonthlyTrend";
import { TopCauses } from "@/components/analytics/TopCauses";
import { ModelMetricsPanel } from "@/components/analytics/ModelMetricsPanel";
import { RiskSimulator } from "@/components/simulator/RiskSimulator";
import { SegmentPriorityPanel } from "@/components/analytics/SegmentPriorityPanel";
import { cn } from "@/components/ui";

const TABS: { id: PanelTab; label: string }[] = [
  { id: "analytics", label: "Analítica" },
  { id: "segments", label: "Tramos" },
  { id: "simulator", label: "Simulador" },
  { id: "model", label: "Modelo" },
];

export function AnalyticsPanel() {
  const { activeTab, setTab, panelOpen } = useUiStore();
  if (!panelOpen) return null;
  return (
    <Tabs.Root value={activeTab} onValueChange={(v) => setTab(v as PanelTab)}
      className="hud-aside flex w-[360px] shrink-0 flex-col border-l border-slate-800 bg-slate-950/85">
      <Tabs.List className="flex border-b border-slate-800 px-2" aria-label="Paneles">
        {TABS.map((t) => (
          <Tabs.Trigger key={t.id} value={t.id}
            className={cn("px-3 py-2 text-xs text-slate-400 data-[state=active]:border-b-2 data-[state=active]:border-cyan-400 data-[state=active]:text-slate-100")}>
            {t.label}
          </Tabs.Trigger>
        ))}
      </Tabs.List>
      <div className="flex-1 overflow-y-auto p-3">
        {/* Montaje condicional: los gráficos sólo existen cuando su pestaña está activa */}
        {activeTab === "analytics" && (
          <div className="space-y-3">
            <p className="text-[10px] text-slate-500">Métricas de la ventana visible del mapa y los filtros activos (DuckDB OLAP).</p>
            <KpiSummaryCards />
            <HourlyDistribution />
            <MonthlyTrend />
            <WeatherImpactChart />
            <RiskCorrelationPlot />
            <TopCauses />
          </div>
        )}
        {activeTab === "segments" && <SegmentPriorityPanel />}
        {activeTab === "simulator" && <RiskSimulator />}
        {activeTab === "model" && <ModelMetricsPanel />}
      </div>
    </Tabs.Root>
  );
}
