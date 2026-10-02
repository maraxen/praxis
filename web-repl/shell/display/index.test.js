// index.test.js -- the display entry and its loader (spec
// .praxia/docs/specs/260929_notebook-display-epic.md section 4 rows for
// display/index.js and praxis-shell.js; D13: display failures are non-fatal).
//
// Two things are under test: `mount(window)` in index.js, and the loader IIFE
// appended to praxis-shell.js (extracted by its marker line and run against a
// fake window/document/location, with a stub display/index.js in a temp dir so
// nothing real is mounted).

import { describe, expect, test } from "bun:test";
import { mkdtempSync, mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { pathToFileURL } from "node:url";

import { mount, mountDisplayErrorBanner } from "./index.js";
import { EXEC_ATTR, STATE_ATTR } from "./chrome.js";
import {
  announcement,
  createFakeApp,
  createFakeBroadcastHub,
  createFakeCell,
  createFakeDocument,
  createFakeNotebookPanel,
  createFakeWindow,
  praxisOutput,
  stamp,
} from "./__tests__/fakes.js";

function recordingLogger() {
  const errors = [];
  return { errors, error: (...a) => errors.push(a), warn() {}, log() {} };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("mount(window)", () => {
  test("waits for jupyterapp, then for app.restored, then mounts chrome with the app", async () => {
    const order = [];
    let resolveRestored;
    const app = createFakeApp();
    app.restored = new Promise((r) => {
      resolveRestored = r;
    });
    const win = createFakeWindow({ app: null });
    const modules = {
      chrome: async () => ({
        mountChrome: (opts) => {
          order.push(["mountChrome", opts.app === app]);
          return { dispose() {} };
        },
      }),
    };
    const done = mount(win, { modules, logger: recordingLogger() });
    await flush();
    expect(order).toEqual([]); // no app yet
    win.jupyterapp = app;
    win.tick();
    await flush();
    expect(order).toEqual([]); // app present, not restored
    resolveRestored();
    const result = await done;
    expect(order).toEqual([["mountChrome", true]]);
    expect(result.errors).toEqual([]);
    expect(win.pendingTimers).toBe(0);
  });

  test("with the real chrome module it writes the cell states of an open notebook", async () => {
    const cell = createFakeCell({ source: "x = 1", executionCount: 2, outputs: ["stream"] });
    const app = createFakeApp({ panels: [createFakeNotebookPanel({ cells: [cell] })] });
    const win = createFakeWindow({ app });
    const result = await mount(win, { logger: recordingLogger() });
    expect(result.errors).toEqual([]);
    expect(cell.node.getAttribute(STATE_ATTR)).toBe("ran");
    expect(cell.node.getAttribute(EXEC_ATTR)).toBe("2");
  });

  test("a chrome module that fails to load is contained: mount resolves, loudly", async () => {
    const win = createFakeWindow({ app: createFakeApp() });
    const logger = recordingLogger();
    const modules = {
      chrome: async () => {
        throw new SyntaxError("chrome.js does not parse");
      },
    };
    const result = await mount(win, { modules, logger });
    expect(result.errors.map((e) => e.module)).toEqual(["chrome"]);
    expect(result.errors[0].message).toContain("does not parse");
    expect(logger.errors.length).toBeGreaterThan(0);
    expect(logger.errors[0].join(" ")).toContain("chrome");
  });

  test("a chrome module whose mountChrome throws is contained", async () => {
    const win = createFakeWindow({ app: createFakeApp() });
    const logger = recordingLogger();
    const modules = {
      chrome: async () => ({
        mountChrome() {
          throw new Error("mount blew up");
        },
      }),
    };
    const result = await mount(win, { modules, logger });
    expect(result.errors.map((e) => e.module)).toEqual(["chrome"]);
    expect(logger.errors.length).toBeGreaterThan(0);
  });

  test("a chrome module without a mountChrome export is contained", async () => {
    const win = createFakeWindow({ app: createFakeApp() });
    const result = await mount(win, { modules: { chrome: async () => ({}) }, logger: recordingLogger() });
    expect(result.errors.map((e) => e.module)).toEqual(["chrome"]);
  });

  test("app.restored rejecting is contained", async () => {
    const app = createFakeApp();
    app.restored = Promise.reject(new Error("restore failed"));
    const logger = recordingLogger();
    const result = await mount(createFakeWindow({ app }), { logger });
    expect(result.errors.length).toBe(1);
    expect(logger.errors.length).toBeGreaterThan(0);
  });

  test("the outcome is recorded on window.__praxisDisplay for probing", async () => {
    const win = createFakeWindow({ app: createFakeApp() });
    await mount(win, { logger: recordingLogger() });
    expect(win.__praxisDisplay.status).toBe("mounted");
    const bad = createFakeWindow({ app: createFakeApp() });
    await mount(bad, {
      modules: {
        chrome: async () => {
          throw new Error("x");
        },
      },
      logger: recordingLogger(),
    });
    expect(bad.__praxisDisplay.status).toBe("failed");
  });
});

// -- B9: stale and interact rows ------------------------------------------------------------

describe("mount(window): the stale and interact rows (B9)", () => {
  function rows({ stale, interact, chrome } = {}) {
    const order = [];
    const modules = {
      chrome: async () => ({
        mountChrome: (opts) => {
          order.push("chrome");
          if (chrome) throw chrome;
          return { tag: "chrome-controller", onExecution() {}, windowing() {} };
        },
      }),
      stale: async () => {
        if (stale === "load") throw new SyntaxError("stale.js does not parse");
        return {
          mountStale: (opts) => {
            order.push("stale");
            if (stale === "throw") throw new Error("stale mount blew up");
            order.push(["stale sees chrome", opts.controllers.chrome?.tag]);
            return { tag: "stale-controller" };
          },
        };
      },
      interact: async () => ({
        mountInteract: (opts) => {
          order.push("interact");
          if (interact === "throw") throw new Error("interact mount blew up");
          order.push(["interact sees stale", opts.controllers.stale?.tag]);
          return { tag: "interact-controller" };
        },
      }),
    };
    return { modules, order };
  }

  test("chrome, then stale, then interact; each receives the earlier controllers", async () => {
    const { modules, order } = rows();
    const win = createFakeWindow({ app: createFakeApp() });
    const result = await mount(win, { modules, logger: recordingLogger() });
    expect(result.errors).toEqual([]);
    expect(order).toEqual([
      "chrome",
      "stale",
      ["stale sees chrome", "chrome-controller"],
      "interact",
      ["interact sees stale", "stale-controller"],
    ]);
    expect(Object.keys(result.controllers)).toEqual(["chrome", "stale", "interact"]);
  });

  test("a stale module that fails to load does not stop interact, and is named", async () => {
    const { modules, order } = rows({ stale: "load" });
    const logger = recordingLogger();
    const result = await mount(createFakeWindow({ app: createFakeApp() }), { modules, logger });
    expect(result.errors.map((e) => e.module)).toEqual(["stale"]);
    expect(result.errors[0].message).toContain("does not parse");
    expect(order).toContain("interact");
    expect(result.controllers.interact.tag).toBe("interact-controller");
    expect(logger.errors.length).toBeGreaterThan(0);
  });

  test("a stale mount that throws does not stop interact", async () => {
    const { modules, order } = rows({ stale: "throw" });
    const result = await mount(createFakeWindow({ app: createFakeApp() }), { modules, logger: recordingLogger() });
    expect(result.errors.map((e) => e.module)).toEqual(["stale"]);
    expect(order).toContain("interact");
  });

  test("an interact mount that throws leaves chrome and stale mounted", async () => {
    const { modules } = rows({ interact: "throw" });
    const result = await mount(createFakeWindow({ app: createFakeApp() }), { modules, logger: recordingLogger() });
    expect(result.errors.map((e) => e.module)).toEqual(["interact"]);
    expect(result.controllers.chrome.tag).toBe("chrome-controller");
    expect(result.controllers.stale.tag).toBe("stale-controller");
  });

  test("a chrome that fails still lets stale and interact mount (stale runs without it)", async () => {
    const { modules, order } = rows({ chrome: new Error("chrome blew up") });
    const result = await mount(createFakeWindow({ app: createFakeApp() }), { modules, logger: recordingLogger() });
    expect(result.errors.map((e) => e.module)).toEqual(["chrome"]);
    expect(order).toContainEqual(["stale sees chrome", undefined]);
    expect(order).toContain("interact");
  });

  test("a modules table that omits a row skips it (the seam of the chrome-only tests above)", async () => {
    const result = await mount(createFakeWindow({ app: createFakeApp() }), {
      modules: { chrome: async () => ({ mountChrome: () => ({}) }) },
      logger: recordingLogger(),
    });
    expect(result.errors).toEqual([]);
    expect(Object.keys(result.controllers)).toEqual(["chrome"]);
  });

  test("with the real modules: an announcement marks a stamped output, a click reaches the dock", async () => {
    const cell = createFakeCell({
      source: "x",
      executionCount: 2,
      outputs: [praxisOutput(stamp({ resource: "assay", rev: 1, session: "sA", exec: 2 }))],
    });
    const app = createFakeApp({ panels: [createFakeNotebookPanel({ cells: [cell] })] });
    const hub = createFakeBroadcastHub();
    const document = createFakeDocument();
    const win = createFakeWindow({ app, document, broadcast: hub });
    const logger = recordingLogger();
    const result = await mount(win, { logger });
    expect(result.errors).toEqual([]);
    expect(result.status).toBe("mounted");
    expect(Object.keys(result.controllers)).toEqual(["chrome", "stale", "interact", "dock"]); // C5: dock is the fourth row

    hub.post("praxis_repl", announcement({ session: "sA", exec: 3, revs: { assay: 2 } }));
    const marks = cell.host(0).children.filter((c) => c.classList.contains("praxis-stale"));
    expect(marks.map((m) => m.textContent)).toEqual(["Changed since, see deck panel."]);

    const calls = [];
    result.controllers.dock = { focus: (name) => calls.push(name) };
    const g = document.createElement("g");
    g.setAttribute("data-praxis-res", "assay");
    document.body.appendChild(g);
    g.dispatch("click", {});
    expect(calls).toEqual(["assay"]);
    expect(logger.errors).toEqual([]);
  });
});

// -- the loader IIFE appended to praxis-shell.js ---------------------------------

const SHELL_PATH = new URL("../praxis-shell.js", import.meta.url);
const MARKER = "// A5 -- notebook display loader";

function loaderSource() {
  const text = readFileSync(SHELL_PATH, "utf8");
  const at = text.indexOf(MARKER);
  expect(at).toBeGreaterThan(-1);
  return text.slice(at);
}

/** Run the loader against fakes. `stubBody` is the body of a stub
 * display/index.js placed next to a fake praxis-shell.js in a temp dir. */
async function runLoader({ pathname = "/praxis/lab/index.html", stubBody, currentScript = "auto" } = {}) {
  const dir = mkdtempSync(join(tmpdir(), "praxis-display-loader-"));
  mkdirSync(join(dir, "display"));
  writeFileSync(join(dir, "display", "index.js"), stubBody ?? "export async function mount() {}\n");
  const src = pathToFileURL(join(dir, "praxis-shell.js")).href;
  const errors = [];
  const fakeConsole = { error: (...a) => errors.push(a), warn() {}, log() {} };
  const document = { currentScript: currentScript === "auto" ? { src } : currentScript };
  const win = { marker: "the-window" };
  const location = { pathname };
  let threw = null;
  try {
    new Function("window", "document", "location", "console", loaderSource())(win, document, location, fakeConsole);
  } catch (err) {
    threw = err;
  }
  await new Promise((resolve) => setTimeout(resolve, 100));
  return { threw, errors, win, dir };
}

describe("praxis-shell.js loader IIFE", () => {
  test("the loader is appended after the persistence loader, once", () => {
    const text = readFileSync(SHELL_PATH, "utf8");
    expect(text.split("display/index.js").length - 1).toBeGreaterThanOrEqual(1);
    expect(text.split(MARKER).length - 1).toBe(1);
    expect(text.indexOf("persistence/panel.js")).toBeLessThan(text.indexOf(MARKER));
    // Gated to the lab/ entry, like the persistence loader (the regex literal
    // \/lab\/(index\.html)?$; the behavioural cases below prove the gate).
    expect(loaderSource()).toContain("\\/lab\\/");
  });

  test("on /lab/ it imports display/index.js and calls mount(window)", async () => {
    const stub =
      "export async function mount(win) { win.mountedBy = 'stub'; win.sawMarker = win.marker; }\n";
    const { threw, errors, win } = await runLoader({ stubBody: stub });
    expect(threw).toBeNull();
    expect(errors).toEqual([]);
    expect(win.mountedBy).toBe("stub");
    expect(win.sawMarker).toBe("the-window");
  });

  test("the lab/ gate also accepts the bare directory path", async () => {
    const stub = "export async function mount(win) { win.mountedBy = 'stub'; }\n";
    const { win } = await runLoader({ pathname: "/lab/", stubBody: stub });
    expect(win.mountedBy).toBe("stub");
  });

  test("off the lab/ entry it does nothing", async () => {
    const stub = "export async function mount(win) { win.mountedBy = 'stub'; }\n";
    const { threw, errors, win } = await runLoader({ pathname: "/praxis/repl/index.html", stubBody: stub });
    expect(threw).toBeNull();
    expect(errors).toEqual([]);
    expect(win.mountedBy).toBeUndefined();
  });

  test("a mount that rejects is logged and never thrown", async () => {
    const stub = "export async function mount() { throw new Error('mount rejected'); }\n";
    const { threw, errors } = await runLoader({ stubBody: stub });
    expect(threw).toBeNull();
    expect(errors.length).toBe(1);
    expect(errors[0].join(" ")).toContain("mount rejected");
  });

  test("a display/index.js that does not parse is logged and never thrown", async () => {
    const { threw, errors } = await runLoader({ stubBody: "export const = ;\n" });
    expect(threw).toBeNull();
    expect(errors.length).toBe(1);
  });

  test("a missing display/index.js (an unstaged dist) is logged and never thrown", async () => {
    const dir = mkdtempSync(join(tmpdir(), "praxis-display-loader-missing-"));
    const src = pathToFileURL(join(dir, "praxis-shell.js")).href;
    const errors = [];
    let threw = null;
    try {
      new Function("window", "document", "location", "console", loaderSource())(
        {},
        { currentScript: { src } },
        { pathname: "/lab/index.html" },
        { error: (...a) => errors.push(a), warn() {}, log() {} },
      );
    } catch (err) {
      threw = err;
    }
    await new Promise((resolve) => setTimeout(resolve, 100));
    expect(threw).toBeNull();
    expect(errors.length).toBe(1);
  });

  test("an unresolvable script src is logged and never thrown", async () => {
    const { threw, errors } = await runLoader({ currentScript: null });
    expect(threw).toBeNull();
    expect(errors.length).toBe(1);
  });
});


// -- D13 / B8: the shell side of praxis:display-error ---------------------------------------
//
// The kernel's bootstrap stage (praxis_bootstrap.py, step 13) catches a failure to install the
// display and posts {type: "praxis:display-error", reason} on praxis_repl before praxis:ready. D13:
// "the shell shows [it] as a one-line banner. It is never silent." index.js owns that banner. It
// listens from the start of mount(), before jupyterapp exists, so an early message is not lost.

describe("the praxis:display-error banner (D13, B8)", () => {
  function setup({ app = createFakeApp(), withDocument = true, withBroadcast = true } = {}) {
    const document = withDocument ? createFakeDocument() : null;
    const hub = withBroadcast ? createFakeBroadcastHub() : null;
    const win = createFakeWindow({ app, document, broadcast: hub });
    return { win, document, hub };
  }
  const banners = (document) => document.body.children.filter((c) => c.hasAttribute("data-praxis-display-error"));

  test("a display-error message shows one banner with the reason, as plain text", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    expect(banners(document)).toEqual([]); // nothing until the kernel says so
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "boom: cannot draw" });
    const [banner] = banners(document);
    expect(banner).toBeDefined();
    expect(banner.getAttribute("role")).toBe("alert");
    expect(banner.textContent).toContain("boom: cannot draw");
    expect(banner.textContent).toContain("display");
    expect(banner.textContent).not.toContain("\n");
  });

  test("the reason is text, never markup", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "<img src=x onerror=alert(1)>&amp;" });
    const [banner] = banners(document);
    expect(banner.textContent).toContain("<img src=x onerror=alert(1)>&amp;");
    // built with createElement + textContent only: no element other than the message and the dismiss button
    const tags = [];
    const walk = (el) => el.children.forEach((c) => (tags.push(c.localName), walk(c)));
    walk(banner);
    expect(tags.every((t) => t === "span" || t === "button")).toBe(true);
  });

  test("it listens from the start of mount, so a message before jupyterapp exists is not lost", async () => {
    const { win, document, hub } = setup({ app: null });
    const done = mount(win, { modules: {}, logger: recordingLogger() });
    await flush();
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "early" });
    expect(banners(document).length).toBe(1);
    win.jupyterapp = createFakeApp();
    win.tick();
    await done;
    expect(banners(document).length).toBe(1);
  });

  test("other messages on the channel do nothing", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    for (const data of [
      { type: "praxis:ready" },
      { type: "praxis:error", reason: "fail-closed is the shell's other message" },
      { type: "praxis:resource-changed", json: "{}" },
      { type: "praxis:shell-ping" },
      { reason: "no type" },
      null,
      "praxis:display-error",
      42,
    ]) {
      hub.post("praxis_repl", data);
    }
    expect(banners(document)).toEqual([]);
  });

  test("a message on another channel does nothing", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_viz3d", { type: "praxis:display-error", reason: "wrong channel" });
    expect(banners(document)).toEqual([]);
  });

  test("a second message updates the one banner instead of stacking", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "first" });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "second" });
    const found = banners(document);
    expect(found.length).toBe(1);
    expect(found[0].textContent).toContain("second");
    expect(found[0].textContent).not.toContain("first");
  });

  test("the dismiss button removes the banner, and a later message shows it again", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "x" });
    const [banner] = banners(document);
    const button = banner.children.find((c) => c.localName === "button");
    expect(button.getAttribute("aria-label")).toBeTruthy();
    button.dispatch("click");
    expect(banners(document)).toEqual([]);
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "again" });
    expect(banners(document).length).toBe(1);
  });

  test("a missing or non-string reason still gives a banner, and a huge one is capped to one line", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error" });
    expect(banners(document)[0].textContent).toContain("unknown");
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "a".repeat(5000) + "\nsecond line" });
    const text = banners(document)[0].textContent;
    expect(text.length).toBeLessThan(500);
    expect(text).not.toContain("\n");
  });

  test("with no BroadcastChannel or no document, mount still works and says nothing", async () => {
    for (const opts of [{ withBroadcast: false }, { withDocument: false }, { withBroadcast: false, withDocument: false }]) {
      const { win } = setup(opts);
      const logger = recordingLogger();
      const result = await mount(win, { modules: {}, logger });
      expect(result.errors).toEqual([]);
      expect(logger.errors).toEqual([]);
    }
  });

  test("mountDisplayErrorBanner is contained when the document throws, and reports it loudly", () => {
    const { hub } = setup();
    const document = createFakeDocument();
    document.createElement = () => {
      throw new Error("dom is broken");
    };
    const win = createFakeWindow({ app: createFakeApp(), document, broadcast: hub });
    const logger = recordingLogger();
    const controller = mountDisplayErrorBanner({ win, logger });
    expect(() => hub.post("praxis_repl", { type: "praxis:display-error", reason: "r" })).not.toThrow();
    expect(logger.errors.length).toBe(1);
    expect(typeof controller.dispose).toBe("function");
  });

  test("dispose closes the channel and takes the banner away", async () => {
    const { win, document, hub } = setup();
    const controller = mountDisplayErrorBanner({ win, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "x" });
    expect(banners(document).length).toBe(1);
    controller.dispose();
    expect(banners(document)).toEqual([]);
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "y" });
    expect(banners(document)).toEqual([]);
  });

  test("the banner uses no storage and no selector built from the message", async () => {
    const { win, document, hub } = setup();
    await mount(win, { modules: {}, logger: recordingLogger() });
    hub.post("praxis_repl", { type: "praxis:display-error", reason: "a\"]'b" });
    expect(document.body.selectorCalls).toEqual([]);
    expect(document.selectorCalls).toEqual([]);
  });
});
