import { useQuery } from "@tanstack/react-query";
import { Activity, BarChart3, Brain, Gauge, Table2 } from "lucide-react";
import { api } from "@/services/api";
import { useUiStore, type PanelTab } from "@/stores/useUiStore";
import { cn } from "@/components/ui";

interface Health {
  status: string;
  model: { loaded: boolean; algorithm: string | null; mode: string };
}

const TABS: { id: PanelTab; label: string; icon: typeof BarChart3 }[] = [
  { id: "analytics", label: "Analítica", icon: BarChart3 },
  { id: "simulator", label: "Simulador", icon: Gauge },
  { id: "model", label: "Modelo", icon: Brain },
];

export function Header() {
  const { activeTab, setTab, panelOpen, togglePanel, drawerOpen, toggleDrawer } = useUiStore();
  const health = useQuery({
    queryKey: ["health"],
    queryFn: () => api.get<Health>("/health").then((r) => r.data),
    refetchInterval: 30_000,
  });
  const up = health.data?.status === "UP";
  return (
    <header className="flex h-12 shrink-0 items-center justify-between border-b border-slate-800 bg-slate-950 px-4">
      <div className="flex items-center gap-3">
        <span className="grid h-7 w-7 place-items-center rounded-lg bg-red-600"><Activity size={16} className="text-white" /></span>
        <div className="leading-tight">
          <h1 className="text-sm font-semibold text-slate-100">Chicago Road Risk</h1>
          <p className="text-[10px] text-slate-500">Riesgo vial geoespacial · Big Data & ML</p>
        </div>
      </div>
      <nav className="flex items-center gap-1">
        {TABS.map(({ id, label, icon: Icon }) => (
          <button
            key={id}
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
          className={cn("flex items-center gap-1.5 rounded-lg px-3 py-1.5 text-xs text-slate-400 hover:text-slate-100",
            drawerOpen && "bg-slate-800 text-slate-100")}
        >
          <Table2 size={14} />Tabla
        </button>
      </nav>
      <div className="flex items-center gap-2 text-[11px] text-slate-400" title="Estado del backend">
        <span className={cn("h-2 w-2 rounded-full", up ? "bg-emerald-400" : health.isLoading ? "bg-slate-500" : "bg-red-500")} />
        {up ? `API en línea · ${health.data?.model.loaded ? `modelo ${health.data.model.algorithm}` : "modo heurístico"}` : "API no disponible"}
      </div>
    </header>
  );
}
