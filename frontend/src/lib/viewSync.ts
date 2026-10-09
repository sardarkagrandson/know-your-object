/**
 * ViewSync keeps any number of Aladin Lite instances looking at the same sky position
 * and field of view.
 *
 * Aladin Lite v3 reports navigation through the throttled `positionChanged` / `zoomChanged`
 * callbacks, and *also* fires them when we programmatically call `gotoRaDec` / `setFoV`.
 * Those echoes can arrive either synchronously (the callbacks are leading-edge throttled, so a
 * `zoomChanged` may fire inside `setFoV`, before `gotoRaDec` has run) or later, from the render
 * loop. Two guards cover both cases: a pane is muted while we are writing to it, and afterwards
 * callbacks that merely echo the last state we pushed (within a tolerance scaled to the field of
 * view) are discarded.
 */

export interface ViewState {
  ra: number; // degrees, ICRS
  dec: number; // degrees, ICRS
  fov: number; // horizontal field of view, degrees
}

/** The subset of the Aladin Lite instance API that ViewSync needs (kept small for testing). */
export interface SyncableView {
  on(event: "positionChanged", cb: (pos: { ra: number; dec: number; dragging?: boolean }) => void): void;
  on(event: "zoomChanged", cb: (fov: number) => void): void;
  gotoRaDec(ra: number, dec: number): void;
  setFoV(fov: number): void;
  getFov(): [number, number];
  getRaDec(): [number, number];
}

type Listener = (state: ViewState, sourceId: string | null) => void;

const DEG = Math.PI / 180;
/** Longer than Aladin Lite's 100 ms callback throttle. */
const SETTLE_DELAY_MS = 250;

/** Great-circle separation between two points, in degrees. */
export function angularSeparationDeg(ra1: number, dec1: number, ra2: number, dec2: number): number {
  const dRa = (ra2 - ra1) * DEG;
  const d1 = dec1 * DEG;
  const d2 = dec2 * DEG;
  const sinDDec = Math.sin((d2 - d1) / 2);
  const sinDRa = Math.sin(dRa / 2);
  const a = sinDDec * sinDDec + Math.cos(d1) * Math.cos(d2) * sinDRa * sinDRa;
  return (2 * Math.asin(Math.min(1, Math.sqrt(a)))) / DEG;
}

export function statesMatch(a: ViewState, b: ViewState): boolean {
  const fovRef = Math.max(Math.min(a.fov, b.fov), 1e-4);
  const posTol = fovRef * 2e-3; // ~0.2% of the FOV: well under a pixel for typical pane sizes
  const fovTol = fovRef * 2e-3;
  return (
    Math.abs(a.fov - b.fov) <= fovTol && angularSeparationDeg(a.ra, a.dec, b.ra, b.dec) <= posTol
  );
}

export class ViewSync {
  private panes = new Map<string, SyncableView>();
  private lastApplied = new Map<string, ViewState>();
  private applying = new Set<string>();
  private settleTimer: ReturnType<typeof setTimeout> | null = null;
  private listeners = new Set<Listener>();
  private _enabled = true;
  private _state: ViewState | null = null;
  private lastActiveId: string | null = null;

  constructor(initial?: ViewState) {
    if (initial) this._state = { ...initial };
  }

  get state(): ViewState | null {
    return this._state ? { ...this._state } : null;
  }

  get enabled(): boolean {
    return this._enabled;
  }

  /** Turning sync on snaps every pane to the most recently navigated one. */
  setEnabled(enabled: boolean): void {
    if (this._enabled === enabled) return;
    this._enabled = enabled;
    if (enabled) {
      const source = this.lastActiveId ?? this.panes.keys().next().value ?? null;
      const ref = source ? this.readPane(source) : this._state;
      if (ref) {
        this._state = ref;
        this.applyToAll(ref, source);
        this.emit(ref, source);
        if (source) this.scheduleSettle(source);
      }
    }
  }

  get paneIds(): string[] {
    return [...this.panes.keys()];
  }

  register(id: string, view: SyncableView): void {
    this.panes.set(id, view);
    view.on("positionChanged", (pos) => this.onPaneChanged(id, { ra: pos.ra, dec: pos.dec }));
    view.on("zoomChanged", (fov) => this.onPaneChanged(id, { fov }));
    if (this._state) {
      this.apply(id, this._state);
    } else {
      const s = this.readPane(id);
      if (s) this._state = s;
    }
  }

  unregister(id: string): void {
    this.panes.delete(id);
    this.lastApplied.delete(id);
    if (this.lastActiveId === id) this.lastActiveId = null;
  }

  /** Programmatic navigation: applied to every pane regardless of the sync toggle. */
  goTo(partial: Partial<ViewState>): void {
    const base = this._state ?? { ra: 0, dec: 0, fov: 1 };
    const next: ViewState = { ...base, ...partial };
    this._state = next;
    this.applyToAll(next, null);
    this.emit(next, null);
  }

  subscribe(listener: Listener): () => void {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  }

  /** Current centre / FOV as reported by one pane (null if unknown). */
  paneState(id: string): ViewState | null {
    return this.readPane(id);
  }

  // -- internals ----------------------------------------------------------------------------

  private readPane(id: string): ViewState | null {
    const view = this.panes.get(id);
    if (!view) return null;
    try {
      const [ra, dec] = view.getRaDec();
      const [fov] = view.getFov();
      if (![ra, dec, fov].every(Number.isFinite)) return null;
      return { ra, dec, fov };
    } catch {
      return null;
    }
  }

  private onPaneChanged(id: string, partial: Partial<ViewState>): void {
    if (this.applying.has(id)) return; // synchronous echo of our own write
    const current = this.readPane(id);
    if (!current) return;
    const next: ViewState = { ...current, ...partial };

    const applied = this.lastApplied.get(id);
    if (applied && statesMatch(next, applied)) {
      return; // echo of a state we pushed to this pane
    }

    this.lastActiveId = id;
    this.lastApplied.set(id, next);

    if (!this._enabled) {
      this.emit(next, id);
      return;
    }
    this._state = next;
    this.applyToAll(next, id);
    this.emit(next, id);
    this.scheduleSettle(id);
  }

  /**
   * Aladin's callbacks are throttled, so the last frame of an animated zoom or an inertial
   * pan can go unreported. Shortly after each change, re-read the active pane and push any
   * residual difference to the others.
   */
  private scheduleSettle(id: string): void {
    if (this.settleTimer) clearTimeout(this.settleTimer);
    this.settleTimer = setTimeout(() => {
      this.settleTimer = null;
      if (!this._enabled || !this._state) return;
      const actual = this.readPane(id);
      if (!actual || statesMatch(actual, this._state)) return;
      this._state = actual;
      this.lastApplied.set(id, actual);
      this.applyToAll(actual, id);
      this.emit(actual, id);
    }, SETTLE_DELAY_MS);
  }

  private applyToAll(state: ViewState, exceptId: string | null): void {
    for (const id of this.panes.keys()) {
      if (id !== exceptId) this.apply(id, state);
    }
  }

  private apply(id: string, state: ViewState): void {
    const view = this.panes.get(id);
    if (!view) return;
    this.lastApplied.set(id, state);
    const current = this.readPane(id);
    this.applying.add(id);
    try {
      if (!current || Math.abs(current.fov - state.fov) > state.fov * 1e-4) {
        view.setFoV(state.fov);
      }
      if (
        !current ||
        angularSeparationDeg(current.ra, current.dec, state.ra, state.dec) > state.fov * 1e-4
      ) {
        view.gotoRaDec(state.ra, state.dec);
      }
    } catch (err) {
      console.error(`ViewSync: failed to apply state to pane ${id}`, err);
    } finally {
      this.applying.delete(id);
    }
  }

  private emit(state: ViewState, sourceId: string | null): void {
    for (const l of this.listeners) {
      try {
        l({ ...state }, sourceId);
      } catch (err) {
        console.error("ViewSync listener failed", err);
      }
    }
  }
}
