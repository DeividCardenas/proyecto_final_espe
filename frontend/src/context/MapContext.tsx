import { createContext, useContext, type ReactNode } from "react";
import type { Map as MLMap } from "maplibre-gl";

interface MapContextValue {
  map: MLMap | null;
  loaded: boolean;
}

// La instancia mutable de MapLibre se comparte por contexto (no en Zustand) para
// evitar referencias circulares en DevTools y renders innecesarios.
const MapContext = createContext<MapContextValue>({ map: null, loaded: false });

export function MapProvider({ value, children }: { value: MapContextValue; children: ReactNode }) {
  return <MapContext.Provider value={value}>{children}</MapContext.Provider>;
}

export function useMapInstance(): MapContextValue {
  return useContext(MapContext);
}
