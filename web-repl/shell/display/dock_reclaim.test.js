// dock_reclaim.test.js -- the deck panel's medium-tier re-clamp (backlog #5656; spec
// .praxia/docs/specs/261001_nd-next-5656-deck-layout.md, rev 2 accepted 2026-10-01; AC-N2, AC-N3).
//
// WHY A SECOND FILE. dock.test.js runs dock.js against the LEGACY fake dock, which hands whatever a capped deck cannot use
// to its unlimited sibling, so it can never show an empty strip beside the deck. The recorded real-browser run (K2) shows the
// strip: Lumino's split honours a child's minimum but not its maximum, so the deck's half stays wide and the capped deck sits
// centred in it (73.5 px empty at 1440 open, 220 px after a drag past 480). These tests use the opt-in MEASURED mode of
// __tests__/fakes.js, and nothing about the OUTCOME (width, empty strip) is asserted until a calibration block has shown that
// the measured fake reproduces the recorded numbers from a stock split (no dock.js involved).
//
// BLOCKS.
//   "measured fake calibration"  (AC-N2)  the fake against the K2 snapshots: 473.5 / 553.5 / 420 / 480 / 247 / 407 / 73.5 / 220.
//   "medium re-clamp (N5656-3)"  (AC-N3)  dock.js under the measured fake, and eight mutants of dock.js that must each FAIL.
//
// The recorded numbers (outputs/repl_smoke/dock-check/result.K2.json, result_sha256 e0176c978f22f9ca9908ce1213308e5ca11e951b611f64b25ff89e05e178b1e2,
// dist ba43b338) used below: dock 962 px (1280x800) and 1122 px (1440x900); the dock's own padding is 5 px a side and the
// handle 5 px, so the notebook and the deck share 947 and 1107 px. All numbers are in px.

import { describe, expect, test } from "bun:test";

import {
  createFakeDeckApp,
  createFakeDockPanel,
  createFakeDocument,
  createFakeLumino,
  createFakeLuminoNotebook,
  createFakeWindow,
} from "./__tests__/fakes.js";

const NEAR = 2; // toBeCloseTo(x, 2): within 0.005, so "within 0.01 px" holds with room

// -- a stock split, no dock.js ---------------------------------------------------------------------------------------------

/** The page of the calibration: a dock `width` px wide, one notebook (inline min-width 2px), and a deck added the way dock.js does
 * (`split-right`, ref the notebook, inline CSS limits 420 / 480) or, with `limits: false`, a stock widget with no limits. */
function stock({ width, mode = "measured", limits = true, resizeRule } = {}) {
  const doc = createFakeDocument();
  const lumino = createFakeLumino(doc);
  const dock = createFakeDockPanel(lumino, doc, { width, mode, resizeRule });
  doc.body.appendChild(dock.node);
  const notebook = createFakeLuminoNotebook(lumino, doc, { id: "nb1" });
  notebook.node.style.minWidth = "2px";
  dock.seed(notebook);
  const deck = new lumino.Widget({ node: doc.createElement("div") });
  deck.id = "deck";
  if (limits) {
    deck.node.style.minWidth = "420px";
    deck.node.style.maxWidth = "480px";
  }
  dock.addWidget(deck, { mode: "split-right", ref: "nb1" });
  return { doc, lumino, dock, notebook, deck };
}

const deckWidth = (s) => s.deck.node.rect.width;
const notebookWidth = (s) => s.notebook.node.rect.width;
const dead = (s) => s.dock.deadSpace(s.deck, s.notebook);

describe("measured fake calibration", () => {
  test("1280 open (dock 962): the deck fills its 473.5 half, the notebook has 473.5, nothing is empty", () => {
    const s = stock({ width: 962 });
    expect(deckWidth(s)).toBeCloseTo(473.5, NEAR);
    expect(notebookWidth(s)).toBeCloseTo(473.5, NEAR);
    expect(dead(s)).toBeCloseTo(0, NEAR);
    // the deck starts exactly at the handle's right edge: nb.left 5 + 473.5 + handle 5
    expect(s.deck.node.rect.left).toBeCloseTo(5 + 473.5 + 5, NEAR);
  });

  test("1440 open (dock 1122): the deck is capped at 480 in a 553.5 half and centred: 36.75 + 36.75 px empty", () => {
    const s = stock({ width: 1122 });
    expect(deckWidth(s)).toBeCloseTo(480, NEAR);
    expect(notebookWidth(s)).toBeCloseTo(553.5, NEAR);
    expect(dead(s)).toBeCloseTo(73.5, NEAR);
    const handleRight = s.notebook.node.rect.left + notebookWidth(s) + s.dock.handleWidth;
    expect(s.deck.node.rect.left - handleRight).toBeCloseTo(36.75, NEAR); // empty on the handle side
    const dockInnerRight = s.dock.node.rect.left + s.dock.node.rect.width - s.dock.inset;
    expect(dockInnerRight - (s.deck.node.rect.left + deckWidth(s))).toBeCloseTo(36.75, NEAR); // and on the far side
  });

  for (const [width, notebook] of [[962, 527], [1122, 687]]) {
    test(`a drag to 300 at dock ${width}: clamped to the 420 minimum, the notebook takes ${notebook}, nothing is empty`, () => {
      const s = stock({ width });
      s.dock.drag(s.deck, 300);
      expect(deckWidth(s)).toBeCloseTo(420, NEAR);
      expect(notebookWidth(s)).toBeCloseTo(notebook, NEAR);
      expect(dead(s)).toBeCloseTo(0, NEAR);
    });
  }

  for (const [width, notebook] of [[962, 247], [1122, 407]]) {
    test(`a drag to 700 at dock ${width}: the deck stays 480, the notebook drops to ${notebook}, 220 px are empty (110 + 110)`, () => {
      const s = stock({ width });
      s.dock.drag(s.deck, 700);
      expect(deckWidth(s)).toBeCloseTo(480, NEAR);
      expect(notebookWidth(s)).toBeCloseTo(notebook, NEAR);
      expect(dead(s)).toBeCloseTo(220, NEAR);
      const handleRight = s.notebook.node.rect.left + notebookWidth(s) + s.dock.handleWidth;
      expect(s.deck.node.rect.left - handleRight).toBeCloseTo(110, NEAR);
    });
  }

  test("a 50/50 split with the limits cleared (the wide-like case) at dock 1122: 553.5 each, nothing is empty", () => {
    const s = stock({ width: 1122, limits: false });
    expect(deckWidth(s)).toBeCloseTo(553.5, NEAR);
    expect(notebookWidth(s)).toBeCloseTo(553.5, NEAR);
    expect(dead(s)).toBeCloseTo(0, NEAR);
  });

  test("saveLayout() reports the ALLOCATION as its sizes, like the recorded run (0.5/0.5, 0.6206/0.3794, 0.3677/0.6323)", () => {
    const s = stock({ width: 1122 });
    const sizes = () => s.dock.saveLayout().main.sizes;
    expect(sizes()[0]).toBeCloseTo(0.5, 6);
    s.dock.drag(s.deck, 300);
    expect(sizes()[0]).toBeCloseTo(0.6205962059620597, 6); // 687 / 1107, recorded split_sizes of geo_after_low
    expect(sizes()[1]).toBeCloseTo(0.3794037940379404, 6);
    s.dock.drag(s.deck, 700);
    expect(sizes()[0]).toBeCloseTo(0.3676603432700994, 6); // 407 / 1107, recorded split_sizes of geo_after_high
    expect(sizes()[1]).toBeCloseTo(0.6323396567299007, 6);
  });

  test("the limits are read when the dock refits, not before (S1 css_limits_refit): a changed inline max-width alone moves nothing", () => {
    const s = stock({ width: 1122 });
    s.deck.node.style.maxWidth = "450px";
    expect(deckWidth(s)).toBeCloseTo(480, NEAR);
    s.dock.fit();
    expect(deckWidth(s)).toBeCloseTo(450, NEAR);
    expect(dead(s)).toBeCloseTo(103.5, NEAR); // 553.5 - 450
  });

  test("the legacy mode on the same inputs still reports the legacy numbers: 1440 open is deck 480, notebook 960", () => {
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    const dock = createFakeDockPanel(lumino, doc, { width: 1440 }); // the default mode
    expect(dock.mode).toBe("legacy");
    doc.body.appendChild(dock.node);
    const notebook = createFakeLuminoNotebook(lumino, doc, { id: "nb1" });
    dock.seed(notebook);
    const deck = new lumino.Widget({ node: doc.createElement("div") });
    deck.id = "deck";
    deck.node.style.minWidth = "420px";
    deck.node.style.maxWidth = "480px";
    dock.addWidget(deck, { mode: "split-right", ref: "nb1" });
    expect(dock.widthOf(deck)).toBe(480);
    expect(dock.widthOf(notebook)).toBe(960); // the legacy rule hands the clamped 240 px to the notebook
    expect(deck.node.rect.width).toBe(0); // legacy nodes have no geometry
    expect(dock.pendingLayoutModified).toBe(0);
  });

  test("the legacy rule is the negative of 'the fake cannot show dead space': the same capped deck, the same dock, no empty strip", () => {
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    const app = createFakeDeckApp({ doc, notebooks: 1, width: 1122, lumino }); // legacy
    const deck = new lumino.Widget({ node: doc.createElement("div") });
    deck.id = "deck";
    deck.node.style.minWidth = "420px";
    deck.node.style.maxWidth = "480px";
    app.shell.add(deck, "main", { mode: "split-right", ref: "nb1" });
    // the legacy fake gives the notebook 1122 - 480 = 642 (everything the deck cannot use); the measured one gives 553.5
    expect(app.dock.widthOf(app.panels[0])).toBe(642);
    expect(app.dock.widthOf(deck)).toBe(480);
    const measured = stock({ width: 1122 });
    expect(notebookWidth(measured)).not.toBeCloseTo(642, 0);
  });

  test("measured mode is opt-in: the default is legacy, a bad mode or resize rule throws", () => {
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    expect(createFakeDockPanel(lumino, doc, { width: 1000 }).mode).toBe("legacy");
    expect(createFakeDeckApp({ doc, width: 1000 }).dock.measured).toBe(false);
    expect(createFakeDeckApp({ doc: createFakeDocument(), width: 1000, mode: "measured" }).dock.measured).toBe(true);
    expect(() => createFakeDockPanel(lumino, doc, { width: 1000, mode: "exact" })).toThrow();
    expect(() => createFakeDockPanel(lumino, doc, { width: 1000, mode: "measured", resizeRule: "other" })).toThrow();
  });

  test("a seeded notebook gets JupyterLab's min-width: 2px in measured mode only", () => {
    const measured = stock({ width: 962 });
    measured.notebook.node.style.minWidth = "";
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    const dock = createFakeDockPanel(lumino, doc, { width: 962, mode: "measured" });
    const bare = createFakeLuminoNotebook(lumino, doc, { id: "nb1" });
    dock.seed(bare);
    expect(bare.node.style.minWidth).toBe("2px");
    const legacy = createFakeDockPanel(lumino, doc, { width: 962 });
    const bare2 = createFakeLuminoNotebook(lumino, doc, { id: "nb2" });
    legacy.seed(bare2);
    expect(bare2.node.style.minWidth || "").toBe("");
  });

  test("the main area resizes under both rules: proportional keeps relative sizes, equalExcess gives each child the same extra px", () => {
    // the deck at 420 in a split of 947 (dock 962) -> dock 1122 (available 1107, +160)
    const proportional = stock({ width: 962, resizeRule: "proportional" });
    proportional.dock.drag(proportional.deck, 420);
    proportional.dock.setWidth(1122);
    // the half is 420 x 1107/947 = 490.97 px, the deck is capped at 480: the spec's "~11 px (proportional)"
    expect(deckWidth(proportional)).toBeCloseTo(480, NEAR);
    expect(dead(proportional)).toBeCloseTo(420 * (1107 / 947) - 480, NEAR);
    expect(dead(proportional)).toBeGreaterThan(10);
    expect(dead(proportional)).toBeLessThan(12);
    const equal = stock({ width: 962, resizeRule: "equalExcess" });
    equal.dock.drag(equal.deck, 420);
    equal.dock.setWidth(1122);
    expect(dead(equal)).toBeCloseTo(20, NEAR); // the half gets +80 (half of the extra 160): 500, the deck is capped at 480
    expect(deckWidth(equal)).toBeCloseTo(480, NEAR);
    expect(notebookWidth(equal)).toBeCloseTo(527 + 80, NEAR);
  });

  test("layoutModified is QUEUED: add, restore and a drag's release post it, a window resize does not, flush emits once", () => {
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    const app = createFakeDeckApp({ doc, width: 1122, lumino, mode: "measured" });
    const win = createFakeWindow({ app, document: doc, innerWidth: 1440 });
    void win;
    let emitted = 0;
    app.shell.layoutModified.connect(() => {
      emitted += 1;
    });
    const deck = new lumino.Widget({ node: doc.createElement("div") });
    deck.id = "deck";
    app.shell.add(deck, "main", { mode: "split-right", ref: "nb1" });
    expect(emitted).toBe(0); // not synchronous
    expect(app.dock.pendingLayoutModified).toBe(1);
    app.dock.drag(deck, 600);
    app.dock.restoreLayout(app.dock.saveLayout());
    expect(app.dock.pendingLayoutModified).toBe(3);
    expect(app.flushLayout()).toBe(true);
    expect(emitted).toBe(1); // the three posts coalesce into one emission
    expect(app.flushLayout()).toBe(false);
    app.dock.saveLayout();
    app.dock.fit();
    app.dock.setWidth(1000); // a window resize
    expect(app.dock.pendingLayoutModified).toBe(0);
    app.dock.setWidth(1200, { layoutModified: true }); // a shell call (collapseLeft / expandLeft)
    expect(app.dock.pendingLayoutModified).toBe(1);
    expect(app.flushLayout()).toBe(true);
    expect(emitted).toBe(2);
  });

  test("the legacy shell still emits layoutModified inside add (no behaviour change for dock.test.js)", () => {
    const doc = createFakeDocument();
    const lumino = createFakeLumino(doc);
    const app = createFakeDeckApp({ doc, width: 1122, lumino });
    let emitted = 0;
    app.shell.layoutModified.connect(() => {
      emitted += 1;
    });
    const deck = new lumino.Widget({ node: doc.createElement("div") });
    deck.id = "deck";
    app.shell.add(deck, "main", { mode: "split-right", ref: "nb1" });
    expect(emitted).toBe(1);
  });
});
