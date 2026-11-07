import { useRef, useState, type KeyboardEvent } from "react";
import {
  flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { CrashFeature } from "@/types/api";
import { useUiStore } from "@/stores/useUiStore";
import { cn, SEVERITY_LABELS, severityClass } from "@/components/ui";
import { fmtDateTime } from "@/lib/dates";

const ROW_HEIGHT = 30;

const columns: ColumnDef<CrashFeature>[] = [
  // Se ordena por el texto ISO (orden cronológico) y se muestra legible
  { id: "date", header: "Fecha", accessorFn: (r) => r.properties.date, size: 150, cell: (c) => fmtDateTime(String(c.getValue())) },
  {
    id: "severity", header: "Severidad", accessorFn: (r) => r.properties.severity, size: 90,
    cell: (c) => {
      const s = c.getValue() as 0 | 1 | 2;
      return <span className={cn("rounded-full px-2 py-0.5 text-[10px] font-semibold", severityClass(s))}>{SEVERITY_LABELS[s]}</span>;
    },
  },
  { id: "street", header: "Ubicación", accessorFn: (r) => r.properties.street, size: 220 },
  { id: "crash_type", header: "Tipo", accessorFn: (r) => r.properties.crash_type ?? "", size: 170 },
  { id: "cause", header: "Causa", accessorFn: (r) => r.properties.cause ?? "", size: 230 },
  { id: "injuries", header: "Lesion.", accessorFn: (r) => r.properties.injuries, size: 60 },
  { id: "fatal", header: "Fatal", accessorFn: (r) => r.properties.fatal, size: 50 },
  { id: "weather", header: "Clima", accessorFn: (r) => r.properties.weather ?? "", size: 110 },
  { id: "workzone", header: "Obra", accessorFn: (r) => (r.properties.workzone ? "Sí" : "No"), size: 50 },
];

const ARIA_SORT = { asc: "ascending", desc: "descending" } as const;

/**
 * Tabla virtualizada: con 10.000 filas en memoria sólo se renderizan las ~30 filas
 * visibles (más un pequeño overscan), manteniendo el desplazamiento a 60 FPS.
 * Accesible con teclado: Tab llega a las filas; Enter o Espacio ubica el siniestro en el mapa,
 * y las flechas arriba/abajo recorren las filas.
 */
export function VirtualCrashTable({ rows, height = 260 }: { rows: CrashFeature[]; height?: number }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const selectCrash = useUiStore((s) => s.selectCrash);
  const selectedId = useUiStore((s) => s.selectedCrashId);
  const table = useReactTable({
    data: rows,
    columns,
    state: { sorting },
    onSortingChange: setSorting,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getRowId: (r) => r.properties.id,
  });
  const tableRows = table.getRowModel().rows;
  const parentRef = useRef<HTMLDivElement>(null);
  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 6,
    initialRect: { width: 1000, height },
  });
  const totalWidth = columns.reduce((a, c) => a + (c.size ?? 100), 0);

  const select = (f: CrashFeature) => selectCrash(f.properties.id, f.geometry.coordinates as [number, number], true);
  const onRowKey = (e: KeyboardEvent<HTMLDivElement>, index: number, f: CrashFeature) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      select(f);
    } else if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const next = Math.min(tableRows.length - 1, Math.max(0, index + (e.key === "ArrowDown" ? 1 : -1)));
      virtualizer.scrollToIndex(next);
      requestAnimationFrame(() => parentRef.current?.querySelector<HTMLElement>(`[data-index="${next}"]`)?.focus());
    }
  };

  return (
    <div ref={parentRef} className="overflow-auto" style={{ height }} data-testid="virtual-table"
      role="table" aria-label="Siniestros de la ventana visible" aria-rowcount={tableRows.length + 1}>
      <div style={{ width: totalWidth, minWidth: "100%" }}>
        <div role="rowgroup" className="sticky top-0 z-10 border-b border-slate-800 bg-slate-950">
          <div role="row" aria-rowindex={1} className="flex text-[11px] font-semibold text-slate-400">
            {table.getHeaderGroups()[0].headers.map((h) => {
              const sorted = h.column.getIsSorted();
              return (
                <div key={h.id} role="columnheader" aria-sort={sorted ? ARIA_SORT[sorted] : "none"} style={{ width: h.getSize() }} className="shrink-0">
                  <button onClick={h.column.getToggleSortingHandler()}
                    className="flex w-full items-center gap-1 px-2 py-1.5 text-left hover:text-slate-200">
                    {flexRender(h.column.columnDef.header, h.getContext())}
                    {sorted === "asc" && <ArrowUp size={10} aria-hidden="true" />}
                    {sorted === "desc" && <ArrowDown size={10} aria-hidden="true" />}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
        <div role="rowgroup" style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const row = tableRows[vi.index];
            const f = row.original;
            const selected = selectedId === f.properties.id;
            return (
              <div
                key={row.id}
                role="row"
                aria-rowindex={vi.index + 2}
                aria-current={selected || undefined}
                data-index={vi.index}
                tabIndex={0}
                onClick={() => select(f)}
                onKeyDown={(e) => onRowKey(e, vi.index, f)}
                className={cn("absolute left-0 flex w-full cursor-pointer items-center border-b border-slate-900 text-[11px] text-slate-300 outline-none hover:bg-slate-800/60 focus-visible:bg-slate-800 focus-visible:ring-1 focus-visible:ring-inset focus-visible:ring-cyan-500",
                  selected && "bg-cyan-900/40")}
                style={{ height: ROW_HEIGHT, transform: `translateY(${vi.start}px)` }}
              >
                {row.getVisibleCells().map((cell) => (
                  <div key={cell.id} role="cell" className="shrink-0 truncate px-2" style={{ width: cell.column.getSize() }}>
                    {flexRender(cell.column.columnDef.cell, cell.getContext())}
                  </div>
                ))}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
