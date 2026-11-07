import { useEffect, useRef, useState, type RefObject } from "react";
import { Map as MLMap, type ErrorEvent as MLErrorEvent, type MapOptions, type StyleSpecification } from "maplibre-gl";

export const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

/**
 * Estilo de respaldo sin dependencias externas (sólo un fondo). Si CARTO no responde
 * (sin internet en una exposición, CDN caído), el mapa sigue mostrando las capas del
 * proyecto, que vienen de nuestra API. Las tipografías de las etiquetas de los clusters
 * se piden igual a CARTO: si tampoco llegan, sólo faltan esos números.
 */
export const FALLBACK_STYLE: StyleSpecification = {
  version: 8,
  name: "respaldo-local",
  glyphs: "https://tiles.basemaps.cartocdn.com/fonts/{fontstack}/{range}.pbf",
  sources: {},
  layers: [{ id: "background", type: "background", paint: { "background-color": "#0b1120" } }],
};

/** Tiempo máximo para recibir el estilo del mapa base antes de pasar al respaldo. */
export const BASEMAP_TIMEOUT_MS = 10_000;

/** Detección de WebGL2 (maplibregl.supported() fue retirado en MapLibre v3+). */
export function isWebGL2Supported(): boolean {
  try {
    const canvas = document.createElement("canvas");
    return !!canvas.getContext("webgl2");
  } catch {
    return false;
  }
}

export interface UseMapLibreResult {
  map: MLMap | null;
  loaded: boolean;
  webGlSupported: boolean;
  contextLost: boolean;
  /** El mapa base externo no cargó y se usa el estilo de respaldo */
  basemapFallback: boolean;
}

/**
 * Ciclo de vida seguro de MapLibre en React 18:
 *  - guardia isMounted ante el doble montaje de StrictMode,
 *  - desuscripción explícita de eventos y destrucción con map.remove() (sin fugas de GPU),
 *  - recuperación ante pérdida de contexto WebGL (suspensión / cambio de GPU),
 *  - respaldo si el estilo del mapa base falla o tarda demasiado.
 */
export function useMapLibre(
  containerRef: RefObject<HTMLDivElement>,
  options: Omit<MapOptions, "container">,
): UseMapLibreResult {
  const [map, setMap] = useState<MLMap | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [contextLost, setContextLost] = useState(false);
  const [basemapFallback, setBasemapFallback] = useState(false);
  const [webGlSupported] = useState(isWebGL2Supported);
  const optionsRef = useRef(options);

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    if (!webGlSupported) {
      if (import.meta.env.MODE !== "test") console.warn("[useMapLibre] WebGL2 no disponible: el mapa no puede inicializarse con aceleración por hardware");
      return;
    }
    let isMounted = true;
    let usingFallback = false;
    // Se marca al recibir el JSON del estilo (no isStyleLoaded(), que sigue en false mientras
    // cargan las teselas y confundiría un fallo de tesela con un fallo del mapa base)
    let styleReady = false;
    const instance = new MLMap({ container, ...optionsRef.current });

    const switchToFallback = () => {
      if (!isMounted || usingFallback || styleReady) return;
      usingFallback = true;
      setBasemapFallback(true);
      instance.setStyle(FALLBACK_STYLE);
    };
    const timer = window.setTimeout(switchToFallback, BASEMAP_TIMEOUT_MS);

    const handleStyleLoad = () => {
      styleReady = true;
      window.clearTimeout(timer);
    };
    const handleLoad = () => {
      window.clearTimeout(timer);
      if (!isMounted) return;
      setLoaded(true);
    };
    const handleError = (e: MLErrorEvent) => {
      // Un fallo del estilo antes de cargar deja el mapa vacío: se pasa al respaldo.
      // Los errores de teselas sueltas (red intermitente) no cambian el estilo.
      if (!styleReady && !usingFallback) switchToFallback();
      else if (import.meta.env.MODE !== "test") console.warn("[useMapLibre]", e.error?.message ?? e);
    };
    const handleContextLost = (e: { originalEvent?: Event }) => {
      e.originalEvent?.preventDefault();
      if (isMounted) setContextLost(true);
    };
    const handleContextRestored = () => {
      if (!isMounted) return;
      setContextLost(false);
      instance.triggerRepaint();
    };

    instance.on("style.load", handleStyleLoad);
    instance.on("load", handleLoad);
    instance.on("error", handleError);
    instance.on("webglcontextlost", handleContextLost);
    instance.on("webglcontextrestored", handleContextRestored);
    setMap(instance);

    return () => {
      isMounted = false;
      window.clearTimeout(timer);
      instance.off("style.load", handleStyleLoad);
      instance.off("load", handleLoad);
      instance.off("error", handleError);
      instance.off("webglcontextlost", handleContextLost);
      instance.off("webglcontextrestored", handleContextRestored);
      instance.remove();
      setMap(null);
      setLoaded(false);
    };
  }, [containerRef, webGlSupported]);

  return { map, loaded, webGlSupported, contextLost, basemapFallback };
}
