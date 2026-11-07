import { Suspense, useId, useRef, useState, type KeyboardEvent } from "react";
import { HelpCircle, X } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { startSectionTour } from "@/components/tour/launcher";
import { useUiStore } from "@/stores/useUiStore";
import { cn } from "@/components/ui";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { lazyNamed } from "@/lib/lazyNamed";
import { TABS } from "./tabs";

/*
 * Cada pestaña es un módulo independiente que se carga bajo demanda (chunk propio):
 * es la frontera de "micro frontend" del proyecto. Comparten React, el store y el
 * mapa por importación, sin el coste de federar bundles en tiempo de ejecución
 * (ver docs/ADR_MICRO_FRONTENDS.md). Cada módulo tiene su propio límite de errores.
 */
const KpiSummaryCards = lazyNamed(() => import("@/components/analytics/KpiSummaryCards"), "KpiSummaryCards");
const HourlyDistribution = lazyNamed(() => import("@/components/analytics/HourlyDistribution"), "HourlyDistribution");
const MonthlyTrend = lazyNamed(() => import("@/components/analytics/MonthlyTrend"), "MonthlyTrend");
const WeatherImpactChart = lazyNamed(() => import("@/components/analytics/WeatherImpactChart"), "WeatherImpactChart");
const TopCauses = lazyNamed(() => import("@/components/analytics/TopCauses"), "TopCauses");
const RiskCorrelationPlot = lazyNamed(() => import("@/components/analytics/RiskCorrelationPlot"), "RiskCorrelationPlot");
const SegmentPriorityPanel = lazyNamed(() => import("@/components/analytics/SegmentPriorityPanel"), "SegmentPriorityPanel");
const RiskSimulator = lazyNamed(() => import("@/components/simulator/RiskSimulator"), "RiskSimulator");
const ModelMetricsPanel = lazyNamed(() => import("@/components/analytics/ModelMetricsPanel"), "ModelMetricsPanel");

type AnalyticsView = "summary" | "factors";
const VIEWS: { id: AnalyticsView; label: string }[] = [
  { id: "summary", label: "1 · Cuánto y cuándo" },
  { id: "factors", label: "2 · En qué condiciones" },
];

/**
 * Analítica en dos pasos de lectura (menos gráficos a la vez) con jerarquía de bento:
 * cifras clave en mosaico, una tarjeta principal destacada por paso y las secundarias debajo.
 * Las pestañas siguen el patrón ARIA (flechas izquierda/derecha, Inicio, Fin).
 */
function AnalyticsBento() {
  const [view, setView] = useState<AnalyticsView>("summary");
  const id = useId();
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);
  const onKey = (e: KeyboardEvent, i: number) => {
    const next = e.key === "ArrowRight" ? i + 1 : e.key === "ArrowLeft" ? i - 1 : e.key === "Home" ? 0 : e.key === "End" ? VIEWS.length - 1 : null;
    if (next === null) return;
    e.preventDefault();
    const j = (next + VIEWS.length) % VIEWS.length;
    setView(VIEWS[j].id);
    tabsRef.current[j]?.focus();
  };
  return (
    <div className="grid grid-cols-2 gap-2" data-testid="analytics-bento">
      <div className="col-span-2 grid grid-cols-2 gap-1 rounded-lg border border-slate-800 p-0.5" role="tablist" aria-label="Paso de lectura" data-tour="analytics-steps">
        {VIEWS.map((v, i) => (
          <button key={v.id} role="tab" id={`${id}-tab-${v.id}`} aria-controls={`${id}-panel`} aria-selected={view === v.id}
            tabIndex={view === v.id ? 0 : -1} ref={(el) => { tabsRef.current[i] = el; }}
            onClick={() => setView(v.id)} onKeyDown={(e) => onKey(e, i)}
            className={cn("rounded-md py-1 text-[11px] text-slate-400 hover:text-slate-100", view === v.id && "bg-slate-800 text-slate-100")}>
            {v.label}
          </button>
        ))}
      </div>
      <div role="tabpanel" id={`${id}-panel`} aria-labelledby={`${id}-tab-${view}`} className="col-span-2 grid grid-cols-2 gap-2">
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
    </div>
  );
}

/** Panel de la sección activa. La navegación vive sólo en la cabecera (una sola barra de secciones). */
export function AnalyticsPanel() {
  const { activeTab, panelOpen, togglePanel } = useUiStore(
    useShallow((s) => ({ activeTab: s.activeTab, panelOpen: s.panelOpen, togglePanel: s.togglePanel })),
  );
  if (!panelOpen) return null;
  const tab = TABS.find((t) => t.id === activeTab) ?? TABS[0];
  return (
    <aside
      aria-label={tab.label}
      className={cn("hud-aside flex shrink-0 flex-col border-l border-slate-800 bg-slate-950/85 transition-[width]",
        // Se adapta a portátiles: nunca más de ~45% del ancho de la ventana
        activeTab === "analytics" ? "w-[clamp(340px,42vw,600px)]" : "w-[clamp(320px,32vw,400px)]")}
    >
      <header className="flex items-center justify-between border-b border-slate-800 px-3 py-2">
        <div className="leading-tight">
          <h2 className="hud-title text-sm font-semibold text-slate-100">{tab.label}</h2>
          <p className="text-[11px] text-slate-400">{tab.hint}</p>
        </div>
        <div className="flex items-center gap-2">
          <button onClick={() => void startSectionTour(activeTab)} aria-label={`Guía de ${tab.label}`} title={`Guía de ${tab.label}`}
            className="text-slate-400 hover:text-slate-200"><HelpCircle size={15} /></button>
          <button onClick={togglePanel} aria-label="Cerrar panel" className="text-slate-400 hover:text-slate-200"><X size={16} /></button>
        </div>
      </header>
      <div className="flex-1 overflow-y-auto p-3">
        {/* Montaje condicional: los gráficos sólo existen cuando su sección está activa */}
        <ErrorBoundary area={tab.label} resetKey={activeTab}>
          <Suspense fallback={<p className="text-xs text-slate-400">Cargando módulo…</p>}>
            {activeTab === "analytics" && <AnalyticsBento />}
            {activeTab === "segments" && <SegmentPriorityPanel />}
            {activeTab === "simulator" && <RiskSimulator />}
            {activeTab === "model" && <ModelMetricsPanel />}
          </Suspense>
        </ErrorBoundary>
      </div>
    </aside>
  );
}
