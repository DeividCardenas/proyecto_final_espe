import { lazy, type ComponentType } from "react";

const RELOAD_KEY = "chicago-road-risk-chunk-reload";

/**
 * React.lazy para exportaciones con nombre, con un reintento: si el chunk ya no existe
 * (pestaña abierta antes de un despliegue nuevo) se recarga la página una sola vez; si
 * vuelve a fallar, el error llega al ErrorBoundary en vez de quedar la pantalla en blanco.
 */
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export function lazyNamed<M extends Record<K, ComponentType<any>>, K extends keyof M & string>(
  load: () => Promise<M>,
  key: K,
) {
  return lazy(async () => {
    try {
      const m = await load();
      try { sessionStorage.removeItem(RELOAD_KEY); } catch { /* sin almacenamiento */ }
      return { default: m[key] as M[K] };
    } catch (e) {
      let reloaded = true;
      try {
        reloaded = sessionStorage.getItem(RELOAD_KEY) === "1";
        if (!reloaded) sessionStorage.setItem(RELOAD_KEY, "1");
      } catch { /* sin almacenamiento: no se recarga en bucle */ }
      if (!reloaded) {
        window.location.reload();
        return new Promise<never>(() => {});
      }
      throw e;
    }
  });
}
