import { BarChart3, Brain, Gauge, ListOrdered } from "lucide-react";
import type { PanelTab } from "@/stores/useUiStore";

/** Única navegación de la app, nombrada por lo que hace el usuario en cada sección. */
export const TABS: { id: PanelTab; label: string; icon: typeof BarChart3; hint: string }[] = [
  { id: "segments", label: "Priorizar", icon: ListOrdered, hint: "Cuadras con mayor riesgo previsto" },
  { id: "analytics", label: "Explorar", icon: BarChart3, hint: "Cuándo y en qué condiciones ocurren" },
  { id: "simulator", label: "Simular", icon: Gauge, hint: "Probar un escenario en un punto" },
  { id: "model", label: "Modelo", icon: Brain, hint: "Cómo se validó el modelo" },
];
