import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";
import { useQueryFilters } from "./useViewportCrashes";

const fmtDate = (s: string | null | undefined) =>
  s ? new Date(s).toLocaleDateString("es", { day: "numeric", month: "short", year: "numeric" }) : "—";

/**
 * KPIs de la ventana visible y de toda la ciudad con los mismos filtros, para que
 * cada cifra se lea junto a su comparación, y el texto de ámbito/periodo.
 */
export function useKpis() {
  const f = useQueryFilters();
  const local = useQuery({
    queryKey: ["kpis", f],
    queryFn: () => crashService.kpis(f),
    enabled: !!f.bounds,
    placeholderData: keepPreviousData,
  });
  const cityFilters = { ...f, bounds: null };
  const city = useQuery({
    queryKey: ["kpis", cityFilters],
    queryFn: () => crashService.kpis(cityFilters),
    placeholderData: keepPreviousData,
    staleTime: 5 * 60_000,
  });
  const k = local.data;
  const scope = k ? `Ventana visible del mapa · ${fmtDate(k.first_date)} – ${fmtDate(k.last_date)}` : "Ventana visible del mapa";
  return { local, city, scope, filters: f };
}
