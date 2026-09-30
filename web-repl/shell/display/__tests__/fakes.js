// fakes.js -- Test doubles for web-repl/shell/display (spec
// .praxia/docs/specs/260929_notebook-display-epic.md section 4, fakes.js row;
// task A5). Modelled on shell/coxswain/__tests__/dom_stub.js: web-repl has no
// package.json and no installed dependencies, so the shell modules are
// exercised against these stand-ins instead of jsdom or a real JupyterLab.
//
// They implement exactly the JupyterLab surface chrome.js reads, as recorded
// by spike S1 (.praxia/docs/research/260929_notebook-display-s1-lumino-widget.md):
//   app.shell.widgets('main'), app.shell.currentChanged / layoutModified,
//   app.restored;
//   panel.node (class jp-NotebookPanel), panel.content.widgets,
//   panel.content.model.cells.changed, panel.content.notebookConfig
//   .windowingMode, panel.content.activeCellChanged, panel.revealed;
//   cell.node, cell.model, cell.inViewportChanged;
//   cellModel.type / executionCount / executionState / sharedModel.getSource()
//   / outputs (length, get(i).type, changed) / stateChanged / contentChanged.
//
// Lumino's Signal calls a slot as slot(sender, args) in connection order;
// createFakeSignal does the same and counts live connections so a test can
// assert idempotent re-attachment.

export function createFakeSignal() {
  const slots = [];
  return {
    connect(slot) {
      if (slots.includes(slot)) return false;
      slots.push(slot);
      return true;
    },
    disconnect(slot) {
      const index = slots.indexOf(slot);
      if (index < 0) return false;
      slots.splice(index, 1);
      return true;
    },
    emit(sender, args) {
      for (const slot of slots.slice()) slot(sender, args);
    },
    get connectionCount() {
      return slots.length;
    },
  };
}

/** A DOM node with just the attribute surface the writer uses, plus a log of
 * every setAttribute call so idempotency is observable. */
export function createFakeNode(classes = []) {
  const attrs = new Map();
  const classSet = new Set(classes);
  return {
    nodeType: 1,
    setAttributeCalls: [],
    setAttribute(name, value) {
      this.setAttributeCalls.push([name, String(value)]);
      attrs.set(name, String(value));
    },
    getAttribute(name) {
      return attrs.has(name) ? attrs.get(name) : null;
    },
    removeAttribute(name) {
      attrs.delete(name);
    },
    hasAttribute(name) {
      return attrs.has(name);
    },
    classList: {
      contains: (name) => classSet.has(name),
      add: (name) => classSet.add(name),
      remove: (name) => classSet.delete(name),
    },
  };
}

/** A cell model with JupyterLab's execution life cycle. `type` is "code",
 * "markdown" or "raw". Setters emit the same signals the real model does. */
export function createFakeCellModel({
  type = "code",
  source = "",
  executionCount = null,
  executionState = "idle",
  outputs = [],
} = {}) {
  let src = source;
  let count = executionCount;
  let state = executionState;
  const outs = outputs.map((t) => ({ type: t }));

  const model = {
    type,
    stateChanged: createFakeSignal(),
    contentChanged: createFakeSignal(),
    sharedModel: {
      changed: createFakeSignal(),
      getSource: () => src,
    },
    outputs: {
      changed: createFakeSignal(),
      get length() {
        return outs.length;
      },
      get: (index) => outs[index],
    },
    get executionCount() {
      return count;
    },
    get executionState() {
      return state;
    },

    // -- what a user does -------------------------------------------------
    /** Edit the source (a keystroke). */
    setSource(text) {
      src = text;
      model.sharedModel.changed.emit(model.sharedModel, { sourceChange: [] });
      model.contentChanged.emit(model, undefined);
    },

    // -- what the kernel round trip does ---------------------------------
    /** JupyterLab clears the count and the outputs and sets state running. */
    startExecution() {
      count = null;
      model.stateChanged.emit(model, { name: "executionCount", newValue: null });
      outs.length = 0;
      model.outputs.changed.emit(model.outputs, { type: "remove" });
      state = "running";
      model.stateChanged.emit(model, { name: "executionState", newValue: "running" });
    },
    /** The reply: an output (stream or error), the count, then idle. */
    finishExecution({ count: newCount, error = false, countBeforeIdle = true } = {}) {
      outs.push({ type: error ? "error" : "stream" });
      model.outputs.changed.emit(model.outputs, { type: "add" });
      const setCount = () => {
        count = newCount;
        model.stateChanged.emit(model, { name: "executionCount", newValue: newCount });
      };
      const setIdle = () => {
        state = "idle";
        model.stateChanged.emit(model, { name: "executionState", newValue: "idle" });
      };
      if (countBeforeIdle) {
        setCount();
        setIdle();
      } else {
        setIdle();
        setCount();
      }
    },
    /** Convenience: a full successful or failed execution. */
    execute(newCount, { error = false, source: newSource } = {}) {
      if (newSource !== undefined) model.setSource(newSource);
      model.startExecution();
      model.finishExecution({ count: newCount, error });
    },
  };
  return model;
}

/** A cell widget: `node`, `model` and the viewport signal. */
export function createFakeCell(modelOptions = {}) {
  return {
    model: createFakeCellModel(modelOptions),
    node: createFakeNode(["jp-Cell"]),
    inViewportChanged: createFakeSignal(),
  };
}

/** A notebook panel. `windowingMode` is what `content.notebookConfig` reports
 * (null to simulate an unreadable mode). */
export function createFakeNotebookPanel({ cells = [], windowingMode = "contentVisibility" } = {}) {
  const widgets = cells.slice();
  const cellsList = { changed: createFakeSignal() };
  const content = {
    widgets,
    model: { cells: cellsList },
    activeCellChanged: createFakeSignal(),
    modelChanged: createFakeSignal(),
    notebookConfig: windowingMode === null ? {} : { windowingMode },
  };
  return {
    node: createFakeNode(["jp-NotebookPanel"]),
    content,
    disposed: createFakeSignal(),
    revealed: Promise.resolve(),
    /** Insert a cell the way JupyterLab does: widgets first, then the model
     * list's `changed`. */
    addCell(cell) {
      widgets.push(cell);
      cellsList.changed.emit(cellsList, { type: "add" });
      return cell;
    },
  };
}

/** The app handle (`window.jupyterapp`): a shell with main-area widgets. */
export function createFakeApp({ panels = [] } = {}) {
  const main = panels.slice();
  const shell = {
    currentChanged: createFakeSignal(),
    layoutModified: createFakeSignal(),
    *widgets(area) {
      if (area === "main") yield* main;
    },
  };
  return {
    shell,
    restored: Promise.resolve(),
    /** Open a panel the way the shell does: it joins the area, then the
     * shell signals. */
    addPanel(panel) {
      main.push(panel);
      shell.layoutModified.emit(shell, undefined);
      shell.currentChanged.emit(shell, { newValue: panel });
      return panel;
    },
  };
}

/** A minimal `window` for index.js: a jupyterapp that may appear later, and a
 * synchronous stand-in for setInterval/clearInterval. */
export function createFakeWindow({ app = null } = {}) {
  const timers = new Map();
  let nextId = 1;
  const win = {
    jupyterapp: app,
    setInterval(fn) {
      const id = nextId++;
      timers.set(id, fn);
      return id;
    },
    clearInterval(id) {
      timers.delete(id);
    },
    /** Fire every pending interval callback once. */
    tick() {
      for (const fn of Array.from(timers.values())) fn();
    },
    get pendingTimers() {
      return timers.size;
    },
  };
  return win;
}
