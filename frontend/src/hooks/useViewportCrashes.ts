import { useMemo } from "react";
import { useShallow } from "zustand/react/shallow";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { crashService, roundBounds, type QueryFilters } from "@/services/crashService";
import { useFilterStore } from "@/stores/useFilterStore";
import { useMapStore } from "@/stores/useMapStore";
import { useDebounce } from "./useDebounce";

/**
 * Filtros activos + ventana del mapa, con debounce de 250 ms para peticiones al backend.
 * Los límites se redondean igual que en la petición, para que la clave de caché coincida.
 */
export function useQueryFilters(): QueryFilters {
  const rawBounds = useMapStore((s) => s.bounds);
  const { startDate, endDate, hourRange, severities, workzoneOnly } = useFilterStore(
    useShallow((s) => ({
      startDate: s.startDate, endDate: s.endDate, hourRange: s.hourRange, severities: s.severities, workzoneOnly: s.workzoneOnly,
    })),
  );
  const bounds = useMemo(() => (rawBounds ? roundBounds(rawBounds) : null), [rawBounds]);
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
    queryFn: ({ signal }) => crashService.geojson(f, VIEWPORT_LIMIT, signal),
    enabled: enabled && !!f.bounds,
    placeholderData: keepPreviousData,
    staleTime: 60_000,
  });
}
