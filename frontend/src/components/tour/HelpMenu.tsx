import { useCallback, useEffect, useRef, useState } from "react";
import { HelpCircle } from "lucide-react";
import { useShallow } from "zustand/react/shallow";
import { useUiStore } from "@/stores/useUiStore";
import { cn } from "@/components/ui";
import { TABS } from "@/components/layout/tabs";
import { setHelpHints, startFullTour, startSectionTour } from "./launcher";
import { useDismiss } from "@/hooks/useDismiss";

/** Menú «Ayuda»: recorrido completo, guía de la sección abierta y puntos de ayuda opcionales. */
export function HelpMenu() {
  const { activeTab, helpHints, setHints } = useUiStore(
    useShallow((s) => ({ activeTab: s.activeTab, helpHints: s.helpHints, setHints: s.setHelpHints })),
  );
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);
  const close = useCallback(() => setOpen(false), []);
  useDismiss(open, ref, close);

  // Los puntos de ayuda viven fuera de React (Driver.js): se sincronizan con el store.
  // Sólo se carga Driver.js cuando el usuario los activa.
  const hintsShown = useRef(false);
  useEffect(() => {
    if (!helpHints && !hintsShown.current) return;
    hintsShown.current = helpHints;
    void setHelpHints(helpHints);
  }, [helpHints]);
  useEffect(() => () => {
    if (hintsShown.current) void setHelpHints(false);
  }, []);

  const section = TABS.find((t) => t.id === activeTab)?.label ?? "";
  const item = "block w-full rounded px-2 py-1.5 text-left hover:bg-slate-800 focus-visible:bg-slate-800";
  const pick = (fn: () => void) => () => {
    setOpen(false);
    fn();
  };

  return (
    <div ref={ref} className="relative" data-tour="nav-help">
      <button onClick={() => setOpen((v) => !v)} aria-haspopup="menu" aria-expanded={open} aria-label="Ayuda" title="Ayuda"
        className={cn("flex items-center gap-1.5 rounded-lg px-2 py-1.5 text-xs text-slate-400 hover:text-slate-100", open && "bg-slate-800 text-slate-100")}>
        <HelpCircle size={14} /><span className="hidden lg:inline">Ayuda</span>
      </button>
      {open && (
        <div role="menu" className="hud-panel absolute right-0 top-10 z-50 w-72 border border-slate-700 bg-slate-900 p-1.5 text-xs shadow-2xl">
          <button role="menuitem" className={item} onClick={pick(() => void startFullTour())}>
            <span className="block font-semibold text-slate-100">Recorrido completo</span>
            <span className="block text-[11px] text-slate-400">Cada parte: qué hace, qué significa y cómo se hizo (1 min)</span>
          </button>
          <button role="menuitem" className={item} onClick={pick(() => void startSectionTour(activeTab))}>
            <span className="block font-semibold text-slate-100">Guía de «{section}»</span>
            <span className="block text-[11px] text-slate-400">Sólo la sección abierta</span>
          </button>
          <button role="menuitemcheckbox" aria-checked={helpHints} className={item} onClick={pick(() => setHints(!helpHints))}>
            <span className="block font-semibold text-slate-100">{helpHints ? "Ocultar" : "Mostrar"} puntos de ayuda</span>
            <span className="block text-[11px] text-slate-400">Marcas «?» sobre la pantalla; ábrelas cuando quieras</span>
          </button>
        </div>
      )}
    </div>
  );
}
