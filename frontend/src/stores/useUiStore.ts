import { create } from "zustand";
import type { SegmentProps } from "@/types/api";

export interface SelectedSegment extends SegmentProps {
  coordinates: [number, number];
}

export type PanelTab = "analytics" | "segments" | "simulator" | "model";

interface UiState {
  activeTab: PanelTab;
  panelOpen: boolean;
  drawerOpen: boolean;
  /** Filtros plegados por defecto: al entrar sólo se ve el mapa y la respuesta principal */
  filtersOpen: boolean;
  /** Recorrido guiado de 3 pasos (se abre solo en la primera visita) */
  tourOpen: boolean;
  selectedCrashId: string | null;
  selectedCoords: [number, number] | null;
  flyOnSelect: boolean;
  simulatorPoint: [number, number] | null;
  pickingPoint: boolean;
  focusPoint: [number, number] | null;
  /** Cuadra seleccionada en el mapa o en la lista: su predicción se explica en el panel */
  selectedSegment: SelectedSegment | null;
  selectSegment: (s: SelectedSegment | null) => void;
  focus: (p: [number, number]) => void;
  setTab: (t: PanelTab) => void;
  togglePanel: () => void;
  toggleDrawer: () => void;
  toggleFilters: () => void;
  setTourOpen: (v: boolean) => void;
  selectCrash: (id: string | null, coords?: [number, number] | null, fly?: boolean) => void;
  setSimulatorPoint: (p: [number, number] | null) => void;
  setPickingPoint: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeTab: "segments",
  panelOpen: true,
  drawerOpen: false,
  filtersOpen: false,
  tourOpen: false,
  selectedCrashId: null,
  selectedCoords: null,
  flyOnSelect: false,
  simulatorPoint: null,
  pickingPoint: false,
  focusPoint: null,
  selectedSegment: null,
  selectSegment: (selectedSegment) =>
    // Una sola selección activa a la vez: el resaltado y el vuelo del mapa siguen a la última
    set(selectedSegment
      ? { selectedSegment, selectedCrashId: null, selectedCoords: null, flyOnSelect: false, activeTab: "segments", panelOpen: true }
      : { selectedSegment }),
  focus: (focusPoint) => set({ focusPoint: [...focusPoint] as [number, number] }),
  setTab: (activeTab) => set({ activeTab, panelOpen: true }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  toggleFilters: () => set((s) => ({ filtersOpen: !s.filtersOpen })),
  setTourOpen: (tourOpen) => set({ tourOpen }),
  selectCrash: (selectedCrashId, coords = null, fly = false) =>
    set(selectedCrashId
      ? { selectedCrashId, selectedCoords: coords, flyOnSelect: fly, selectedSegment: null }
      : { selectedCrashId, selectedCoords: null, flyOnSelect: fly }),
  setSimulatorPoint: (simulatorPoint) =>
    set(simulatorPoint
      ? { simulatorPoint, pickingPoint: false, selectedSegment: null, selectedCrashId: null, selectedCoords: null }
      : { simulatorPoint, pickingPoint: false }),
  setPickingPoint: (pickingPoint) => set({ pickingPoint }),
}));
