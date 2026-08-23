import "@testing-library/jest-dom/vitest";
import { cleanup } from "@testing-library/react";
import { afterEach, vi } from "vitest";

// DOM nach jedem Test aufräumen (unabhängig von globals)
afterEach(() => cleanup());

// Mantine nutzt matchMedia in jsdom nicht nativ → Polyfill
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }),
});

// ResizeObserver für Mantine-Komponenten absichern
if (typeof window.ResizeObserver === "undefined") {
  class ResizeObserverMock {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  window.ResizeObserver = ResizeObserverMock as unknown as typeof ResizeObserver;
}

// Floating-UI (Mantine-Dropdowns) braucht reale Maße; jsdom liefert 0×0.
const originalGetRect = Element.prototype.getBoundingClientRect;
Element.prototype.getBoundingClientRect = function () {
  const rect = originalGetRect.call(this);
  if (rect.width === 0 && rect.height === 0) {
    return {
      ...rect,
      top: 0,
      left: 0,
      right: 200,
      bottom: 24,
      width: 200,
      height: 24,
      x: 0,
      y: 0,
    } as DOMRect;
  }
  return rect;
};
