import { useState } from "react";
import { Compass, X } from "lucide-react";
import { guideSeen, markGuideSeen, startFullTour } from "./launcher";

/**
 * Invitación discreta de la primera visita: no tapa el mapa ni bloquea nada.
 * Si se descarta (o se hace el recorrido) no vuelve a aparecer; la guía sigue en «Ayuda».
 */
export function GuideInvite() {
  const [visible, setVisible] = useState(() => !guideSeen());
  if (!visible) return null;
  const dismiss = () => {
    markGuideSeen();
    setVisible(false);
  };
  return (
    <div role="status" data-testid="guide-invite"
      className="hud-panel absolute bottom-6 right-3 z-20 w-72 rounded-xl border border-slate-700 bg-slate-900/95 p-3 shadow-xl backdrop-blur">
      <div className="flex items-start gap-2">
        <Compass size={16} className="mt-0.5 shrink-0 text-cyan-300" />
        <div className="min-w-0 flex-1">
          <p className="text-[13px] font-semibold text-slate-100">¿Primera vez aquí?</p>
          <p className="mt-0.5 text-[12px] leading-snug text-slate-400">
            Un recorrido de un minuto explica cada parte: qué hace, qué significa y cómo se hizo.
          </p>
          <div className="mt-2 flex items-center gap-3">
            <button onClick={() => { setVisible(false); void startFullTour(); }}
              className="rounded-lg bg-cyan-600 px-3 py-1 text-xs font-semibold text-white hover:bg-cyan-500">
              Ver recorrido
            </button>
            <button onClick={dismiss} className="text-xs text-slate-400 hover:text-slate-100">Ahora no</button>
          </div>
        </div>
        <button onClick={dismiss} aria-label="Cerrar invitación" className="text-slate-400 hover:text-slate-200"><X size={14} /></button>
      </div>
    </div>
  );
}
