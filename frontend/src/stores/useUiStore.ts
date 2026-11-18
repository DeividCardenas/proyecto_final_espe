import { create } from "zustand";
import type { SegmentProps } from "@/types/api";

export interface SelectedSegment extends SegmentProps {
  coordinates: [number, number];
}

export type PanelTab = "analytics" | "segments" | "simulator" | "model";
/** Altura del panel en móvil (hoja inferior): sólo la cabecera, media pantalla o casi completa */
export type SheetSnap = "peek" | "half" | "full";

interface UiState {
  activeTab: PanelTab;
  panelOpen: boolean;
  drawerOpen: boolean;
  /** Filtros plegados por defecto: al entrar sólo se ve el mapa y la respuesta principal */
  filtersOpen: boolean;
  /** Puntos de ayuda (?) sobre la interfaz: sólo si el usuario los activa */
  helpHints: boolean;
  selectedCrashId: string | null;
  selectedCoords: [number, number] | null;
  flyOnSelect: boolean;
  simulatorPoint: [number, number] | null;
  pickingPoint: boolean;
  focusPoint: [number, number] | null;
  /** Cuadra seleccionada en el mapa o en la lista: su predicción se explica en el panel */
  selectedSegment: SelectedSegment | null;
  /** Móvil: altura de la hoja inferior del panel (en escritorio no se usa) */
  sheet: SheetSnap;
  /** Móvil: leyenda del mapa desplegada (plegada por defecto para no tapar el mapa) */
  legendOpen: boolean;
  setSheet: (s: SheetSnap) => void;
  setLegendOpen: (v: boolean) => void;
  selectSegment: (s: SelectedSegment | null) => void;
  focus: (p: [number, number]) => void;
  setTab: (t: PanelTab) => void;
  togglePanel: () => void;
  toggleDrawer: () => void;
  toggleFilters: () => void;
  setHelpHints: (v: boolean) => void;
  selectCrash: (id: string | null, coords?: [number, number] | null, fly?: boolean) => void;
  setSimulatorPoint: (p: [number, number] | null) => void;
  setPickingPoint: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  activeTab: "segments",
  panelOpen: true,
  drawerOpen: false,
  filtersOpen: false,
  helpHints: false,
  selectedCrashId: null,
  selectedCoords: null,
  flyOnSelect: false,
  simulatorPoint: null,
  pickingPoint: false,
  focusPoint: null,
  selectedSegment: null,
  sheet: "half",
  legendOpen: false,
  setSheet: (sheet) => set({ sheet }),
  setLegendOpen: (legendOpen) => set({ legendOpen }),
  selectSegment: (selectedSegment) =>
    // Una sola selección activa a la vez: el resaltado y el vuelo del mapa siguen a la última
    set(selectedSegment
      ? { selectedSegment, selectedCrashId: null, selectedCoords: null, flyOnSelect: false, activeTab: "segments", panelOpen: true,
        sheet: "half" }
      : { selectedSegment }),
  focus: (focusPoint) => set({ focusPoint: [...focusPoint] as [number, number] }),
  setTab: (activeTab) => set((s) => ({ activeTab, panelOpen: true, sheet: s.sheet === "peek" ? "half" : s.sheet })),
  togglePanel: () => set((s) => ({ panelOpen: !s.panelOpen })),
  toggleDrawer: () => set((s) => ({ drawerOpen: !s.drawerOpen })),
  toggleFilters: () => set((s) => ({ filtersOpen: !s.filtersOpen })),
  setHelpHints: (helpHints) => set({ helpHints }),
  selectCrash: (selectedCrashId, coords = null, fly = false) =>
    set(selectedCrashId
      ? { selectedCrashId, selectedCoords: coords, flyOnSelect: fly, selectedSegment: null }
      : { selectedCrashId, selectedCoords: null, flyOnSelect: fly }),
  setSimulatorPoint: (simulatorPoint) =>
    set(simulatorPoint
      ? { simulatorPoint, pickingPoint: false, selectedSegment: null, selectedCrashId: null, selectedCoords: null, sheet: "half" }
      : { simulatorPoint, pickingPoint: false }),
  // En móvil la hoja se pliega mientras se elige el punto, para dejar el mapa libre
  setPickingPoint: (pickingPoint) => set((s) => ({ pickingPoint, sheet: pickingPoint ? "peek" : s.sheet })),
}));
