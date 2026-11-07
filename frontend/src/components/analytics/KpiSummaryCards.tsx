import { useState } from "react";
import { useKpis } from "@/hooks/useKpis";
import { cn, fmtNumber, fmtPct } from "@/components/ui";
import type { Kpis } from "@/types/api";

/** Valor por cada `per` siniestros (null si no hay siniestros). */
const perCrash = (k: Kpis | undefined, field: keyof Kpis, per: number) =>
  k && k.total_crashes ? (Number(k[field] ?? 0) / k.total_crashes) * per : null;

const ratio = (a: number | null | undefined, b: number | null | undefined) => (a != null && b ? a / b : null);
const fmtX = (r: number) => `${r.toLocaleString("es", { minimumFractionDigits: 1, maximumFractionDigits: 1 })}×`;
type Tone = "up" | "down" | undefined;
/** Rojo si la zona está peor que Chicago (≥ 5% por encima), verde si mejor. */
const toneOf = (r: number | null): Tone => (r === null ? undefined : r > 1.05 ? "up" : r < 0.95 ? "down" : undefined);

/**
 * Cifras clave, cada una con su comparación. Los conteos respetan todos los filtros;
 * las tasas se calculan sobre todos los siniestros de la zona y el periodo (sin los
 * filtros de severidad u obra), para que no salgan al 100% por construcción.
 */
/** Cifras visibles de entrada; el resto, detrás de «ver más» (mostrar menos para concentrar). */
const VISIBLE = 3;

export function KpiSummaryCards() {
  const [all, setAll] = useState(false);
  const { local, city, localRates, cityRates, composed } = useKpis();
  const k = local.data;
  const c = city.data;
  const r = localRates.data;
  const cr = cityRates.data;
  const yoy = k?.yoy_change ?? null;
  const shareOfCity = ratio(k?.total_crashes, c?.total_crashes);

  const critRatio = ratio(r?.critical_rate, cr?.critical_rate);
  const fatal = perCrash(r, "fatalities", 1000);
  const cityFatal = perCrash(cr, "fatalities", 1000);
  const injured = perCrash(r, "total_injuries", 100);
  const cityInjured = perCrash(cr, "total_injuries", 100);
  const incap = perCrash(r, "incapacitating", 1000);
  const cityIncap = perCrash(cr, "incapacitating", 1000);
  const wz = perCrash(r, "workzone_crashes", 1);
  const cityWz = perCrash(cr, "workzone_crashes", 1);

  const items: { label: string; value: string; compare: string; tone?: Tone }[] = [
    {
      label: "Siniestros",
      value: fmtNumber(k?.total_crashes),
      compare: [
        yoy === null ? null : `${yoy > 0 ? "+" : ""}${fmtPct(yoy)} vs. 12 meses previos`,
        shareOfCity === null ? null : `${fmtPct(shareOfCity, 1)} de Chicago`,
      ].filter(Boolean).join(" · ") || "—",
      tone: yoy === null ? undefined : yoy > 0 ? "up" : "down",
    },
    {
      label: "Tasa de siniestros críticos",
      value: fmtPct(r?.critical_rate, 2),
      compare: critRatio === null ? "—" : `${fmtX(critRatio)} la de Chicago (${fmtPct(cr?.critical_rate, 2)})`,
      tone: toneOf(critRatio),
    },
    {
      label: "Fallecidos",
      value: fmtNumber(k?.fatalities),
      compare: fatal === null ? "—" : `${fmtNumber(fatal, 1)} por 1.000 siniestros (Chicago ${fmtNumber(cityFatal, 1)})`,
      tone: toneOf(ratio(fatal, cityFatal)),
    },
    {
      label: "Lesiones incapacitantes",
      value: fmtNumber(k?.incapacitating),
      compare: incap === null ? "—" : `${fmtNumber(incap, 1)} por 1.000 siniestros (Chicago ${fmtNumber(cityIncap, 1)})`,
      tone: toneOf(ratio(incap, cityIncap)),
    },
    {
      label: "Lesionados",
      value: fmtNumber(k?.total_injuries),
      compare: injured === null ? "—" : `${fmtNumber(injured, 1)} por 100 siniestros (Chicago ${fmtNumber(cityInjured, 1)})`,
      tone: toneOf(ratio(injured, cityInjured)),
    },
    {
      label: "En zona de obra",
      value: fmtPct(wz, 1),
      compare: `de los siniestros (Chicago ${fmtPct(cityWz, 1)})`,
      tone: toneOf(ratio(wz, cityWz)),
    },
  ];
  return (
    <div className={cn("col-span-2 grid grid-cols-3 gap-2", local.isLoading && "opacity-60")} data-testid="kpi-cards" data-tour="kpis">
      {(all ? items : items.slice(0, VISIBLE)).map((it) => (
        <div key={it.label} className="hud-panel rounded-xl border border-slate-800 bg-slate-900/80 px-3 py-2">
          <p className="text-[10px] uppercase tracking-wide text-slate-500">{it.label}</p>
          <p className="hud-kpi text-xl font-semibold tabular-nums text-slate-100">{it.value}</p>
          <p className={cn("text-[10px] leading-snug text-slate-400", it.tone === "up" && "text-red-300", it.tone === "down" && "text-emerald-300")}>
            {it.compare}
          </p>
        </div>
      ))}
      <button onClick={() => setAll((v) => !v)} className="col-span-3 justify-self-start text-[10px] text-cyan-300 hover:underline">
        {all ? "ver menos cifras" : `ver ${items.length - VISIBLE} cifras más (lesiones y zona de obra)`}
      </button>
      {composed && (
        <p className="col-span-3 text-[10px] leading-snug text-amber-300/90" data-testid="rates-note">
          Los conteos respetan los filtros de severidad y zona de obra; las tasas y proporciones se calculan sobre
          todos los siniestros de la zona y el periodo, para que sigan siendo comparables.
        </p>
      )}
    </div>
  );
}
