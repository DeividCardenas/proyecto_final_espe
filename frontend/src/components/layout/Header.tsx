import { useQuery } from "@tanstack/react-query";
import { Activity, BarChart3, Brain, Gauge, ListOrdered, SlidersHorizontal, Table2 } from "lucide-react";
import { api } from "@/services/api";
import { useUiStore, type PanelTab } from "@/stores/useUiStore";
import { activeFilterCount, useFilterStore } from "@/stores/useFilterStore";
import { cn } from "@/components/ui";
import { useTheme } from "@/stores/useThemeStore";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { HelpMenu } from "@/components/tour/HelpMenu";

interface Health {
  status: string;
  model: { loaded: boolean; algorithm: string | null; mode: string };
}

/** Única navegación de la app, nombrada por lo que hace el usuario en cada sección. */
export const TABS: { id: PanelTab; label: string; icon: typeof BarChart3; hint: string }[] = [
  { id: "segments", label: "Priorizar", icon: ListOrdered, hint: "Cuadras con mayor riesgo previsto" },
  { id: "analytics", label: "Explorar", icon: BarChart3, hint: "Cuándo y en qué condiciones ocurren" },
  { id: "simulator", label: "Simular", icon: Gauge, hint: "Probar un escenario en un punto" },
  { id: "model", label: "Modelo", icon: Brain, hint: "Cómo se validó el modelo" },
];

export function Header() {
  const { activeTab, setTab, panelOpen, togglePanel, drawerOpen, toggleDrawer, filtersOpen, toggleFilters } = useUiStore();
  const filterCount = activeFilterCount(useFilterStore());
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<Health>("/health").then((r) => r.data),
    refetchInterval: 30_000,
  });
  const up = health.data?.status === "UP";
  const theme = useTheme();
  return (
    <header className="hud-header relative z-10 flex h-12 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950 px-4">
      <div className="flex items-center gap-3">
        <span className="grid h-7 w-7 place-items-center rounded-lg" style={{ background: theme.swatch[2] }}><Activity size={16} className="text-white" /></span>
        <div className="leading-tight">
          <h1 className="hud-title hud-logo-text text-sm font-semibold text-slate-100">Chicago Road Risk</h1>
          <p className="font-mono text-[10px] text-slate-500">{theme.headerSub}</p>
        </div>
      </div>
      <nav className="flex items-center gap-1" aria-label="Secciones">
        <button
          onClick={toggleFilters}
          data-tour="nav-filters"
          aria-pressed={filtersOpen}
          className={cn("mr-2 flex items-center gap-1.5 rounded-lg border border-slate-700 px-3 py-1.5 text-xs text-slate-300 hover:text-slate-100",
            filtersOpen && "bg-slate-800 text-slate-100")}
        >
          <SlidersHorizontal size={14} />Filtros
          {filterCount > 0 && (
            <span className="grid h-4 min-w-4 place-items-center rounded-full bg-cyan-600 px-1 text-[10px] font-semibold text-white"
              aria-label={`${filterCount} filtros activos`}>{filterCount}</span>
          )}
        </button>
        {TABS.map(({ id, label, icon: Icon, hint }) => (
          <button
            key={id}
            data-tour={`nav-${id}`}
            title={hint}
            aria-pressed={activeTab === id && panelOpen}
            onClick={() => (activeTab === id && panelOpen ? togglePanel() : setTab(id))}
            className={cn(
              "flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-slate-100",
              activeTab === id && panelOpen && "bg-slate-800 text-slate-100",
            )}
          >
            <Icon size={14} />{label}
          </button>
        ))}
        <button
          onClick={toggleDrawer}
          data-tour="nav-table"
          title="Siniestros de la zona visible, exportables"
          aria-pressed={drawerOpen}
          className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-slate-100",
            drawerOpen && "bg-slate-800 text-slate-100")}
        >
          <Table2 size={14} />Tabla
        </button>
      </nav>
      <div className="flex items-center gap-3">
        <HelpMenu />
        <ThemeSwitcher />
        {/* Estado del servicio: discreto; el detalle técnico queda en el tooltip */}
        <span
          role="status"
          className={cn("h-2 w-2 rounded-full", up ? "bg-emerald-400" : health.isLoading ? "bg-slate-500" : "bg-red-500")}
          title={up ? `Datos en línea · ${health.data?.model.loaded ? `modelo ${health.data.model.algorithm}` : "modo heurístico"}` : "Sin conexión con el servidor de datos"}
          aria-label={up ? "Datos en línea" : "Sin conexión con el servidor de datos"}
        />
      </div>
    </header>
  );
}
