import { afterEach, beforeEach, describe, expect, it } from "vitest";
import { act, fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MobileTabBar } from "@/components/layout/Header";
import { useUiStore } from "@/stores/useUiStore";
import { isMobileViewport } from "@/hooks/useIsMobile";

const setViewport = (mobile: boolean) => {
  window.matchMedia = ((q: string) => ({
    matches: mobile, media: q, onchange: null,
    addEventListener: () => {}, removeEventListener: () => {}, addListener: () => {}, removeListener: () => {}, dispatchEvent: () => false,
  })) as unknown as typeof window.matchMedia;
};

describe("interfaz móvil", () => {
  beforeEach(() => useUiStore.setState({ activeTab: "segments", panelOpen: true, drawerOpen: false, sheet: "half" }));
  afterEach(() => setViewport(false));

  it("detecta el ancho de teléfono con matchMedia y no falla sin él", () => {
    setViewport(true);
    expect(isMobileViewport()).toBe(true);
    // @ts-expect-error jsdom sin matchMedia
    window.matchMedia = undefined;
    expect(isMobileViewport()).toBe(false);
  });

  it("abrir la tabla cierra el panel y elegir una sección cierra la tabla", () => {
    render(<QueryClientProvider client={new QueryClient()}><MobileTabBar /></QueryClientProvider>);
    fireEvent.click(screen.getByRole("button", { name: "Tabla" }));
    expect(useUiStore.getState()).toMatchObject({ drawerOpen: true, panelOpen: false });
    fireEvent.click(screen.getByRole("button", { name: "Explorar" }));
    expect(useUiStore.getState()).toMatchObject({ drawerOpen: false, panelOpen: true, activeTab: "analytics" });
  });

  it("la hoja se pliega al elegir punto en el mapa y vuelve a media pantalla al abrir una sección", () => {
    act(() => useUiStore.getState().setPickingPoint(true));
    expect(useUiStore.getState().sheet).toBe("peek");
    act(() => useUiStore.getState().setTab("model"));
    expect(useUiStore.getState().sheet).toBe("half");
  });
});
