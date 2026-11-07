import { describe, expect, it, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { activeFilterCount } from "@/stores/useFilterStore";
import { useUiStore } from "@/stores/useUiStore";
import { GuideInvite } from "@/components/tour/GuideInvite";
import { GUIDE_SEEN_KEY, startFullTour } from "@/components/tour/guide";
import { describe as describeGuide, GUIDE } from "@/components/tour/guideContent";

const base = { startDate: null, endDate: null, hourRange: [0, 23] as [number, number], severities: [0, 1, 2] as (0 | 1 | 2)[], workzoneOnly: false };

describe("pantalla de entrada", () => {
  it("cuenta sólo los filtros distintos de los valores por defecto", () => {
    expect(activeFilterCount(base)).toBe(0);
    expect(activeFilterCount({ ...base, startDate: "2025-01-01", hourRange: [7, 9], severities: [2], workzoneOnly: true })).toBe(4);
  });

  it("los filtros empiezan plegados", () => {
    expect(useUiStore.getState().filtersOpen).toBe(false);
  });
});

describe("guía de uso", () => {
  beforeEach(() => localStorage.clear());

  it("invita en la primera visita sin bloquear y al descartarla no vuelve", () => {
    const first = render(<GuideInvite />);
    expect(screen.getByTestId("guide-invite")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Ahora no"));
    expect(screen.queryByTestId("guide-invite")).toBeNull();
    expect(localStorage.getItem(GUIDE_SEEN_KEY)).toBe("1");
    first.unmount();
    render(<GuideInvite />);
    expect(screen.queryByTestId("guide-invite")).toBeNull();
  });

  it("cada parte explica qué hace y el texto se escapa", () => {
    for (const e of Object.values(GUIDE)) expect(e.hace.length).toBeGreaterThan(10);
    const html = describeGuide({ title: "x", hace: "a <b>", significa: "s", hizo: "h" });
    expect(html).toContain("a &lt;b&gt;");
    expect(html).toContain("Qué significa:");
    expect(html).toContain("Cómo se hizo:");
  });

  it("el recorrido completo abre un globo con su progreso", async () => {
    startFullTour();
    await new Promise((r) => setTimeout(r, 50));
    expect(document.querySelector(".driver-popover-title")?.textContent).toContain("Bienvenido");
    expect(document.querySelector(".driver-popover-progress-text")?.textContent).toMatch(/1 de \d+/);
  });
});
