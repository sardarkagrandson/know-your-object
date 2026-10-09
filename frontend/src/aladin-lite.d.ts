// Minimal typings for the subset of the Aladin Lite v3 API that AstroScope uses.
declare module "aladin-lite" {
  export interface AladinPositionEvent {
    ra: number;
    dec: number;
    dragging: boolean;
    frame?: string;
  }

  export interface AladinOptions {
    survey?: string;
    fov?: number;
    target?: string;
    cooFrame?: "ICRS" | "ICRSd" | "galactic" | "J2000" | "J2000d";
    projection?: string;
    showReticle?: boolean;
    showCooGrid?: boolean;
    showCooGridControl?: boolean;
    showLayersControl?: boolean;
    showFullscreenControl?: boolean;
    showSimbadPointerControl?: boolean;
    showProjectionControl?: boolean;
    showZoomControl?: boolean;
    showSettingsControl?: boolean;
    showShareControl?: boolean;
    showStatusBar?: boolean;
    showFrame?: boolean;
    showCooLocation?: boolean;
    showContextMenu?: boolean;
    reticleColor?: string;
    reticleSize?: number;
    backgroundColor?: string;
    realFullscreen?: boolean;
  }

  export interface AladinCatalog {
    addSources(sources: unknown[]): void;
    removeAll(): void;
    show(): void;
    hide(): void;
  }

  export interface AladinMOC {
    name?: string;
    skyFrac?: number;
  }

  export interface AladinInstance {
    on(event: "positionChanged", cb: (pos: AladinPositionEvent) => void): void;
    on(event: "zoomChanged", cb: (fov: number) => void): void;
    on(event: string, cb: (...args: unknown[]) => void): void;
    gotoRaDec(ra: number, dec: number): void;
    setFoV(fov: number): void;
    getFov(): [number, number];
    getRaDec(): [number, number];
    setBaseImageLayer(survey: string | unknown): void;
    setImageSurvey(survey: string | unknown): void;
    addMOC(moc: AladinMOC): void;
    addCatalog(catalog: AladinCatalog): void;
    remove(layer: unknown): void;
    removeLayers(): void;
    setProjection(name: string): void;
  }

  export interface AladinStatic {
    init: Promise<void>;
    aladin(target: string | HTMLElement, options?: AladinOptions): AladinInstance;
    MOCFromURL(
      url: string,
      options?: { name?: string; color?: string; lineWidth?: number; opacity?: number; fill?: boolean },
      onSuccess?: (moc: AladinMOC) => void,
      onError?: (moc: AladinMOC) => void,
    ): AladinMOC;
    catalog(options?: {
      name?: string;
      color?: string;
      sourceSize?: number;
      shape?: string;
      onClick?: string | ((source: unknown) => void);
    }): AladinCatalog;
    source(ra: number, dec: number, data?: Record<string, unknown>): unknown;
  }

  const A: AladinStatic;
  export default A;
}
