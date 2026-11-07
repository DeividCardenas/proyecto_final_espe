/**
 * Contenido de la guía de uso. Cada parte de la plataforma se explica en tres líneas:
 * qué hace, qué significa lo que se ve y cómo se hizo. Una sola fuente alimenta el
 * recorrido completo, las guías por sección y los puntos de ayuda.
 */
import type { Side } from "driver.js";

export interface GuideEntry {
  /** Selector del elemento (atributo data-tour) */
  element?: string;
  title: string;
  hace: string;
  significa?: string;
  hizo?: string;
  side?: Side;
}

const t = (id: string) => `[data-tour="${id}"]`;

export const GUIDE = {
  welcome: {
    title: "Bienvenido a Chicago Road Risk",
    hace: "La plataforma anticipa qué cuadras de Chicago tienen más riesgo de siniestros graves el próximo año, para decidir dónde intervenir primero.",
    significa: "Cada paso de esta guía explica qué hace una parte, qué significa lo que ves y cómo se construyó. Puedes salir cuando quieras con Esc o con la ×.",
  },
  map: {
    element: t("map"),
    title: "El mapa",
    hace: "Muestra las cuadras que el modelo prioriza y, al acercarte, cada siniestro registrado.",
    significa: "Cada círculo es una cuadra: el color indica la probabilidad de riesgo Alto en los próximos 12 meses y el tamaño, su prioridad (top 1% y top 10%). Al pasar el cursor ves su probabilidad.",
    hizo: "MapLibre GL JS (WebGL) con teselas vectoriales que genera PostGIS, para dibujar cientos de miles de siniestros sin que el mapa se trabe.",
    side: "right",
  },
  legend: {
    element: t("legend"),
    title: "Leyenda",
    hace: "Traduce los colores y tamaños del mapa.",
    significa: "Sólo aparece la leyenda de las capas que tienes activas.",
    hizo: "Usa las mismas escalas de color que el mapa y el tema visual, así nunca se contradicen.",
    side: "right",
  },
  mapControls: {
    element: t("map-controls"),
    title: "Controles del mapa",
    hace: "Acercar, alejar, inclinar la vista en 3D y volver al centro de Chicago.",
    significa: "Los siniestros individuales aparecen a partir de cierto acercamiento (zoom 13).",
    side: "left",
  },
  priorityHero: {
    element: t("priority-hero"),
    title: "El resultado principal",
    hace: "Resume en una frase lo que logra el modelo.",
    significa: "Qué parte de los siniestros graves del año siguiente concentró el 10% de cuadras señaladas, y cuántas veces más que si se eligieran al azar.",
    hizo: "Modelo por tramo vial: regresión logística, elegida frente a Random Forest y XGBoost porque capta más siniestros graves en ese 10%. Se validó en el tiempo (historia de 2024 para anticipar 2025) y en el espacio (bloques de unos 2 km).",
    side: "left",
  },
  priorityList: {
    element: t("priority-list"),
    title: "Cuadras a priorizar",
    hace: "Lista las cuadras con mayor probabilidad de riesgo Alto. Al hacer clic se ubica en el mapa y se explica su predicción.",
    significa: "El porcentaje de la derecha es la probabilidad de riesgo Alto; «sin.» son los siniestros de los últimos 12 meses.",
    hizo: "Una cuadra agrupa los siniestros por la centena del número, la dirección y la calle (por ejemplo, 700 S CICERO AVE), con los datos abiertos de la Ciudad de Chicago (API SODA).",
    side: "left",
  },
  segmentExplain: {
    element: t("segment-explain"),
    title: "Por qué esta cuadra",
    hace: "Explica la predicción de la cuadra elegida.",
    significa: "La franja de puntos la compara con todas las cuadras de la ciudad; las barras rojas son las variables que suben el riesgo y las grises, las que lo bajan.",
    hizo: "Aporte de cada variable de la regresión logística frente a una cuadra típica, calculado por la API (FastAPI).",
    side: "left",
  },
  navFilters: {
    element: t("nav-filters"),
    title: "Filtros y capas",
    hace: "Abre los filtros de periodo, hora y severidad, y las capas del mapa.",
    significa: "El número del botón indica cuántos filtros están activos; el mapa y los gráficos los respetan.",
    hizo: "La hora y la severidad se filtran en la tarjeta gráfica del navegador, sin volver a pedir datos; las fechas se aplican en el servidor.",
    side: "bottom",
  },
  navAnalytics: {
    element: t("nav-analytics"),
    title: "Explorar",
    hace: "Muestra cuándo y en qué condiciones ocurren los siniestros de la zona visible del mapa.",
    significa: "Cada gráfico dice su conclusión arriba y se compara con el promedio o con todo Chicago.",
    hizo: "Agregaciones en DuckDB (capa Gold de la arquitectura Medallion) y gráficos dibujados con D3.",
    side: "bottom",
  },
  navSimulator: {
    element: t("nav-simulator"),
    title: "Simular",
    hace: "Estima la severidad de un siniestro en el punto que elijas, cambiando velocidad, hora, clima, luz y obras.",
    significa: "Es un escenario hipotético: cómo cambiaría la gravedad esperada si ocurriera un siniestro allí.",
    hizo: "Modelo XGBoost por siniestro; como no hay un choque concreto, promedia los tipos de choque más frecuentes según su frecuencia histórica.",
    side: "bottom",
  },
  navModel: {
    element: t("nav-model"),
    title: "Modelo",
    hace: "Muestra cómo se validaron los modelos y con qué métricas.",
    significa: "En el AUC, 0,5 equivale a azar y 1 a acertar siempre.",
    hizo: "Comparación de regresión logística, Random Forest y XGBoost con validación temporal y espacial.",
    side: "bottom",
  },
  navTable: {
    element: t("nav-table"),
    title: "Tabla",
    hace: "Lista los siniestros de la zona visible y permite exportarlos (CSV, GeoJSON).",
    significa: "Al hacer clic en una fila, el siniestro se ubica en el mapa.",
    hizo: "Tabla virtualizada: sólo dibuja las filas visibles, por eso maneja miles sin perder fluidez.",
    side: "bottom",
  },
  navTheme: {
    element: t("nav-theme"),
    title: "Tema visual",
    hace: "Cambia la apariencia de la plataforma.",
    significa: "Clásico es el recomendado para analizar; los demás son pieles de exhibición.",
    side: "bottom",
  },
  navHelp: {
    element: t("nav-help"),
    title: "Ayuda",
    hace: "Repite este recorrido, abre la guía de la sección en la que estás o activa los puntos de ayuda (?) sobre la pantalla.",
    significa: "Nada de esto se muestra solo: aparece únicamente cuando lo pides.",
    side: "bottom",
  },
  analyticsSteps: {
    element: t("analytics-steps"),
    title: "Dos pasos de lectura",
    hace: "Separa los gráficos en «Cuánto y cuándo» y «En qué condiciones» para no mostrar todo a la vez.",
    side: "left",
  },
  kpis: {
    element: t("kpis"),
    title: "Cifras clave",
    hace: "Resume los siniestros de la zona visible.",
    significa: "Debajo de cada cifra está su comparación con Chicago: en rojo si la zona está peor y en verde si está mejor.",
    hizo: "Las tasas se calculan sobre todos los siniestros de la zona y el periodo, para que no cambien al filtrar por severidad.",
    side: "left",
  },
  analyticsHero: {
    element: t("analytics-hero"),
    title: "Gráfico principal",
    hace: "Muestra a qué hora ocurren más siniestros.",
    significa: "La barra resaltada es la hora pico y la línea punteada, el promedio. Al hacer clic en una barra se filtra esa hora.",
    side: "left",
  },
  simLocation: {
    element: t("sim-location"),
    title: "Dónde simular",
    hace: "Elige el punto del escenario: por defecto el Loop, o el que marques en el mapa.",
    side: "left",
  },
  simResult: {
    element: t("sim-result"),
    title: "Riesgo predicho",
    hace: "Muestra la probabilidad de cada nivel de severidad y las variables que más influyen.",
    significa: "Se recalcula al instante cada vez que cambias un parámetro.",
    hizo: "La API FastAPI carga el modelo una vez y responde cada predicción en milisegundos.",
    side: "left",
  },
  modelMain: {
    element: t("model-main"),
    title: "Modelo principal",
    hace: "Resume el modelo por cuadra y su resultado en el año que no vio al entrenar.",
    significa: "Más abajo está la comparativa completa y el modelo por siniestro que usa el simulador.",
    side: "left",
  },
} satisfies Record<string, GuideEntry>;

export type GuideKey = keyof typeof GUIDE;

const esc = (s: string) => s.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");

/** Cuerpo del globo: «Qué hace / Qué significa / Cómo se hizo». */
export function describe(e: GuideEntry): string {
  const row = (label: string, text?: string) =>
    text ? `<p class="crr-guide-row"><b>${label}</b> ${esc(text)}</p>` : "";
  return row("Qué hace:", e.hace) + row("Qué significa:", e.significa) + row("Cómo se hizo:", e.hizo);
}
