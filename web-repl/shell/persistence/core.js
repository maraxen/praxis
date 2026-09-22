// core.js -- REPL persistence ladder state machine (backlog #4296, spec
// .praxia/docs/specs/260922_repl-persistence-ladder.md).
//
// createPersistence({storage, pickDirectory, handleStore, contents, flags,
// onChange}) is a pure DI state machine: no window/document/navigator
// references anywhere in this file. panel.js (T6) owns all browser wiring
// and DOM; it is the only place `showDirectoryPicker`, `navigator.storage`,
// IndexedDB and `document` are ever named.
//
// This module grew over three fixer tasks against the SAME state machine,
// per the spec's module-plan row and fixer task list (section 4, section 6):
//   T2 -- L1 persist()/persisted(), tier derivation, folder
//         bind/rehydrate-on-load/reconnect, the atomic rebind
//         (handleStore.rebind) + binding-generation bump,
//         onProtectClick / onChooseFolderClick / onReconnectClick.
//   T3 -- the write chain: per-save mirror, persisted pending set + its
//         flush, byte-comparing bulk sync, exclusion + mirrored-paths
//         bookkeeping, restore, plus onRestoreClick, onReplaceDiskCopyClick,
//         handleFileSaved, handleFileRemoved.
//   T4 -- the first-save disclosure gate: handleExplicitSave, the
//         `praxis-repl-persistence-ack` flag, the state.modal model,
//         onKeepBrowserOnlyClick.
// All three are implemented below; T6 (panel.js) is the only remaining
// consumer-side piece (DOM, `contents.fileChanged`/`commandExecuted` wiring).
//
// D6 gesture invariant (enforced statically by T5's
// check_gesture_invariant.py): onProtectClick, onChooseFolderClick and
// onReconnectClick are plain, non-async, NAMED functions matching
// `on[A-Z]\w*Click`, and each calls its gesture API (storage.persist,
// pickDirectory, handle.requestPermission) as its first statement -- at most
// preceded by a synchronous conditional that reads already-cached state
// (e.g. `if (!pickDirectory) return`). Everything asynchronous is chained on
// the promise the gesture call returns, never awaited or `.then`-ed before
// it. `core.js` never names `showDirectoryPicker` itself: it only ever calls
// the injected `pickDirectory`, which panel.js binds to
// `window.showDirectoryPicker.bind(window)` (D6).

import { fileBytesToModel, modelToFileBytes, splitDrivePath } from "./codec.js";

/**
 * @typedef {"L0"|"L1"|"L2"|"L2-syncing"|"L2-paused"} Tier
 * @typedef {"permission"|"folder-unavailable"|"error"} PauseReason
 */

const ACK_KEY = "praxis-repl-persistence-ack";
const REASON_NAME_NOT_ALLOWED = "name not allowed on disk";
const REASON_DIFFERS_ON_DISK = "differs on disk";

/**
 * Persists the four `praxis-repl-persistence` keys (D1): `working-folder`,
 * `pending-paths`, `excluded-paths` and `mirrored-paths`. `rebind` MUST be
 * atomic: it stores the new handle and clears the three binding-scoped sets
 * in ONE transaction, before anything queues a bulk sync (D1, B-2). This is
 * the only mutation core.js ever calls directly on a successful choose; T3's
 * write chain reads/writes the other three keys through `get`/`set`.
 *
 * @typedef {object} HandleStore
 * @property {(key: string) => Promise<any>} get
 * @property {(key: string, value: any) => Promise<void>} set
 * @property {(handle: any) => Promise<void>} rebind
 */

/**
 * Create the persistence state machine.
 *
 * @param {object} options
 * @param {{persist: () => Promise<boolean>, persisted: () => Promise<boolean>}|null} [options.storage]
 *   `navigator.storage`, or `null` when `navigator.storage.persist` is absent
 *   (D5). `persistSupported` in the returned state reflects this.
 * @param {((options: {mode: string}) => Promise<any>)|null} [options.pickDirectory]
 *   Injected `window.showDirectoryPicker.bind(window)`, or `null` when FSA is
 *   unsupported (D5). `fsaSupported` in the returned state reflects this.
 * @param {HandleStore} options.handleStore
 * @param {{get: (path: string, opts?: {content?: boolean}) => Promise<object>, save: (path: string, model: object) => Promise<object>}} [options.contents]
 *   The JupyterLab contents adapter over `jupyterapp.serviceManager.contents`.
 *   `get(path, {content:true})` on a directory returns a shallow
 *   `{name, path, type}[]` in `.content`, the real `IContents.get`
 *   directory-listing contract -- `listDriveFiles` walks it recursively for
 *   bulk sync. `save(path, {type:"directory"})` creates a directory;
 *   `save(path, {type:"file", format, content})` writes a file (restore).
 *   Required once a folder is bound; `null` is only valid pre-bind (L0/L1).
 * @param {{getItem: (key: string) => string|null, setItem: (key: string, value: string) => void}} [options.flags]
 *   The localStorage-shaped flags adapter for `praxis-repl-persistence-ack`
 *   (D4). `null` leaves `state.ack` permanently `null` (the gate is
 *   requested every time, never acknowledged) -- panel.js is expected to
 *   always inject real `localStorage`.
 * @param {(state: object) => void} [options.onChange] Called with a fresh
 *   state snapshot after every state change.
 * @returns {object} `{ state, init, onProtectClick, onChooseFolderClick,
 *   onReconnectClick, onRestoreClick, onReplaceDiskCopyClick,
 *   handleFileSaved, handleFileRemoved, handleExplicitSave,
 *   onKeepBrowserOnlyClick }`
 */
export function createPersistence({
  storage = null,
  pickDirectory = null,
  handleStore,
  contents = null,
  flags = null,
  onChange = null,
} = {}) {
  if (!handleStore || typeof handleStore.rebind !== "function") {
    throw new Error("createPersistence requires a handleStore with get/set/rebind");
  }

  // -- Internal model --------------------------------------------------------
  // Never exposed directly: `state` (below) derives a fresh, frozen snapshot
  // from this on every read, so callers can never mutate internals by
  // reference.
  const model = {
    persisted: false, // last known truth from storage.persisted()/persist()
    askAgain: false, // true once persist() has resolved something other than true
    handle: null, // the bound FSA directory handle (in-memory only; never persisted by core itself -- handleStore owns that)
    folderName: null,
    permission: null, // "granted" | "prompt" | "denied" | null (no folder bound)
    pauseReason: null, // PauseReason | null
    pendingCount: 0,
    excludedCount: 0,
    generation: 0, // bumped on every successful rebind (D1, B-2); write jobs carry this and drop stale ones
    ack: null, // T4: "folder" | "browser-only" | null, mirrors flags[ACK_KEY]
    modalOpen: false, // T4: whether the first-save gate should currently be shown
    lastBulkSync: null, // {written, identical, differs} tallies from the most recent bulk sync, or null before any (spec section 3.3)
    reconnectRefused: false, // true once onReconnectClick has resolved non-granted; cleared on a successful choose/reconnect/rebind
  };

  // T3: binding-scoped sets (D1, D7). Kept as real Sets/Maps in memory for
  // O(1) membership checks; `model.pendingCount`/`excludedCount` above stay
  // in sync with their sizes, and every mutation is mirrored into
  // `handleStore`'s three persisted keys via the persist* helpers below.
  let pendingPaths = new Set();
  let excludedPaths = new Map(); // path -> reason
  let mirroredPaths = new Set();
  // T3: paths a restore is currently writing into the drive. `handleFileSaved`
  // suppresses the `fileChanged` echo restore's own `contents.save` produces
  // for these, so restore never re-enters the mirror chain for its own writes.
  const restoringPaths = new Set();
  // T3: the ONE ordered write-chain (D7 "one ordered write path"). Every
  // disk-touching job -- per-save mirror, pending flush, bulk sync, Replace
  // -- runs through `enqueue`, strictly in order. Restore does NOT use this
  // chain: it writes into the drive, never to disk (D7).
  let writeChain = Promise.resolve();

  /** @returns {Tier} */
  function deriveTier() {
    if (model.handle) {
      // A bound folder always wins over the L1 story (D1: "L1 (unless L2 is
      // active)") -- even a paused L2 outranks a granted L1.
      if (model.pauseReason) return "L2-paused";
      if (model.pendingCount > 0) return "L2-syncing";
      return "L2";
    }
    return model.persisted === true ? "L1" : "L0";
  }

  function snapshot() {
    return Object.freeze({
      fsaSupported: pickDirectory !== null,
      persistSupported: storage !== null && typeof storage.persist === "function",
      tier: deriveTier(),
      pauseReason: model.pauseReason,
      persisted: model.persisted,
      askAgain: model.askAgain,
      permission: model.permission,
      folderName: model.folderName,
      pendingCount: model.pendingCount,
      excludedCount: model.excludedCount,
      // The same source of truth core already persists (`excludedPaths`,
      // T3's binding-scoped Map), surfaced as a plain array so panel.js can
      // render the "Not mirrored" list and per-path Replace buttons without
      // reaching around core into handleStore itself.
      excludedPaths: Object.freeze(
        Array.from(excludedPaths, ([path, reason]) => Object.freeze({ path, reason })),
      ),
      generation: model.generation,
      ack: model.ack,
      lastBulkSync: model.lastBulkSync,
      reconnectRefused: model.reconnectRefused,
      modal: Object.freeze({ open: model.modalOpen, choose: pickDirectory !== null }),
    });
  }

  function notify() {
    if (typeof onChange === "function") onChange(snapshot());
  }

  function applyPermissionResult(permission) {
    model.permission = permission;
    model.pauseReason = permission === "granted" ? null : "permission";
  }

  /** Classify an error into a PauseReason (D1, B-9, B-11). Shared by the
   * handle-level rehydrate/reconnect path and T3's write chain, EXCEPT for
   * the per-path `TypeError` "name not allowed" exclusion, which only
   * applies to the actual disk-write step (see `excludeIfNameNotAllowed`) --
   * never here, so a `TypeError` reaching this function (e.g. from
   * `contents.get`, B-9) just pauses like any other unclassified error. */
  function classifyPauseReason(error) {
    if (error && (error.name === "NotFoundError" || error.name === "InvalidStateError")) {
      // D1: the folder itself is gone (deleted/moved), at init OR on write.
      // The panel offers "Choose a folder again", never Reconnect -- a
      // Reconnect here could never succeed.
      return "folder-unavailable";
    }
    if (error && (error.name === "NotAllowedError" || error.name === "SecurityError")) {
      return "permission";
    }
    return "error";
  }

  function applyHandleError(error) {
    model.pauseReason = classifyPauseReason(error);
  }

  // -- T3: persisted-set bookkeeping ------------------------------------

  async function persistPending() {
    await handleStore.set("pending-paths", Array.from(pendingPaths));
    model.pendingCount = pendingPaths.size;
  }
  async function addPending(path) {
    if (!pendingPaths.has(path)) {
      pendingPaths.add(path);
      await persistPending();
    }
  }
  async function removePending(path) {
    if (pendingPaths.has(path)) {
      pendingPaths.delete(path);
      await persistPending();
    }
  }
  async function persistExcluded() {
    const obj = {};
    for (const [path, reason] of excludedPaths) obj[path] = reason;
    await handleStore.set("excluded-paths", obj);
    model.excludedCount = excludedPaths.size;
  }
  async function excludePath(path, reason) {
    excludedPaths.set(path, reason);
    await persistExcluded();
  }
  async function unexcludePath(path) {
    if (excludedPaths.delete(path)) {
      await persistExcluded();
    }
  }
  async function persistMirrored() {
    await handleStore.set("mirrored-paths", Array.from(mirroredPaths));
  }
  async function addMirrored(path) {
    if (!mirroredPaths.has(path)) {
      mirroredPaths.add(path);
      await persistMirrored();
    }
  }

  // -- T3: the disk side of the mirror (raw FSA navigation) ---------------

  function bytesEqual(a, b) {
    if (a.length !== b.length) return false;
    for (let i = 0; i < a.length; i += 1) {
      if (a[i] !== b[i]) return false;
    }
    return true;
  }

  async function writeBytesToDisk(rootHandle, path, bytes) {
    const segments = path.split("/");
    const fileName = segments.pop();
    let dir = rootHandle;
    for (const seg of segments) {
      dir = await dir.getDirectoryHandle(seg, { create: true });
    }
    const fileHandle = await dir.getFileHandle(fileName, { create: true });
    const writable = await fileHandle.createWritable();
    try {
      await writable.write(bytes);
      await writable.close();
    } catch (error) {
      try {
        await writable.abort?.();
      } catch {
        /* the original error is what matters */
      }
      throw error;
    }
  }

  async function readBytesFromDisk(rootHandle, path) {
    const segments = path.split("/");
    const fileName = segments.pop();
    let dir = rootHandle;
    for (const seg of segments) {
      dir = await dir.getDirectoryHandle(seg, { create: false });
    }
    const fileHandle = await dir.getFileHandle(fileName, { create: false });
    const file = await fileHandle.getFile();
    return new Uint8Array(await file.arrayBuffer());
  }

  /** The create:false disk-side existence check (D7 "first writes are
   * checked too" / bulk sync). A `NotFoundError`/`InvalidStateError` here
   * means "absent on disk" (benign) -- NOT a folder-unavailable pause, unlike
   * the same error names from an actual create:true write attempt. Any other
   * error propagates for the caller to classify. */
  async function readExistingDiskBytes(handle, path) {
    try {
      return await readBytesFromDisk(handle, path);
    } catch (error) {
      if (error && (error.name === "NotFoundError" || error.name === "InvalidStateError")) {
        return null;
      }
      throw error;
    }
  }

  /**
   * The byte-checked "first write" of `path` under the current binding
   * (D7): read the existing disk copy (if any), and either write + mirror
   * it (absent or identical) or exclude it (differs / name not allowed).
   * Used by both the per-save mirror's first-write path and bulk sync.
   *
   * @returns {Promise<"written"|"identical"|"excluded"|"error">}
   */
  async function writeWithByteCheck(handle, path, bytes) {
    let existing;
    try {
      existing = await readExistingDiskBytes(handle, path);
    } catch (error) {
      if (error && error.name === "TypeError") {
        await excludePath(path, REASON_NAME_NOT_ALLOWED);
        return "excluded";
      }
      model.pauseReason = classifyPauseReason(error);
      return "error";
    }
    if (existing !== null && !bytesEqual(existing, bytes)) {
      await excludePath(path, REASON_DIFFERS_ON_DISK);
      return "excluded";
    }
    try {
      await writeBytesToDisk(handle, path, bytes);
    } catch (error) {
      if (error && error.name === "TypeError") {
        await excludePath(path, REASON_NAME_NOT_ALLOWED);
        return "excluded";
      }
      model.pauseReason = classifyPauseReason(error);
      return "error";
    }
    await addMirrored(path);
    return existing !== null ? "identical" : "written";
  }

  // -- T3: the one ordered write chain (D7) --------------------------------

  function enqueue(jobFn) {
    const job = writeChain.then(() => jobFn());
    // jobFn (every job below) catches all of its own errors internally and
    // never rejects; this `.catch` is a defensive backstop only, so one
    // misbehaving job can never wedge the chain for everything queued after it.
    writeChain = job.catch(() => {});
    return job;
  }

  /** The mirror write for one path: per-save mirror AND pending-flush drain
   * both funnel through this (D1, D7). Drops silently if `generation` is
   * stale (B-2) or the folder isn't bound. Skips (no-op) excluded paths --
   * the flush and the per-save mirror both skip them (D7); `onReplaceDiskCopyClick`
   * bypasses this function entirely via `performReplace`. */
  async function performMirrorWrite(path, generation) {
    if (generation !== model.generation) return; // stale binding dropped (D1, B-2)
    const handle = model.handle;
    if (!handle) return;

    if (excludedPaths.has(path)) {
      await removePending(path); // defensive: excluded paths never stay pending
      notify();
      return;
    }
    if (model.permission !== "granted") {
      await addPending(path);
      notify();
      return;
    }

    let contentModel;
    try {
      contentModel = await contents.get(path, { content: true });
    } catch (error) {
      // B-9: a TypeError here (or anything else) from `contents.get` is NOT
      // a "name not allowed" exclusion -- that classification is reserved
      // for the FSA handle's own write methods. It just pauses.
      model.pauseReason = classifyPauseReason(error);
      await addPending(path);
      notify();
      return;
    }

    let bytes;
    try {
      bytes = modelToFileBytes(contentModel);
    } catch {
      // Not a file we know how to mirror (e.g. a directory model) -- nothing
      // to write; don't leave it stuck pending forever.
      await removePending(path);
      notify();
      return;
    }

    if (!mirroredPaths.has(path)) {
      const result = await writeWithByteCheck(handle, path, bytes);
      if (result === "excluded") {
        await removePending(path);
      } else if (result === "error") {
        await addPending(path);
      } else {
        await removePending(path);
      }
      notify();
      return;
    }

    // Already our own mirror copy -- overwrite directly, no byte check.
    try {
      await writeBytesToDisk(handle, path, bytes);
    } catch (error) {
      if (error && error.name === "TypeError") {
        await excludePath(path, REASON_NAME_NOT_ALLOWED);
        await removePending(path);
        notify();
        return;
      }
      model.pauseReason = classifyPauseReason(error);
      await addPending(path);
      notify();
      return;
    }
    await addMirrored(path);
    await removePending(path);
    notify();
  }

  /** D1, B-1: flush trigger is "handle bound AND permission granted AND
   * pending set non-empty", never a tier transition. Fire-and-forget from
   * every call site (init-time rehydrate, Reconnect): `deriveTier()` already
   * reports "L2-syncing" while `pendingPaths` is non-empty, so callers don't
   * need to await this to show correct state; they just need to have
   * triggered it. */
  function scheduleFlush() {
    const generation = model.generation;
    const jobs = Array.from(pendingPaths).map((path) => enqueue(() => performMirrorWrite(path, generation)));
    return Promise.all(jobs);
  }

  /** @returns {Promise<"written"|"identical"|"excluded"|"error"|null>} `null`
   * when there was nothing to do (stale generation, already mirrored/excluded,
   * or an unreadable/unmirrorable drive file) -- these don't count toward the
   * section 3.3 tally, only actual attempted writes do. */
  async function bulkSyncOne(handle, path, generation) {
    if (generation !== model.generation) return null;
    if (mirroredPaths.has(path) || excludedPaths.has(path)) return null;
    let contentModel;
    try {
      contentModel = await contents.get(path, { content: true });
    } catch {
      return null; // best-effort: an unreadable drive file is retried on its next save
    }
    let bytes;
    try {
      bytes = modelToFileBytes(contentModel);
    } catch {
      return null;
    }
    const result = await writeWithByteCheck(handle, path, bytes);
    notify();
    return result;
  }

  function isDotPath(path) {
    return path.split("/").some((seg) => seg.startsWith("."));
  }

  /** Recursively list every FILE path in the drive, skipping dot-prefixed
   * segments (D1, D7), via nested `contents.get(path, {content:true})` calls
   * -- the real `IContents.get` directory-listing contract (module row 4). */
  async function listDriveFiles(prefix) {
    const results = [];
    let dirModel;
    try {
      dirModel = await contents.get(prefix, { content: true });
    } catch {
      return results;
    }
    const children = Array.isArray(dirModel.content) ? dirModel.content : [];
    for (const child of children) {
      if (child.name && child.name.startsWith(".")) continue;
      if (child.type === "directory") {
        results.push(...(await listDriveFiles(child.path)));
      } else {
        results.push(child.path);
      }
    }
    return results;
  }

  /** Byte-comparing bulk sync on choose (D1 section 3.3, D7). Queued with
   * the binding generation captured at call time so a later rebind
   * supersedes it (D1, B-2). Runs through the same write chain as
   * per-save/flush jobs, so it can never interleave out of order with them. */
  function scheduleBulkSync(handle, generation) {
    return enqueue(() => performBulkSync(handle, generation));
  }

  async function performBulkSync(handle, generation) {
    if (generation !== model.generation) return;
    if (model.permission !== "granted") return; // nothing to sync without permission yet
    const files = await listDriveFiles("");
    // Section 3.3 tally: "written N, identical M, not mirrored K (differ on
    // disk)". Only paths this bulk sync actually attempted (not already
    // mirrored/excluded, not dot-prefixed) count.
    let written = 0;
    let identical = 0;
    let differs = 0;
    for (const path of files) {
      if (generation !== model.generation) return; // superseded mid-walk
      if (isDotPath(path)) continue;
      const result = await bulkSyncOne(handle, path, generation);
      if (result === "written") written += 1;
      else if (result === "identical") identical += 1;
      else if (result === "excluded") differs += 1;
    }
    model.lastBulkSync = { written, identical, differs };
    notify();
  }

  /** T4, D4, B-3: every successful choose -- the modal's, the panel's, and
   * "Choose a folder again" -- funnels through `applyChoose`, so this is the
   * single place that needs to set the ack. It also resolves an open gate:
   * "Choosing a folder successfully resolves the gate" (D4). */
  function recordSuccessfulChoose() {
    model.ack = "folder";
    writeAck("folder");
    model.modalOpen = false;
  }

  function readAck() {
    if (!flags || typeof flags.getItem !== "function") return null;
    const value = flags.getItem(ACK_KEY);
    return value === "folder" || value === "browser-only" ? value : null;
  }
  function writeAck(value) {
    if (!flags || typeof flags.setItem !== "function") return;
    flags.setItem(ACK_KEY, value);
  }

  async function rehydrateFolder() {
    const handle = await handleStore.get("working-folder");
    if (!handle) return;
    model.handle = handle;
    model.folderName = handle.name ?? null;

    try {
      const permission = await handle.queryPermission({ mode: "readwrite" });
      applyPermissionResult(permission);
    } catch (error) {
      applyHandleError(error);
    }

    const pending = await handleStore.get("pending-paths");
    pendingPaths = new Set(Array.isArray(pending) ? pending : []);
    model.pendingCount = pendingPaths.size;

    const excluded = await handleStore.get("excluded-paths");
    excludedPaths = new Map(excluded ? Object.entries(excluded) : []);
    model.excludedCount = excludedPaths.size;

    const mirrored = await handleStore.get("mirrored-paths");
    mirroredPaths = new Set(Array.isArray(mirrored) ? mirrored : []);

    if (model.permission === "granted" && pendingPaths.size > 0) {
      // D1, B-1: the flush trigger is this condition, never a tier
      // transition (L2 requires an empty pending set, so a trigger on "tier
      // becomes L2" could never fire).
      scheduleFlush();
    }
  }

  /** Read the browser's current L1 answer. A missing `storage` (or one
   * without `.persisted`) leaves `persisted` at its default `false`, which
   * `snapshot()` reports as `persistSupported: false` for the panel's
   * "not available" copy (D5, AC-1). */
  async function refreshPersisted() {
    if (!storage || typeof storage.persisted !== "function") return;
    const result = await storage.persisted();
    model.persisted = result === true;
  }

  /** Rehydrate everything from IndexedDB / re-check permission (D1 "Reload"
   * row, section 3.4). Must run before anything else reads `state`. */
  async function init() {
    model.ack = readAck(); // T4
    await refreshPersisted();
    await rehydrateFolder();
    notify();
  }

  /** D4 button 2 / D1 L1 row. Plain, non-async: `storage.persist()` is the
   * first statement, satisfying D6. */
  function onProtectClick() {
    if (!storage || typeof storage.persist !== "function") return undefined;
    const result = storage.persist(); // gesture call
    return result.then((granted) => {
      model.persisted = granted === true;
      model.askAgain = granted !== true;
      notify();
    });
  }

  async function applyChoose(handle) {
    // D1 / B-2: store the handle and clear the three binding-scoped sets in
    // ONE transaction, before anything else -- so nothing learned about the
    // old binding can leak into the new one.
    await handleStore.rebind(handle);
    model.generation += 1; // binding-generation bump (D1, B-2)
    model.handle = handle;
    model.folderName = handle.name ?? null;
    // The store's three binding-scoped sets were just cleared by `rebind`
    // (D1, B-2) -- mirror that in the in-memory Sets too, so nothing from
    // the OLD binding (pending, excluded or mirrored) can leak into the new
    // one.
    pendingPaths = new Set();
    excludedPaths = new Map();
    mirroredPaths = new Set();
    model.pendingCount = 0;
    model.excludedCount = 0;
    model.lastBulkSync = null; // this binding hasn't run a bulk sync yet
    model.reconnectRefused = false; // a fresh binding has no Reconnect history

    try {
      const permission = await handle.queryPermission({ mode: "readwrite" });
      applyPermissionResult(permission);
    } catch (error) {
      applyHandleError(error);
    }

    // D4/B-3: "any successful choose" sets the ack to "folder". T4 fills
    // this in; every choose path (panel, modal, "Choose a folder again")
    // reaches it through here, so T4 needs no other call site.
    recordSuccessfulChoose();

    // D1/D7: the bulk sync supersedes any flush queued under the previous
    // generation. T3 fills this in.
    scheduleBulkSync(handle, model.generation);

    notify();
  }

  /** Panel's "Choose working folder" / "Choose a different folder" / "Choose
   * a folder again". Plain, non-async: `pickDirectory(...)` is the first
   * statement, satisfying D6. A cancelled or failed picker call (e.g. the
   * user dismissed the native dialog) leaves state untouched -- it is not a
   * failure state, just a no-op. */
  function onChooseFolderClick() {
    if (!pickDirectory) return undefined;
    const picked = pickDirectory({ mode: "readwrite" }); // gesture call
    return picked.then(
      (handle) => applyChoose(handle),
      () => {
        // Picker cancelled/dismissed (e.g. AbortError) -- no state change.
      },
    );
  }

  /** Panel's "Reconnect folder". Plain, non-async: the cached-state
   * conditional `if (!model.handle) return` is the only thing allowed before
   * `requestPermission(...)`, which is the gesture call itself (D6, the same
   * shape as `if (!pickDirectory) return`). */
  function onReconnectClick() {
    if (!model.handle) return undefined;
    const request = model.handle.requestPermission({ mode: "readwrite" }); // gesture call
    return request.then(
      (permission) => {
        applyPermissionResult(permission);
        // D1 row 50: a Reconnect that resolves non-granted stays paused and
        // switches the panel from "Reconnect folder" to "Choose a folder
        // again" -- distinct from the pre-attempt L2-paused state, which
        // still offers Reconnect (D1 row 48).
        model.reconnectRefused = permission !== "granted";
        if (permission === "granted" && model.pendingCount > 0) {
          scheduleFlush();
        }
        notify();
      },
      (error) => {
        applyHandleError(error);
        notify();
      },
    );
  }

  // -- T3: save/remove entry points, Replace, restore -----------------------

  /** Routed here by panel.js from `contents.fileChanged` type "save"
   * (explicit save AND autosave alike -- G2). Not a gesture call: the actual
   * disk write happens later, off the write chain, never inside a click
   * handler. Suppressed for paths an active restore is currently writing
   * into the drive, so restore's own `contents.save` never re-enters the
   * mirror chain for itself (D7). Returns the enqueued job's promise so
   * callers (including tests) can await completion; the mirror chain itself
   * is fire-and-forget from every OTHER call site. */
  function handleFileSaved(path) {
    try {
      splitDrivePath(path); // reject ""/"."/".."/invalid segments
    } catch {
      return undefined;
    }
    if (restoringPaths.has(path)) return undefined;
    if (!model.handle) return undefined; // nothing bound to mirror into
    const generation = model.generation;
    return enqueue(() => performMirrorWrite(path, generation));
  }

  /** Routed here by panel.js from `contents.fileChanged` type "delete" or
   * "rename" (`oldValue.path` in both cases). Drops the path from
   * `mirrored-paths` (D7): the disk copy is never deleted/renamed itself
   * (non-goal), so a later create at the same path goes through the
   * first-write byte check again instead of blindly overwriting a stale
   * disk copy. */
  async function handleFileRemoved(path) {
    if (mirroredPaths.has(path)) {
      mirroredPaths.delete(path);
      await persistMirrored();
      notify();
    }
  }

  /** Panel's per-file "Replace disk copy", for an excluded "differs on
   * disk" path (D7). Not gesture-bound (D6): shown only while permission is
   * already granted, so it needs no `requestPermission` call of its own. */
  function onReplaceDiskCopyClick(path) {
    if (!model.handle) return undefined;
    const generation = model.generation;
    return enqueue(() => performReplace(path, generation));
  }

  async function performReplace(path, generation) {
    if (generation !== model.generation) return;
    if (!excludedPaths.has(path)) return; // nothing to replace
    const handle = model.handle;

    let contentModel;
    try {
      contentModel = await contents.get(path, { content: true });
    } catch (error) {
      model.pauseReason = classifyPauseReason(error);
      notify();
      return;
    }
    let bytes;
    try {
      bytes = modelToFileBytes(contentModel);
    } catch {
      return;
    }
    try {
      await writeBytesToDisk(handle, path, bytes);
    } catch (error) {
      if (error && error.name === "TypeError") {
        // Still not writable under this name -- stays excluded, same reason.
        notify();
        return;
      }
      model.pauseReason = classifyPauseReason(error);
      notify();
      return;
    }
    await unexcludePath(path);
    await addMirrored(path);
    notify();
  }

  async function ensureDriveDirs(path) {
    const segments = path.split("/");
    segments.pop(); // filename
    let acc = "";
    for (const seg of segments) {
      acc = acc ? `${acc}/${seg}` : seg;
      await contents.save(acc, { type: "directory" });
    }
  }

  /** Recursively list every FILE path in the bound FSA folder, skipping
   * dot-prefixed segments (D1, D7). */
  async function listFolderFiles(handle, prefix) {
    const results = [];
    for await (const child of handle.values()) {
      if (child.name.startsWith(".")) continue;
      const path = prefix ? `${prefix}/${child.name}` : child.name;
      if (child.kind === "directory") {
        results.push(...(await listFolderFiles(child, path)));
      } else {
        results.push(path);
      }
    }
    return results;
  }

  /** Restore writes into the DRIVE, never to disk -- it does NOT use the
   * write chain (D7). Every folder file absent from the drive is written,
   * with parent directories created first; drive files are never
   * overwritten. Restored paths are added to `mirrored-paths`, since the
   * disk copy is by definition equal. */
  async function runRestore() {
    const handle = model.handle;
    const generation = model.generation;
    let entries;
    try {
      entries = await listFolderFiles(handle, "");
    } catch (error) {
      applyHandleError(error);
      notify();
      return { restored: 0, skipped: 0 };
    }

    let restored = 0;
    let skipped = 0;
    for (const path of entries) {
      if (generation !== model.generation) break; // a later rebind supersedes this restore
      if (isDotPath(path)) {
        skipped += 1;
        continue;
      }
      let existsInDrive = true;
      try {
        await contents.get(path, { content: false });
      } catch {
        existsInDrive = false;
      }
      if (existsInDrive) {
        skipped += 1;
        continue;
      }

      restoringPaths.add(path);
      try {
        await ensureDriveDirs(path);
        const bytes = await readBytesFromDisk(handle, path);
        const fileModel = fileBytesToModel(path, bytes);
        await contents.save(path, fileModel);
        mirroredPaths.add(path); // restored == disk copy, by definition (D7)
        restored += 1;
      } finally {
        restoringPaths.delete(path);
      }
    }
    await persistMirrored();
    notify();
    return { restored, skipped };
  }

  /** Panel's "Restore from folder". If the cached permission is not
   * "granted", this calls `requestPermission` first -- ITS gesture-bound
   * call (D6, AC-2's `onRestoreClick` case). When already granted, there is
   * no gesture call to make at all: restore touches only `contents` and the
   * FSA handle's non-gesture read/enumerate methods, so the plain
   * conditional shape (cached-state check, then either the gesture call or
   * the non-gesture async work) still satisfies D6. */
  function onRestoreClick() {
    if (!model.handle) return undefined;
    if (model.permission !== "granted") {
      const request = model.handle.requestPermission({ mode: "readwrite" }); // gesture call
      return request.then(
        (permission) => {
          applyPermissionResult(permission);
          notify();
          if (permission !== "granted") return undefined;
          return runRestore();
        },
        (error) => {
          applyHandleError(error);
          notify();
        },
      );
    }
    return runRestore();
  }

  // -- T4: first-save disclosure gate (D4) -----------------------------

  /** Called after an explicit save's `evt.result` resolves (panel.js, D4).
   * Requests the modal iff no working folder is connected (tier is not L2)
   * AND the ack is unset. `handleFileSaved` (autosave) never calls this. */
  function handleExplicitSave() {
    const shouldOpen = deriveTier() !== "L2" && model.ack == null;
    if (shouldOpen) {
      model.modalOpen = true;
      notify();
    }
    return shouldOpen;
  }

  /** Modal button 3, "Keep in this browser only" (D4). */
  function onKeepBrowserOnlyClick() {
    model.ack = "browser-only";
    writeAck("browser-only");
    model.modalOpen = false;
    notify();
  }

  return {
    get state() {
      return snapshot();
    },
    init,
    onProtectClick,
    onChooseFolderClick,
    onReconnectClick,

    // T3
    onRestoreClick,
    onReplaceDiskCopyClick,
    handleFileSaved,
    handleFileRemoved,

    // T4
    handleExplicitSave,
    onKeepBrowserOnlyClick,
  };
}
