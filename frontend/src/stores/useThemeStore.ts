import { create } from "zustand";
import { THEMES, type ThemeDef, type ThemeId } from "@/theme/themes";

// v2: el tema por defecto pasó a ser Clásico (sobrio); las pieles temáticas quedan como opción
const STORAGE_KEY = "chicago-road-risk-theme-v2";

function readStored(): ThemeId {
  try {
    const v = localStorage.getItem(STORAGE_KEY) as ThemeId | null;
    if (v && v in THEMES) return v;
  } catch {
    /* almacenamiento no disponible (modo privado, previsualización) */
  }
  return "classic";
}

interface ThemeState {
  themeId: ThemeId;
  setTheme: (id: ThemeId) => void;
}

export const useThemeStore = create<ThemeState>((set) => ({
  themeId: readStored(),
  setTheme: (themeId) => {
    try {
      localStorage.setItem(STORAGE_KEY, themeId);
    } catch {
      /* preferencia sólo en memoria */
    }
    set({ themeId });
  },
}));

export function useTheme(): ThemeDef {
  return THEMES[useThemeStore((s) => s.themeId)];
}
