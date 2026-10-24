import type { ReactNode } from "react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import type { Severity } from "@/types/api";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export const SEVERITY_LABELS: Record<Severity, string> = { 0: "Bajo", 1: "Moderado", 2: "Crítico" };

export function severityClass(s: Severity) {
  return s === 2 ? "bg-red-600/90 text-white" : s === 1 ? "bg-yellow-400/90 text-slate-900" : "bg-sky-500/80 text-white";
}

export function Card({ title, children, className, right }: { title?: string; children: ReactNode; className?: string; right?: ReactNode }) {
  return (
    <section className={cn("rounded-xl border border-slate-800 bg-slate-900/80 p-3", className)}>
      {title && (
        <header className="mb-2 flex items-center justify-between">
          <h3 className="text-[11px] font-semibold uppercase tracking-wider text-slate-400">{title}</h3>
          {right}
        </header>
      )}
      {children}
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
