import { api } from "./api";
import type { SegmentRiskRequest, SegmentRiskResponse } from "@/types/api";

export const predictionService = {
  segmentRisk: (req: SegmentRiskRequest, signal?: AbortSignal) =>
    api.post<SegmentRiskResponse>("/predict/segment-risk", req, { signal }).then((r) => r.data),
};
