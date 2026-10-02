// stale.js -- staleness marks in the notebook DOM (spec
// .praxia/docs/specs/260929_notebook-display-epic.md D7 "Marking", "Current
// session, per notebook panel" and "Marks survive re-rendering", D2 "One stamp
// reader", D14, section 4 stale.js row, AC-19; task B9).
//
// Two notices are written into an output's DOM, never into the notebook model
// (so they are never saved):
//
//   "Changed since, see deck panel."   the output's stamp has a non-null `rev`
//        older than the latest rev the kernel announced for the same
//        (session, resource). Outputs stamped `rev: null` (ledger, error) are
//        never marked this way.
//   "Drawn in an earlier session."     the output's stamp session is not its
//        panel's current session. The current session is per notebook panel
//        (`panelSession`, below) and is not known until the panel has an
//        observed execution of a stamped cell after its kernel last started, so
//        a restored, never-executed panel writes none.
//
// WHERE THE FACTS COME FROM
//   * Stamps are read from the MODEL through `stampOf` (D2), the one stamp
//     reader; the DOM's `data-*` is never read here (S2: an untrusted reopen
//     strips it, the stamp survives in the model).
//   * Announcements arrive on BroadcastChannel `praxis_repl` as
//     {type: "praxis:resource-changed", json} (B7 stale.py): json is
//     {"session","exec","revs":{name:rev}} (<= 4096 bytes) or
//     {"session","exec","all":true}. Nothing else is read from that channel.
//   * `panelSession[P]` is the stamp session of the newest stamped output of a
//     cell whose execution chrome.js observed in this page after P's kernel
//     last started (P's sessionContext kernelChanged / statusChanged reset it).
//     chrome.js's events are filtered on `phase === "finished"`.
//
// MARKS SURVIVE RE-RENDERING. Nothing here holds a DOM node: the state is the rev
// tracker and each panel's session; the marks are re-derived from it and written
// idempotently (at most one mark per kind per output) on each cell's
// `outputs.changed`, on `inViewportChanged` (subscribed only when chrome.js's
// `windowing(panel)` says the panel's windowing mode needs it; S1: the notebook
// runs contentVisibility, where cells are never detached), on `activeCellChanged`,
// on every announcement and whenever a panel's session changes.
//
// Model outputs map to DOM nodes by index: `cell.outputArea.widgets[i].node` is
// the node of `cell.model.outputs.get(i)` (the model-first pattern of
// repl_smoke.py); the mark goes into that node's `.jp-OutputArea-output` element.
//
// FAILURE CONTAINMENT. Every signal handler, every panel, every cell, every
// output and the channel handler run under their own try/catch; a failure is
// logged with `logger.error` and stops nothing else. A malformed announcement
// is dropped silently. Nothing here throws out of `mountStale`'s handlers, and
// nothing writes to the model.

import { windowingModeOf } from "./chrome.js";

export const CHANNEL = "praxis_repl";
export const MESSAGE_TYPE = "praxis:resource-changed";
/** The kernel's cap on the announcement's `json` field, in bytes (B7 JSON_CAP). */
export const MAX_JSON = 4096;

export const CHANGED_TEXT = "Changed since, see deck panel.";
export const EARLIER_TEXT = "Drawn in an earlier session.";
export const MARK_CLASS = "praxis-stale";
export const MARK_ATTR = "data-praxis-stale";
const KIND_CHANGED = "changed";
const KIND_EARLIER = "earlier-session";

const CONTENT_VISIBILITY = "contentVisibility";
/** Session-context statuses that mean a kernel (re)started. */
const RESTART_STATUSES = new Set(["starting", "restarting", "autorestarting"]);

const hasOwn = Object.prototype.hasOwnProperty;

/** `obj[key]` for an OWN property of an object, else undefined (no prototype reads). */
function own(obj, key) {
  return obj !== null && typeof obj === "object" && hasOwn.call(obj, key) ? obj[key] : undefined;
}

const isCount = (value) => Number.isSafeInteger(value) && value >= 0;

// -- D2: the one stamp reader ----------------------------------------------------------------

/**
 * The stamp of a model output: `metadata.praxis` (S3-A) or, when the kernel
 * could only attach it to the `text/html` formatter, `metadata["text/html"].praxis`
 * (S3-B). Only own properties are read; anything unreadable gives undefined.
 */
export function stampOf(output) {
  try {
    const metadata = output === null || output === undefined ? undefined : output.metadata;
    return own(metadata, "praxis") ?? own(own(metadata, "text/html"), "praxis");
  } catch {
    return undefined;
  }
}

// -- the announcement ----------------------------------------------------------------------------

/**
 * Parse a `praxis:resource-changed` message. Returns
 * `{session, exec, revs: Map<name, rev>, all}` or null for anything malformed
 * (wrong type, no or oversize `json`, bad JSON, no session, neither `revs` nor
 * `all: true`). Entries of `revs` whose value is not a non-negative integer are
 * dropped. Never throws.
 */
export function parseAnnouncement(data) {
  try {
    if (data === null || typeof data !== "object") return null;
    if (data.type !== MESSAGE_TYPE) return null;
    const text = data.json;
    if (typeof text !== "string" || text.length > MAX_JSON) return null;
    const body = JSON.parse(text);
    if (body === null || typeof body !== "object" || Array.isArray(body)) return null;

    const session = own(body, "session");
    if (typeof session !== "string" || session === "") return null;
    const rawExec = own(body, "exec");
    const exec = isCount(rawExec) ? rawExec : null;
    const all = own(body, "all") === true;

    const revs = new Map();
    const rawRevs = own(body, "revs");
    if (rawRevs !== undefined) {
      if (rawRevs === null || typeof rawRevs !== "object" || Array.isArray(rawRevs)) return null;
      for (const [name, rev] of Object.entries(rawRevs)) {
        if (isCount(rev)) revs.set(name, rev);
      }
    } else if (!all) {
      return null;
    }
    return { session, exec, revs, all };
  } catch {
    return null;
  }
}

/**
 * The latest announced rev per (session, resource), and the `all: true`
 * announcements per session. State is in Maps only (names are user-controlled).
 */
export function createRevTracker() {
  const latest = new Map(); // session -> Map(resource name -> rev)
  const alls = new Map(); //   session -> {unknown: boolean, maxExec: number}

  return {
    apply(announcement) {
      if (!announcement) return;
      const { session, exec, revs, all } = announcement;
      if (revs && revs.size > 0) {
        let byName = latest.get(session);
        if (!byName) {
          byName = new Map();
          latest.set(session, byName);
        }
        for (const [name, rev] of revs) {
          const known = byName.get(name);
          if (known === undefined || rev > known) byName.set(name, rev);
        }
      }
      if (all) {
        let record = alls.get(session);
        if (!record) {
          record = { unknown: false, maxExec: -1 };
          alls.set(session, record);
        }
        if (exec === null) record.unknown = true;
        else if (exec > record.maxExec) record.maxExec = exec;
      }
    },

    /** True when `stamp` has a non-null `rev` and the kernel announced a newer
     * state of its resource in its session. Never for `rev: null`. */
    isChanged(stamp) {
      if (stamp === null || typeof stamp !== "object") return false;
      const session = own(stamp, "session");
      const resource = own(stamp, "resource");
      const rev = own(stamp, "rev");
      if (typeof session !== "string" || typeof resource !== "string" || !isCount(rev)) return false;

      const known = latest.get(session)?.get(resource);
      if (known !== undefined && known > rev) return true;

      // `all: true` names no resource and no rev: every stamped output of the
      // session drawn BEFORE the announcing cell is marked. The announcing
      // cell's own output and later ones are not (they are at least as new).
      const record = alls.get(session);
      if (record) {
        if (record.unknown) return true;
        const exec = own(stamp, "exec");
        if (!isCount(exec)) return true;
        return exec < record.maxExec;
      }
      return false;
    },
  };
}

// -- the two decisions (pure) ------------------------------------------------------------------------

/** "Changed since": the output's stamp is older than the latest announced rev. */
export function changedSince(stamp, tracker) {
  return tracker.isChanged(stamp);
}

/** "Drawn in an earlier session": only with a known panel session, and only
 * when the stamp's session differs from it. */
export function earlierSession(stamp, panelSession) {
  if (typeof panelSession !== "string") return false;
  const session = own(stamp, "session");
  return typeof session === "string" && session !== panelSession;
}

// -- the DOM writer ------------------------------------------------------------------------------------

function marksOfKind(host, kind) {
  return Array.from(host.children || []).filter(
    (child) => child && typeof child.getAttribute === "function" && child.getAttribute(MARK_ATTR) === kind,
  );
}

/** Ensure exactly one mark of `kind` in `host` when `want`, none otherwise.
 * Idempotent: nothing is touched when the DOM is already right. */
function setMark(doc, host, kind, text, want) {
  const existing = marksOfKind(host, kind);
  if (!want) {
    for (const el of existing) host.removeChild(el);
    return;
  }
  for (const extra of existing.slice(1)) host.removeChild(extra);
  if (existing.length > 0) return;
  const el = doc.createElement("div");
  el.classList.add(MARK_CLASS);
  el.setAttribute(MARK_ATTR, kind);
  el.textContent = text;
  host.appendChild(el);
}

/** The element a mark is written into: the output's own container, so it flows
 * under the rendered output rather than beside JupyterLab's prompt. */
function hostOf(node) {
  if (typeof node.querySelector === "function") {
    const inner = node.querySelector(".jp-OutputArea-output");
    if (inner) return inner;
  }
  return node;
}

function isNotebookPanel(widget) {
  return Boolean(
    widget &&
      widget.content &&
      widget.node &&
      widget.node.classList &&
      widget.node.classList.contains("jp-NotebookPanel"),
  );
}

/** The session of the newest stamped output of a cell, or null. */
function newestSession(cell) {
  const outputs = cell.model.outputs;
  if (!outputs) return null;
  for (let i = outputs.length - 1; i >= 0; i -= 1) {
    const session = own(stampOf(outputs.get(i)), "session");
    if (typeof session === "string" && session !== "") return session;
  }
  return null;
}

// -- the controller ---------------------------------------------------------------------------------------

/**
 * Mount the staleness marks.
 *
 * @param {object} opts
 * @param opts.app          the app handle (`window.jupyterapp`)
 * @param opts.win          the window (`document`, `BroadcastChannel`)
 * @param opts.logger       console-like (`error`, `warn`); defaults to `console`
 * @param opts.controllers  what earlier modules returned; `controllers.chrome`
 *                          supplies observed executions and `windowing(panel)`
 * @returns {{
 *   panelSession(panel): (string|null),
 *   handleMessage(data): boolean,
 *   apply(): void,
 *   scan(): void,
 *   dispose(): void,
 * }}
 */
export function mountStale({ app, win, logger = console, controllers = {} } = {}) {
  const chrome = controllers ? controllers.chrome : undefined;
  const doc = win ? win.document : undefined;
  const tracker = createRevTracker();
  const panels = new Map(); // panel -> {panel, viewport, cells: Map(cell -> {disposers}), observed: Map, session, cellsList, disposers}
  const rootDisposers = [];
  let channel = null;
  let disposed = false;

  const warn = (...args) => {
    if (logger && typeof logger.warn === "function") logger.warn(...args);
  };

  function guarded(label, fn) {
    return (...args) => {
      if (disposed) return undefined;
      try {
        return fn(...args);
      } catch (err) {
        logger.error(`praxis display stale: ${label} failed:`, err);
        return undefined;
      }
    };
  }

  function connect(disposers, signal, slot) {
    if (!signal || typeof signal.connect !== "function") return;
    signal.connect(slot);
    disposers.push(() => {
      if (typeof signal.disconnect === "function") signal.disconnect(slot);
    });
  }

  function runDisposers(disposers) {
    for (const dispose of disposers.splice(0)) {
      try {
        dispose();
      } catch (err) {
        logger.error("praxis display stale: disconnect failed:", err);
      }
    }
  }

  // -- marking ---------------------------------------------------------------------------------------

  function applyOutput(entry, cell, index) {
    const stamp = stampOf(cell.model.outputs.get(index));
    if (stamp === null || typeof stamp !== "object") return;
    const widget = cell.outputArea && cell.outputArea.widgets && cell.outputArea.widgets[index];
    if (!widget || !widget.node || !doc) return;
    const host = hostOf(widget.node);

    setMark(doc, host, KIND_CHANGED, CHANGED_TEXT, changedSince(stamp, tracker));

    // With the session unknown nothing is written, and nothing already written
    // is taken back (an old mark on an old output stays true).
    const earlier = earlierSession(stamp, entry.session);
    if (earlier || entry.session !== null) {
      setMark(doc, host, KIND_EARLIER, EARLIER_TEXT, earlier);
    }
  }

  function applyCell(entry, cell) {
    const model = cell && cell.model;
    if (!model || model.type !== "code" || !model.outputs) return;
    const count = model.outputs.length;
    for (let i = 0; i < count; i += 1) {
      try {
        applyOutput(entry, cell, i);
      } catch (err) {
        logger.error("praxis display stale: marking an output failed:", err);
      }
    }
  }

  function applyPanel(entry) {
    for (const cell of Array.from(entry.cells.keys())) {
      guarded("cell marks", () => applyCell(entry, cell))();
    }
  }

  function applyAll() {
    for (const entry of Array.from(panels.values())) {
      guarded("panel marks", () => applyPanel(entry))();
    }
  }

  // -- the panel's current session ----------------------------------------------------------------------

  /** Recompute `entry.session` from the observed cells' outputs. True when it changed. */
  function recomputeSession(entry) {
    const widgets = entry.panel.content && entry.panel.content.widgets;
    const present = widgets ? new Set(Array.from(widgets)) : null;
    let found = null;
    for (const cell of Array.from(entry.observed.keys()).reverse()) {
      if (present && !present.has(cell)) {
        entry.observed.delete(cell); // a deleted cell no longer speaks for the panel
        continue;
      }
      const session = newestSession(cell);
      if (session !== null) {
        found = session;
        break;
      }
    }
    const changed = found !== entry.session;
    entry.session = found;
    return changed;
  }

  /** P's kernel (re)started: no session is known until a stamped execution is observed. */
  function resetSession(entry) {
    entry.observed.clear();
    entry.session = null;
  }

  // -- one cell ---------------------------------------------------------------------------------------------

  function attachCell(entry, cell) {
    if (entry.cells.has(cell)) return;
    const model = cell && cell.model;
    if (!model || model.type !== "code") return;

    const cellEntry = { disposers: [] };
    entry.cells.set(cell, cellEntry);

    connect(
      cellEntry.disposers,
      model.outputs && model.outputs.changed,
      guarded("outputs changed", () => {
        if (entry.observed.has(cell) && recomputeSession(entry)) applyPanel(entry);
        else applyCell(entry, cell);
      }),
    );
    if (entry.viewport) {
      connect(cellEntry.disposers, cell.inViewportChanged, guarded("viewport", () => applyCell(entry, cell)));
    }
    applyCell(entry, cell);
  }

  // -- one panel ---------------------------------------------------------------------------------------------

  function scanPanel(entry) {
    const content = entry.panel.content;
    const cells = content.model && content.model.cells;
    if (cells && entry.cellsList !== cells) {
      entry.cellsList = cells;
      connect(entry.disposers, cells.changed, guarded("cell list", () => scanPanel(entry)));
    }
    for (const cell of Array.from(content.widgets || [])) {
      guarded("attach cell", () => attachCell(entry, cell))();
    }
  }

  function viewportNeeded(panel) {
    const info = chrome && typeof chrome.windowing === "function" ? chrome.windowing(panel) : null;
    if (info) return Boolean(info.viewportSubscribed);
    return windowingModeOf(panel) !== CONTENT_VISIBILITY;
  }

  function attachPanel(panel) {
    if (disposed || !isNotebookPanel(panel)) return false;
    const existing = panels.get(panel);
    if (existing) {
      scanPanel(existing);
      return true;
    }

    const entry = {
      panel,
      viewport: viewportNeeded(panel),
      cells: new Map(),
      observed: new Map(),
      session: null,
      cellsList: null,
      disposers: [],
    };
    panels.set(panel, entry);

    const rescan = guarded("panel rescan", () => {
      scanPanel(entry);
      applyPanel(entry);
    });
    connect(entry.disposers, panel.content.activeCellChanged, rescan);
    connect(entry.disposers, panel.content.modelChanged, rescan);
    connect(
      entry.disposers,
      panel.disposed,
      guarded("panel dispose", () => {
        for (const cellEntry of entry.cells.values()) runDisposers(cellEntry.disposers);
        runDisposers(entry.disposers);
        panels.delete(panel);
      }),
    );

    const context = panel.sessionContext;
    if (context) {
      connect(
        entry.disposers,
        context.kernelChanged,
        guarded("kernel changed", (_sender, args) => {
          const oldKernel = own(args, "oldValue");
          const newKernel = own(args, "newValue");
          if (oldKernel === newKernel) return;
          resetSession(entry);
        }),
      );
      connect(
        entry.disposers,
        context.statusChanged,
        guarded("kernel status", (_sender, status) => {
          if (RESTART_STATUSES.has(status)) resetSession(entry);
        }),
      );
    }

    scanPanel(entry);
    return true;
  }

  // -- the app ------------------------------------------------------------------------------------------------

  function scan() {
    const shell = app && app.shell;
    if (!shell || typeof shell.widgets !== "function") return;
    for (const widget of Array.from(shell.widgets("main"))) {
      guarded("attach panel", () => attachPanel(widget))();
    }
    for (const entry of Array.from(panels.values())) {
      guarded("panel scan", () => scanPanel(entry))();
    }
  }

  const onShellChange = guarded("shell scan", scan);
  connect(rootDisposers, app && app.shell && app.shell.currentChanged, onShellChange);
  connect(rootDisposers, app && app.shell && app.shell.layoutModified, onShellChange);

  // -- observed executions (chrome.js) ---------------------------------------------------------------------------

  if (chrome && typeof chrome.onExecution === "function") {
    const unsubscribe = chrome.onExecution(
      guarded("execution event", (event) => {
        // Only a FINISHED execution has outputs to read; "started" is ignored.
        if (!event || event.phase !== "finished") return;
        attachPanel(event.panel);
        const entry = panels.get(event.panel);
        if (!entry) return;
        scanPanel(entry);
        entry.observed.delete(event.cell); // most recently finished last
        entry.observed.set(event.cell, true);
        recomputeSession(entry);
        applyPanel(entry);
      }),
    );
    if (typeof unsubscribe === "function") rootDisposers.push(unsubscribe);
  } else {
    warn("praxis display stale: the chrome controller is not mounted; no session marks will be written.");
  }

  // -- announcements -------------------------------------------------------------------------------------------------

  function handleMessage(data) {
    if (disposed) return false;
    const announcement = parseAnnouncement(data);
    if (!announcement) return false;
    tracker.apply(announcement);
    applyAll();
    return true;
  }

  const Channel = win ? win.BroadcastChannel : undefined;
  if (typeof Channel !== "function") {
    warn("praxis display stale: no BroadcastChannel; staleness announcements will not be heard.");
  } else {
    try {
      channel = new Channel(CHANNEL);
      const onMessage = guarded("announcement", (event) => handleMessage(event ? event.data : undefined));
      if (typeof channel.addEventListener === "function") {
        channel.addEventListener("message", onMessage);
        rootDisposers.push(() => channel.removeEventListener("message", onMessage));
      } else {
        channel.onmessage = onMessage;
      }
      rootDisposers.push(() => channel.close());
    } catch (err) {
      logger.error("praxis display stale: cannot open the praxis_repl channel:", err);
    }
  }

  scan();

  return {
    panelSession(panel) {
      const entry = panels.get(panel);
      return entry ? entry.session : null;
    },
    handleMessage: (data) => {
      try {
        return handleMessage(data);
      } catch (err) {
        logger.error("praxis display stale: handleMessage failed:", err);
        return false;
      }
    },
    apply: guarded("apply", applyAll),
    scan: guarded("scan", scan),
    dispose() {
      if (disposed) return;
      for (const entry of panels.values()) {
        for (const cellEntry of entry.cells.values()) runDisposers(cellEntry.disposers);
        runDisposers(entry.disposers);
      }
      panels.clear();
      runDisposers(rootDisposers);
      disposed = true;
    },
  };
}
