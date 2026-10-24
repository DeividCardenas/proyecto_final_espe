import { api } from "./api";
import type { SegmentRiskRequest, SegmentRiskResponse } from "@/types/api";

export const predictionService = {
  segmentRisk: (req: SegmentRiskRequest) =>
    api.post<SegmentRiskResponse>("/predict/segment-risk", req).then((r) => r.data),
};
