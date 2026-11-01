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
  selectCrash: (id: string | null, coords?: [number, number] | null, fly?: boolean) => void;
  setSimulatorPoint: (p: [number, number] | null) => void;
  setPickingPoint: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeTab: "segments",
  panelOpen: true,
  drawerOpen: false,
  selectedCrashId: null,
  selectedCoords: null,
  flyOnSelect: false,
  simulatorPoint: null,
  pickingPoint: false,
  focusPoint: null,
  selectedSegment: null,
  selectSegment: (selectedSegment) =>
    set(selectedSegment ? { selectedSegment, activeTab: "segments", panelOpen: true } : { selectedSegment }),
  focus: (focusPoint) => set({ focusPoint: [...focusPoint] as [number, number] }),
  setTab: (activeTab) => set({ activeTab, panelOpen: true }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  selectCrash: (selectedCrashId, coords = null, fly = false) =>
    set({ selectedCrashId, selectedCoords: selectedCrashId ? coords : null, flyOnSelect: fly }),
  setSimulatorPoint: (simulatorPoint) => set({ simulatorPoint, pickingPoint: false }),
  setPickingPoint: (pickingPoint) => set({ pickingPoint }),
}));
