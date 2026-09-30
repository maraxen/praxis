// interact.js -- hover readout, keyboard navigation and click-to-focus for
// Praxis outputs (spec .praxia/docs/specs/260929_notebook-display-epic.md
// section 3.4 "Interaction", D12 Click, D14 "One shell script owns all
// interaction", D2 "Escaping", section 4 interact.js row, AC-19; task B9).
//
// Outputs carry no script (D2). They carry data the shell reads:
//   data-praxis-res     the resource group, holding the FULL resource name
//   data-praxis-grid    compact JSON: v, kind ("volume"|"tip"), res, x0, y0,
//                       dx, dy, rows, cols, ids (space-joined), vals, flags.
//                       A well at row r (A = 0), column c (1-based) sits at
//                       (x0 + (c-1)*dx, y0 + r*dy) in the svg's user units.
//   tabindex, role, aria-label   on plate and tip-rack figures and on the
//                       OUTER group of a deck. Inner deck groups (carriers,
//                       labware, fixtures) carry data-praxis-res only, and
//                       full-detail labware also a grid; blocked labware none.
//
// ONE delegated listener per event type on the document, so outputs added or
// re-attached later work with no wiring:
//   mousemove / mouseout   a small readout ("assay B3: 100 µL", "tips_300 C2:
//                          tip" / "taken") positioned by the shell (.praxis-readout)
//   focusin / keydown      Tab focuses a figure; a focus ring (.praxis-focus-ring,
//                          an svg rect) starts at the first well; the arrow keys
//                          move it, clamped at the edges (no wrap); Escape leaves
//                          the grid. One shell-owned aria-live="polite" region
//                          announces the SAME text as the hover readout.
//   click                  the nearest data-praxis-res ancestor is the resource:
//                          `dock.focus(name)` gets its exact name, and the output
//                          gets the persistent rose outline (class `is-focus` on
//                          its .praxis-out root, one output at a time).
//
// NAMES ARE DATA (D14, D2). A resource name is user-controlled. It is compared
// and passed on as a string (`el.dataset.praxisRes`), written into the DOM only
// through textContent, and never interpolated into a selector: nodes are found by
// walking parentNode, never by a selector built from a name.
//
// DEGRADES SILENTLY. On an untrusted reopen (S2) the SVG, every data-* and
// tabindex are stripped, so there is nothing to find and nothing happens. A
// malformed data-praxis-grid gives no readout and no ring. Every handler runs
// under its own try/catch and logs with `logger.error`; nothing here throws out
// of a listener, and nothing here touches the notebook model.
//
// Coordinates: the pointer's client position maps to svg user units through the
// svg's bounding rect and viewBox.
//
// Pure, exported for tests: rowLabel, parseGrid, hitTest, moveCursor, readoutText.

const SVG_NS = "http://www.w3.org/2000/svg";
const KINDS = new Set(["volume", "tip"]);
/** Sanity caps on a descriptor (the largest labware is a 1536-well plate). */
const MAX_GRID_TEXT = 200000;
const MAX_DIM = 64;
const MAX_CELLS = 4096;
const ARROWS = {
  ArrowRight: [0, 1],
  ArrowLeft: [0, -1],
  ArrowDown: [1, 0],
  ArrowUp: [-1, 0],
};
const MAX_DEPTH = 500;

const hasOwn = Object.prototype.hasOwnProperty;
const own = (obj, key) => (obj !== null && typeof obj === "object" && hasOwn.call(obj, key) ? obj[key] : undefined);

// -- pure ------------------------------------------------------------------------------------------

/** PLR's row labels: A..Z, then AA, AB, ... (labware.py `_row_label`). */
export function rowLabel(index) {
  if (index < 26) return String.fromCharCode(65 + index);
  return String.fromCharCode(64 + Math.floor(index / 26)) + String.fromCharCode(65 + (index % 26));
}

/** "B12" -> {row: 1, col: 12} (row 0 = A), or null. */
function parseId(id) {
  const m = /^([A-Z]{1,2})([1-9][0-9]*)$/.exec(id);
  if (!m) return null;
  const label = m[1];
  const row =
    label.length === 1
      ? label.charCodeAt(0) - 65
      : (label.charCodeAt(0) - 64) * 26 + (label.charCodeAt(1) - 65);
  return { row, col: Number(m[2]) };
}

const posKey = (row, col) => `${row},${col}`;

/**
 * Parse and validate a `data-praxis-grid` value. Returns
 * `{kind, res, x0, y0, dx, dy, rows, cols, ids: string[], vals: number[], byPos}`
 * or null when it is not a well-formed v1 descriptor. Never throws.
 */
export function parseGrid(text) {
  try {
    if (typeof text !== "string" || text.length > MAX_GRID_TEXT) return null;
    const d = JSON.parse(text);
    if (d === null || typeof d !== "object" || Array.isArray(d)) return null;
    if (own(d, "v") !== 1) return null;
    const kind = own(d, "kind");
    if (typeof kind !== "string" || !KINDS.has(kind)) return null;
    const res = own(d, "res");
    if (typeof res !== "string") return null;
    const x0 = own(d, "x0");
    const y0 = own(d, "y0");
    const dx = own(d, "dx");
    const dy = own(d, "dy");
    if (![x0, y0, dx, dy].every((n) => typeof n === "number" && Number.isFinite(n))) return null;
    if (!(dx > 0) || !(dy > 0)) return null;
    const rows = own(d, "rows");
    const cols = own(d, "cols");
    for (const n of [rows, cols]) {
      if (!Number.isInteger(n) || n < 1 || n > MAX_DIM) return null;
    }
    if (rows * cols > MAX_CELLS) return null;

    const idText = own(d, "ids");
    const vals = own(d, "vals");
    if (typeof idText !== "string" || !Array.isArray(vals)) return null;
    const ids = idText.split(" ");
    if (ids.length !== vals.length || ids.length > rows * cols) return null;

    const byPos = new Map();
    const pos = [];
    for (let i = 0; i < ids.length; i += 1) {
      const p = parseId(ids[i]);
      if (!p || p.row >= rows || p.col > cols) return null;
      const key = posKey(p.row, p.col);
      if (byPos.has(key)) return null;
      byPos.set(key, i);
      pos.push(p);
      const v = vals[i];
      if (typeof v !== "number" || !Number.isFinite(v)) return null;
      if (kind === "tip" && v !== 0 && v !== 1) return null;
    }
    return { kind, res, x0, y0, dx, dy, rows, cols, ids, vals, pos, byPos };
  } catch {
    return null;
  }
}

/**
 * The index of the well under the point (x, y) in the svg's user units, or
 * null. A well owns the pitch cell centred on it: [centre - pitch/2, centre +
 * pitch/2), so the near edge of the grid is inclusive and the far edge exclusive,
 * and a point on the boundary between two wells goes to the higher index.
 */
export function hitTest(grid, x, y) {
  if (!grid || !Number.isFinite(x) || !Number.isFinite(y)) return null;
  const col = Math.floor((x - grid.x0) / grid.dx + 0.5) + 1;
  const row = Math.floor((y - grid.y0) / grid.dy + 0.5);
  if (col < 1 || col > grid.cols || row < 0 || row >= grid.rows) return null;
  const index = grid.byPos.get(posKey(row, col));
  return index === undefined ? null : index;
}

/** The index the cursor moves to on `key`, clamped at the edges (no wrap): an
 * arrow onto a position with no well, or any other key, leaves it where it is. */
export function moveCursor(grid, index, key) {
  if (!grid || typeof key !== "string" || !hasOwn.call(ARROWS, key)) return index;
  const at = grid.pos[index];
  if (!at) return index;
  const [dRow, dCol] = ARROWS[key];
  const next = grid.byPos.get(posKey(at.row + dRow, at.col + dCol));
  return next === undefined ? index : next;
}

const tidy = (n) => String(Math.round(n * 100) / 100);

/** The readout / live-region text of well `index`, or null. */
export function readoutText(grid, index) {
  if (!grid || !Number.isInteger(index) || index < 0 || index >= grid.ids.length) return null;
  const id = grid.ids[index];
  const value = grid.vals[index];
  if (grid.kind === "tip") return `${grid.res} ${id}: ${value === 1 ? "tip" : "taken"}`;
  return `${grid.res} ${id}: ${tidy(value)} µL`;
}

// -- DOM helpers (no selectors built from names) -------------------------------------------------------

/** The nearest ancestor-or-self carrying a non-empty data-praxis-res. */
function findRes(target) {
  let el = target;
  for (let depth = 0; el && depth < MAX_DEPTH; depth += 1, el = el.parentNode) {
    const dataset = el.dataset;
    if (dataset && typeof dataset.praxisRes === "string" && dataset.praxisRes !== "") return el;
  }
  return null;
}

function findAncestor(el, test) {
  let node = el;
  for (let depth = 0; node && depth < MAX_DEPTH; depth += 1, node = node.parentNode) {
    if (test(node)) return node;
  }
  return null;
}

const hasClass = (name) => (node) => Boolean(node.classList && node.classList.contains(name));
const isSvg = (node) => node.localName === "svg" || String(node.tagName).toLowerCase() === "svg";

function clientToUser(svg, clientX, clientY) {
  const rect = svg.getBoundingClientRect();
  const box = String(svg.getAttribute("viewBox") || "")
    .trim()
    .split(/[\s,]+/)
    .map(Number);
  if (box.length !== 4 || !box.every(Number.isFinite) || !(box[2] > 0) || !(box[3] > 0)) return null;
  if (!(rect.width > 0) || !(rect.height > 0)) return null;
  return {
    x: box[0] + ((clientX - rect.left) * box[2]) / rect.width,
    y: box[1] + ((clientY - rect.top) * box[3]) / rect.height,
  };
}

// -- the controller ---------------------------------------------------------------------------------------

/**
 * Mount the interaction layer.
 *
 * @param {object} opts
 * @param opts.win          the window (`document`)
 * @param opts.logger       console-like; defaults to `console`
 * @param opts.controllers  what earlier modules returned; `controllers.dock`
 *                          (sprint C) is read at click time
 * @param opts.dock         an explicit dock API (`{focus(name)}`), overriding
 * @returns {{dispose(): void, focused(): (string|null)}}
 */
export function mountInteract({ win, logger = console, controllers = {}, dock } = {}) {
  const doc = win ? win.document : undefined;
  const inert = { dispose() {}, focused: () => null };
  if (!doc || typeof doc.addEventListener !== "function") {
    if (logger && typeof logger.warn === "function") {
      logger.warn("praxis display interact: no document; output interaction is off.");
    }
    return inert;
  }

  let readout = null;
  let live = null;
  let cursor = null; // {g, grid, index, ring}
  let focusedOutput = null;
  let focusedName = null;
  let disposed = false;
  const grids = new WeakMap(); // resource group -> {text, grid}

  function guarded(label, fn) {
    return (...args) => {
      if (disposed) return undefined;
      try {
        return fn(...args);
      } catch (err) {
        logger.error(`praxis display interact: ${label} failed:`, err);
        return undefined;
      }
    };
  }

  const attach = (el) => {
    if (doc.body && !el.parentNode) doc.body.appendChild(el);
  };
  const detach = (el) => {
    if (el && el.parentNode) el.parentNode.removeChild(el);
  };

  // -- the grid of a resource group -----------------------------------------------------------------------

  function gridOf(g) {
    const text = typeof g.getAttribute === "function" ? g.getAttribute("data-praxis-grid") : null;
    if (typeof text !== "string") return null;
    const cached = grids.get(g);
    if (cached && cached.text === text) return cached.grid;
    const grid = parseGrid(text);
    grids.set(g, { text, grid });
    return grid;
  }

  // -- the live region (one, shell-owned) ----------------------------------------------------------------------

  function ensureLive() {
    if (live) {
      attach(live);
      return live;
    }
    const el = doc.createElement("div");
    el.setAttribute("aria-live", "polite");
    el.setAttribute("aria-atomic", "true");
    el.setAttribute("data-praxis-live", "");
    Object.assign(el.style, {
      position: "absolute",
      width: "1px",
      height: "1px",
      overflow: "hidden",
      clip: "rect(0 0 0 0)",
      whiteSpace: "nowrap",
    });
    live = el;
    attach(el);
    return el;
  }

  function setLive(text) {
    const el = ensureLive();
    if (el.textContent !== text) el.textContent = text;
  }

  // -- the hover readout -----------------------------------------------------------------------------------------

  function showReadout(text, clientX, clientY) {
    if (!readout) {
      readout = doc.createElement("div");
      readout.classList.add("praxis-readout");
      readout.setAttribute("aria-hidden", "true"); // the live region announces; this is for the eye
    }
    attach(readout);
    readout.textContent = text;
    readout.style.left = `${clientX + 12}px`;
    readout.style.top = `${clientY + 16}px`;
    readout.style.display = "";
  }

  function hideReadout() {
    if (readout) readout.style.display = "none";
  }

  const onMouseMove = guarded("hover", (event) => {
    const g = findRes(event.target);
    const grid = g ? gridOf(g) : null;
    const svg = g ? findAncestor(g, isSvg) : null;
    if (!grid || !svg) return hideReadout();
    const at = clientToUser(svg, event.clientX, event.clientY);
    if (!at) return hideReadout();
    const index = hitTest(grid, at.x, at.y);
    const text = index === null ? null : readoutText(grid, index);
    if (text === null) return hideReadout();
    return showReadout(text, event.clientX, event.clientY);
  });

  const onMouseOut = guarded("hover end", () => hideReadout());

  // -- the keyboard cursor ---------------------------------------------------------------------------------------------

  const round3 = (n) => Math.round(n * 1000) / 1000;

  function drawCursor() {
    const { g, grid, index } = cursor;
    const at = grid.pos[index];
    if (!cursor.ring || cursor.ring.parentNode !== g) {
      const ring = doc.createElementNS(SVG_NS, "rect");
      ring.classList.add("praxis-focus-ring");
      ring.setAttribute("aria-hidden", "true");
      g.appendChild(ring);
      cursor.ring = ring;
    }
    const { ring } = cursor;
    ring.setAttribute("x", String(round3(grid.x0 + (at.col - 1) * grid.dx - grid.dx / 2)));
    ring.setAttribute("y", String(round3(grid.y0 + at.row * grid.dy - grid.dy / 2)));
    ring.setAttribute("width", String(round3(grid.dx)));
    ring.setAttribute("height", String(round3(grid.dy)));
    setLive(readoutText(grid, index) ?? "");
  }

  function clearCursor() {
    if (!cursor) return;
    detach(cursor.ring);
    cursor = null;
    if (live) setLive("");
  }

  function startCursor(g, grid) {
    clearCursor();
    cursor = { g, grid, index: 0, ring: null };
    drawCursor();
  }

  const onFocusIn = guarded("focus in", (event) => {
    const g = findRes(event.target);
    const grid = g ? gridOf(g) : null;
    if (!g || !grid) return clearCursor();
    return startCursor(g, grid);
  });

  const onFocusOut = guarded("focus out", (event) => {
    if (cursor && findRes(event.target) === cursor.g) clearCursor();
  });

  const onKeyDown = guarded("key", (event) => {
    const key = event.key;
    if (key === "Escape") return clearCursor(); // leave the grid; JupyterLab keeps its own Escape
    if (typeof key !== "string" || !hasOwn.call(ARROWS, key)) return undefined;
    const g = findRes(event.target);
    const grid = g ? gridOf(g) : null;
    if (!g || !grid) return undefined; // e.g. a deck's outer group: nothing to navigate
    if (!cursor || cursor.g !== g) {
      startCursor(g, grid);
    } else {
      cursor.index = moveCursor(cursor.grid, cursor.index, key);
      drawCursor();
    }
    event.preventDefault();
    if (typeof event.stopPropagation === "function") event.stopPropagation();
    return undefined;
  });

  // -- click ------------------------------------------------------------------------------------------------------------------

  function setFocusedOutput(container, name) {
    if (focusedOutput && focusedOutput !== container) focusedOutput.classList.remove("is-focus");
    if (container) container.classList.add("is-focus");
    focusedOutput = container;
    focusedName = name;
  }

  const onClick = guarded("click", (event) => {
    const g = findRes(event.target);
    if (!g) return;
    const name = g.dataset.praxisRes; // exactly the resource name; never a selector
    const output = findAncestor(g, hasClass("praxis-out")) || findAncestor(g, hasClass("jp-OutputArea-output"));
    setFocusedOutput(output, name);
    const target = dock ?? (controllers ? controllers.dock : undefined);
    if (target && typeof target.focus === "function") target.focus(name);
  });

  // -- wiring ---------------------------------------------------------------------------------------------------------------------

  const listeners = [
    ["mousemove", onMouseMove, false],
    ["mouseout", onMouseOut, false],
    ["click", onClick, false],
    ["focusin", onFocusIn, false],
    ["focusout", onFocusOut, false],
    ["keydown", onKeyDown, true], // capture: ahead of the notebook's own arrow-key commands
  ];
  for (const [type, handler, capture] of listeners) doc.addEventListener(type, handler, capture);
  ensureLive();

  return {
    focused: () => focusedName,
    dispose() {
      if (disposed) return;
      for (const [type, handler, capture] of listeners) doc.removeEventListener(type, handler, capture);
      clearCursor();
      detach(readout);
      detach(live);
      if (focusedOutput) focusedOutput.classList.remove("is-focus");
      readout = null;
      live = null;
      focusedOutput = null;
      focusedName = null;
      disposed = true;
    },
  };
}
