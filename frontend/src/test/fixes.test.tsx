import { describe, expect, it, beforeEach, vi } from "vitest";
import { render, screen, fireEvent } from "@testing-library/react";
import { chicagoLocalIso, chicagoNow } from "@/lib/chicagoTime";
import { fmtDateTime, orderedRange, periodPresets } from "@/lib/dates";
import { targetYear } from "@/lib/modelLabels";
import { useFilterStore } from "@/stores/useFilterStore";
import { riskStops } from "@/components/map/layers/RiskChoroplethLayer";
import { mergeWeather } from "@/components/analytics/WeatherImpactChart";
import { fillHours } from "@/components/analytics/HourlyDistribution";
import { csvCell, CSV_BOM, toCsv } from "@/components/table/TableExportBar";
import { fitLabel } from "@/components/charts/d3";
import { crashService, toParams } from "@/services/crashService";
import { ErrorBoundary, isChunkError } from "@/components/ErrorBoundary";
import { buildCrashFilter } from "@/hooks/useSpatialFilters";

describe("simulador en hora de Chicago", () => {
  it("toma la fecha y hora de Chicago aunque el navegador esté en otra zona", () => {
    // 2026-11-07 23:30 UTC = 17:30 en Chicago (CST, UTC-6), 18:30 en Bogotá
    expect(chicagoNow(new Date("2026-11-07T23:30:00Z"))).toEqual({ date: "2026-11-07", hour: 17 });
    // 2026-07-01 03:00 UTC = 22:00 del 30 de junio en Chicago (CDT, UTC-5)
    expect(chicagoNow(new Date("2026-07-01T03:00:00Z"))).toEqual({ date: "2026-06-30", hour: 22 });
  });

  it("envía el momento sin zona horaria (la API lo lee como hora de Chicago)", () => {
    expect(chicagoLocalIso("2026-11-07", 18)).toBe("2026-11-07T18:00:00");
    expect(chicagoLocalIso("2026-11-07", 7)).toBe("2026-11-07T07:00:00");
  });
});

describe("periodo", () => {
  it("los atajos cuentan desde el último dato y no desde hoy", () => {
    const p = periodPresets("2026-10-23", new Date(2026, 10, 15));
    expect(p.map((x) => x.start)).toEqual([null, "2025-10-24", "2026-07-26", "2026-09-24"]);
  });

  it("sin cobertura conocida usan la fecha de hoy", () => {
    const p = periodPresets(null, new Date(2026, 10, 15));
    expect(p[3].start).toBe("2026-10-17");
  });

  it("un rango invertido se ordena en vez de pedir un periodo vacío", () => {
    expect(orderedRange("2026-05-01", "2026-01-01")).toEqual(["2026-01-01", "2026-05-01"]);
    expect(orderedRange("2026-01-01", null)).toEqual(["2026-01-01", null]);
    useFilterStore.getState().setDates("2026-05-01", "2026-01-01");
    expect(useFilterStore.getState().startDate).toBe("2026-01-01");
    expect(useFilterStore.getState().endDate).toBe("2026-05-01");
    useFilterStore.getState().reset();
  });

  it("formatea fechas como fecha de calendario (sin corrimiento por UTC)", () => {
    expect(fmtDateTime("2026-01-01")).toMatch(/^1 ene/);
    expect(fmtDateTime("2026-10-23T14:05:00")).toMatch(/23 oct.*2026, 14:05$/);
    expect(fmtDateTime(null)).toBe("—");
  });
});

describe("filtro «sólo zona de obra» en el mapa", () => {
  it("viaja en la URL de teselas para filtrar en el servidor en todos los zooms", () => {
    expect(crashService.tileUrl(null, null, true)).toContain("workzone_only=true");
    expect(crashService.tileUrl("2026-01-01", null, false)).not.toContain("workzone_only");
  });

  it("el filtro GPU de hora y severidad no depende de 'workzone' (ausente en teselas agregadas)", () => {
    expect(JSON.stringify(buildCrashFilter([0, 23], [0, 1, 2]))).not.toContain("workzone");
  });

  it("los límites del mapa se redondean igual en la petición", () => {
    const p = toParams({ bounds: [-87.6312345678, 41.8, -87.6, 41.9] });
    expect(p.min_lon).toBe(-87.63123);
  });
});

describe("textos del modelo", () => {
  it("el año evaluado sale de la ventana del reporte", () => {
    expect(targetYear("historia 2024 -> riesgo 2025")).toBe("2025");
    expect(targetYear("historia 2025 -> riesgo 2026")).toBe("2026");
    expect(targetYear(undefined)).toBeNull();
  });
});

describe("rampa de la rejilla de riesgo", () => {
  const ascending = (s: number[]) => s.every((v, i) => i === 0 || v > s[i - 1]);
  it("siempre es estrictamente creciente", () => {
    expect(ascending(riskStops({ p50: 0, p80: 0.02, p95: 0.05 }))).toBe(true);
    expect(ascending(riskStops({ p50: 0.01, p80: 0.01, p95: 0.01 }))).toBe(true);
    expect(ascending(riskStops(undefined))).toBe(true);
    expect(riskStops({ p50: 0.1, p80: 0.2, p95: 0.3 })).toEqual([0.05, 0.1, 0.2, 0.3]);
  });
});

describe("gráficos", () => {
  it("agrupa climas que se traducen igual con su tasa ponderada", () => {
    const rows = mergeWeather([
      { weather: "CLOUDY", crashes: 100, critical_rate: 0.02 },
      { weather: "CLOUDY/OVERCAST", crashes: 300, critical_rate: 0.01 },
      { weather: "RAIN", crashes: 50, critical_rate: 0.03 },
    ]);
    expect(rows).toHaveLength(2);
    const cloudy = rows.find((r) => r.weather === "Nublado")!;
    expect(cloudy.crashes).toBe(400);
    expect(cloudy.critical_rate).toBeCloseTo(0.0125);
  });

  it("muestra las 24 horas aunque alguna no tenga siniestros", () => {
    const h = fillHours([{ hour: 3, crashes: 5, critical: 1 }]);
    expect(h).toHaveLength(24);
    expect(h[0]).toEqual({ hour: 0, crashes: 0, critical: 0 });
    expect(h[3].crashes).toBe(5);
  });

  it("recorta etiquetas largas para no pisar el valor", () => {
    expect(fitLabel("despejado", "40% de los siniestros", 60)).toEqual({ label: "despejado", note: "40% de los siniestros" });
    const fit = fitLabel("failing to yield right-of-way", "12,5% críticos", 30);
    expect(`${fit.label}${fit.note ? `  ·  ${fit.note}` : ""}`.length).toBeLessThanOrEqual(30);
  });
});

describe("exportación CSV", () => {
  it("añade BOM para Excel y neutraliza fórmulas", () => {
    expect(csvCell("=HYPERLINK(\"x\")")).toBe("\"'=HYPERLINK(\"\"x\"\")\"");
    expect(csvCell("+1")).toBe("'+1");
    expect(csvCell(-87.6)).toBe("-87.6");
    expect(csvCell(null)).toBe("");
    expect(toCsv([]).startsWith(CSV_BOM)).toBe(true);
  });
});

describe("límite de errores", () => {
  beforeEach(() => {
    // React registra el error en consola aunque se capture
    vi.spyOn(console, "error").mockImplementation(() => {});
  });

  it("un fallo en una sección muestra un aviso y no tumba la app", () => {
    let boom = true;
    function Fragile() {
      if (boom) throw new Error("datos inesperados");
      return <p>recuperado</p>;
    }
    render(<div><p>mapa</p><ErrorBoundary area="Explorar"><Fragile /></ErrorBoundary></div>);
    expect(screen.getByText("mapa")).toBeInTheDocument();
    expect(screen.getByRole("alert")).toHaveTextContent("Algo falló en «Explorar»");
    boom = false;
    fireEvent.click(screen.getByText("Reintentar"));
    expect(screen.getByText("recuperado")).toBeInTheDocument();
  });

  it("reconoce un chunk que ya no existe tras un despliegue", () => {
    expect(isChunkError(new TypeError("Failed to fetch dynamically imported module: /assets/x.js"))).toBe(true);
    expect(isChunkError(new Error("otra cosa"))).toBe(false);
  });
});
