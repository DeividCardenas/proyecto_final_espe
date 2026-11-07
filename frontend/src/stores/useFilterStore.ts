import { create } from "zustand";
import type { Severity } from "@/types/api";

export interface FilterState {
  startDate: string | null; // YYYY-MM-DD
  endDate: string | null;
  hourRange: [number, number];
  severities: Severity[];
  workzoneOnly: boolean;
  setDates: (start: string | null, end: string | null) => void;
  setHourRange: (range: [number, number]) => void;
  toggleSeverity: (s: Severity) => void;
  setWorkzoneOnly: (v: boolean) => void;
  reset: () => void;
}

const initial = {
  startDate: null,
  endDate: null,
  hourRange: [0, 23] as [number, number],
  severities: [0, 1, 2] as Severity[],
  workzoneOnly: false,
};

export const useFilterStore = create<FilterState>((set) => ({
  ...initial,
  setDates: (startDate, endDate) => set({ startDate, endDate }),
  setHourRange: (hourRange) => set({ hourRange }),
  toggleSeverity: (s) =>
    set((st) => {
      const has = st.severities.includes(s);
      // Siempre debe quedar al menos una severidad seleccionada
      if (has && st.severities.length === 1) return st;
      return { severities: has ? st.severities.filter((x) => x !== s) : [...st.severities, s].sort() };
    }),
  setWorkzoneOnly: (workzoneOnly) => set({ workzoneOnly }),
  reset: () => set(initial),
}));

/** Número de filtros distintos de los valores por defecto (se muestra en el botón «Filtros»). */
export function activeFilterCount(f: Pick<FilterState, "startDate" | "endDate" | "hourRange" | "severities" | "workzoneOnly">) {
  return (
    (f.startDate || f.endDate ? 1 : 0)
    + (f.hourRange[0] > 0 || f.hourRange[1] < 23 ? 1 : 0)
    + (f.severities.length < 3 ? 1 : 0)
    + (f.workzoneOnly ? 1 : 0)
  );
}
