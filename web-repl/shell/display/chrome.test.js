// chrome.test.js -- AC-5 (cell-state logic) and section 3.1 of the notebook
// display epic (.praxia/docs/specs/260929_notebook-display-epic.md, task A5).
//
// Ground truth for the five states is the S1 spike record
// (.praxia/docs/research/260929_notebook-display-s1-lumino-widget.md,
// outcome s1_a): not-run / running / ran come from the notebook MODEL,
// error from an `error` output, stale from source-vs-snapshot (section 3.1),
// and the notebook runs in windowingMode contentVisibility.

import { describe, expect, test } from "bun:test";

import {
  CELL_STATES,
  EXEC_ATTR,
  STATE_ATTR,
  cellState,
  mountChrome,
  writeCellAttrs,
} from "./chrome.js";
import {
  createFakeApp,
  createFakeCell,
  createFakeCellModel,
  createFakeNode,
  createFakeNotebookPanel,
} from "./__tests__/fakes.js";

const state = (cell) => cell.node.getAttribute(STATE_ATTR);
const exec = (cell) => cell.node.getAttribute(EXEC_ATTR);

function silentLogger() {
  const errors = [];
  return { errors, error: (...a) => errors.push(a), warn: () => {}, log: () => {} };
}

function chromeFor(panels, options = {}) {
  const app = createFakeApp({ panels });
  const logger = silentLogger();
  const chrome = mountChrome({ app, logger, ...options });
  return { app, chrome, logger };
}

describe("constants", () => {
  test("the five states and the two attribute names are the spec's", () => {
    expect([...CELL_STATES].sort()).toEqual(["error", "not-run", "ran", "running", "stale"]);
    expect(STATE_ATTR).toBe("data-praxis-cell-state");
    expect(EXEC_ATTR).toBe("data-praxis-exec");
  });
});

describe("cellState (pure; AC-5)", () => {
  const model = (o) => createFakeCellModel(o);

  test("not-run: no execution count", () => {
    expect(cellState(model({ source: "x = 1" }), { running: false, snapshot: null })).toBe("not-run");
  });

  test("ran: a successful execution, source equal to the snapshot", () => {
    const m = model({ source: "x = 1", executionCount: 1, outputs: ["stream"] });
    expect(cellState(m, { running: false, snapshot: "x = 1" })).toBe("ran");
  });

  test("ran: an execution count of 0 is a run (null, not falsy, means never run)", () => {
    const m = model({ source: "x = 1", executionCount: 0 });
    expect(cellState(m, { running: false, snapshot: "x = 1" })).toBe("ran");
  });

  test("running while executing", () => {
    const m = model({ source: "x = 1", executionState: "running" });
    expect(cellState(m, { running: true, snapshot: null })).toBe("running");
  });

  test("error: an output whose type is error", () => {
    const m = model({ source: "1/0", executionCount: 2, outputs: ["error"] });
    expect(cellState(m, { running: false, snapshot: "1/0" })).toBe("error");
  });

  test("error: found among several outputs, not only the last", () => {
    const m = model({ source: "s", executionCount: 2, outputs: ["stream", "error", "stream"] });
    expect(cellState(m, { running: false, snapshot: "s" })).toBe("error");
  });

  test("not error: a stream or display output is ran", () => {
    const m = model({ source: "s", executionCount: 2, outputs: ["stream", "display_data", "execute_result"] });
    expect(cellState(m, { running: false, snapshot: "s" })).toBe("ran");
  });

  test("stale: non-null count, a snapshot, and the source differs from it", () => {
    const m = model({ source: "x = 2", executionCount: 1, outputs: ["stream"] });
    expect(cellState(m, { running: false, snapshot: "x = 1" })).toBe("stale");
  });

  test("stale requires a snapshot: count set but no snapshot is not stale", () => {
    const m = model({ source: "x = 2", executionCount: 1, outputs: ["stream"] });
    expect(cellState(m, { running: false, snapshot: null })).toBe("ran");
  });

  test("stale requires a non-null count: snapshot set but count null is not stale", () => {
    const m = model({ source: "x = 2", executionCount: null });
    expect(cellState(m, { running: false, snapshot: "x = 1" })).toBe("not-run");
  });

  test("an edited cell that never ran (null count, no snapshot) is not-run", () => {
    const m = model({ source: "edited but never executed", executionCount: null });
    expect(cellState(m, { running: false, snapshot: null })).toBe("not-run");
  });

  test("an empty-string snapshot is a snapshot (empty source, then typed)", () => {
    const m = model({ source: "x", executionCount: 1 });
    expect(cellState(m, { running: false, snapshot: "" })).toBe("stale");
  });

  test("precedence: a running cell whose source was edited is running", () => {
    const m = model({ source: "edited", executionCount: 1, executionState: "running" });
    expect(cellState(m, { running: true, snapshot: "original" })).toBe("running");
  });

  test("precedence: an edited cell whose last output is an error is stale", () => {
    const m = model({ source: "edited", executionCount: 3, outputs: ["error"] });
    expect(cellState(m, { running: false, snapshot: "original" })).toBe("stale");
  });

  test("precedence: running beats error", () => {
    const m = model({ source: "s", executionCount: 3, outputs: ["error"], executionState: "running" });
    expect(cellState(m, { running: true, snapshot: "s" })).toBe("running");
  });

  test("precedence: error beats ran and not-run", () => {
    const withCount = model({ source: "s", executionCount: 3, outputs: ["error"] });
    const noCount = model({ source: "s", executionCount: null, outputs: ["error"] });
    expect(cellState(withCount, { running: false, snapshot: "s" })).toBe("error");
    expect(cellState(noCount, { running: false, snapshot: null })).toBe("error");
  });

  test("defaults: no options is not running and has no snapshot", () => {
    expect(cellState(model({ source: "s", executionCount: 1 }))).toBe("ran");
    expect(cellState(model({ source: "s" }))).toBe("not-run");
  });

  // Negative control for the whole table above: every state is reachable and
  // no two of the five hand-built situations collapse to one answer.
  test("negative control: the five canonical situations give five distinct states", () => {
    const got = new Set([
      cellState(model({ source: "a" }), { running: false, snapshot: null }),
      cellState(model({ source: "a", executionCount: 1 }), { running: false, snapshot: "a" }),
      cellState(model({ source: "a" }), { running: true, snapshot: null }),
      cellState(model({ source: "a", executionCount: 1, outputs: ["error"] }), { running: false, snapshot: "a" }),
      cellState(model({ source: "b", executionCount: 1 }), { running: false, snapshot: "a" }),
    ]);
    expect(got.size).toBe(5);
  });
});

describe("writeCellAttrs (DOM writer; AC-5)", () => {
  test("sets data-praxis-cell-state and data-praxis-exec", () => {
    const node = createFakeNode();
    writeCellAttrs(node, "ran", 4);
    expect(node.getAttribute(STATE_ATTR)).toBe("ran");
    expect(node.getAttribute(EXEC_ATTR)).toBe("4");
  });

  test("a null execution count writes an empty exec attribute", () => {
    const node = createFakeNode();
    writeCellAttrs(node, "not-run", null);
    expect(node.getAttribute(STATE_ATTR)).toBe("not-run");
    expect(node.getAttribute(EXEC_ATTR)).toBe("");
  });

  test("count 0 is written as 0, not blanked", () => {
    const node = createFakeNode();
    writeCellAttrs(node, "ran", 0);
    expect(node.getAttribute(EXEC_ATTR)).toBe("0");
  });

  test("idempotent: a second identical write touches nothing and reports no change", () => {
    const node = createFakeNode();
    expect(writeCellAttrs(node, "ran", 4)).toBe(true);
    const calls = node.setAttributeCalls.length;
    expect(writeCellAttrs(node, "ran", 4)).toBe(false);
    expect(node.setAttributeCalls.length).toBe(calls);
  });

  test("a change writes only the attribute that changed", () => {
    const node = createFakeNode();
    writeCellAttrs(node, "ran", 4);
    const calls = node.setAttributeCalls.length;
    expect(writeCellAttrs(node, "stale", 4)).toBe(true);
    expect(node.setAttributeCalls.slice(calls)).toEqual([[STATE_ATTR, "stale"]]);
  });

  test("an unknown state is refused, loudly, and nothing is written", () => {
    const node = createFakeNode();
    expect(() => writeCellAttrs(node, "sparkly", 1)).toThrow();
    expect(node.setAttributeCalls.length).toBe(0);
  });
});

describe("mountChrome: state from the model at first observation", () => {
  test("a fresh notebook: never-run cells are not-run with an empty count", () => {
    const cell = createFakeCell({ source: "x = 1" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    expect(state(cell)).toBe("not-run");
    expect(exec(cell)).toBe("");
  });

  test("a loaded notebook: saved outputs give ran and error, with counts", () => {
    const ran = createFakeCell({ source: "print(1)", executionCount: 1, outputs: ["stream"] });
    const bad = createFakeCell({ source: "1/0", executionCount: 2, outputs: ["error"] });
    chromeFor([createFakeNotebookPanel({ cells: [ran, bad] })]);
    expect([state(ran), exec(ran)]).toEqual(["ran", "1"]);
    expect([state(bad), exec(bad)]).toEqual(["error", "2"]);
  });

  test("after a reload a cell becomes stale only after an edit in this page", () => {
    const cell = createFakeCell({ source: "print(1)", executionCount: 1, outputs: ["stream"] });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    expect(state(cell)).toBe("ran");
    cell.model.setSource("print(2)");
    expect(state(cell)).toBe("stale");
  });

  test("restoring the original text of an edited cell returns it to ran", () => {
    const cell = createFakeCell({ source: "print(1)", executionCount: 1, outputs: ["stream"] });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.setSource("print(2)");
    cell.model.setSource("print(1)");
    expect(state(cell)).toBe("ran");
  });

  test("an edited never-run cell stays not-run through every edit", () => {
    const cell = createFakeCell({ source: "" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.setSource("a");
    expect(state(cell)).toBe("not-run");
    cell.model.setSource("ab");
    expect(state(cell)).toBe("not-run");
  });

  test("markdown and raw cells are not touched", () => {
    const md = createFakeCell({ type: "markdown", source: "# hi" });
    const raw = createFakeCell({ type: "raw", source: "raw" });
    chromeFor([createFakeNotebookPanel({ cells: [md, raw] })]);
    expect(md.node.setAttributeCalls).toEqual([]);
    expect(raw.node.setAttributeCalls).toEqual([]);
  });
});

describe("mountChrome: transitions", () => {
  test("not-run -> running -> ran, then an edit makes it stale", () => {
    const cell = createFakeCell({ source: "x = 1" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    expect(state(cell)).toBe("not-run");
    cell.model.startExecution();
    expect(state(cell)).toBe("running");
    cell.model.finishExecution({ count: 1 });
    expect(state(cell)).toBe("ran");
    expect(exec(cell)).toBe("1");
    cell.model.setSource("x = 2");
    expect(state(cell)).toBe("stale");
  });

  test("the same run reaches ran whether the count or the idle state arrives last", () => {
    const a = createFakeCell({ source: "a" });
    const b = createFakeCell({ source: "b" });
    chromeFor([createFakeNotebookPanel({ cells: [a, b] })]);
    a.model.startExecution();
    a.model.finishExecution({ count: 1, countBeforeIdle: true });
    b.model.startExecution();
    b.model.finishExecution({ count: 2, countBeforeIdle: false });
    expect(state(a)).toBe("ran");
    expect(state(b)).toBe("ran");
  });

  test("running: editing while it runs stays running, and is stale once it finishes", () => {
    const cell = createFakeCell({ source: "v1" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.startExecution();
    cell.model.setSource("v2");
    expect(state(cell)).toBe("running");
    cell.model.finishExecution({ count: 1 });
    expect(state(cell)).toBe("stale");
  });

  test("the snapshot is the source at the start of the execution", () => {
    const cell = createFakeCell({ source: "v1" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.execute(1);
    cell.model.setSource("v2");
    expect(state(cell)).toBe("stale");
    cell.model.execute(2); // runs v2
    expect(state(cell)).toBe("ran");
    expect(exec(cell)).toBe("2");
  });

  test("error output: ran-then-failed is error, and an edit then makes it stale", () => {
    const cell = createFakeCell({ source: "1/0" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.execute(1, { error: true });
    expect(state(cell)).toBe("error");
    cell.model.setSource("1/1");
    expect(state(cell)).toBe("stale");
  });

  test("an error cell that is re-run successfully becomes ran", () => {
    const cell = createFakeCell({ source: "1/0" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.execute(1, { error: true });
    cell.model.execute(2, { source: "1/1" });
    expect(state(cell)).toBe("ran");
  });

  test("an interrupted run (count never set) is not-run, not stale", () => {
    const cell = createFakeCell({ source: "x" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    cell.model.startExecution();
    cell.model.setSource("xy");
    // The kernel is interrupted: state returns to idle with no count.
    cell.model.finishExecution({ count: null });
    expect(state(cell)).toBe("not-run");
  });

  test("an execution finishing without a running phase observed still takes a snapshot", () => {
    const cell = createFakeCell({ source: "x" });
    chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    // Count arrives with no preceding running state (a very fast run).
    cell.model.finishExecution({ count: 1 });
    expect(state(cell)).toBe("ran");
    cell.model.setSource("y");
    expect(state(cell)).toBe("stale");
  });
});

describe("mountChrome: discovery and idempotent attach", () => {
  test("a panel opened after mount is picked up through the shell signals", () => {
    const { app } = chromeFor([]);
    const cell = createFakeCell({ source: "x", executionCount: 1, outputs: ["stream"] });
    app.addPanel(createFakeNotebookPanel({ cells: [cell] }));
    expect(state(cell)).toBe("ran");
  });

  test("a cell added to a panel later is observed", () => {
    const panel = createFakeNotebookPanel({ cells: [] });
    chromeFor([panel]);
    const cell = panel.addCell(createFakeCell({ source: "x" }));
    expect(state(cell)).toBe("not-run");
    cell.model.execute(1);
    expect(state(cell)).toBe("ran");
  });

  test("non-notebook main-area widgets are ignored", () => {
    const other = { node: createFakeNode(["jp-MainAreaWidget"]), content: {} };
    const { chrome, logger } = chromeFor([other]);
    expect(logger.errors).toEqual([]);
    expect(chrome).toBeTruthy();
  });

  test("re-attaching the same panel adds no signal connection", () => {
    const cell = createFakeCell({ source: "x", executionCount: 1, outputs: ["stream"] });
    const panel = createFakeNotebookPanel({ cells: [cell] });
    const { chrome, app } = chromeFor([panel]);
    const counts = () => [
      cell.model.stateChanged.connectionCount,
      cell.model.contentChanged.connectionCount,
      cell.model.sharedModel.changed.connectionCount,
      cell.model.outputs.changed.connectionCount,
      panel.content.model.cells.changed.connectionCount,
    ];
    const before = counts();
    expect(before.every((n) => n >= 0)).toBe(true);
    chrome.attachPanel(panel);
    chrome.attachPanel(panel);
    chrome.scan();
    app.shell.layoutModified.emit(app.shell, undefined);
    app.shell.currentChanged.emit(app.shell, { newValue: panel });
    expect(counts()).toEqual(before);
    // Negative control for the count: at least one of them is observed.
    expect(before.reduce((a, b) => a + b, 0)).toBeGreaterThan(0);
  });

  test("re-attaching does not reset the snapshot (an edited cell stays stale)", () => {
    const cell = createFakeCell({ source: "v1", executionCount: 1, outputs: ["stream"] });
    const panel = createFakeNotebookPanel({ cells: [cell] });
    const { chrome } = chromeFor([panel]);
    cell.model.setSource("v2");
    expect(state(cell)).toBe("stale");
    chrome.attachPanel(panel);
    chrome.scan();
    expect(state(cell)).toBe("stale");
  });

  test("re-attaching writes nothing more to a cell whose state did not change", () => {
    const cell = createFakeCell({ source: "x", executionCount: 1, outputs: ["stream"] });
    const panel = createFakeNotebookPanel({ cells: [cell] });
    const { chrome } = chromeFor([panel]);
    const writes = cell.node.setAttributeCalls.length;
    chrome.attachPanel(panel);
    chrome.refresh();
    expect(cell.node.setAttributeCalls.length).toBe(writes);
  });

  test("dispose disconnects every signal and stops writing", () => {
    const cell = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [cell] });
    const { chrome, app } = chromeFor([panel]);
    chrome.dispose();
    expect(cell.model.stateChanged.connectionCount).toBe(0);
    expect(cell.model.contentChanged.connectionCount).toBe(0);
    expect(cell.model.outputs.changed.connectionCount).toBe(0);
    expect(app.shell.layoutModified.connectionCount).toBe(0);
    expect(app.shell.currentChanged.connectionCount).toBe(0);
    cell.model.execute(1);
    expect(state(cell)).toBe("not-run");
  });
});

describe("mountChrome: windowing mode (S1 caveat)", () => {
  function viewportCount(cell) {
    return cell.inViewportChanged.connectionCount;
  }

  test("contentVisibility is read, reported, and needs no viewport subscription", () => {
    const cell = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [cell], windowingMode: "contentVisibility" });
    const { chrome } = chromeFor([panel]);
    expect(chrome.windowing(panel)).toEqual({ mode: "contentVisibility", viewportSubscribed: false });
    expect(viewportCount(cell)).toBe(0);
  });

  test("any other mode subscribes to inViewportChanged and rewrites the attributes on re-attach", () => {
    const cell = createFakeCell({ source: "x", executionCount: 1, outputs: ["stream"] });
    const panel = createFakeNotebookPanel({ cells: [cell], windowingMode: "full" });
    const { chrome } = chromeFor([panel]);
    expect(chrome.windowing(panel)).toEqual({ mode: "full", viewportSubscribed: true });
    expect(viewportCount(cell)).toBe(1);
    // The cell's node loses the attributes (a re-created node), then re-enters the viewport.
    cell.node.removeAttribute(STATE_ATTR);
    cell.node.removeAttribute(EXEC_ATTR);
    cell.inViewportChanged.emit(cell, true);
    expect(state(cell)).toBe("ran");
    expect(exec(cell)).toBe("1");
  });

  test("an unreadable mode is treated as not contentVisibility (conservative)", () => {
    const cell = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [cell], windowingMode: null });
    const { chrome } = chromeFor([panel]);
    expect(chrome.windowing(panel)).toEqual({ mode: null, viewportSubscribed: true });
    expect(viewportCount(cell)).toBe(1);
  });

  test("re-attach in a non-contentVisibility mode adds no second viewport subscription", () => {
    const cell = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [cell], windowingMode: "defer" });
    const { chrome } = chromeFor([panel]);
    chrome.attachPanel(panel);
    chrome.scan();
    expect(viewportCount(cell)).toBe(1);
  });

  test("a mode that is not contentVisibility warns once per panel", () => {
    const warns = [];
    const panel = createFakeNotebookPanel({ cells: [createFakeCell()], windowingMode: "full" });
    const app = createFakeApp({ panels: [panel] });
    const chrome = mountChrome({ app, logger: { error() {}, log() {}, warn: (...a) => warns.push(a) } });
    chrome.attachPanel(panel);
    chrome.scan();
    expect(warns.length).toBe(1);
  });
});

describe("mountChrome: observed-execution event (for stale.js panelSession, D7)", () => {
  test("reports (cell, panel) when an execution starts and when it finishes", () => {
    const cell = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [cell] });
    const { chrome } = chromeFor([panel]);
    const seen = [];
    chrome.onExecution((e) => seen.push(e));
    cell.model.startExecution();
    cell.model.finishExecution({ count: 7 });
    expect(seen.map((e) => e.phase)).toEqual(["started", "finished"]);
    for (const e of seen) {
      expect(e.cell).toBe(cell);
      expect(e.panel).toBe(panel);
    }
    expect(seen[1].executionCount).toBe(7);
  });

  test("a cell loaded with saved outputs is not an observed execution", () => {
    const cell = createFakeCell({ source: "x", executionCount: 3, outputs: ["stream"] });
    const app = createFakeApp({ panels: [createFakeNotebookPanel({ cells: [cell] })] });
    const seen = [];
    const chrome = mountChrome({ app, logger: silentLogger() });
    chrome.onExecution((e) => seen.push(e));
    chrome.scan();
    expect(seen).toEqual([]);
  });

  test("an edit is not an execution", () => {
    const cell = createFakeCell({ source: "x", executionCount: 3, outputs: ["stream"] });
    const { chrome } = chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    const seen = [];
    chrome.onExecution((e) => seen.push(e));
    cell.model.setSource("y");
    expect(seen).toEqual([]);
  });

  test("the returned function unsubscribes", () => {
    const cell = createFakeCell({ source: "x" });
    const { chrome } = chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    const seen = [];
    const off = chrome.onExecution((e) => seen.push(e));
    off();
    cell.model.execute(1);
    expect(seen).toEqual([]);
  });

  test("a throwing listener is contained: the attributes are still written and it is logged", () => {
    const cell = createFakeCell({ source: "x" });
    const { chrome, logger } = chromeFor([createFakeNotebookPanel({ cells: [cell] })]);
    chrome.onExecution(() => {
      throw new Error("listener boom");
    });
    cell.model.execute(1);
    expect(state(cell)).toBe("ran");
    expect(logger.errors.length).toBeGreaterThan(0);
  });
});

describe("mountChrome: a broken cell does not stop the others", () => {
  test("a model that throws on read is logged and the sibling cell is still written", () => {
    const bad = createFakeCell({ source: "bad" });
    Object.defineProperty(bad.model, "executionCount", {
      get() {
        throw new Error("model exploded");
      },
    });
    const good = createFakeCell({ source: "good", executionCount: 1, outputs: ["stream"] });
    const { logger } = chromeFor([createFakeNotebookPanel({ cells: [bad, good] })]);
    expect(state(good)).toBe("ran");
    expect(logger.errors.length).toBeGreaterThan(0);
  });
});
