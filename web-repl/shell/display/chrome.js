// chrome.js -- notebook cell chrome: the status rail's state (spec
// .praxia/docs/specs/260929_notebook-display-epic.md section 3.1, section 4
// chrome.js row, AC-5; task A5).
//
// Each code cell is in exactly one of five states, written on the cell node as
// `data-praxis-cell-state` (the theme's rail keys on it, A4) together with
// `data-praxis-exec` (the execution count shown at the rail's top):
//
//   running > stale > error > ran > not-run       (precedence, highest first)
//
// The state is derived from the notebook MODEL, not from JupyterLab's CSS
// classes (spike S1, outcome s1_a): not-run / running / ran from the execution
// count and state, error from an output whose type is "error", stale from the
// source differing from a snapshot. The snapshot is the cell source captured
// when an execution is observed in this page, or at first observation for a
// cell loaded with saved outputs; so after a reload a cell is ran or error from
// its saved outputs and becomes stale only after an edit made in this page. A
// cell is stale only with a non-null execution count AND a snapshot: an edited
// cell that never ran stays not-run.
//
// Windowing (S1 caveat): the notebook runs in windowingMode "contentVisibility",
// where cells are never detached and no re-attach signal exists. chrome.js reads
// the mode when it attaches a panel; in any other mode (or an unreadable one) it
// also subscribes to each cell's `inViewportChanged` and re-writes the
// attributes, so a re-attached node is never left bare.
//
// Failure containment: every signal handler, every cell and every listener runs
// under its own try/catch; a failure is logged with `logger.error` and never
// stops the other cells, the other panels or the shell.
//
// No `<script>`, no `import` of anything outside this directory, and nothing
// here touches the model: it reads it.

export const STATE_ATTR = "data-praxis-cell-state";
export const EXEC_ATTR = "data-praxis-exec";
export const CELL_STATES = Object.freeze(["not-run", "ran", "running", "error", "stale"]);

const CONTENT_VISIBILITY = "contentVisibility";

// -- Reading a cell model ------------------------------------------------------

/** The cell's current source text. */
export function cellSource(model) {
  const shared = model.sharedModel;
  if (shared && typeof shared.getSource === "function") return shared.getSource();
  if (model.value && typeof model.value.text === "string") return model.value.text;
  throw new Error("chrome: cannot read a cell model's source");
}

/** The execution count, or null when the cell has none (never ran, or cleared). */
export function executionCount(model) {
  const count = model.executionCount;
  return count === undefined ? null : count;
}

/** True while the kernel is executing the cell (the prompt reads `[*]:`). */
export function isRunning(model) {
  return model.executionState === "running";
}

function outputTypeOf(output) {
  if (output == null) return null;
  if (typeof output.type === "string") return output.type;
  if (typeof output.output_type === "string") return output.output_type;
  if (typeof output.toJSON === "function") {
    const json = output.toJSON();
    return json && typeof json.output_type === "string" ? json.output_type : null;
  }
  return null;
}

/** The type of every output of the cell (JupyterLab's IOutputAreaModel, or a
 * plain array of nbformat output dicts). */
export function outputTypes(model) {
  const outputs = model.outputs;
  if (!outputs) return [];
  const types = [];
  if (Array.isArray(outputs)) {
    for (const output of outputs) types.push(outputTypeOf(output));
    return types;
  }
  if (typeof outputs.length === "number" && typeof outputs.get === "function") {
    for (let i = 0; i < outputs.length; i += 1) types.push(outputTypeOf(outputs.get(i)));
  }
  return types;
}

/** True when any output of the cell is an error output. */
export function hasErrorOutput(model) {
  return outputTypes(model).includes("error");
}

// -- The derivation (pure) -----------------------------------------------------

/**
 * The cell's state. Precedence: running > stale > error > ran > not-run.
 *
 * @param model    a cell model
 * @param opts.running   the cell is executing (see isRunning)
 * @param opts.snapshot  the source captured when an execution was observed, or
 *                       null when none was
 */
export function cellState(model, { running = false, snapshot = null } = {}) {
  if (running) return "running";
  const count = executionCount(model);
  if (count !== null && snapshot !== null && cellSource(model) !== snapshot) return "stale";
  if (hasErrorOutput(model)) return "error";
  if (count !== null) return "ran";
  return "not-run";
}

// -- Snapshot bookkeeping (pure) -----------------------------------------------

/**
 * Advance a cell's tracking record by one observation of its model.
 *
 * `prev` is null at the first observation of a cell. A cell first seen with an
 * execution count (a loaded cell) or already running gets a snapshot of its
 * current source. Afterwards the snapshot is re-taken at the start of every
 * execution observed here (the source that is about to run), and, if a count
 * arrives with no start observed, when the count arrives.
 *
 * Returns `{track, events}`; `events` holds "started" when a run began and
 * "finished" when a new execution count arrived (never at first observation).
 */
export function trackCell(prev, model) {
  const count = executionCount(model);
  const running = isRunning(model);

  if (prev === null) {
    const observed = running || count !== null;
    return {
      track: {
        snapshot: observed ? cellSource(model) : null,
        count,
        running,
        snapshotForRun: running,
      },
      events: [],
    };
  }

  let { snapshot, snapshotForRun } = prev;
  const events = [];

  if (!prev.running && running) {
    snapshot = cellSource(model);
    snapshotForRun = true;
    events.push("started");
  }

  if (count !== null && count !== prev.count) {
    if (!snapshotForRun) snapshot = cellSource(model);
    snapshotForRun = false;
    events.push("finished");
  }

  if (count === null && !running && !snapshotForRun) {
    snapshot = null;
  }

  return { track: { snapshot, count, running, snapshotForRun }, events };
}

// -- The DOM writer -----------------------------------------------------------

/**
 * Write the two attributes on a cell node. Idempotent: an attribute whose value
 * is already right is not touched (so an attribute observer never loops).
 * Returns true when anything was written. A null count writes an empty
 * `data-praxis-exec`.
 */
export function writeCellAttrs(node, state, exec) {
  if (!CELL_STATES.includes(state)) {
    throw new Error(`chrome: unknown cell state ${JSON.stringify(state)}`);
  }
  const execText = exec === null || exec === undefined ? "" : String(exec);
  let changed = false;
  if (node.getAttribute(STATE_ATTR) !== state) {
    node.setAttribute(STATE_ATTR, state);
    changed = true;
  }
  if (node.getAttribute(EXEC_ATTR) !== execText) {
    node.setAttribute(EXEC_ATTR, execText);
    changed = true;
  }
  return changed;
}

// -- Notebook discovery --------------------------------------------------------

function isNotebookPanel(widget) {
  return Boolean(
    widget &&
      widget.content &&
      widget.node &&
      widget.node.classList &&
      widget.node.classList.contains("jp-NotebookPanel"),
  );
}

/** The panel's windowing mode ("contentVisibility", "full", "defer", "none"),
 * or null when it cannot be read. */
export function windowingModeOf(panel) {
  try {
    const content = panel.content;
    const config = content && content.notebookConfig;
    const mode = (config && config.windowingMode) ?? (content && content.windowingMode);
    return typeof mode === "string" ? mode : null;
  } catch {
    return null;
  }
}

// -- The controller ------------------------------------------------------------

/**
 * Start the chrome on a JupyterLab app: derive and write the state of every
 * code cell of every open notebook, and keep it current.
 *
 * @param {object} opts
 * @param opts.app     the app handle (`window.jupyterapp`)
 * @param opts.logger  console-like (`error`, `warn`); defaults to `console`
 * @returns {{
 *   attachPanel(panel): boolean,
 *   scan(): void,
 *   refresh(): void,
 *   onExecution(listener): () => void,
 *   windowing(panel): ({mode: string|null, viewportSubscribed: boolean}|null),
 *   dispose(): void,
 * }}
 */
export function mountChrome({ app, logger = console } = {}) {
  const panels = new Map(); // panel -> panelEntry
  const listeners = new Set();
  const rootDisposers = [];
  let disposed = false;

  function guarded(label, fn) {
    return (...args) => {
      if (disposed) return undefined;
      try {
        return fn(...args);
      } catch (err) {
        logger.error(`praxis display chrome: ${label} failed:`, err);
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
        logger.error("praxis display chrome: disconnect failed:", err);
      }
    }
  }

  function emitExecution(event) {
    for (const listener of Array.from(listeners)) {
      try {
        listener(event);
      } catch (err) {
        logger.error("praxis display chrome: execution listener failed:", err);
      }
    }
  }

  // -- one cell ---------------------------------------------------------------

  function refreshCell(entry) {
    const { cell, panel } = entry;
    const model = cell.model;
    const { track, events } = trackCell(entry.track, model);
    entry.track = track;
    const state = cellState(model, { running: track.running, snapshot: track.snapshot });
    writeCellAttrs(cell.node, state, executionCount(model));
    for (const phase of events) {
      emitExecution({ cell, panel, phase, executionCount: track.count });
    }
  }

  function attachCell(panelEntry, cell) {
    if (panelEntry.cells.has(cell)) return;
    const model = cell && cell.model;
    if (!model || model.type !== "code") return;

    const entry = { cell, panel: panelEntry.panel, track: null, disposers: [] };
    panelEntry.cells.set(cell, entry);
    const refresh = guarded("cell refresh", () => refreshCell(entry));

    connect(entry.disposers, model.stateChanged, refresh);
    connect(entry.disposers, model.contentChanged, refresh);
    connect(entry.disposers, model.sharedModel && model.sharedModel.changed, refresh);
    connect(entry.disposers, model.outputs && model.outputs.changed, refresh);
    if (panelEntry.viewportSubscribed) {
      connect(entry.disposers, cell.inViewportChanged, refresh);
    }
    refresh();
  }

  // -- one panel --------------------------------------------------------------

  function scanPanel(panelEntry) {
    const content = panelEntry.panel.content;
    // The notebook model can be replaced after we attach (modelChanged): follow
    // its cell list.
    const cells = content.model && content.model.cells;
    if (cells && panelEntry.cellsList !== cells) {
      panelEntry.cellsList = cells;
      connect(panelEntry.disposers, cells.changed, guarded("cell list", () => scanPanel(panelEntry)));
    }
    for (const cell of Array.from(content.widgets || [])) {
      guarded("attach cell", () => attachCell(panelEntry, cell))();
    }
  }

  function attachPanel(panel) {
    if (disposed || !isNotebookPanel(panel)) return false;
    const existing = panels.get(panel);
    if (existing) {
      scanPanel(existing);
      return true;
    }

    const mode = windowingModeOf(panel);
    const viewportSubscribed = mode !== CONTENT_VISIBILITY;
    const panelEntry = {
      panel,
      mode,
      viewportSubscribed,
      cells: new Map(),
      cellsList: null,
      disposers: [],
    };
    panels.set(panel, panelEntry);

    if (viewportSubscribed) {
      logger.warn(
        `praxis display chrome: notebook windowingMode is ${JSON.stringify(mode)}, not ` +
          `"${CONTENT_VISIBILITY}"; also subscribing to inViewportChanged.`,
      );
    }

    const rescan = guarded("panel rescan", () => scanPanel(panelEntry));
    connect(panelEntry.disposers, panel.content.activeCellChanged, rescan);
    connect(panelEntry.disposers, panel.content.modelChanged, rescan);
    connect(
      panelEntry.disposers,
      panel.disposed,
      guarded("panel dispose", () => {
        for (const entry of panelEntry.cells.values()) runDisposers(entry.disposers);
        runDisposers(panelEntry.disposers);
        panels.delete(panel);
      }),
    );
    if (panel.revealed && typeof panel.revealed.then === "function") {
      panel.revealed.then(rescan, () => {});
    }

    scanPanel(panelEntry);
    return true;
  }

  // -- the app ----------------------------------------------------------------

  function scan() {
    const shell = app && app.shell;
    if (!shell || typeof shell.widgets !== "function") return;
    for (const widget of Array.from(shell.widgets("main"))) {
      guarded("attach panel", () => attachPanel(widget))();
    }
    for (const panelEntry of Array.from(panels.values())) {
      guarded("panel scan", () => scanPanel(panelEntry))();
    }
  }

  function refresh() {
    for (const panelEntry of Array.from(panels.values())) {
      for (const entry of Array.from(panelEntry.cells.values())) {
        guarded("cell refresh", () => refreshCell(entry))();
      }
    }
  }

  const onShellChange = guarded("shell scan", scan);
  connect(rootDisposers, app && app.shell && app.shell.currentChanged, onShellChange);
  connect(rootDisposers, app && app.shell && app.shell.layoutModified, onShellChange);
  scan();

  return {
    attachPanel: (panel) => {
      try {
        return attachPanel(panel);
      } catch (err) {
        logger.error("praxis display chrome: attachPanel failed:", err);
        return false;
      }
    },
    scan: guarded("scan", scan),
    refresh: guarded("refresh", refresh),
    onExecution(listener) {
      listeners.add(listener);
      return () => {
        listeners.delete(listener);
      };
    },
    windowing(panel) {
      const panelEntry = panels.get(panel);
      return panelEntry
        ? { mode: panelEntry.mode, viewportSubscribed: panelEntry.viewportSubscribed }
        : null;
    },
    dispose() {
      if (disposed) return;
      for (const panelEntry of panels.values()) {
        for (const entry of panelEntry.cells.values()) runDisposers(entry.disposers);
        runDisposers(panelEntry.disposers);
      }
      panels.clear();
      runDisposers(rootDisposers);
      listeners.clear();
      disposed = true;
    },
  };
}
