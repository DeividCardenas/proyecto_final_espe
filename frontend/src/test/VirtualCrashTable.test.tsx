import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { VirtualCrashTable } from "@/components/table/VirtualCrashTable";
import { toCsv } from "@/components/table/TableExportBar";
import type { CrashFeature } from "@/types/api";

function makeRows(n: number): CrashFeature[] {
  return Array.from({ length: n }, (_, i) => ({
    type: "Feature",
    geometry: { type: "Point", coordinates: [-87.63 + i * 1e-5, 41.88] },
    properties: {
      id: `c${i}`, date: "2025-01-01T10:00", hour: 10, dow: 3, severity: (i % 3) as 0 | 1 | 2, injuries: i % 2, fatal: 0,
      weather: "CLEAR", lighting: "DAYLIGHT", speed: 30, cause: "UNABLE TO DETERMINE", street: `${i} N STATE ST`,
      crash_type: "REAR END", workzone: false, aadt: 15000,
    },
  }));
}

describe("VirtualCrashTable", () => {
  it("renderiza menos de 40 filas en el DOM para 10.000 registros", () => {
    render(<VirtualCrashTable rows={makeRows(10_000)} height={600} />);
    const rendered = screen.getAllByRole("row");
    expect(rendered.length).toBeGreaterThan(0);
    expect(rendered.length).toBeLessThanOrEqual(40);
  });
});

describe("toCsv", () => {
  it("escapa comas y comillas y añade coordenadas", () => {
    const rows = makeRows(1);
    rows[0].properties.street = 'AV "X", 5';
    const csv = toCsv(rows).split("\n");
    expect(csv[0].endsWith("lon,lat")).toBe(true);
    expect(csv[1]).toContain('"AV ""X"", 5"');
  });
});
