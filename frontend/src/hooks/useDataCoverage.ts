import { useQuery } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";

/**
 * Rango de fechas que cubren los datos cargados (toda la ciudad, sin filtros).
 * Sirve de ancla para los atajos de periodo y para avisar hasta cuándo hay datos.
 */
export function useDataCoverage() {
  const q = useQuery({
    queryKey: ["kpis", "coverage"],
    queryFn: ({ signal }) => crashService.kpis({}, signal),
    staleTime: Infinity,
  });
  return { firstDate: q.data?.first_date ?? null, lastDate: q.data?.last_date ?? null, query: q };
}
