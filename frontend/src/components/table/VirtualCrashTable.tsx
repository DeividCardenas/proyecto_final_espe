import { useMemo, useRef, useState } from "react";
import {
  flexRender, getCoreRowModel, getSortedRowModel, useReactTable, type ColumnDef, type SortingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import { ArrowDown, ArrowUp } from "lucide-react";
import type { CrashFeature } from "@/types/api";
import { useUiStore } from "@/stores/useUiStore";
import { cn, SEVERITY_LABELS, severityClass } from "@/components/ui";

const ROW_HEIGHT = 30;

const columns: ColumnDef<CrashFeature>[] = [
  { id: "date", header: "Fecha", accessorFn: (r) => r.properties.date, size: 130, cell: (c) => String(c.getValue()).replace("T", " ") },
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

/**
 * Tabla virtualizada: con 10.000 filas en memoria sólo se renderizan las ~30 filas
 * visibles (más un pequeño overscan), manteniendo el desplazamiento a 60 FPS.
 */
export function VirtualCrashTable({ rows, height = 260 }: { rows: CrashFeature[]; height?: number }) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const selectCrash = useUiStore((s) => s.selectCrash);
  const selectedId = useUiStore((s) => s.selectedCrashId);
  const data = useMemo(() => rows, [rows]);
  const table = useReactTable({
    data,
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

  return (
    <div ref={parentRef} className="overflow-auto" style={{ height }} data-testid="virtual-table">
      <div style={{ width: totalWidth, minWidth: "100%" }}>
        <div className="sticky top-0 z-10 flex border-b border-slate-800 bg-slate-950 text-[11px] font-semibold text-slate-400">
          {table.getHeaderGroups()[0].headers.map((h) => (
            <button key={h.id} style={{ width: h.getSize() }} onClick={h.column.getToggleSortingHandler()}
              className="flex shrink-0 items-center gap-1 px-2 py-1.5 text-left hover:text-slate-200">
              {flexRender(h.column.columnDef.header, h.getContext())}
              {h.column.getIsSorted() === "asc" && <ArrowUp size={10} />}
              {h.column.getIsSorted() === "desc" && <ArrowDown size={10} />}
            </button>
          ))}
        </div>
        <div style={{ height: virtualizer.getTotalSize(), position: "relative" }}>
          {virtualizer.getVirtualItems().map((vi) => {
            const row = tableRows[vi.index];
            const f = row.original;
            return (
              <div
                key={row.id}
                role="row"
                onClick={() => selectCrash(f.properties.id, f.geometry.coordinates as [number, number], true)}
                className={cn("absolute left-0 flex w-full cursor-pointer items-center border-b border-slate-900 text-[11px] text-slate-300 hover:bg-slate-800/60",
                  selectedId === f.properties.id && "bg-cyan-900/40")}
                style={{ height: ROW_HEIGHT, transform: `translateY(${vi.start}px)` }}
              >
                {row.getVisibleCells().map((cell) => (
                  <div key={cell.id} className="shrink-0 truncate px-2" style={{ width: cell.column.getSize() }}>
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
