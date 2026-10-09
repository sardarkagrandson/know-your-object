import { describe, expect, it } from "vitest";
import { ViewSync, angularSeparationDeg, statesMatch, type SyncableView } from "./viewSync";

/** A fake Aladin instance that echoes programmatic changes through its callbacks, like the real one. */
class FakeView implements SyncableView {
  ra = 0;
  dec = 0;
  fov = 1;
  calls: string[] = [];
  private posCb?: (p: { ra: number; dec: number; dragging?: boolean }) => void;
  private zoomCb?: (fov: number) => void;

  on(event: "positionChanged" | "zoomChanged", cb: unknown): void {
    if (event === "positionChanged") this.posCb = cb as typeof this.posCb;
    else this.zoomCb = cb as typeof this.zoomCb;
  }
  gotoRaDec(ra: number, dec: number): void {
    this.calls.push(`goto(${ra},${dec})`);
    // Real Aladin rounds through the projection, so echo a value that is not bit-identical.
    this.ra = ra + 1e-7;
    this.dec = dec - 1e-7;
    this.posCb?.({ ra: this.ra, dec: this.dec });
  }
  setFoV(fov: number): void {
    this.calls.push(`fov(${fov})`);
    this.fov = fov;
    this.zoomCb?.(fov);
  }
  getFov(): [number, number] {
    return [this.fov, this.fov * 0.75];
  }
  getRaDec(): [number, number] {
    return [this.ra, this.dec];
  }
  /** Simulate the user dragging / zooming this pane. */
  userNavigate(ra: number, dec: number, fov = this.fov): void {
    this.ra = ra;
    this.dec = dec;
    this.fov = fov;
    this.zoomCb?.(fov);
    this.posCb?.({ ra, dec, dragging: true });
  }
}

function grid() {
  const sync = new ViewSync({ ra: 10, dec: 20, fov: 0.5 });
  const views = ["a", "b", "c", "d"].map((id) => {
    const v = new FakeView();
    sync.register(id, v);
    return v;
  });
  return { sync, views };
}

describe("angularSeparationDeg", () => {
  it("handles the RA wrap", () => {
    expect(angularSeparationDeg(359.9, 0, 0.1, 0)).toBeCloseTo(0.2, 6);
  });
  it("is zero for identical points", () => {
    expect(angularSeparationDeg(53.4, -36.1, 53.4, -36.1)).toBe(0);
  });
});

describe("statesMatch", () => {
  it("tolerates sub-pixel differences but not real moves", () => {
    const s = { ra: 53.4, dec: -36.1, fov: 0.2 };
    expect(statesMatch(s, { ...s, ra: 53.4 + 1e-5 })).toBe(true);
    expect(statesMatch(s, { ...s, ra: 53.5 })).toBe(false);
    expect(statesMatch(s, { ...s, fov: 0.3 })).toBe(false);
  });
});

describe("ViewSync", () => {
  it("applies the initial state to panes as they register", () => {
    const { views } = grid();
    for (const v of views) {
      expect(v.ra).toBeCloseTo(10, 5);
      expect(v.dec).toBeCloseTo(20, 5);
      expect(v.fov).toBe(0.5);
    }
  });

  it("propagates user navigation in one pane to all others exactly once", () => {
    const { sync, views } = grid();
    for (const v of views) v.calls = [];
    views[0].userNavigate(53.4, -36.1, 0.2);
    for (const v of views.slice(1)) {
      expect(v.ra).toBeCloseTo(53.4, 5);
      expect(v.dec).toBeCloseTo(-36.1, 5);
      expect(v.fov).toBe(0.2);
      expect(v.calls).toEqual(["fov(0.2)", "goto(53.4,-36.1)"]);
    }
    // The source pane is never written back to (that would cause a feedback loop).
    expect(views[0].calls).toEqual([]);
    expect(sync.state).toEqual({ ra: 53.4, dec: -36.1, fov: 0.2 });
  });

  it("ignores echoes so the panes do not ping-pong", () => {
    const { sync, views } = grid();
    const seen: string[] = [];
    sync.subscribe((_s, src) => seen.push(src ?? "program"));
    views[1].userNavigate(100, 5);
    // One emission from the originating pane; the three echoes are swallowed.
    expect(seen).toEqual(["b"]);
  });

  it("goTo() moves every pane and notifies listeners with a null source", () => {
    const { sync, views } = grid();
    const seen: Array<string | null> = [];
    sync.subscribe((_s, src) => seen.push(src));
    sync.goTo({ ra: 187.7, dec: 12.4, fov: 0.1 });
    for (const v of views) {
      expect(v.ra).toBeCloseTo(187.7, 5);
      expect(v.fov).toBe(0.1);
    }
    expect(seen).toEqual([null]);
  });

  it("does not propagate while disabled, then snaps to the last active pane when re-enabled", () => {
    const { sync, views } = grid();
    sync.setEnabled(false);
    views[2].userNavigate(200, -10, 0.05);
    expect(views[0].ra).toBeCloseTo(10, 5);
    expect(views[0].fov).toBe(0.5);

    sync.setEnabled(true);
    for (const v of views) {
      expect(v.ra).toBeCloseTo(200, 5);
      expect(v.dec).toBeCloseTo(-10, 5);
      expect(v.fov).toBe(0.05);
    }
  });

  it("stops talking to unregistered panes", () => {
    const { sync, views } = grid();
    sync.unregister("d");
    views[3].calls = [];
    views[0].userNavigate(1, 1);
    expect(views[3].calls).toEqual([]);
    expect(sync.paneIds).toEqual(["a", "b", "c"]);
  });
});
