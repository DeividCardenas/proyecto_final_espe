import { useMemo } from "react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { crashService, type QueryFilters } from "@/services/crashService";
import { useFilterStore } from "@/stores/useFilterStore";
import { useMapStore } from "@/stores/useMapStore";
import { useDebounce } from "./useDebounce";

/** Filtros activos + ventana del mapa, con debounce de 250 ms para peticiones al backend. */
export function useQueryFilters(): QueryFilters {
  const bounds = useMapStore((s) => s.bounds);
  const startDate = useFilterStore((s) => s.startDate);
  const endDate = useFilterStore((s) => s.endDate);
  const hourRange = useFilterStore((s) => s.hourRange);
  const severities = useFilterStore((s) => s.severities);
  const workzoneOnly = useFilterStore((s) => s.workzoneOnly);
  const value = useMemo(
    () => ({ bounds, startDate, endDate, hourRange, severities, workzoneOnly }),
    [bounds, startDate, endDate, hourRange, severities, workzoneOnly],
  );
  return useDebounce(value, 250);
}

export const VIEWPORT_LIMIT = 10_000;

/** Siniestros más recientes de la ventana visible (tabla virtualizada y clusters). */
export function useViewportCrashes(enabled = true) {
  const f = useQueryFilters();
  return useQuery({
    queryKey: ["crashes-viewport", f],
    queryFn: () => crashService.geojson(f, VIEWPORT_LIMIT),
    enabled: enabled && !!f.bounds,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}
