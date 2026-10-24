import { useEffect, useRef, useState, type RefObject } from "react";
import { Map as MLMap, type MapOptions } from "maplibre-gl";

export const BASEMAP_STYLE = "https://basemaps.cartocdn.com/gl/dark-matter-gl-style/style.json";

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
}

/**
 * Ciclo de vida seguro de MapLibre en React 18:
 *  - guardia isMounted ante el doble montaje de StrictMode,
 *  - desuscripción explícita de 'load' y destrucción con map.remove() (sin fugas de GPU),
 *  - recuperación ante pérdida de contexto WebGL (suspensión / cambio de GPU).
 */
export function useMapLibre(
  containerRef: RefObject<HTMLDivElement>,
  options: Omit<MapOptions, "container">,
): UseMapLibreResult {
  const [map, setMap] = useState<MLMap | null>(null);
  const [loaded, setLoaded] = useState(false);
  const [contextLost, setContextLost] = useState(false);
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
    const instance = new MLMap({ container, ...optionsRef.current });

    const handleLoad = () => {
      if (!isMounted) return;
      setLoaded(true);
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

    instance.on("load", handleLoad);
    instance.on("webglcontextlost", handleContextLost);
    instance.on("webglcontextrestored", handleContextRestored);
    setMap(instance);

    return () => {
      isMounted = false;
      instance.off("load", handleLoad);
      instance.off("webglcontextlost", handleContextLost);
      instance.off("webglcontextrestored", handleContextRestored);
      instance.remove();
      setMap(null);
      setLoaded(false);
    };
  }, [containerRef, webGlSupported]);

  return { map, loaded, webGlSupported, contextLost };
}
