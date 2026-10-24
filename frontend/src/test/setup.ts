import "@testing-library/jest-dom/vitest";

// jsdom no implementa ResizeObserver (requerido por Radix y TanStack Virtual)
class ResizeObserverMock {
  observe() {}
  unobserve() {}
  disconnect() {}
}
globalThis.ResizeObserver ??= ResizeObserverMock as unknown as typeof ResizeObserver;
