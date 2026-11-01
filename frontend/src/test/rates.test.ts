import { hasCompositionFilter, rateFiltersOf } from "@/hooks/useKpis";

describe("filtros de tasas", () => {
  it("quita severidad y zona de obra pero conserva zona, fechas y horas", () => {
    const f = { bounds: [-87.7, 41.8, -87.6, 41.9] as [number, number, number, number], startDate: "2025-01-01",
      endDate: null, hourRange: [7, 9] as [number, number], severities: [2] as (0 | 1 | 2)[], workzoneOnly: true };
    const r = rateFiltersOf(f);
    expect(r.severities).toEqual([0, 1, 2]);
    expect(r.workzoneOnly).toBe(false);
    expect(r.bounds).toEqual(f.bounds);
    expect(r.startDate).toBe("2025-01-01");
    expect(r.hourRange).toEqual([7, 9]);
  });

  it("detecta cuándo los filtros cambian la composición", () => {
    expect(hasCompositionFilter({ severities: [0, 1, 2], workzoneOnly: false })).toBe(false);
    expect(hasCompositionFilter({ severities: [2] })).toBe(true);
    expect(hasCompositionFilter({ severities: [0, 1, 2], workzoneOnly: true })).toBe(true);
  });
});
