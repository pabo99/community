// Vitest global setup.
//
// jsdom does not implement window.matchMedia, which some PrimeVue components
// (e.g. Select) call on mount. Provide a minimal no-op polyfill so component
// tests can mount those components.
import { vi } from "vitest";

if (!window.matchMedia) {
  window.matchMedia = vi.fn().mockImplementation((query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: vi.fn(),
    removeListener: vi.fn(),
    addEventListener: vi.fn(),
    removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  }));
}
