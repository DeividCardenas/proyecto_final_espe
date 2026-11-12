import { useMemo } from "react";
import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { RankChart } from "@/components/charts/d3";
import type { WeatherRow } from "@/types/api";

const WEATHER_ES: Record<string, string> = {
  CLEAR: "Despejado", RAIN: "Lluvia", SNOW: "Nieve", CLOUDY: "Nublado", "CLOUDY/OVERCAST": "Nublado",
  UNKNOWN: "Desconocido", OTHER: "Otro", "FREEZING RAIN/DRIZZLE": "Lluvia helada", "FOG/SMOKE/HAZE": "Niebla",
  "SLEET/HAIL": "Aguanieve / granizo", "BLOWING SNOW": "Ventisca", "SEVERE CROSS WIND GATE": "Viento cruzado",
  "BLOWING SAND, SOIL, DIRT": "Polvo",
};
// Con menos siniestros la tasa es demasiado inestable para compararla
const MIN_CRASHES = 200;

/**
 * Agrupa las categorías que se traducen igual (CLOUDY y CLOUDY/OVERCAST → «Nublado»):
 * suma siniestros y recalcula la tasa crítica ponderada, para no repetir filas.
 */
export function mergeWeather(rows: WeatherRow[]): WeatherRow[] {
  const acc = new Map<string, { crashes: number; critical: number }>();
  for (const r of rows) {
    const label = WEATHER_ES[r.weather] ?? r.weather;
    const a = acc.get(label) ?? { crashes: 0, critical: 0 };
    a.crashes += r.crashes;
    a.critical += r.critical_rate * r.crashes;
    acc.set(label, a);
  }
  return [...acc].map(([weather, a]) => ({ weather, crashes: a.crashes, critical_rate: a.crashes ? a.critical / a.crashes : 0 }));
}

/** Tasa de siniestros críticos por clima, comparada con la tasa global (posición sobre una escala común). */
export function WeatherImpactChart() {
  // Tasa por clima: sobre todos los siniestros (sin severidad ni obra), si no saldría 100%
  const { rateFilters: f, scope, localRates, composed } = useKpis();
  const query = useQuery({
    queryKey: ["weather", f],
    queryFn: ({ signal }) => crashService.weather(f, signal),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const data = useMemo(() => mergeWeather(query.data ?? []), [query.data]);
  const total = data.reduce((a, d) => a + d.crashes, 0) || 1;
  const rows = data.filter((d) => d.crashes >= MIN_CRASHES).sort((a, b) => b.critical_rate - a.critical_rate);
  const overall = localRates.data?.critical_rate ?? null;
  const worst = rows[0];
  return (
    <Card
      title="¿Con qué clima son más graves?"
      className="col-span-2"
      error={query.isError}
      onRetry={() => void query.refetch()}
      takeaway={query.isLoading ? undefined : rows.length < 2 ? (
        <>En esta zona no hay suficientes siniestros por clima (≥ {MIN_CRASHES}) para comparar; aleja el mapa.</>
      ) : worst && overall ? (
        <>Con <b>{worst.weather.toLowerCase()}</b> la tasa crítica es {fmtPct(worst.critical_rate, 2)},{" "}
          {(worst.critical_rate / overall).toLocaleString("es", { maximumFractionDigits: 1 })}× la global.</>
      ) : undefined}
      context={`% de siniestros con fallecidos o lesiones incapacitantes; climas con ≥ ${MIN_CRASHES} siniestros${composed ? " · tasas sin filtros de severidad ni obra" : ""} · ${scope}`}
    >
      <RankChart
        ariaLabel="Tasa de siniestros críticos por condición climática"
        mark="dot"
        data={rows.map((d, i) => ({
          label: d.weather,
          value: d.critical_rate,
          note: `${d.crashes / total < 0.01 ? "<1%" : fmtPct(d.crashes / total, 0)} de los siniestros (${fmtNumber(d.crashes)})`,
          highlight: i === 0,
        }))}
        format={(v) => fmtPct(v, 2)}
        reference={overall ? { value: overall, label: `global ${fmtPct(overall, 2)}` } : undefined}
      />
    </Card>
  );
}
