import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { crashService, type QueryFilters } from "@/services/crashService";
import type { Severity } from "@/types/api";
import { fmtDateTime } from "@/lib/dates";
import { useQueryFilters } from "./useViewportCrashes";

// Fecha de calendario: new Date("YYYY-MM-DD") se leería en UTC y en América mostraría el día anterior
const fmtDate = (s: string | null | undefined) => (s ? fmtDateTime(s.slice(0, 10)) : "—");

const ALL_SEVERITIES: Severity[] = [0, 1, 2];

/**
 * Filtros para calcular tasas: se quitan severidad y "sólo zona de obra". Si no, con
 * el filtro "Crítico" la tasa crítica sería siempre 100% y con "sólo obra" el % en obra
 * también: el numerador dejaría de compararse con el total de siniestros.
 */
export function rateFiltersOf(f: QueryFilters): QueryFilters {
  return { ...f, severities: ALL_SEVERITIES, workzoneOnly: false };
}

export function hasCompositionFilter(f: QueryFilters) {
  return (f.severities?.length ?? 3) < 3 || !!f.workzoneOnly;
}

/**
 * KPIs de la ventana visible y de toda la ciudad, para que cada cifra se lea junto a
 * su comparación:
 * - `local` / `city`: con todos los filtros (conteos: siniestros, fallecidos...).
 * - `localRates` / `cityRates`: sin severidad ni obra (tasas y proporciones).
 */
export function useKpis() {
  const f = useQueryFilters();
  const rf = rateFiltersOf(f);
  const composed = hasCompositionFilter(f);
  const kpis = (filters: QueryFilters, enabled = true) => ({
    queryKey: ["kpis", filters],
    queryFn: ({ signal }: { signal: AbortSignal }) => crashService.kpis(filters, signal),
    enabled,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
  const local = useQuery(kpis(f, !!f.bounds));
  const city = useQuery(kpis({ ...f, bounds: null }));
  // Sin filtros de composición las consultas coinciden y React Query reutiliza la caché
  const localRates = useQuery(kpis(composed ? rf : f, !!f.bounds));
  const cityRates = useQuery(kpis({ ...(composed ? rf : f), bounds: null }));
  const k = local.data;
  const scope = k ? `Ventana visible del mapa · ${fmtDate(k.first_date)} – ${fmtDate(k.last_date)}` : "Ventana visible del mapa";
  return { local, city, localRates, cityRates, scope, filters: f, rateFilters: composed ? rf : f, composed };
}
