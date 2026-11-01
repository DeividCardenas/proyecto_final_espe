import { lazy, Suspense, useState, type ComponentType } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import { useUiStore, type PanelTab } from "@/stores/useUiStore";
import { cn } from "@/components/ui";

/*
 * Cada pestaña es un módulo independiente que se carga bajo demanda (chunk propio):
 * es la frontera de "micro frontend" del proyecto. Comparten React, el store y el
 * mapa por importación, sin el coste de federar bundles en tiempo de ejecución
 * (ver docs/ADR_MICRO_FRONTENDS.md).
 */
const named = <K extends string>(load: () => Promise<Record<K, ComponentType>>, key: K) =>
  lazy(() => load().then((m) => ({ default: m[key] })));

const KpiSummaryCards = named(() => import("@/components/analytics/KpiSummaryCards"), "KpiSummaryCards");
const HourlyDistribution = named(() => import("@/components/analytics/HourlyDistribution"), "HourlyDistribution");
const MonthlyTrend = named(() => import("@/components/analytics/MonthlyTrend"), "MonthlyTrend");
const WeatherImpactChart = named(() => import("@/components/analytics/WeatherImpactChart"), "WeatherImpactChart");
const TopCauses = named(() => import("@/components/analytics/TopCauses"), "TopCauses");
const RiskCorrelationPlot = named(() => import("@/components/analytics/RiskCorrelationPlot"), "RiskCorrelationPlot");
const SegmentPriorityPanel = named(() => import("@/components/analytics/SegmentPriorityPanel"), "SegmentPriorityPanel");
const RiskSimulator = named(() => import("@/components/simulator/RiskSimulator"), "RiskSimulator");
const ModelMetricsPanel = named(() => import("@/components/analytics/ModelMetricsPanel"), "ModelMetricsPanel");

const TABS: { id: PanelTab; label: string }[] = [
  { id: "segments", label: "Tramos" },
  { id: "analytics", label: "Analítica" },
  { id: "simulator", label: "Simulador" },
  { id: "model", label: "Modelo" },
];

type AnalyticsView = "summary" | "factors";
const VIEWS: { id: AnalyticsView; label: string }[] = [
  { id: "summary", label: "1 · Cuánto y cuándo" },
  { id: "factors", label: "2 · En qué condiciones" },
];

/** Analítica en dos pasos de lectura: menos gráficos a la vez, cada uno con su comparación. */
function AnalyticsBento() {
  const [view, setView] = useState<AnalyticsView>("summary");
  return (
    <div className="grid grid-cols-2 gap-2">
      <div className="col-span-2 grid grid-cols-2 gap-1 rounded-lg border border-slate-800 p-0.5" role="tablist" aria-label="Paso de lectura">
        {VIEWS.map((v) => (
          <button key={v.id} role="tab" aria-selected={view === v.id} onClick={() => setView(v.id)}
            className={cn("rounded-md py-1 text-[11px] text-slate-400 hover:text-slate-100", view === v.id && "bg-slate-800 text-slate-100")}>
            {v.label}
          </button>
        ))}
      </div>
      {view === "summary" ? (
        <>
          <KpiSummaryCards />
          <HourlyDistribution />
          <MonthlyTrend />
        </>
      ) : (
        <>
          <WeatherImpactChart />
          <TopCauses />
          <RiskCorrelationPlot />
        </>
      )}
    </div>
  );
}

export function AnalyticsPanel() {
  const { activeTab, setTab, panelOpen } = useUiStore();
  if (!panelOpen) return null;
  return (
    <Tabs.Root value={activeTab} onValueChange={(v) => setTab(v as PanelTab)}
      className="hud-aside flex w-[400px] shrink-0 flex-col border-l border-slate-800 bg-slate-950/85">
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
        <Suspense fallback={<p className="text-xs text-slate-500">Cargando módulo…</p>}>
          {activeTab === "analytics" && <AnalyticsBento />}
          {activeTab === "segments" && <SegmentPriorityPanel />}
          {activeTab === "simulator" && <RiskSimulator />}
          {activeTab === "model" && <ModelMetricsPanel />}
        </Suspense>
      </div>
    </Tabs.Root>
  );
}
