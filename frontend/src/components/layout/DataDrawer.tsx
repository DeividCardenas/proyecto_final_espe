import { X } from "lucide-react";
import { useQueryFilters, useViewportCrashes, VIEWPORT_LIMIT } from "@/hooks/useViewportCrashes";
import { useUiStore } from "@/stores/useUiStore";
import { VirtualCrashTable } from "@/components/table/VirtualCrashTable";
import { TableExportBar } from "@/components/table/TableExportBar";

export function DataDrawer() {
  const { drawerOpen, toggleDrawer } = useUiStore();
  const filters = useQueryFilters();
  const { data, isFetching } = useViewportCrashes(drawerOpen);
  if (!drawerOpen) return null;
  const rows = data?.features ?? [];
  return (
    <section className="hud-aside flex h-[320px] shrink-0 flex-col border-t border-slate-800 bg-slate-950/90">
      <header className="flex items-center justify-between px-3 py-1.5">
        <p className="text-xs text-slate-300">
          <b className="tabular-nums">{rows.length.toLocaleString("es")}</b> siniestros en la ventana visible
          {rows.length >= VIEWPORT_LIMIT && <span className="text-slate-500"> (los {VIEWPORT_LIMIT.toLocaleString("es")} más recientes)</span>}
          {isFetching && <span className="ml-2 text-cyan-400">actualizando…</span>}
        </p>
        <div className="flex items-center gap-2">
          <TableExportBar rows={rows} filters={filters} />
          <button onClick={toggleDrawer} aria-label="Cerrar tabla" className="text-slate-500 hover:text-slate-200"><X size={16} /></button>
        </div>
      </header>
      <VirtualCrashTable rows={rows} height={276} />
    </section>
  );
}
