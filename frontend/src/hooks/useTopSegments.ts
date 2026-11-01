import { useQuery } from "@tanstack/react-query";
import { crashService } from "@/services/crashService";

/** Proporción de cuadras priorizadas que se muestran: la misma con la que se valida el modelo (top 10%). */
export const PRIORITY_SHARE = 0.1;

/** Cuadras del top 10% por P(riesgo Alto): lo que el mapa y la lista muestran. */
export function useTopSegments(enabled = true) {
  const metrics = useQuery({ queryKey: ["segment-metrics"], queryFn: crashService.segmentMetrics, staleTime: Infinity });
  const scored = metrics.data?.forecast.segments_scored;
  const limit = scored ? Math.ceil(scored * PRIORITY_SHARE) : 0;
  const segments = useQuery({
    queryKey: ["segments", limit],
    queryFn: () => crashService.segments(limit),
    enabled: enabled && limit > 0,
    staleTime: Infinity,
  });
  return { metrics, segments, limit };
}
