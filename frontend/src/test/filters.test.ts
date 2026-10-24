import { beforeEach, describe, expect, it } from "vitest";
import { buildCrashFilter } from "@/hooks/useSpatialFilters";
import { useFilterStore } from "@/stores/useFilterStore";
import { toParams } from "@/services/crashService";

describe("buildCrashFilter", () => {
  it("genera una expresión GPU con rango horario y severidades", () => {
    expect(buildCrashFilter([7, 9], [2])).toEqual([
      "all",
      [">=", ["get", "hour"], 7],
      ["<=", ["get", "hour"], 9],
      ["in", ["get", "severity"], ["literal", [2]]],
    ]);
  });
});

describe("useFilterStore", () => {
  beforeEach(() => useFilterStore.getState().reset());

  it("nunca deja la selección de severidad vacía", () => {
    const s = useFilterStore.getState();
    s.toggleSeverity(0);
    s.toggleSeverity(1);
    s.toggleSeverity(2);
    expect(useFilterStore.getState().severities).toEqual([2]);
  });
});

describe("toParams", () => {
  it("omite filtros por defecto y serializa el BBOX", () => {
    expect(toParams({ bounds: [-87.7, 41.8, -87.6, 41.9], hourRange: [0, 23], severities: [0, 1, 2] })).toEqual({
      min_lon: -87.7, min_lat: 41.8, max_lon: -87.6, max_lat: 41.9,
    });
    expect(toParams({ hourRange: [8, 10], severities: [2], workzoneOnly: true })).toEqual({
      hour_from: 8, hour_to: 10, severity: [2], workzone_only: true,
    });
  });
});
