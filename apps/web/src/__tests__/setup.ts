// apps/web/src/__tests__/setup.ts
// Setup global pour les tests Vitest
// Importe les matchers jest-dom pour les assertions DOM
import "@testing-library/jest-dom";
import { afterEach } from "vitest";

// Mock de window.matchMedia (non disponible dans jsdom)
Object.defineProperty(window, "matchMedia", {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => undefined,
    removeListener: () => undefined,
    addEventListener: () => undefined,
    removeEventListener: () => undefined,
    dispatchEvent: () => true,
  }),
});

// Mock de window.ResizeObserver (non disponible dans jsdom)
global.ResizeObserver = class ResizeObserver {
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Mock de IntersectionObserver (non disponible dans jsdom)
global.IntersectionObserver = class IntersectionObserver {
  readonly root = null;
  readonly rootMargin = "";
  readonly thresholds: readonly number[] = [];
  observe() {}
  unobserve() {}
  disconnect() {}
  takeRecords() {
    return [];
  }
};

// Nettoyage après chaque test
afterEach(() => {
  // Nettoyer sessionStorage et localStorage entre les tests
  sessionStorage.clear();
  localStorage.clear();
});
