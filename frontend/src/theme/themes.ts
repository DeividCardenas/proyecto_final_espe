/**
 * Sistema de temas visuales.
 *
 * Cada tema redefine las escalas `slate` (superficies y texto) y `cyan` (acento)
 * de Tailwind mediante variables CSS en formato "R G B", de modo que todos los
 * componentes cambian de piel sin tocar sus clases. Además define la paleta del
 * mapa base, de las capas de datos y de los gráficos.
 */

export type ThemeId = "classic" | "tron" | "cyberpunk" | "nerv";

type Scale = Record<"50" | "100" | "200" | "300" | "400" | "500" | "600" | "700" | "800" | "900" | "950", string>;

export interface ThemeDef {
  id: ThemeId;
  name: string;
  tagline: string;
  /** Subtítulo de la cabecera (p. ej. textos de interfaz estilo NERV) */
  headerSub: string;
  swatch: [string, string, string];
  slate: Scale;
  cyan: Scale;
  fonts: { display: string; body: string; mono: string };
  severity: [string, string, string];
  heatmap: [string, string, string, string, string];
  chart: { primary: string; critical: string; series: string[]; grid: string; axis: string; tooltipBg: string; tooltipBorder: string };
  map: {
    background: string;
    water: string;
    land: string;
    building: string;
    roadMajor: string;
    roadMinor: string;
    roadOpacity: number;
    label: string;
    labelHalo: string;
    boundary: string;
  };
  cluster: [string, string, string, string];
}

const rgb = (hex: string) => {
  const n = parseInt(hex.slice(1), 16);
  return `${(n >> 16) & 255} ${(n >> 8) & 255} ${n & 255}`;
};

function scale(hexes: string[]): Scale {
  const keys = ["50", "100", "200", "300", "400", "500", "600", "700", "800", "900", "950"] as const;
  return Object.fromEntries(keys.map((k, i) => [k, rgb(hexes[i])])) as Scale;
}

export const THEMES: Record<ThemeId, ThemeDef> = {
  classic: {
    id: "classic",
    name: "Clásico",
    tagline: "Analítico sobrio",
    headerSub: "Riesgo vial geoespacial · Big Data & ML",
    swatch: ["#0f172a", "#06b6d4", "#dc2626"],
    slate: scale(["#f8fafc", "#f1f5f9", "#e2e8f0", "#cbd5e1", "#94a3b8", "#64748b", "#475569", "#334155", "#1e293b", "#0f172a", "#020617"]),
    cyan: scale(["#ecfeff", "#cffafe", "#a5f3fc", "#67e8f9", "#22d3ee", "#06b6d4", "#0891b2", "#0e7490", "#155e75", "#164e63", "#083344"]),
    fonts: { display: "Inter", body: "Inter", mono: "ui-monospace" },
    severity: ["#38bdf8", "#facc15", "#dc2626"],
    heatmap: ["#1e3a8a", "#7c3aed", "#db2777", "#f97316", "#fde047"],
    chart: { primary: "#0ea5e9", critical: "#dc2626", series: ["#38bdf8", "#818cf8", "#a78bfa", "#f472b6", "#fb923c", "#facc15", "#4ade80", "#94a3b8"], grid: "#1e293b", axis: "#64748b", tooltipBg: "#0f172a", tooltipBorder: "#334155" },
    map: { background: "", water: "", land: "", building: "", roadMajor: "", roadMinor: "", roadOpacity: 1, label: "", labelHalo: "", boundary: "" },
    cluster: ["#0ea5e9", "#8b5cf6", "#ec4899", "#f97316"],
  },

  // TRON: Legacy. Negro profundo, líneas finas de luz cian y acento naranja.
  tron: {
    id: "tron",
    name: "The Grid",
    tagline: "TRON · neón cian sobre negro",
    headerSub: "END OF LINE · SECTOR CHICAGO · RISK GRID",
    swatch: ["#02070c", "#5ff7ff", "#ff8a1f"],
    slate: scale(["#f2feff", "#d9fbff", "#b4f2f8", "#8cdbe4", "#5aa8b3", "#3d7480", "#24505a", "#163843", "#0b2530", "#05141c", "#02080d"]),
    cyan: scale(["#effeff", "#d4fdff", "#a8fbff", "#7ff8ff", "#5ff7ff", "#25e4f5", "#00bcd4", "#00909f", "#006874", "#004651", "#002a31"]),
    fonts: { display: "Orbitron", body: "Rajdhani", mono: "Share Tech Mono" },
    severity: ["#5ff7ff", "#f2f7ff", "#ff8a1f"],
    heatmap: ["#00222b", "#00607a", "#00b8d4", "#5ff7ff", "#e8feff"],
    chart: { primary: "#5ff7ff", critical: "#ff8a1f", series: ["#5ff7ff", "#25b8cc", "#a8fbff", "#ff8a1f", "#ffc27a", "#2a6f7d", "#e6fdff", "#4a8f9c"], grid: "#0c2a35", axis: "#3d7480", tooltipBg: "#02080d", tooltipBorder: "#25e4f5" },
    map: { background: "#010508", water: "#000000", land: "#020a10", building: "#04121a", roadMajor: "#3be9ff", roadMinor: "#0d6b7a", roadOpacity: 0.55, label: "#6fdcea", labelHalo: "#010508", boundary: "#5ff7ff" },
    cluster: ["#25e4f5", "#7ff8ff", "#ffc27a", "#ff8a1f"],
  },

  // Cyberpunk 2077 (Night City). Amarillo ácido, cian eléctrico y rojo, sobre negro.
  cyberpunk: {
    id: "cyberpunk",
    name: "Night City",
    tagline: "Cyberpunk · amarillo, cian y rojo",
    headerSub: "NCPD // TRAFFIC THREAT ASSESSMENT // CHICAGO.EXE",
    swatch: ["#0b0b10", "#fcee0a", "#ff003c"],
    slate: scale(["#fffdeb", "#fffbd1", "#f5efb0", "#d9d39a", "#9e9a76", "#6f6c58", "#4a483f", "#2f2e2b", "#1c1c1d", "#111114", "#09090c"]),
    cyan: scale(["#fffde6", "#fffbbf", "#fff785", "#fff24a", "#fcee0a", "#e0d300", "#b3a800", "#857d00", "#5c5700", "#3d3a00", "#211f00"]),
    fonts: { display: "Rajdhani", body: "Rajdhani", mono: "Share Tech Mono" },
    severity: ["#00f0ff", "#fcee0a", "#ff003c"],
    heatmap: ["#1a0b2e", "#5b1a8c", "#ff003c", "#ff7a00", "#fcee0a"],
    chart: { primary: "#fcee0a", critical: "#ff003c", series: ["#fcee0a", "#00f0ff", "#ff003c", "#b86bff", "#ff7a00", "#6dff9e", "#f5f5f5", "#8a8a8a"], grid: "#232326", axis: "#6f6c58", tooltipBg: "#09090c", tooltipBorder: "#fcee0a" },
    map: { background: "#08080b", water: "#04141a", land: "#0d0d11", building: "#17171c", roadMajor: "#fcee0a", roadMinor: "#7a2a3a", roadOpacity: 0.45, label: "#00f0ff", labelHalo: "#08080b", boundary: "#ff003c" },
    cluster: ["#00f0ff", "#b86bff", "#ff003c", "#fcee0a"],
  },

  // NERV / Evangelion. Pantallas MAGI: naranja ámbar, verde terminal y rojo de alerta.
  nerv: {
    id: "nerv",
    name: "NERV / MAGI",
    tagline: "Evangelion · naranja, verde y alerta roja",
    headerSub: "特務機関NERV · 交通危険解析システム · MAGI SYSTEM",
    swatch: ["#0c0705", "#ff8c1a", "#36ff7a"],
    slate: scale(["#fff6ea", "#ffe9cf", "#f4cfa3", "#dba66f", "#a9784a", "#7a5434", "#563823", "#3a2517", "#24170e", "#150d08", "#0b0604"]),
    cyan: scale(["#fff4e6", "#ffe3bf", "#ffc985", "#ffad4d", "#ff8c1a", "#f07400", "#c25d00", "#944700", "#6b3300", "#472200", "#2a1400"]),
    fonts: { display: "Shippori Mincho B1", body: "Barlow Condensed", mono: "Share Tech Mono" },
    severity: ["#36ff7a", "#ff8c1a", "#ff1f1f"],
    heatmap: ["#1f0d04", "#6b2a00", "#e05a00", "#ff8c1a", "#ffe0a8"],
    chart: { primary: "#ff8c1a", critical: "#ff1f1f", series: ["#ff8c1a", "#36ff7a", "#8a5cd6", "#ff1f1f", "#ffd27a", "#2fb8a6", "#f4cfa3", "#7a5434"], grid: "#2a1a10", axis: "#7a5434", tooltipBg: "#0b0604", tooltipBorder: "#ff8c1a" },
    map: { background: "#070403", water: "#020302", land: "#0c0705", building: "#170d07", roadMajor: "#ff8c1a", roadMinor: "#5c2e0a", roadOpacity: 0.5, label: "#36ff7a", labelHalo: "#070403", boundary: "#ff1f1f" },
    cluster: ["#36ff7a", "#ffad4d", "#ff8c1a", "#ff1f1f"],
  },
};

export const THEME_ORDER: ThemeId[] = ["tron", "cyberpunk", "nerv", "classic"];

/** Aplica las variables CSS del tema al documento. */
export function applyThemeVars(theme: ThemeDef, root: HTMLElement = document.documentElement) {
  root.dataset.theme = theme.id;
  for (const [k, v] of Object.entries(theme.slate)) root.style.setProperty(`--slate-${k}`, v);
  for (const [k, v] of Object.entries(theme.cyan)) root.style.setProperty(`--cyan-${k}`, v);
  root.style.setProperty("--font-display", `"${theme.fonts.display}"`);
  root.style.setProperty("--font-body", `"${theme.fonts.body}"`);
  root.style.setProperty("--font-mono", `"${theme.fonts.mono}"`);
  root.style.setProperty("--accent", theme.swatch[1]);
  root.style.setProperty("--accent-2", theme.swatch[2]);
  root.style.setProperty("--critical", theme.severity[2]);
}
