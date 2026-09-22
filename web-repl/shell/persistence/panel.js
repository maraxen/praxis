// panel.js -- REPL persistence ladder: DOM + real browser adapters
// (backlog #4296, T6; spec
// .praxia/docs/specs/260922_repl-persistence-ladder.md sections 3, 4, D4, D5).
//
// This is the ONLY module in web-repl/shell/persistence that ever names
// `window`, `document`, `navigator`, `indexedDB` or FSA globals directly.
// core.js (T2-T4) is a pure DI state machine with none of those; this file
// builds its real adapters, wires DOM events and Lumino signals to it, and
// renders the status chip / panel / first-save `<dialog>` from `core.state`
// snapshots. `mount(window)` is the module's only export (module plan row).
//
// D6 gesture invariant (statically enforced by T5's
// check_gesture_invariant.py over this directory): every button's click
// listener is EXACTLY `() => core.on<Something>Click(...)`, with nothing --
// no `await`, no `.then(`, no other statement -- before that call. Anything
// asynchronous is chained on the promise the call returns. `pickDirectory`
// is injected into core as `window.showDirectoryPicker.bind(window)` -- a
// REFERENCE, not a call -- so the literal string `showDirectoryPicker(`
// never appears in this file; `core.js` never names it at all.
//
// The smoke harness's forced-prompt test switch is a page-level test-only
// global; this file must never reference it (B-11).

import { createPersistence } from "./core.js";

const DB_NAME = "praxis-repl-persistence";
const DB_STORE = "handles";
const SAVE_COMMAND_IDS = new Set(["docmanager:save", "docmanager:save-as", "docmanager:save-all"]);
const REASON_DIFFERS_ON_DISK = "differs on disk";

// -- Real adapter: raw IndexedDB handle store --------------------------------
//
// DB `praxis-repl-persistence`, store `handles` (module plan row for this
// file). The name deliberately does NOT match the legacy migration's
// `/^JupyterLite Storage - /` pattern (AC-14 storage hygiene). `rebind` is
// the one atomic operation core.js requires (D1, B-2): it stores the new
// handle AND clears the three binding-scoped sets in a SINGLE readwrite
// transaction, so nothing can ever observe a half-cleared binding.

function openHandleDb() {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      if (!request.result.objectStoreNames.contains(DB_STORE)) {
        request.result.createObjectStore(DB_STORE);
      }
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

function idbRequest(store, method, ...args) {
  return new Promise((resolve, reject) => {
    const request = store[method](...args);
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

/** @returns {import("./core.js").HandleStore} */
function createIndexedDbHandleStore() {
  let dbPromise = null;
  function db() {
    if (!dbPromise) dbPromise = openHandleDb();
    return dbPromise;
  }
  return {
    async get(key) {
      const conn = await db();
      const tx = conn.transaction(DB_STORE, "readonly");
      return idbRequest(tx.objectStore(DB_STORE), "get", key);
    },
    async set(key, value) {
      const conn = await db();
      return new Promise((resolve, reject) => {
        const tx = conn.transaction(DB_STORE, "readwrite");
        tx.objectStore(DB_STORE).put(value, key);
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    },
    async rebind(handle) {
      const conn = await db();
      return new Promise((resolve, reject) => {
        const tx = conn.transaction(DB_STORE, "readwrite");
        const store = tx.objectStore(DB_STORE);
        store.put(handle, "working-folder");
        store.put([], "pending-paths");
        store.put({}, "excluded-paths");
        store.put([], "mirrored-paths");
        tx.oncomplete = () => resolve();
        tx.onerror = () => reject(tx.error);
      });
    },
  };
}

// -- Waiting for the JupyterLab app -----------------------------------------

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

// -- DOM construction ---------------------------------------------------------
//
// Stable selectors (T6):
//   #praxis-persistence[data-praxis-tier][data-praxis-excluded]
//   [data-praxis-action=protect|choose-folder|reconnect|restore|keep-browser-only|toggle-panel]
//   [data-praxis-action=replace-disk-copy][data-praxis-path="<path>"]
//   dialog#praxis-persistence-first-save

function el(doc, tag, props) {
  const node = doc.createElement(tag);
  if (props) Object.assign(node, props);
  return node;
}

function buildChrome(doc) {
  const root = el(doc, "div", { id: "praxis-persistence" });
  root.setAttribute("data-praxis-tier", "L0");
  root.setAttribute("data-praxis-excluded", "0");
  // Fixed, content-sized box (D1 section 3.1: "must not intercept pointer
  // events outside its own box"). A block-level element only claims clicks
  // within its own laid-out box, so keeping this box content-sized (not
  // spanning the viewport) is sufficient -- no pointer-events trickery
  // needed.
  Object.assign(root.style, {
    position: "fixed",
    right: "8px",
    bottom: "8px",
    zIndex: "2147483000",
    display: "inline-flex",
    flexDirection: "column",
    alignItems: "flex-end",
    fontFamily: "system-ui, sans-serif",
    fontSize: "12px",
    maxWidth: "320px",
  });

  const chip = el(doc, "button", { type: "button" });
  chip.setAttribute("data-praxis-action", "toggle-panel");
  Object.assign(chip.style, {
    border: "1px solid #888",
    borderRadius: "4px",
    padding: "4px 8px",
    background: "#fff",
    cursor: "pointer",
  });

  const panel = el(doc, "div");
  panel.hidden = true;
  Object.assign(panel.style, {
    marginTop: "4px",
    border: "1px solid #888",
    borderRadius: "4px",
    padding: "8px",
    background: "#fff",
    maxWidth: "320px",
  });

  root.append(chip, panel);

  const dialog = el(doc, "dialog", { id: "praxis-persistence-first-save" });
  dialog.setAttribute("role", "dialog");
  dialog.setAttribute("aria-labelledby", "praxis-persistence-first-save-text");
  dialog.tabIndex = -1; // focus() fallback target if the dialog ever has no focusable child

  return { root, chip, panel, dialog };
}

function textEl(doc, tag, text) {
  const node = el(doc, tag);
  node.textContent = text;
  return node;
}

function actionButton(doc, action, text, onClick) {
  const button = el(doc, "button", { type: "button" });
  button.setAttribute("data-praxis-action", action);
  button.textContent = text;
  button.addEventListener("click", onClick);
  return button;
}

// -- Status-chip / panel labels -----------------------------------------------

function tierLabel(state) {
  switch (state.tier) {
    case "L0":
      return { text: "Browser only", warn: true };
    case "L1":
      return { text: "Browser storage protected", warn: false };
    case "L2":
      return state.excludedCount > 0
        ? { text: `Folder: ${state.folderName} (${state.excludedCount} not mirrored)`, warn: true }
        : { text: `Folder: ${state.folderName}`, warn: false };
    case "L2-syncing":
      return { text: `Folder: ${state.folderName} (syncing ${state.pendingCount})`, warn: false };
    case "L2-paused":
      return state.pauseReason === "folder-unavailable"
        ? { text: "Folder unavailable", warn: true }
        : { text: "Folder disconnected", warn: true };
    default:
      return { text: "", warn: false };
  }
}

function protectLabel(state) {
  return state.askAgain ? "Ask again" : "Protect browser storage";
}

// -- The module ---------------------------------------------------------------

/**
 * Mount the persistence chip/panel/modal into `win`. Waits for
 * `win.jupyterapp` to exist and for `app.restored` to resolve before
 * building or rendering anything (D1 section 3.1, T6 "Render only after
 * app.restored").
 *
 * @param {Window} win
 * @returns {Promise<object>} the created `core` instance, for tests/console probing.
 */
export async function mount(win) {
  const doc = win.document;
  const app = await waitForJupyterApp(win);
  await app.restored;

  const ui = buildChrome(doc);
  doc.body.appendChild(ui.root);
  doc.body.appendChild(ui.dialog);

  // -- D5 feature detection (no user-agent sniffing) --------------------------
  const fsaSupported = win.isSecureContext && typeof win.showDirectoryPicker === "function";
  // Reference, never a call -- D6. core.js never names showDirectoryPicker.
  const pickDirectory = fsaSupported ? win.showDirectoryPicker.bind(win) : null;
  const storage = win.navigator && win.navigator.storage ? win.navigator.storage : null;
  const handleStore = createIndexedDbHandleStore();
  const contents = app.serviceManager.contents;
  const flags = win.localStorage;

  let panelOpen = false;
  let choiceRecorded = false;
  let restoreStatus = null; // "restored N, skipped M" after a completed restore

  const core = createPersistence({
    storage,
    pickDirectory,
    handleStore,
    contents,
    flags,
    onChange: (state) => render(state),
  });

  function focusDialog() {
    const focusable = ui.dialog.querySelector("button, [tabindex]");
    (focusable || ui.dialog).focus();
  }

  function openModal() {
    if (ui.dialog.open) return;
    choiceRecorded = false;
    ui.dialog.showModal();
    focusDialog();
  }

  ui.dialog.addEventListener("cancel", (event) => {
    event.preventDefault();
  });
  ui.dialog.addEventListener("close", () => {
    // D4: Escape (and Chromium's non-cancelable SECOND consecutive Escape,
    // via CloseWatcher) must not close the gate without a recorded choice.
    if (!choiceRecorded) {
      ui.dialog.showModal();
      focusDialog();
    }
  });

  ui.chip.addEventListener("click", () => {
    panelOpen = !panelOpen;
    ui.panel.hidden = !panelOpen;
  });

  // core.state.excludedPaths is the same source of truth core.js itself
  // persists (T3's binding-scoped exclusion Map), surfaced as
  // `[{path, reason}]` -- the panel renders the "Not mirrored" list and
  // per-file Replace disk copy buttons straight from it, never reaching
  // around core into handleStore.
  function renderExcludedList(list, state) {
    list.replaceChildren();
    for (const { path, reason } of state.excludedPaths) {
      const item = el(doc, "li");
      item.append(textEl(doc, "span", `${path} -- ${reason}`));
      if (reason === REASON_DIFFERS_ON_DISK && state.permission === "granted") {
        const replaceBtn = actionButton(doc, "replace-disk-copy", "Replace disk copy", () =>
          core.onReplaceDiskCopyClick(path),
        );
        replaceBtn.setAttribute("data-praxis-path", path);
        item.append(" ", replaceBtn);
      }
      list.append(item);
    }
  }

  function buildL1Row(state) {
    if (state.persisted === true) return null; // hidden once L1 is granted (section 3.2)
    const row = el(doc, "div");
    row.append(
      textEl(
        doc,
        "p",
        state.persistSupported ? "Browser may clear this storage." : "Storage persistence: not available in this browser.",
      ),
    );
    if (state.persistSupported) {
      row.append(actionButton(doc, "protect", protectLabel(state), () => core.onProtectClick()));
    }
    return row;
  }

  function buildL2Row(state) {
    const row = el(doc, "div");
    if (!state.fsaSupported) {
      row.append(
        textEl(
          doc,
          "p",
          "Working folders need a Chromium-based browser (Chrome, Edge). Use the file browser's Download to keep copies.",
        ),
      );
      return row;
    }

    const folderBound = state.tier === "L2" || state.tier === "L2-syncing" || state.tier === "L2-paused";
    // D1 rows 48/50/53, section 3.2: "Choose a folder again" replaces
    // Reconnect once the folder itself is gone, OR once a Reconnect attempt
    // has already resolved non-granted -- the pre-attempt paused state still
    // offers Reconnect.
    const unavailable = state.tier === "L2-paused" && (state.pauseReason === "folder-unavailable" || state.reconnectRefused);
    const pausedForPermission = state.tier === "L2-paused" && !unavailable;

    if (!folderBound) {
      row.append(actionButton(doc, "choose-folder", "Choose working folder", () => core.onChooseFolderClick()));
    } else if (unavailable) {
      row.append(actionButton(doc, "choose-folder", "Choose a folder again", () => core.onChooseFolderClick()));
    } else {
      row.append(
        actionButton(doc, "choose-folder", "Choose a different folder", () => core.onChooseFolderClick()),
      );
      if (pausedForPermission) {
        row.append(actionButton(doc, "reconnect", "Reconnect folder", () => core.onReconnectClick()));
      }
      row.append(
        actionButton(doc, "restore", "Restore from folder", () =>
          core.onRestoreClick()?.then((result) => {
            if (!result) return;
            restoreStatus = `restored ${result.restored}, skipped ${result.skipped}`;
            render(core.state);
          }),
        ),
      );
    }

    if (restoreStatus) {
      row.append(textEl(doc, "p", restoreStatus));
    }

    if (state.lastBulkSync) {
      const { written, identical, differs } = state.lastBulkSync;
      row.append(textEl(doc, "p", `written ${written}, identical ${identical}, not mirrored ${differs} (differ on disk)`));
    }

    if (state.excludedCount > 0) {
      const heading = textEl(doc, "p", "Not mirrored:");
      const list = el(doc, "ul");
      list.setAttribute("data-praxis-role", "not-mirrored-list");
      renderExcludedList(list, state);
      row.append(heading, list);
    }

    return row;
  }

  function buildL3Row() {
    const row = el(doc, "div");
    row.append(
      textEl(doc, "p", "Export/import individual files via the file browser's Download and Upload."),
    );
    return row;
  }

  function renderPanelBody(state) {
    ui.panel.replaceChildren();
    const l1 = buildL1Row(state);
    if (l1) ui.panel.append(l1);
    ui.panel.append(buildL2Row(state), buildL3Row());
  }

  function renderModalBody(state) {
    ui.dialog.replaceChildren();
    const text = textEl(
      doc,
      "p",
      "Saved — but only inside this browser. Browsers can clear this storage.",
    );
    text.id = "praxis-persistence-first-save-text";
    ui.dialog.append(text);

    if (state.modal.choose) {
      ui.dialog.append(
        actionButton(doc, "choose-folder", "Choose working folder", () => core.onChooseFolderClick()),
      );
    }
    ui.dialog.append(actionButton(doc, "protect", protectLabel(state), () => core.onProtectClick()));
    ui.dialog.append(
      actionButton(doc, "keep-browser-only", "Keep in this browser only", () => core.onKeepBrowserOnlyClick()),
    );
  }

  function syncModal(state) {
    if (!state.modal.open && ui.dialog.open) {
      // A choice was recorded elsewhere in core (a successful choose, or
      // Keep browser only) -- close the real <dialog> and mark the choice
      // recorded so the `close` listener above does not re-arm it.
      choiceRecorded = true;
      ui.dialog.close();
    } else if (state.modal.open && ui.dialog.open) {
      // Still open (e.g. after Protect, D4: "leaves the dialog open") --
      // keep its buttons in sync with the latest ask-again wording.
      renderModalBody(state);
    }
  }

  function render(state) {
    ui.root.setAttribute("data-praxis-tier", state.tier);
    ui.root.setAttribute("data-praxis-excluded", String(state.excludedCount));
    const { text, warn } = tierLabel(state);
    ui.chip.textContent = text;
    ui.chip.style.color = warn ? "#b45309" : "";
    ui.chip.style.fontWeight = warn ? "600" : "400";
    renderPanelBody(state);
    syncModal(state);
  }

  // -- Lumino wiring (D4, module plan row) -------------------------------
  app.commands.commandExecuted.connect((_sender, evt) => {
    if (!SAVE_COMMAND_IDS.has(evt.id)) return;
    Promise.resolve(evt.result).then(
      () => {
        if (core.handleExplicitSave()) {
          renderModalBody(core.state);
          openModal();
        }
      },
      () => {
        // A rejected/cancelled save opens nothing (D4).
      },
    );
  });

  contents.fileChanged.connect((_sender, change) => {
    if (change.type === "save") {
      core.handleFileSaved(change.newValue.path);
    } else if (change.type === "delete" || change.type === "rename") {
      core.handleFileRemoved(change.oldValue.path);
    }
  });

  await core.init();
  render(core.state);

  return core;
}
