import { useEffect } from "react";
import type { FilterSpecification, Map as MLMap } from "maplibre-gl";
import { useFilterStore } from "@/stores/useFilterStore";
import type { Severity } from "@/types/api";

/** Expresión de filtro evaluada en GPU (sin red ni recolección de basura). */
export function buildCrashFilter(hourRange: [number, number], severities: Severity[], workzoneOnly = false):
  FilterSpecification {
  const all: unknown[] = [
    "all",
    [">=", ["get", "hour"], hourRange[0]],
    ["<=", ["get", "hour"], hourRange[1]],
    ["in", ["get", "severity"], ["literal", severities]],
  ];
  if (workzoneOnly) all.push(["==", ["get", "workzone"], true]);
  return all as FilterSpecification;
}

/** Sincroniza los filtros de la barra lateral con map.setFilter() en las capas indicadas. */
export function useSpatialFilters(map: MLMap | null, loaded: boolean, layerIds: string[]) {
  const hourRange = useFilterStore((s) => s.hourRange);
  const severities = useFilterStore((s) => s.severities);
  useEffect(() => {
    if (!map || !loaded) return;
    // «Sólo zona de obra» va en la URL de teselas (servidor), porque las teselas agregadas
    // de zoom < 13 no traen 'workzone' por punto. Aquí sólo hora y severidad (GPU).
    const filter = buildCrashFilter(hourRange, severities);
    for (const id of layerIds) {
      if (map.getLayer(id)) map.setFilter(id, filter);
    }
  }, [map, loaded, hourRange, severities, layerIds]);
}
