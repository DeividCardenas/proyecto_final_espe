import { useQuery, keepPreviousData } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useKpis } from "@/hooks/useKpis";
import { Card, fmtNumber, fmtPct } from "@/components/ui";
import { RankChart } from "@/components/charts/d3";

const WEATHER_ES: Record<string, string> = {
  CLEAR: "Despejado", RAIN: "Lluvia", SNOW: "Nieve", CLOUDY: "Nublado", "CLOUDY/OVERCAST": "Nublado",
  UNKNOWN: "Desconocido", OTHER: "Otro", "FREEZING RAIN/DRIZZLE": "Lluvia helada", "FOG/SMOKE/HAZE": "Niebla",
  "SLEET/HAIL": "Aguanieve / granizo", "BLOWING SNOW": "Ventisca", "SEVERE CROSS WIND GATE": "Viento cruzado",
  "BLOWING SAND, SOIL, DIRT": "Polvo",
};
// Con menos siniestros la tasa es demasiado inestable para compararla
const MIN_CRASHES = 200;

/** Tasa de siniestros críticos por clima, comparada con la tasa global (posición sobre una escala común). */
export function WeatherImpactChart() {
  // Tasa por clima: sobre todos los siniestros (sin severidad ni obra), si no saldría 100%
  const { rateFilters: f, scope, localRates, composed } = useKpis();
  const { data = [] } = useQuery({
    queryKey: ["weather", f],
    queryFn: () => crashService.weather(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const total = data.reduce((a, d) => a + d.crashes, 0) || 1;
  const rows = data.filter((d) => d.crashes >= MIN_CRASHES).sort((a, b) => b.critical_rate - a.critical_rate);
  const overall = localRates.data?.critical_rate ?? null;
  const worst = rows[0];
  return (
    <Card
      title="¿Con qué clima son más graves?"
      className="col-span-2"
      takeaway={rows.length < 2 ? (
        <>En esta zona no hay suficientes siniestros por clima (≥ {MIN_CRASHES}) para comparar; aleja el mapa.</>
      ) : worst && overall ? (
        <>Con <b>{(WEATHER_ES[worst.weather] ?? worst.weather).toLowerCase()}</b> la tasa crítica es {fmtPct(worst.critical_rate, 2)},{" "}
          {(worst.critical_rate / overall).toLocaleString("es", { maximumFractionDigits: 1 })}× la global.</>
      ) : undefined}
      context={`% de siniestros con fallecidos o lesiones incapacitantes; climas con ≥ ${MIN_CRASHES} siniestros${composed ? " · tasas sin filtros de severidad ni obra" : ""} · ${scope}`}
    >
      <RankChart
        ariaLabel="Tasa de siniestros críticos por condición climática"
        mark="dot"
        data={rows.map((d, i) => ({
          label: WEATHER_ES[d.weather] ?? d.weather,
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
