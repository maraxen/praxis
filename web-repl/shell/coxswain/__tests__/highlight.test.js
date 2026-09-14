// highlight.js -- the DOM-free N8-B/FR-11 directive builder (W4).
//
// The builder turns a clarify exit's location targets into a plain directive
// object that viz_highlight.js renders on its DEDICATED Konva overlay layer.
// It never touches a DOM node, Konva, or any channel itself (NFR-3).
//
// AC-12: under prefers-reduced-motion: reduce the directive is a STATIC
// OUTLINE with zero animation frames.

import { describe, expect, test } from "bun:test";

import {
  HIGHLIGHT_DIRECTIVE_VERSION,
  REDUCED_MOTION_QUERY,
  buildClearDirective,
  buildHighlightDirective,
  prefersReducedMotion,
} from "../highlight.js";

const TARGETS = [
  { name: "PLT_CAR_L5AC_A00", position: "rails 7" },
  { name: "PLT_CAR_P3AC_A00", position: "rails 13" },
];

describe("buildHighlightDirective", () => {
  test("animated directive carries pulse kind, frames, and as-given targets", () => {
    const d = buildHighlightDirective({ targets: TARGETS });
    expect(d.version).toBe(HIGHLIGHT_DIRECTIVE_VERSION);
    expect(d.kind).toBe("pulse_outline");
    expect(d.animate).toBe(true);
    expect(d.frames).toBeGreaterThan(0);
    expect(d.period_ms).toBeGreaterThan(0);
    expect(d.shapes.map((s) => s.position)).toEqual(["rails 7", "rails 13"]);
    // FR-3's as-given rule reaches even the highlight layer.
    expect(d.shapes.map((s) => s.name)).toEqual([
      "PLT_CAR_L5AC_A00",
      "PLT_CAR_P3AC_A00",
    ]);
  });

  test("AC-12: reduced motion yields a static outline with NO animation frames", () => {
    const d = buildHighlightDirective({ targets: TARGETS, reduced_motion: true });
    expect(d.kind).toBe("static_outline");
    expect(d.animate).toBe(false);
    expect(d.frames).toBe(0);
  });

  test("animate:false forces static even without reduced motion", () => {
    const d = buildHighlightDirective({ targets: TARGETS, animate: false });
    expect(d.animate).toBe(false);
    expect(d.frames).toBe(0);
  });

  test("string targets are accepted and normalized to shapes", () => {
    const d = buildHighlightDirective({ targets: ["rails 7"] });
    expect(d.shapes).toEqual([{ label: "rails 7" }]);
  });

  test("empty or malformed targets throw loudly, never render nothing silently", () => {
    expect(() => buildHighlightDirective({ targets: [] })).toThrow();
    expect(() => buildHighlightDirective({})).toThrow();
    expect(() =>
      buildHighlightDirective({ targets: [{ nope: true }] })
    ).toThrow();
    expect(() => buildHighlightDirective({ targets: [42] })).toThrow();
  });
});

describe("buildClearDirective", () => {
  test("produces a clear directive with no shapes", () => {
    const d = buildClearDirective();
    expect(d.version).toBe(HIGHLIGHT_DIRECTIVE_VERSION);
    expect(d.kind).toBe("clear");
    expect(d.shapes).toEqual([]);
  });
});

describe("prefersReducedMotion", () => {
  test("reads the media query result from an injected matchMedia", () => {
    expect(prefersReducedMotion({ matches: true })).toBe(true);
    expect(prefersReducedMotion({ matches: false })).toBe(false);
  });

  test("absent matchMedia fails closed to reduced motion", () => {
    expect(prefersReducedMotion(null)).toBe(true);
    expect(prefersReducedMotion(undefined)).toBe(true);
  });

  test("the query string is the standard prefers-reduced-motion reduce query", () => {
    expect(REDUCED_MOTION_QUERY).toBe("(prefers-reduced-motion: reduce)");
  });
});
