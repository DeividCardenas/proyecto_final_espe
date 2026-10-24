import { StrictMode, useRef } from "react";
import { act, render } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";

const instances: MockMap[] = [];

class MockMap {
  handlers = new Map<string, Set<(...a: unknown[]) => void>>();
  removed = false;
  triggerRepaint = vi.fn();
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

vi.mock("maplibre-gl", () => ({ default: { Map: vi.fn((o) => new MockMap(o)) } }));

const webgl = { ok: true };

import { useMapLibre } from "@/hooks/useMapLibre";

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
});
