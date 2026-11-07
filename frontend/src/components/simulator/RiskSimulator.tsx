import { useMemo, useState } from "react";
import * as Slider from "@radix-ui/react-slider";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useShallow } from "zustand/react/shallow";
import { MapPin, MousePointerClick } from "lucide-react";
import { predictionService } from "@/services/predictionService";
import { useUiStore } from "@/stores/useUiStore";
import { useDebounce } from "@/hooks/useDebounce";
import { Card, cn, fmtPct } from "@/components/ui";
import type { LightingInput, SegmentRiskRequest, WeatherInput } from "@/types/api";
import { RiskGauge } from "./RiskGauge";
import { chicagoLocalIso, chicagoNow } from "@/lib/chicagoTime";
import { modelLabel } from "@/lib/modelLabels";

const WEATHER: { v: WeatherInput; l: string }[] = [
  { v: "CLEAR", l: "Despejado" }, { v: "RAIN", l: "Lluvia" }, { v: "SNOW", l: "Nieve" }, { v: "FOG", l: "Niebla" },
];
const LIGHT: { v: LightingInput; l: string }[] = [
  { v: "DAY", l: "Día" }, { v: "DARK_LIGHTED", l: "Noche iluminada" }, { v: "DARK", l: "Noche oscura" }, { v: "DUSK_DAWN", l: "Amanecer/ocaso" },
];
const DEFAULT_POINT: [number, number] = [-87.6298, 41.8781];
const CRASH_TYPES = ["", "PEDESTRIAN", "PEDALCYCLIST", "ANGLE", "REAR END", "TURNING", "HEAD ON", "FIXED OBJECT", "SIDESWIPE SAME DIRECTION"];

function Seg<T extends string>({ options, value, onChange }: { options: { v: T; l: string }[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="grid grid-cols-2 gap-1">
      {options.map((o) => (
        <button key={o.v} onClick={() => onChange(o.v)}
          className={cn("rounded-md border border-slate-700 px-2 py-1 text-[11px] text-slate-300 hover:bg-slate-800",
            value === o.v && "border-cyan-600 bg-cyan-900/40 text-cyan-100")}>
          {o.l}
        </button>
      ))}
    </div>
  );
}

export function RiskSimulator() {
  const { simulatorPoint, setSimulatorPoint, pickingPoint, setPickingPoint } = useUiStore(useShallow((s) => ({
    simulatorPoint: s.simulatorPoint, setSimulatorPoint: s.setSimulatorPoint, pickingPoint: s.pickingPoint, setPickingPoint: s.setPickingPoint,
  })));
  const [speed, setSpeed] = useState(30);
  const [weather, setWeather] = useState<WeatherInput>("CLEAR");
  const [lighting, setLighting] = useState<LightingInput>("DAY");
  const [workzone, setWorkzone] = useState(false);
  const [crashType, setCrashType] = useState("");
  // Fecha y hora de Chicago, no las del navegador: el escenario se evalúa en hora local de Chicago
  const [today] = useState(() => chicagoNow().date);
  const [hour, setHour] = useState(() => chicagoNow().hour);

  const point = simulatorPoint ?? DEFAULT_POINT;
  // Objeto memoizado: sólo cambia cuando cambia una entrada (evita peticiones en bucle)
  const draft = useMemo<SegmentRiskRequest>(() => {
    return {
      coordinates: point,
      posted_speed_limit: speed,
      weather_condition: weather,
      lighting_condition: lighting,
      active_workzone: workzone,
      first_crash_type: crashType || null,
      // Sin zona horaria: la API lo interpreta como hora de Chicago (toISOString() lo pasaba a UTC)
      when: chicagoLocalIso(today, hour),
    };
  }, [point, speed, weather, lighting, workzone, crashType, hour, today]);
  const request = useDebounce(draft, 250);

  // Consulta (no mutación): cachea escenarios repetidos y cancela la petición anterior al mover un control
  const prediction = useQuery({
    queryKey: ["segment-risk", request],
    queryFn: ({ signal }) => predictionService.segmentRisk(request, signal),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
  });
  const r = prediction.data;

  return (
    <div className="space-y-3" data-testid="risk-simulator">
      <Card title="Ubicación del tramo" tourId="sim-location">
        <div className="flex items-center gap-2 text-[11px] text-slate-300">
          <MapPin size={14} className="text-cyan-400" />
          <span className="tabular-nums">{point[1].toFixed(5)}, {point[0].toFixed(5)}</span>
          {!simulatorPoint && <span className="text-slate-400">(Loop por defecto)</span>}
        </div>
        <div className="mt-2 flex gap-2">
          <button onClick={() => setPickingPoint(!pickingPoint)}
            className={cn("flex flex-1 items-center justify-center gap-1 rounded-md border px-2 py-1.5 text-[11px]",
              pickingPoint ? "border-cyan-500 bg-cyan-900/50 text-cyan-100" : "border-slate-700 text-slate-300 hover:bg-slate-800")}>
            <MousePointerClick size={12} />{pickingPoint ? "Haga clic en el mapa…" : "Elegir en el mapa"}
          </button>
          {simulatorPoint && <button onClick={() => setSimulatorPoint(null)} className="rounded-md border border-slate-700 px-2 text-[11px] text-slate-400">Reiniciar</button>}
        </div>
      </Card>

      <Card title={`Límite de velocidad · ${speed} mph`}>
        <Slider.Root className="relative flex h-5 items-center" min={5} max={55} step={5} value={[speed]}
          onValueChange={(v) => setSpeed(v[0])} aria-label="Límite de velocidad">
          <Slider.Track className="relative h-1.5 grow rounded-full bg-slate-800"><Slider.Range className="absolute h-full rounded-full bg-cyan-500" /></Slider.Track>
          <Slider.Thumb className="block h-4 w-4 rounded-full border-2 border-cyan-400 bg-slate-950" aria-label="mph" />
        </Slider.Root>
      </Card>
      <Card title={`Hora en Chicago · ${hour}:00`}>
        <Slider.Root className="relative flex h-5 items-center" min={0} max={23} step={1} value={[hour]}
          onValueChange={(v) => setHour(v[0])} aria-label="Hora">
          <Slider.Track className="relative h-1.5 grow rounded-full bg-slate-800"><Slider.Range className="absolute h-full rounded-full bg-cyan-500" /></Slider.Track>
          <Slider.Thumb className="block h-4 w-4 rounded-full border-2 border-cyan-400 bg-slate-950" aria-label="hora" />
        </Slider.Root>
      </Card>
      <Card title="Clima"><Seg options={WEATHER} value={weather} onChange={setWeather} /></Card>
      <Card title="Iluminación"><Seg options={LIGHT} value={lighting} onChange={setLighting} /></Card>
      <Card title="Contexto">
        <label className="flex items-center gap-2 text-[11px] text-slate-300">
          <input type="checkbox" checked={workzone} onChange={(e) => setWorkzone(e.target.checked)} className="accent-orange-500" />
          Obra vial CDOT activa a menos de 250 m
        </label>
        <select value={crashType} onChange={(e) => setCrashType(e.target.value)} aria-label="Tipo de colisión"
          className="mt-2 w-full rounded-md border border-slate-700 bg-slate-900 px-2 py-1 text-[11px] text-slate-200">
          {CRASH_TYPES.map((t) => <option key={t} value={t}>{t ? t.toLowerCase() : "Tipo de colisión: promedio histórico"}</option>)}
        </select>
      </Card>

      <Card title="Riesgo predicho" tourId="sim-result" right={r && <span className="text-[10px] text-slate-400">{r.model.mode === "ml" ? modelLabel(r.model.algorithm) : "heurístico"} · {r.inference_ms} ms</span>}>
        {prediction.isError && (
          <p role="alert" className="text-xs text-amber-300">
            No se pudo calcular la predicción.{" "}
            <button onClick={() => void prediction.refetch()} className="underline">Reintentar</button>
          </p>
        )}
        {r && (
          <div className="flex flex-col items-center">
            <RiskGauge score={r.critical_score} label={`${r.risk_level} · ${fmtPct(r.critical_score)} crítico`} />
            {r.critical_alert && <p className="mb-1 rounded bg-red-600/20 px-2 py-0.5 text-[11px] text-red-300">Alerta: supera el umbral óptimo del modelo</p>}
            <div className="mt-1 grid w-full grid-cols-3 gap-1 text-center text-[11px]">
              {Object.entries(r.probabilities).map(([k, v]) => (
                <div key={k} className="rounded bg-slate-800/80 py-1"><p className="text-slate-400">{k}</p><p className="font-semibold tabular-nums text-slate-100">{fmtPct(v)}</p></div>
              ))}
            </div>
            <ul className="mt-3 w-full space-y-1 text-[11px]">
              {r.top_factors.map((f) => (
                <li key={f.feature} className="flex justify-between text-slate-300">
                  <span>{f.feature}</span>
                  <span className={f.direction === "aumenta" ? "text-red-300" : "text-emerald-300"}>{f.direction === "aumenta" ? "▲" : "▼"} {Math.abs(f.contribution).toFixed(3)}</span>
                </li>
              ))}
            </ul>
            <p className="mt-2 w-full text-[10px] text-slate-400">
              AADT {String(r.context.aadt_volume ?? "—")}{r.context.aadt_imputed ? " (imputado)" : ""} · {String(r.context.cell_crashes_per_year ?? "—")} siniestros/año en la celda
            </p>
          </div>
        )}
      </Card>
    </div>
  );
}
