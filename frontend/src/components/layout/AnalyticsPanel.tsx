import { Suspense, useId, useRef, useState, type KeyboardEvent, type PointerEvent } from "react";
import { ChevronDown, ChevronUp, HelpCircle, X } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { startSectionTour } from "@/components/tour/launcher";
import { useUiStore, type SheetSnap } from "@/stores/useUiStore";
import { useIsMobile } from "@/hooks/useIsMobile";
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

/** Altura de cada posición de la hoja inferior (móvil), relativa al alto disponible bajo la cabecera. */
const SHEET_HEIGHT: Record<SheetSnap, string> = { peek: "3.25rem", half: "50%", full: "calc(100% - 7rem)" };
const SHEET_ORDER: SheetSnap[] = ["peek", "half", "full"];

/**
 * Asa de la hoja inferior: tocar alterna media pantalla ↔ casi completa (o abre si está plegada);
 * arrastrar arriba/abajo sube o baja un nivel.
 */
function useSheetDrag() {
  const { sheet, setSheet } = useUiStore(useShallow((s) => ({ sheet: s.sheet, setSheet: s.setSheet })));
  const start = useRef<number | null>(null);
  const onPointerDown = (e: PointerEvent) => { start.current = e.clientY; };
  const onPointerUp = (e: PointerEvent) => {
    if (start.current === null) return;
    const dy = e.clientY - start.current;
    start.current = null;
    const i = SHEET_ORDER.indexOf(sheet);
    if (Math.abs(dy) < 12) setSheet(sheet === "half" ? "full" : "half");
    else setSheet(SHEET_ORDER[Math.max(0, Math.min(SHEET_ORDER.length - 1, i + (dy < 0 ? 1 : -1)))]);
  };
  return { sheet, setSheet, handlers: { onPointerDown, onPointerUp, onPointerCancel: () => { start.current = null; } } };
}

/** Panel de la sección activa. La navegación vive sólo en la cabecera (una sola barra de secciones). */
export function AnalyticsPanel() {
  const { activeTab, panelOpen, togglePanel } = useUiStore(
    useShallow((s) => ({ activeTab: s.activeTab, panelOpen: s.panelOpen, togglePanel: s.togglePanel })),
  );
  const mobile = useIsMobile();
  const { sheet, setSheet, handlers } = useSheetDrag();
  if (!panelOpen) return null;
  const tab = TABS.find((t) => t.id === activeTab) ?? TABS[0];
  return (
    <aside
      aria-label={tab.label}
      data-testid="analytics-panel"
      data-sheet={mobile ? sheet : undefined}
      style={mobile ? { height: SHEET_HEIGHT[sheet] } : undefined}
      className={cn("hud-aside flex shrink-0 flex-col bg-slate-950/85",
        mobile
          // Móvil: hoja inferior a todo el ancho, bajo el mapa (no lo tapa ni se superpone a la leyenda)
          ? "w-full rounded-t-2xl border-t border-slate-700 shadow-[0_-8px_24px_rgba(0,0,0,0.45)] transition-[height] duration-200"
          : cn("border-l border-slate-800 transition-[width]",
            // Se adapta a portátiles: nunca más de ~45% del ancho de la ventana
            activeTab === "analytics" ? "w-[clamp(340px,42vw,600px)]" : "w-[clamp(320px,32vw,400px)]"))}
    >
      {mobile && (
        <div {...handlers} className="flex h-4 shrink-0 touch-none cursor-grab items-end justify-center" aria-hidden="true">
          <span className="h-1 w-10 rounded-full bg-slate-600" />
        </div>
      )}
      <header {...(mobile ? handlers : {})}
        className={cn("flex items-center justify-between gap-2 border-b border-slate-800 px-3",
          mobile ? "touch-none pb-1.5 pt-0.5" : "py-2")}>
        <div className="min-w-0 leading-tight">
          <h2 className="hud-title truncate text-sm font-semibold text-slate-100">{tab.label}</h2>
          <p className="truncate text-[11px] text-slate-400">{tab.hint}</p>
        </div>
        <div className="flex shrink-0 items-center gap-1 md:gap-2">
          {mobile && (
            <button onClick={() => setSheet(sheet === "full" ? "half" : sheet === "half" ? "full" : "half")}
              onPointerDown={(e) => e.stopPropagation()} onPointerUp={(e) => e.stopPropagation()}
              aria-label={sheet === "full" ? "Reducir panel" : "Ampliar panel"}
              className="grid h-8 w-8 place-items-center text-slate-400 hover:text-slate-200">
              {sheet === "full" ? <ChevronDown size={18} /> : <ChevronUp size={18} />}
            </button>
          )}
          <button onClick={() => void startSectionTour(activeTab)} aria-label={`Guía de ${tab.label}`} title={`Guía de ${tab.label}`}
            onPointerDown={(e) => e.stopPropagation()} onPointerUp={(e) => e.stopPropagation()}
            className="text-slate-400 hover:text-slate-200 max-md:grid max-md:h-8 max-md:w-6 max-md:place-items-center"><HelpCircle size={15} /></button>
          <button onClick={togglePanel} aria-label="Cerrar panel"
            onPointerDown={(e) => e.stopPropagation()} onPointerUp={(e) => e.stopPropagation()}
            className="text-slate-400 hover:text-slate-200 max-md:grid max-md:h-8 max-md:w-6 max-md:place-items-center"><X size={16} /></button>
        </div>
      </header>
      <div className={cn("flex-1 overflow-y-auto overscroll-contain p-3", mobile && sheet === "peek" && "hidden")}>
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
