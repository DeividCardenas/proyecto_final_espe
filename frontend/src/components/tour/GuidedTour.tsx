import { useEffect, useState } from "react";
import { ArrowRight, X } from "lucide-react";
import { useTopSegments } from "@/hooks/useTopSegments";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore } from "@/stores/useUiStore";
import { fmtPct } from "@/components/ui";

export const TOUR_KEY = "chicago-road-risk-tour-done";

function tourDone(): boolean {
  try {
    return localStorage.getItem(TOUR_KEY) === "1";
  } catch {
    return false; // sin almacenamiento: se ofrece el recorrido, que siempre se puede saltar
  }
}

function markDone() {
  try {
    localStorage.setItem(TOUR_KEY, "1");
  } catch {
    /* preferencia sólo en memoria */
  }
}

/**
 * Función explicativa (narrativa secuencial) sobre una interfaz exploratoria:
 * tres pasos — Dónde, Por qué, Qué hacer — que se ofrecen sólo en la primera visita,
 * se pueden saltar y se reabren desde «Recorrido» en la cabecera.
 */
export function GuidedTour() {
  const { tourOpen, setTourOpen, setTab, selectSegment, focus } = useUiStore();
  const layers = useMapStore((s) => s.layers);
  const toggleLayer = useMapStore((s) => s.toggleLayer);
  const { metrics, segments } = useTopSegments();
  const [step, setStep] = useState(0);

  // Primera visita: se abre solo
  useEffect(() => {
    if (!tourDone()) setTourOpen(true);
  }, [setTourOpen]);

  useEffect(() => {
    if (!tourOpen) return;
    setStep(0);
    setTab("segments");
  }, [tourOpen, setTab]);

  if (!tourOpen) return null;

  const m = metrics.data;
  const win = m ? m.comparison[m.winner] : null;
  const first = segments.data?.features[0];

  const steps = [
    {
      title: "Dónde",
      text: "Los círculos del mapa son las cuadras con mayor probabilidad de riesgo Alto en los próximos 12 meses. Más grande y más rojo significa más prioritaria.",
      enter: () => {
        setTab("segments");
        if (!layers.segments) toggleLayer("segments");
      },
    },
    {
      title: "Por qué",
      text: "Al hacer clic en una cuadra verás su probabilidad, cómo se compara con el resto de Chicago y qué variables la explican. Te mostramos la primera de la lista.",
      enter: () => {
        if (!first) return;
        const coords = first.geometry.coordinates as [number, number];
        selectSegment({ ...first.properties, coordinates: coords });
        focus(coords);
      },
    },
    {
      title: "Qué hacer",
      text: win
        ? `En la validación, el 10% de cuadras señaladas concentró el ${fmtPct(win.top10_capture_severe, 0)} de los siniestros graves: es la lista para priorizar intervenciones. En Explorar verás cuándo y en qué condiciones ocurren, y en Simular podrás probar escenarios.`
        : "Usa la lista de Priorizar para decidir dónde intervenir primero. En Explorar verás cuándo y en qué condiciones ocurren, y en Simular podrás probar escenarios.",
      enter: () => undefined,
    },
  ];

  const close = () => {
    markDone();
    setTourOpen(false);
  };
  const go = (i: number) => {
    steps[i].enter();
    setStep(i);
  };
  const s = steps[step];

  return (
    <div role="dialog" aria-label="Recorrido guiado" aria-live="polite" data-testid="guided-tour"
      className="hud-panel absolute bottom-6 left-1/2 z-20 w-[min(440px,calc(100%-2rem))] -translate-x-1/2 rounded-xl border border-cyan-700/60 bg-slate-900/95 p-4 shadow-2xl backdrop-blur">
      <div className="mb-1 flex items-center justify-between">
        <p className="text-[10px] uppercase tracking-wider text-slate-500">Paso {step + 1} de {steps.length}</p>
        <button onClick={close} aria-label="Saltar recorrido" className="text-slate-500 hover:text-slate-200"><X size={14} /></button>
      </div>
      <h2 className="hud-title text-base font-semibold text-slate-100">{s.title}</h2>
      <p className="mt-1 text-[13px] leading-snug text-slate-300">{s.text}</p>
      <div className="mt-3 flex items-center justify-between">
        <div className="flex gap-1.5" aria-hidden>
          {steps.map((_, i) => <i key={i} className={`h-1.5 w-6 rounded-full ${i <= step ? "bg-cyan-500" : "bg-slate-700"}`} />)}
        </div>
        <div className="flex items-center gap-3">
          <button onClick={close} className="text-xs text-slate-400 hover:text-slate-100">Saltar</button>
          {step < steps.length - 1 ? (
            <button onClick={() => go(step + 1)}
              className="flex items-center gap-1 rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500">
              Siguiente <ArrowRight size={13} />
            </button>
          ) : (
            <button onClick={close} className="rounded-lg bg-cyan-600 px-3 py-1.5 text-xs font-semibold text-white hover:bg-cyan-500">
              Empezar
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
