// index.js -- entry of the notebook display shell code (spec
// .praxia/docs/specs/260929_notebook-display-epic.md section 4, index.js row;
// D13; task A5). Loaded by the loader IIFE appended to praxis-shell.js, which
// calls `mount(window)` on the lab/ entry only.
//
// `mount(window)` waits for `window.jupyterapp` (the app handle the shell
// already uses) and for `app.restored`, then mounts each display module in
// order: `chrome` (sprint A), then `stale` and `interact` (sprint B, B9), and
// `dock` (sprint C) becomes a further row of MODULES. `stale` reads the chrome's
// controller (observed executions) and `interact` reads a later `controllers.dock`
// at click time, both through the `controllers` they are handed.
//
// NON-FATAL BY CONTRACT (D13). A broken drawing layer must not take the REPL
// away from the user, so `mount` never rejects and never throws: a module that
// fails to load, or whose mount function throws or is missing, is logged loudly
// with `logger.error` and recorded in the result and on
// `window.__praxisDisplay`; the modules after it still mount. Nothing is
// swallowed silently. (The typed `praxis:display-error` channel message and its
// banner belong to the bootstrap stage and are not sent from here.)

/** One row per display module: how to load it and which export mounts it. Each
 * mount function receives `{app, win, logger, controllers}`, where `controllers`
 * holds what earlier modules returned (`controllers.chrome`, for `stale`). */
const MODULES = [
  { name: "chrome", mount: "mountChrome" },
  { name: "stale", mount: "mountStale" },
  { name: "interact", mount: "mountInteract" },
];

const DEFAULT_LOADERS = {
  chrome: () => import("./chrome.js"),
  stale: () => import("./stale.js"),
  interact: () => import("./interact.js"),
};

function waitForJupyterApp(win) {
  if (win.jupyterapp) return Promise.resolve(win.jupyterapp);
  return new Promise((resolve) => {
    const interval = win.setInterval(() => {
      if (win.jupyterapp) {
        win.clearInterval(interval);
        resolve(win.jupyterapp);
      }
    }, 50);
  });
}

/**
 * Mount the display. Never rejects.
 *
 * @param {Window} win
 * @param {object} [options]
 * @param options.modules  name -> () => Promise<module>; defaults to the real
 *                         modules (a test seam). A row this table has no loader
 *                         for is skipped, so a caller can mount a subset.
 * @param options.logger   console-like; defaults to `console`
 * @returns {Promise<{status: "mounted"|"failed", errors: Array<{module: string,
 *   message: string, error: unknown}>, controllers: object}>}
 */
export async function mount(win, { modules = DEFAULT_LOADERS, logger = console } = {}) {
  const errors = [];
  const controllers = {};

  function record(module, err) {
    const message = err && err.message ? err.message : String(err);
    errors.push({ module, message, error: err });
    try {
      logger.error(`praxis display: ${module} failed to load or mount, the display is degraded:`, err);
    } catch {
      // A broken logger must not break the shell either.
    }
  }

  try {
    const app = await waitForJupyterApp(win);
    await app.restored;
    for (const spec of MODULES) {
      const load = modules[spec.name];
      if (typeof load !== "function" && modules !== DEFAULT_LOADERS) continue; // a subset was asked for
      try {
        const mod = await load();
        if (typeof mod[spec.mount] !== "function") {
          throw new Error(`display/${spec.name}.js does not export ${spec.mount}()`);
        }
        controllers[spec.name] = mod[spec.mount]({ app, win, logger, controllers });
      } catch (err) {
        record(spec.name, err);
      }
    }
  } catch (err) {
    record("app", err);
  }

  const result = { status: errors.length === 0 ? "mounted" : "failed", errors, controllers };
  try {
    win.__praxisDisplay = result;
  } catch {
    // A frozen window object is not worth failing over.
  }
  return result;
}
