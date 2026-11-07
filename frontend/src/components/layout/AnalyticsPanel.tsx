import { lazy, Suspense, useState, type ComponentType } from "react";
import { HelpCircle, X } from "lucide-react";
import { startSectionTour } from "@/components/tour/guide";
import { useUiStore } from "@/stores/useUiStore";
import { cn } from "@/components/ui";
import { TABS } from "./Header";

/*
 * Cada pestaña es un módulo independiente que se carga bajo demanda (chunk propio):
 * es la frontera de "micro frontend" del proyecto. Comparten React, el store y el
 * mapa por importación, sin el coste de federar bundles en tiempo de ejecución
 * (ver docs/ADR_MICRO_FRONTENDS.md).
 */
const named = <K extends string, P extends object = object>(load: () => Promise<Record<K, ComponentType<P>>>, key: K) =>
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

type AnalyticsView = "summary" | "factors";
const VIEWS: { id: AnalyticsView; label: string }[] = [
  { id: "summary", label: "1 · Cuánto y cuándo" },
  { id: "factors", label: "2 · En qué condiciones" },
];

/**
 * Analítica en dos pasos de lectura (menos gráficos a la vez) con jerarquía de bento:
 * cifras clave en mosaico, una tarjeta principal destacada por paso y las secundarias debajo.
 */
function AnalyticsBento() {
  const [view, setView] = useState<AnalyticsView>("summary");
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="analytics-bento">
      <div className="col-span-2 grid grid-cols-2 gap-1 rounded-lg border border-slate-800 p-0.5" role="tablist" aria-label="Paso de lectura" data-tour="analytics-steps">
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
          <div className="col-span-2"><HourlyDistribution hero /></div>
          <div className="col-span-2"><MonthlyTrend /></div>
        </>
      ) : (
        <>
          <div className="col-span-2"><TopCauses hero /></div>
          {/* Las etiquetas del ranking por clima necesitan el ancho completo para no cruzar la referencia */}
          <div className="col-span-2"><WeatherImpactChart /></div>
          <div className="col-span-2"><RiskCorrelationPlot /></div>
        </>
      )}
    </div>
  );
}

/** Panel de la sección activa. La navegación vive sólo en la cabecera (una sola barra de secciones). */
export function AnalyticsPanel() {
  const { activeTab, panelOpen, togglePanel } = useUiStore();
  if (!panelOpen) return null;
  const tab = TABS.find((t) => t.id === activeTab)!;
  return (
    <aside
      aria-label={tab.label}
      className={cn("hud-aside flex shrink-0 flex-col border-l border-slate-800 bg-slate-950/85 transition-[width]",
        activeTab === "analytics" ? "w-[600px]" : "w-[400px]")}
    >
      <header className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <div className="leading-tight">
          <h2 className="hud-title text-sm font-semibold text-slate-100">{tab.label}</h2>
          <p className="text-[11px] text-slate-500">{tab.hint}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => startSectionTour(activeTab)} aria-label={`Guía de ${tab.label}`} title={`Guía de ${tab.label}`}
            className="text-slate-500 hover:text-slate-200"><HelpCircle size={15} /></button>
          <button onClick={togglePanel} aria-label="Cerrar panel" className="text-slate-500 hover:text-slate-200"><X size={16} /></button>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto p-3">
        {/* Montaje condicional: los gráficos sólo existen cuando su sección está activa */}
        <Suspense fallback={<p className="text-xs text-slate-500">Cargando módulo…</p>}>
          {activeTab === "analytics" && <AnalyticsBento />}
          {activeTab === "segments" && <SegmentPriorityPanel />}
          {activeTab === "simulator" && <RiskSimulator />}
          {activeTab === "model" && <ModelMetricsPanel />}
        </Suspense>
      </div>
    </aside>
  );
}
