// panel_dom.js -- a minimal fake DOM and window for driving panel.js's `mount`
// under bun, with no browser (task 260929_notebook-display-design, backlog
// #5653: restyle the persistence UI with the epic tokens, no behaviour change).
//
// What it is for. panel.js is only ever exercised by the real-browser
// `--persistence-check`. This harness lets a unit test pin the DOM panel.js
// builds (tags, attributes, text, nesting) and the inline style keys it sets,
// so a pure restyle can be shown not to have moved anything the gate reads.
// It is deliberately small: it implements exactly what panel.js touches and
// nothing else, and reflects the properties panel.js assigns (`id`, `type`,
// `hidden`, `tabIndex`, `rel`, `href`) to attributes the way a real DOM does,
// so a snapshot of attributes is a snapshot of the markup.
//
// Not a test file (no `.test.js` suffix), like fakes.js.

class FakeText {
  constructor(text) {
    this.text = String(text);
    this.parentNode = null;
  }
}

const REFLECTED = { id: "id", type: "type", rel: "rel", href: "href", tabIndex: "tabindex" };

export class FakeElement {
  constructor(tag, doc) {
    this.localName = tag;
    this.ownerDocument = doc;
    this.children = [];
    this.parentNode = null;
    this.style = {};
    this._attrs = new Map();
    this._listeners = new Map();
    this.open = false; // <dialog>
    this.focused = false;
  }

  // -- reflected properties ------------------------------------------------
  set id(v) { this._attrs.set("id", String(v)); }
  get id() { return this._attrs.get("id") ?? ""; }
  set type(v) { this._attrs.set("type", String(v)); }
  get type() { return this._attrs.get("type") ?? ""; }
  set rel(v) { this._attrs.set("rel", String(v)); }
  get rel() { return this._attrs.get("rel") ?? ""; }
  set href(v) { this._attrs.set("href", String(v)); }
  get href() { return this._attrs.get("href") ?? ""; }
  set tabIndex(v) { this._attrs.set("tabindex", String(v)); }
  get tabIndex() { return Number(this._attrs.get("tabindex") ?? -1); }
  set hidden(v) {
    if (v) this._attrs.set("hidden", "");
    else this._attrs.delete("hidden");
  }
  get hidden() { return this._attrs.has("hidden"); }

  setAttribute(name, value) { this._attrs.set(name, String(value)); }
  getAttribute(name) { return this._attrs.has(name) ? this._attrs.get(name) : null; }
  hasAttribute(name) { return this._attrs.has(name); }

  // -- tree ----------------------------------------------------------------
  _adopt(node) {
    if (node.parentNode) node.parentNode._remove(node);
    node.parentNode = this;
    this.children.push(node);
  }
  _remove(node) {
    this.children = this.children.filter((c) => c !== node);
    node.parentNode = null;
  }
  appendChild(node) {
    this._adopt(node);
    return node;
  }
  append(...nodes) {
    for (const n of nodes) this._adopt(typeof n === "string" ? new FakeText(n) : n);
  }
  replaceChildren(...nodes) {
    for (const c of this.children) c.parentNode = null;
    this.children = [];
    this.append(...nodes);
  }
  set textContent(v) {
    this.replaceChildren(String(v));
  }
  get textContent() {
    return this.children.map((c) => (c instanceof FakeText ? c.text : c.textContent)).join("");
  }

  // -- events / focus / dialog ----------------------------------------------
  addEventListener(type, fn) {
    if (!this._listeners.has(type)) this._listeners.set(type, []);
    this._listeners.get(type).push(fn);
  }
  dispatch(type, event = {}) {
    for (const fn of this._listeners.get(type) ?? []) fn({ type, preventDefault() {}, ...event });
  }
  focus() { this.focused = true; }
  showModal() { this.open = true; }
  close() { this.open = false; }

  // `button, [tabindex]` is the only selector panel.js passes (focusDialog).
  querySelector(selector) {
    const parts = selector.split(",").map((s) => s.trim());
    const hit = (el) =>
      parts.some((p) => (p.startsWith("[") ? el.hasAttribute(p.slice(1, -1)) : el.localName === p));
    const walk = (el) => {
      for (const c of el.children) {
        if (c instanceof FakeText) continue;
        if (hit(c)) return c;
        const deeper = walk(c);
        if (deeper) return deeper;
      }
      return null;
    };
    return walk(this);
  }
}

export class FakeDocument {
  constructor() {
    this.head = new FakeElement("head", this);
    this.body = new FakeElement("body", this);
  }
  createElement(tag) {
    return new FakeElement(tag, this);
  }
  getElementById(id) {
    const walk = (el) => {
      for (const c of el.children) {
        if (c instanceof FakeText) continue;
        if (c.id === id) return c;
        const deeper = walk(c);
        if (deeper) return deeper;
      }
      return null;
    };
    return walk(this.head) ?? walk(this.body);
  }
}

/** A key/value store with the `Storage` surface core.js uses. */
function fakeLocalStorage() {
  const map = new Map();
  return {
    getItem: (k) => (map.has(k) ? map.get(k) : null),
    setItem: (k, v) => map.set(k, String(v)),
    removeItem: (k) => map.delete(k),
  };
}

/** `indexedDB.open` for the raw handle store: every `get` resolves undefined. */
export function installFakeIndexedDb() {
  const tick = (fn) => queueMicrotask(fn);
  const store = {
    get() {
      const request = {};
      tick(() => {
        request.result = undefined;
        request.onsuccess?.();
      });
      return request;
    },
    put() {},
  };
  const conn = {
    objectStoreNames: { contains: () => true },
    createObjectStore: () => store,
    transaction() {
      return { objectStore: () => store };
    },
  };
  globalThis.indexedDB = {
    open() {
      const request = { result: conn };
      tick(() => request.onsuccess?.());
      return request;
    },
  };
}

/**
 * A window for `mount`. `fsa: false` removes `showDirectoryPicker` (the
 * non-Chromium branch, harness S3). Returns `{ win, doc, commandHandlers }`;
 * `commandHandlers` holds whatever panel.js connected to
 * `commands.commandExecuted`, so a test can fire a save.
 */
export function makeWindow({ fsa = true } = {}) {
  const doc = new FakeDocument();
  const commandHandlers = [];
  const win = {
    document: doc,
    isSecureContext: true,
    localStorage: fakeLocalStorage(),
    navigator: { storage: { persist: async () => true, persisted: async () => false } },
    setInterval: (...a) => setInterval(...a),
    clearInterval: (...a) => clearInterval(...a),
    jupyterapp: {
      restored: Promise.resolve(),
      commands: { commandExecuted: { connect: (fn) => commandHandlers.push(fn) } },
      serviceManager: {
        contents: {
          fileChanged: { connect() {} },
          get: async () => ({ content: [] }),
          save: async () => ({}),
        },
      },
    },
  };
  if (fsa) win.showDirectoryPicker = async () => ({});
  return { win, doc, commandHandlers };
}

// -- snapshots ---------------------------------------------------------------

/** Tag, attributes (sorted; `style` is not an attribute here) and children. */
export function snapshot(node) {
  if (node instanceof FakeText) return node.text;
  const attrs = {};
  for (const k of [...node._attrs.keys()].sort()) attrs[k] = node._attrs.get(k);
  const out = { tag: node.localName, attrs, children: node.children.map(snapshot) };
  if (node.localName === "dialog") out.open = node.open;
  return out;
}

/** Every element under `node` (and `node` itself), depth first. */
export function elementsOf(node) {
  const out = [node];
  for (const c of node.children) if (!(c instanceof FakeText)) out.push(...elementsOf(c));
  return out;
}

const tick = () => new Promise((resolve) => setTimeout(resolve, 0));

/**
 * Mount `panelModule.mount` in a fresh fake window and walk three states:
 * the initial render, the panel opened by a chip click, and the first-save
 * modal opened by an explicit save. Returns the snapshots of `body`'s children
 * (root, dialog) for each, plus the live elements for style/attribute checks.
 */
export async function captureStates(panelModule, { fsa = true } = {}) {
  installFakeIndexedDb();
  const { win, doc, commandHandlers } = makeWindow({ fsa });
  await panelModule.mount(win);
  const [root, dialog] = doc.body.children;
  const chip = root.children[0];
  const states = { initial: doc.body.children.map(snapshot) };

  chip.dispatch("click");
  states.panelOpen = doc.body.children.map(snapshot);
  chip.dispatch("click"); // close it again so the modal state is independent

  for (const handler of commandHandlers) handler(null, { id: "docmanager:save", result: undefined });
  await tick();
  await tick();
  states.modal = doc.body.children.map(snapshot);

  return { states, doc, win, root, dialog, chip };
}
