import { useSyncExternalStore } from "react";

/** Mismo corte que el prefijo `md:` de Tailwind: por debajo de 768 px la interfaz pasa a modo móvil. */
export const MOBILE_QUERY = "(max-width: 767px)";

const media = () => (typeof window !== "undefined" && window.matchMedia ? window.matchMedia(MOBILE_QUERY) : null);

/** Lectura puntual (fuera de React: guía de uso, manejadores). */
export const isMobileViewport = () => !!media()?.matches;

function subscribe(cb: () => void) {
  const m = media();
  m?.addEventListener?.("change", cb);
  return () => m?.removeEventListener?.("change", cb);
}

/** true en pantallas de teléfono; se actualiza al girar el dispositivo o redimensionar. */
export function useIsMobile() {
  return useSyncExternalStore(subscribe, isMobileViewport, () => false);
}
