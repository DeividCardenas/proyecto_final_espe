import { describe, expect, it, beforeEach } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { activeFilterCount } from "@/stores/useFilterStore";
import { useUiStore } from "@/stores/useUiStore";
import { GuidedTour, TOUR_KEY } from "@/components/tour/GuidedTour";

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

describe("recorrido guiado", () => {
  const renderTour = () =>
    render(
      <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false, enabled: false } } })}>
        <GuidedTour />
      </QueryClientProvider>,
    );

  beforeEach(() => {
    localStorage.clear();
    useUiStore.setState({ tourOpen: false });
  });

  it("se abre en la primera visita y al saltarlo no vuelve a abrirse", () => {
    const first = renderTour();
    expect(screen.getByTestId("guided-tour")).toBeInTheDocument();
    expect(screen.getByText("Dónde")).toBeInTheDocument();
    fireEvent.click(screen.getByText("Saltar"));
    expect(screen.queryByTestId("guided-tour")).toBeNull();
    expect(localStorage.getItem(TOUR_KEY)).toBe("1");
    first.unmount();
    renderTour();
    expect(screen.queryByTestId("guided-tour")).toBeNull();
  });

  it("avanza por los tres pasos", () => {
    renderTour();
    fireEvent.click(screen.getByText(/Siguiente/));
    expect(screen.getByText("Por qué")).toBeInTheDocument();
    fireEvent.click(screen.getByText(/Siguiente/));
    expect(screen.getByText("Qué hacer")).toBeInTheDocument();
    expect(screen.getByText("Empezar")).toBeInTheDocument();
  });
});
