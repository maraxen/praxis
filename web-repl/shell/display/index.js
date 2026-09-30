// index.js -- entry of the notebook display shell code (spec
// .praxia/docs/specs/260929_notebook-display-epic.md section 4, index.js row;
// D13; task A5). Loaded by the loader IIFE appended to praxis-shell.js, which
// calls `mount(window)` on the lab/ entry only.
//
// `mount(window)` waits for `window.jupyterapp` (the app handle the shell
// already uses) and for `app.restored`, then mounts each display module in
// order: `chrome` (sprint A), then `stale` and `interact` (sprint B, B9), then
// `dock` (sprint C, C5: the deck panel). `stale` reads the chrome's controller
// (observed executions) and `interact` reads a later `controllers.dock` at click
// time, both through the `controllers` they are handed; `dock` is mounted after
// `interact` and is the object interact.js finds there (`controllers.dock.focus`).
//
// NON-FATAL BY CONTRACT (D13). A broken drawing layer must not take the REPL
// away from the user, so `mount` never rejects and never throws: a module that
// fails to load, or whose mount function throws or is missing, is logged loudly
// with `logger.error` and recorded in the result and on
// `window.__praxisDisplay`; the modules after it still mount. Nothing is
// swallowed silently.
//
// THE KERNEL'S HALF OF D13 (B8). The bootstrap's display stage catches a failure to
// install `praxis.display` and posts `{type: "praxis:display-error", reason}` on the
// `praxis_repl` channel before `praxis:ready`. D13: "the shell shows [it] as a
// one-line banner. It is never silent." That banner is here (`mountDisplayErrorBanner`),
// started at the very beginning of `mount` (before `jupyterapp` exists, so a message
// sent early is not lost). The message is plain text only: built with createElement
// and textContent, never markup, and no selector is built from it (D14).

/** One row per display module: how to load it and which export mounts it. Each
 * mount function receives `{app, win, logger, controllers}`, where `controllers`
 * holds what earlier modules returned (`controllers.chrome`, for `stale`). */
const MODULES = [
  { name: "chrome", mount: "mountChrome" },
  { name: "stale", mount: "mountStale" },
  { name: "interact", mount: "mountInteract" },
  { name: "dock", mount: "mountDock" },
];

const DEFAULT_LOADERS = {
  chrome: () => import("./chrome.js"),
  stale: () => import("./stale.js"),
  interact: () => import("./interact.js"),
  dock: () => import("./dock.js"),
};

const CHANNEL = "praxis_repl";
const DISPLAY_ERROR = "praxis:display-error";
const BANNER_ATTR = "data-praxis-display-error";
const REASON_MAX = 300;

function bannerText(reason) {
  let text = typeof reason === "string" ? reason.replace(/\s+/g, " ").trim() : "";
  if (!text) text = "unknown error";
  if (text.length > REASON_MAX) text = `${text.slice(0, REASON_MAX - 1)}…`;
  return `The notebook display did not start (${text}). PyLabRobot still works; outputs will look plain.`;
}

/**
 * Show `praxis:display-error` messages as a one-line banner (D13, task B8). Never throws.
 *
 * @param {object} options
 * @param options.win     the window (`document`, `BroadcastChannel`); with either missing
 *                        this is a quiet no-op
 * @param options.logger  console-like
 * @returns {{dispose(): void}}
 */
export function mountDisplayErrorBanner({ win, logger = console }) {
  const noop = { dispose() {} };
  const document = win && win.document;
  const Channel = win && win.BroadcastChannel;
  if (!document || typeof Channel !== "function") return noop;

  let banner = null;
  let label = null;

  function show(reason) {
    const text = bannerText(reason);
    if (banner && banner.parentNode) {
      label.textContent = text;
      return;
    }
    banner = document.createElement("div");
    banner.setAttribute(BANNER_ATTR, "");
    banner.setAttribute("role", "alert");
    Object.assign(banner.style, {
      position: "fixed",
      top: "0",
      left: "0",
      right: "0",
      zIndex: "10000",
      display: "flex",
      alignItems: "center",
      gap: "8px",
      padding: "4px 12px",
      whiteSpace: "nowrap",
      overflow: "hidden",
      textOverflow: "ellipsis",
      fontSize: "13px",
      color: "var(--jp-error-color1, #B3402A)",
      background: "var(--jp-layout-color1, #EEF1F4)",
      borderBottom: "1px solid var(--jp-error-color1, #B3402A)",
    });
    label = document.createElement("span");
    label.textContent = text;
    const close = document.createElement("button");
    close.setAttribute("type", "button");
    close.setAttribute("aria-label", "Dismiss this message");
    close.textContent = "×";
    close.addEventListener("click", () => dismiss());
    banner.appendChild(label);
    banner.appendChild(close);
    document.body.appendChild(banner);
  }

  function dismiss() {
    if (banner) banner.remove();
    banner = null;
    label = null;
  }

  function onMessage(event) {
    try {
      const data = event && event.data;
      if (!data || typeof data !== "object" || data.type !== DISPLAY_ERROR) return;
      show(data.reason);
    } catch (err) {
      try {
        logger.error("praxis display: could not show the display-error banner:", err);
      } catch {
        // A broken logger must not break the shell either.
      }
    }
  }

  let channel = null;
  try {
    channel = new Channel(CHANNEL);
    channel.addEventListener("message", onMessage);
  } catch (err) {
    try {
      logger.error("praxis display: cannot listen for display-error messages:", err);
    } catch {
      // ignore
    }
    return noop;
  }
  return {
    dispose() {
      try {
        channel.removeEventListener("message", onMessage);
        channel.close();
      } catch {
        // already closed
      }
      dismiss();
    },
  };
}

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
 *   message: string, error: unknown}>, controllers: object, banner: {dispose(): void}}>}
 */
export async function mount(win, { modules = DEFAULT_LOADERS, logger = console } = {}) {
  const errors = [];
  const controllers = {};
  // D13: listen for the kernel's praxis:display-error before anything else, so an early one is not lost.
  const banner = mountDisplayErrorBanner({ win, logger });

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

  const result = { status: errors.length === 0 ? "mounted" : "failed", errors, controllers, banner };
  try {
    win.__praxisDisplay = result;
  } catch {
    // A frozen window object is not worth failing over.
  }
  return result;
}
