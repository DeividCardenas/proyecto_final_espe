import { Suspense } from "react";
import { X } from "lucide-react";
import { useQueryFilters, useViewportCrashes, VIEWPORT_LIMIT } from "@/hooks/useViewportCrashes";
import { useUiStore } from "@/stores/useUiStore";
import { TableExportBar } from "@/components/table/TableExportBar";
import { ErrorBoundary } from "@/components/ErrorBoundary";
import { QueryError } from "@/components/ui";
import { lazyNamed } from "@/lib/lazyNamed";

// La tabla (TanStack Table + Virtual) se descarga sólo al abrir el cajón
const VirtualCrashTable = lazyNamed(() => import("@/components/table/VirtualCrashTable"), "VirtualCrashTable");

export function DataDrawer() {
  const drawerOpen = useUiStore((s) => s.drawerOpen);
  if (!drawerOpen) return null;
  return <DrawerContent />;
}

function DrawerContent() {
  const toggleDrawer = useUiStore((s) => s.toggleDrawer);
  const filters = useQueryFilters();
  const { data, isFetching, isError, refetch } = useViewportCrashes(true);
  const rows = data?.features ?? [];
  return (
    <section aria-label="Tabla de siniestros" className="hud-aside flex h-[320px] shrink-0 flex-col border-t border-slate-800 bg-slate-950/90">
      <header className="flex flex-wrap items-center justify-between gap-2 px-3 py-1.5">
        <p className="text-xs text-slate-300" aria-live="polite">
          <b className="tabular-nums">{rows.length.toLocaleString("es")}</b> siniestros en la ventana visible
          {rows.length >= VIEWPORT_LIMIT && <span className="text-slate-400"> (los {VIEWPORT_LIMIT.toLocaleString("es")} más recientes)</span>}
          {isFetching && <span className="ml-2 text-cyan-400">actualizando…</span>}
        </p>
        <div className="flex items-center gap-2">
          <TableExportBar rows={rows} filters={filters} />
          <button onClick={toggleDrawer} aria-label="Cerrar tabla" className="text-slate-400 hover:text-slate-200"><X size={16} /></button>
        </div>
      </header>
      {isError ? (
        <div className="px-3"><QueryError what="los siniestros de la zona" onRetry={() => void refetch()} /></div>
      ) : (
        <ErrorBoundary area="Tabla">
          <Suspense fallback={<p className="px-3 text-xs text-slate-400">Cargando tabla…</p>}>
            <VirtualCrashTable rows={rows} height={276} />
          </Suspense>
        </ErrorBoundary>
      )}
    </section>
  );
}
