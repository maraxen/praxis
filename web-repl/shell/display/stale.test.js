// stale.test.js -- AC-19 (shell stale marks) of the notebook display epic
// (.praxia/docs/specs/260929_notebook-display-epic.md: D7 "Marking", "Current
// session, per notebook panel", "Marks survive re-rendering"; D2 "One stamp
// reader"; D14; section 4 stale.js row; task B9).
//
// Ground truth for the contracts this consumes:
//   * B7 (praxis/display/stale.py): the kernel posts on BroadcastChannel
//     `praxis_repl` exactly {type: "praxis:resource-changed", json: <string>},
//     json = {"session", "exec", "revs": {name: rev}} (<= 4096 bytes) or
//     {"session", "exec", "all": true}.
//   * S1: windowingMode contentVisibility (no re-attach signal); chrome.js
//     subscribes to inViewportChanged in any other mode and says so through
//     controller.windowing(panel).
//   * S2: an untrusted reopen strips data-* / the SVG, but the stamp is model
//     metadata, so stale.js never reads the DOM's data-*.
//
// Every scenario is a function of the module under test, so the same scenarios
// run against the real stale.js AND against mutants (a stale.js that marks
// everything, one that marks nothing): a mutant that survives a scenario means
// the scenario cannot fail. The model is read-only (the fake's writers throw).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import * as real from "./stale.js";
import { mountChrome } from "./chrome.js";
import {
  announcement,
  createFakeApp,
  createFakeBroadcastHub,
  createFakeCell,
  createFakeDocument,
  createFakeNotebookPanel,
  createFakeSignal,
  createFakeWindow,
  praxisOutput,
  stamp,
} from "./__tests__/fakes.js";

const { stampOf, parseAnnouncement, createRevTracker, CHANGED_TEXT, EARLIER_TEXT } = real;

const CHANNEL = "praxis_repl";
const MARK = "praxis-stale";

function recordingLogger() {
  const errors = [];
  const warns = [];
  return {
    errors,
    warns,
    error: (...a) => errors.push(a),
    warn: (...a) => warns.push(a),
    log() {},
  };
}

/** Text of every stale mark inside output i of `cell`. */
function texts(cell, i = 0) {
  const host = cell.host(i);
  return host.children.filter((c) => c.classList.contains(MARK)).map((c) => c.textContent);
}

function markCount(cell, i = 0) {
  return texts(cell, i).length;
}

/** Mount the chrome, then stale (module `mod`), on `panels`. */
function world({ panels, mod = real, chrome = true, broadcast = true } = {}) {
  const app = createFakeApp({ panels });
  const hub = createFakeBroadcastHub();
  const document = createFakeDocument();
  const win = createFakeWindow({ app, document, broadcast: broadcast ? hub : null });
  const logger = recordingLogger();
  const chromeCtl = chrome ? mountChrome({ app, logger }) : undefined;
  const stale = mod.mountStale({ app, win, logger, controllers: chromeCtl ? { chrome: chromeCtl } : {} });
  return { app, hub, win, logger, chrome: chromeCtl, stale };
}

const post = (w, message) => w.hub.post(CHANNEL, message);

/** Run a cell that draws `output` (a full execution: started, output, count). */
function draw(cell, count, st, options) {
  cell.model.execute(count, { outputs: [praxisOutput(st, options)] });
}

/** A cell loaded from a saved notebook: executed earlier, never run in this page. */
function restored(st, { count = 3, options } = {}) {
  return createFakeCell({ source: "saved", executionCount: count, outputs: [praxisOutput(st, options)] });
}

// -- the scenarios (each takes the module under test) ---------------------------------

const scenarios = {
  changedSinceOnlyForOlderRevInTheSameSession(mod) {
    const c1 = createFakeCell({ source: "draw assay" });
    const c2 = createFakeCell({ source: "draw tips" });
    const c3 = createFakeCell({ source: "draw assay again" });
    const panel = createFakeNotebookPanel({ cells: [c1, c2, c3] });
    const w = world({ panels: [panel], mod });
    draw(c1, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    draw(c2, 2, stamp({ kind: "tiprack", resource: "tips_300", rev: 1, session: "sA", exec: 2 }));
    draw(c3, 3, stamp({ resource: "assay", rev: 2, session: "sA", exec: 3 }));

    post(w, announcement({ session: "sA", exec: 4, revs: { assay: 2 } }));
    expect(texts(c1)).toEqual([CHANGED_TEXT]);
    expect(texts(c2)).toEqual([]); // another resource
    expect(texts(c3)).toEqual([]); // drawn at that rev (the drawing cell's own output)

    // Another session's announcement, and an equal or lower rev, mark nothing new.
    post(w, announcement({ session: "sZ", exec: 9, revs: { assay: 99, tips_300: 99 } }));
    post(w, announcement({ session: "sA", exec: 5, revs: { assay: 1, tips_300: 1 } }));
    expect(texts(c2)).toEqual([]);
    expect(texts(c3)).toEqual([]);

    // A later rev marks the newer drawing too, and the first stays marked exactly once.
    post(w, announcement({ session: "sA", exec: 6, revs: { assay: 3 } }));
    expect(texts(c3)).toEqual([CHANGED_TEXT]);
    expect(texts(c1)).toEqual([CHANGED_TEXT]);
    expect(w.logger.errors).toEqual([]);
  },

  revNullIsNeverChangedSinceButIsEarlierSession(mod) {
    const ledger = restored(stamp({ kind: "ledger", resource: "assay", rev: null, session: "sOld", exec: 2 }));
    const error = restored(stamp({ kind: "error", resource: "assay", rev: null, session: "sOld", exec: 3 }));
    const live = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [ledger, error, live] });
    const w = world({ panels: [panel], mod });
    draw(live, 4, stamp({ kind: "tiprack", resource: "tips_300", rev: 1, session: "sNew", exec: 4 }));

    post(w, announcement({ session: "sOld", exec: 9, revs: { assay: 7 } }));
    post(w, announcement({ session: "sNew", exec: 10, revs: { assay: 7 } }));
    expect(texts(ledger)).toEqual([EARLIER_TEXT]);
    expect(texts(error)).toEqual([EARLIER_TEXT]);
    expect(texts(live)).toEqual([]);
    expect(w.logger.errors).toEqual([]);
  },

  sessionMarksPerPanelAndRestart(mod) {
    const r = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const u = createFakeCell({ source: "print" });
    const d = createFakeCell({ source: "draw d" });
    const e = createFakeCell({ source: "draw e" });
    const panel = createFakeNotebookPanel({ cells: [r, u, d, e] });
    const w = world({ panels: [panel], mod });

    // Nothing observed yet: the session is unknown and nothing is marked.
    expect(w.stale.panelSession(panel)).toBeNull();
    expect(texts(r)).toEqual([]);

    // An observed execution with no stamped output does not make it known.
    u.model.execute(4);
    expect(w.stale.panelSession(panel)).toBeNull();
    expect(texts(r)).toEqual([]);

    // An observed stamped execution does; the restored output is now earlier.
    draw(d, 5, stamp({ kind: "tiprack", resource: "tips_300", session: "sNew", exec: 5 }));
    expect(w.stale.panelSession(panel)).toBe("sNew");
    expect(texts(r)).toEqual([EARLIER_TEXT]);
    expect(texts(d)).toEqual([]);
    draw(e, 6, stamp({ resource: "assay", session: "sNew", exec: 6 }));
    expect(texts(e)).toEqual([]);

    // Kernel restart: the session is unknown again; nothing new is written.
    panel.restartKernel();
    expect(w.stale.panelSession(panel)).toBeNull();
    expect(texts(e)).toEqual([]);

    // A re-run drawing cell makes the new session current. Its own new output
    // is NOT marked (negative control); the pre-restart outputs are.
    draw(d, 1, stamp({ kind: "tiprack", resource: "tips_300", session: "sNew2", exec: 1 }));
    expect(w.stale.panelSession(panel)).toBe("sNew2");
    expect(texts(d)).toEqual([]);
    expect(texts(e)).toEqual([EARLIER_TEXT]);
    expect(texts(r)).toEqual([EARLIER_TEXT]);
    expect(w.logger.errors).toEqual([]);
  },

  twoPanelsNeverMarkEachOther(mod) {
    const p1 = createFakeCell({ source: "draw in P" });
    const p2 = createFakeCell({ source: "draw in P again" });
    const q1 = createFakeCell({ source: "draw in Q" });
    const P = createFakeNotebookPanel({ cells: [p1, p2] });
    const Q = createFakeNotebookPanel({ cells: [q1] });
    const w = world({ panels: [P, Q], mod });
    draw(p1, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    draw(q1, 1, stamp({ resource: "assay", rev: 1, session: "sB", exec: 1 }));
    draw(p2, 2, stamp({ kind: "tiprack", resource: "tips_300", rev: 1, session: "sA", exec: 2 }));

    expect(w.stale.panelSession(P)).toBe("sA");
    expect(w.stale.panelSession(Q)).toBe("sB");
    for (const cell of [p1, p2, q1]) expect(texts(cell)).toEqual([]);

    // An announcement from P's kernel marks only outputs of session sA.
    post(w, announcement({ session: "sA", exec: 3, revs: { assay: 2 } }));
    expect(texts(p1)).toEqual([CHANGED_TEXT]);
    expect(texts(q1)).toEqual([]);
    expect(w.logger.errors).toEqual([]);
  },

  marksReappliedOnOutputsChanged(mod) {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel], mod });
    const st = stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 });
    draw(c, 1, st);
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([CHANGED_TEXT]);

    const oldHost = c.host(0);
    c.model.setOutputs([praxisOutput(st)]); // the output node is replaced
    expect(c.host(0)).not.toBe(oldHost);
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    expect(c.host(0).appendCalls).toBe(1); // written once, not once per signal
    expect(w.logger.errors).toEqual([]);
  },

  marksReappliedOnReattachSignal(mod) {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c], windowingMode: "full" });
    const w = world({ panels: [panel], mod });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([CHANGED_TEXT]);

    c.rerender(); // a windowed cell detached and re-attached: fresh nodes, no marks
    expect(texts(c)).toEqual([]);
    c.inViewportChanged.emit(c, true);
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    c.inViewportChanged.emit(c, true);
    c.inViewportChanged.emit(c, true);
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    expect(c.host(0).appendCalls).toBe(1);
    expect(w.logger.errors).toEqual([]);
  },

  marksReappliedOnActiveCellChanged(mod) {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel], mod });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));

    c.rerender();
    expect(texts(c)).toEqual([]);
    panel.content.activeCellChanged.emit(panel.content, c);
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    panel.content.activeCellChanged.emit(panel.content, c);
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    expect(c.host(0).appendCalls).toBe(1);
    expect(w.logger.errors).toEqual([]);
  },

  bothStampCarriersAreMarkedAlike(mod) {
    const a = createFakeCell({ source: "S3-A carrier" });
    const b = createFakeCell({ source: "S3-B carrier" });
    const panel = createFakeNotebookPanel({ cells: [a, b] });
    const w = world({ panels: [panel], mod });
    draw(a, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }), { carrier: "praxis" });
    draw(b, 2, stamp({ resource: "assay", rev: 1, session: "sA", exec: 2 }), { carrier: "html" });
    expect(w.stale.panelSession(panel)).toBe("sA"); // the html carrier feeds panelSession too
    post(w, announcement({ session: "sA", exec: 3, revs: { assay: 2 } }));
    expect(texts(a)).toEqual([CHANGED_TEXT]);
    expect(texts(b)).toEqual([CHANGED_TEXT]);
    expect(w.logger.errors).toEqual([]);
  },

  hostileNamesAreOnlyDataNeverSelectors(mod) {
    const hostile = "<b>&\"'x";
    const names = [hostile, "__proto__", "constructor", "hasOwnProperty", "toString"];
    const cells = names.map((n) => createFakeCell({ source: `draw ${n}` }));
    const panel = createFakeNotebookPanel({ cells });
    const w = world({ panels: [panel], mod });
    names.forEach((n, i) => draw(cells[i], i + 1, stamp({ resource: n, rev: 1, session: "sA", exec: i + 1 })));

    // JSON.parse makes "__proto__" an OWN key; build the text by hand to be sure.
    const json =
      '{"session":"sA","exec":9,"revs":{' +
      `${JSON.stringify(hostile)}:2,"__proto__":2,"constructor":2}}`;
    post(w, { type: "praxis:resource-changed", json });
    expect(texts(cells[0])).toEqual([CHANGED_TEXT]);
    expect(texts(cells[1])).toEqual([CHANGED_TEXT]); // "__proto__"
    expect(texts(cells[2])).toEqual([CHANGED_TEXT]); // "constructor"
    expect(texts(cells[3])).toEqual([]); // "hasOwnProperty": never announced
    expect(texts(cells[4])).toEqual([]); // "toString": never announced
    // The name never reaches the DOM text or a selector.
    for (const cell of cells) for (const t of texts(cell)) expect(t).not.toContain("x");
    expect(w.logger.errors).toEqual([]);
  },

  allAnnouncementMarksEveryStampedResourceDrawnBefore(mod) {
    const cells = [1, 2, 3, 4, 5].map((n) => createFakeCell({ source: `cell ${n}` }));
    const [older, tips, ledger, own, later] = cells;
    const panel = createFakeNotebookPanel({ cells });
    const w = world({ panels: [panel], mod });
    draw(older, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    draw(tips, 2, stamp({ kind: "tiprack", resource: "tips_300", rev: 4, session: "sA", exec: 2 }));
    draw(ledger, 3, stamp({ kind: "ledger", resource: null, rev: null, session: "sA", exec: 3 }));
    draw(own, 5, stamp({ resource: "assay", rev: 2, session: "sA", exec: 5 }));
    draw(later, 6, stamp({ resource: "assay", rev: 3, session: "sA", exec: 6 }));

    post(w, announcement({ session: "sA", exec: 5, all: true }));
    expect(texts(older)).toEqual([CHANGED_TEXT]);
    expect(texts(tips)).toEqual([CHANGED_TEXT]); // every resource, not just one name
    expect(texts(ledger)).toEqual([]); // rev null: never
    expect(texts(own)).toEqual([]); // the announcing cell's own output
    expect(texts(later)).toEqual([]); // drawn after the change
    expect(w.logger.errors).toEqual([]);
  },

  noChromeNoSessionMarksButChangedSinceStillWorks(mod) {
    const r = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const panel = createFakeNotebookPanel({ cells: [r] });
    const w = world({ panels: [panel], mod, chrome: false });
    expect(w.stale.panelSession(panel)).toBeNull();
    expect(texts(r)).toEqual([]);
    post(w, announcement({ session: "sOld", exec: 4, revs: { assay: 2 } }));
    expect(texts(r)).toEqual([CHANGED_TEXT]); // no session mark, no chrome needed
    expect(w.logger.errors).toEqual([]);
  },

  marksNeedNoDataAttributes(mod) {
    // S2: an untrusted reopen strips data-* from the DOM. The output node here
    // has none; the stamp is read from the model, so the mark is still written.
    const c = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel], mod });
    expect(c.host(0).getAttribute("data-praxis-res")).toBeNull();
    post(w, announcement({ session: "sOld", exec: 4, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    expect(w.logger.errors).toEqual([]);
  },
};

// -- the real module ----------------------------------------------------------------------

describe("stale.js scenarios (real module)", () => {
  for (const [name, scenario] of Object.entries(scenarios)) {
    test(name, () => scenario(real));
  }
});

// -- controls: mutants that must FAIL --------------------------------------------------------

const SOURCE = readFileSync(new URL("./stale.js", import.meta.url), "utf8");
const CHROME_URL = pathToFileURL(new URL("./chrome.js", import.meta.url).pathname).href;

/** A copy of stale.js with `injection` placed at the top of `fn`'s body. */
async function mutant(fn, injection) {
  const header = new RegExp(`export function ${fn}\\(([^)]*)\\) \\{`, "g");
  const hits = SOURCE.match(header);
  if (!hits || hits.length !== 1) throw new Error(`mutation harness: cannot find export function ${fn}(...) once`);
  let text = SOURCE.replace(header, (m) => `${m}\n  ${injection}\n`);
  text = text.replaceAll('"./chrome.js"', JSON.stringify(CHROME_URL));
  if (/from\s+["']\.\//.test(text)) throw new Error("mutation harness: an unrewritten relative import");
  const dir = mkdtempSync(join(tmpdir(), "praxis-stale-mutant-"));
  const file = join(dir, `${fn}.mjs`);
  writeFileSync(file, text);
  return import(pathToFileURL(file).href);
}

const MUTANTS = {
  marksChangedEverywhere: await mutant("changedSince", "return true;"),
  marksChangedNowhere: await mutant("changedSince", "return false;"),
  marksEarlierEverywhere: await mutant("earlierSession", "return true;"),
  marksEarlierNowhere: await mutant("earlierSession", "return false;"),
};

// Which scenarios each mutant MUST fail (a control that cannot fail proves nothing).
const MUST_FAIL = {
  marksChangedEverywhere: [
    "changedSinceOnlyForOlderRevInTheSameSession",
    "revNullIsNeverChangedSinceButIsEarlierSession",
    "twoPanelsNeverMarkEachOther",
    "allAnnouncementMarksEveryStampedResourceDrawnBefore",
  ],
  marksChangedNowhere: [
    "changedSinceOnlyForOlderRevInTheSameSession",
    "marksReappliedOnOutputsChanged",
    "marksReappliedOnReattachSignal",
    "marksReappliedOnActiveCellChanged",
    "bothStampCarriersAreMarkedAlike",
    "hostileNamesAreOnlyDataNeverSelectors",
    "allAnnouncementMarksEveryStampedResourceDrawnBefore",
    "noChromeNoSessionMarksButChangedSinceStillWorks",
    "marksNeedNoDataAttributes",
  ],
  marksEarlierEverywhere: [
    "revNullIsNeverChangedSinceButIsEarlierSession",
    "sessionMarksPerPanelAndRestart",
    "twoPanelsNeverMarkEachOther",
    "noChromeNoSessionMarksButChangedSinceStillWorks",
  ],
  marksEarlierNowhere: [
    "revNullIsNeverChangedSinceButIsEarlierSession",
    "sessionMarksPerPanelAndRestart",
  ],
};

describe("stale.js controls: mutants must fail", () => {
  test("the mutants are real: each differs from the source", () => {
    for (const mod of Object.values(MUTANTS)) expect(typeof mod.mountStale).toBe("function");
  });
  for (const [mutantName, names] of Object.entries(MUST_FAIL)) {
    for (const name of names) {
      test(`${mutantName} fails ${name}`, () => {
        expect(() => scenarios[name](MUTANTS[mutantName])).toThrow();
      });
    }
  }
  test("positive control: the real module passes every scenario the mutants fail", () => {
    for (const names of Object.values(MUST_FAIL)) for (const name of names) scenarios[name](real);
  });
});

// -- stampOf (D2) ---------------------------------------------------------------------------------

describe("stampOf", () => {
  const st = stamp({ resource: "assay", rev: 3, session: "sA", exec: 7 });

  test("reads metadata.praxis (S3-A)", () => {
    expect(stampOf({ metadata: { praxis: st } })).toEqual(st);
  });

  test("reads metadata['text/html'].praxis (S3-B)", () => {
    expect(stampOf({ metadata: { "text/html": { praxis: st } } })).toEqual(st);
  });

  test("metadata.praxis wins over the S3-B carrier", () => {
    const other = stamp({ resource: "other" });
    expect(stampOf({ metadata: { praxis: st, "text/html": { praxis: other } } })).toEqual(st);
  });

  test("a null metadata.praxis falls through to the S3-B carrier (the ?? of the D2 expression)", () => {
    expect(stampOf({ metadata: { praxis: null, "text/html": { praxis: st } } })).toEqual(st);
  });

  test("missing metadata, missing praxis and non-outputs give undefined, never a throw", () => {
    for (const bad of [undefined, null, {}, { metadata: null }, { metadata: {} }, { metadata: { "text/html": null } },
      { metadata: { "text/html": {} } }, 5, "text", []]) {
      expect(stampOf(bad)).toBeUndefined();
    }
  });

  test("prototype-pollution safe: only OWN properties are read", () => {
    const inherited = Object.create({ praxis: st });
    expect(stampOf({ metadata: inherited })).toBeUndefined();
    const inheritedHtml = { metadata: { "text/html": Object.create({ praxis: st }) } };
    expect(stampOf(inheritedHtml)).toBeUndefined();
    const polluted = JSON.parse('{"metadata": {"__proto__": {"praxis": {"resource": "evil"}}}}');
    expect(stampOf(polluted)).toBeUndefined();
    expect(stampOf({ metadata: { praxis: st } })).toEqual(st); // and the normal read still works
  });

  test("a getter that throws is contained", () => {
    const output = {
      get metadata() {
        throw new Error("boom");
      },
    };
    expect(stampOf(output)).toBeUndefined();
  });

  test("works on a JupyterLab-style output model (toJSON only carries the same metadata)", () => {
    const model = { type: "display_data", metadata: Object.freeze({ praxis: st }) };
    expect(stampOf(model)).toEqual(st);
  });
});

// -- parseAnnouncement --------------------------------------------------------------------------------

describe("parseAnnouncement", () => {
  const msg = (body) => ({ type: "praxis:resource-changed", json: typeof body === "string" ? body : JSON.stringify(body) });

  test("a revs announcement", () => {
    const a = parseAnnouncement(msg({ session: "sA", exec: 4, revs: { assay: 2, tips_300: 1 } }));
    expect(a.session).toBe("sA");
    expect(a.exec).toBe(4);
    expect(a.all).toBe(false);
    expect(a.revs instanceof Map).toBe(true);
    expect([...a.revs.entries()]).toEqual([["assay", 2], ["tips_300", 1]]);
  });

  test("an all announcement carries no revs", () => {
    const a = parseAnnouncement(msg({ session: "sA", exec: 4, all: true }));
    expect(a.all).toBe(true);
    expect(a.revs.size).toBe(0);
  });

  test("a null exec is kept as null", () => {
    expect(parseAnnouncement(msg({ session: "sA", exec: null, revs: { a: 0 } })).exec).toBeNull();
  });

  test("a non-integer exec is read as null, not trusted", () => {
    expect(parseAnnouncement(msg({ session: "sA", exec: "4", revs: { a: 1 } })).exec).toBeNull();
  });

  test("entries whose rev is not a non-negative integer are dropped, the rest are kept", () => {
    const a = parseAnnouncement(msg({ session: "sA", exec: 1, revs: { ok: 3, str: "2", frac: 1.5, neg: -1, nul: null, big: 1e400 } }));
    expect([...a.revs.keys()]).toEqual(["ok"]);
  });

  test("hostile keys survive as data", () => {
    const a = parseAnnouncement(msg('{"session":"sA","exec":1,"revs":{"__proto__":2,"constructor":3}}'));
    expect(a.revs.get("__proto__")).toBe(2);
    expect(a.revs.get("constructor")).toBe(3);
    expect(Object.getPrototypeOf(a.revs)).toBe(Map.prototype);
  });

  test("malformed messages give null, never a throw", () => {
    const bad = [
      undefined, null, 5, "praxis:resource-changed", [], {},
      { type: "other", json: "{}" },
      { type: "praxis:shell-ping" },
      { type: "praxis:resource-changed" },
      { type: "praxis:resource-changed", json: 5 },
      { type: "praxis:resource-changed", json: null },
      msg("{not json"), msg("[]"), msg("null"), msg("5"), msg('"s"'),
      msg({ exec: 1, revs: { a: 1 } }), // no session
      msg({ session: 5, exec: 1, revs: { a: 1 } }), // session not a string
      msg({ session: "", exec: 1, revs: { a: 1 } }), // empty session
      msg({ session: "sA", exec: 1 }), // neither revs nor all
      msg({ session: "sA", exec: 1, revs: [1, 2] }), // revs not an object
      msg({ session: "sA", exec: 1, revs: "x" }),
      msg({ session: "sA", exec: 1, revs: null }),
      msg({ session: "sA", exec: 1, all: "yes" }), // all must be exactly true
      msg({ session: "sA", exec: 1, all: false }),
    ];
    for (const b of bad) expect(parseAnnouncement(b)).toBeNull();
  });

  test("the json cap is the kernel's 4096 bytes: 4096 passes, 4097 is dropped", () => {
    const pad = (n) => {
      const base = '{"session":"sA","exec":1,"revs":{"a":1},"pad":""}';
      return base.replace('""', JSON.stringify("x".repeat(n - base.length)));
    };
    const ok = pad(4096);
    const over = pad(4097);
    expect(ok.length).toBe(4096);
    expect(over.length).toBe(4097);
    expect(parseAnnouncement({ type: "praxis:resource-changed", json: ok })).not.toBeNull();
    expect(parseAnnouncement({ type: "praxis:resource-changed", json: over })).toBeNull();
  });

  test("a getter that throws on the message is contained", () => {
    const evil = {
      get type() {
        throw new Error("boom");
      },
    };
    expect(parseAnnouncement(evil)).toBeNull();
  });
});

// -- the rev tracker ----------------------------------------------------------------------------------

describe("createRevTracker", () => {
  const ann = (o) => parseAnnouncement(announcement(o));

  test("keeps the latest rev per (session, resource) and only ever raises it", () => {
    const t = createRevTracker();
    t.apply(ann({ session: "sA", exec: 1, revs: { assay: 5 } }));
    t.apply(ann({ session: "sA", exec: 2, revs: { assay: 3 } })); // out of order: ignored
    expect(t.isChanged(stamp({ resource: "assay", rev: 4, session: "sA" }))).toBe(true);
    expect(t.isChanged(stamp({ resource: "assay", rev: 5, session: "sA" }))).toBe(false);
    expect(t.isChanged(stamp({ resource: "assay", rev: 4, session: "sB" }))).toBe(false);
    expect(t.isChanged(stamp({ resource: "plate", rev: 1, session: "sA" }))).toBe(false);
  });

  test("never for rev null, a null resource, or a non-stamp", () => {
    const t = createRevTracker();
    t.apply(ann({ session: "sA", exec: 1, revs: { assay: 9 } }));
    t.apply(ann({ session: "sA", exec: 2, all: true }));
    expect(t.isChanged(stamp({ resource: "assay", rev: null, session: "sA", exec: 1 }))).toBe(false);
    expect(t.isChanged(stamp({ resource: null, rev: 1, session: "sA", exec: 1 }))).toBe(false);
    expect(t.isChanged(null)).toBe(false);
    expect(t.isChanged(undefined)).toBe(false);
    expect(t.isChanged({ resource: "assay", rev: "1", session: "sA" })).toBe(false);
  });

  test("all: outputs of the announcing cell and later cells are not changed, earlier ones are", () => {
    const t = createRevTracker();
    t.apply(ann({ session: "sA", exec: 5, all: true }));
    expect(t.isChanged(stamp({ resource: "a", rev: 1, session: "sA", exec: 4 }))).toBe(true);
    expect(t.isChanged(stamp({ resource: "a", rev: 1, session: "sA", exec: 5 }))).toBe(false);
    expect(t.isChanged(stamp({ resource: "a", rev: 1, session: "sA", exec: 6 }))).toBe(false);
    expect(t.isChanged(stamp({ resource: "a", rev: 1, session: "sB", exec: 1 }))).toBe(false);
  });

  test("all with an unknown exec, or a stamp with an unknown exec, marks (nothing can clear it)", () => {
    const t = createRevTracker();
    t.apply(ann({ session: "sA", exec: null, all: true }));
    expect(t.isChanged(stamp({ resource: "a", rev: 1, session: "sA", exec: 9 }))).toBe(true);
    const u = createRevTracker();
    u.apply(ann({ session: "sA", exec: 5, all: true }));
    expect(u.isChanged(stamp({ resource: "a", rev: 1, session: "sA", exec: null }))).toBe(true);
  });
});

// -- the decision functions (pure) -------------------------------------------------------------------------

describe("earlierSession", () => {
  test("only with a known panel session, and only when the stamp's session differs", () => {
    expect(real.earlierSession(stamp({ session: "sA" }), "sB")).toBe(true);
    expect(real.earlierSession(stamp({ session: "sA" }), "sA")).toBe(false);
    expect(real.earlierSession(stamp({ session: "sA" }), null)).toBe(false);
    expect(real.earlierSession(null, "sA")).toBe(false);
    expect(real.earlierSession({ session: 5 }, "sA")).toBe(false);
  });
});

// -- mount: robustness, failure containment, dispose ---------------------------------------------------------

describe("mountStale: the announcement channel", () => {
  test("malformed messages are dropped: no throw, no mark, no logged error, and a good one still works", () => {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    const junk = [
      null, undefined, "x", 5, [], {}, { type: "praxis:resource-changed" },
      { type: "praxis:resource-changed", json: "{not json" },
      { type: "praxis:resource-changed", json: "[]" },
      { type: "praxis:resource-changed", json: '{"session":"sA","exec":1}' },
      { type: "praxis:shell-ping" },
      { type: "praxis:resource-changed", json: JSON.stringify({ session: "sA", exec: 1, revs: { assay: "9" } }) },
    ];
    for (const message of junk) expect(() => post(w, message)).not.toThrow();
    expect(texts(c)).toEqual([]);
    expect(w.logger.errors).toEqual([]);
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([CHANGED_TEXT]);
  });

  test("listens on praxis_repl and nothing else", () => {
    const c = createFakeCell({ source: "draw" });
    const w = world({ panels: [createFakeNotebookPanel({ cells: [c] })] });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    w.hub.post("praxis_viz3d", announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([]);
    expect(w.hub.openCount(CHANNEL)).toBe(1);
  });

  test("handleMessage returns whether it accepted the message", () => {
    const w = world({ panels: [createFakeNotebookPanel({ cells: [createFakeCell()] })] });
    expect(w.stale.handleMessage(announcement({ session: "sA", exec: 1, revs: { a: 1 } }))).toBe(true);
    expect(w.stale.handleMessage({ type: "x" })).toBe(false);
  });

  test("no BroadcastChannel in the window: it degrades (a warning), the session marks still work", () => {
    const r = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [r, d] });
    const w = world({ panels: [panel], broadcast: false });
    expect(w.logger.errors).toEqual([]);
    expect(w.logger.warns.length).toBeGreaterThan(0);
    draw(d, 4, stamp({ kind: "tiprack", resource: "tips_300", session: "sNew", exec: 4 }));
    expect(texts(r)).toEqual([EARLIER_TEXT]);
  });

  test("a BroadcastChannel constructor that throws is contained", () => {
    const app = createFakeApp({ panels: [] });
    const win = createFakeWindow({ app, document: createFakeDocument() });
    win.BroadcastChannel = class {
      constructor() {
        throw new Error("no channel for you");
      }
    };
    const logger = recordingLogger();
    expect(() => real.mountStale({ app, win, logger, controllers: {} })).not.toThrow();
    expect(logger.errors.length).toBeGreaterThan(0);
  });
});

describe("mountStale: the chrome's execution events", () => {
  /** A stand-in for chrome.js's controller, so the `phase` filter is testable:
   * the real chrome emits "started" before the outputs are cleared. */
  function fakeChrome() {
    const listeners = [];
    return {
      onExecution(listener) {
        listeners.push(listener);
        return () => listeners.splice(listeners.indexOf(listener), 1);
      },
      windowing: () => ({ mode: "contentVisibility", viewportSubscribed: false }),
      emit: (event) => listeners.slice().forEach((l) => l(event)),
      get listenerCount() {
        return listeners.length;
      },
    };
  }

  test("only a finished execution counts as observed; started does not", () => {
    const r = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const panel = createFakeNotebookPanel({ cells: [r] });
    const app = createFakeApp({ panels: [panel] });
    const logger = recordingLogger();
    const chrome = fakeChrome();
    const stale = real.mountStale({
      app,
      win: createFakeWindow({ app, document: createFakeDocument(), broadcast: createFakeBroadcastHub() }),
      logger,
      controllers: { chrome },
    });
    chrome.emit({ cell: r, panel, phase: "started", executionCount: null });
    expect(stale.panelSession(panel)).toBeNull();
    chrome.emit({ cell: r, panel, phase: "finished", executionCount: 3 });
    expect(stale.panelSession(panel)).toBe("sOld");
    expect(logger.errors).toEqual([]);
  });

  test("a count that arrives before the outputs still yields the session when the outputs land", () => {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    c.model.startExecution();
    c.model.finishExecution({ count: 2, outputs: [] });
    expect(w.stale.panelSession(panel)).toBeNull();
    c.model.setOutputs([praxisOutput(stamp({ resource: "assay", session: "sA", exec: 2 }))]);
    expect(w.stale.panelSession(panel)).toBe("sA");
  });

  test("the newest stamped output of the newest observed cell wins, skipping unstamped cells", () => {
    const a = createFakeCell({ source: "a" });
    const b = createFakeCell({ source: "b" });
    const u = createFakeCell({ source: "u" });
    const panel = createFakeNotebookPanel({ cells: [a, b, u] });
    const w = world({ panels: [panel] });
    draw(a, 1, stamp({ resource: "assay", session: "sA", exec: 1 }));
    draw(b, 2, stamp({ resource: "assay", session: "sB", exec: 2 }));
    u.model.execute(3);
    expect(w.stale.panelSession(panel)).toBe("sB");
  });

  test("within a cell the LAST stamped output speaks, not the first, and unstamped outputs are skipped", () => {
    const c = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    c.model.execute(1, {
      outputs: [
        praxisOutput(stamp({ resource: "assay", session: "sFirst", exec: 1 })),
        "stream",
        praxisOutput(stamp({ resource: "assay", session: "sLast", exec: 1 })),
        "stream",
      ],
    });
    expect(w.stale.panelSession(panel)).toBe("sLast");
  });

  test("a cell removed from the panel no longer speaks for it", () => {
    const a = createFakeCell({ source: "a" });
    const b = createFakeCell({ source: "b" });
    const panel = createFakeNotebookPanel({ cells: [a, b] });
    const w = world({ panels: [panel] });
    draw(a, 1, stamp({ resource: "assay", session: "sA", exec: 1 }));
    draw(b, 2, stamp({ resource: "assay", session: "sB", exec: 2 }));
    expect(w.stale.panelSession(panel)).toBe("sB");
    panel.content.widgets.splice(panel.content.widgets.indexOf(b), 1);
    a.model.setOutputs([praxisOutput(stamp({ resource: "assay", session: "sA", exec: 1 }))]);
    expect(w.stale.panelSession(panel)).toBe("sA");
  });

  test("a kernel switch (kernelChanged) also forgets the session", () => {
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [d] });
    const w = world({ panels: [panel] });
    draw(d, 1, stamp({ resource: "assay", session: "sA", exec: 1 }));
    expect(w.stale.panelSession(panel)).toBe("sA");
    panel.switchKernel();
    expect(w.stale.panelSession(panel)).toBeNull();
  });

  test("busy / idle status changes do not forget the session", () => {
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [d] });
    const w = world({ panels: [panel] });
    draw(d, 1, stamp({ resource: "assay", session: "sA", exec: 1 }));
    const ctx = panel.sessionContext;
    ctx.statusChanged.emit(ctx, "busy");
    ctx.statusChanged.emit(ctx, "idle");
    expect(w.stale.panelSession(panel)).toBe("sA");
  });

  test("a panel with no sessionContext still works", () => {
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [d], sessionContext: false });
    const w = world({ panels: [panel] });
    draw(d, 1, stamp({ resource: "assay", session: "sA", exec: 1 }));
    expect(w.stale.panelSession(panel)).toBe("sA");
    expect(w.logger.errors).toEqual([]);
  });

  test("a panel opened after mount is picked up (shell signals)", () => {
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [d] });
    const w = world({ panels: [] });
    w.app.addPanel(panel);
    draw(d, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    // (the fake chrome was mounted before the panel too; chrome picks it up by the same signals)
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(d)).toEqual([CHANGED_TEXT]);
  });
});

describe("mountStale: marks are DOM only, and well formed", () => {
  test("the mark is a .praxis-stale element carrying its kind; it is written into the output host", () => {
    const r = restored(stamp({ resource: "assay", rev: 1, session: "sOld", exec: 3 }));
    const d = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [r, d] });
    const w = world({ panels: [panel] });
    draw(d, 4, stamp({ kind: "tiprack", resource: "tips_300", session: "sNew", exec: 4 }));
    post(w, announcement({ session: "sOld", exec: 9, revs: { assay: 2 } }));
    const marks = r.host(0).children.filter((c) => c.classList.contains(MARK));
    expect(marks.map((m) => m.getAttribute("data-praxis-stale")).sort()).toEqual(["changed", "earlier-session"]);
    expect(marks.map((m) => m.textContent).sort()).toEqual([CHANGED_TEXT, EARLIER_TEXT].sort());
    expect(CHANGED_TEXT).toBe("Changed since, see deck panel.");
    expect(EARLIER_TEXT).toBe("Drawn in an earlier session.");
  });

  test("the model is only read: every model writer of the fake throws, and none was called", () => {
    const c = createFakeCell({ source: "draw" });
    expect(() => c.model.outputs.set(0, {})).toThrow();
    expect(() => c.model.setMetadata("k", 1)).toThrow();
    expect(() => c.model.sharedModel.updateOutputs()).toThrow();
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([CHANGED_TEXT]);
    expect(w.logger.errors).toEqual([]); // a write would have thrown and been logged
  });

  test("outputs without a usable stamp are left alone: streams, malformed stamps, no metadata", () => {
    const c = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    c.model.execute(1, {
      outputs: [
        "stream",
        { type: "display_data" },
        { type: "display_data", metadata: { praxis: "not an object" } },
        { type: "display_data", metadata: { praxis: { resource: "assay", rev: "1", session: "sA" } } },
        { type: "display_data", metadata: { praxis: { resource: "assay", rev: 1, session: 5 } } },
        { type: "display_data", metadata: { praxis: [] } },
      ],
    });
    post(w, announcement({ session: "sA", exec: 2, revs: { assay: 9 } }));
    for (let i = 0; i < 6; i += 1) expect(texts(c, i)).toEqual([]);
    expect(w.logger.errors).toEqual([]);
  });
});

describe("mountStale: failure containment", () => {
  test("a cell whose outputs throw does not stop the other cells, and is logged", () => {
    const bad = createFakeCell({ source: "bad" });
    const good = createFakeCell({ source: "good" });
    const panel = createFakeNotebookPanel({ cells: [bad, good] });
    const w = world({ panels: [panel] });
    draw(good, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    Object.defineProperty(bad.model.outputs, "length", {
      get() {
        throw new Error("outputs are broken");
      },
    });
    expect(() => post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }))).not.toThrow();
    expect(texts(good)).toEqual([CHANGED_TEXT]);
    expect(w.logger.errors.length).toBeGreaterThan(0);
  });

  test("an output whose metadata getter throws does not stop its siblings", () => {
    const c = createFakeCell({ source: "x" });
    const panel = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [panel] });
    c.model.execute(1, {
      outputs: [praxisOutput(stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }))],
    });
    const original = c.model.outputs.get;
    c.model.outputs.get = (i) =>
      i === 0
        ? {
            get metadata() {
              throw new Error("metadata is broken");
            },
          }
        : original(i);
    expect(() => post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }))).not.toThrow();
    expect(w.logger.errors).toEqual([]); // stampOf contains it: undefined, not an error
  });

  test("a panel whose widgets throw does not stop other panels", () => {
    const bad = createFakeNotebookPanel({ cells: [] });
    Object.defineProperty(bad.content, "widgets", {
      get() {
        throw new Error("widgets are broken");
      },
    });
    const c = createFakeCell({ source: "draw" });
    const good = createFakeNotebookPanel({ cells: [c] });
    const w = world({ panels: [bad, good] });
    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    expect(() => post(w, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }))).not.toThrow();
    expect(texts(c)).toEqual([CHANGED_TEXT]);
  });

  test("an app without a shell, and no controllers at all, mount without throwing", () => {
    const logger = recordingLogger();
    expect(() => real.mountStale({ app: {}, win: createFakeWindow({}), logger })).not.toThrow();
    expect(() => real.mountStale({ app: undefined, win: createFakeWindow({}), logger, controllers: {} })).not.toThrow();
  });
});

describe("mountStale: dispose", () => {
  test("disconnects every signal, closes the channel, unsubscribes from the chrome, and stops marking", () => {
    const c = createFakeCell({ source: "draw" });
    const panel = createFakeNotebookPanel({ cells: [c], windowingMode: "full" });
    const app = createFakeApp({ panels: [panel] });
    const hub = createFakeBroadcastHub();
    const win = createFakeWindow({ app, document: createFakeDocument(), broadcast: hub });
    const logger = recordingLogger();
    const chrome = mountChrome({ app, logger });
    const before = {
      outputs: c.model.outputs.changed.connectionCount,
      viewport: c.inViewportChanged.connectionCount,
      active: panel.content.activeCellChanged.connectionCount,
      status: panel.sessionContext.statusChanged.connectionCount,
      layout: app.shell.layoutModified.connectionCount,
    };
    const stale = real.mountStale({ app, win, logger, controllers: { chrome } });
    expect(c.model.outputs.changed.connectionCount).toBeGreaterThan(before.outputs);
    expect(hub.openCount(CHANNEL)).toBe(1);

    draw(c, 1, stamp({ resource: "assay", rev: 1, session: "sA", exec: 1 }));
    stale.dispose();
    expect(c.model.outputs.changed.connectionCount).toBe(before.outputs);
    expect(c.inViewportChanged.connectionCount).toBe(before.viewport);
    expect(panel.content.activeCellChanged.connectionCount).toBe(before.active);
    expect(panel.sessionContext.statusChanged.connectionCount).toBe(before.status);
    expect(app.shell.layoutModified.connectionCount).toBe(before.layout);
    expect(hub.openCount(CHANNEL)).toBe(0);

    hub.post(CHANNEL, announcement({ session: "sA", exec: 2, revs: { assay: 2 } }));
    expect(texts(c)).toEqual([]);
    expect(() => stale.dispose()).not.toThrow();
    expect(logger.errors).toEqual([]);
  });

  test("contentVisibility subscribes to no viewport signal; other modes do", () => {
    const cv = createFakeCell({ source: "a" });
    const full = createFakeCell({ source: "b" });
    const P = createFakeNotebookPanel({ cells: [cv] });
    const Q = createFakeNotebookPanel({ cells: [full], windowingMode: "full" });
    world({ panels: [P, Q] });
    expect(cv.inViewportChanged.connectionCount).toBe(0);
    expect(full.inViewportChanged.connectionCount).toBeGreaterThan(0);
  });

  test("createFakeSignal sanity: the connection counts above count real connections", () => {
    const s = createFakeSignal();
    const f = () => {};
    s.connect(f);
    expect(s.connectionCount).toBe(1);
    s.disconnect(f);
    expect(s.connectionCount).toBe(0);
  });
});
