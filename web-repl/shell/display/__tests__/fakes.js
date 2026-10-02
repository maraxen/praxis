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
// B9 additions: a small DOM (FakeElement / FakeDocument with bubbling events, a
// querySelector that supports ONLY a single class or tag selector so a selector
// built from a resource name throws), output metadata on cell outputs (frozen,
// and every writer of the model throws: the shell must only read), a cell's
// output area (widgets whose nodes are REPLACED on every render, like
// JupyterLab's), a panel's sessionContext (kernel restart signals), and a
// BroadcastChannel hub. See the "B9" section at the end of this file.
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

function forbidden(name) {
  return () => {
    throw new Error(`fake model: ${name} is a write; the shell must only read the model`);
  };
}

function deepFreeze(value) {
  if (value && typeof value === "object" && !Object.isFrozen(value)) {
    Object.freeze(value);
    for (const key of Object.keys(value)) deepFreeze(value[key]);
  }
  return value;
}

/** A model output: a type string, or `{type, metadata}`. Frozen, so a write to
 * an output (or its stamp) throws. */
function makeOutput(spec) {
  if (typeof spec === "string") return deepFreeze({ type: spec, metadata: {} });
  return deepFreeze({ type: "display_data", metadata: {}, ...spec });
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
  const outs = outputs.map(makeOutput);

  const model = {
    type,
    stateChanged: createFakeSignal(),
    contentChanged: createFakeSignal(),
    sharedModel: {
      changed: createFakeSignal(),
      getSource: () => src,
      // The shell reads the model; it never writes it (D7). Every writer of the
      // real model throws here so a write is a loud failure.
      setSource: forbidden("sharedModel.setSource"),
      updateSource: forbidden("sharedModel.updateSource"),
      setMetadata: forbidden("sharedModel.setMetadata"),
      updateOutputs: forbidden("sharedModel.updateOutputs"),
    },
    setMetadata: forbidden("model.setMetadata"),
    outputs: {
      changed: createFakeSignal(),
      get length() {
        return outs.length;
      },
      get: (index) => outs[index],
      add: forbidden("outputs.add"),
      set: forbidden("outputs.set"),
      clear: forbidden("outputs.clear"),
      removeStream: forbidden("outputs.removeStream"),
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
    /** Replace every output (a loaded notebook, or a kernel that displayed). */
    setOutputs(list) {
      outs.length = 0;
      for (const o of list) outs.push(makeOutput(o));
      model.outputs.changed.emit(model.outputs, { type: "set" });
    },
    /** The reply: outputs (default: one stream or error), the count, then idle.
     * `outputs` entries are type strings or `{type, metadata}`. */
    finishExecution({ count: newCount, error = false, countBeforeIdle = true, outputs: newOutputs } = {}) {
      const list = newOutputs ?? [error ? "error" : "stream"];
      for (const o of list) {
        outs.push(makeOutput(o));
        model.outputs.changed.emit(model.outputs, { type: "add" });
      }
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
    execute(newCount, { error = false, source: newSource, outputs: newOutputs } = {}) {
      if (newSource !== undefined) model.setSource(newSource);
      model.startExecution();
      model.finishExecution({ count: newCount, error, outputs: newOutputs });
    },
  };
  return model;
}

/** A cell widget: `node`, `model`, the viewport signal and `outputArea`.
 *
 * `outputArea.widgets[i].node` is the DOM of `model.outputs.get(i)`:
 * `div.jp-OutputArea-child > div.jp-OutputArea-output`. Like JupyterLab's
 * OutputArea (connected to the model first), the fake re-renders on every
 * `outputs.changed` with FRESH nodes, so a mark written to an old node is gone.
 * `rerender()` does the same on demand (a windowed cell re-attached). */
export function createFakeCell(modelOptions = {}) {
  const cell = {
    model: createFakeCellModel(modelOptions),
    node: createFakeNode(["jp-Cell"]),
    inViewportChanged: createFakeSignal(),
    outputArea: { widgets: [] },
    rerender() {
      const model = cell.model;
      cell.outputArea.widgets = [];
      for (let i = 0; i < model.outputs.length; i += 1) {
        const node = new FakeElement("div");
        node.classList.add("jp-OutputArea-child");
        const host = new FakeElement("div");
        host.classList.add("jp-OutputArea-output");
        node.appendChild(host);
        cell.outputArea.widgets.push({ node });
      }
    },
    /** The `.jp-OutputArea-output` element of output i (undefined if none). */
    host(i) {
      const widget = cell.outputArea.widgets[i];
      return widget ? widget.node.children[0] : undefined;
    },
  };
  // Re-render BEFORE the signal's slots run (the OutputArea is connected first),
  // without a slot of its own, so the signal's connectionCount stays the shell's.
  const signal = cell.model.outputs.changed;
  const emit = signal.emit;
  signal.emit = (sender, args) => {
    cell.rerender();
    emit(sender, args);
  };
  cell.rerender();
  return cell;
}

/** A notebook panel. `windowingMode` is what `content.notebookConfig` reports
 * (null to simulate an unreadable mode). */
export function createFakeNotebookPanel({
  cells = [],
  windowingMode = "contentVisibility",
  sessionContext = true,
} = {}) {
  const widgets = cells.slice();
  const cellsList = { changed: createFakeSignal() };
  const content = {
    widgets,
    model: { cells: cellsList },
    activeCellChanged: createFakeSignal(),
    modelChanged: createFakeSignal(),
    notebookConfig: windowingMode === null ? {} : { windowingMode },
  };
  const ctx = sessionContext
    ? { kernelChanged: createFakeSignal(), statusChanged: createFakeSignal() }
    : undefined;
  return {
    node: createFakeNode(["jp-NotebookPanel"]),
    content,
    sessionContext: ctx,
    disposed: createFakeSignal(),
    revealed: Promise.resolve(),
    /** A kernel restart, as the session context signals it. */
    restartKernel() {
      ctx.statusChanged.emit(ctx, "restarting");
      ctx.statusChanged.emit(ctx, "idle");
    },
    /** A different kernel attached to the panel. */
    switchKernel() {
      ctx.kernelChanged.emit(ctx, { oldValue: { id: "k1" }, newValue: { id: "k2" }, name: "kernel" });
    },
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
 * synchronous stand-in for setInterval/clearInterval.
 *
 * C5 additions (all additive): `innerWidth`, window events (`addEventListener` /
 * `removeEventListener` / `dispatchEvent`), `getComputedStyle` (padding taken from an
 * element's `_padding`, px per side), a `ResizeObserver` whose callbacks a test fires with
 * `win.resizeObservers.trigger()`, and the delay each interval was created with. */
export function createFakeWindow({ app = null, document = null, broadcast = null, innerWidth = 1440 } = {}) {
  const timers = new Map();
  const delays = new Map();
  const listeners = [];
  const observers = [];
  let nextId = 1;
  class FakeResizeObserver {
    constructor(callback) {
      this.callback = callback;
      this.targets = new Set();
      this.disconnected = false;
      observers.push(this);
    }

    observe(el) {
      this.targets.add(el);
    }

    unobserve(el) {
      this.targets.delete(el);
    }

    disconnect() {
      this.targets.clear();
      this.disconnected = true;
    }
  }
  const win = {
    jupyterapp: app,
    innerWidth,
    innerHeight: 900,
    ...(document ? { document } : {}),
    ...(broadcast ? { BroadcastChannel: broadcast.BroadcastChannel } : {}),
    ResizeObserver: FakeResizeObserver,
    resizeObservers: {
      all: observers,
      /** Fire every live observer that watches something, as the browser does after a layout. */
      trigger() {
        for (const ro of observers.slice()) {
          if (ro.targets.size > 0) ro.callback(Array.from(ro.targets, (target) => ({ target })), ro);
        }
      },
      get liveCount() {
        return observers.filter((ro) => ro.targets.size > 0).length;
      },
    },
    setInterval(fn, delay) {
      const id = nextId++;
      timers.set(id, fn);
      delays.set(id, delay);
      return id;
    },
    clearInterval(id) {
      timers.delete(id);
      delays.delete(id);
    },
    /** Fire every pending interval callback once. */
    tick() {
      for (const fn of Array.from(timers.values())) fn();
    },
    get pendingTimers() {
      return timers.size;
    },
    /** The delays of the intervals still pending. */
    get intervalDelays() {
      return Array.from(delays.values());
    },
    addEventListener(type, fn) {
      if (!listeners.some((l) => l.type === type && l.fn === fn)) listeners.push({ type, fn });
    },
    removeEventListener(type, fn) {
      const index = listeners.findIndex((l) => l.type === type && l.fn === fn);
      if (index >= 0) listeners.splice(index, 1);
    },
    /** Deliver `event` (`{type, ...}`) to the listeners of its type. */
    dispatchEvent(event) {
      for (const l of listeners.slice()) if (l.type === event.type) l.fn(event);
      return true;
    },
    listenerCount(type) {
      return listeners.filter((l) => l.type === type).length;
    },
    getComputedStyle(el) {
      const px = `${(el && el._padding) || 0}px`;
      return { paddingLeft: px, paddingRight: px };
    },
  };
  return win;
}

// -- B9: DOM ---------------------------------------------------------------------

const SIMPLE_SELECTOR = /^(\.[A-Za-z0-9_-]+|[A-Za-z][A-Za-z0-9]*)$/;

function camel(name) {
  return name.replace(/-([a-z])/g, (_m, ch) => ch.toUpperCase());
}

/**
 * A DOM element with the surface the display modules use: attributes, dataset
 * (derived from `data-*` attributes, so a stripped attribute is gone from the
 * dataset too), classList, children, textContent, bubbling events, and a
 * querySelector that supports ONLY `.class` and `tag` selectors. Any other
 * selector, in particular one built from a resource name (D14), throws.
 */
export class FakeElement {
  constructor(tagName = "div", ownerDocument = null) {
    this.nodeType = 1;
    this.tagName = tagName;
    this.localName = tagName.toLowerCase();
    this.ownerDocument = ownerDocument;
    this.parentNode = null;
    this.children = [];
    this.style = {};
    this.rect = { left: 0, top: 0, width: 0, height: 0 };
    this.appendCalls = 0;
    this.selectorCalls = [];
    this._attrs = new Map();
    this._text = "";
    this._listeners = [];
    this.classList = {
      contains: (name) => this._classes().includes(name),
      add: (name) => {
        if (!this._classes().includes(name)) this._setClasses([...this._classes(), name]);
      },
      remove: (name) => this._setClasses(this._classes().filter((c) => c !== name)),
      toggle: (name, force) => {
        const has = this._classes().includes(name);
        const want = force === undefined ? !has : Boolean(force);
        if (want && !has) this.classList.add(name);
        if (!want && has) this.classList.remove(name);
        return want;
      },
    };
  }

  _classes() {
    return (this._attrs.get("class") || "").split(/\s+/).filter(Boolean);
  }

  _setClasses(list) {
    if (list.length) this._attrs.set("class", list.join(" "));
    else this._attrs.delete("class");
  }

  get className() {
    return this._attrs.get("class") || "";
  }

  set className(value) {
    this._attrs.set("class", String(value));
  }

  get dataset() {
    const out = {};
    for (const [name, value] of this._attrs) {
      if (name.startsWith("data-")) out[camel(name.slice(5))] = value;
    }
    return out;
  }

  get textContent() {
    return this._text + this.children.map((c) => c.textContent).join("");
  }

  set textContent(value) {
    for (const child of this.children.splice(0)) child.parentNode = null;
    this._text = String(value);
  }

  setAttribute(name, value) {
    this._attrs.set(name, String(value));
    // C5: an opt-in log of every attribute write (`doc.attrLog = []`), so a test can count
    // `src` writes without holding an element (D11 invariant I2).
    const log = this.ownerDocument && this.ownerDocument.attrLog;
    if (log) log.push({ el: this, tag: this.localName, name, value: String(value) });
  }

  getAttribute(name) {
    return this._attrs.has(name) ? this._attrs.get(name) : null;
  }

  removeAttribute(name) {
    this._attrs.delete(name);
  }

  hasAttribute(name) {
    return this._attrs.has(name);
  }

  appendChild(child) {
    if (child.parentNode) child.parentNode.removeChild(child);
    this.children.push(child);
    child.parentNode = this;
    this.appendCalls += 1;
    // C5: an opt-in log of insertions (`doc.appendLog = []`): what the child's `src` was at the
    // moment it entered a parent (an iframe with its `src` already set loads the right page).
    const log = this.ownerDocument && this.ownerDocument.appendLog;
    if (log) log.push({ parent: this, child, srcAtInsert: child.getAttribute ? child.getAttribute("src") : null });
    return child;
  }

  removeChild(child) {
    const index = this.children.indexOf(child);
    if (index >= 0) this.children.splice(index, 1);
    child.parentNode = null;
    return child;
  }

  remove() {
    if (this.parentNode) this.parentNode.removeChild(this);
  }

  contains(other) {
    for (let n = other; n; n = n.parentNode) if (n === this) return true;
    return false;
  }

  _match(sel, el) {
    return sel.startsWith(".") ? el.classList.contains(sel.slice(1)) : el.localName === sel.toLowerCase();
  }

  querySelectorAll(selector) {
    this.selectorCalls.push(selector);
    if (typeof selector !== "string" || !SIMPLE_SELECTOR.test(selector)) {
      throw new Error(`fake querySelector: unsupported selector ${JSON.stringify(selector)}`);
    }
    const found = [];
    const walk = (el) => {
      for (const child of el.children) {
        if (this._match(selector, child)) found.push(child);
        walk(child);
      }
    };
    walk(this);
    return found;
  }

  querySelector(selector) {
    return this.querySelectorAll(selector)[0] ?? null;
  }

  getBoundingClientRect() {
    return { ...this.rect, right: this.rect.left + this.rect.width, bottom: this.rect.top + this.rect.height };
  }

  focus() {
    this.focused = true;
  }

  addEventListener(type, fn, options) {
    // Round 5: the capture flag (`true` or `{capture: true}`) is kept, so a capture listener is a different registration
    // from a bubble listener of the same function and runs in the capture phase of `dispatch`.
    const capture = options === true || Boolean(options && options.capture);
    if (!this._listeners.some((l) => l.type === type && l.fn === fn && l.capture === capture)) this._listeners.push({ type, fn, capture });
  }

  removeEventListener(type, fn, options) {
    const capture = options === true || Boolean(options && options.capture);
    this._listeners = this._listeners.filter((l) => !(l.type === type && l.fn === fn && l.capture === capture));
  }

  get listenerCount() {
    return this._listeners.length;
  }

  /** Dispatch a bubbling event from this element up through its ancestors (and
   * the document). Returns the event. */
  dispatch(type, props = {}) {
    const event = {
      type,
      target: this,
      bubbles: true,
      defaultPrevented: false,
      propagationStopped: false,
      relatedTarget: null,
      preventDefault() {
        this.defaultPrevented = true;
      },
      stopPropagation() {
        this.propagationStopped = true;
      },
      ...props,
    };
    // Round 5: the capture phase first (document down to the target), then the target and the bubble (up). A listener
    // registered without `capture` behaves exactly as before.
    const path = [];
    for (let node = this; node; node = node.parentNode) path.push(node);
    for (const node of path.slice().reverse()) {
      if (event.propagationStopped) break;
      event.currentTarget = node;
      for (const l of (node._listeners || []).slice()) if (l.type === type && l.capture) l.fn(event);
    }
    for (const node of path) {
      if (event.propagationStopped) break;
      event.currentTarget = node;
      for (const l of (node._listeners || []).slice()) if (l.type === type && !l.capture) l.fn(event);
    }
    return event;
  }
}

/** A document: `body`, element factories, and the top of the event chain. */
export class FakeDocument extends FakeElement {
  constructor() {
    super("#document");
    this.nodeType = 9;
    this.body = new FakeElement("body", this);
    this.appendChild(this.body);
  }

  createElement(tag) {
    const el = new FakeElement(tag, this);
    // C5: `doc.onCreate = (el) => ...` lets a test give an iframe its `contentWindow`.
    if (typeof this.onCreate === "function") this.onCreate(el);
    return el;
  }

  createElementNS(_ns, tag) {
    return new FakeElement(tag, this);
  }
}

export function createFakeDocument() {
  return new FakeDocument();
}

// -- B9: BroadcastChannel ------------------------------------------------------------

/**
 * A synchronous stand-in for BroadcastChannel: a message posted on one channel
 * is delivered to every OTHER open channel of the same name, to
 * `addEventListener("message")` listeners and to `onmessage`, as
 * `{data}`. `hub.post(name, data)` posts from a throwaway sender (the kernel
 * worker). `hub.openCount(name)` counts open channels, so a test can assert a
 * dispose closed its channel.
 */
export function createFakeBroadcastHub() {
  const channels = [];
  class FakeBroadcastChannel {
    constructor(name) {
      this.name = name;
      this.closed = false;
      this.onmessage = null;
      this._listeners = [];
      channels.push(this);
    }

    postMessage(data) {
      for (const c of channels.slice()) {
        if (c !== this && c.name === this.name && !c.closed) c._deliver(data);
      }
    }

    addEventListener(type, fn) {
      if (type === "message") this._listeners.push(fn);
    }

    removeEventListener(type, fn) {
      this._listeners = this._listeners.filter((f) => f !== fn);
    }

    close() {
      this.closed = true;
    }

    _deliver(data) {
      const event = { data };
      for (const fn of this._listeners.slice()) fn(event);
      if (typeof this.onmessage === "function") this.onmessage(event);
    }
  }
  return {
    BroadcastChannel: FakeBroadcastChannel,
    /** `except` (C5): channels that must not hear this post, so a probe can record what only the
     * shell under test posted. */
    post(name, data, { except = [] } = {}) {
      const sender = new FakeBroadcastChannel(name);
      for (const c of channels.slice()) {
        if (c !== sender && c.name === name && !c.closed && !except.includes(c)) c._deliver(data);
      }
      sender.closed = true;
    },
    openCount(name) {
      return channels.filter((c) => c.name === name && !c.closed).length;
    },
  };
}

// -- B9: praxis outputs ------------------------------------------------------------------

/** A resource output's stamp (D2). */
export function stamp({ kind = "plate", resource = "assay", rev = 1, session = "sA", exec = 1 } = {}) {
  return { v: 1, kind, resource, rev, session, exec };
}

/** A model output carrying `stamp` at `metadata.praxis` (S3-A) or, with
 * `carrier: "html"`, at `metadata["text/html"].praxis` (S3-B). */
export function praxisOutput(stampValue, { carrier = "praxis" } = {}) {
  const metadata =
    carrier === "html" ? { "text/html": { praxis: stampValue } } : { praxis: stampValue };
  return { type: "display_data", metadata };
}

/** The message the kernel posts (B7): `{type, json}` with `json` compact JSON. */
export function announcement({ session = "sA", exec = 1, revs, all } = {}) {
  const body = { session, exec };
  if (revs !== undefined) body.revs = revs;
  if (all !== undefined) body.all = all;
  return { type: "praxis:resource-changed", json: JSON.stringify(body) };
}

// -- C5: Lumino, the main DockPanel, the deck app, commands, plrViewer ---------------------------
//
// What dock.js reads, as S1 recorded it (.praxia/docs/research/260929_notebook-display-s1-
// lumino-widget.md): a shell widget whose prototype chain ends, at index 3 here, in the
// root Lumino `Widget` class (its prototype owns `processMessage` and `onAfterAttach`, and
// its own prototype is `Object.prototype`); `new Ctor({node})`; `app.shell.add(widget,
// "main", {mode: "split-right", ref})`, which needs `widget.id` like the real LabShell;
// `widget.parent` is the main DockPanel, with `saveLayout()` / `restoreLayout()` (a tree of
// tab-area and split-area configs, split areas carrying `sizes`) and `fit()`.
//
// The dock panel below is a small layout simulator, not a Lumino clone. It honours inline
// px `min-width` / `max-width` on a widget node (S1: css_limits_honoured), but only the
// values it read at the last `addWidget`, `fit()` or `restoreLayout()` (S1: css_limits_refit):
// so a build that sets limits and never calls `parent.fit()` leaves the width where it was.
// `restoreLayout()` never touches the widget's DOM (S1: restore_layout_keeps_iframe).

export function createFakeLumino(doc, { decoy = false } = {}) {
  const instances = [];
  class Widget {
    constructor(options = {}) {
      this.node = options.node || doc.createElement("div");
      this.parent = null;
      this.isAttached = false;
      this.isDisposed = false;
      this.id = "";
      this.title = { label: "", closable: false };
      this.disposed = createFakeSignal();
      this.closeRequests = 0;
      this.fitCalls = 0;
      this.activations = 0;
      instances.push(this);
    }

    processMessage() {}

    onAfterAttach() {}

    addClass(name) {
      this.node.classList.add(name);
    }

    activate() {
      this.activations += 1;
    }

    fit() {
      this.fitCalls += 1;
    }

    close() {
      this.closeRequests += 1;
      this.onCloseRequest({ type: "close-request" });
    }

    onCloseRequest() {
      if (this.parent && typeof this.parent.removeWidget === "function") this.parent.removeWidget(this);
      else {
        this.isAttached = false;
        this.node.remove();
      }
    }

    dispose() {
      if (this.isDisposed) return;
      this.isDisposed = true;
      this.close();
      this.disposed.emit(this, undefined);
    }
  }
  class Level1 extends Widget {}
  if (decoy) {
    // A class in the middle of the chain that also owns both methods but is NOT the root:
    // only "its own prototype is Object.prototype" tells the root from it.
    Level1.prototype.processMessage = function processMessage() {};
    Level1.prototype.onAfterAttach = function onAfterAttach() {};
  }
  class Level2 extends Level1 {
    onUpdateRequest() {}
  }
  class NotebookPanel extends Level2 {
    onActivateRequest() {}
  }
  return { Widget, Level1, NotebookPanel, instances };
}

const pxValue = (text) => {
  const m = /^(\d+(?:\.\d+)?)px$/.exec(text || "");
  return m ? Number(m[1]) : null;
};

function cloneArea(area) {
  if (!area) return null;
  if (area.type === "tab-area") return { type: "tab-area", widgets: area.widgets.slice(), currentIndex: area.currentIndex };
  return {
    type: "split-area",
    orientation: area.orientation,
    children: area.children.map(cloneArea),
    sizes: area.sizes.slice(),
  };
}

function firstTabArea(area) {
  if (area.type === "tab-area") return area;
  for (const child of area.children) {
    const found = firstTabArea(child);
    if (found) return found;
  }
  return null;
}

function tabAreaOf(area, widget) {
  if (!area) return null;
  if (area.type === "tab-area") return area.widgets.includes(widget) ? area : null;
  for (const child of area.children) {
    const found = tabAreaOf(child, widget);
    if (found) return found;
  }
  return null;
}

function replaceArea(area, target, replacement) {
  if (area === target) return replacement;
  if (area.type === "tab-area") return area;
  return { ...area, children: area.children.map((child) => replaceArea(child, target, replacement)) };
}

function prune(area, widget) {
  if (!area) return null;
  if (area.type === "tab-area") {
    const widgets = area.widgets.filter((w) => w !== widget);
    return widgets.length ? { ...area, widgets, currentIndex: 0 } : null;
  }
  const kept = [];
  const sizes = [];
  area.children.forEach((child, index) => {
    const next = prune(child, widget);
    if (next) {
      kept.push(next);
      sizes.push(area.sizes[index]);
    }
  });
  if (kept.length === 0) return null;
  if (kept.length === 1) return kept[0];
  const sum = sizes.reduce((a, b) => a + b, 0) || 1;
  return { ...area, children: kept, sizes: sizes.map((s) => s / sum) };
}

export function createFakeDockPanel(lumino, doc, { width = 1440 } = {}) {
  class FakeDockPanel extends lumino.Widget {
    constructor() {
      super({ node: doc.createElement("div") });
      this.node.rect = { left: 0, top: 40, width, height: 800 };
      this.layoutTree = null;
      this.saveCalls = 0;
      this.restoreCalls = [];
      this._limits = new Map();
      this._px = new Map();
    }

    get mainWidth() {
      return this.node.rect.width;
    }

    /** Place a widget that is already "in the shell" (a notebook panel). */
    seed(widget) {
      widget.parent = this;
      widget.isAttached = true;
      this.node.appendChild(widget.node);
      if (!this.layoutTree) this.layoutTree = { type: "tab-area", widgets: [widget], currentIndex: 0 };
      else firstTabArea(this.layoutTree).widgets.push(widget);
      this._reflow(true);
    }

    *allWidgets(area = this.layoutTree) {
      if (!area) return;
      if (area.type === "tab-area") yield* area.widgets;
      else for (const child of area.children) yield* this.allWidgets(child);
    }

    addWidget(widget, options = {}) {
      const ref = options.ref ? Array.from(this.allWidgets()).find((w) => w.id === options.ref) : null;
      const target = (ref && tabAreaOf(this.layoutTree, ref)) || firstTabArea(this.layoutTree);
      if (options.mode === "split-right") {
        const added = { type: "tab-area", widgets: [widget], currentIndex: 0 };
        this.layoutTree = replaceArea(this.layoutTree, target, {
          type: "split-area",
          orientation: "horizontal",
          children: [target, added],
          sizes: [0.5, 0.5],
        });
      } else {
        target.widgets.push(widget);
      }
      widget.parent = this;
      widget.isAttached = true;
      this.node.appendChild(widget.node);
      this._readLimits(widget);
      this._reflow(false);
    }

    removeWidget(widget) {
      this.layoutTree = prune(this.layoutTree, widget);
      widget.parent = null;
      widget.isAttached = false;
      widget.node.remove();
      this._px.delete(widget);
      this._limits.delete(widget);
      this._reflow(false);
    }

    saveLayout() {
      this.saveCalls += 1;
      return { main: cloneArea(this.layoutTree) };
    }

    restoreLayout(config) {
      this.restoreCalls.push(config);
      this.layoutTree = cloneArea(config.main);
      for (const w of this.allWidgets()) this._readLimits(w);
      this._reflow(false);
    }

    fit() {
      this.fitCalls += 1;
      for (const w of this.allWidgets()) this._readLimits(w);
      this._reflow(false);
    }

    _readLimits(widget) {
      const min = pxValue(widget.node.style.minWidth);
      const max = pxValue(widget.node.style.maxWidth);
      this._limits.set(widget, [min === null ? 0 : min, max === null ? Infinity : max]);
    }

    _areaLimits(area) {
      if (area.type !== "tab-area") return [0, Infinity];
      let lo = 0;
      let hi = Infinity;
      for (const w of area.widgets) {
        const [a, b] = this._limits.get(w) || [0, Infinity];
        lo = Math.max(lo, a);
        hi = Math.min(hi, b);
      }
      return [lo, hi];
    }

    _assign(area, px) {
      if (area.type === "tab-area") {
        for (const w of area.widgets) this._px.set(w, px);
        return;
      }
      if (area.orientation !== "horizontal") {
        for (const child of area.children) this._assign(child, px);
        return;
      }
      const sum = area.sizes.reduce((a, b) => a + b, 0) || 1;
      const widths = area.sizes.map((s) => (s / sum) * px);
      // Clamp each child to its limits, giving the difference to the unlimited siblings.
      for (let pass = 0; pass < 2; pass += 1) {
        area.children.forEach((child, i) => {
          const [lo, hi] = this._areaLimits(child);
          const clamped = Math.min(hi, Math.max(lo, widths[i]));
          const delta = widths[i] - clamped;
          if (delta === 0) return;
          widths[i] = clamped;
          const others = area.children.map((_c, j) => j).filter((j) => j !== i);
          for (const j of others) widths[j] += delta / others.length;
        });
      }
      area.children.forEach((child, i) => this._assign(child, widths[i]));
    }

    _reflow(readAll) {
      if (readAll) for (const w of this.allWidgets()) this._readLimits(w);
      this._px.clear();
      if (this.layoutTree) this._assign(this.layoutTree, this.mainWidth);
    }

    /** The width, in px, Lumino gave the widget at the last layout. */
    widthOf(widget) {
      return this._px.get(widget);
    }

    /** The user drags the splitter so that `widget` is `px` wide (clamped to the cached limits). */
    drag(widget, px) {
      const area = tabAreaOf(this.layoutTree, widget);
      const findSplit = (node) => {
        if (node.type === "tab-area") return null;
        const idx = node.children.findIndex((c) => c === area);
        if (idx >= 0 && node.orientation === "horizontal") return { node, idx };
        for (const c of node.children) {
          const hit = findSplit(c);
          if (hit) return hit;
        }
        return null;
      };
      const hit = findSplit(this.layoutTree);
      if (!hit) return this.widthOf(widget);
      const frac = Math.min(1, Math.max(0, px / this.mainWidth));
      const others = hit.node.children.length - 1;
      hit.node.sizes = hit.node.sizes.map((_s, i) => (i === hit.idx ? frac : (1 - frac) / others));
      this._reflow(false);
      return this.widthOf(widget);
    }

    /** The main area (not the window) changes width: a window resize or a sidebar toggle. */
    setWidth(px) {
      this.node.rect.width = px;
      this._reflow(false);
    }
  }
  return new FakeDockPanel();
}

/** A notebook panel that is a real (fake) Lumino widget: its prototype chain reaches the root. */
export function createFakeLuminoNotebook(lumino, doc, { id = "nb1", cells = [], kernel = true } = {}) {
  const panel = createFakeNotebookPanel({ cells });
  Object.setPrototypeOf(panel, lumino.NotebookPanel.prototype);
  panel.node = doc.createElement("div");
  panel.node.classList.add("jp-NotebookPanel");
  panel.content.node = doc.createElement("div");
  panel.content.node.classList.add("jp-Notebook");
  panel.node.appendChild(panel.content.node);
  panel.content.activeCell = null;
  Object.assign(panel, {
    id,
    parent: null,
    isAttached: false,
    isDisposed: false,
    title: { label: id },
    closeRequests: 0,
    fitCalls: 0,
    activations: 0,
  });
  panel.sessionContext.session = { kernel: kernel ? { id: `k-${id}` } : null };
  /** The user activates `cell`: the active cell changes and the signal fires. */
  panel.activate = (cell) => {
    panel.content.activeCell = cell;
    panel.content.activeCellChanged.emit(panel.content, cell);
  };
  /** The session context reports a kernel status. */
  panel.kernelStatus = (status) => {
    panel.sessionContext.statusChanged.emit(panel.sessionContext, status);
  };
  /** The panel loses its kernel (or gets a fresh one). */
  panel.setKernel = (kernelObject) => {
    const old = panel.sessionContext.session.kernel;
    panel.sessionContext.session.kernel = kernelObject;
    panel.sessionContext.kernelChanged.emit(panel.sessionContext, {
      name: "kernel",
      oldValue: old,
      newValue: kernelObject,
    });
  };
  return panel;
}

/** JupyterLab's command registry, reduced to what dock.js uses. */
export function createFakeCommands() {
  const registry = new Map();
  return {
    registry,
    addCommand(id, options) {
      if (registry.has(id)) throw new Error(`Command '${id}' already registered.`);
      registry.set(id, options);
      return {
        dispose() {
          registry.delete(id);
        },
      };
    },
    hasCommand: (id) => registry.has(id),
    execute(id, args) {
      const options = registry.get(id);
      if (!options) return Promise.reject(new Error(`Command '${id}' not registered.`));
      return Promise.resolve(options.execute(args));
    },
    label: (id) => (registry.has(id) ? registry.get(id).label : ""),
  };
}

/**
 * The app dock.js runs against: real-looking Lumino widgets (root class at chain index 3),
 * a main DockPanel that lays out split-right, a shell whose `add` insists on a widget `id`
 * like the LabShell, commands, and one notebook panel per requested notebook.
 */
export function createFakeDeckApp({ doc, notebooks = 1, width = 1440, lumino = createFakeLumino(doc) } = {}) {
  const dock = createFakeDockPanel(lumino, doc, { width });
  doc.body.appendChild(dock.node); // the main area is part of the page
  const panels = [];
  for (let i = 0; i < notebooks; i += 1) {
    const panel = createFakeLuminoNotebook(lumino, doc, { id: `nb${i + 1}` });
    panels.push(panel);
    dock.seed(panel);
  }
  const shell = {
    currentChanged: createFakeSignal(),
    layoutModified: createFakeSignal(),
    currentWidget: panels[0] || null,
    addCalls: [],
    *widgets(area) {
      if (area === "main") yield* dock.allWidgets();
    },
    add(widget, area, options) {
      shell.addCalls.push({ widget, area, options });
      if (!widget.id) throw new Error("Widgets added to the app shell must have unique id property.");
      if (Array.from(dock.allWidgets()).some((w) => w.id === widget.id)) {
        throw new Error(`Widget with id '${widget.id}' already added.`);
      }
      if (area !== "main") throw new Error(`fake shell: area ${area} is not modelled`);
      dock.addWidget(widget, options || {});
      shell.layoutModified.emit(shell, undefined);
    },
  };
  const commands = createFakeCommands();
  const app = { shell, commands, restored: Promise.resolve(), dock, panels, lumino };
  return app;
}

/** The page's `window.plrViewer` (D12): records every call. `names` is what `resources()` returns. */
export function createFakePlrViewer({ names = [] } = {}) {
  const viewer = {
    names,
    calls: [],
    resources() {
      viewer.calls.push(["resources"]);
      return viewer.names;
    },
    focus(name, view) {
      viewer.calls.push(["focus", name, view]);
    },
    view(name) {
      viewer.calls.push(["view", name]);
    },
    /** Every `focus`/`view` call, without the polling noise. */
    get actions() {
      return viewer.calls.filter((c) => c[0] !== "resources");
    },
  };
  return viewer;
}
