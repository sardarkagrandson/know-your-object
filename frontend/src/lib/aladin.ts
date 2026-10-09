import type { AladinStatic } from "aladin-lite";

let loader: Promise<AladinStatic> | null = null;

/**
 * Load Aladin Lite once (it initialises a WebAssembly module and needs WebGL2).
 * The import is dynamic so the ~2 MB bundle does not block first paint.
 */
export function loadAladin(): Promise<AladinStatic> {
  if (!loader) {
    loader = import("aladin-lite").then(async (mod) => {
      const A = mod.default;
      await A.init;
      return A;
    });
    loader.catch(() => {
      loader = null; // allow a retry after a failure (e.g. WebGL2 unavailable)
    });
  }
  return loader;
}
