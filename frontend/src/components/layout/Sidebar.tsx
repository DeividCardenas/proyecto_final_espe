import * as Slider from "@radix-ui/react-slider";
import * as Checkbox from "@radix-ui/react-checkbox";
import { useState } from "react";
import { Check, ChevronDown, RotateCcw, X } from "lucide-react";
import { activeFilterCount, useFilterStore } from "@/stores/useFilterStore";
import { useUiStore } from "@/stores/useUiStore";
import { useMapStore, type LayerId } from "@/stores/useMapStore";
import { cn, SEVERITY_LABELS } from "@/components/ui";
import type { Severity } from "@/types/api";
import { useTheme } from "@/stores/useThemeStore";
import { useShallow } from "zustand/react/shallow";
import { useDataCoverage } from "@/hooks/useDataCoverage";
import { fmtDateTime, periodPresets } from "@/lib/dates";

interface LayerDef { id: LayerId; label: string; hint: string; tech: string }

/*
 * Capas en dos niveles: las tres que responden a la pregunta principal (dónde está el
 * riesgo) siempre visibles; el resto, de contexto, detrás de «Más capas». El detalle
 * técnico de cada capa queda en el tooltip (title), no en la interfaz.
 */
const MAIN_LAYERS: LayerDef[] = [
  { id: "segments", label: "Riesgo por cuadra", hint: "Predicción para los próximos 12 meses", tech: "Modelo por tramo vial · top 10% de cuadras por P(riesgo Alto)" },
  { id: "points", label: "Siniestros", hint: "Se ven al acercarte", tech: "Teselas vectoriales MVT · visibles desde zoom 13" },
  { id: "heatmap", label: "Mapa de calor", hint: "Dónde se concentran", tech: "Densidad ponderada por severidad (teselas MVT)" },
];
const MORE_LAYERS: LayerDef[] = [
  { id: "risk", label: "Riesgo por zona", hint: "Celdas de 500 m", tech: "Rejilla de 500 m con el modelo de severidad" },
  { id: "hotspots", label: "Puntos calientes", hint: "Grupos de siniestros muy cercanos", tech: "DBSCAN en PostGIS (radio 40 m)" },
  { id: "clusters", label: "Agrupaciones", hint: "Cuántos siniestros por zona", tech: "Supercluster en el cliente" },
  { id: "permits", label: "Obras en la vía", hint: "Cierres por obra", tech: "Permisos CDOT con cierre total/parcial + 250 m" },
  { id: "aadt", label: "Volumen de tráfico", hint: "Vehículos por día", tech: "Aforos AADT de 2006" },
];

function Box({ checked, onChange, color, label, title }: {
  checked: boolean; onChange: () => void; color?: string; label: string; title?: string;
}) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300" title={title}>
      <Checkbox.Root
        checked={checked}
        onCheckedChange={onChange}
        aria-label={label}
        className="grid h-4 w-4 place-items-center rounded border border-slate-600 bg-slate-800 data-[state=checked]:border-cyan-500 data-[state=checked]:bg-cyan-600"
      >
        <Checkbox.Indicator><Check size={12} className="text-white" /></Checkbox.Indicator>
      </Checkbox.Root>
      {color && <i className="h-2.5 w-2.5 rounded-full" style={{ background: color }} />}
      {label}
    </label>
  );
}

function LayerList({ items }: { items: LayerDef[] }) {
  const { layers, toggleLayer } = useMapStore(useShallow((s) => ({ layers: s.layers, toggleLayer: s.toggleLayer })));
  return (
    <div className="space-y-2">
      {items.map((l) => (
        <div key={l.id}>
          <Box checked={layers[l.id]} onChange={() => toggleLayer(l.id)} label={l.label} title={l.tech} />
          <p className="ml-6 text-[10px] text-slate-400">{l.hint}</p>
        </div>
      ))}
    </div>
  );
}

/** Panel de filtros y capas: plegado por defecto para que al entrar el mapa sea el protagonista. */
export function Sidebar() {
  const filtersOpen = useUiStore((s) => s.filtersOpen);
  if (!filtersOpen) return null;
  return <FiltersPanel />;
}

function FiltersPanel() {
  const f = useFilterStore();
  const SEVERITY_COLORS = useTheme().severity;
  const toggleFilters = useUiStore((s) => s.toggleFilters);
  const moreActive = useMapStore((s) => MORE_LAYERS.filter((l) => s.layers[l.id]).length);
  const [showMore, setShowMore] = useState(false);
  // Los atajos cuentan hacia atrás desde el último dato cargado, no desde hoy
  const { firstDate, lastDate } = useDataCoverage();
  const presets = periodPresets(lastDate);
  const sectionTitle = "hud-title mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-400";
  const active = activeFilterCount(f);

  return (
    <aside className="hud-aside flex w-64 shrink-0 flex-col gap-5 overflow-y-auto border-r border-slate-800 bg-slate-950/85 p-4"
      aria-label="Filtros y capas" data-testid="filters-panel">
      <div className="-mb-2 flex items-center justify-between">
        <p className="text-xs font-semibold text-slate-200">Filtros y capas</p>
        <button onClick={toggleFilters} aria-label="Cerrar filtros" className="text-slate-400 hover:text-slate-200"><X size={14} /></button>
      </div>

      <section>
        <h2 className={sectionTitle}>Capas del mapa</h2>
        <LayerList items={MAIN_LAYERS} />
        <button onClick={() => setShowMore((v) => !v)} aria-expanded={showMore || moreActive > 0}
          className="mt-2 flex items-center gap-1 text-[11px] text-cyan-300 hover:underline">
          <ChevronDown size={12} className={cn("transition-transform", (showMore || moreActive > 0) && "rotate-180")} />
          Más capas{moreActive > 0 && ` (${moreActive} activa${moreActive > 1 ? "s" : ""})`}
        </button>
        {(showMore || moreActive > 0) && <div className="mt-2"><LayerList items={MORE_LAYERS} /></div>}
      </section>

      <section>
        <h2 className={sectionTitle}>Periodo</h2>
        <div className="mb-2 grid grid-cols-4 gap-1">
          {presets.map((p) => (
            <button
              key={p.label}
              onClick={() => f.setDates(p.start, null)}
              aria-pressed={f.startDate === p.start && !f.endDate}
              title={p.start ? `Desde el ${fmtDateTime(p.start)} hasta el último dato` : "Todo el periodo disponible"}
              className={cn("rounded-md border border-slate-700 px-1 py-1 text-[11px] text-slate-300 hover:bg-slate-800",
                f.startDate === p.start && !f.endDate && "border-cyan-600 bg-cyan-900/40 text-cyan-200")}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input type="date" aria-label="Fecha inicial" value={f.startDate ?? ""} min={firstDate?.slice(0, 10)} max={f.endDate ?? lastDate?.slice(0, 10)}
            onChange={(e) => f.setDates(e.target.value || null, f.endDate)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 [color-scheme:dark]" />
          <input type="date" aria-label="Fecha final" value={f.endDate ?? ""} min={f.startDate ?? firstDate?.slice(0, 10)} max={lastDate?.slice(0, 10)}
            onChange={(e) => f.setDates(f.startDate, e.target.value || null)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 [color-scheme:dark]" />
        </div>
        {lastDate && (
          <p className="mt-1.5 text-[10px] text-slate-400" data-testid="data-coverage">
            Datos del {fmtDateTime(firstDate?.slice(0, 10))} al {fmtDateTime(lastDate.slice(0, 10))}
          </p>
        )}
      </section>

      <section>
        <h2 className={sectionTitle}>Hora del día <span className="normal-case text-cyan-300">{f.hourRange[0]}:00 – {f.hourRange[1]}:59</span></h2>
        <Slider.Root
          className="relative flex h-5 w-full touch-none select-none items-center"
          min={0} max={23} step={1} minStepsBetweenThumbs={0}
          value={f.hourRange}
          onValueChange={(v) => f.setHourRange([v[0], v[1]] as [number, number])}
          aria-label="Rango horario"
        >
          <Slider.Track className="relative h-1.5 grow rounded-full bg-slate-800">
            <Slider.Range className="absolute h-full rounded-full bg-cyan-500" />
          </Slider.Track>
          <Slider.Thumb className="block h-4 w-4 rounded-full border-2 border-cyan-400 bg-slate-950" aria-label="Hora inicial" />
          <Slider.Thumb className="block h-4 w-4 rounded-full border-2 border-cyan-400 bg-slate-950" aria-label="Hora final" />
        </Slider.Root>
      </section>

      <section>
        <h2 className={sectionTitle}>Severidad</h2>
        <div className="space-y-1.5">
          {([2, 1, 0] as Severity[]).map((s) => (
            <Box key={s} checked={f.severities.includes(s)} onChange={() => f.toggleSeverity(s)} color={SEVERITY_COLORS[s]}
              label={SEVERITY_LABELS[s]} />
          ))}
          <Box checked={f.workzoneOnly} onChange={() => f.setWorkzoneOnly(!f.workzoneOnly)} label="Sólo en zona de obra" />
        </div>
      </section>

      <button onClick={f.reset} disabled={active === 0}
        className="mt-auto flex items-center justify-center gap-1.5 rounded-lg border border-slate-700 py-1.5 text-xs text-slate-400 hover:bg-slate-800 disabled:opacity-40">
        <RotateCcw size={12} /> Restablecer filtros{active > 0 && ` (${active})`}
      </button>
    </aside>
  );
}
