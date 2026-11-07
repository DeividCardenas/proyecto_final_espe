import { useQuery } from "@tanstack/react-query";
import { Activity, SlidersHorizontal, Table2 } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { api } from "@/services/api";
import { useUiStore } from "@/stores/useUiStore";
import { activeFilterCount, useFilterStore } from "@/stores/useFilterStore";
import { cn } from "@/components/ui";
import { useTheme } from "@/stores/useThemeStore";
import { ThemeSwitcher } from "./ThemeSwitcher";
import { HelpMenu } from "@/components/tour/HelpMenu";
import { TABS } from "./tabs";

export { TABS } from "./tabs";

interface Health {
  status: string;
  model: { loaded: boolean; algorithm: string | null; mode: string };
}

/*
 * En pantallas medianas (< 1280 px) los botones muestran sólo el icono, con el nombre en
 * aria-label y title, para que la barra no se desborde.
 */
export function Header() {
  const { activeTab, setTab, panelOpen, togglePanel, drawerOpen, toggleDrawer, filtersOpen, toggleFilters } = useUiStore(
    useShallow((s) => ({
      activeTab: s.activeTab, setTab: s.setTab, panelOpen: s.panelOpen, togglePanel: s.togglePanel,
      drawerOpen: s.drawerOpen, toggleDrawer: s.toggleDrawer, filtersOpen: s.filtersOpen, toggleFilters: s.toggleFilters,
    })),
  );
  // Sólo el número de filtros activos: no se repinta la cabecera al arrastrar el rango horario
  const filterCount = useFilterStore((s) => activeFilterCount(s));
  const health = useQuery({
    queryKey: ["health"],
    queryFn: ({ signal }) => api.get<Health>("/health", { signal }).then((r) => r.data),
    refetchInterval: 30_000,
  });
  const up = health.data?.status === "UP";
  const theme = useTheme();
  const navBtn = "flex items-center gap-1.5 rounded-lg px-2.5 py-1.5 text-xs text-slate-400 hover:text-slate-100 xl:px-3";
  return (
    <header className="hud-header relative z-10 flex h-12 shrink-0 items-center justify-between gap-3 border-b border-slate-800 bg-slate-950 px-4">
      <div className="flex min-w-0 items-center gap-3">
        <span className="grid h-7 w-7 shrink-0 place-items-center rounded-lg" style={{ background: theme.swatch[2] }}><Activity size={16} className="text-white" /></span>
        <div className="min-w-0 leading-tight">
          <h1 className="hud-title hud-logo-text truncate text-sm font-semibold text-slate-100">Chicago Road Risk</h1>
          <p className="hidden truncate font-mono text-[10px] text-slate-400 lg:block">{theme.headerSub}</p>
        </div>
      </div>
      <nav className="flex items-center gap-1" aria-label="Secciones">
        <button
          onClick={toggleFilters}
          data-tour="nav-filters"
          aria-pressed={filtersOpen}
          aria-label={filterCount > 0 ? `Filtros (${filterCount} activos)` : "Filtros"}
          title="Filtros y capas"
          className={cn("mr-1 flex items-center gap-1.5 rounded-lg border border-slate-700 px-2.5 py-1.5 text-xs text-slate-300 hover:text-slate-100 xl:mr-2 xl:px-3",
            filtersOpen && "bg-slate-800 text-slate-100")}
        >
          <SlidersHorizontal size={14} /><span className="hidden xl:inline">Filtros</span>
          {filterCount > 0 && (
            <span className="grid h-4 min-w-4 place-items-center rounded-full bg-cyan-600 px-1 text-[10px] font-semibold text-white"
              aria-hidden="true">{filterCount}</span>
          )}
        </button>
        {TABS.map(({ id, label, icon: Icon, hint }) => (
          <button
            key={id}
            data-tour={`nav-${id}`}
            title={`${label}: ${hint}`}
            aria-label={label}
            aria-pressed={activeTab === id && panelOpen}
            onClick={() => (activeTab === id && panelOpen ? togglePanel() : setTab(id))}
            className={cn(navBtn, activeTab === id && panelOpen && "bg-slate-800 text-slate-100")}
          >
            <Icon size={14} /><span className="hidden lg:inline">{label}</span>
          </button>
        ))}
        <button
          onClick={toggleDrawer}
          data-tour="nav-table"
          title="Tabla: siniestros de la zona visible, exportables"
          aria-label="Tabla"
          aria-pressed={drawerOpen}
          className={cn(navBtn, drawerOpen && "bg-slate-800 text-slate-100")}
        >
          <Table2 size={14} /><span className="hidden lg:inline">Tabla</span>
        </button>
      </nav>
      <div className="flex shrink-0 items-center gap-2 xl:gap-3">
        <HelpMenu />
        <ThemeSwitcher />
        {/* Estado del servicio: discreto; el detalle técnico queda en el tooltip */}
        <span
          role="status"
          className={cn("h-2 w-2 rounded-full", up ? "bg-emerald-400" : health.isLoading ? "bg-slate-500" : "bg-red-500")}
          title={up ? `Datos en línea · ${health.data?.model.loaded ? `modelo ${health.data.model.algorithm}` : "modo heurístico"}` : "Sin conexión con el servidor de datos"}
          aria-label={up ? "Datos en línea" : health.isLoading ? "Comprobando conexión" : "Sin conexión con el servidor de datos"}
        />
      </div>
    </header>
  );
}
