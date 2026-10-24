import { create } from "zustand";

export type PanelTab = "analytics" | "simulator" | "model";

interface UiState {
  activeTab: PanelTab;
  panelOpen: boolean;
  drawerOpen: boolean;
  selectedCrashId: string | null;
  selectedCoords: [number, number] | null;
  flyOnSelect: boolean;
  simulatorPoint: [number, number] | null;
  pickingPoint: boolean;
  setTab: (t: PanelTab) => void;
  togglePanel: () => void;
  toggleDrawer: () => void;
  selectCrash: (id: string | null, coords?: [number, number] | null, fly?: boolean) => void;
  setSimulatorPoint: (p: [number, number] | null) => void;
  setPickingPoint: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeTab: "analytics",
  panelOpen: true,
  drawerOpen: false,
  selectedCrashId: null,
  selectedCoords: null,
  flyOnSelect: false,
  simulatorPoint: null,
  pickingPoint: false,
  setTab: (activeTab) => set({ activeTab, panelOpen: true }),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  selectCrash: (selectedCrashId, coords = null, fly = false) =>
    set({ selectedCrashId, selectedCoords: selectedCrashId ? coords : null, flyOnSelect: fly }),
  setSimulatorPoint: (simulatorPoint) => set({ simulatorPoint, pickingPoint: false }),
  setPickingPoint: (pickingPoint) => set({ pickingPoint }),
}));
