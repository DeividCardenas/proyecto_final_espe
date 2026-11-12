import { StrictMode, useRef } from "react";
import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const instances: MockMap[] = [];

class MockMap {
  handlers = new Map<string, Set<(...a: unknown[]) => void>>();
  removed = false;
  triggerRepaint = vi.fn();
  setStyle = vi.fn();
  constructor(public opts: Record<string, unknown>) {
    instances.push(this);
  }
  on(ev: string, fn: (...a: unknown[]) => void) {
    if (!this.handlers.has(ev)) this.handlers.set(ev, new Set());
    this.handlers.get(ev)!.add(fn);
    return this;
  }
  off(ev: string, fn: (...a: unknown[]) => void) {
    this.handlers.get(ev)?.delete(fn);
    return this;
  }
  emit(ev: string, payload: unknown = {}) {
    this.handlers.get(ev)?.forEach((fn) => fn(payload));
  }
  remove() {
    this.removed = true;
  }
}

vi.mock("maplibre-gl", () => ({ Map: vi.fn((o) => new MockMap(o)) }));

const webgl = { ok: true };

import { BASEMAP_TIMEOUT_MS, FALLBACK_STYLE, useMapLibre } from "@/hooks/useMapLibre";

function Harness({ onState }: { onState: (s: ReturnType<typeof useMapLibre>) => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const state = useMapLibre(ref, { style: "about:blank" });
  onState(state);
  return <div ref={ref} />;
}

describe("useMapLibre", () => {
  beforeEach(() => {
    instances.length = 0;
    webgl.ok = true;
    HTMLCanvasElement.prototype.getContext = vi.fn(() => (webgl.ok ? ({} as RenderingContext) : null)) as never;
  });

  it("destruye la instancia con map.remove() y desuscribe 'load' al desmontar", () => {
    const { unmount } = render(<Harness onState={() => {}} />);
    expect(instances).toHaveLength(1);
    const map = instances[0];
    unmount();
    expect(map.removed).toBe(true);
    expect(map.handlers.get("load")?.size ?? 0).toBe(0);
  });

  it("sobrevive al doble montaje de StrictMode sin fugas (sólo una instancia viva)", () => {
    const { unmount } = render(<StrictMode><Harness onState={() => {}} /></StrictMode>);
    const alive = instances.filter((m) => !m.removed);
    expect(alive).toHaveLength(1);
    unmount();
    expect(instances.every((m) => m.removed)).toBe(true);
  });

  it("previene el comportamiento por defecto al perder el contexto WebGL y repinta al restaurarlo", () => {
    let last: ReturnType<typeof useMapLibre> | null = null;
    render(<Harness onState={(s) => (last = s)} />);
    const map = instances[0];
    const preventDefault = vi.fn();
    act(() => map.emit("webglcontextlost", { originalEvent: { preventDefault } }));
    expect(preventDefault).toHaveBeenCalled();
    act(() => map.emit("webglcontextrestored"));
    expect(map.triggerRepaint).toHaveBeenCalled();
    expect(last).not.toBeNull();
  });

  it("no instancia el mapa si no hay WebGL2", () => {
    webgl.ok = false;
    let last: ReturnType<typeof useMapLibre> | null = null;
    render(<Harness onState={(s) => (last = s)} />);
    expect(instances).toHaveLength(0);
    expect(last!.webGlSupported).toBe(false);
  });

  it("pasa al mapa base de respaldo si el estilo externo falla antes de cargar", () => {
    let last: ReturnType<typeof useMapLibre> | null = null;
    render(<Harness onState={(st) => (last = st)} />);
    const map = instances[0];
    act(() => map.emit("error", { error: new Error("Failed to fetch style") }));
    expect(map.setStyle).toHaveBeenCalledWith(FALLBACK_STYLE);
    expect(last!.basemapFallback).toBe(true);
    // Un segundo error no vuelve a cambiar el estilo
    act(() => map.emit("error", { error: new Error("otro") }));
    expect(map.setStyle).toHaveBeenCalledTimes(1);
  });

  it("no confunde un fallo de tesela con un fallo del mapa base", () => {
    let last: ReturnType<typeof useMapLibre> | null = null;
    render(<Harness onState={(st) => (last = st)} />);
    const map = instances[0];
    act(() => map.emit("style.load"));
    act(() => map.emit("error", { error: new Error("tile 404") }));
    expect(map.setStyle).not.toHaveBeenCalled();
    expect(last!.basemapFallback).toBe(false);
  });

  it("usa el respaldo si el estilo no llega a tiempo, y no si ya llegó", () => {
    vi.useFakeTimers();
    try {
      render(<Harness onState={() => {}} />);
      const slow = instances[0];
      act(() => { vi.advanceTimersByTime(BASEMAP_TIMEOUT_MS + 1); });
      expect(slow.setStyle).toHaveBeenCalledWith(FALLBACK_STYLE);

      instances.length = 0;
      render(<Harness onState={() => {}} />);
      const fast = instances[0];
      act(() => fast.emit("style.load"));
      act(() => { vi.advanceTimersByTime(BASEMAP_TIMEOUT_MS + 1); });
      expect(fast.setStyle).not.toHaveBeenCalled();
    } finally {
      vi.useRealTimers();
    }
  });
});
