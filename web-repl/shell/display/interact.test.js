// interact.test.js -- AC-19 (interact.js) of the notebook display epic
// (.praxia/docs/specs/260929_notebook-display-epic.md: section 3.4 "Interaction",
// D12 Click, D14 "One shell script owns all interaction", D2 "Escaping"; task B9).
//
// Ground truth for the DOM this reads is B2's labware.py: the figure `<g>` carries
// `data-praxis-res` (the FULL name), `role="img"`, `aria-label`, `tabindex="0"` and
// `data-praxis-grid` (JSON: v, kind "volume"|"tip", res, x0, y0, dx, dy, rows, cols,
// ids (space-joined), vals (uL, or 1/0 for tips), flags). A well at row r (A = 0),
// column c (1-based) sits at (x0 + (c-1)*dx, y0 + r*dy) in the svg's user units.
// In a DECK output (B3) only the OUTER group has role / aria-label / tabindex; the
// inner carrier, labware and fixture groups carry `data-praxis-res` only, and
// full-detail labware also `data-praxis-grid`. Blocked labware has no grid.
//
// S2: an untrusted reopen strips the SVG and every `data-*` / `tabindex`; nothing
// here may throw or write there.
//
// The DOM scenarios take the module under test, so they run against the real
// interact.js and against mutants that must FAIL them.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import * as real from "./interact.js";
import {
  FakeElement,
  createFakeApp,
  createFakeDocument,
  createFakeWindow,
} from "./__tests__/fakes.js";

const { parseGrid, hitTest, moveCursor, readoutText, rowLabel } = real;

function recordingLogger() {
  const errors = [];
  return { errors, error: (...a) => errors.push(a), warn() {}, log() {} };
}

// -- fixtures ----------------------------------------------------------------------------------

const ROW_LETTERS = "ABCDEFGHIJKLMNOP";

/** A grid descriptor object (B2's shape) for `rows` x `cols`, row-major. */
function descriptor({ kind = "volume", res = "assay", rows = 8, cols = 12, x0 = 10, y0 = 6, dx = 8, dy = 8, vals = () => 0, flags } = {}) {
  const ids = [];
  const values = [];
  for (let r = 0; r < rows; r += 1) {
    for (let c = 1; c <= cols; c += 1) {
      ids.push(`${ROW_LETTERS[r]}${c}`);
      values.push(vals(r, c));
    }
  }
  return { v: 1, kind, res, x0, y0, dx, dy, rows, cols, ids: ids.join(" "), vals: values, flags: flags ?? "0".repeat(ids.length) };
}

const grid96 = () => parseGrid(JSON.stringify(descriptor()));
const grid384 = () =>
  parseGrid(JSON.stringify(descriptor({ rows: 16, cols: 24, x0: 6, y0: 3, dx: 4, dy: 4, res: "big" })));

const SCALE = 2; // client px per user unit in the fake svg
const SVG_LEFT = 100;
const SVG_TOP = 50;
const clientOf = (ux, uy) => ({ clientX: SVG_LEFT + ux * SCALE, clientY: SVG_TOP + uy * SCALE });

/** Build `body > div.jp-OutputArea-output > div.praxis-out > svg` and return the pieces.
 * The svg is 400 x 300 user units at SCALE. */
function figureShell(doc) {
  const host = doc.createElement("div");
  host.classList.add("jp-OutputArea-output");
  const out = doc.createElement("div");
  out.classList.add("praxis-out");
  const svg = doc.createElement("svg");
  svg.setAttribute("viewBox", "0 0 400 300");
  svg.rect = { left: SVG_LEFT, top: SVG_TOP, width: 400 * SCALE, height: 300 * SCALE };
  doc.body.appendChild(host);
  host.appendChild(out);
  out.appendChild(svg);
  return { host, out, svg };
}

/** A B2 figure: one resource group with grid, role, aria-label, tabindex. */
function labwareFigure(doc, desc, { res = desc.res, tabindex = true, gridText } = {}) {
  const shell = figureShell(doc);
  const g = doc.createElement("g");
  g.setAttribute("data-praxis-res", res);
  g.setAttribute("data-praxis-grid", gridText ?? JSON.stringify(desc));
  g.setAttribute("role", "img");
  g.setAttribute("aria-label", `${res} sentence`);
  if (tabindex) g.setAttribute("tabindex", "0");
  shell.svg.appendChild(g);
  return { ...shell, g };
}

function setup({ dock, controllers = {}, mod = real } = {}) {
  const document = createFakeDocument();
  const app = createFakeApp();
  const win = createFakeWindow({ app, document });
  const logger = recordingLogger();
  const dockApi = dock === undefined ? { calls: [], focus(name) { this.calls.push(name); } } : dock;
  const ctl = mod.mountInteract({ app, win, logger, controllers: dockApi ? { dock: dockApi, ...controllers } : controllers });
  return { document, win, app, logger, ctl, dock: dockApi };
}

const bodyChild = (doc, pred) => doc.body.children.find(pred);
const readoutEl = (doc) => bodyChild(doc, (c) => c.classList.contains("praxis-readout"));
const liveEl = (doc) => bodyChild(doc, (c) => c.getAttribute("aria-live") === "polite");
const shown = (el) => Boolean(el) && el.style.display !== "none" && !el.hasAttribute("hidden");
const ringOf = (g) => g.children.find((c) => c.classList.contains("praxis-focus-ring"));
const ringBox = (ring) => ["x", "y", "width", "height"].map((k) => Number(ring.getAttribute(k)));

function hover(g, id, desc) {
  const grid = parseGrid(JSON.stringify(desc));
  const i = grid.ids.indexOf(id);
  const col = Number(id.slice(1));
  const row = ROW_LETTERS.indexOf(id[0]);
  const ux = desc.x0 + (col - 1) * desc.dx;
  const uy = desc.y0 + row * desc.dy;
  expect(i).toBeGreaterThanOrEqual(0);
  return g.dispatch("mousemove", clientOf(ux, uy));
}

// -- scenarios (each takes the module under test) -------------------------------------------------

const scenarios = {
  hoverShowsTheReadoutOfTheWellUnderThePointer(mod) {
    const w = setup({ mod });
    const desc = descriptor({ vals: (r, c) => (r === 1 && c === 3 ? 100 : 0) });
    const { g } = labwareFigure(w.document, desc);
    hover(g, "B3", desc);
    const el = readoutEl(w.document);
    expect(el).toBeDefined();
    expect(shown(el)).toBe(true);
    expect(el.textContent).toBe("assay B3: 100 µL");
    expect(Number.isFinite(parseFloat(el.style.left))).toBe(true);
    expect(Number.isFinite(parseFloat(el.style.top))).toBe(true);
    hover(g, "A1", desc);
    expect(el.textContent).toBe("assay A1: 0 µL");
    // Leaving the figure hides it.
    g.dispatch("mouseout", { relatedTarget: null });
    expect(shown(el)).toBe(false);
    // A point between wells of nothing (outside the grid) hides it too.
    hover(g, "B3", desc);
    g.dispatch("mousemove", clientOf(desc.x0 - 40, desc.y0 - 40));
    expect(shown(el)).toBe(false);
    expect(w.logger.errors).toEqual([]);
  },

  tipReadoutSaysTipOrTaken(mod) {
    const w = setup({ mod });
    const desc = descriptor({ kind: "tip", res: "tips_300", vals: (r, c) => (r === 2 && c === 2 ? 0 : 1) });
    const { g } = labwareFigure(w.document, desc);
    hover(g, "C2", desc);
    expect(readoutEl(w.document).textContent).toBe("tips_300 C2: taken");
    hover(g, "C3", desc);
    expect(readoutEl(w.document).textContent).toBe("tips_300 C3: tip");
    expect(w.logger.errors).toEqual([]);
  },

  keyboardMovesTheRingAndTheLiveRegionEqualsTheHoverText(mod) {
    const w = setup({ mod });
    const desc = descriptor({ vals: (r, c) => (r === 1 && c === 3 ? 100 : 5 * c) });
    const { g } = labwareFigure(w.document, desc);
    const key = (k) => g.dispatch("keydown", { key: k });

    g.dispatch("focusin", {});
    const live = liveEl(w.document);
    expect(live).toBeDefined();
    expect(live.textContent).toBe("assay A1: 5 µL");
    expect(ringBox(ringOf(g))).toEqual([6, 2, 8, 8]); // A1: centre (10, 6), one pitch square

    let ev = key("ArrowRight");
    expect(live.textContent).toBe("assay A2: 10 µL"); // ArrowRight from A1 gives A2
    expect(ev.defaultPrevented).toBe(true);
    key("ArrowLeft");
    expect(live.textContent).toBe("assay A1: 5 µL");
    key("ArrowDown");
    expect(live.textContent).toBe("assay B1: 5 µL"); // ArrowDown from A1 gives B1
    expect(ringBox(ringOf(g))).toEqual([6, 10, 8, 8]);

    // Clamped at the edges: no wrap, no error.
    key("ArrowLeft");
    expect(live.textContent).toBe("assay B1: 5 µL");
    key("ArrowUp");
    key("ArrowUp");
    expect(live.textContent).toBe("assay A1: 5 µL");
    for (let i = 0; i < 20; i += 1) key("ArrowRight");
    expect(live.textContent).toBe("assay A12: 60 µL");
    for (let i = 0; i < 20; i += 1) key("ArrowDown");
    expect(live.textContent).toBe("assay H12: 60 µL");

    // The live text equals the hover text of the same well.
    key("Escape");
    g.dispatch("focusin", {});
    key("ArrowDown");
    key("ArrowRight");
    key("ArrowRight");
    const keyboardText = live.textContent;
    hover(g, "B3", desc);
    expect(readoutEl(w.document).textContent).toBe(keyboardText);
    expect(keyboardText).toBe("assay B3: 100 µL");

    // Keys the grid does not own are left alone.
    ev = key("Tab");
    expect(ev.defaultPrevented).toBe(false);
    expect(w.logger.errors).toEqual([]);
  },

  escapeLeavesTheGrid(mod) {
    const w = setup({ mod });
    const desc = descriptor();
    const { g } = labwareFigure(w.document, desc);
    g.dispatch("focusin", {});
    g.dispatch("keydown", { key: "ArrowRight" });
    expect(ringOf(g)).toBeDefined();
    const ev = g.dispatch("keydown", { key: "Escape" });
    expect(ringOf(g)).toBeUndefined();
    expect(liveEl(w.document).textContent).toBe("");
    expect(ev.defaultPrevented).toBe(false); // JupyterLab's own Escape is not swallowed
    expect(w.logger.errors).toEqual([]);
  },

  clickFocusesTheExactResourceName(mod) {
    for (const name of ["assay", "<b>&\"'x", "__proto__", "a b\n\"c\""]) {
      const w = setup({ mod });
      const desc = descriptor({ res: name });
      const { g, out, svg } = labwareFigure(w.document, desc);
      const inner = w.document.createElement("path"); // a click lands on a child of the group
      g.appendChild(inner);
      inner.dispatch("click", { clientX: 1, clientY: 1 });
      expect(w.dock.calls).toEqual([name]);
      expect(out.classList.contains("is-focus")).toBe(true);
      expect(svg.classList.contains("is-focus")).toBe(false);
      expect(w.logger.errors).toEqual([]); // a selector built from the name would have thrown
    }
  },

  clickMovesTheFocusOutlineToOneOutput(mod) {
    const w = setup({ mod });
    const one = labwareFigure(w.document, descriptor({ res: "assay" }));
    const two = labwareFigure(w.document, descriptor({ res: "source" }));
    one.g.dispatch("click", {});
    expect(one.out.classList.contains("is-focus")).toBe(true);
    two.g.dispatch("click", {});
    expect(two.out.classList.contains("is-focus")).toBe(true);
    expect(one.out.classList.contains("is-focus")).toBe(false);
    expect(w.dock.calls).toEqual(["assay", "source"]);
    expect(w.logger.errors).toEqual([]);
  },
};

// -- the real module -----------------------------------------------------------------------------------

describe("interact.js scenarios (real module)", () => {
  for (const [name, scenario] of Object.entries(scenarios)) {
    test(name, () => scenario(real));
  }
});

// -- controls: mutants must FAIL ------------------------------------------------------------------------

const SOURCE = readFileSync(new URL("./interact.js", import.meta.url), "utf8");

async function mutant(fn, injection) {
  const header = new RegExp(`export function ${fn}\\(([^)]*)\\) \\{`, "g");
  const hits = SOURCE.match(header);
  if (!hits || hits.length !== 1) throw new Error(`mutation harness: cannot find export function ${fn}(...) once`);
  const text = SOURCE.replace(header, (m) => `${m}\n  ${injection}\n`);
  if (/from\s+["']\.\//.test(text)) throw new Error("mutation harness: an unrewritten relative import");
  const dir = mkdtempSync(join(tmpdir(), "praxis-interact-mutant-"));
  const file = join(dir, `${fn}.mjs`);
  writeFileSync(file, text);
  return import(pathToFileURL(file).href);
}

const MUTANTS = {
  hitTestFindsNothing: await mutant("hitTest", "return null;"),
  cursorNeverMoves: await mutant("moveCursor", "return index;"),
  readoutIsEmpty: await mutant("readoutText", "return null;"),
};

const MUST_FAIL = {
  hitTestFindsNothing: ["hoverShowsTheReadoutOfTheWellUnderThePointer", "tipReadoutSaysTipOrTaken",
    "keyboardMovesTheRingAndTheLiveRegionEqualsTheHoverText"],
  cursorNeverMoves: ["keyboardMovesTheRingAndTheLiveRegionEqualsTheHoverText"],
  readoutIsEmpty: ["hoverShowsTheReadoutOfTheWellUnderThePointer", "tipReadoutSaysTipOrTaken",
    "keyboardMovesTheRingAndTheLiveRegionEqualsTheHoverText"],
};

describe("interact.js controls: mutants must fail", () => {
  for (const [mutantName, names] of Object.entries(MUST_FAIL)) {
    for (const name of names) {
      test(`${mutantName} fails ${name}`, () => {
        expect(() => scenarios[name](MUTANTS[mutantName])).toThrow();
      });
    }
  }
  test("positive control: the real module passes every scenario the mutants fail", () => {
    for (const names of Object.values(MUST_FAIL)) for (const name of names) scenarios[name](real);
  });
});

// -- pure: the hit-test -----------------------------------------------------------------------------------

describe("rowLabel", () => {
  test("A..Z then AA, AB (PLR's labels, as labware.py's _row_label)", () => {
    expect(rowLabel(0)).toBe("A");
    expect(rowLabel(7)).toBe("H");
    expect(rowLabel(15)).toBe("P");
    expect(rowLabel(25)).toBe("Z");
    expect(rowLabel(26)).toBe("AA");
    expect(rowLabel(27)).toBe("AB");
    expect(rowLabel(51)).toBe("AZ");
    expect(rowLabel(52)).toBe("BA");
  });
});

describe("hitTest (pure)", () => {
  const at = (grid, x, y) => {
    const i = hitTest(grid, x, y);
    return i === null ? null : grid.ids[i];
  };

  test("every well centre of a 96 grid maps to its own id", () => {
    const g = grid96();
    expect(g.ids.length).toBe(96);
    for (let r = 0; r < 8; r += 1) {
      for (let c = 1; c <= 12; c += 1) {
        expect(at(g, 10 + (c - 1) * 8, 6 + r * 8)).toBe(`${ROW_LETTERS[r]}${c}`);
      }
    }
  });

  test("every well centre of a 384 grid maps to its own id", () => {
    const g = grid384();
    expect(g.ids.length).toBe(384);
    for (let r = 0; r < 16; r += 1) {
      for (let c = 1; c <= 24; c += 1) {
        expect(at(g, 6 + (c - 1) * 4, 3 + r * 4)).toBe(`${ROW_LETTERS[r]}${c}`);
      }
    }
  });

  test("96 edges: a well owns [centre - pitch/2, centre + pitch/2); the outer half-pitch is inside", () => {
    const g = grid96();
    // A1 is centred (10, 6): its cell is x in [6, 14), y in [2, 10).
    expect(at(g, 6, 2)).toBe("A1"); // the near edge is inclusive
    expect(at(g, 13.99, 9.99)).toBe("A1");
    expect(at(g, 14, 6)).toBe("A2"); // the shared boundary goes to the higher index
    expect(at(g, 10, 10)).toBe("B1");
    expect(at(g, 5.99, 6)).toBeNull(); // left of A1's cell
    expect(at(g, 10, 1.99)).toBeNull(); // above A1's cell
    // H12 is centred (98, 62): its cell is x in [94, 102), y in [58, 66).
    expect(at(g, 101.99, 65.99)).toBe("H12");
    expect(at(g, 102, 62)).toBeNull(); // the far edge is exclusive
    expect(at(g, 98, 66)).toBeNull();
  });

  test("384 edges", () => {
    const g = grid384();
    // A1 centred (6, 3): cell x in [4, 8), y in [1, 5).
    expect(at(g, 4, 1)).toBe("A1");
    expect(at(g, 3.99, 3)).toBeNull();
    expect(at(g, 8, 3)).toBe("A2");
    // P24 centred (6 + 23*4, 3 + 15*4) = (98, 63): cell x in [96, 100), y in [61, 65).
    expect(at(g, 99.99, 64.99)).toBe("P24");
    expect(at(g, 100, 63)).toBeNull();
    expect(at(g, 98, 65)).toBeNull();
  });

  test("points far outside, and non-finite points, hit nothing", () => {
    const g = grid96();
    for (const [x, y] of [[-1000, 6], [10, -1000], [1e9, 1e9], [NaN, 6], [10, NaN], [Infinity, 6], [10, -Infinity]]) {
      expect(hitTest(g, x, y)).toBeNull();
    }
    expect(hitTest(null, 10, 6)).toBeNull();
  });

  test("a 1 x 1 grid (a single well figure)", () => {
    const g = parseGrid(JSON.stringify(descriptor({ rows: 1, cols: 1, x0: 20, y0: 20, dx: 10, dy: 10 })));
    expect(at(g, 20, 20)).toBe("A1");
    expect(at(g, 25, 25)).toBeNull();
    expect(at(g, 24.99, 24.99)).toBe("A1");
  });

  test("a sparse grid (an id absent from ids) hits nothing there", () => {
    const d = descriptor({ rows: 1, cols: 3, x0: 10, y0: 10, dx: 8, dy: 8 });
    d.ids = "A1 A3";
    d.vals = [1, 3];
    d.flags = "00";
    const g = parseGrid(JSON.stringify(d));
    expect(at(g, 10, 10)).toBe("A1");
    expect(at(g, 18, 10)).toBeNull();
    expect(at(g, 26, 10)).toBe("A3");
  });
});

describe("moveCursor (pure)", () => {
  const idx = (g, id) => g.ids.indexOf(id);
  const step = (g, from, key) => g.ids[moveCursor(g, idx(g, from), key)];

  test("ArrowRight from A1 gives A2; ArrowDown from A1 gives B1", () => {
    const g = grid96();
    expect(step(g, "A1", "ArrowRight")).toBe("A2");
    expect(step(g, "A1", "ArrowDown")).toBe("B1");
    expect(step(g, "B2", "ArrowLeft")).toBe("B1");
    expect(step(g, "B2", "ArrowUp")).toBe("A2");
  });

  test("clamped at every edge (no wrap)", () => {
    const g = grid96();
    expect(step(g, "A1", "ArrowLeft")).toBe("A1");
    expect(step(g, "A1", "ArrowUp")).toBe("A1");
    expect(step(g, "A12", "ArrowRight")).toBe("A12");
    expect(step(g, "H1", "ArrowDown")).toBe("H1");
    expect(step(g, "H12", "ArrowRight")).toBe("H12");
    expect(step(g, "H12", "ArrowDown")).toBe("H12");
    const g4 = grid384();
    expect(step(g4, "P24", "ArrowRight")).toBe("P24");
    expect(step(g4, "P24", "ArrowDown")).toBe("P24");
  });

  test("other keys, and a step onto a missing id, leave the cursor where it is", () => {
    const g = grid96();
    expect(moveCursor(g, 5, "Tab")).toBe(5);
    expect(moveCursor(g, 5, "a")).toBe(5);
    const d = descriptor({ rows: 1, cols: 3 });
    d.ids = "A1 A3";
    d.vals = [1, 3];
    d.flags = "00";
    const sparse = parseGrid(JSON.stringify(d));
    expect(sparse.ids[moveCursor(sparse, 0, "ArrowRight")]).toBe("A1");
  });
});

describe("parseGrid / readoutText (pure)", () => {
  test("a valid descriptor", () => {
    const g = grid96();
    expect(g.kind).toBe("volume");
    expect(g.res).toBe("assay");
    expect(g.rows).toBe(8);
    expect(g.cols).toBe(12);
    expect(g.ids.length).toBe(96);
  });

  test("readout text for volume and tip grids, with tidy numbers", () => {
    const v = parseGrid(JSON.stringify(descriptor({ vals: (r, c) => (r === 0 && c === 1 ? 12.5 : r === 0 && c === 2 ? 0.1 + 0.2 : 100) })));
    expect(readoutText(v, 0)).toBe("assay A1: 12.5 µL");
    expect(readoutText(v, 1)).toBe("assay A2: 0.3 µL");
    expect(readoutText(v, 2)).toBe("assay A3: 100 µL");
    const t = parseGrid(JSON.stringify(descriptor({ kind: "tip", res: "tips_300", vals: (r, c) => (c === 1 ? 0 : 1) })));
    expect(readoutText(t, 0)).toBe("tips_300 A1: taken");
    expect(readoutText(t, 1)).toBe("tips_300 A2: tip");
    expect(readoutText(v, 999)).toBeNull();
    expect(readoutText(v, -1)).toBeNull();
    expect(readoutText(null, 0)).toBeNull();
  });

  test("a hostile resource name is text, unchanged", () => {
    const g = parseGrid(JSON.stringify(descriptor({ res: "<b>&\"'x", rows: 1, cols: 1, vals: () => 7 })));
    expect(readoutText(g, 0)).toBe("<b>&\"'x A1: 7 µL");
  });

  test("malformed descriptors give null, never a throw", () => {
    const good = descriptor();
    const clone = (o) => JSON.parse(JSON.stringify({ ...good, ...o }));
    const bad = [
      undefined, null, 5, "", "{not json", "[]", "null", "5", '"s"', "{}",
      JSON.stringify(clone({ v: 2 })),
      JSON.stringify(clone({ kind: "colour" })),
      JSON.stringify(clone({ kind: 5 })),
      JSON.stringify(clone({ res: 5 })),
      JSON.stringify(clone({ rows: 0 })),
      JSON.stringify(clone({ cols: 0 })),
      JSON.stringify(clone({ rows: 1.5 })),
      JSON.stringify(clone({ rows: 100000, cols: 100000 })),
      JSON.stringify(clone({ dx: 0 })),
      JSON.stringify(clone({ dy: -8 })),
      JSON.stringify(clone({ x0: "10" })),
      JSON.stringify(clone({ y0: null })),
      JSON.stringify(clone({ ids: 5 })),
      JSON.stringify(clone({ ids: "A1 nonsense", vals: [1, 2], flags: "00" })),
      JSON.stringify(clone({ ids: "A1 A1", vals: [1, 2], flags: "00" })), // duplicate ids
      JSON.stringify(clone({ vals: [1, 2] })), // length mismatch
      JSON.stringify(clone({ vals: "x" })),
      JSON.stringify(clone({ ids: "A13", vals: [1], flags: "0" })), // a column beyond cols
      JSON.stringify(clone({ ids: "I1", vals: [1], flags: "0" })), // a row beyond rows
    ];
    for (const text of bad) expect(() => parseGrid(text)).not.toThrow();
    for (const text of bad) expect(parseGrid(text)).toBeNull();
  });

  test("a non-finite value gives a null readout for that well, not a throw", () => {
    const d = descriptor({ rows: 1, cols: 2 });
    d.vals = [1, "x"];
    const g = parseGrid(JSON.stringify(d));
    expect(g === null || readoutText(g, 1) === null).toBe(true);
  });
});

// -- DOM: shapes, degradation, containment --------------------------------------------------------------------

describe("interact.js: the deck-shaped output (B3)", () => {
  /** The outer group carries role / aria-label / tabindex; inner groups carry
   * data-praxis-res only, full-detail labware also data-praxis-grid. */
  function deckFigure(doc) {
    const shell = figureShell(doc);
    const mk = (res, extra = {}) => {
      const g = doc.createElement("g");
      g.setAttribute("data-praxis-res", res);
      for (const [k, v] of Object.entries(extra)) g.setAttribute(k, v);
      return g;
    };
    const desc = descriptor({ res: "assay_plate" });
    const outer = mk("deck", { role: "img", "aria-label": "deck sentence", tabindex: "0" });
    const carrier = mk("plate_carrier");
    const labware = mk("assay_plate", { "data-praxis-grid": JSON.stringify(desc) });
    const blocked = mk("tips_blocked"); // below the detail threshold: no grid
    const fixture = mk("waste");
    shell.svg.appendChild(outer);
    outer.appendChild(carrier);
    carrier.appendChild(labware);
    outer.appendChild(blocked);
    outer.appendChild(fixture);
    return { ...shell, outer, carrier, labware, blocked, fixture, desc };
  }

  test("hover over gridded labware nested in the deck reads out its well", () => {
    const w = setup();
    const f = deckFigure(w.document);
    hover(f.labware, "B3", f.desc);
    expect(readoutEl(w.document).textContent).toBe("assay_plate B3: 0 µL");
    expect(w.logger.errors).toEqual([]);
  });

  test("hover over a carrier, blocked labware, a fixture or the deck itself shows no readout", () => {
    const w = setup();
    const f = deckFigure(w.document);
    for (const el of [f.carrier, f.blocked, f.fixture, f.outer]) {
      el.dispatch("mousemove", clientOf(20, 20));
      expect(shown(readoutEl(w.document))).toBe(false);
    }
    expect(w.logger.errors).toEqual([]);
  });

  test("keyboard: focus lands on the OUTER group; with no grid there is no ring, no live text, no key handling", () => {
    const w = setup();
    const f = deckFigure(w.document);
    f.outer.dispatch("focusin", {});
    for (const key of ["ArrowRight", "ArrowDown", "ArrowLeft", "ArrowUp", "Escape"]) {
      const ev = f.outer.dispatch("keydown", { key });
      expect(ev.defaultPrevented).toBe(false);
    }
    expect(ringOf(f.outer)).toBeUndefined();
    expect(ringOf(f.labware)).toBeUndefined();
    const live = liveEl(w.document);
    expect(!live || live.textContent === "").toBe(true);
    expect(w.logger.errors).toEqual([]);
  });

  test("click focuses the nested resource by dataset.praxisRes, whatever its depth", () => {
    const w = setup();
    const f = deckFigure(w.document);
    f.carrier.dispatch("click", {});
    f.blocked.dispatch("click", {});
    f.labware.dispatch("click", {});
    f.fixture.dispatch("click", {});
    f.outer.dispatch("click", {});
    expect(w.dock.calls).toEqual(["plate_carrier", "tips_blocked", "assay_plate", "waste", "deck"]);
    expect(f.out.classList.contains("is-focus")).toBe(true);
    expect(w.logger.errors).toEqual([]);
  });
});

describe("interact.js: silent degradation", () => {
  function fire(el) {
    const events = [
      ["mousemove", clientOf(20, 20)],
      ["mouseout", { relatedTarget: null }],
      ["click", {}],
      ["focusin", {}],
      ["focusout", {}],
      ["keydown", { key: "ArrowRight" }],
      ["keydown", { key: "Escape" }],
    ];
    for (const [type, props] of events) {
      expect(() => el.dispatch(type, props)).not.toThrow();
    }
  }

  test("an untrusted reopen: no svg, no data-*, no tabindex -> nothing happens, nothing throws", () => {
    const w = setup();
    const host = w.document.createElement("div");
    host.classList.add("jp-OutputArea-output");
    const out = w.document.createElement("div");
    out.classList.add("praxis-out");
    const table = w.document.createElement("table");
    const summary = w.document.createElement("summary");
    w.document.body.appendChild(host);
    host.appendChild(out);
    out.appendChild(table);
    out.appendChild(summary);
    fire(table);
    fire(summary);
    fire(out);
    expect(w.dock.calls).toEqual([]);
    expect(out.classList.contains("is-focus")).toBe(false);
    expect(shown(readoutEl(w.document))).toBe(false);
    expect(w.logger.errors).toEqual([]);
  });

  test("a figure whose data-praxis-grid and tabindex were stripped: hover and keys do nothing; click still resolves the resource", () => {
    const w = setup();
    const desc = descriptor();
    const { g } = labwareFigure(w.document, desc, { tabindex: false });
    g.removeAttribute("data-praxis-grid");
    fire(g);
    expect(shown(readoutEl(w.document))).toBe(false);
    expect(ringOf(g)).toBeUndefined();
    expect(w.dock.calls).toEqual(["assay"]); // the click in fire()
    expect(w.logger.errors).toEqual([]);
  });

  test("a malformed data-praxis-grid: no readout, no ring, no throw, no logged error", () => {
    for (const gridText of ["{not json", "[]", "null", '{"v":1}', JSON.stringify({ ...descriptor(), rows: 0 })]) {
      const w = setup();
      const { g } = labwareFigure(w.document, descriptor(), { gridText });
      fire(g);
      expect(shown(readoutEl(w.document))).toBe(false);
      expect(ringOf(g)).toBeUndefined();
      expect(w.logger.errors).toEqual([]);
    }
  });

  test("an svg with no viewBox or no size: no readout, no throw", () => {
    const w = setup();
    const desc = descriptor();
    const { g, svg } = labwareFigure(w.document, desc);
    svg.removeAttribute("viewBox");
    expect(() => hover(g, "B3", desc)).not.toThrow();
    expect(shown(readoutEl(w.document))).toBe(false);
    svg.setAttribute("viewBox", "0 0 400 300");
    svg.rect = { left: 0, top: 0, width: 0, height: 0 };
    expect(() => hover(g, "B3", desc)).not.toThrow();
    expect(shown(readoutEl(w.document))).toBe(false);
    expect(w.logger.errors).toEqual([]);
  });

  test("no dock: a click still outlines the output and does not throw", () => {
    const w = setup({ dock: null });
    const { g, out } = labwareFigure(w.document, descriptor());
    expect(() => g.dispatch("click", {})).not.toThrow();
    expect(out.classList.contains("is-focus")).toBe(true);
    expect(w.logger.errors).toEqual([]);
  });

  test("the dock is read at click time: one that mounts after interact is used", () => {
    const controllers = {};
    const w = setup({ dock: null, controllers });
    const { g } = labwareFigure(w.document, descriptor());
    const calls = [];
    controllers.dock = { focus: (name) => calls.push(name) };
    g.dispatch("click", {});
    expect(calls).toEqual(["assay"]);
  });

  test("a window with no document mounts a no-op controller and warns nothing fatal", () => {
    const logger = recordingLogger();
    const ctl = real.mountInteract({ app: createFakeApp(), win: createFakeWindow({}), logger, controllers: {} });
    expect(typeof ctl.dispose).toBe("function");
    expect(() => ctl.dispose()).not.toThrow();
    expect(logger.errors).toEqual([]);
  });
});

describe("interact.js: failure containment", () => {
  test("a dock whose focus throws is logged, not rethrown, and the next click works", () => {
    let fail = true;
    const calls = [];
    const dock = {
      focus(name) {
        if (fail) throw new Error("dock exploded");
        calls.push(name);
      },
    };
    const w = setup({ dock });
    const { g } = labwareFigure(w.document, descriptor());
    expect(() => g.dispatch("click", {})).not.toThrow();
    expect(w.logger.errors.length).toBe(1);
    fail = false;
    g.dispatch("click", {});
    expect(calls).toEqual(["assay"]);
  });

  test("a throwing element (getBoundingClientRect) is contained per event", () => {
    const w = setup();
    const desc = descriptor();
    const { g, svg } = labwareFigure(w.document, desc);
    svg.getBoundingClientRect = () => {
      throw new Error("layout exploded");
    };
    expect(() => hover(g, "B3", desc)).not.toThrow();
    expect(w.logger.errors.length).toBeGreaterThan(0);
    svg.getBoundingClientRect = FakeElement.prototype.getBoundingClientRect;
    hover(g, "B3", desc);
    expect(readoutEl(w.document).textContent).toBe("assay B3: 0 µL");
  });
});

describe("interact.js: mount and dispose", () => {
  test("exactly one live region (polite), owned by the shell, and it is not the hover readout", () => {
    const w = setup();
    const lives = w.document.body.children.filter((c) => c.getAttribute("aria-live") === "polite");
    expect(lives.length).toBe(1);
    expect(lives[0].classList.contains("praxis-readout")).toBe(false);
  });

  test("dispose removes every listener, the readout and the live region, and stops reacting", () => {
    const w = setup();
    const desc = descriptor();
    const { g } = labwareFigure(w.document, desc);
    hover(g, "B3", desc);
    expect(readoutEl(w.document)).toBeDefined();
    w.ctl.dispose();
    expect(w.document.listenerCount).toBe(0);
    expect(readoutEl(w.document)).toBeUndefined();
    expect(liveEl(w.document)).toBeUndefined();
    g.dispatch("click", {});
    expect(w.dock.calls).toEqual([]);
    expect(() => w.ctl.dispose()).not.toThrow();
  });
});
