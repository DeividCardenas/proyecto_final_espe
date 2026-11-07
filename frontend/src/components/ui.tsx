import type { ReactNode } from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Severity } from "@/types/api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const SEVERITY_LABELS: Record<Severity, string> = { 0: "Bajo", 1: "Moderado", 2: "Crítico" };

export function severityClass(s: Severity) {
  return s === 2 ? "bg-red-600/90 text-white" : s === 1 ? "bg-amber-500/90 text-slate-900" : "bg-slate-500/80 text-white";
}

/**
 * Tarjeta del bento grid. `takeaway` es la lectura principal del gráfico (el dato
 * con su comparación) y `context` la unidad, el ámbito y el periodo.
 */
export function Card({ title, children, className, right, takeaway, context, hero, tourId }: {
  title?: string; children: ReactNode; className?: string; right?: ReactNode; takeaway?: ReactNode; context?: ReactNode;
  /** Tarjeta principal del bento: borde de acento y lectura más grande (lo primero que se mira) */
  hero?: boolean;
  /** Ancla para la guía de uso (data-tour) */
  tourId?: string;
}) {
  return (
    <section data-tour={tourId} className={cn("hud-panel h-full rounded-xl border border-slate-800 bg-slate-900/80 p-3", hero && "border-cyan-700/60", className)}>
      {title && (
        <header className="mb-1 flex items-center justify-between gap-2">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
          {right}
        </header>
      )}
      {takeaway && <p className={cn("mb-2 font-medium leading-snug text-slate-100", hero ? "text-[15px]" : "text-[13px]")}>{takeaway}</p>}
      {children}
      {context && <p className="mt-1.5 text-[10px] leading-snug text-slate-500">{context}</p>}
    </section>
  );
}

export function fmtNumber(n: number | null | undefined, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return "—";
  return n.toLocaleString("es", { maximumFractionDigits: digits, minimumFractionDigits: digits });
}

export function fmtPct(n: number | null | undefined, digits = 1) {
  if (n === null || n === undefined) return "—";
  return `${(n * 100).toLocaleString("es", { maximumFractionDigits: digits, minimumFractionDigits: digits })}%`;
}
