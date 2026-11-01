/**
 * Gráficos D3 para el panel analítico.
 *
 * D3 calcula escalas, ticks y formas (d3-scale, d3-array, d3-shape) y React
 * pinta el SVG: así los gráficos respetan el ciclo de vida de React y las
 * pieles visuales sin manipular el DOM a mano.
 *
 * Criterios de diseño (feedback de visualización):
 * - La posición es la codificación principal; el color es neutro y sólo se
 *   satura para resaltar el dato que importa (pico, tramo seleccionado...).
 * - Las barras empiezan siempre en cero (no se exageran diferencias pequeñas).
 * - Cada gráfico admite una línea de referencia para dar comparación.
 */
import { useLayoutEffect, useRef, useState, type KeyboardEvent } from "react";
import { scaleBand, scaleLinear, scaleTime } from "d3-scale";
import { extent, max, min } from "d3-array";
import { line } from "d3-shape";
import { useTheme } from "@/stores/useThemeStore";

export const MUTED = "rgb(var(--slate-600))";
const TEXT = "rgb(var(--slate-400))";
const TEXT_STRONG = "rgb(var(--slate-200))";
const FONT = 10;

/** Ancho del contenedor (ResizeObserver); en entornos sin él usa un ancho fijo. */
export function useWidth(fallback = 320) {
  const ref = useRef<HTMLDivElement>(null);
  const [width, setWidth] = useState(fallback);
  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;
    setWidth(el.clientWidth || fallback);
    if (typeof ResizeObserver === "undefined") return;
    const ro = new ResizeObserver(([e]) => setWidth(Math.max(120, Math.round(e.contentRect.width))));
    ro.observe(el);
    return () => ro.disconnect();
  }, [fallback]);
  return { ref, width };
}

export interface Reference { value: number; label: string }

// ----------------------------------------------------------------------------
// Columnas (distribución por una variable ordinal, p. ej. hora del día)
// ----------------------------------------------------------------------------
export function ColumnChart({
  data, height = 150, highlight, reference, onSelect, format = (v) => v.toLocaleString("es"), tickEvery = 3,
  ariaLabel,
}: {
  data: { key: number | string; label: string; value: number }[];
  height?: number;
  highlight?: number | string;
  reference?: Reference;
  onSelect?: (key: number | string) => void;
  format?: (v: number) => string;
  tickEvery?: number;
  ariaLabel: string;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const m = { top: 14, right: 6, bottom: 18, left: 34 };
  const x = scaleBand<string>().domain(data.map((d) => String(d.key))).range([m.left, width - m.right]).padding(0.18);
  const y = scaleLinear().domain([0, Math.max(reference?.value ?? 0, max(data, (d) => d.value) ?? 1)]).nice()
    .range([height - m.bottom, m.top]);
  return (
    <div ref={ref}>
      <svg width={width} height={height} role={onSelect ? "group" : "img"} aria-label={ariaLabel}>
        {y.ticks(4).map((v) => (
          <g key={v}>
            <line x1={m.left} x2={width - m.right} y1={y(v)} y2={y(v)} stroke={t.chart.grid} />
            <text x={m.left - 4} y={y(v)} dy="0.32em" textAnchor="end" fontSize={FONT} fill={TEXT}>{format(v)}</text>
          </g>
        ))}
        {data.map((d, i) => {
          const hl = d.key === highlight;
          // Barras seleccionables también con teclado (Tab + Enter/Espacio)
          const interactive = onSelect
            ? {
              role: "button", tabIndex: 0, "aria-label": `${d.label}: ${format(d.value)}`,
              onClick: () => onSelect(d.key),
              onKeyDown: (e: KeyboardEvent) => {
                if (e.key === "Enter" || e.key === " ") { e.preventDefault(); onSelect(d.key); }
              },
              style: { cursor: "pointer" },
            }
            : {};
          return (
            <g key={d.key} {...interactive}>
              <rect x={x(String(d.key))} y={y(d.value)} width={x.bandwidth()} height={y(0) - y(d.value)}
                fill={hl ? t.chart.primary : MUTED} rx={1}>
                <title>{`${d.label}: ${format(d.value)}`}</title>
              </rect>
              {i % tickEvery === 0 && (
                <text x={(x(String(d.key)) ?? 0) + x.bandwidth() / 2} y={height - 4} textAnchor="middle" fontSize={FONT} fill={TEXT}>
                  {d.label}
                </text>
              )}
            </g>
          );
        })}
        {reference && <RefLineH y={y(reference.value)} x1={m.left} x2={width - m.right} label={reference.label} />}
      </svg>
    </div>
  );
}

function RefLineH({ y, x1, x2, label }: { y: number; x1: number; x2: number; label: string }) {
  return (
    <g pointerEvents="none">
      <line x1={x1} x2={x2} y1={y} y2={y} stroke={TEXT_STRONG} strokeDasharray="3 3" strokeWidth={1} />
      <text x={x2} y={y - 3} textAnchor="end" fontSize={FONT} fill={TEXT_STRONG}>{label}</text>
    </g>
  );
}

// ----------------------------------------------------------------------------
// Línea temporal (evolución)
// ----------------------------------------------------------------------------
export function LineChart({
  data, height = 130, reference, format = (v) => v.toLocaleString("es"), ariaLabel,
}: {
  data: { date: Date; value: number }[];
  height?: number;
  reference?: Reference;
  format?: (v: number) => string;
  ariaLabel: string;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const m = { top: 14, right: 10, bottom: 18, left: 34 };
  if (data.length === 0) return <div ref={ref} style={{ height }} />;
  const [d0, d1] = extent(data, (d) => d.date) as [Date, Date];
  const x = scaleTime().domain([d0, d1]).range([m.left, width - m.right]);
  const y = scaleLinear().domain([0, max(data, (d) => d.value) ?? 1]).nice().range([height - m.bottom, m.top]);
  const path = line<{ date: Date; value: number }>().x((d) => x(d.date)).y((d) => y(d.value))(data) ?? "";
  const last = data[data.length - 1];
  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        {y.ticks(4).map((v) => (
          <g key={v}>
            <line x1={m.left} x2={width - m.right} y1={y(v)} y2={y(v)} stroke={t.chart.grid} />
            <text x={m.left - 4} y={y(v)} dy="0.32em" textAnchor="end" fontSize={FONT} fill={TEXT}>{format(v)}</text>
          </g>
        ))}
        {x.ticks(Math.max(2, Math.floor(width / 70))).map((d) => (
          <text key={+d} x={x(d)} y={height - 4} textAnchor="middle" fontSize={FONT} fill={TEXT}>
            {d.toLocaleDateString("es", { month: "short", year: "2-digit" })}
          </text>
        ))}
        {reference && <RefLineH y={y(reference.value)} x1={m.left} x2={width - m.right} label={reference.label} />}
        <path d={path} fill="none" stroke={MUTED} strokeWidth={1.5} />
        {data.map((d) => (
          <circle key={+d.date} cx={x(d.date)} cy={y(d.value)} r={6} fill="transparent">
            <title>{`${d.date.toLocaleDateString("es", { month: "long", year: "numeric" })}: ${format(d.value)}`}</title>
          </circle>
        ))}
        <circle cx={x(last.date)} cy={y(last.value)} r={3.5} fill={t.chart.primary} />
      </svg>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Ranking horizontal (barras desde cero o puntos para tasas)
// ----------------------------------------------------------------------------
export function RankChart({
  data, format, reference, mark = "bar", ariaLabel, domainMax,
}: {
  data: { label: string; value: number; note?: string; highlight?: boolean }[];
  format: (v: number) => string;
  reference?: Reference;
  mark?: "bar" | "dot";
  ariaLabel: string;
  domainMax?: number;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const row = 26;
  const m = { top: reference ? 14 : 2, right: 44, left: 4 };
  const height = m.top + data.length * row;
  const x = scaleLinear()
    .domain([0, domainMax ?? Math.max(reference?.value ?? 0, max(data, (d) => d.value) ?? 1)])
    .range([m.left, width - m.right]);
  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        {data.map((d, i) => {
          const y0 = m.top + i * row;
          const color = d.highlight ? t.chart.critical : mark === "dot" ? TEXT_STRONG : MUTED;
          return (
            <g key={d.label}>
              <text x={m.left} y={y0 + 9} fontSize={FONT} fill={TEXT}>
                {d.label}{d.note && <tspan fill={TEXT} opacity={0.7}>{`  ·  ${d.note}`}</tspan>}
              </text>
              <line x1={m.left} x2={width - m.right} y1={y0 + 18} y2={y0 + 18} stroke={t.chart.grid} />
              {mark === "bar" ? (
                <rect x={m.left} y={y0 + 14} width={Math.max(1, x(d.value) - m.left)} height={8} rx={1} fill={color} />
              ) : (
                <circle cx={x(d.value)} cy={y0 + 18} r={4} fill={color} />
              )}
              <text x={width - m.right + 4} y={y0 + 21} fontSize={FONT} fill={TEXT_STRONG}>{format(d.value)}</text>
            </g>
          );
        })}
        {reference && (
          <g pointerEvents="none">
            <line x1={x(reference.value)} x2={x(reference.value)} y1={m.top - 2} y2={height} stroke={TEXT_STRONG} strokeDasharray="3 3" />
            <text x={x(reference.value)} y={9} textAnchor="middle" fontSize={FONT} fill={TEXT_STRONG}>{reference.label}</text>
          </g>
        )}
      </svg>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Barras divergentes (aporte de cada variable a la predicción)
// ----------------------------------------------------------------------------
export function DivergingBars({
  data, ariaLabel, leftLabel, rightLabel,
}: {
  data: { label: string; value: number; detail?: string }[];
  ariaLabel: string;
  leftLabel: string;
  rightLabel: string;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const row = 30;
  const m = { top: 16, right: 6, left: 6 };
  const height = m.top + data.length * row;
  const lim = Math.max(0.5, max(data, (d) => Math.abs(d.value)) ?? 1);
  const x = scaleLinear().domain([-lim, lim]).range([m.left, width - m.right]);
  const x0 = x(0);
  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        <text x={x0 - 4} y={9} textAnchor="end" fontSize={FONT} fill={TEXT}>{`← ${leftLabel}`}</text>
        <text x={x0 + 4} y={9} fontSize={FONT} fill={TEXT}>{`${rightLabel} →`}</text>
        {data.map((d, i) => {
          const y0 = m.top + i * row;
          const up = d.value >= 0;
          return (
            <g key={d.label}>
              <text x={up ? x0 - 4 : x0 + 4} y={y0 + 12} textAnchor={up ? "end" : "start"} fontSize={FONT} fill={TEXT_STRONG}>
                {d.label}
              </text>
              {d.detail && (
                <text x={up ? x0 - 4 : x0 + 4} y={y0 + 24} textAnchor={up ? "end" : "start"} fontSize={9} fill={TEXT}>{d.detail}</text>
              )}
              <rect x={Math.min(x0, x(d.value))} y={y0 + 6} width={Math.max(1, Math.abs(x(d.value) - x0))} height={12} rx={1}
                fill={up ? t.chart.critical : MUTED}>
                <title>{`${d.label}: ${d.value > 0 ? "+" : ""}${d.value.toFixed(2)} log-odds`}</title>
              </rect>
            </g>
          );
        })}
        <line x1={x0} x2={x0} y1={m.top} y2={height} stroke={TEXT_STRONG} />
      </svg>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Strip plot con jitter (distribución + posición de un elemento)
// ----------------------------------------------------------------------------
export function StripPlot({
  values, marker, reference, format, height = 64, ariaLabel,
}: {
  values: number[];
  marker?: number;
  reference?: Reference;
  format: (v: number) => string;
  height?: number;
  ariaLabel: string;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const m = { top: 14, right: 8, bottom: 16, left: 8 };
  const x = scaleLinear().domain([0, 1]).range([m.left, width - m.right]);
  const band = height - m.top - m.bottom;
  // Jitter determinista (secuencia de Weyl): el dibujo no cambia entre renders
  const jitter = (i: number) => ((i * 0.618033988749895) % 1) * band;
  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        {values.map((v, i) => (
          <circle key={i} cx={x(v)} cy={m.top + jitter(i)} r={1.6} fill={MUTED} opacity={0.55} />
        ))}
        {[0, 0.25, 0.5, 0.75, 1].map((v) => (
          <text key={v} x={x(v)} y={height - 3} textAnchor={v === 0 ? "start" : v === 1 ? "end" : "middle"} fontSize={FONT} fill={TEXT}>
            {format(v)}
          </text>
        ))}
        {reference && (
          <g pointerEvents="none">
            <line x1={x(reference.value)} x2={x(reference.value)} y1={m.top - 2} y2={m.top + band} stroke={TEXT_STRONG} strokeDasharray="3 3" />
            <text x={x(reference.value) + 3} y={9} fontSize={FONT} fill={TEXT_STRONG}>{reference.label}</text>
          </g>
        )}
        {marker !== undefined && (
          <g pointerEvents="none">
            <line x1={x(marker)} x2={x(marker)} y1={m.top - 4} y2={m.top + band + 2} stroke={t.chart.critical} strokeWidth={2.5} />
            <text x={Math.min(x(marker), width - 40)} y={9} textAnchor="middle" fontSize={FONT} fontWeight={700} fill={t.chart.critical}>
              esta cuadra
            </text>
          </g>
        )}
      </svg>
    </div>
  );
}

// ----------------------------------------------------------------------------
// Dispersión (relación entre dos variables cuantitativas)
// ----------------------------------------------------------------------------
export function Scatter({
  points, xFormat, yFormat, xLabel, yLabel, height = 150, reference, ariaLabel,
}: {
  points: { x: number; y: number; label: string }[];
  xFormat: (v: number) => string;
  yFormat: (v: number) => string;
  xLabel: string;
  yLabel: string;
  height?: number;
  reference?: Reference;
  ariaLabel: string;
}) {
  const t = useTheme();
  const { ref, width } = useWidth();
  const m = { top: 14, right: 10, bottom: 28, left: 38 };
  const x = scaleLinear().domain([min(points, (p) => p.x) ?? 0, max(points, (p) => p.x) ?? 1]).nice()
    .range([m.left, width - m.right]);
  const y = scaleLinear().domain([0, Math.max(reference?.value ?? 0, max(points, (p) => p.y) ?? 1)]).nice()
    .range([height - m.bottom, m.top]);
  return (
    <div ref={ref}>
      <svg width={width} height={height} role="img" aria-label={ariaLabel}>
        {y.ticks(4).map((v) => (
          <g key={v}>
            <line x1={m.left} x2={width - m.right} y1={y(v)} y2={y(v)} stroke={t.chart.grid} />
            <text x={m.left - 4} y={y(v)} dy="0.32em" textAnchor="end" fontSize={FONT} fill={TEXT}>{yFormat(v)}</text>
          </g>
        ))}
        {x.ticks(4).map((v) => (
          <text key={v} x={x(v)} y={height - 15} textAnchor="middle" fontSize={FONT} fill={TEXT}>{xFormat(v)}</text>
        ))}
        <text x={width - m.right} y={height - 3} textAnchor="end" fontSize={FONT} fill={TEXT}>{xLabel}</text>
        <text x={m.left} y={9} fontSize={FONT} fill={TEXT}>{yLabel}</text>
        {reference && <RefLineH y={y(reference.value)} x1={m.left} x2={width - m.right} label={reference.label} />}
        {points.map((p) => (
          <circle key={p.label} cx={x(p.x)} cy={y(p.y)} r={4} fill={TEXT_STRONG} opacity={0.85}>
            <title>{p.label}</title>
          </circle>
        ))}
      </svg>
    </div>
  );
}
