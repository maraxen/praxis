// highlight.js -- the DOM-free N8-B/FR-11 highlight directive builder (W4).
//
// Turns a clarification exit's location targets into a PLAIN directive object.
// The consumer is overlay/assets/coxswain/viz_highlight.js, which renders the
// directive on its own dedicated Konva overlay layer; this module itself never
// touches a DOM node, Konva, or any channel (NFR-3, zero dependencies/AC-3).
//
// AC-12: under `prefers-reduced-motion: reduce` the directive is a static
// outline with ZERO animation frames. viz_highlight.js treats `animate:false`
// as binding regardless of what the visualizer document's own media query
// says; when the directive animates but the visualizer document is reduced,
// the renderer downgrades locally (defense in depth on both sides).

/** §4.6/NFR-6 media query, exported so both sides query the identical string. */
export const REDUCED_MOTION_QUERY = "(prefers-reduced-motion: reduce)";

export const HIGHLIGHT_DIRECTIVE_VERSION = 1;

const PULSE_PERIOD_MS = 800;
const PULSE_FRAMES = 2;

function normalizeTarget(target) {
  if (target && typeof target === "object") {
    const label =
      typeof target.position === "string" && target.position.length > 0
        ? target.position
        : typeof target.name === "string"
          ? target.name
          : null;
    if (!label) return null;
    return {
      label,
      ...(typeof target.name === "string" ? { name: target.name } : {}),
      ...(typeof target.position === "string" ? { position: target.position } : {}),
    };
  }
  if (typeof target === "string" && target.trim().length > 0) {
    return { label: target };
  }
  return null;
}

/**
 * Build one highlight directive.
 *   targets        non-empty array; entries are `{name?, position?}` objects
 *                  or plain strings. Order is preserved as given (FR-3).
 *   animate        default true; forced false by reduced motion.
 *   reduced_motion simulated `prefers-reduced-motion: reduce` (AC-12).
 */
export function buildHighlightDirective({ targets, animate = true, reduced_motion = false }) {
  if (!Array.isArray(targets) || targets.length === 0) {
    throw new Error("buildHighlightDirective: targets must be a non-empty array");
  }
  const shapes = targets.map(normalizeTarget);
  if (shapes.some((s) => s === null)) {
    throw new Error(
      "buildHighlightDirective: every target needs a name or position string",
    );
  }
  const motion = animate && !reduced_motion;
  return {
    version: HIGHLIGHT_DIRECTIVE_VERSION,
    kind: motion ? "pulse_outline" : "static_outline",
    // AC-12: reduce means NO animation frames -- not fewer, not slower.
    animate: motion,
    frames: motion ? PULSE_FRAMES : 0,
    ...(motion ? { period_ms: PULSE_PERIOD_MS } : {}),
    shapes,
  };
}

/** The empty directive viz_highlight.js applies to wipe its overlay layer. */
export function buildClearDirective() {
  return { version: HIGHLIGHT_DIRECTIVE_VERSION, kind: "clear", shapes: [] };
}

/**
 * Read the user's reduced-motion preference from an injected matchMedia-like
 * result. An ABSENT matchMedia fails closed to reduced (static) rendering:
 * an unreadable preference must never enable animation (NFR-5's direction).
 */
export function prefersReducedMotion(matchMediaResult) {
  if (matchMediaResult && typeof matchMediaResult === "object") {
    return matchMediaResult.matches === true;
  }
  return true;
}
