// dock.js -- the deck panel widget (spec
// .praxia/docs/specs/260929_notebook-display-epic.md, task C5; D1 S1, D6, D11 "Deck-panel
// state machine", D12, D14, section 3.6; AC-35 and AC-36 unit halves).
//
// WHAT IT IS. A real Lumino Widget (S1-A, run 1e0cab6d): the root `Widget` class is found by
// walking the prototype chain of a widget the shell already holds, identified structurally
// (its prototype owns `processMessage` and `onAfterAttach`, and its own prototype is
// `Object.prototype`); the panel is `new Ctor({node})`, added with
// `app.shell.add(w, "main", {mode: "split-right", ref})`. At 1024-1279 px the same node is
// a fixed-position drawer over the notebook instead. Header (deck name, Follow, Iso / Top /
// Front), body (the ONE iframe, or one of two texts), footer (the focused resource, then the
// one-row motion slot). Class names and ARIA states are the A4 theme's
// (`.praxis-deck-panel__header|title|follow|views|footer|motion`, `aria-checked`,
// `aria-pressed`).
//
// THE LIFECYCLE IS THE D11 TABLE, NOTHING ELSE. States `closed`, `open-waiting`,
// `open-connected`, `open-lost`; events mount, announce, reopen, close panel, kernel close,
// plr:gone, tier crossing, iframe reload, kernel restart; transitions T1-T27; invariants
// I1-I6. In code: one function per event, each a `switch` over the state, in this order of
// concerns: (1) work that can fail is done first (create the iframe, attach the panel), (2)
// only then are the state and the DOM changed together. The iframe is the only thing whose
// presence is tied to a state (I1); the two texts are tied to two states (I5).
//
// WHAT IT LISTENS TO.
//   BroadcastChannel `praxis_viz3d` (every message is a JSON string, C4): the SHELL sends
//     {kind: "query"}                                    on mount (T1) and on reopen (T4)
//   and acts ONLY on the kernel's
//     {kind: "announce", viewer, deck, session}          T2 T3 T6 T11 T18 T27
//     {kind: "close", viewer, reason}                    T5 T8 T12 T13 T19 T20
//   `open`, `accept`, `msg`, `bye` and `evict` are page<->kernel traffic and are ignored.
//   Anything that is not a JSON object of a known kind, has no viewer id, or is over
//   MAX_MESSAGE bytes (an announce or close is tiny; a scene is not) is dropped unparsed.
//   `praxis:dock-status` CustomEvents on the window, dispatched by the iframe's embed.js:
//     detail {event: "plr:gone", viewer}                 T9 T14 T20 (honoured only in
//                                                        open-connected and only for the
//                                                        viewer the panel shows: I4)
//     detail {event: "plr:status", connected, viewer}    recorded only
//   The viewer's kernel's `sessionContext` (kernel restart, T23-T26): `statusChanged` to
//   restarting / autorestarting / dead, or `kernelChanged`, on the notebook panel that owns
//   the viewer (`viewerPanel`, or the only panel with a kernel).
//   The command `praxis:toggle-deck-panel` (reopen when closed, close panel when open).
//
// SIZING (D6), for the case S1 recorded, `honoured_reachable` (exported once, as SIZING, so
// the browser harness can assert it): 1280-1599 px use CSS limits (min 420 / max 480 px) on
// the widget node; >= 1600 px use layout sizing, `saveLayout()` -> edit the split area's
// `sizes` -> `restoreLayout()` on the main DockPanel, to
// panel_width = max(420, main_area_width - 960 - nb_h_padding), also on every ResizeObserver
// callback (`restoreLayout()` keeps the iframe, S1); `parent.fit()` after every tier change
// inside the split so Lumino re-reads the limits. The other D6 table rows (CSS ignored,
// layout unreachable, `restore_layout_keeps_iframe` false, S1-L) are not built: S1 ruled
// them out for this build.
//
// NEVER THROWS INTO THE SHELL. Every entry point (channel message, window event, signal
// slot, command, click, timer, public method) runs under its own try/catch and reports with
// `logger.error`; a failed step leaves the state where it was. A dock that cannot mount
// (no document, no channel) still returns a controller. No storage keys, no eval, no
// network, no selector built from a name (D14: names are compared and passed on as strings).

import { isRunning } from "./chrome.js";
import { stampOf } from "./stale.js";

// -- constants ------------------------------------------------------------------------------------------------------------

export const CHANNEL = "praxis_viz3d";
export const TOGGLE_COMMAND = "praxis:toggle-deck-panel";
export const DOCK_STATUS_EVENT = "praxis:dock-status";
export const NO_VIEWER_TEXT =
  "No deck viewer is running. Run `viewer = await praxis.viz.viewer3d.dock(deck)` in a cell.";
export const LOST_TEXT =
  "The deck view lost its connection. Close and reopen the deck panel, or run `dock(deck)` again.";
export const MOTION_TEXT = "Motion playback is not available for this backend.";
export const STATES = Object.freeze(["closed", "open-waiting", "open-connected", "open-lost"]);
export const PRESETS = Object.freeze(["iso", "top", "front"]);

/** The D6 sizing case in force (S1 run 1e0cab6d): every AC-36 width key is asserted. */
export const SIZING = Object.freeze({
  case: "honoured_reachable",
  cssLimitsHonoured: true,
  layoutSizingReachable: true,
  cssLimitsRefit: true,
  restoreLayoutKeepsIframe: true,
});

const WIDGET_ID = "praxis-deck-panel";
const MIN_PANEL = 420;
const MAX_PANEL = 480;
const NOTEBOOK_CAP = 960;
const WIDE_FROM = 1600;
const SPLIT_FROM = 1280;
const MAX_MESSAGE = 4096;
const MAX_ID = 200;
const MAX_TITLE = 200;
const POLL_MS = 250;
const POLL_MAX = 40; // 10 s of 250 ms
const RESTART_STATUSES = new Set(["restarting", "autorestarting", "dead"]);
const SHELL_AREAS = ["main", "left", "right", "top", "bottom", "down", "header", "menu"];
const NO_FOCUS_TEXT = "No resource focused.";

const hasOwn = Object.prototype.hasOwnProperty;

// -- pure helpers ---------------------------------------------------------------------------------------------------

/** The D6 tier of a window width: "wide" (>= 1600), "medium" (1280-1599), else "drawer" (< 1280,
 * including the out-of-scope < 1024, where the drawer is the only layout that never reflows). */
export function tierOf(width) {
  if (width >= WIDE_FROM) return "wide";
  if (width >= SPLIT_FROM) return "medium";
  return "drawer";
}

/** Where a tier keeps the panel: the split (main area) or the drawer. */
export function homeOf(tier) {
  return tier === "drawer" ? "drawer" : "split";
}

/** D6 >= 1600: panel_width = max(420, main_area_width - 960 - nb_h_padding). */
export function panelWidth(mainWidth, padding) {
  return Math.max(MIN_PANEL, mainWidth - NOTEBOOK_CAP - padding);
}

/** The iframe URL for a viewer id: `assets/visualizer3d/index.html?embed=1&view=top&viewer=<id>`. */
export function viewerSrc(base, id) {
  const root = base.endsWith("/") ? base : `${base}/`;
  return `${root}assets/visualizer3d/index.html?embed=1&view=top&viewer=${encodeURIComponent(id)}`;
}

function defaultBase() {
  try {
    return new URL("../../", import.meta.url).href; // <dist>/shell/display/dock.js -> <dist>/
  } catch {
    return "../../";
  }
}

function own(obj, key) {
  return obj !== null && typeof obj === "object" && hasOwn.call(obj, key) ? obj[key] : undefined;
}

function isNotebookPanel(widget) {
  return Boolean(
    widget && widget.content && widget.node && widget.node.classList && widget.node.classList.contains("jp-NotebookPanel"),
  );
}

/** The structural test for the root Lumino Widget prototype (S1-A). */
function isRootPrototype(proto) {
  return (
    proto !== null &&
    typeof proto === "object" &&
    hasOwn.call(proto, "processMessage") &&
    hasOwn.call(proto, "onAfterAttach") &&
    Object.getPrototypeOf(proto) === Object.prototype &&
    typeof proto.constructor === "function"
  );
}

/** The root Widget class reached from any widget the shell holds, or null. */
function findRootConstructor(shell) {
  const candidates = [];
  if (shell) {
    if (shell.currentWidget) candidates.push(shell.currentWidget);
    if (typeof shell.widgets === "function") {
      for (const area of SHELL_AREAS) {
        try {
          candidates.push(...Array.from(shell.widgets(area)));
        } catch {
          // an area this shell does not have
        }
      }
    }
  }
  for (const widget of candidates) {
    let proto = widget && typeof widget === "object" ? Object.getPrototypeOf(widget) : null;
    for (let depth = 0; proto && depth < 64; depth += 1) {
      if (isRootPrototype(proto)) return proto.constructor;
      proto = Object.getPrototypeOf(proto);
    }
  }
  return null;
}

/** The horizontal split area that directly holds `widget`'s tab area: {node, index}, or null. */
function findSplit(area, widget) {
  if (!area || area.type !== "split-area" || !Array.isArray(area.children)) return null;
  if (area.orientation === "horizontal") {
    const index = area.children.findIndex(
      (child) => child && child.type === "tab-area" && Array.isArray(child.widgets) && child.widgets.includes(widget),
    );
    if (index >= 0) return { node: area, index };
  }
  for (const child of area.children) {
    const found = findSplit(child, widget);
    if (found) return found;
  }
  return null;
}

/** `resources()` is non-empty (an array, or an object with keys). */
function nonEmpty(resources) {
  if (resources === null || resources === undefined) return false;
  if (typeof resources.length === "number") return resources.length > 0;
  if (typeof resources === "object") return Object.keys(resources).length > 0;
  return false;
}

function viewerId(value) {
  return typeof value === "string" && value.length > 0 && value.length <= MAX_ID ? value : null;
}

// -- the controller -------------------------------------------------------------------------------------------------------

/**
 * Mount the deck panel.
 *
 * @param {object} opts
 * @param opts.app          the app handle (`window.jupyterapp`)
 * @param opts.win          the window (`document`, `BroadcastChannel`, `innerWidth`, ...)
 * @param opts.logger       console-like; defaults to `console`
 * @param opts.controllers  what earlier modules returned (unused; kept for the mount contract)
 * @param opts.baseUrl      the dist root the iframe `src` is resolved against; defaults to
 *                          two directories above this module (`<dist>/shell/display/`)
 * @returns {{
 *   state(): string, snapshot(): object, focus(name: string): boolean, toggle(): void,
 *   open(): void, close(): void, sizing: object, dispose(): void,
 * }}
 */
export function mountDock({ app, win, logger = console, controllers, baseUrl } = {}) {
  void controllers;
  const doc = win ? win.document : undefined;
  const base = typeof baseUrl === "string" && baseUrl ? baseUrl : defaultBase();
  const disposers = [];
  const panels = new Map(); // notebook panel -> {panel, kernelPresent, disposers}
  const viewerPanel = new Map(); // viewer id -> notebook panel (D11, kernel restart)

  let state = "closed";
  let seen = false;
  let current = null;
  let preset = "top";
  let follow = true;
  let connected = null;
  let focused = null;
  let home = null; // "split" | "drawer" | null (closed)
  let tier = "drawer";
  let widget = null;
  let dom = null;
  let channel = null;
  let resizeObserver = null;
  let pollTimer = null;
  let refPanel = null;
  let selfClosing = false;
  let attaching = false;
  let sizing = false;
  let disposed = false;

  // -- reporting (never throws) ---------------------------------------------------------------------------------

  function report(label, err) {
    try {
      logger.error(`praxis display dock: ${label} failed:`, err);
    } catch {
      // A broken logger must not break the shell either.
    }
  }

  function note(message) {
    try {
      logger.warn(`praxis display dock: ${message}`);
    } catch {
      // ignore
    }
  }

  function guarded(label, fn) {
    return (...args) => {
      if (disposed) return undefined;
      try {
        return fn(...args);
      } catch (err) {
        report(label, err);
        return undefined;
      }
    };
  }

  function connectSignal(signal, slot) {
    if (!signal || typeof signal.connect !== "function") return () => {};
    signal.connect(slot);
    return () => {
      try {
        if (typeof signal.disconnect === "function") signal.disconnect(slot);
      } catch (err) {
        report("disconnect", err);
      }
    };
  }

  function listen(target, type, handler, options) {
    if (!target || typeof target.addEventListener !== "function") return;
    target.addEventListener(type, handler, options);
    disposers.push(() => {
      if (typeof target.removeEventListener === "function") target.removeEventListener(type, handler, options);
    });
  }

  // -- the window -------------------------------------------------------------------------------------------------------

  function currentWidth() {
    const w = win ? win.innerWidth : undefined;
    if (typeof w === "number" && w > 0) return w;
    const root = doc && doc.documentElement;
    return root && typeof root.clientWidth === "number" ? root.clientWidth : 0;
  }

  // -- the panel DOM ---------------------------------------------------------------------------------------------------

  function element(tag, className) {
    const el = doc.createElement(tag);
    if (className) el.classList.add(className);
    return el;
  }

  function button(label, className) {
    const el = element("button", className);
    el.setAttribute("type", "button");
    el.textContent = label;
    return el;
  }

  function buildDom() {
    if (!doc) throw new Error("dock: there is no document to build the deck panel in");
    const node = element("div", "praxis-deck-panel");
    node.setAttribute("data-praxis-deck-state", state);

    const header = element("div", "praxis-deck-panel__header");
    const title = element("span", "praxis-deck-panel__title");
    title.textContent = "Deck";
    const followButton = button("Follow", "praxis-deck-panel__follow");
    followButton.setAttribute("role", "switch");
    followButton.setAttribute("aria-checked", String(follow));
    const views = element("div", "praxis-deck-panel__views");
    views.setAttribute("role", "group");
    views.setAttribute("aria-label", "View");
    const viewButtons = new Map();
    for (const name of PRESETS) {
      const b = button(name[0].toUpperCase() + name.slice(1));
      b.setAttribute("aria-pressed", String(name === preset));
      views.appendChild(b);
      viewButtons.set(name, b);
    }
    const close = button("×", "praxis-deck-panel__close");
    close.setAttribute("aria-label", "Close the deck panel");
    Object.assign(close.style, { marginLeft: "8px", border: "0", background: "none", color: "inherit", font: "inherit", cursor: "pointer" });
    header.appendChild(title);
    header.appendChild(followButton);
    header.appendChild(views);
    header.appendChild(close);

    const body = element("div", "praxis-deck-panel__body");
    Object.assign(body.style, {
      flex: "1 1 auto",
      minHeight: "300px",
      display: "flex",
      flexDirection: "column",
      position: "relative",
      overflow: "hidden",
    });
    const text = element("div", "praxis-deck-panel__text");
    text.setAttribute("role", "status");
    Object.assign(text.style, { padding: "16px", fontSize: "14px", color: "var(--jp-content-font-color2)" });

    const footer = element("div", "praxis-deck-panel__footer");
    Object.assign(footer.style, { flex: "0 1 auto", minHeight: "0", overflow: "hidden" });
    const focusLine = doc.createElement("span");
    focusLine.setAttribute("data-praxis-deck-focus", "");
    focusLine.textContent = NO_FOCUS_TEXT;
    const motion = element("div", "praxis-deck-panel__motion");
    motion.textContent = MOTION_TEXT;
    motion.setAttribute("aria-disabled", "true");
    Object.assign(motion.style, { maxHeight: "36px", overflow: "hidden", flexShrink: "1" });
    footer.appendChild(focusLine);
    footer.appendChild(motion);

    node.appendChild(header);
    node.appendChild(body);
    node.appendChild(footer);

    followButton.addEventListener("click", guarded("follow toggle", () => setFollow(!follow)));
    for (const [name, b] of viewButtons) b.addEventListener("click", guarded("view preset", () => setPreset(name)));
    close.addEventListener("click", guarded("close button", () => closePanel()));
    node.addEventListener(
      "keydown",
      guarded("keydown", (event) => {
        // Escape hides the drawer while focus is in it (D6). Nowhere else.
        if (event && event.key === "Escape" && home === "drawer" && state !== "closed") closePanel();
      }),
    );
    return { node, title, followButton, viewButtons, close, body, text, focusLine };
  }

  function ensureWidget() {
    if (widget && !widget.isDisposed) return widget;
    const shell = app && app.shell;
    const Root = findRootConstructor(shell);
    if (!Root) {
      throw new Error(
        "dock: cannot find the root Lumino Widget class from any shell widget (S1-A); the deck panel cannot be built",
      );
    }
    const Deck = class PraxisDeckWidget extends Root {
      onCloseRequest(message) {
        if (typeof super.onCloseRequest === "function") super.onCloseRequest(message);
        guarded("tab close", () => onWidgetClosed(this))();
      }
    };
    if (!dom || widget) dom = buildDom(); // a first build, or a rebuild after the widget was disposed
    const w = new Deck({ node: dom.node });
    w.id = WIDGET_ID;
    if (w.title) {
      w.title.label = "Deck";
      w.title.closable = true;
    }
    disposers.push(connectSignal(w.disposed, guarded("widget disposed", () => onWidgetGone(w))));
    widget = w;
    syncChrome();
    return w;
  }

  function syncChrome() {
    if (!dom) return;
    dom.followButton.setAttribute("aria-checked", String(follow));
    for (const [name, b] of dom.viewButtons) b.setAttribute("aria-pressed", String(name === preset));
    dom.close.style.display = home === "drawer" ? "" : "none";
    dom.focusLine.textContent = focused === null ? NO_FOCUS_TEXT : focused;
  }

  function setTitle(deck) {
    if (!dom) return;
    const name = typeof deck === "string" && deck.trim() ? deck.trim().slice(0, MAX_TITLE) : "Deck";
    dom.title.textContent = name;
  }

  function setFocused(name) {
    focused = name;
    if (dom) dom.focusLine.textContent = name === null ? NO_FOCUS_TEXT : name;
  }

  /** Set the state and make the body text agree with it (I5). */
  function setState(next) {
    state = next;
    if (!dom) return;
    dom.node.setAttribute("data-praxis-deck-state", next);
    if (next === "open-waiting") showText(NO_VIEWER_TEXT);
    else if (next === "open-lost") showText(LOST_TEXT);
    else hideText();
  }

  function showText(message) {
    dom.text.textContent = message;
    if (dom.text.parentNode !== dom.body) dom.body.appendChild(dom.text);
  }

  function hideText() {
    if (dom.text.parentNode) dom.text.parentNode.removeChild(dom.text);
  }

  // -- the iframe -------------------------------------------------------------------------------------------------------

  /** Every iframe in the panel DOM, read at call time (I1: at most one, only in open-connected). */
  function framesIn() {
    const out = [];
    if (!dom) return out;
    const visit = (el) => {
      for (const child of Array.from(el.children || [])) {
        if (child && child.localName === "iframe") out.push(child);
        visit(child);
      }
    };
    visit(dom.node);
    return out;
  }

  /** A NEW iframe whose `src` is already set (it loads the right page the moment it is inserted). */
  function makeFrame(id) {
    const frame = doc.createElement("iframe");
    frame.classList.add("praxis-deck-panel__frame");
    frame.setAttribute("title", "Deck viewer");
    Object.assign(frame.style, { flex: "1 1 auto", width: "100%", minHeight: "300px", border: "0" });
    frame.addEventListener("load", guarded("iframe load", () => startPresetPoll()));
    frame.setAttribute("src", viewerSrc(base, id));
    return frame;
  }

  function setSrc(frame, id) {
    frame.setAttribute("src", viewerSrc(base, id));
  }

  function removeFrames() {
    stopPresetPoll();
    for (const frame of framesIn()) {
      try {
        frame.remove();
      } catch (err) {
        report("remove the iframe", err);
      }
    }
  }

  /** The page's `window.plrViewer` in the iframe currently in the panel (D12), or null. */
  function plrViewer() {
    const [frame] = framesIn();
    if (!frame) return null;
    try {
      const viewer = frame.contentWindow ? frame.contentWindow.plrViewer : undefined;
      return viewer && typeof viewer === "object" ? viewer : null;
    } catch {
      return null; // not same-origin yet, or the page is being replaced
    }
  }

  // -- D12: the preset, Follow, focus -------------------------------------------------------------------------------

  function stopPresetPoll() {
    if (pollTimer !== null && win && typeof win.clearInterval === "function") win.clearInterval(pollTimer);
    pollTimer = null;
  }

  /** Apply the held preset once the page has a `plrViewer` AND `resources()` is non-empty. True when
   * there is nothing more to wait for. */
  function tryApplyPreset() {
    if (state !== "open-connected") return true;
    const viewer = plrViewer();
    if (!viewer || typeof viewer.resources !== "function" || typeof viewer.view !== "function") return false;
    let resources;
    try {
      resources = viewer.resources();
    } catch {
      return false;
    }
    if (!nonEmpty(resources)) return false;
    try {
      viewer.view(preset);
    } catch (err) {
      report("re-apply the preset", err);
    }
    return true;
  }

  /** After every load of the panel's iframe (T2, T6, T11, T15, T16, T18): poll every 250 ms, give up after 10 s. */
  function startPresetPoll() {
    stopPresetPoll();
    if (tryApplyPreset()) return;
    if (!win || typeof win.setInterval !== "function") return;
    let attempts = 0;
    pollTimer = win.setInterval(
      guarded("preset poll", () => {
        attempts += 1;
        if (tryApplyPreset() || attempts >= POLL_MAX) stopPresetPoll();
      }),
      POLL_MS,
    );
  }

  function setPreset(name) {
    if (!PRESETS.includes(name)) return;
    preset = name;
    syncChrome();
    if (state !== "open-connected") return; // Iso / Top / Front only update the held preset elsewhere
    const viewer = plrViewer();
    if (viewer && typeof viewer.view === "function") {
      try {
        viewer.view(name);
      } catch (err) {
        report("view", err);
      }
    }
  }

  function setFollow(on) {
    follow = Boolean(on);
    syncChrome();
  }

  /** Focus a resource on the page with the held preset (never `focus(name)`, whose default would override it). */
  function focus(name) {
    if (typeof name !== "string" || name === "") return false;
    if (state !== "open-connected") return false;
    const viewer = plrViewer();
    if (!viewer || typeof viewer.focus !== "function") return false;
    try {
      viewer.focus(name, preset);
    } catch (err) {
      report("focus", err);
      return false;
    }
    setFocused(name);
    return true;
  }

  /** The resource stamped on the first output of the cell whose stamp names one (D12 Follow). */
  function firstResource(cell) {
    const outputs = cell && cell.model ? cell.model.outputs : undefined;
    if (!outputs || typeof outputs.get !== "function") return null;
    for (let i = 0; i < outputs.length; i += 1) {
      const resource = own(stampOf(outputs.get(i)), "resource");
      if (typeof resource === "string" && resource !== "") return resource;
    }
    return null;
  }

  function onActiveCellChanged(panel, cell) {
    if (!follow || state !== "open-connected") return;
    const active = cell && typeof cell === "object" ? cell : panel.content ? panel.content.activeCell : null;
    const name = firstResource(active);
    if (name !== null) focus(name);
  }

  // -- attaching: the split and the drawer ---------------------------------------------------------------------------

  function mainDock() {
    const parent = widget ? widget.parent : null;
    if (parent && typeof parent.saveLayout === "function" && typeof parent.restoreLayout === "function") return parent;
    const shell = app && app.shell;
    const viaShell = shell ? shell._dockPanel : undefined; // S1: the accessor, capability-checked
    if (viaShell && typeof viaShell.saveLayout === "function" && typeof viaShell.restoreLayout === "function") return viaShell;
    return null;
  }

  function referencePanel() {
    const shell = app && app.shell;
    if (shell && isNotebookPanel(shell.currentWidget)) return shell.currentWidget;
    if (refPanel && !refPanel.isDisposed) return refPanel;
    for (const entry of panels.values()) return entry.panel;
    return null;
  }

  function notebookPadding() {
    const panel = referencePanel();
    const el = panel ? (panel.content && panel.content.node) || panel.node : null;
    if (!el || !win || typeof win.getComputedStyle !== "function") return 0;
    try {
      const style = win.getComputedStyle(el);
      return (parseFloat(style.paddingLeft) || 0) + (parseFloat(style.paddingRight) || 0);
    } catch {
      return 0;
    }
  }

  function setLimits() {
    widget.node.style.minWidth = `${MIN_PANEL}px`;
    widget.node.style.maxWidth = `${MAX_PANEL}px`;
  }

  function clearLimits() {
    widget.node.style.minWidth = "";
    widget.node.style.maxWidth = "";
  }

  /** `parent.fit()`: Lumino re-reads the size limits (S1: css_limits_refit). */
  function fitParent() {
    const parent = widget ? widget.parent : null;
    if (!parent || typeof parent.fit !== "function") return;
    try {
      parent.fit();
    } catch (err) {
      report("parent.fit()", err);
    }
  }

  /** >= 1600: saveLayout -> edit the split area's sizes -> restoreLayout (S1: reachable; keeps the iframe). */
  function layoutSize() {
    const dock = mainDock();
    if (!dock || !dock.node) return;
    const rect = typeof dock.node.getBoundingClientRect === "function" ? dock.node.getBoundingClientRect() : null;
    const main = rect ? rect.width : 0;
    if (!(main > 0)) return;
    const config = dock.saveLayout();
    const split = findSplit(config ? config.main : null, widget);
    if (!split) return; // the user moved the deck out of a horizontal split: leave it to Lumino
    const target = Math.min(main * 0.9, panelWidth(main, notebookPadding()));
    const fraction = target / main;
    const sizes = split.node.sizes.slice();
    const total = sizes.reduce((a, b) => a + b, 0) || 1;
    if (Math.abs(sizes[split.index] / total - fraction) < 0.002) return;
    const others = total - sizes[split.index];
    const next = sizes.map((s, i) => {
      if (i === split.index) return fraction;
      return others > 0 ? (s / others) * (1 - fraction) : (1 - fraction) / (sizes.length - 1);
    });
    split.node.sizes = next;
    sizing = true;
    try {
      dock.restoreLayout(config);
    } finally {
      sizing = false;
    }
  }

  /** Size the panel for the tier it is in. `reason`: "open", "tier" (a 1600 crossing or a re-home), or "resize"
   * (a ResizeObserver callback, only ever at >= 1600: the 1280-1599 clamp is CSS and needs no callback). */
  function applySizing(reason) {
    if (home !== "split" || !widget) return;
    if (tier === "medium") {
      setLimits(); // 1280-1599: CSS limits do the clamping, also for a splitter drag
      fitParent();
      return;
    }
    clearLimits(); // no maximum at >= 1600
    if (reason !== "resize") fitParent();
    layoutSize();
  }

  function observeDock() {
    stopObserving();
    const dock = mainDock();
    const Observer = win ? win.ResizeObserver : undefined;
    if (typeof Observer !== "function" || !dock || !dock.node) return;
    resizeObserver = new Observer(guarded("resize observer", () => onDockResized()));
    resizeObserver.observe(dock.node);
  }

  function stopObserving() {
    if (resizeObserver) {
      try {
        resizeObserver.disconnect();
      } catch (err) {
        report("disconnect the resize observer", err);
      }
    }
    resizeObserver = null;
  }

  function onDockResized() {
    if (sizing || state === "closed" || home !== "split") return;
    evaluateTier();
    if (home === "split" && tier === "wide") applySizing("resize");
  }

  function drawerBox() {
    let top = "0";
    let bottom = "0";
    try {
      const dockNode = doc && typeof doc.getElementById === "function" ? doc.getElementById("jp-main-dock-panel") : null;
      const rect = dockNode ? dockNode.getBoundingClientRect() : null;
      if (rect && rect.height > 0 && win && typeof win.innerHeight === "number") {
        top = `${rect.top}px`;
        bottom = `${Math.max(0, win.innerHeight - rect.bottom)}px`;
      }
    } catch {
      // fall back to the whole window height
    }
    return { top, bottom };
  }

  const DRAWER_STYLE = ["position", "top", "right", "bottom", "width", "zIndex", "boxShadow"];

  function applyDrawerStyle() {
    const { top, bottom } = drawerBox();
    Object.assign(widget.node.style, {
      position: "fixed",
      top,
      right: "0",
      bottom,
      width: `${MAX_PANEL}px`,
      zIndex: "900",
      boxShadow: "0 0 12px rgba(0, 0, 0, 0.25)",
    });
    clearLimits();
  }

  function clearDrawerStyle() {
    for (const key of DRAWER_STYLE) widget.node.style[key] = "";
  }

  /** Attach the panel (with whatever it holds) in `target`: "split" or "drawer". False when it could not be. */
  function attach(target) {
    attaching = true;
    try {
      ensureWidget();
      if (target === "drawer") {
        applyDrawerStyle();
        doc.body.appendChild(widget.node);
      } else {
        clearDrawerStyle();
        if (widget.node.parentNode) widget.node.parentNode.removeChild(widget.node);
        if (tier === "medium") setLimits();
        else clearLimits();
        const reference = referencePanel();
        const options = { mode: "split-right", activate: false };
        if (reference && reference.id) options.ref = reference.id;
        app.shell.add(widget, "main", options);
        refPanel = reference;
      }
      home = target;
      syncChrome();
    } catch (err) {
      report("attach the deck panel", err);
      try {
        if (widget && widget.node.parentNode) widget.node.parentNode.removeChild(widget.node);
      } catch {
        // already gone
      }
      home = null;
      return false;
    } finally {
      attaching = false;
    }
    if (target === "split") {
      // The panel IS in the shell now; a sizing failure is reported but never undoes the attach.
      try {
        observeDock();
        applySizing("open");
      } catch (err) {
        report("size the deck panel", err);
      }
    }
    return true;
  }

  /** Take the panel out of the shell, keeping what it holds (state is untouched). */
  function detachPanel() {
    selfClosing = true;
    try {
      stopObserving();
      if (widget && home === "split" && (widget.parent || widget.isAttached)) widget.close();
      if (widget && widget.node.parentNode) widget.node.parentNode.removeChild(widget.node);
    } catch (err) {
      report("detach the deck panel", err);
    } finally {
      selfClosing = false;
      home = null;
    }
  }

  function onWidgetClosed(closed) {
    if (disposed || selfClosing || closed !== widget || home !== "split") return;
    closePanel(); // the split tab was closed (close panel)
  }

  function onWidgetGone(gone) {
    if (gone !== widget) return;
    widget = null;
    if (!disposed && !selfClosing && state !== "closed") closePanel();
  }

  // -- D11: the events -------------------------------------------------------------------------------------------------

  function syncTier() {
    tier = tierOf(currentWidth());
  }

  function postQuery() {
    if (!channel) return;
    try {
      channel.postMessage(JSON.stringify({ kind: "query" }));
    } catch (err) {
      report("post query", err);
    }
  }

  /** Something outside the shell stopped the connection to the page: go where a stopped viewer goes. */
  function toWaiting() {
    removeFrames();
    current = null;
    connected = null;
    setFocused(null);
    setState("open-waiting");
  }

  function toLost() {
    removeFrames();
    connected = null;
    setFocused(null);
    setState("open-lost");
  }

  /** T2 / T6 / T18: attach if needed, then create ONE new iframe carrying the viewer id. */
  function connectTo(id, deck, attachTarget) {
    let frame;
    try {
      frame = makeFrame(id);
    } catch (err) {
      report("create the deck iframe", err);
      return;
    }
    if (attachTarget !== null && !attach(attachTarget)) return;
    removeFrames();
    setTitle(deck);
    setState("open-connected");
    dom.body.appendChild(frame);
    current = id;
    connected = null;
    setFocused(null);
  }

  /** T11: the panel shows another viewer; the iframe in the panel gets the new src. */
  function retarget(id, deck) {
    const [frame, ...extra] = framesIn();
    if (!frame) {
      connectTo(id, deck, null);
      return;
    }
    for (const stray of extra) stray.remove();
    setSrc(frame, id);
    setTitle(deck);
    current = id;
    connected = null;
    setFocused(null);
  }

  function recordViewerPanel(id) {
    scanPanels();
    const running = [];
    for (const entry of panels.values()) {
      const cells = entry.panel.content ? Array.from(entry.panel.content.widgets || []) : [];
      if (cells.some((cell) => cell && cell.model && cell.model.type === "code" && isRunning(cell.model))) {
        running.push(entry.panel);
      }
    }
    if (running.length === 1) viewerPanel.set(id, running[0]);
  }

  function onAnnounce(id, deck) {
    recordViewerPanel(id);
    const first = !seen;
    seen = true;
    switch (state) {
      case "closed":
        if (first) {
          syncTier();
          connectTo(id, deck, homeOf(tier)); // T2
        }
        return; // T3 otherwise
      case "open-waiting": // T6
      case "open-lost": // T18
        connectTo(id, deck, null);
        return;
      default: // open-connected
        if (id !== current) retarget(id, deck); // T11; T27 when the id is the current one
    }
  }

  function onKernelClose(id) {
    if ((state === "open-connected" || state === "open-lost") && id === current) toWaiting(); // T12, T19
  }

  function onDockStatus(event) {
    const detail = event ? event.detail : undefined;
    if (!detail || typeof detail !== "object") return;
    const viewer = typeof detail.viewer === "string" ? detail.viewer : null;
    if (viewer === null || viewer !== current) return; // a page the panel no longer shows
    if (detail.event === "plr:gone") {
      if (state === "open-connected") toLost(); // T14; ignored everywhere else (I4)
    } else if (detail.event === "plr:status" && typeof detail.connected === "boolean") {
      connected = detail.connected;
    }
  }

  function reopen() {
    syncTier();
    if (!attach(homeOf(tier))) return;
    current = null;
    setState("open-waiting"); // T4
    postQuery();
  }

  function closePanel() {
    if (state === "closed") return; // T5
    removeFrames();
    detachPanel();
    current = null;
    connected = null;
    setFocused(null);
    setState("closed"); // T7, T17, T22
  }

  function toggle() {
    if (state === "closed") reopen();
    else closePanel();
  }

  /** Re-home an open panel between split and drawer (T10, T15, T21), state and iframe intact. */
  function rehome() {
    if (state === "closed") return;
    const target = homeOf(tier);
    if (home === target) return;
    detachPanel();
    if (!attach(target)) {
      note("could not re-home the deck panel after a tier change; closing it");
      removeFrames();
      current = null;
      setFocused(null);
      setState("closed");
    }
  }

  function evaluateTier() {
    const next = tierOf(currentWidth());
    if (next === tier) return;
    const previous = tier;
    tier = next;
    if (state === "closed") return; // T5
    if (homeOf(previous) !== homeOf(next)) rehome(); // the 1280 crossing is a lifecycle event
    else if (home === "split") applySizing("tier"); // a 1600 crossing only re-sizes the split
  }

  // -- the viewer's kernel (kernel restart, T23-T26) -----------------------------------------------------------------

  function hasKernel(panel) {
    const context = panel ? panel.sessionContext : undefined;
    return Boolean(context && context.session && context.session.kernel);
  }

  /** Is `entry`'s panel the viewer's kernel's panel? `viewerPanel[current]`, else the only panel with a kernel. */
  function ownsViewer(entry, hadKernel) {
    const mapped = current !== null ? viewerPanel.get(current) : undefined;
    if (mapped) return mapped === entry.panel;
    let count = 0;
    let only = null;
    for (const other of panels.values()) {
      if (other === entry ? hadKernel : hasKernel(other.panel)) {
        count += 1;
        only = other;
      }
    }
    return count === 1 && only === entry;
  }

  function onKernelSignal(entry) {
    const hadKernel = entry.kernelPresent;
    entry.kernelPresent = hasKernel(entry.panel);
    const fires = (state === "open-connected" || state === "open-lost") && ownsViewer(entry, hadKernel);
    if (fires) toWaiting(); // T25, T26
  }

  function trackPanel(panel) {
    if (panels.has(panel)) return;
    const entry = { panel, kernelPresent: hasKernel(panel), disposers: [] };
    panels.set(panel, entry);
    const context = panel.sessionContext;
    if (context) {
      entry.disposers.push(
        connectSignal(
          context.statusChanged,
          guarded("kernel status", (_sender, status) => {
            if (RESTART_STATUSES.has(status)) onKernelSignal(entry);
            else entry.kernelPresent = hasKernel(panel);
          }),
        ),
        connectSignal(
          context.kernelChanged,
          guarded("kernel changed", (_sender, args) => {
            if (own(args, "oldValue") === own(args, "newValue")) return;
            onKernelSignal(entry);
          }),
        ),
      );
    }
    if (panel.content) {
      entry.disposers.push(
        connectSignal(
          panel.content.activeCellChanged,
          guarded("active cell", (_sender, cell) => onActiveCellChanged(panel, cell)),
        ),
      );
    }
    entry.disposers.push(
      connectSignal(
        panel.disposed,
        guarded("panel disposed", () => {
          for (const dispose of entry.disposers.splice(0)) dispose();
          panels.delete(panel);
          for (const [id, mapped] of Array.from(viewerPanel)) if (mapped === panel) viewerPanel.delete(id);
        }),
      ),
    );
  }

  function scanPanels() {
    const shell = app && app.shell;
    if (!shell || typeof shell.widgets !== "function") return;
    for (const candidate of Array.from(shell.widgets("main"))) {
      if (isNotebookPanel(candidate)) guarded("track panel", trackPanel)(candidate);
    }
  }

  function onLayoutModified() {
    scanPanels();
    // A tab closed some other way than through onCloseRequest: the widget has no parent any more.
    if (!attaching && !selfClosing && state !== "closed" && home === "split" && widget && !widget.parent) closePanel();
  }

  // -- the channel ----------------------------------------------------------------------------------------------------------

  function handleMessage(data) {
    if (typeof data !== "string" || data.length > MAX_MESSAGE) return;
    let message;
    try {
      message = JSON.parse(data);
    } catch {
      return;
    }
    if (message === null || typeof message !== "object" || Array.isArray(message)) return;
    const id = viewerId(message.viewer);
    if (id === null) return;
    switch (message.kind) {
      case "announce":
        onAnnounce(id, message.deck);
        return;
      case "close":
        onKernelClose(id);
        return;
      default: // open, accept, msg, bye, evict, query: not the shell's
    }
  }

  // -- mount --------------------------------------------------------------------------------------------------------------

  syncTier();
  if (!doc) note("the window has no document; the deck panel cannot be shown.");

  const Channel = win ? win.BroadcastChannel : undefined;
  if (typeof Channel !== "function") {
    note("no BroadcastChannel; the deck panel will not hear the viewer.");
  } else {
    try {
      channel = new Channel(CHANNEL);
      const onMessage = guarded("channel message", (event) => handleMessage(event ? event.data : undefined));
      if (typeof channel.addEventListener === "function") {
        channel.addEventListener("message", onMessage);
        disposers.push(() => channel.removeEventListener("message", onMessage));
      } else {
        channel.onmessage = onMessage;
      }
      disposers.push(() => channel.close());
    } catch (err) {
      channel = null;
      report("open the praxis_viz3d channel", err);
    }
  }

  listen(win, DOCK_STATUS_EVENT, guarded("dock status", onDockStatus));
  listen(win, "resize", guarded("window resize", evaluateTier));

  const shell = app ? app.shell : undefined;
  if (shell) {
    disposers.push(connectSignal(shell.currentChanged, guarded("shell changed", scanPanels)));
    disposers.push(connectSignal(shell.layoutModified, guarded("layout modified", onLayoutModified)));
  }
  guarded("scan panels", scanPanels)();

  const commands = app ? app.commands : undefined;
  if (commands && typeof commands.addCommand === "function") {
    if (typeof commands.hasCommand === "function" && commands.hasCommand(TOGGLE_COMMAND)) {
      note(`the command ${TOGGLE_COMMAND} is already registered; leaving it to its owner.`);
    } else {
      try {
        const registration = commands.addCommand(TOGGLE_COMMAND, {
          label: "Toggle Deck Panel",
          caption: "Show or hide the deck panel",
          execute: guarded("toggle command", toggle),
        });
        if (registration && typeof registration.dispose === "function") disposers.push(() => registration.dispose());
      } catch (err) {
        report("register the toggle command", err);
      }
    }
  }

  postQuery(); // T1

  return {
    sizing: SIZING,
    state: () => state,
    snapshot: () => ({ state, seen, current, preset, follow, home, tier, focused, connected }),
    focus: (name) => {
      try {
        return focus(name);
      } catch (err) {
        report("focus", err);
        return false;
      }
    },
    toggle: guarded("toggle", toggle),
    open: guarded("open", () => {
      if (state === "closed") reopen();
    }),
    close: guarded("close", closePanel),
    dispose() {
      if (disposed) return;
      disposed = true;
      stopPresetPoll();
      stopObserving();
      selfClosing = true;
      try {
        if (widget && (widget.parent || widget.isAttached)) widget.close();
        if (widget && widget.node.parentNode) widget.node.parentNode.removeChild(widget.node);
      } catch (err) {
        report("close the deck panel", err);
      }
      for (const entry of panels.values()) for (const dispose of entry.disposers.splice(0)) dispose();
      panels.clear();
      viewerPanel.clear();
      for (const dispose of disposers.splice(0).reverse()) {
        try {
          dispose();
        } catch (err) {
          report("dispose", err);
        }
      }
    },
  };
}
