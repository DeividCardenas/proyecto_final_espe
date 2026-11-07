/**
 * Guía de uso con Driver.js (MIT, sin dependencias):
 *  - recorrido completo por cada parte de la plataforma,
 *  - guía corta de la sección abierta,
 *  - puntos de ayuda (?) opcionales sobre la interfaz.
 * Nada se abre solo: el usuario lo pide desde «Ayuda» o desde la invitación de la
 * primera visita, y puede salir en cualquier momento (Esc, ×, clic fuera).
 */
import { driver, type DriveStep, type Driver } from "driver.js";
import { hints, type Hints } from "driver.js/hints";
import "driver.js/dist/driver.css";
import "driver.js/dist/hints.css";
import { useMapStore } from "@/stores/useMapStore";
import { useUiStore, type PanelTab } from "@/stores/useUiStore";
import { describe, GUIDE, type GuideKey } from "./guideContent";

import { markGuideSeen } from "./launcher";

// Este módulo (con Driver.js) se carga bajo demanda desde ./launcher
export { GUIDE_SEEN_KEY, guideSeen, markGuideSeen } from "./launcher";

interface Step {
  key: GuideKey;
  /** Prepara la interfaz antes de mostrar el paso (abrir una sección, elegir una cuadra…) */
  before?: () => void;
}

const ui = () => useUiStore.getState();

const openTab = (tab: PanelTab) => () => {
  const s = ui();
  if (s.activeTab !== tab || !s.panelOpen) s.setTab(tab);
};
const showPriority = () => {
  openTab("segments")();
  ui().selectSegment(null);
  const map = useMapStore.getState();
  if (!map.layers.segments) map.toggleLayer("segments");
};
/** Abre la explicación de la primera cuadra de la lista (simula el clic del usuario). */
const pickFirstSegment = () => {
  openTab("segments")();
  const first = document.querySelector<HTMLButtonElement>('[data-tour="priority-list"] li button');
  first?.click();
};

const FULL: Step[] = [
  { key: "welcome", before: showPriority },
  { key: "map" },
  { key: "legend" },
  { key: "priorityHero", before: showPriority },
  { key: "priorityList" },
  { key: "segmentExplain", before: pickFirstSegment },
  { key: "navFilters" },
  { key: "navAnalytics" },
  { key: "navSimulator" },
  { key: "navModel" },
  { key: "navTable" },
  { key: "navTheme" },
  { key: "navHelp" },
];

const SECTION: Record<PanelTab, Step[]> = {
  segments: [{ key: "priorityHero", before: showPriority }, { key: "priorityList" }, { key: "map" }, { key: "legend" }],
  analytics: [
    { key: "analyticsSteps", before: openTab("analytics") },
    { key: "kpis" },
    { key: "analyticsHero" },
  ],
  simulator: [{ key: "simLocation", before: openTab("simulator") }, { key: "simResult" }],
  model: [{ key: "modelMain", before: openTab("model") }, { key: "navModel" }],
};

let active: Driver | null = null;

function run(steps: Step[], onEnd?: () => void) {
  active?.destroy();
  const toDrive = (s: Step, i: number): DriveStep => {
    const e = GUIDE[s.key];
    return {
      element: "element" in e ? e.element : undefined,
      // El elemento puede tardar en montarse (sección que se abre, cuadra que se elige)
      waitForElement: 1500,
      skipMissingElement: true,
      popover: {
        title: e.title, description: describe(e), side: "side" in e ? e.side : undefined, align: "start",
        // Sin «Anterior» en el primer paso
        ...(i === 0 ? { showButtons: ["next", "close"] as const } : {}),
      },
    };
  };
  const go = (d: Driver, index: number) => {
    steps[index]?.before?.();
    // Un fotograma para que React aplique el cambio antes de buscar el elemento
    requestAnimationFrame(() => d.moveTo(index));
  };
  const d = driver({
    steps: steps.map(toDrive),
    showProgress: true,
    progressText: "{{current}} de {{total}}",
    nextBtnText: "Siguiente",
    prevBtnText: "Anterior",
    doneBtnText: "Listo",
    closeBtnLabel: "Cerrar guía",
    popoverClass: "crr-guide",
    overlayOpacity: 0.45,
    stagePadding: 6,
    stageRadius: 10,
    overlayClickBehavior: "close",
    allowKeyboardControl: true,
    onNextClick: (_el, _step, { driver: dr }) => {
      const i = dr.getActiveIndex() ?? 0;
      if (dr.isLastStep()) dr.destroy();
      else go(dr, i + 1);
    },
    onPrevClick: (_el, _step, { driver: dr }) => go(dr, Math.max(0, (dr.getActiveIndex() ?? 0) - 1)),
    onDestroyed: () => {
      active = null;
      markGuideSeen();
      onEnd?.();
    },
  });
  active = d;
  steps[0]?.before?.();
  requestAnimationFrame(() => d.drive(0));
}

/** Recorrido completo: cada parte, qué hace, qué significa y cómo se hizo. */
export function startFullTour() {
  run(FULL);
}

/** Guía corta de la sección abierta en el panel. */
export function startSectionTour(tab: PanelTab) {
  run(SECTION[tab]);
}

// ---------------------------------------------------------------------------
// Puntos de ayuda (?) opcionales
// ---------------------------------------------------------------------------
const HINT_KEYS: GuideKey[] = ["navFilters", "navSimulator", "navModel", "navTable", "legend"];
let hintLayer: Hints | null = null;

export function setHelpHints(on: boolean) {
  hintLayer?.hide();
  hintLayer = null;
  if (!on) return;
  hintLayer = hints({
    popoverClass: "crr-guide",
    buttonText: "Entendido",
    beacon: { animate: true },
    hints: HINT_KEYS.map((key) => {
      const e = GUIDE[key];
      return {
        id: key,
        element: "element" in e ? e.element! : "body",
        beacon: { side: key === "legend" ? "top" : "bottom", align: "end" },
        popover: { title: e.title, description: describe(e), side: "side" in e ? e.side : "bottom" },
      };
    }),
  });
  hintLayer.show();
}
