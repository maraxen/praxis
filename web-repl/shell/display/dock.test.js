// dock.test.js -- the deck panel widget (spec
// .praxia/docs/specs/260929_notebook-display-epic.md, task C5; sections D6, D11 "Deck-panel
// state machine", D12, D14, 3.6; AC-35 and AC-36 unit halves, AC-38 state-table half).
//
// dock.js is exercised against the fakes in __tests__/fakes.js: a Lumino widget whose root
// class sits at chain index 3 (S1-A), a main DockPanel that lays out split-right and
// honours inline min/max width the way S1 measured, a shell whose `add` insists on a widget
// id, commands, a BroadcastChannel hub, a ResizeObserver and the session contexts of
// notebook panels. What the SHELL posts on `praxis_viz3d` is recorded by a probe channel
// that does not hear the kernel's own posts, so "the shell posted a query" is read from
// the wire, never from dock.js.
//
// READING THE PANEL. Every read of the panel goes through the DOM the widget owns, at the
// moment of the read (`env.frames()` walks the deck widget's node each time). Invariants
// I1..I6 are checked that way after every transition, never from an element a test held.
// The one place a test keeps an element is an identity check ("the removed iframe is never
// reused", "a tier crossing keeps the same iframe"), stated as such.
//
// NEGATIVE CONTROLS. The last describe block patches dock.js's own source (each anchor must
// match exactly once) and requires each of the mutants below to FAIL its probe scenario:
// a panel that never removes the iframe, one that reacts to `open` / `msg`, one that skips
// `query` on reopen, one that ignores `parent.fit()`, and one that never observes resizes.

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

import * as realDock from "./dock.js";
import { mount as mountDisplay } from "./index.js";
import { mountInteract } from "./interact.js";
import {
  createFakeBroadcastHub,
  createFakeCell,
  createFakeDeckApp,
  createFakeDocument,
  createFakeLumino,
  createFakePlrViewer,
  createFakeWindow,
  praxisOutput,
  stamp,
} from "./__tests__/fakes.js";

// -- the spec's verbatim strings (D11 table, section 3.6, D12) -----------------------------------------------------
const NO_VIEWER = "No deck viewer is running. Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell.";
const LOST = "The deck view lost its connection. Close and reopen the deck panel, or run `dock(deck)` again.";
const MOTION = "Motion playback is not available for this backend.";
const TOGGLE = "praxis:toggle-deck-panel";
const BASE = "https://praxis.test/";
const HERE = dirname(fileURLToPath(import.meta.url));

// -- the environment -------------------------------------------------------------------------------------------------------

function recordingLogger() {
  const errors = [];
  const warns = [];
  return { errors, warns, error: (...a) => errors.push(a), warn: (...a) => warns.push(a), log() {}, debug() {} };
}

function walk(el, visit) {
  visit(el);
  for (const child of el.children) walk(child, visit);
}

const viewerOf = (frame) => new URL(frame.getAttribute("src")).searchParams.get("viewer");

/**
 * One page: fake document, hub, Lumino, app with `notebooks` panels (each with a kernel), a
 * window `width` px wide, a probe on `praxis_viz3d`, and dock.js mounted on it.
 */
function makeEnv({
  mod = realDock,
  width = 1440,
  notebooks = 1,
  pad = 8,
  sidebar = 0,
  decoy = false,
  mountIt = true,
  broadcast = true,
  options = {},
} = {}) {
  const doc = createFakeDocument();
  doc.attrLog = [];
  doc.appendLog = [];
  const hub = createFakeBroadcastHub();
  const lumino = createFakeLumino(doc, { decoy });
  const app = createFakeDeckApp({ doc, notebooks, width: width - sidebar, lumino });
  for (const panel of app.panels) panel.content.node._padding = pad;
  const win = createFakeWindow({ app, document: doc, broadcast: broadcast ? hub : null, innerWidth: width });
  const logger = recordingLogger();

  const heard = [];
  const probe = new hub.BroadcastChannel("praxis_viz3d");
  probe.addEventListener("message", (event) => {
    try {
      heard.push(JSON.parse(event.data));
    } catch {
      heard.push({ kind: "<unparseable>", raw: event.data });
    }
  });

  const plrNames = [];
  const allFrames = [];
  const plrOf = new Map();
  doc.onCreate = (el) => {
    if (el.localName !== "iframe") return;
    allFrames.push(el);
    el.contentWindow = {
      get plrViewer() {
        if (env.plrReady === false) return undefined;
        if (!plrOf.has(el)) plrOf.set(el, createFakePlrViewer({ names: plrNames }));
        return plrOf.get(el);
      },
    };
  };

  const env = {
    doc,
    hub,
    lumino,
    app,
    win,
    logger,
    heard,
    probe,
    plrNames,
    plrReady: true,
    allFrames,
    plrOf,
    sidebar,
    ctl: null,
    panels: app.panels,
    dock: app.dock,
    width,
    /** The kernel (or a page) posts on praxis_viz3d; the probe does not hear it. */
    post(message) {
      hub.post("praxis_viz3d", typeof message === "string" ? message : JSON.stringify(message), { except: [probe] });
    },
    announce: (viewer, deck = "PlateDeck") =>
      env.post({ kind: "announce", viewer, deck, session: "sess1" }),
    kernelClose: (viewer, reason = "stop") => env.post({ kind: "close", viewer, reason }),
    /** The iframe's embed.js forwards plr:gone / plr:status to its parent window (C4). */
    gone: (viewer) => win.dispatchEvent({ type: "praxis:dock-status", detail: { event: "plr:gone", viewer } }),
    status: (viewer, connected) =>
      win.dispatchEvent({ type: "praxis:dock-status", detail: { event: "plr:status", connected, viewer } }),
    /** praxis:toggle-deck-panel, executed like the command palette does. */
    toggle: () => app.commands.execute(TOGGLE),
    resize(w) {
      env.width = w;
      win.innerWidth = w;
      app.dock.setWidth(w - env.sidebar);
      win.dispatchEvent({ type: "resize" });
      win.resizeObservers.trigger();
    },
    /** The file browser opens (px > 0) or closes: the main area changes width, the window does not. */
    setSidebar(px) {
      env.sidebar = px;
      app.dock.setWidth(env.width - px);
      win.resizeObservers.trigger();
    },
    deckWidget() {
      const found = lumino.instances.filter((w) => w.node.classList.contains("praxis-deck-panel"));
      return found.length ? found[found.length - 1] : null;
    },
    node() {
      const w = env.deckWidget();
      return w ? w.node : null;
    },
    frames() {
      const out = [];
      const node = env.node();
      if (node) walk(node, (el) => (el.localName === "iframe" ? out.push(el) : undefined));
      return out;
    },
    attached() {
      const node = env.node();
      if (!node) return false;
      let top = node;
      while (top.parentNode) top = top.parentNode;
      return top === doc;
    },
    inDock() {
      const w = env.deckWidget();
      return Boolean(w) && Array.from(app.dock.allWidgets()).includes(w);
    },
    inBody() {
      const node = env.node();
      return Boolean(node) && node.parentNode === doc.body;
    },
    domState() {
      const node = env.node();
      return node ? node.getAttribute("data-praxis-deck-state") : "closed";
    },
    text: () => (env.node() ? env.node().textContent : ""),
    find: (cls) => (env.node() ? env.node().querySelector(cls) : null),
    viewButton(label) {
      const views = env.find(".praxis-deck-panel__views");
      return views ? views.children.find((b) => b.textContent === label) : null;
    },
    click: (el) => el.dispatch("click", {}),
    escape() {
      const target = env.find(".praxis-deck-panel__header") || env.node();
      target.dispatch("keydown", { key: "Escape" });
    },
    srcWrites: () => doc.attrLog.filter((a) => a.tag === "iframe" && a.name === "src").map((a) => a.value),
    queries: () => heard.filter((m) => m.kind === "query").length,
    plrActions() {
      const out = [];
      for (const frame of allFrames) {
        const viewer = plrOf.get(frame);
        if (viewer) for (const call of viewer.actions) out.push({ viewer: viewerOf(frame), call });
      }
      return out;
    },
    /** A cell of `panel` starts executing (its model's executionState is `running`). */
    startCell(panel) {
      const cell = createFakeCell({ source: "dock(deck)" });
      panel.addCell(cell);
      cell.model.startExecution();
      return cell;
    },
    mark: () => ({ src: env.srcWrites().length, q: env.queries(), frames: allFrames.length }),
    since: (m) => ({
      srcWrites: env.srcWrites().length - m.src,
      queries: env.queries() - m.q,
      framesCreated: allFrames.length - m.frames,
    }),
    remount(overrides = {}) {
      env.ctl = mod.mountDock({ app, win, logger, controllers: {}, baseUrl: BASE, ...options, ...overrides });
      return env.ctl;
    },
  };
  if (mountIt) env.remount();
  return env;
}

/** I1, I5 and attachment, read from the DOM after a transition (never from a held element). */
function assertInvariants(env, { state, current = null }) {
  expect(env.ctl.state()).toBe(state);
  expect(env.domState()).toBe(state);
  expect(env.attached()).toBe(state !== "closed");
  const frames = env.frames();
  // I1: an iframe iff open-connected, then exactly one, whose src carries viewer=<current>.
  expect(frames.length).toBe(state === "open-connected" ? 1 : 0);
  if (state === "open-connected") {
    expect(viewerOf(frames[0])).toBe(current);
    expect(new URL(frames[0].getAttribute("src")).searchParams.get("embed")).toBe("1");
    expect(new URL(frames[0].getAttribute("src")).searchParams.get("view")).toBe("top");
  }
  // I5: the no-viewer text iff open-waiting, the lost-connection text iff open-lost.
  const text = env.text();
  expect(text.includes(NO_VIEWER)).toBe(state === "open-waiting");
  expect(text.includes(LOST)).toBe(state === "open-lost");
  expect(env.ctl.snapshot().current).toBe(state === "open-connected" || state === "open-lost" ? current : null);
  // A panel that works logs no error (an error swallowed by a guard would show here).
  expect(env.logger.errors).toEqual([]);
  // The shell posts `query` and nothing else on praxis_viz3d.
  expect(env.heard.every((m) => m.kind === "query")).toBe(true);
}

/** The panel's home in its tier: split (in the main DockPanel) at >= 1280 px, else the drawer (body). */
function assertHome(env, home) {
  expect(env.attached()).toBe(true);
  if (home === "split") {
    expect(env.inDock()).toBe(true);
    expect(env.inBody()).toBe(false);
  } else {
    expect(env.inDock()).toBe(false);
    expect(env.inBody()).toBe(true);
  }
}

// -- pure helpers --------------------------------------------------------------------------------------------------------

describe("tiers and the >= 1600 width formula (D6)", () => {
  test("tierOf: the boundaries are 1024, 1280 and 1600", () => {
    expect(realDock.tierOf(1023)).toBe("drawer"); // out of scope: the drawer is the only tier that never reflows
    expect(realDock.tierOf(1024)).toBe("drawer");
    expect(realDock.tierOf(1279)).toBe("drawer");
    expect(realDock.tierOf(1280)).toBe("medium");
    expect(realDock.tierOf(1599)).toBe("medium");
    expect(realDock.tierOf(1600)).toBe("wide");
    expect(realDock.tierOf(1920)).toBe("wide");
  });

  test("panelWidth = max(420, main - 960 - padding)", () => {
    expect(realDock.panelWidth(1600, 16)).toBe(624);
    expect(realDock.panelWidth(1920, 16)).toBe(944);
    expect(realDock.panelWidth(1920, 0)).toBe(960);
    expect(realDock.panelWidth(1300, 16)).toBe(420); // 324 -> the 420 floor
    expect(realDock.panelWidth(1376, 16)).toBe(420); // exactly the floor
    expect(realDock.panelWidth(1400, 16)).toBe(424);
  });

  test("the sizing case in force is one exported constant (C7 asserts it)", () => {
    expect(realDock.SIZING.case).toBe("honoured_reachable");
    expect(realDock.SIZING.cssLimitsHonoured).toBe(true);
    expect(realDock.SIZING.layoutSizingReachable).toBe(true);
    expect(realDock.SIZING.cssLimitsRefit).toBe(true);
    expect(realDock.SIZING.restoreLayoutKeepsIframe).toBe(true);
    expect(Object.isFrozen(realDock.SIZING)).toBe(true);
    const env = makeEnv();
    expect(env.ctl.sizing).toBe(realDock.SIZING);
  });

  test("viewerSrc builds assets/visualizer3d/index.html?embed=1&view=top&viewer=<id>, encoded", () => {
    expect(realDock.viewerSrc(BASE, "v1")).toBe(`${BASE}assets/visualizer3d/index.html?embed=1&view=top&viewer=v1`);
    const u = new URL(realDock.viewerSrc(BASE, "a b&c=d"));
    expect(u.searchParams.get("viewer")).toBe("a b&c=d");
    expect(u.searchParams.get("embed")).toBe("1");
    expect(u.searchParams.get("view")).toBe("top");
  });
});

// -- S1-A: the widget --------------------------------------------------------------------------------------------------

describe("the widget (S1-A: the root Lumino Widget found by walking a shell widget's prototype chain)", () => {
  test("it is built from the structural root, not from a middle class that also owns the methods", () => {
    const env = makeEnv({ decoy: true });
    env.announce("v1");
    const widget = env.deckWidget();
    expect(widget).not.toBeNull();
    expect(widget instanceof env.lumino.Widget).toBe(true);
    // The root is the class whose prototype owns processMessage AND onAfterAttach and whose own
    // prototype is Object.prototype: never Level1, which owns both but sits above the root's subclass.
    let proto = Object.getPrototypeOf(widget);
    while (Object.getPrototypeOf(proto) !== env.lumino.Widget.prototype) proto = Object.getPrototypeOf(proto);
    expect(Object.getPrototypeOf(proto)).toBe(env.lumino.Widget.prototype);
    expect(widget instanceof env.lumino.Level1).toBe(false);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("it is constructed with {node}, given an id, a title, and added split-right of the current notebook", () => {
    const env = makeEnv({ notebooks: 2 });
    env.announce("v1");
    const [call] = env.app.shell.addCalls;
    expect(call.area).toBe("main");
    expect(call.options.mode).toBe("split-right");
    expect(call.options.ref).toBe("nb1"); // shell.currentWidget
    expect(call.options.activate).toBe(false); // the notebook keeps the keyboard
    const widget = call.widget;
    expect(typeof widget.id).toBe("string");
    expect(widget.id.length).toBeGreaterThan(0);
    expect(widget.title.label).toBe("Deck");
    expect(widget.title.closable).toBe(true);
    expect(widget.node.classList.contains("praxis-deck-panel")).toBe(true);
    // The notebook shrinks to make room: it is a split, notebook left, deck right.
    const layout = env.app.dock.saveLayout().main;
    expect(layout.type).toBe("split-area");
    expect(layout.children[1].widgets).toEqual([widget]);
  });

  test("the ref is the current notebook, whichever it is", () => {
    const env = makeEnv({ notebooks: 2 });
    env.app.shell.currentWidget = env.panels[1];
    env.announce("v1");
    expect(env.app.shell.addCalls[0].options.ref).toBe("nb2");
  });

  test("with no root class reachable the panel stays closed, the failure is logged and nothing throws", () => {
    const env = makeEnv();
    // A shell whose widgets are plain objects: no chain reaches a root.
    env.app.shell.currentWidget = null;
    env.app.shell.widgets = function* widgets() {
      yield { id: "plain", node: env.doc.createElement("div") };
    };
    expect(() => env.announce("v1")).not.toThrow();
    expect(env.ctl.state()).toBe("closed");
    expect(env.app.shell.addCalls).toEqual([]);
    expect(env.logger.errors.length).toBeGreaterThan(0);
    expect(env.logger.errors[0].join(" ")).toContain("Widget");
  });

  test("shell.add throwing is contained: closed, logged, and a later toggle can still open it", () => {
    const env = makeEnv();
    const realAdd = env.app.shell.add;
    env.app.shell.add = () => {
      throw new Error("shell.add blew up");
    };
    expect(() => env.announce("v1")).not.toThrow();
    expect(env.ctl.state()).toBe("closed");
    expect(env.frames().length).toBe(0);
    expect(env.logger.errors.length).toBeGreaterThan(0);
    env.app.shell.add = realAdd;
    env.toggle();
    expect(env.ctl.state()).toBe("open-waiting");
  });
});

// -- the header, footer and motion slot (D12, section 3.6) -----------------------------------------------------------

describe("the panel's chrome (header, footer, motion slot)", () => {
  test("header: the deck name, a Follow switch (on), Iso / Top / Front (Top pressed); the A4 class names and ARIA", () => {
    const env = makeEnv();
    env.announce("v1", "PlateDeck");
    const header = env.find(".praxis-deck-panel__header");
    expect(header).not.toBeNull();
    expect(env.find(".praxis-deck-panel__title").textContent).toBe("PlateDeck");
    const follow = env.find(".praxis-deck-panel__follow");
    expect(follow.getAttribute("role")).toBe("switch");
    expect(follow.getAttribute("aria-checked")).toBe("true");
    const views = env.find(".praxis-deck-panel__views");
    expect(views.children.map((b) => b.textContent)).toEqual(["Iso", "Top", "Front"]);
    expect(views.children.map((b) => b.getAttribute("aria-pressed"))).toEqual(["false", "true", "false"]);
    expect(env.node().classList.contains("praxis-deck-panel")).toBe(true);
  });

  test("the deck name is data: it goes in as text, never markup", () => {
    const env = makeEnv();
    env.announce("v1", "<img src=x onerror=alert(1)>");
    expect(env.find(".praxis-deck-panel__title").textContent).toBe("<img src=x onerror=alert(1)>");
    expect(env.find(".praxis-deck-panel__title").children.length).toBe(0);
  });

  test("footer: the focused resource, then the one-row motion slot with its fixed text", () => {
    const env = makeEnv();
    env.announce("v1");
    const footer = env.find(".praxis-deck-panel__footer");
    expect(footer).not.toBeNull();
    const motion = env.find(".praxis-deck-panel__motion");
    expect(motion.textContent).toBe(MOTION);
    expect(motion.getAttribute("aria-disabled")).toBe("true");
    expect(footer.contains(motion)).toBe(true);
    // The motion slot is at most one row: the height rule needs it to collapse first.
    expect(motion.style.maxHeight).toBe("36px");
  });

  test("the body keeps the iframe at least 300 px tall (D6 height rule)", () => {
    const env = makeEnv();
    env.announce("v1");
    const body = env.find(".praxis-deck-panel__body");
    expect(body.style.minHeight).toBe("300px");
    expect(env.frames()[0].style.minHeight).toBe("300px");
  });

  test("the placeholder texts are the section 3.6 strings, verbatim", () => {
    const env = makeEnv();
    env.toggle();
    expect(env.find(".praxis-deck-panel__body").textContent).toBe(NO_VIEWER);
    env.announce("v1");
    env.gone("v1");
    expect(env.find(".praxis-deck-panel__body").textContent).toBe(LOST);
  });
});

// -- the state table: one test per row ---------------------------------------------------------------------------------

describe("D11 deck-panel state table, one test per row (T1-T27)", () => {
  // -- T1 ---------------------------------------------------------------------------------------------------------------
  test("T1 (none) + mount -> closed: seen false, current none, one query posted, nothing attached", () => {
    const env = makeEnv();
    expect(env.ctl.snapshot()).toMatchObject({ state: "closed", seen: false, current: null });
    expect(env.queries()).toBe(1);
    expect(env.app.shell.addCalls).toEqual([]);
    expect(env.deckWidget()).toBeNull();
    assertInvariants(env, { state: "closed" });
  });

  // -- closed -----------------------------------------------------------------------------------------------------------
  test("T2 closed + announce (first) -> open-connected: attach in the tier's home, ONE iframe, src carries viewer=<id>", () => {
    const env = makeEnv();
    const m = env.mark();
    env.announce("v1", "PlateDeck");
    expect(env.ctl.snapshot()).toMatchObject({ state: "open-connected", seen: true, current: "v1" });
    expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 1 });
    assertHome(env, "split");
    const [frame] = env.frames();
    const url = new URL(frame.getAttribute("src"));
    expect(url.pathname.endsWith("/assets/visualizer3d/index.html")).toBe(true);
    // The src was already on the iframe when it entered the DOM (a page loaded without an id is never created).
    expect(env.doc.appendLog.find((e) => e.child === frame).srcAtInsert).toContain("viewer=v1");
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("T3 closed + announce (not first) -> closed: ignored, no iframe is created", () => {
    const env = makeEnv();
    env.announce("v1"); // T2
    env.toggle(); // T17 -> closed
    expect(env.ctl.state()).toBe("closed");
    const m = env.mark();
    const adds = env.app.shell.addCalls.length;
    env.announce("v2");
    expect(env.ctl.snapshot()).toMatchObject({ state: "closed", seen: true, current: null });
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    expect(env.app.shell.addCalls.length).toBe(adds);
    assertInvariants(env, { state: "closed" });
  });

  test("T3 still records viewerPanel: the announce is remembered for the kernel-restart event", () => {
    const env = makeEnv({ notebooks: 2 });
    env.announce("v1"); // T2
    env.toggle(); // closed
    const cell = env.startCell(env.panels[0]); // exactly one panel (nb1) has a cell executing
    env.announce("v2"); // T3, ignored, but viewerPanel[v2] = nb1
    cell.model.finishExecution({ count: 1 }); // nothing executes by the time of the T6 announce below
    env.toggle(); // T4
    env.announce("v2"); // T6
    expect(env.ctl.state()).toBe("open-connected");
    env.panels[0].kernelStatus("restarting"); // two panels have kernels: only viewerPanel can name nb1
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T4 closed + reopen -> open-waiting: attach with NO iframe, the no-viewer text, ONE query", () => {
    const env = makeEnv();
    const m = env.mark();
    env.toggle();
    expect(env.ctl.snapshot()).toMatchObject({ state: "open-waiting", seen: false, current: null });
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 1, framesCreated: 0 });
    assertHome(env, "split");
    assertInvariants(env, { state: "open-waiting" });
  });

  describe("T5 closed + {kernel close (any), plr:gone, tier crossing, close panel} -> closed, no action", () => {
    function closedEnv() {
      const env = makeEnv();
      env.announce("v1");
      env.toggle(); // closed, seen = true
      return env;
    }
    function expectQuiet(env, m, adds) {
      expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
      expect(env.app.shell.addCalls.length).toBe(adds);
      assertInvariants(env, { state: "closed" });
    }

    test("kernel close", () => {
      const env = closedEnv();
      const m = env.mark();
      const adds = env.app.shell.addCalls.length;
      env.kernelClose("v1");
      env.kernelClose("other");
      expectQuiet(env, m, adds);
    });

    test("plr:gone", () => {
      const env = closedEnv();
      const m = env.mark();
      const adds = env.app.shell.addCalls.length;
      env.gone("v1");
      expectQuiet(env, m, adds);
    });

    test("tier crossing, both ways (a closed panel stays closed and is not attached)", () => {
      const env = closedEnv();
      const m = env.mark();
      const adds = env.app.shell.addCalls.length;
      env.resize(1152);
      expect(env.ctl.state()).toBe("closed");
      env.resize(1440);
      expectQuiet(env, m, adds);
    });

    test("close panel (a late tab-close request and Escape on the detached panel)", () => {
      const env = closedEnv();
      const m = env.mark();
      const adds = env.app.shell.addCalls.length;
      expect(() => env.deckWidget().close()).not.toThrow();
      env.escape();
      expectQuiet(env, m, adds);
    });

    test("T5 from a page that never opened the panel", () => {
      const env = makeEnv();
      env.kernelClose("v1");
      env.gone("v1");
      env.resize(1152);
      env.resize(1440);
      expect(env.ctl.state()).toBe("closed");
      expect(env.deckWidget()).toBeNull();
      expect(env.queries()).toBe(1); // the mount's, no other
    });
  });

  test("T23 closed + kernel restart -> closed, no action", () => {
    const env = makeEnv();
    env.announce("v1");
    env.toggle(); // closed
    const m = env.mark();
    env.panels[0].kernelStatus("restarting");
    env.panels[0].setKernel(null);
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "closed" });
  });

  // -- open-waiting -------------------------------------------------------------------------------------------------------
  describe("T6 open-waiting + announce (first or not; including the answer to a query) -> open-connected", () => {
    test("first: a reopen before any announce, then the answering announce", () => {
      const env = makeEnv();
      env.toggle(); // T4, seen false
      const m = env.mark();
      env.announce("v1");
      expect(env.ctl.snapshot()).toMatchObject({ state: "open-connected", seen: true, current: "v1" });
      expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 1 });
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("not first: the text is hidden and a NEW iframe is created (a removed element is never reused)", () => {
      const env = makeEnv();
      env.announce("v1");
      const removed = env.frames()[0];
      env.kernelClose("v1"); // T12 -> open-waiting
      assertInvariants(env, { state: "open-waiting" });
      const m = env.mark();
      env.announce("v2");
      const [frame] = env.frames();
      expect(frame).not.toBe(removed);
      expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 1 });
      assertInvariants(env, { state: "open-connected", current: "v2" });
    });

    test("an iframe-less open panel gets its iframe from the announce, already carrying the src", () => {
      const env = makeEnv();
      env.toggle();
      expect(env.frames().length).toBe(0);
      env.announce("v9");
      const [frame] = env.frames();
      expect(env.doc.appendLog.find((e) => e.child === frame).srcAtInsert).toContain("viewer=v9");
    });
  });

  describe("T7 open-waiting + close panel -> closed: detach, current none", () => {
    test("praxis:toggle-deck-panel while open", () => {
      const env = makeEnv();
      env.toggle();
      env.toggle();
      assertInvariants(env, { state: "closed" });
    });

    test("the split tab closed", () => {
      const env = makeEnv();
      env.toggle();
      env.deckWidget().close();
      assertInvariants(env, { state: "closed" });
      expect(env.inDock()).toBe(false);
    });

    test("the drawer's close button, and Escape in the drawer", () => {
      const env = makeEnv({ width: 1152 });
      env.toggle();
      assertHome(env, "drawer");
      env.click(env.find(".praxis-deck-panel__close"));
      assertInvariants(env, { state: "closed" });
      env.toggle();
      env.escape();
      assertInvariants(env, { state: "closed" });
    });
  });

  test("T8 open-waiting + kernel close (any) -> open-waiting, no action", () => {
    const env = makeEnv();
    env.toggle();
    const m = env.mark();
    env.kernelClose("v1");
    env.kernelClose("v2", "error");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T24 open-waiting + kernel restart -> open-waiting, no action", () => {
    const env = makeEnv();
    env.toggle();
    const m = env.mark();
    env.panels[0].kernelStatus("restarting");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T9 open-waiting + plr:gone -> open-waiting: ignored (C5-2), the lost text never shows", () => {
    const env = makeEnv();
    env.toggle();
    env.gone("v1");
    env.gone(null);
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T10 open-waiting + tier crossing -> open-waiting: re-home the panel, NO query re-sent", () => {
    const env = makeEnv();
    env.toggle();
    const m = env.mark();
    env.resize(1152);
    assertHome(env, "drawer");
    assertInvariants(env, { state: "open-waiting" });
    env.resize(1440);
    assertHome(env, "split");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
    // An outstanding answer still lands through T6 after the move.
    env.announce("v1");
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  // -- open-connected -----------------------------------------------------------------------------------------------------
  test("T11 open-connected + announce (id != current) -> the iframe in the panel gets the new src; current = id", () => {
    const env = makeEnv();
    env.announce("v1");
    const frame = env.frames()[0];
    const m = env.mark();
    env.announce("v2", "OtherDeck");
    expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 0 });
    expect(env.frames()).toEqual([frame]); // the same element: its src is rewritten (the page reloads)
    expect(env.find(".praxis-deck-panel__title").textContent).toBe("OtherDeck");
    assertInvariants(env, { state: "open-connected", current: "v2" });
  });

  test("T11 recreates the iframe when the panel has none (the announce never leaves a viewer-less iframe-less panel)", () => {
    const env = makeEnv();
    env.announce("v1");
    env.frames()[0].remove(); // something outside removed it
    expect(env.frames().length).toBe(0);
    env.announce("v2");
    assertInvariants(env, { state: "open-connected", current: "v2" });
  });

  test("T27 open-connected + announce (id = current) -> no src write, no iframe, no reload", () => {
    const env = makeEnv();
    env.announce("v1");
    const frame = env.frames()[0];
    const m = env.mark();
    env.announce("v1"); // for example another page's query, answered by the same viewer
    env.announce("v1");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    expect(env.frames()).toEqual([frame]);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("T12 open-connected + kernel close (current) -> open-waiting: iframe removed, no-viewer text, current none", () => {
    const env = makeEnv();
    env.announce("v1");
    const m = env.mark();
    env.kernelClose("v1");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T25 open-connected + kernel restart -> open-waiting as T12, and no `close` is needed or posted", () => {
    const env = makeEnv();
    env.startCell(env.panels[0]);
    env.announce("v1");
    const m = env.mark();
    env.panels[0].kernelStatus("restarting");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
    expect(env.heard.filter((x) => x.kind === "close")).toEqual([]);
  });

  test("T13 open-connected + kernel close (not current) -> open-connected, no action", () => {
    const env = makeEnv();
    env.announce("v1");
    const frame = env.frames()[0];
    env.kernelClose("v0");
    env.kernelClose("v2");
    expect(env.frames()).toEqual([frame]);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("T14 open-connected + plr:gone -> open-lost: iframe removed, the lost text, current KEPT", () => {
    const env = makeEnv();
    env.announce("v1");
    const m = env.mark();
    env.gone("v1");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-lost", current: "v1" });
    // current is kept: a kernel close for it is "current" (T19).
    env.kernelClose("v1");
    assertInvariants(env, { state: "open-waiting" });
  });

  describe("T15 open-connected + tier crossing -> open-connected: re-home WITH the iframe, no src write, no query", () => {
    test("down (split -> drawer) and up (drawer -> split), the same iframe element", () => {
      const env = makeEnv();
      env.announce("v1");
      const frame = env.frames()[0];
      const m = env.mark();
      env.resize(1152);
      assertHome(env, "drawer");
      expect(env.frames()).toEqual([frame]);
      assertInvariants(env, { state: "open-connected", current: "v1" });
      env.resize(1440);
      assertHome(env, "split");
      expect(env.frames()).toEqual([frame]);
      expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("the crossing points are exactly 1280 (up) and 1279 (down)", () => {
      const env = makeEnv({ width: 1279 });
      env.announce("v1");
      assertHome(env, "drawer");
      env.resize(1280);
      assertHome(env, "split");
      env.resize(1279);
      assertHome(env, "drawer");
    });
  });

  test("T16 open-connected + iframe reload -> open-connected: no lifecycle action, no src write, no query", () => {
    const env = makeEnv();
    env.announce("v1");
    const m = env.mark();
    env.frames()[0].dispatch("load", {});
    env.frames()[0].dispatch("load", {});
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  describe("T17 open-connected + close panel -> closed: iframe removed, detach, current none", () => {
    test("praxis:toggle-deck-panel while open", () => {
      const env = makeEnv();
      env.announce("v1");
      env.toggle();
      assertInvariants(env, { state: "closed" });
      expect(env.inDock()).toBe(false);
    });

    test("the split tab closed", () => {
      const env = makeEnv();
      env.announce("v1");
      env.deckWidget().close();
      assertInvariants(env, { state: "closed" });
    });

    test("the drawer's close button", () => {
      const env = makeEnv({ width: 1152 });
      env.announce("v1");
      env.click(env.find(".praxis-deck-panel__close"));
      assertInvariants(env, { state: "closed" });
    });

    test("Escape while focus is in the drawer", () => {
      const env = makeEnv({ width: 1152 });
      env.announce("v1");
      env.escape();
      assertInvariants(env, { state: "closed" });
    });
  });

  // -- open-lost ------------------------------------------------------------------------------------------------------------
  test("T18 open-lost + announce -> open-connected: text hidden, ONE NEW iframe carrying the new src", () => {
    const env = makeEnv();
    env.announce("v1");
    const first = env.frames()[0];
    env.gone("v1");
    const m = env.mark();
    env.announce("v2");
    expect(env.frames()[0]).not.toBe(first);
    expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 1 });
    assertInvariants(env, { state: "open-connected", current: "v2" });
  });

  test("T19 open-lost + kernel close (current) -> open-waiting: the no-viewer text instead of the lost text", () => {
    const env = makeEnv();
    env.announce("v1");
    env.gone("v1");
    env.kernelClose("v1");
    assertInvariants(env, { state: "open-waiting" });
  });

  test("T26 open-lost + kernel restart -> open-waiting as T19", () => {
    const env = makeEnv();
    env.startCell(env.panels[0]);
    env.announce("v1");
    env.gone("v1");
    env.panels[0].kernelStatus("dead");
    assertInvariants(env, { state: "open-waiting" });
  });

  describe("T20 open-lost + {kernel close (not current), plr:gone} -> open-lost, no action", () => {
    test("kernel close for another viewer", () => {
      const env = makeEnv();
      env.announce("v1");
      env.gone("v1");
      const m = env.mark();
      env.kernelClose("v2");
      expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
      assertInvariants(env, { state: "open-lost", current: "v1" });
    });

    test("another plr:gone", () => {
      const env = makeEnv();
      env.announce("v1");
      env.gone("v1");
      env.gone("v1");
      assertInvariants(env, { state: "open-lost", current: "v1" });
    });
  });

  test("T21 open-lost + tier crossing -> open-lost: re-home the panel, the lost text stays", () => {
    const env = makeEnv();
    env.announce("v1");
    env.gone("v1");
    env.resize(1152);
    assertHome(env, "drawer");
    assertInvariants(env, { state: "open-lost", current: "v1" });
    env.resize(1440);
    assertHome(env, "split");
    assertInvariants(env, { state: "open-lost", current: "v1" });
  });

  describe("T22 open-lost + close panel -> closed: detach, current none", () => {
    test("toggle", () => {
      const env = makeEnv();
      env.announce("v1");
      env.gone("v1");
      env.toggle();
      assertInvariants(env, { state: "closed" });
    });

    test("the split tab closed", () => {
      const env = makeEnv();
      env.announce("v1");
      env.gone("v1");
      env.deckWidget().close();
      assertInvariants(env, { state: "closed" });
    });

    test("the drawer's close button and Escape", () => {
      const env = makeEnv({ width: 1152 });
      env.announce("v1");
      env.gone("v1");
      env.click(env.find(".praxis-deck-panel__close"));
      assertInvariants(env, { state: "closed" });
      env.toggle();
      env.announce("v2");
      env.gone("v2");
      env.escape();
      assertInvariants(env, { state: "closed" });
    });
  });
});

// -- sequences on top of the rows ---------------------------------------------------------------------------------------

describe("sequences the spec names", () => {
  test("C6-1 re-dock: v1 connected, kernel close(v1), announce(v2) -> one NEW iframe with viewer=v2; a later plr:gone is honoured", () => {
    const env = makeEnv();
    env.announce("v1");
    const removed = env.frames()[0];
    env.kernelClose("v1");
    assertInvariants(env, { state: "open-waiting" });
    env.announce("v2");
    const frames = env.frames();
    expect(frames.length).toBe(1);
    expect(frames[0]).not.toBe(removed);
    expect(viewerOf(frames[0])).toBe("v2");
    expect(env.srcWrites().map((s) => new URL(s).searchParams.get("viewer"))).toEqual(["v1", "v2"]);
    assertInvariants(env, { state: "open-connected", current: "v2" });
    env.gone("v2");
    assertInvariants(env, { state: "open-lost", current: "v2" });
  });

  test("C5-2: kernel close(current), then plr:gone -> the no-viewer text stays", () => {
    const env = makeEnv();
    env.announce("v1");
    env.kernelClose("v1");
    env.gone("v1");
    assertInvariants(env, { state: "open-waiting" });
    expect(env.text().includes("lost its connection")).toBe(false);
  });

  test("Reopen: closed -> reopen shows no iframe and posts ONE query; the answering announce creates the only iframe, already carrying its src", () => {
    const env = makeEnv();
    env.announce("v1");
    env.toggle(); // closed
    assertInvariants(env, { state: "closed" });
    const m = env.mark();
    env.toggle(); // T4
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 1, framesCreated: 0 });
    assertInvariants(env, { state: "open-waiting" });
    // the live viewer answers the query with an announce
    env.announce("v1");
    const frames = env.frames();
    expect(frames.length).toBe(1);
    expect(env.doc.appendLog.filter((e) => e.child === frames[0])[0].srcAtInsert).toContain("viewer=v1");
    expect(env.since(m)).toEqual({ srcWrites: 1, queries: 1, framesCreated: 1 });
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  describe("C7-6 kernel restart, observed on the viewer's kernel's sessionContext", () => {
    const triggers = [
      ["statusChanged: restarting", (p) => p.kernelStatus("restarting")],
      ["statusChanged: autorestarting", (p) => p.kernelStatus("autorestarting")],
      ["statusChanged: dead", (p) => p.kernelStatus("dead")],
      ["kernelChanged to no kernel", (p) => p.setKernel(null)],
      ["kernelChanged to another kernel", (p) => p.setKernel({ id: "k-new" })],
    ];
    for (const [label, trigger] of triggers) {
      test(`${label}: open-connected -> open-waiting, no iframe, the no-viewer text, no query posted`, () => {
        const env = makeEnv({ notebooks: 2 });
        env.startCell(env.panels[0]); // viewerPanel[v1] = P
        env.announce("v1");
        expect(env.ctl.state()).toBe("open-connected");
        const m = env.mark();
        trigger(env.panels[0]);
        expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
        assertInvariants(env, { state: "open-waiting" });
      });
    }

    test("a restart of another panel Q leaves open-connected unchanged", () => {
      const env = makeEnv({ notebooks: 2 });
      env.startCell(env.panels[0]);
      env.announce("v1");
      const frame = env.frames()[0];
      env.panels[1].kernelStatus("restarting");
      env.panels[1].kernelStatus("dead");
      env.panels[1].setKernel(null);
      expect(env.frames()).toEqual([frame]);
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("statuses that are not a restart (idle, busy) do nothing", () => {
      const env = makeEnv();
      env.startCell(env.panels[0]);
      env.announce("v1");
      env.panels[0].kernelStatus("idle");
      env.panels[0].kernelStatus("busy");
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("from open-lost, P's restart -> open-waiting with the no-viewer text (T26)", () => {
      const env = makeEnv({ notebooks: 2 });
      env.startCell(env.panels[0]);
      env.announce("v1");
      env.gone("v1");
      env.panels[0].kernelStatus("restarting");
      assertInvariants(env, { state: "open-waiting" });
    });

    test("with no viewerPanel entry and two panels with kernels, a restart changes nothing (the stated gap)", () => {
      const env = makeEnv({ notebooks: 2 });
      env.announce("v1"); // nothing executing: no entry
      env.panels[0].kernelStatus("restarting");
      env.panels[1].kernelStatus("restarting");
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("with no viewerPanel entry and exactly one panel with a kernel, it fires", () => {
      const env = makeEnv({ notebooks: 2 });
      env.panels[1].setKernel(null); // Q has no kernel
      env.announce("v1");
      env.panels[0].kernelStatus("restarting");
      assertInvariants(env, { state: "open-waiting" });
    });

    test("with one panel and no entry, the kernel going away (dead, or kernelChanged to none) fires", () => {
      for (const trigger of [(p) => p.kernelStatus("dead"), (p) => p.setKernel(null)]) {
        const env = makeEnv();
        env.announce("v1");
        trigger(env.panels[0]);
        assertInvariants(env, { state: "open-waiting" });
      }
    });

    test("after a restart the panel is usable again: the next announce reconnects", () => {
      const env = makeEnv();
      env.startCell(env.panels[0]);
      env.announce("v1");
      env.panels[0].kernelStatus("restarting");
      env.announce("v2");
      assertInvariants(env, { state: "open-connected", current: "v2" });
      env.gone("v2"); // and plr:gone is honoured again (I4)
      assertInvariants(env, { state: "open-lost", current: "v2" });
    });

    test("a cell that is executing in two panels names no panel (exactly one is required)", () => {
      const env = makeEnv({ notebooks: 2 });
      env.startCell(env.panels[0]);
      env.startCell(env.panels[1]);
      env.announce("v1");
      env.panels[0].kernelStatus("restarting"); // no entry, two kernels: the gap
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });
  });

  test("C7-9 same id: announce(v1) writes no src and creates no iframe (T27); announce(v2) then writes viewer=v2 (T11)", () => {
    const env = makeEnv();
    env.announce("v1");
    const frame = env.frames()[0];
    const m = env.mark();
    env.announce("v1");
    expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
    env.announce("v2");
    expect(env.since(m)).toEqual({ srcWrites: 1, queries: 0, framesCreated: 0 });
    expect(env.frames()).toEqual([frame]);
    expect(viewerOf(env.frames()[0])).toBe("v2");
  });

  test("C7-9: a tier crossing's DOM move is T15 only: one reload re-applies the preset once, never twice", () => {
    const env = makeEnv();
    env.plrNames.push("assay");
    env.announce("v1");
    env.frames()[0].dispatch("load", {}); // the first load: one view("top")
    const before = env.plrActions().length;
    env.resize(1152); // the move reloads the iframe once
    env.frames()[0].dispatch("load", {});
    env.win.tick();
    env.win.tick();
    expect(env.plrActions().length - before).toBe(1);
    expect(env.plrActions().at(-1).call).toEqual(["view", "top"]);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });
});

// -- the held preset and the page's plrViewer (D12) ----------------------------------------------------------

describe("the held preset (D12, C7-7)", () => {
  const loadFrame = (env) => env.frames()[0].dispatch("load", {});

  test("C7-7: a load with the preset front calls no view() while resources() is empty; once non-empty, exactly one view('front')", () => {
    const env = makeEnv();
    env.toggle(); // open-waiting: no iframe yet
    env.click(env.viewButton("Front"));
    env.announce("v1");
    loadFrame(env);
    for (let i = 0; i < 6; i += 1) env.win.tick();
    expect(env.plrActions()).toEqual([]);
    env.plrNames.push("assay");
    env.win.tick();
    expect(env.plrActions()).toEqual([{ viewer: "v1", call: ["view", "front"] }]);
    for (let i = 0; i < 6; i += 1) env.win.tick();
    expect(env.plrActions().length).toBe(1); // exactly one
    expect(env.win.pendingTimers).toBe(0);
  });

  test("the poll runs every 250 ms and gives up after 10 s", () => {
    const env = makeEnv();
    env.announce("v1");
    loadFrame(env);
    expect(env.win.intervalDelays).toContain(250);
    for (let i = 0; i < 41; i += 1) env.win.tick(); // 10 s of 250 ms polls and one more
    expect(env.win.pendingTimers).toBe(0);
    env.plrNames.push("assay");
    env.win.tick();
    expect(env.plrActions()).toEqual([]); // it gave up
  });

  test("a page whose plrViewer does not exist yet is polled, not an error", () => {
    const env = makeEnv();
    env.plrReady = false;
    env.announce("v1");
    loadFrame(env);
    env.win.tick();
    env.win.tick();
    env.plrReady = true;
    env.plrNames.push("assay");
    env.win.tick();
    expect(env.plrActions()).toEqual([{ viewer: "v1", call: ["view", "top"] }]);
    expect(env.logger.errors).toEqual([]);
  });

  test("every load re-applies the held preset (T16): the press, then two reloads, three views of the same preset", () => {
    const env = makeEnv();
    env.plrNames.push("assay");
    env.announce("v1");
    env.click(env.viewButton("Iso")); // pressed while connected: view("iso") at once
    loadFrame(env);
    loadFrame(env);
    expect(env.plrActions().map((a) => a.call)).toEqual([
      ["view", "iso"],
      ["view", "iso"],
      ["view", "iso"],
    ]);
    expect(env.ctl.snapshot().preset).toBe("iso");
  });

  test("Iso / Top / Front: aria-pressed follows the held preset; connected presses call view() on the iframe in the panel", () => {
    const env = makeEnv();
    env.announce("v1");
    env.click(env.viewButton("Front"));
    expect(env.plrActions()).toEqual([{ viewer: "v1", call: ["view", "front"] }]);
    const pressed = () => env.find(".praxis-deck-panel__views").children.map((b) => b.getAttribute("aria-pressed"));
    expect(pressed()).toEqual(["false", "false", "true"]);
    env.click(env.viewButton("Iso"));
    expect(pressed()).toEqual(["true", "false", "false"]);
    expect(env.ctl.snapshot().preset).toBe("iso");
  });

  test("in any state without an iframe a preset press only updates the held preset", () => {
    const env = makeEnv();
    env.toggle(); // open-waiting
    env.click(env.viewButton("Front"));
    expect(env.ctl.snapshot().preset).toBe("front");
    env.announce("v1");
    env.gone("v1"); // open-lost
    env.click(env.viewButton("Iso"));
    expect(env.ctl.snapshot().preset).toBe("iso");
    expect(env.plrActions()).toEqual([]);
  });
});

// -- Follow (D12, AC-35 unit half) --------------------------------------------------------------------------------

describe("Follow (D12; AC-35 unit half)", () => {
  function followEnv() {
    const env = makeEnv();
    const plate = createFakeCell({ executionCount: 1, outputs: [praxisOutput(stamp({ resource: "assay" }))] });
    const ledger = createFakeCell({
      executionCount: 2,
      outputs: [praxisOutput(stamp({ kind: "ledger", resource: null, rev: null }))],
    });
    const mixed = createFakeCell({
      executionCount: 3,
      outputs: [
        "stream",
        praxisOutput(stamp({ kind: "ledger", resource: null, rev: null })),
        praxisOutput(stamp({ resource: "assay" })),
        praxisOutput(stamp({ resource: "source" })),
      ],
    });
    const errorPanel = createFakeCell({
      executionCount: 4,
      outputs: [praxisOutput(stamp({ kind: "error", resource: null, rev: null }))],
    });
    const plain = createFakeCell({ executionCount: 5, outputs: ["stream"] });
    const empty = createFakeCell({ executionCount: null, outputs: [] });
    const html = createFakeCell({
      executionCount: 6,
      outputs: [praxisOutput(stamp({ resource: "tips_300" }), { carrier: "html" })],
    });
    const cells = { plate, ledger, mixed, errorPanel, plain, empty, html };
    for (const cell of Object.values(cells)) env.panels[0].addCell(cell);
    env.plrNames.push("assay", "source", "tips_300");
    env.announce("v1");
    expect(env.ctl.state()).toBe("open-connected"); // the precondition every Follow case below relies on
    return { env, ...cells };
  }
  const focusCalls = (env) => env.plrActions().filter((a) => a.call[0] === "focus");
  const footerFocus = (env) => {
    let text = null;
    walk(env.find(".praxis-deck-panel__footer"), (el) => {
      if (el.hasAttribute && el.hasAttribute("data-praxis-deck-focus")) text = el.textContent;
    });
    return text;
  };

  test("on by default; activating a cell whose first Praxis output has a resource focuses it with the held preset", () => {
    const { env, plate } = followEnv();
    expect(env.find(".praxis-deck-panel__follow").getAttribute("aria-checked")).toBe("true");
    env.panels[0].activate(plate);
    expect(focusCalls(env)).toEqual([{ viewer: "v1", call: ["focus", "assay", "top"] }]);
    expect(footerFocus(env)).toBe("assay");
  });

  test("follow_skips_null: a cell whose only Praxis output is a ledger leaves the camera unchanged", () => {
    const { env, ledger } = followEnv();
    env.panels[0].activate(ledger);
    expect(focusCalls(env)).toEqual([]);
  });

  test("a cell whose outputs are [stream, ledger, plate assay, plate source] focuses the FIRST non-null resource", () => {
    const { env, mixed } = followEnv();
    env.panels[0].activate(mixed);
    expect(focusCalls(env)).toEqual([{ viewer: "v1", call: ["focus", "assay", "top"] }]);
  });

  test("channel-owner error panels, generic panels, and cells with no output leave the camera alone", () => {
    const { env, errorPanel, plain, empty } = followEnv();
    for (const cell of [errorPanel, plain, empty]) env.panels[0].activate(cell);
    env.panels[0].activate(null);
    expect(focusCalls(env)).toEqual([]);
  });

  test("the stamp is read through stampOf: the S3-B carrier (metadata['text/html'].praxis) works too", () => {
    const { env, html } = followEnv();
    env.panels[0].activate(html);
    expect(focusCalls(env)).toEqual([{ viewer: "v1", call: ["focus", "tips_300", "top"] }]);
  });

  test("Follow off holds the camera; the switch toggles back on", () => {
    const { env, plate, mixed } = followEnv();
    const follow = env.find(".praxis-deck-panel__follow");
    env.click(follow);
    expect(follow.getAttribute("aria-checked")).toBe("false");
    env.panels[0].activate(plate);
    expect(focusCalls(env)).toEqual([]);
    env.click(follow);
    expect(follow.getAttribute("aria-checked")).toBe("true");
    env.panels[0].activate(mixed);
    expect(focusCalls(env).length).toBe(1);
  });

  test("follow_keeps_preset: after Front, a Follow-driven focus passes 'front'", () => {
    const { env, plate } = followEnv();
    env.click(env.viewButton("Front"));
    env.panels[0].activate(plate);
    expect(focusCalls(env)).toEqual([{ viewer: "v1", call: ["focus", "assay", "front"] }]);
  });

  test("it acts only in open-connected: closed, open-waiting and open-lost do nothing (and do not throw)", () => {
    const { env, plate } = followEnv();
    env.gone("v1"); // open-lost
    expect(() => env.panels[0].activate(plate)).not.toThrow();
    env.kernelClose("v1"); // open-waiting
    env.panels[0].activate(plate);
    env.toggle(); // closed
    env.panels[0].activate(plate);
    expect(focusCalls(env)).toEqual([]);
    expect(env.logger.errors).toEqual([]);
  });

  test("the call goes to the iframe currently in the panel, read at call time (a re-dock made a new one)", () => {
    const { env, plate } = followEnv();
    env.kernelClose("v1");
    env.announce("v2"); // a new iframe
    env.panels[0].activate(plate);
    expect(focusCalls(env)).toEqual([{ viewer: "v2", call: ["focus", "assay", "top"] }]);
  });

  test("a page that is not ready (no plrViewer) is not an error and the footer does not claim a focus", () => {
    const { env, plate } = followEnv();
    env.plrReady = false;
    expect(() => env.panels[0].activate(plate)).not.toThrow();
    expect(footerFocus(env)).not.toBe("assay");
    expect(env.logger.errors).toEqual([]);
  });

  test("a plrViewer that throws is contained and logged", () => {
    const { env, plate } = followEnv();
    env.frames()[0].contentWindow.plrViewer; // create the viewer object for the frame
    env.plrOf.get(env.frames()[0]).focus = () => {
      throw new Error("cross-frame failure");
    };
    expect(() => env.panels[0].activate(plate)).not.toThrow();
    expect(env.logger.errors.length).toBeGreaterThan(0);
    expect(env.ctl.state()).toBe("open-connected");
  });

  test("the footer's focus line resets when the viewer goes away", () => {
    const { env, plate } = followEnv();
    env.panels[0].activate(plate);
    expect(footerFocus(env)).toBe("assay");
    env.kernelClose("v1");
    expect(footerFocus(env)).not.toBe("assay");
  });
});

// -- click-to-focus wiring with interact.js (B9) ---------------------------------------------------------------------

describe("click-to-focus (interact.js -> dock.focus(name))", () => {
  function clickResource(env, name) {
    const g = env.doc.createElement("g");
    g.setAttribute("data-praxis-res", name);
    env.doc.body.appendChild(g);
    g.dispatch("click", {});
    g.remove();
  }

  test("a click on a data-praxis-res resource focuses it on the page with the held preset", () => {
    const env = makeEnv();
    env.plrNames.push("assay", "source");
    env.announce("v1");
    const interact = mountInteract({ win: env.win, logger: env.logger, controllers: { dock: env.ctl } });
    clickResource(env, "source");
    expect(env.plrActions()).toEqual([{ viewer: "v1", call: ["focus", "source", "top"] }]);
    env.click(env.viewButton("Front"));
    clickResource(env, "assay");
    expect(env.plrActions().at(-1)).toEqual({ viewer: "v1", call: ["focus", "assay", "front"] });
    interact.dispose();
  });

  test("interact.js finds controllers.dock at click time, and outside open-connected a click does nothing", () => {
    const env = makeEnv();
    const controllers = {};
    const interact = mountInteract({ win: env.win, logger: env.logger, controllers });
    controllers.dock = env.ctl; // mounted after interact, as in index.js
    clickResource(env, "assay"); // closed
    env.toggle(); // open-waiting
    clickResource(env, "assay");
    env.announce("v1");
    env.gone("v1"); // open-lost
    expect(() => clickResource(env, "assay")).not.toThrow();
    expect(env.plrActions()).toEqual([]);
    expect(env.logger.errors).toEqual([]);
    interact.dispose();
  });

  test("focus(name) returns whether the page took it, and a bad name is data, not a selector", () => {
    const env = makeEnv();
    env.plrNames.push("assay");
    expect(env.ctl.focus("assay")).toBe(false); // closed
    env.announce("v1");
    expect(env.ctl.focus('we"ird[name]')).toBe(true);
    expect(env.plrActions().at(-1).call).toEqual(["focus", 'we"ird[name]', "top"]);
    expect(env.ctl.focus("")).toBe(false);
    expect(env.ctl.focus(42)).toBe(false);
  });
});

// -- praxis:toggle-deck-panel ---------------------------------------------------------------------------------------------

describe("praxis:toggle-deck-panel", () => {
  test("it is registered once, with a label", () => {
    const env = makeEnv();
    expect(env.app.commands.hasCommand(TOGGLE)).toBe(true);
    expect(typeof env.app.commands.label(TOGGLE)).toBe("string");
    expect(env.app.commands.label(TOGGLE).length).toBeGreaterThan(0);
  });

  test("toggle while closed reopens (T4); toggle while open closes, from every open state", () => {
    const env = makeEnv();
    env.toggle();
    expect(env.ctl.state()).toBe("open-waiting");
    env.toggle();
    expect(env.ctl.state()).toBe("closed");
    env.announce("v1");
    expect(env.ctl.state()).toBe("open-connected");
    env.toggle();
    expect(env.ctl.state()).toBe("closed");
    env.toggle();
    env.announce("v1");
    env.gone("v1");
    expect(env.ctl.state()).toBe("open-lost");
    env.toggle();
    expect(env.ctl.state()).toBe("closed");
  });

  test("a second mount on the same app does not throw when the command already exists", () => {
    const env = makeEnv();
    expect(() => env.remount()).not.toThrow();
    expect(env.logger.errors).toEqual([]);
  });

  test("an app without commands still mounts (the panel just has no palette entry)", () => {
    const env = makeEnv({ mountIt: false });
    delete env.app.commands;
    expect(() => env.remount()).not.toThrow();
    expect(env.ctl.state()).toBe("closed");
  });

  test("the controller's toggle() is the same event", () => {
    const env = makeEnv();
    env.ctl.toggle();
    expect(env.ctl.state()).toBe("open-waiting");
    env.ctl.toggle();
    expect(env.ctl.state()).toBe("closed");
  });
});

// -- the praxis_viz3d protocol (D11, C4 facts) ------------------------------------------------------------------------

describe("the praxis_viz3d protocol", () => {
  test("the shell posts exactly {kind: 'query'} as a JSON string, on mount", () => {
    const env = makeEnv();
    expect(env.heard).toEqual([{ kind: "query" }]);
  });

  const pageTraffic = [
    { kind: "open", viewer: "v2", client: "c1" },
    { kind: "accept", viewer: "v2", client: "c1" },
    { kind: "msg", viewer: "v2", client: "c1", data: "{}" },
    { kind: "bye", viewer: "v2", client: "c1" },
    { kind: "evict", viewer: "v2", client: "c1" },
    { kind: "open", viewer: "v1", client: "c1" },
    { kind: "accept", viewer: "v1", client: "c1" },
    { kind: "msg", viewer: "v1", client: "c1", data: "{}" },
  ];
  const states = {
    closed: () => makeEnv(),
    "open-waiting": () => {
      const env = makeEnv();
      env.toggle();
      return env;
    },
    "open-connected": () => {
      const env = makeEnv();
      env.announce("v1");
      return env;
    },
    "open-lost": () => {
      const env = makeEnv();
      env.announce("v1");
      env.gone("v1");
      return env;
    },
  };
  for (const [name, build] of Object.entries(states)) {
    test(`open / accept / msg / bye / evict are page<->kernel traffic: ignored in ${name}`, () => {
      const env = build();
      const m = env.mark();
      const current = env.ctl.snapshot().current;
      for (const message of pageTraffic) env.post(message);
      expect(env.since(m)).toEqual({ srcWrites: 0, queries: 0, framesCreated: 0 });
      assertInvariants(env, { state: name, current });
    });
  }

  const malformed = [
    "not json",
    "",
    "[]",
    "null",
    "42",
    '"a string"',
    "{}",
    '{"kind":7}',
    '{"kind":"nope","viewer":"v1"}',
    '{"kind":"announce"}',
    '{"kind":"announce","viewer":""}',
    '{"kind":"announce","viewer":5}',
    '{"kind":"announce","viewer":{"a":1}}',
    '{"kind":"announce","viewer":["v1"]}',
    `{"kind":"announce","viewer":"${"v".repeat(300)}"}`,
    '{"kind":"close"}',
    '{"kind":"close","viewer":null}',
    '{"kind":"close","viewer":7}',
  ];
  for (const raw of malformed) {
    test(`a malformed message is dropped without a trace: ${raw.slice(0, 40)}`, () => {
      const env = makeEnv();
      env.post(raw);
      assertInvariants(env, { state: "closed" });
      env.announce("v1");
      env.post(raw);
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });
  }

  test("a non-string payload is dropped (every message is a JSON string)", () => {
    const env = makeEnv();
    for (const data of [{ kind: "announce", viewer: "v1" }, 5, null, undefined, ["announce"], true]) {
      env.hub.post("praxis_viz3d", data, { except: [env.probe] });
    }
    assertInvariants(env, { state: "closed" });
  });

  test("an oversize message is dropped without being parsed (an announce or close is tiny)", () => {
    const env = makeEnv();
    env.post({ kind: "announce", viewer: "v1", deck: "x".repeat(5000) });
    assertInvariants(env, { state: "closed" });
    env.post({ kind: "msg", viewer: "v1", client: "c", data: "y".repeat(400000) }); // a scene
    assertInvariants(env, { state: "closed" });
  });

  test("the announce's deck name is optional: without one the header says Deck", () => {
    const env = makeEnv();
    env.post({ kind: "announce", viewer: "v1" });
    expect(env.find(".praxis-deck-panel__title").textContent).toBe("Deck");
    env.announce("v2", 12345);
    expect(env.find(".praxis-deck-panel__title").textContent).toBe("Deck");
  });

  test("a viewer id is data: it is encoded into the src, never trusted as a URL part", () => {
    const env = makeEnv();
    env.announce("v1&embed=0#x");
    const url = new URL(env.frames()[0].getAttribute("src"));
    expect(url.searchParams.get("viewer")).toBe("v1&embed=0#x");
    expect(url.searchParams.get("embed")).toBe("1");
    expect(env.ctl.snapshot().current).toBe("v1&embed=0#x");
  });

  describe("praxis:dock-status from the iframe's embed.js", () => {
    test("plr:gone for a viewer the panel is not showing is ignored (a late event of a replaced page)", () => {
      const env = makeEnv();
      env.announce("v1");
      env.announce("v2");
      env.gone("v1"); // the old page of the replaced src gave up late
      env.gone("other");
      env.gone(null);
      env.gone(undefined);
      assertInvariants(env, { state: "open-connected", current: "v2" });
      env.gone("v2");
      assertInvariants(env, { state: "open-lost", current: "v2" });
    });

    test("malformed dock-status events are ignored", () => {
      const env = makeEnv();
      env.announce("v1");
      for (const event of [
        { type: "praxis:dock-status" },
        { type: "praxis:dock-status", detail: null },
        { type: "praxis:dock-status", detail: "plr:gone" },
        { type: "praxis:dock-status", detail: { event: "plr:unknown", viewer: "v1" } },
        { type: "praxis:dock-status", detail: { viewer: "v1" } },
      ]) {
        expect(() => env.win.dispatchEvent(event)).not.toThrow();
      }
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });

    test("plr:status records whether the page is connected, for the panel it belongs to only", () => {
      const env = makeEnv();
      env.announce("v1");
      expect(env.ctl.snapshot().connected).toBe(null);
      env.status("v1", true);
      expect(env.ctl.snapshot().connected).toBe(true);
      env.status("v1", false);
      expect(env.ctl.snapshot().connected).toBe(false);
      env.status("v2", true); // another viewer's page
      expect(env.ctl.snapshot().connected).toBe(false);
      assertInvariants(env, { state: "open-connected", current: "v1" });
    });
  });
});

// -- sizing in the case in force: honoured / reachable (D6, AC-36 unit half) --------------------------------------------

describe("sizing, case honoured_reachable (D6; AC-36 unit half)", () => {
  const deckWidth = (env) => env.dock.widthOf(env.deckWidget());
  const nbWidth = (env) => env.dock.widthOf(env.panels[0]);
  const insertions = (env) => env.doc.appendLog.filter((e) => e.child.localName === "iframe").length;

  for (const width of [1280, 1440, 1599]) {
    test(`${width} px: CSS limits 420/480 on the widget node, the open-time width is inside, parent.fit() ran`, () => {
      const env = makeEnv({ width });
      env.announce("v1");
      const node = env.node();
      expect(node.style.minWidth).toBe("420px");
      expect(node.style.maxWidth).toBe("480px");
      expect(deckWidth(env)).toBeGreaterThanOrEqual(420);
      expect(deckWidth(env)).toBeLessThanOrEqual(480);
      expect(env.dock.fitCalls).toBeGreaterThanOrEqual(1);
      expect(env.dock.restoreCalls.length).toBe(0); // 1280-1599 is CSS, not layout
    });
  }

  test("1440: a real splitter drag to 300 px is clamped to 420, a drag to 700 px to 480", () => {
    const env = makeEnv({ width: 1440 });
    env.announce("v1");
    expect(env.dock.drag(env.deckWidget(), 300)).toBe(420);
    expect(env.dock.drag(env.deckWidget(), 700)).toBe(480);
    expect(insertions(env)).toBe(1); // no drag reloaded the iframe
  });

  test("1600: layout sizing gives panel_width = max(420, main - 960 - padding), no CSS limit, notebook content 960", () => {
    const env = makeEnv({ width: 1600 });
    env.announce("v1");
    expect(Math.abs(deckWidth(env) - 624)).toBeLessThan(1);
    expect(env.node().style.minWidth || "").toBe("");
    expect(env.node().style.maxWidth || "").toBe(""); // no maximum above 1600
    expect(env.dock.restoreCalls.length).toBeGreaterThanOrEqual(1); // saveLayout, sizes, restoreLayout
    expect(env.dock.saveCalls).toBeGreaterThanOrEqual(1);
    expect(nbWidth(env) - 16).toBeLessThanOrEqual(960 + 1);
    expect(nbWidth(env) - 16).toBeGreaterThanOrEqual(960 - 8);
  });

  test("1920: the formula again (944), and no maximum", () => {
    const env = makeEnv({ width: 1920 });
    env.announce("v1");
    expect(Math.abs(deckWidth(env) - 944)).toBeLessThan(1);
    expect(nbWidth(env) - 16).toBeLessThanOrEqual(960 + 1);
  });

  test("the notebook's own padding is read: with none, 1920 gives 960", () => {
    const env = makeEnv({ width: 1920, pad: 0 });
    env.announce("v1");
    expect(Math.abs(deckWidth(env) - 960)).toBeLessThan(1);
  });

  test("1600 with the file browser open (main area 1300 px): the 420 floor", () => {
    const env = makeEnv({ width: 1600, sidebar: 300 });
    env.announce("v1");
    expect(Math.abs(deckWidth(env) - 420)).toBeLessThan(1);
  });

  test("a window resize within >= 1600 (1600 -> 1920) recomputes on the ResizeObserver, with no iframe reload", () => {
    const env = makeEnv({ width: 1600 });
    env.announce("v1");
    const frame = env.frames()[0];
    const writes = env.srcWrites().length;
    env.resize(1920);
    expect(Math.abs(deckWidth(env) - 944)).toBeLessThan(1);
    expect(env.frames()).toEqual([frame]);
    expect(insertions(env)).toBe(1); // iframe_reloads_during_resize = 0
    expect(env.srcWrites().length).toBe(writes);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("a file-browser toggle at >= 1600 changes the main area only: the ResizeObserver recomputes both ways", () => {
    const env = makeEnv({ width: 1600 });
    env.announce("v1");
    env.setSidebar(300);
    expect(Math.abs(deckWidth(env) - 420)).toBeLessThan(1);
    env.setSidebar(0);
    expect(Math.abs(deckWidth(env) - 624)).toBeLessThan(1);
    expect(insertions(env)).toBe(1);
  });

  test("an unchanged size does not re-issue restoreLayout", () => {
    const env = makeEnv({ width: 1600 });
    env.announce("v1");
    env.win.resizeObservers.trigger();
    const calls = env.dock.restoreCalls.length;
    expect(calls).toBeGreaterThanOrEqual(1); // layout sizing did run
    env.win.resizeObservers.trigger();
    env.win.resizeObservers.trigger();
    expect(env.dock.restoreCalls.length).toBe(calls);
  });

  test("fit_after_tier_change: 1440 -> 1600 -> 1440 with the panel open, parent.fit() at each crossing, each tier's width holds", () => {
    const env = makeEnv({ width: 1440 });
    env.announce("v1");
    const frame = env.frames()[0];
    let fits = env.dock.fitCalls;
    env.resize(1600); // up: the limits go, the formula applies
    expect(env.dock.fitCalls).toBeGreaterThan(fits);
    expect(env.node().style.maxWidth || "").toBe("");
    expect(Math.abs(deckWidth(env) - 624)).toBeLessThan(1);
    fits = env.dock.fitCalls;
    env.resize(1440); // down: the limits return and Lumino re-reads them
    expect(env.dock.fitCalls).toBeGreaterThan(fits);
    expect(env.node().style.minWidth).toBe("420px");
    expect(env.node().style.maxWidth).toBe("480px");
    expect(deckWidth(env)).toBeGreaterThanOrEqual(420);
    expect(deckWidth(env)).toBeLessThanOrEqual(480);
    expect(env.frames()).toEqual([frame]); // a 1600 crossing moves no iframe
    expect(insertions(env)).toBe(1);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("a ResizeObserver callback in the 1280-1599 tier leaves layout alone (CSS limits do the clamping)", () => {
    const env = makeEnv({ width: 1440 });
    env.announce("v1");
    env.win.resizeObservers.trigger();
    env.resize(1500);
    expect(env.dock.restoreCalls.length).toBe(0);
    expect(deckWidth(env)).toBeLessThanOrEqual(480);
  });

  test("closed: the main area is no longer observed and layout is never touched", () => {
    const env = makeEnv({ width: 1600 });
    env.announce("v1");
    env.toggle();
    expect(env.win.resizeObservers.liveCount).toBe(0);
    const calls = env.dock.restoreCalls.length;
    env.resize(1920);
    env.win.resizeObservers.trigger();
    expect(env.dock.restoreCalls.length).toBe(calls);
  });

  test("re-opening at another width sizes by that width (open-time keys)", () => {
    const env = makeEnv({ width: 1440 });
    env.announce("v1");
    env.toggle(); // closed
    env.resize(1920);
    env.toggle(); // T4
    env.announce("v1"); // T6
    expect(Math.abs(deckWidth(env) - 944)).toBeLessThan(1);
    env.toggle();
    env.resize(1280);
    env.toggle();
    env.announce("v1");
    expect(deckWidth(env)).toBeLessThanOrEqual(480);
    expect(deckWidth(env)).toBeGreaterThanOrEqual(420);
  });

  test("a drawer never touches layout, and observes no ResizeObserver", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    assertHome(env, "drawer");
    env.resize(1200);
    expect(env.dock.restoreCalls.length).toBe(0);
    expect(env.dock.saveCalls).toBe(0);
    expect(env.win.resizeObservers.liveCount).toBe(0);
  });

  test("layout sizing degrades quietly when the deck is not in a horizontal split (the user re-arranged it)", () => {
    const env = makeEnv({ width: 1920 });
    env.announce("v1");
    // The user drags the deck into the notebook's own tab group: no split holds it any more.
    const layout = env.dock.layoutTree;
    env.dock.layoutTree = { type: "tab-area", widgets: [...layout.children[0].widgets, env.deckWidget()], currentIndex: 0 };
    expect(() => env.resize(1800)).not.toThrow();
    expect(env.logger.errors).toEqual([]);
  });

  test("a dock panel without saveLayout/restoreLayout leaves the width to Lumino, no error", () => {
    const env = makeEnv({ width: 1920 });
    env.announce("v1");
    expect(env.dock.restoreCalls.length).toBeGreaterThanOrEqual(1); // it did size by layout while it could
    env.dock.saveLayout = undefined;
    expect(() => env.resize(1800)).not.toThrow();
  });
});

// -- the drawer (1024-1279 px) ------------------------------------------------------------------------------------------

describe("the drawer (D6, T2/T7/T10/T15/T17/T21/T22)", () => {
  test("the first announce of a page opens it over the notebook, without reflow", () => {
    const env = makeEnv({ width: 1152 });
    const before = env.dock.widthOf(env.panels[0]);
    env.announce("v1");
    assertHome(env, "drawer");
    expect(env.app.shell.addCalls).toEqual([]); // not a split-right widget
    expect(env.node().style.position).toBe("fixed");
    expect(env.dock.widthOf(env.panels[0])).toBe(before); // drawer_no_reflow
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("the close button exists in the drawer (labelled) and is hidden in the split", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    const close = env.find(".praxis-deck-panel__close");
    expect(close.getAttribute("aria-label")).toBeTruthy();
    expect(close.style.display).not.toBe("none");
    env.resize(1440);
    expect(env.find(".praxis-deck-panel__close").style.display).toBe("none");
    expect(env.node().style.position || "").not.toBe("fixed");
    env.resize(1152);
    expect(env.find(".praxis-deck-panel__close").style.display).not.toBe("none");
    expect(env.node().style.position).toBe("fixed");
  });

  test("drawer_dismiss_reopen: close button (T17), toggle (T4 -> T6), Escape (T17), toggle again", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    env.click(env.find(".praxis-deck-panel__close"));
    assertInvariants(env, { state: "closed" });
    env.toggle();
    assertInvariants(env, { state: "open-waiting" });
    env.announce("v1");
    assertInvariants(env, { state: "open-connected", current: "v1" });
    env.escape();
    assertInvariants(env, { state: "closed" });
    env.toggle();
    env.announce("v1");
    assertHome(env, "drawer");
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("Escape closes only from focus inside the drawer, only in the drawer tier, and only Escape", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    env.doc.body.dispatch("keydown", { key: "Escape" }); // focus elsewhere in the page
    assertInvariants(env, { state: "open-connected", current: "v1" });
    env.find(".praxis-deck-panel__header").dispatch("keydown", { key: "Enter" });
    assertInvariants(env, { state: "open-connected", current: "v1" });
    env.resize(1440); // the split: Escape is not a close there
    env.escape();
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });

  test("tier_up_rehomes: an open drawer resized to 1440 goes into the split with the same iframe and src; back down again", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    const frame = env.frames()[0];
    const src = frame.getAttribute("src");
    env.resize(1440);
    assertHome(env, "split");
    expect(env.app.shell.addCalls.length).toBe(1);
    expect(env.frames()).toEqual([frame]);
    expect(frame.getAttribute("src")).toBe(src);
    expect(env.dock.widthOf(env.deckWidget())).toBeLessThanOrEqual(480);
    env.resize(1152);
    assertHome(env, "drawer");
    expect(frame.getAttribute("src")).toBe(src);
    expect(env.srcWrites().length).toBe(1);
  });

  test("a closed drawer resized up stays closed (T5), and the next open is in the split", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    env.click(env.find(".praxis-deck-panel__close"));
    env.resize(1440);
    assertInvariants(env, { state: "closed" });
    expect(env.inDock()).toBe(false);
    env.toggle();
    assertHome(env, "split");
  });

  test("drawer -> split -> drawer re-homing repeats without leaking a second panel node", () => {
    const env = makeEnv({ width: 1152 });
    env.announce("v1");
    for (let i = 0; i < 4; i += 1) {
      env.resize(1440);
      env.resize(1152);
    }
    const nodes = [];
    walk(env.doc, (el) => {
      if (el.classList && el.classList.contains("praxis-deck-panel")) nodes.push(el);
    });
    expect(nodes.length).toBe(1);
    assertInvariants(env, { state: "open-connected", current: "v1" });
  });
});

// -- the whole table, against a second implementation -------------------------------------------------------------------

describe("random sequences agree with an independent model of the D11 table (I1-I6)", () => {
  function mulberry32(seed) {
    let a = seed;
    return () => {
      a += 0x6d2b79f5;
      let t = a;
      t = Math.imul(t ^ (t >>> 15), t | 1);
      t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }

  /** The table, restated from the spec (T1-T27), for one notebook panel with a kernel. */
  function step(m, event) {
    switch (event.t) {
      case "announce": {
        const first = !m.seen;
        m.seen = true;
        if (m.state === "closed") {
          if (first) {
            m.state = "open-connected";
            m.current = event.id;
            m.src += 1;
          }
        } else if (m.state === "open-waiting" || m.state === "open-lost") {
          m.state = "open-connected";
          m.current = event.id;
          m.src += 1;
        } else if (event.id !== m.current) {
          m.current = event.id;
          m.src += 1;
        }
        break;
      }
      case "kclose":
        if ((m.state === "open-connected" || m.state === "open-lost") && event.id === m.current) {
          m.state = "open-waiting";
          m.current = null;
        }
        break;
      case "gone":
        if (m.state === "open-connected" && event.id === m.current) m.state = "open-lost";
        break;
      case "toggle":
        if (m.state === "closed") {
          m.state = "open-waiting";
          m.q += 1;
        } else {
          m.state = "closed";
          m.current = null;
        }
        break;
      case "restart":
        if (m.state === "open-connected" || m.state === "open-lost") {
          m.state = "open-waiting";
          m.current = null;
        }
        break;
      default: // cross, status: no lifecycle effect
    }
  }

  for (const seed of [1, 2, 3, 4, 5, 6]) {
    test(`seed ${seed}: 400 events`, () => {
      const env = makeEnv();
      const rnd = mulberry32(seed);
      const model = { state: "closed", seen: false, current: null, q: 1, src: 0 };
      const ids = ["v1", "v2", "v3"];
      const trace = [];
      for (let i = 0; i < 400; i += 1) {
        const r = rnd();
        const id = ids[Math.floor(rnd() * ids.length)];
        let event;
        if (r < 0.3) event = { t: "announce", id };
        else if (r < 0.42) event = { t: "kclose", id };
        else if (r < 0.54) event = { t: "gone", id };
        else if (r < 0.66) event = { t: "toggle" };
        else if (r < 0.78) event = { t: "cross" };
        else if (r < 0.86) event = { t: "restart" };
        else if (r < 0.93) event = { t: "status", id };
        else event = { t: "announce", id: model.current || id }; // a same-id announce (T27)
        trace.push(event);
        if (event.t === "announce") env.announce(event.id);
        else if (event.t === "kclose") env.kernelClose(event.id);
        else if (event.t === "gone") env.gone(event.id);
        else if (event.t === "toggle") env.toggle();
        else if (event.t === "cross") env.resize(env.width === 1440 ? 1152 : 1440);
        else if (event.t === "restart") env.panels[0].kernelStatus("restarting");
        else env.status(event.id, true);
        step(model, event);
        try {
          assertInvariants(env, { state: model.state, current: model.current });
          expect(env.srcWrites().length).toBe(model.src); // I2: a src is written only by an acted announce
          expect(env.queries()).toBe(model.q); // I3: a query only at mount and reopen
          if (model.state !== "closed") assertHome(env, env.width >= 1280 ? "split" : "drawer");
        } catch (error) {
          error.message += `\n  after event #${i} ${JSON.stringify(event)}; trace: ${trace.map((e) => `${e.t}${e.id ?? ""}`).join(" ")}`;
          throw error;
        }
      }
    });
  }
});

// -- I4 and I6, stated on their own ------------------------------------------------------------------------------------

describe("invariants I4 and I6", () => {
  test("I4: plr:gone changes state only in open-connected; after a close or a restart it is ignored until an announce", () => {
    const env = makeEnv();
    env.announce("v1");
    env.kernelClose("v1");
    env.gone("v1");
    assertInvariants(env, { state: "open-waiting" });
    env.announce("v2");
    env.panels[0].kernelStatus("restarting");
    env.gone("v2");
    assertInvariants(env, { state: "open-waiting" });
    env.announce("v3");
    env.gone("v3");
    assertInvariants(env, { state: "open-lost", current: "v3" });
  });

  test("I6: a kernel close for the current viewer, or a kernel restart, never shows the lost text", () => {
    for (const cause of [
      (env) => env.kernelClose("v1"),
      (env) => env.panels[0].kernelStatus("dead"),
      (env) => env.panels[0].setKernel(null),
    ]) {
      const env = makeEnv();
      env.announce("v1");
      cause(env);
      expect(env.text().includes("lost its connection")).toBe(false);
      expect(env.text().includes(NO_VIEWER)).toBe(true);
    }
  });
});

// -- failure containment (D13 spirit: a broken deck panel must not take the shell away) ---------------------------------

describe("failure containment", () => {
  test("without a BroadcastChannel it mounts, warns, and the panel still opens (waiting, no query possible)", () => {
    const env = makeEnv({ broadcast: false });
    expect(env.ctl.state()).toBe("closed");
    expect(env.logger.warns.length).toBeGreaterThan(0);
    expect(() => env.toggle()).not.toThrow();
    expect(env.ctl.state()).toBe("open-waiting");
    expect(env.logger.errors).toEqual([]);
  });

  test("a BroadcastChannel constructor that throws is logged, not thrown", () => {
    const env = makeEnv({ mountIt: false });
    env.win.BroadcastChannel = class {
      constructor() {
        throw new Error("no channel for you");
      }
    };
    expect(() => env.remount()).not.toThrow();
    expect(env.logger.errors.length).toBeGreaterThan(0);
    expect(() => env.toggle()).not.toThrow();
    expect(env.ctl.state()).toBe("open-waiting");
  });

  test("a postMessage that throws is logged and the panel carries on", () => {
    const env = makeEnv({ mountIt: false });
    env.hub.BroadcastChannel.prototype.postMessage = () => {
      throw new Error("channel closed");
    };
    expect(() => env.remount()).not.toThrow();
    expect(() => env.toggle()).not.toThrow();
    expect(env.ctl.state()).toBe("open-waiting");
    expect(env.logger.errors.length).toBeGreaterThan(0);
  });

  test("with no document the mount still returns a controller and nothing throws", () => {
    const logger = recordingLogger();
    let ctl;
    expect(() => {
      ctl = realDock.mountDock({ app: {}, win: {}, logger, controllers: {} });
    }).not.toThrow();
    expect(ctl.state()).toBe("closed");
    expect(() => ctl.toggle()).not.toThrow();
    expect(() => ctl.focus("assay")).not.toThrow();
    expect(ctl.state()).toBe("closed");
    expect(logger.errors.length + logger.warns.length).toBeGreaterThan(0);
  });

  test("no arguments at all is survivable", () => {
    expect(() => realDock.mountDock()).not.toThrow();
    expect(() => realDock.mountDock({})).not.toThrow();
  });

  test("an iframe that cannot be created leaves the panel closed with the failure logged", () => {
    const env = makeEnv();
    const create = env.doc.createElement.bind(env.doc);
    env.doc.createElement = (tag) => {
      if (tag === "iframe") throw new Error("no iframes today");
      return create(tag);
    };
    expect(() => env.announce("v1")).not.toThrow();
    expect(env.ctl.state()).toBe("closed");
    expect(env.frames().length).toBe(0);
    expect(env.logger.errors.length).toBeGreaterThan(0);
    env.doc.createElement = create;
    env.toggle(); // and it recovers
    env.announce("v1");
    expect(env.ctl.state()).toBe("open-connected");
  });

  test("a logger that throws does not turn a contained failure into a thrown one", () => {
    const env = makeEnv();
    env.logger.error = () => {
      throw new Error("logger broke");
    };
    let attempts = 0;
    env.app.shell.add = () => {
      attempts += 1;
      throw new Error("shell.add blew up");
    };
    expect(() => env.announce("v1")).not.toThrow();
    expect(attempts).toBe(1); // it did try to attach
    expect(env.ctl.state()).toBe("closed");
  });

  test("a throwing signal slot source (a panel whose sessionContext is missing) does not stop mounting", () => {
    const env = makeEnv({ mountIt: false });
    env.panels[0].sessionContext = undefined;
    expect(() => env.remount()).not.toThrow();
    env.announce("v1");
    expect(env.ctl.state()).toBe("open-connected");
    expect(env.logger.errors).toEqual([]);
  });

  test("dispose(): listeners, channel, observer, timers and the command are released; later events do nothing", () => {
    const env = makeEnv({ width: 1600 });
    env.plrNames.length = 0;
    env.announce("v1");
    env.frames()[0].dispatch("load", {}); // a poll is pending
    expect(env.win.pendingTimers).toBe(1);
    env.ctl.dispose();
    expect(env.win.pendingTimers).toBe(0);
    expect(env.win.resizeObservers.liveCount).toBe(0);
    expect(env.win.listenerCount("praxis:dock-status")).toBe(0);
    expect(env.win.listenerCount("resize")).toBe(0);
    expect(env.hub.openCount("praxis_viz3d")).toBe(1); // only the probe
    expect(env.app.commands.hasCommand(TOGGLE)).toBe(false);
    const adds = env.app.shell.addCalls.length;
    env.announce("v2");
    env.resize(1152);
    expect(env.app.shell.addCalls.length).toBe(adds);
    expect(() => env.ctl.dispose()).not.toThrow();
  });
});

// -- mounted from index.js ------------------------------------------------------------------------------------------------

describe("mounted from index.js (D13: non-fatal, failure-isolated)", () => {
  function page() {
    const doc = createFakeDocument();
    doc.attrLog = [];
    doc.appendLog = [];
    const hub = createFakeBroadcastHub();
    const app = createFakeDeckApp({ doc, notebooks: 1, width: 1440 });
    const win = createFakeWindow({ app, document: doc, broadcast: hub, innerWidth: 1440 });
    const logger = recordingLogger();
    const heard = [];
    const probe = new hub.BroadcastChannel("praxis_viz3d");
    probe.addEventListener("message", (event) => heard.push(JSON.parse(event.data)));
    const viewer = createFakePlrViewer({ names: ["assay", "source"] });
    doc.onCreate = (el) => {
      if (el.localName === "iframe") el.contentWindow = { plrViewer: viewer };
    };
    return { doc, hub, app, win, logger, heard, probe, viewer };
  }
  const announce = (hub, probe, viewer) =>
    hub.post("praxis_viz3d", JSON.stringify({ kind: "announce", viewer, deck: "D", session: "s" }), { except: [probe] });

  test("mount(window) mounts chrome, stale, interact, then dock; a query is posted; nothing errors", async () => {
    const { hub, win, logger, heard } = page();
    const result = await mountDisplay(win, { logger });
    expect(result.errors).toEqual([]);
    expect(result.status).toBe("mounted");
    expect(Object.keys(result.controllers)).toEqual(["chrome", "stale", "interact", "dock"]);
    expect(result.controllers.dock.state()).toBe("closed");
    expect(heard.filter((m) => m.kind === "query").length).toBe(1);
    expect(hub.openCount("praxis_viz3d")).toBe(2); // the probe and the dock
  });

  test("controllers.dock is the object interact.js finds: a click on a resource reaches the page's plrViewer", async () => {
    const { doc, hub, win, logger, probe, viewer } = page();
    const result = await mountDisplay(win, { logger });
    announce(hub, probe, "v1");
    expect(result.controllers.dock.state()).toBe("open-connected");
    const g = doc.createElement("g");
    g.setAttribute("data-praxis-res", "source");
    doc.body.appendChild(g);
    g.dispatch("click", {});
    expect(viewer.actions).toEqual([["focus", "source", "top"]]);
    expect(logger.errors).toEqual([]);
  });

  test("a dock module that fails to load is contained, named, and leaves the other modules mounted", async () => {
    const { win, logger } = page();
    const modules = {
      chrome: () => import("./chrome.js"),
      stale: () => import("./stale.js"),
      interact: () => import("./interact.js"),
      dock: async () => {
        throw new SyntaxError("dock.js does not parse");
      },
    };
    const result = await mountDisplay(win, { modules, logger });
    expect(result.errors.map((e) => e.module)).toEqual(["dock"]);
    expect(result.errors[0].message).toContain("does not parse");
    expect(Object.keys(result.controllers)).toEqual(["chrome", "stale", "interact"]);
    expect(win.__praxisDisplay.status).toBe("failed");
    expect(win.__praxisDisplay.errors.map((e) => e.module)).toEqual(["dock"]);
    expect(logger.errors.length).toBeGreaterThan(0);
  });

  test("a mountDock that throws, or a dock module without mountDock, is contained the same way", async () => {
    for (const dock of [
      async () => ({
        mountDock() {
          throw new Error("mount blew up");
        },
      }),
      async () => ({}),
    ]) {
      const { win, logger } = page();
      const modules = {
        chrome: () => import("./chrome.js"),
        stale: () => import("./stale.js"),
        interact: () => import("./interact.js"),
        dock,
      };
      const result = await mountDisplay(win, { modules, logger });
      expect(result.errors.map((e) => e.module)).toEqual(["dock"]);
      expect(result.controllers.interact).toBeDefined();
    }
  });

  test("an earlier module failing does not stop dock (a chrome that throws)", async () => {
    const { win, logger } = page();
    const modules = {
      chrome: async () => ({
        mountChrome() {
          throw new Error("chrome blew up");
        },
      }),
      dock: () => import("./dock.js"),
    };
    const result = await mountDisplay(win, { modules, logger });
    expect(result.errors.map((e) => e.module)).toEqual(["chrome"]);
    expect(result.controllers.dock.state()).toBe("closed");
  });

  test("the real dock.js does not name the channels it must not use, nor carry test switches", () => {
    const source = readFileSync(join(HERE, "dock.js"), "utf8");
    expect(source.includes("praxis_repl")).toBe(false); // R21 (extended from sprint C)
    expect(/__praxis_test|data-praxis-test/.test(source)).toBe(false); // AC-39(c)
    expect(/requestDevice|requestPort/.test(source)).toBe(false); // R19
    expect(/\beval\s*\(|new Function|cdn\.|https?:\/\//.test(source)).toBe(false); // no eval, no CDN, no network
    expect(source.includes("praxis_viz3d")).toBe(true);
  });
});

// -- negative controls: dock.js with one behaviour broken must FAIL --------------------------------------------------------

describe("negative controls: each broken panel must fail its probe", () => {
  /** A probe scenario is a function of a dock module; it throws (an expect failure) when the module misbehaves. */
  function probeRemovesIframe(mod) {
    let env = makeEnv({ mod });
    env.announce("v1");
    env.kernelClose("v1"); // T12
    assertInvariants(env, { state: "open-waiting" });
    env = makeEnv({ mod });
    env.announce("v1");
    env.toggle(); // T17
    assertInvariants(env, { state: "closed" });
    env = makeEnv({ mod });
    env.announce("v1");
    env.gone("v1"); // T14
    assertInvariants(env, { state: "open-lost", current: "v1" });
  }

  function probeIgnoresPageTraffic(mod) {
    const traffic = [
      { kind: "open", viewer: "v2", client: "c1" },
      { kind: "msg", viewer: "v2", client: "c1", data: "{}" },
      { kind: "accept", viewer: "v2", client: "c1" },
      { kind: "bye", viewer: "v2", client: "c1" },
      { kind: "evict", viewer: "v2", client: "c1" },
    ];
    for (const connected of [false, true]) {
      const env = makeEnv({ mod });
      if (connected) env.announce("v1");
      for (const message of traffic) env.post(message);
      assertInvariants(env, connected ? { state: "open-connected", current: "v1" } : { state: "closed" });
    }
  }

  function probeQueriesOnReopen(mod) {
    const env = makeEnv({ mod });
    expect(env.queries()).toBe(1); // T1
    env.announce("v1");
    env.toggle(); // closed
    env.toggle(); // T4
    expect(env.queries()).toBe(2);
    assertInvariants(env, { state: "open-waiting" });
  }

  function probeFitsAfterTierChange(mod) {
    const env = makeEnv({ mod, width: 1600 });
    env.announce("v1");
    const fits = env.dock.fitCalls;
    env.resize(1440);
    expect(env.dock.fitCalls).toBeGreaterThan(fits);
    const width = env.dock.widthOf(env.deckWidget());
    expect(width).toBeGreaterThanOrEqual(420);
    expect(width).toBeLessThanOrEqual(480);
  }

  function probeObservesResizes(mod) {
    const env = makeEnv({ mod, width: 1600 });
    env.announce("v1");
    env.resize(1920);
    expect(Math.abs(env.dock.widthOf(env.deckWidget()) - 944)).toBeLessThan(1);
  }

  let counter = 0;
  /** dock.js's source with `from` (which must occur exactly once) replaced by `to`, loaded as its own module. */
  async function loadPatched(from, to) {
    const source = readFileSync(join(HERE, "dock.js"), "utf8");
    const first = source.indexOf(from);
    expect(first).toBeGreaterThanOrEqual(0); // the anchor exists...
    expect(source.indexOf(from, first + from.length)).toBe(-1); // ...exactly once
    const patched = source
      .replace(from, to)
      .replace(/from "\.\/([\w-]+)\.js"/g, (_m, name) => `from "${pathToFileURL(join(HERE, `${name}.js`)).href}"`);
    const dir = mkdtempSync(join(tmpdir(), "dock-mutant-"));
    counter += 1;
    const file = join(dir, `dock_${counter}.mjs`);
    writeFileSync(file, patched);
    return import(pathToFileURL(file).href);
  }

  const cases = [
    {
      name: "a panel that never removes the iframe",
      probe: probeRemovesIframe,
      from: "function removeFrames() {",
      to: "function removeFrames() { return;",
    },
    {
      name: "a panel that reacts to page<->kernel `open` / `msg` (as if they were announces)",
      probe: probeIgnoresPageTraffic,
      from: 'case "announce":',
      to: 'case "open": case "msg": case "announce":',
    },
    {
      name: "a panel that skips `query` on reopen",
      probe: probeQueriesOnReopen,
      from: "function postQuery() {",
      to: "function postQuery() { return;",
    },
    {
      name: "a panel that ignores parent.fit()",
      probe: probeFitsAfterTierChange,
      from: "function fitParent() {",
      to: "function fitParent() { return;",
    },
    {
      name: "a panel that never observes resizes",
      probe: probeObservesResizes,
      from: "function observeDock() {",
      to: "function observeDock() { return;",
    },
  ];

  for (const { name, probe, from, to } of cases) {
    test(`positive control: the real dock.js passes the probe for ${name}`, () => {
      probe(realDock);
    });

    test(`positive control: the patch loader with an identity patch passes it too (${name})`, async () => {
      const mod = await loadPatched(from, from);
      probe(mod);
    });

    test(`negative control: ${name} FAILS the probe`, async () => {
      const mod = await loadPatched(from, to);
      expect(() => probe(mod)).toThrow();
    });
  }
});
