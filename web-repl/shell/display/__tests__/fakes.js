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
 * synchronous stand-in for setInterval/clearInterval. */
export function createFakeWindow({ app = null, document = null, broadcast = null } = {}) {
  const timers = new Map();
  let nextId = 1;
  const win = {
    jupyterapp: app,
    ...(document ? { document } : {}),
    ...(broadcast ? { BroadcastChannel: broadcast.BroadcastChannel } : {}),
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

  addEventListener(type, fn) {
    if (!this._listeners.some((l) => l.type === type && l.fn === fn)) this._listeners.push({ type, fn });
  }

  removeEventListener(type, fn) {
    this._listeners = this._listeners.filter((l) => !(l.type === type && l.fn === fn));
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
    for (let node = this; node && !event.propagationStopped; node = node.parentNode) {
      event.currentTarget = node;
      for (const l of (node._listeners || []).slice()) if (l.type === type) l.fn(event);
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
    return new FakeElement(tag, this);
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
    post(name, data) {
      const sender = new FakeBroadcastChannel(name);
      sender.postMessage(data);
      sender.close();
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
