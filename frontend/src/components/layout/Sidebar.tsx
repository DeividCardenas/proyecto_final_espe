import * as Slider from "@radix-ui/react-slider";
import * as Checkbox from "@radix-ui/react-checkbox";
import { Check, RotateCcw } from "lucide-react";
import { format, subDays, subYears } from "date-fns";
import { useFilterStore } from "@/stores/useFilterStore";
import { useMapStore, type LayerId } from "@/stores/useMapStore";
import { cn, SEVERITY_LABELS } from "@/components/ui";
import type { Severity } from "@/types/api";
import { SEVERITY_COLORS } from "@/components/map/layers/CrashHeatmapLayer";

const LAYERS: { id: LayerId; label: string; hint: string }[] = [
  { id: "heatmap", label: "Mapa de calor", hint: "Teselas vectoriales MVT" },
  { id: "points", label: "Siniestros individuales", hint: "Visibles desde zoom 13" },
  { id: "clusters", label: "Clusters dinámicos", hint: "Supercluster en el cliente" },
  { id: "risk", label: "Riesgo predictivo ML", hint: "Rejilla de 500 m" },
  { id: "permits", label: "Obras viales CDOT", hint: "Cierre total/parcial + 250 m" },
  { id: "hotspots", label: "Puntos calientes", hint: "DBSCAN en PostGIS" },
  { id: "aadt", label: "Aforos AADT", hint: "Volumen diario (2006)" },
];

const iso = (d: Date) => format(d, "yyyy-MM-dd");

function Box({ checked, onChange, color, label }: { checked: boolean; onChange: () => void; color?: string; label: string }) {
  return (
    <label className="flex cursor-pointer items-center gap-2 text-xs text-slate-300">
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

export function Sidebar() {
  const f = useFilterStore();
  const { layers, toggleLayer } = useMapStore();
  const today = new Date();
  const presets: { label: string; start: string | null }[] = [
    { label: "Todo", start: null },
    { label: "1 año", start: iso(subYears(today, 1)) },
    { label: "90 días", start: iso(subDays(today, 90)) },
    { label: "30 días", start: iso(subDays(today, 30)) },
  ];
  const sectionTitle = "mb-2 text-[11px] font-semibold uppercase tracking-wider text-slate-500";

  return (
    <aside className="flex w-64 shrink-0 flex-col gap-5 overflow-y-auto border-r border-slate-800 bg-slate-950 p-4">
      <section>
        <h2 className={sectionTitle}>Periodo</h2>
        <div className="mb-2 grid grid-cols-4 gap-1">
          {presets.map((p) => (
            <button
              key={p.label}
              onClick={() => f.setDates(p.start, null)}
              className={cn("rounded-md border border-slate-700 px-1 py-1 text-[11px] text-slate-300 hover:bg-slate-800",
                f.startDate === p.start && !f.endDate && "border-cyan-600 bg-cyan-900/40 text-cyan-200")}
            >
              {p.label}
            </button>
          ))}
        </div>
        <div className="grid grid-cols-2 gap-2">
          <input type="date" aria-label="Fecha inicial" value={f.startDate ?? ""} max={f.endDate ?? undefined}
            onChange={(e) => f.setDates(e.target.value || null, f.endDate)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 [color-scheme:dark]" />
          <input type="date" aria-label="Fecha final" value={f.endDate ?? ""} min={f.startDate ?? undefined}
            onChange={(e) => f.setDates(f.startDate, e.target.value || null)}
            className="rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200 [color-scheme:dark]" />
        </div>
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
        <p className="mt-1 text-[10px] text-slate-500">Filtrado en GPU con map.setFilter (sin red)</p>
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

      <section>
        <h2 className={sectionTitle}>Capas</h2>
        <div className="space-y-2">
          {LAYERS.map((l) => (
            <div key={l.id}>
              <Box checked={layers[l.id]} onChange={() => toggleLayer(l.id)} label={l.label} />
              <p className="ml-6 text-[10px] text-slate-500">{l.hint}</p>
            </div>
          ))}
        </div>
      </section>

      <button onClick={f.reset} className="mt-auto flex items-center justify-center gap-1.5 rounded-lg border border-slate-700 py-1.5 text-xs text-slate-400 hover:bg-slate-800">
        <RotateCcw size={12} /> Restablecer filtros
      </button>
    </aside>
  );
}
