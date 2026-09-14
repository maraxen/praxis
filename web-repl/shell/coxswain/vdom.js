// vdom.js -- the smallest possible DOM-building convention shared by the
// coxswain card renderers: plain virtual trees built with h(), materialized
// by mountTree against any document-like factory (real document in the
// browser, __tests__/dom_stub.js under bun test).
//
// NFR-7 discipline lives here structurally: strings become TEXT nodes, never
// markup; there is no innerHTML-adjacent API anywhere on this surface. This
// file contains no HTML string literals.

export function h(tag, attrs = {}, ...children) {
  return { tag, attrs, children };
}

/**
 * Materialize a virtual tree into real DOM. Attribute writes go through
 * setAttribute only; string children become text nodes.
 */
export function mountTree(tree, doc) {
  const el = doc.createElement(tree.tag);
  for (const [key, value] of Object.entries(tree.attrs || {})) {
    el.setAttribute(key, value);
  }
  for (const child of tree.children) {
    if (typeof child === "string") {
      el.appendChild(doc.createTextNode(child));
    } else if (child && typeof child.tag === "string") {
      el.appendChild(mountTree(child, doc));
    }
  }
  return el;
}
