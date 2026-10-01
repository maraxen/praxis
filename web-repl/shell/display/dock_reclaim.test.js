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
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import * as realDock from "./dock.js";
import {
  createFakeBroadcastHub,
  createFakeDeckApp,
  createFakeDockPanel,
  createFakeDocument,
  createFakeLumino,
  createFakeLuminoNotebook,
  createFakeWindow,
} from "./__tests__/fakes.js";

const HERE = dirname(fileURLToPath(import.meta.url));
const REPO = join(HERE, "..", "..", "..");

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

// ===============================================================================================================================
// "medium re-clamp (N5656-3)": dock.js under the MEASURED fake (AC-N3). RED until T4 (`reclaimMedium`) lands.
// ===============================================================================================================================
//
// WHAT THE FIX MUST DO (spec N5656-3, decisions Q1 = 420, Q2 = (b)): at 1280-1599 px, after an open, a tier entry, the end of a
// splitter drag and a main-area resize (a file-browser toggle or a window resize), size the split through the layout path
// (`saveLayout()` -> edit the split's `sizes` -> `restoreLayout()`) so the deck's half is exactly the deck's width and the notebook
// gets the rest. The width: OPEN_WIDTH_MEDIUM after an open or a tier entry; the width the deck already had after a main-area
// change; the deck's own clamped width after a drag.
//
// NAMING CONTRACT FOR T4. The mutants below patch dock.js by pattern INSIDE a named function. They need: the exports
// OPEN_WIDTH_MEDIUM (420), RECLAIM_EPS_PX (1) and RECLAIM_STREAK_MAX (3); a function declaration `reclaimMedium()` that contains,
// as the spec writes them, `settledDeck === null`, `target / A`, `<= RECLAIM_EPS_PX` (the convergence test), `reclaimStreak >=
// RECLAIM_STREAK_MAX` (the cap) and `tier === "medium"` (or `tier !== "medium"`); and the call `reclaimMedium()` inside the existing
// functions `onLayoutModified` and `onDockResized`. A mutant whose pattern is absent fails with a message saying so: that is "T4 does
// not follow the contract", not a pass.
//
// HOW RED READS. Before T4 the guard tests below (a drag to 460 or to 300, the 1600 -> 1440 tier entry, the wide path, the closed
// panel, the drawer, a deck out of its split, a sibling with a max-width) PASS: they describe behaviour the fix must keep. The
// outcome tests (open, drag past 480, toggle, resize, close + reopen) FAIL with a measured empty strip (73.5 px at 1440 open, 220 px
// after the drag to 700), and every mutant test fails at load because `reclaimMedium` does not exist yet.

const BASE = "https://praxis.test/";
const OPEN = realDock.OPEN_WIDTH_MEDIUM ?? 420; // a missing export is caught by its own test, not by NaN in the others
const STREAK_MAX = realDock.RECLAIM_STREAK_MAX ?? 3;
const MAX_ROUNDS = 10;

function recordingLogger() {
  const errors = [];
  const warns = [];
  return { errors, warns, error: (...a) => errors.push(a), warn: (...a) => warns.push(a), log() {}, debug() {} };
}

/**
 * One page: the measured fake dock (a notebook; the window is `width` px wide and the sidebars take `sidebar` px, so the dock is
 * 962 / 1122 px at 1280 / 1440), a BroadcastChannel hub, a window with a ResizeObserver, and dock.js mounted on it.
 *
 * `layoutModified` is QUEUED by the fake dock and `env.settle()` plays the browser: it delivers the queue (the shell's 0 ms
 * debouncer) and fires a ResizeObserver when the dock's width changed since it last looked (or on its first look: a browser
 * notifies once when observation starts). More than MAX_ROUNDS rounds throws "layout did not settle".
 */
function makeEnv({ mod = realDock, width = 1440, sidebar = 318, resizeRule = "proportional", pad = 8, notebookMaxWidth = null } = {}) {
  const doc = createFakeDocument();
  doc.attrLog = [];
  doc.appendLog = [];
  const hub = createFakeBroadcastHub();
  const lumino = createFakeLumino(doc);
  const app = createFakeDeckApp({ doc, notebooks: 1, width: width - sidebar, lumino, mode: "measured", resizeRule });
  for (const panel of app.panels) panel.content.node._padding = pad;
  if (notebookMaxWidth) {
    app.panels[0].node.style.maxWidth = notebookMaxWidth;
    app.dock.fit(); // Lumino reads the limits at a refit
  }
  const win = createFakeWindow({ app, document: doc, broadcast: hub, innerWidth: width });
  const logger = recordingLogger();
  const observed = new Map(); // ResizeObserver -> the dock width it was last notified with
  const env = {
    doc, hub, lumino, app, win, logger, dock: app.dock, width, sidebar, rounds: [], ctl: null,
    announce: (viewer = "v1") => hub.post("praxis_viz3d", JSON.stringify({ kind: "announce", viewer, deck: "PlateDeck", session: "sess1" })),
    toggle: () => app.commands.execute("praxis:toggle-deck-panel"),
    /** A window resize: the window and the dock change width, the `resize` event fires now, the ResizeObserver at the next settle. */
    resize(w) {
      env.width = w;
      win.innerWidth = w;
      app.dock.setWidth(w - env.sidebar);
      win.dispatchEvent({ type: "resize" });
    },
    /** The file browser opens (px > 0) or closes: the dock changes width, the window does not; the shell posts layoutModified. */
    setSidebar(px) {
      env.sidebar = px;
      app.dock.setWidth(env.width - px, { layoutModified: true });
    },
    /** The user drags the splitter so that the deck's HALF is `px` wide, and releases. */
    drag: (px) => app.dock.drag(env.deckWidget(), px),
    settle() {
      let rounds = 0;
      for (;;) {
        let acted = app.flushLayout();
        const dockWidth = app.dock.node.rect.width;
        for (const ro of win.resizeObservers.all.slice()) {
          if (ro.targets.size === 0 || observed.get(ro) === dockWidth) continue;
          observed.set(ro, dockWidth);
          ro.callback(Array.from(ro.targets, (target) => ({ target })), ro);
          acted = true;
        }
        if (!acted) break;
        rounds += 1;
        if (rounds > MAX_ROUNDS) throw new Error("layout did not settle");
      }
      env.rounds.push(rounds);
      return rounds;
    },
    deckWidget() {
      const found = lumino.instances.filter((w) => w.node.classList.contains("praxis-deck-panel"));
      return found.length ? found[found.length - 1] : null;
    },
    notebook: () => app.panels[0],
    deckW: () => env.deckWidget().node.rect.width,
    nbW: () => app.panels[0].node.rect.width,
    dead: () => app.dock.deadSpace(env.deckWidget(), app.panels[0]),
    avail: () => app.dock.availableWidth(),
    restores: () => app.dock.restoreCalls.length,
    iframesInserted: () => doc.appendLog.filter((e) => e.child.localName === "iframe").length,
    srcWrites: () => doc.attrLog.filter((a) => a.tag === "iframe" && a.name === "src").length,
    remount(overrides = {}) {
      env.ctl = mod.mountDock({ app, win, logger, controllers: {}, baseUrl: BASE, ...overrides });
      return env.ctl;
    },
  };
  env.remount();
  return env;
}

/** Fails with the numbers in the message: `actual` is within `tol` of `expected`. */
function expectNear(actual, expected, tol, label) {
  if (!(Math.abs(actual - expected) <= tol)) throw new Error(`${label}: ${actual} is not within ${tol} of ${expected}`);
}

function expectAtMost(actual, limit, label) {
  if (!(actual <= limit)) throw new Error(`${label}: ${actual} is more than ${limit}`);
}

/** The panel is open and connected in the split, with one iframe, and the shell logged no error. */
function expectOpenInSplit(env) {
  expect(env.ctl.snapshot().state).toBe("open-connected");
  expect(env.ctl.snapshot().home).toBe("split");
  expect(env.logger.errors).toEqual([]);
}

/** Open the panel and let the layout settle (the common first step). */
function openPanel(env) {
  env.announce();
  env.settle();
  expectOpenInSplit(env);
  return env;
}

describe("medium re-clamp (N5656-3)", () => {
  test("the module exports the three constants the spec names (OPEN_WIDTH_MEDIUM 420, RECLAIM_EPS_PX 1, RECLAIM_STREAK_MAX 3)", () => {
    expect(realDock.OPEN_WIDTH_MEDIUM).toBe(420);
    expect(realDock.RECLAIM_EPS_PX).toBe(1);
    expect(realDock.RECLAIM_STREAK_MAX).toBe(3);
  });

  test("OPEN_WIDTH_MEDIUM equals the harness's OPEN_WIDTH_MEDIUM_PX (the Q1 ruling lives in two languages; they must agree)", () => {
    const python = readFileSync(join(REPO, "scripts", "repl_smoke.py"), "utf8");
    const match = /^OPEN_WIDTH_MEDIUM_PX\s*=\s*([0-9.]+)/m.exec(python);
    expect(match).not.toBeNull();
    expect(Number(match[1])).toBe(realDock.OPEN_WIDTH_MEDIUM);
  });

  for (const width of [1280, 1440]) {
    describe(`at ${width} px`, () => {
      test("(a) open: the deck is OPEN_WIDTH_MEDIUM wide, nothing is empty, the notebook has the rest, one iframe, one src write", () => {
        const env = makeEnv({ width });
        env.announce();
        const rounds = env.settle();
        expectOpenInSplit(env);
        expectNear(env.deckW(), OPEN, 0.5, "deck width");
        expectAtMost(env.dead(), 0.5, "empty strip");
        expectNear(env.nbW(), env.avail() - OPEN, 0.5, "notebook width");
        expect(env.restores()).toBeGreaterThanOrEqual(1);
        expect(env.iframesInserted()).toBe(1);
        expect(env.srcWrites()).toBe(1); // T2's own write; the re-clamp never writes src
        expect(env.ctl.snapshot().tier).toBe("medium");
        expect(env.deckWidget().node.style.minWidth).toBe("420px"); // the CSS limits are untouched
        expect(env.deckWidget().node.style.maxWidth).toBe("480px");
        expectAtMost(rounds, 3, "rounds to settle");
      });

      test("(b) a drag to 460 keeps 460: the deck is 460, nothing is empty, and no restore was needed (nothing to fix, nothing done)", () => {
        const env = openPanel(makeEnv({ width }));
        const before = env.restores();
        env.drag(460);
        const rounds = env.settle();
        expectNear(env.deckW(), 460, 0.5, "deck width");
        expectAtMost(env.dead(), 0.5, "empty strip");
        expect(env.restores()).toBe(before);
        expectAtMost(rounds, 3, "rounds to settle");
      });

      test("(c) a drag to 700 is clamped to 480 and the 220 px strip goes to the notebook, with exactly one restore for that release", () => {
        const env = openPanel(makeEnv({ width }));
        const before = env.restores();
        env.drag(700);
        const rounds = env.settle();
        expectNear(env.deckW(), 480, 0.5, "deck width");
        expectAtMost(env.dead(), 0.5, "empty strip");
        expectNear(env.nbW(), env.avail() - 480, 0.5, "notebook width");
        expect(env.restores() - before).toBe(1);
        expectAtMost(rounds, 3, "rounds to settle");
        expect(env.logger.errors).toEqual([]);
      });

      test("(d) a drag to 300 is clamped to 420 and nothing is empty", () => {
        const env = openPanel(makeEnv({ width }));
        env.drag(300);
        env.settle();
        expectNear(env.deckW(), 420, 0.5, "deck width");
        expectAtMost(env.dead(), 0.5, "empty strip");
      });

      for (const resizeRule of ["proportional", "equalExcess"]) {
        test(`(e, j) closing and reopening the file browser keeps the deck at 480 and nothing empty (resize rule ${resizeRule})`, () => {
          const env = openPanel(makeEnv({ width, resizeRule }));
          env.drag(700);
          env.settle();
          expectNear(env.deckW(), 480, 0.5, "deck before the toggle");
          const dockBefore = env.dock.node.rect.width;
          env.setSidebar(0); // the file browser closes: the main area grows by 318 px
          expect(env.dock.node.rect.width - dockBefore).toBe(318); // the toggle happened
          const rounds = env.settle();
          expectNear(env.deckW(), 480, 0.5, "deck after the file browser closed");
          expectAtMost(env.dead(), 0.5, "empty strip after the file browser closed");
          expectAtMost(rounds, 3, "rounds to settle");
          env.setSidebar(318); // and opens again
          env.settle();
          expectNear(env.deckW(), 480, 0.5, "deck after the file browser opened");
          expectAtMost(env.dead(), 0.5, "empty strip after the file browser opened");
          expectNear(env.dock.node.rect.width, dockBefore, 0.5, "the dock is back");
          expect(env.logger.errors).toEqual([]);
        });
      }
    });
  }

  describe("a window resize inside the 1280-1599 tier", () => {
    for (const resizeRule of ["proportional", "equalExcess"]) {
      test(`(f, j) 1280 -> 1440 with the deck at 420: still 420 and nothing empty (resize rule ${resizeRule})`, () => {
        const env = openPanel(makeEnv({ width: 1280, resizeRule }));
        expectNear(env.deckW(), 420, 0.5, "deck at 1280");
        const dockBefore = env.dock.node.rect.width;
        env.resize(1440);
        expect(env.dock.node.rect.width - dockBefore).toBe(160); // the resize happened
        const rounds = env.settle();
        expectNear(env.deckW(), 420, 0.5, "deck at 1440");
        expectAtMost(env.dead(), 0.5, "empty strip at 1440");
        expectAtMost(rounds, 3, "rounds to settle");
        expect(env.logger.errors).toEqual([]);
      });

      test(`(f, j) 1440 -> 1280 with the deck at 480: still 480, the notebook has 467 (resize rule ${resizeRule})`, () => {
        const env = openPanel(makeEnv({ width: 1440, resizeRule }));
        env.drag(700);
        env.settle();
        expectNear(env.deckW(), 480, 0.5, "deck at 1440");
        const dockBefore = env.dock.node.rect.width;
        env.resize(1280);
        expect(dockBefore - env.dock.node.rect.width).toBe(160);
        env.settle();
        expectNear(env.deckW(), 480, 0.5, "deck at 1280");
        expectAtMost(env.dead(), 0.5, "empty strip at 1280");
        expectNear(env.nbW(), 467, 0.5, "notebook at 1280");
      });

      test(`(f, j) the user's own width survives a resize: a deck dragged to 460 is still 460 after 1440 -> 1280 -> 1440 (${resizeRule})`, () => {
        const env = openPanel(makeEnv({ width: 1440, resizeRule }));
        env.drag(460);
        env.settle();
        env.resize(1280);
        env.settle();
        expectNear(env.deckW(), 460, 0.5, "deck at 1280");
        expectAtMost(env.dead(), 0.5, "empty strip at 1280");
        env.resize(1440);
        env.settle();
        expectNear(env.deckW(), 460, 0.5, "deck at 1440");
        expectAtMost(env.dead(), 0.5, "empty strip at 1440");
      });
    }
  });

  describe("tier entry and the wide path", () => {
    test("(g) 1600 -> 1440: the deck is OPEN_WIDTH_MEDIUM and nothing is empty; at 1600 itself only layoutSize restores occurred", () => {
      const env = openPanel(makeEnv({ width: 1600 })); // the dock is 1282 px, as recorded (fit_wide)
      const wideRestores = env.dock.restoreCalls.slice();
      expect(wideRestores.length).toBeGreaterThanOrEqual(1);
      // layoutSize asks for max(420, main - 960 - pad) / main = 420 / 1282 of the dock; the re-clamp (target / A) would ask for 420 / 1267
      for (const config of wideRestores) expectNear(config.main.sizes[1], 420 / 1282, 0.0005, "deck fraction of a wide restore");
      expectNear(env.deckW(), 415.08, 1, "the wide path lands ~5 px short of its target, as recorded");
      expect(env.deckWidget().node.style.maxWidth || "").toBe("");
      env.resize(1440);
      const rounds = env.settle();
      expectNear(env.deckW(), OPEN, 0.5, "deck after entering the medium tier");
      expectAtMost(env.dead(), 0.5, "empty strip after entering the medium tier");
      expect(env.deckWidget().node.style.maxWidth).toBe("480px");
      expectAtMost(rounds, 3, "rounds to settle");
      expect(env.logger.errors).toEqual([]);
    });

    test("(g) at 1600 with the file browser closed (dock 1600, available 1585) layoutSize lands the deck at 618.2 and only layoutSize restores occur", () => {
      const env = openPanel(makeEnv({ width: 1600, sidebar: 0 }));
      expectNear(env.deckW(), (624 * 1585) / 1600, 1, "deck width (624 x 1585 / 1600)");
      expect(env.dock.restoreCalls.length).toBeGreaterThanOrEqual(1);
      for (const config of env.dock.restoreCalls) expectNear(config.main.sizes[1], 624 / 1600, 0.0005, "deck fraction of a wide restore");
      env.resize(1700);
      env.settle();
      expect(env.logger.errors).toEqual([]);
    });
  });

  describe("convergence and the streak cap", () => {
    test("(h) every trigger settles within 3 rounds: open, three drags, a toggle both ways, a resize both ways, a tier round trip", () => {
      const env = makeEnv({ width: 1440 });
      env.announce();
      env.settle();
      env.drag(460);
      env.settle();
      env.drag(700);
      env.settle();
      env.drag(300);
      env.settle();
      env.setSidebar(0);
      env.settle();
      env.setSidebar(318);
      env.settle();
      env.resize(1280);
      env.settle();
      env.resize(1440);
      env.settle();
      env.resize(1600);
      env.settle();
      env.resize(1440);
      env.settle();
      expect(env.rounds.length).toBe(10);
      expect(Math.max(...env.rounds)).toBeLessThanOrEqual(3);
      expectNear(env.deckW(), OPEN, 0.5, "deck at the end");
      expectAtMost(env.dead(), 0.5, "empty strip at the end");
      expect(env.logger.errors).toEqual([]);
    });

    test("(i) a layout that refuses the sizes gets at most RECLAIM_STREAK_MAX restores per trigger and one note", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      const original = env.dock.restoreLayout.bind(env.dock);
      // a layout that ignores the sizes it is given: it restores what it already has (and still posts layoutModified)
      env.dock.restoreLayout = () => original(env.dock.saveLayout());
      const before = env.restores();
      const warnsBefore = env.logger.warns.length;
      env.drag(700);
      env.settle(); // must settle: a loop here is the failure this cap exists for (throws "layout did not settle")
      const restores = env.restores() - before;
      expect(restores).toBeGreaterThanOrEqual(1);
      expect(restores).toBeLessThanOrEqual(STREAK_MAX);
      expect(env.logger.warns.length - warnsBefore).toBe(1);
      expect(env.logger.errors).toEqual([]);
    });
  });

  describe("(k) no re-clamp, no error", () => {
    test("closed: a toggled-off panel is not observed and layout is never touched", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      env.toggle(); // close panel
      expect(env.ctl.snapshot().state).toBe("closed");
      env.settle();
      const restores = env.restores();
      env.resize(1300);
      env.setSidebar(0);
      env.settle();
      expect(env.restores()).toBe(restores);
      expect(env.logger.errors).toEqual([]);
    });

    test("drawer: below 1280 px layout is never read or written", () => {
      const env = makeEnv({ width: 1152 });
      env.announce();
      env.settle();
      expect(env.ctl.snapshot().home).toBe("drawer");
      env.resize(1200);
      env.settle();
      expect(env.dock.restoreCalls.length).toBe(0);
      expect(env.dock.saveCalls).toBe(0);
      expect(env.logger.errors).toEqual([]);
    });

    test("a deck the user moved out of its horizontal split: no restore and no error", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      const deck = env.deckWidget();
      env.dock.layoutTree = { type: "tab-area", widgets: [env.notebook(), deck], currentIndex: 0 };
      env.dock._reflow(false);
      const restores = env.restores();
      expect(() => {
        env.resize(1400);
        env.settle();
      }).not.toThrow();
      expect(env.restores()).toBe(restores);
      expect(env.logger.errors).toEqual([]);
    });

    test("a sibling with a max-width is not measured: no restore and no error", () => {
      const env = makeEnv({ width: 1440, notebookMaxWidth: "900px" });
      env.announce();
      env.settle();
      expect(env.ctl.snapshot().state).toBe("open-connected");
      expect(env.restores()).toBe(0);
      expect(env.logger.errors).toEqual([]);
    });

    test("a dock panel without saveLayout / restoreLayout leaves the width to Lumino, no error", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      env.dock.saveLayout = undefined;
      expect(() => {
        env.drag(700);
        env.settle();
      }).not.toThrow();
      expect(env.logger.errors).toEqual([]);
    });
  });

  describe("close and reopen", () => {
    test("(a, k) a closed and reopened panel is a fresh attach: it opens at OPEN_WIDTH_MEDIUM again, not at the width it had", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      env.drag(460);
      env.settle();
      expectNear(env.deckW(), 460, 0.5, "deck before the close");
      env.toggle(); // close
      env.settle();
      env.toggle(); // reopen: T4 -> waiting; the answering announce connects it (T6)
      env.announce();
      env.settle();
      expectOpenInSplit(env);
      expectNear(env.deckW(), OPEN, 0.5, "deck after the reopen");
      expectAtMost(env.dead(), 0.5, "empty strip after the reopen");
    });

    test("(a) opening at 1280 after a close at another width: the reopen is re-clamped too", () => {
      const env = openPanel(makeEnv({ width: 1440 }));
      env.toggle();
      env.settle();
      env.resize(1280);
      env.settle();
      env.toggle();
      env.announce();
      env.settle();
      expectOpenInSplit(env);
      expectNear(env.deckW(), OPEN, 0.5, "deck after the reopen at 1280");
      expectAtMost(env.dead(), 0.5, "empty strip after the reopen at 1280");
    });
  });
});

// ===============================================================================================================================
// negative controls: dock.js with ONE piece of the re-clamp broken must FAIL the probe that guards it (AC-N3 M1-M8)
// ===============================================================================================================================

describe("medium re-clamp (N5656-3): mutants", () => {
  /** The index just past a string literal that starts at `i` (a quote, a double quote or a backtick). */
  function skipString(source, i) {
    const quote = source[i];
    for (let j = i + 1; j < source.length; j += 1) {
      if (source[j] === "\\") j += 1;
      else if (source[j] === quote) return j;
    }
    return source.length;
  }

  /** `{open, close}`: the indexes of the braces of `function <name>(...) {...}` in dock.js (strings and comments skipped). */
  function bodyRange(source, name) {
    const found = new RegExp(`function\\s+${name}\\s*\\(`).exec(source);
    if (!found) throw new Error(`T4 contract: dock.js has no function ${name}()`);
    const open = source.indexOf("{", found.index);
    let depth = 0;
    for (let i = open; i < source.length; i += 1) {
      const ch = source[i];
      if (ch === "/" && source[i + 1] === "/") {
        const eol = source.indexOf("\n", i);
        if (eol < 0) break;
        i = eol;
      } else if (ch === "/" && source[i + 1] === "*") {
        i = source.indexOf("*/", i + 2) + 1;
      } else if (ch === '"' || ch === "'" || ch === "`") {
        i = skipString(source, i);
      } else if (ch === "{") {
        depth += 1;
      } else if (ch === "}") {
        depth -= 1;
        if (depth === 0) return { open, close: i };
      }
    }
    throw new Error(`T4 contract: the body of ${name}() does not close`);
  }

  /** dock.js's source with the mutant applied inside `spec.fn` (an `identity` application matches the same pattern and changes nothing). */
  function mutate(source, spec, identity) {
    const { open, close } = bodyRange(source, spec.fn);
    let body = source.slice(open + 1, close);
    let hits = 0;
    if (spec.prepend !== undefined) {
      body = (identity ? "" : spec.prepend) + body;
      hits = 1;
    } else {
      for (const [pattern, replacement] of spec.replace) {
        body = body.replace(pattern, (m) => {
          hits += 1;
          return identity ? m : replacement;
        });
      }
    }
    if (hits < 1) throw new Error(`T4 contract: nothing to patch in ${spec.fn}() for "${spec.name}" (pattern ${spec.replace ? spec.replace.map((r) => r[0]).join(" | ") : "prepend"})`);
    return source.slice(0, open + 1) + body + source.slice(close);
  }

  let counter = 0;
  async function load(spec, identity) {
    const source = readFileSync(join(HERE, "dock.js"), "utf8");
    const patched = mutate(source, spec, identity).replace(
      /from "\.\/([\w-]+)\.js"/g,
      (_m, name) => `from "${pathToFileURL(join(HERE, `${name}.js`)).href}"`,
    );
    const dir = mkdtempSync(join(tmpdir(), "dock-reclaim-mutant-"));
    counter += 1;
    const file = join(dir, `dock_${counter}.mjs`);
    writeFileSync(file, patched);
    return import(pathToFileURL(file).href);
  }

  // The probes. Each is a function of a dock module: it throws when the module misbehaves.
  const probes = {
    // M1: with no re-clamp the 1440 open leaves 73.5 px empty and the deck at 480 (AC-N2's measured fake shows exactly that)
    open1440(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      expectNear(env.deckW(), OPEN, 0.5, "deck at 1440 open");
      expectAtMost(env.dead(), 0.5, "empty strip at 1440 open");
    },
    // M2: a drag resizes no window, so no ResizeObserver fires; only layoutModified can fix the 220 px strip
    drag700(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      env.drag(700);
      env.settle();
      expectNear(env.deckW(), 480, 0.5, "deck after the drag");
      expectAtMost(env.dead(), 0.5, "empty strip after the drag");
    },
    // M3: the fake models a window resize as a ResizeObserver callback only (no layoutModified): 11-20 px stay empty
    resizeUp(mod) {
      const env = openPanel(makeEnv({ mod, width: 1280 }));
      env.resize(1440);
      env.settle();
      expectNear(env.deckW(), 420, 0.5, "deck at 1440");
      expectAtMost(env.dead(), 0.5, "empty strip at 1440");
    },
    // M4: the user's width is kept: a deck dragged to 460 must not snap back to 420
    keepsMid(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      const before = env.restores();
      env.drag(460);
      env.settle();
      expectNear(env.deckW(), 460, 0.5, "deck after the drag to 460");
      expect(env.restores()).toBe(before);
    },
    // M5: the fraction is target / A; with a wrong denominator the half lands 6.4 px short of 480
    exact480(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      env.drag(700);
      env.settle();
      expectNear(env.deckW(), 480, 0.5, "deck after the drag to 700");
      expectAtMost(env.dead(), 0.5, "empty strip after the drag to 700");
    },
    // M6: without the convergence test every layoutModified after a restore restores again: one restore per release is gone
    oneRestorePerRelease(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      const before = env.restores();
      env.drag(700);
      const rounds = env.settle();
      expect(env.restores() - before).toBe(1);
      expectAtMost(rounds, 3, "rounds to settle");
    },
    // M7: a layout that refuses the sizes never converges without the cap: settle() throws "layout did not settle"
    refusingLayout(mod) {
      const env = openPanel(makeEnv({ mod, width: 1440 }));
      const original = env.dock.restoreLayout.bind(env.dock);
      env.dock.restoreLayout = () => original(env.dock.saveLayout());
      const before = env.restores();
      env.drag(700);
      env.settle();
      expect(env.restores() - before).toBeGreaterThanOrEqual(1); // it did try
      expectAtMost(env.restores() - before, STREAK_MAX, "restores for one trigger");
    },
    // M8: at 1600 with the file browser closed layoutSize lands the deck at 624 x 1585 / 1600 = 618.2; the re-clamp must not run there
    wide1600(mod) {
      const env = openPanel(makeEnv({ mod, width: 1600, sidebar: 0 }));
      expectNear(env.deckW(), (624 * 1585) / 1600, 1, "deck width at 1600");
      for (const config of env.dock.restoreCalls) expectNear(config.main.sizes[1], 624 / 1600, 0.0005, "deck fraction of a restore");
    },
  };

  // The patch tooling is itself checked on a toy source, so a mutant that "survives" or "dies" is never the tool's doing.
  const TOY = [
    "function other() { return reclaimMedium(); }",
    "function reclaimMedium() {",
    "  // a comment with a brace { and a call reclaimMedium()",
    '  const text = "a string with } and tier === \\"medium\\"";',
    '  if (tier === "medium") { return settledDeck === null ? target / A : 0; }',
    "  return 1;",
    "}",
    'function after() { return tier === "medium" && reclaimMedium(); }',
  ].join("\n");

  test("patch tooling: a mutation edits only inside the named function, even with braces in strings and comments", () => {
    const spec = { name: "toy", fn: "reclaimMedium", replace: [[/\btier\s*===?\s*"medium"/g, "FLIPPED"], [/\btarget\s*\/\s*A\b/g, "target / (A + 15)"]] };
    const out = mutate(TOY, spec, false);
    expect(out).toContain("if (FLIPPED) { return settledDeck === null ? target / (A + 15) : 0; }");
    expect(out).toContain("function other() { return reclaimMedium(); }"); // before: untouched
    expect(out).toContain('function after() { return tier === "medium" && reclaimMedium(); }'); // after: untouched
    expect(out.split("\n").length).toBe(TOY.split("\n").length);
  });

  test("patch tooling: an identity application changes nothing, a prepend lands first in the body, an absent pattern throws", () => {
    const spec = { name: "toy", fn: "reclaimMedium", replace: [[/\bsettledDeck\s*===?\s*null\b/g, "true"]] };
    expect(mutate(TOY, spec, true)).toBe(TOY);
    expect(mutate(TOY, { name: "pre", fn: "reclaimMedium", prepend: "return;" }, false)).toContain("function reclaimMedium() {return;\n");
    expect(mutate(TOY, { name: "pre", fn: "reclaimMedium", prepend: "return;" }, true)).toBe(TOY);
    expect(() => mutate(TOY, { name: "absent", fn: "reclaimMedium", replace: [[/\bnoSuchToken\b/g, "x"]] }, false)).toThrow(/nothing to patch/);
    expect(() => mutate(TOY, { name: "nofn", fn: "noSuchFunction", prepend: "return;" }, false)).toThrow(/no function noSuchFunction/);
    expect(() => mutate(TOY, { name: "pre", fn: "after", replace: [[/\bnoSuchToken\b/g, "x"]] }, true)).toThrow(/nothing to patch/);
  });

  const cases = [
    { id: "M1", name: "no re-clamp (reclaimMedium returns at once)", probe: probes.open1440, fn: "reclaimMedium", prepend: "return;" },
    { id: "M2", name: "no layoutModified trigger", probe: probes.drag700, fn: "onLayoutModified", replace: [[/\breclaimMedium\(\)/g, "void 0"]] },
    { id: "M3", name: "no ResizeObserver trigger", probe: probes.resizeUp, fn: "onDockResized", replace: [[/\breclaimMedium\(\)/g, "void 0"]] },
    {
      id: "M4", name: "the width is not kept (the target is always OPEN_WIDTH_MEDIUM)", probe: probes.keepsMid, fn: "reclaimMedium",
      replace: [[/\bsettledDeck\s*===?\s*null\b/g, "true"], [/\bsettledDeck\s*!==?\s*null\b/g, "false"]],
    },
    { id: "M5", name: "the wrong denominator (target / (A + 15))", probe: probes.exact480, fn: "reclaimMedium", replace: [[/\btarget\s*\/\s*A\b/g, "target / (A + 15)"]] },
    { id: "M6", name: "no convergence test (the early return when the half is within RECLAIM_EPS_PX of the target)", probe: probes.oneRestorePerRelease, fn: "reclaimMedium", replace: [[/<=\s*RECLAIM_EPS_PX\b/g, "<= -1"]] },
    { id: "M7", name: "no streak cap", probe: probes.refusingLayout, fn: "reclaimMedium", replace: [[/\breclaimStreak\s*>=\s*RECLAIM_STREAK_MAX\b/g, "false"]] },
    {
      id: "M8", name: "the re-clamp also runs at the wide tier (no tier === medium condition)", probe: probes.wide1600, fn: "reclaimMedium",
      replace: [[/\btier\s*!==?\s*"medium"/g, "false"], [/\btier\s*===?\s*"medium"/g, "true"]],
    },
  ];

  for (const spec of cases) {
    const label = `${spec.id} ${spec.name}`;
    test(`positive control: the real dock.js passes the probe of ${label}`, () => {
      spec.probe(realDock);
    });

    test(`positive control: the patch loader with an identity patch passes it too (${spec.id})`, async () => {
      const mod = await load(spec, true);
      spec.probe(mod);
    });

    test(`negative control: ${label} FAILS its probe`, async () => {
      const mod = await load(spec, false);
      expect(() => spec.probe(mod)).toThrow();
    });
  }
});
