import { create } from "zustand";

export type LayerId = "heatmap" | "points" | "clusters" | "risk" | "segments" | "permits" | "hotspots" | "aadt";

export type Bounds = [number, number, number, number]; // minLon, minLat, maxLon, maxLat

export const CHICAGO_CENTER: [number, number] = [-87.6298, 41.8781];
export const CHICAGO_MAX_BOUNDS: [[number, number], [number, number]] = [
  [-88.1, 41.6],
  [-87.4, 42.1],
];

interface MapState {
  // Sólo estado serializable: la instancia de MapLibre vive en MapContext
  center: [number, number];
  zoom: number;
  bounds: Bounds | null;
  layers: Record<LayerId, boolean>;
  setViewport: (center: [number, number], zoom: number, bounds: Bounds) => void;
  toggleLayer: (id: LayerId) => void;
}

export const useMapStore = create<MapState>((set) => ({
  center: CHICAGO_CENTER,
  zoom: 10.5,
  bounds: null,
  layers: { heatmap: true, points: true, clusters: false, risk: false, segments: false, permits: false, hotspots: false, aadt: false },
  setViewport: (center, zoom, bounds) => set({ center, zoom, bounds }),
  toggleLayer: (id) => set((s) => ({ layers: { ...s.layers, [id]: !s.layers[id] } })),
}));
