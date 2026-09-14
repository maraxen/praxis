// Minimal DOM stand-in for bun test. web-repl has no package.json and zero
// installed dependencies (NFR-3/AC-3), so the renderers are exercised against
// this stub instead of jsdom/happy-dom. It implements exactly the surface
// shell/coxswain renderers use: createElement, createTextNode, appendChild,
// textContent, className, setAttribute/getAttribute, title, classList.

export class FakeTextNode {
  constructor(data) {
    this.nodeType = 3;
    this.data = String(data);
  }
  get textContent() {
    return this.data;
  }
  set textContent(value) {
    this.data = String(value);
  }
}

export class FakeElement {
  constructor(tagName) {
    this.nodeType = 1;
    this.tagName = String(tagName).toUpperCase();
    this.childNodes = [];
    this._attributes = {};
    this.title = "";
    this.className = "";
    this.value = "";
    this.disabled = false;
  }

  get children() {
    // element children only -- what AC-15's "zero element children" counts
    return this.childNodes.filter((n) => n instanceof FakeElement);
  }

  appendChild(node) {
    if (typeof node === "string") node = new FakeTextNode(node);
    this.childNodes.push(node);
    return node;
  }

  append(...nodes) {
    for (const n of nodes) {
      if (Array.isArray(n)) for (const x of n) this.appendChild(x);
      else this.appendChild(n);
    }
  }

  setAttribute(name, value) {
    this._attributes[name] = String(value);
    if (name === "title") this.title = String(value);
    if (name === "class") this.className = String(value);
    if (name === "value") this.value = String(value);
  }

  getAttribute(name) {
    return name in this._attributes ? this._attributes[name] : null;
  }

  removeAttribute(name) {
    delete this._attributes[name];
  }

  get attributes() {
    return { ...this._attributes };
  }

  get classList() {
    const el = this;
    const tokens = () => el.className.split(/\s+/).filter(Boolean);
    return {
      add(...names) {
        const set = new Set(tokens());
        for (const n of names) set.add(n);
        el.className = [...set].join(" ");
      },
      remove(...names) {
        const set = new Set(tokens());
        for (const n of names) set.delete(n);
        el.className = [...set].join(" ");
      },
      contains(name) {
        return tokens().includes(name);
      },
    };
  }

  get textContent() {
    return this.childNodes.map((n) => n.textContent).join("");
  }
  set textContent(value) {
    this.childNodes = [];
    if (value !== "") this.appendChild(new FakeTextNode(value));
  }
}

export function createFakeDocument() {
  return {
    createElement(tag) {
      return new FakeElement(tag);
    },
    createTextNode(data) {
      return new FakeTextNode(data);
    },
  };
}
