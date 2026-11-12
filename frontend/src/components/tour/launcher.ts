/**
 * Punto de entrada liviano a la guía: Driver.js (y su CSS) se descargan sólo cuando el
 * usuario pide un recorrido o los puntos de ayuda, no en la carga inicial.
 */
import type { PanelTab } from "@/stores/useUiStore";

export const GUIDE_SEEN_KEY = "chicago-road-risk-guide-seen";

export function guideSeen(): boolean {
  try {
    return localStorage.getItem(GUIDE_SEEN_KEY) === "1";
  } catch {
    return false;
  }
}

export function markGuideSeen() {
  try {
    localStorage.setItem(GUIDE_SEEN_KEY, "1");
  } catch {
    /* preferencia sólo en memoria */
  }
}

const loadGuide = () => import("./guide");
// Las órdenes se encadenan para respetar el orden aunque el módulo tarde en llegar
let queue: Promise<unknown> = Promise.resolve();
const enqueue = (fn: (m: Awaited<ReturnType<typeof loadGuide>>) => void) => {
  queue = queue.then(loadGuide).then(fn).catch((e) => {
    if (import.meta.env.MODE !== "test") console.error("[guía] no se pudo cargar", e);
  });
  return queue;
};

export const startFullTour = () => enqueue((m) => m.startFullTour());
export const startSectionTour = (tab: PanelTab) => enqueue((m) => m.startSectionTour(tab));
export const setHelpHints = (on: boolean) => enqueue((m) => m.setHelpHints(on));
