import { useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { useUiStore } from "@/stores/useUiStore";
import { cn } from "@/components/ui";
import { TABS } from "@/components/layout/Header";
import { setHelpHints, startFullTour, startSectionTour } from "./guide";

/** Menú «Ayuda»: recorrido completo, guía de la sección abierta y puntos de ayuda opcionales. */
export function HelpMenu() {
  const { activeTab, helpHints, setHelpHints: setHints } = useUiStore();
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false);
    };
    window.addEventListener("mousedown", close);
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  // Los puntos de ayuda viven fuera de React (Driver.js): se sincronizan con el store
  useEffect(() => {
    setHelpHints(helpHints);
    return () => setHelpHints(false);
  }, [helpHints]);

  const section = TABS.find((t) => t.id === activeTab)?.label ?? "";
  const item = "block w-full rounded px-2 py-1.5 text-left hover:bg-slate-800";
  const pick = (fn: () => void) => () => {
    setOpen(false);
    fn();
  };

  return (
    <div ref={ref} className="relative" data-tour="nav-help">
      <button onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open}
        className={cn("flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-400 hover:text-slate-100", open && "bg-slate-800 text-slate-100")}>
        <HelpCircle size={14} />Ayuda
      </button>
      {open && (
        <div role="menu" className="hud-panel absolute right-0 top-10 z-50 w-72 border border-slate-700 bg-slate-900 p-1.5 text-xs shadow-2xl">
          <button role="menuitem" className={item} onClick={pick(startFullTour)}>
            <span className="block font-semibold text-slate-100">Recorrido completo</span>
            <span className="block text-[11px] text-slate-500">Cada parte: qué hace, qué significa y cómo se hizo (1 min)</span>
          </button>
          <button role="menuitem" className={item} onClick={pick(() => startSectionTour(activeTab))}>
            <span className="block font-semibold text-slate-100">Guía de «{section}»</span>
            <span className="block text-[11px] text-slate-500">Sólo la sección abierta</span>
          </button>
          <button role="menuitemcheckbox" aria-checked={helpHints} className={item} onClick={pick(() => setHints(!helpHints))}>
            <span className="block font-semibold text-slate-100">{helpHints ? "Ocultar" : "Mostrar"} puntos de ayuda</span>
            <span className="block text-[11px] text-slate-500">Marcas «?» sobre la pantalla; ábrelas cuando quieras</span>
          </button>
        </div>
      )}
    </div>
  );
}
