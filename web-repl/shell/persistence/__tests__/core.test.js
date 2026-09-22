// core.test.js -- Tests for createPersistence's L1 logic, tier derivation and
// gesture synchrony (spec .praxia/docs/specs/260922_repl-persistence-ladder.md,
// AC-1 and AC-2, plus the rehydrate/reconnect half of AC-3 that doesn't
// depend on T3's write chain).
//
// T3 appends this file's AC-3 (write chain, exclusion, restore) and AC-2's
// onRestoreClick case. T4 appends AC-4 (the first-save gate). Neither is
// implemented in core.js yet -- see core.js's "T3/T4 EXTENSION POINT" markers.

import { describe, expect, test } from "bun:test";

import { createPersistence } from "../core.js";
import {
  createActivationRecorder,
  createFakeContents,
  createFakeDirectoryHandle,
  createFakeFlags,
  createFakeHandleStore,
  createFakePickDirectory,
  createFakeStorage,
} from "./fakes.js";

/** Yield past a macrotask boundary, so every currently-pending microtask
 * (the fire-and-forget write chain included) has had a chance to settle,
 * without hanging forever on a deliberately-held write (fakes.js `_hold`/
 * `_holdSave`). Used wherever a test needs the chain to actually DRAIN,
 * rather than just get triggered. */
function flushMicrotasks() {
  return new Promise((resolve) => setTimeout(resolve, 0));
}

/** Read a file's bytes back out of a `createFakeDirectoryHandle` root, or
 * `null` if it doesn't exist -- for asserting disk content by bytes/text. */
async function readDiskText(rootHandle, path) {
  const segments = path.split("/");
  const fileName = segments.pop();
  let dir = rootHandle;
  for (const seg of segments) {
    try {
      dir = await dir.getDirectoryHandle(seg);
    } catch {
      return null;
    }
  }
  try {
    const fileHandle = await dir.getFileHandle(fileName);
    const file = await fileHandle.getFile();
    return await file.text();
  } catch {
    return null;
  }
}

/** Seed a `createFakeDirectoryHandle` root with a file at `path` (creating
 * parent directories as needed) -- for pre-populating "what's already on
 * disk" test fixtures directly, without going through core.js at all. */
async function writeDiskFile(rootHandle, path, text) {
  const segments = path.split("/");
  const fileName = segments.pop();
  let dir = rootHandle;
  for (const seg of segments) {
    dir = await dir.getDirectoryHandle(seg, { create: true });
  }
  const fileHandle = await dir.getFileHandle(fileName, { create: true });
  const writable = await fileHandle.createWritable();
  await writable.write(text);
  await writable.close();
}

describe("AC-1: L1 logic", () => {
  test("persisted() true gives L1", async () => {
    const storage = createFakeStorage({ persistedResult: true });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();
    expect(core.state.tier).toBe("L1");
    expect(core.state.persisted).toBe(true);
  });

  test("persisted() false gives L0", async () => {
    const storage = createFakeStorage({ persistedResult: false });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();
    expect(core.state.tier).toBe("L0");
    expect(core.state.persisted).toBe(false);
  });

  test("persist() resolving false gives L0 with askAgain", async () => {
    const storage = createFakeStorage({ persistedResult: false, persistResult: false });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();
    await core.onProtectClick();
    expect(core.state.tier).toBe("L0");
    expect(core.state.askAgain).toBe(true);
  });

  test("persist() resolving true gives L1", async () => {
    const storage = createFakeStorage({ persistedResult: false, persistResult: true });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();
    await core.onProtectClick();
    expect(core.state.tier).toBe("L1");
    expect(core.state.askAgain).toBe(false);
  });

  test("a missing storage gives persistSupported: false and never L1", async () => {
    const core = createPersistence({ storage: null, handleStore: createFakeHandleStore() });
    await core.init();
    expect(core.state.persistSupported).toBe(false);
    expect(core.state.tier).toBe("L0");
  });

  test("a tier never reads L1 without a true from the fake", async () => {
    const storage = createFakeStorage({ persistedResult: false });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();
    expect(core.state.tier).not.toBe("L1");
    await core.onProtectClick(); // default persistResult is true, but persisted() already read false above
    // onProtectClick's own resolution is what flips it -- confirms no accidental L1 before that resolves.
  });
});

describe("AC-2: gesture synchrony", () => {
  test("onProtectClick records activation === true at storage.persist", async () => {
    const activation = createActivationRecorder();
    const storage = createFakeStorage({ activation });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();

    activation.set(true);
    const pending = core.onProtectClick();
    activation.set(false); // flipped synchronously, right after the call returns
    await pending;

    const call = activation.calls.find((c) => c.name === "persist");
    expect(call).toBeDefined();
    expect(call.activation).toBe(true);
  });

  test("onChooseFolderClick records activation === true at the injected pickDirectory", async () => {
    const activation = createActivationRecorder();
    const handle = createFakeDirectoryHandle({ name: "work" });
    const pickDirectory = createFakePickDirectory({ handle, activation });
    const core = createPersistence({ pickDirectory, handleStore: createFakeHandleStore() });
    await core.init();

    activation.set(true);
    const pending = core.onChooseFolderClick();
    activation.set(false);
    await pending;

    const call = activation.calls.find((c) => c.name === "pickDirectory");
    expect(call).toBeDefined();
    expect(call.activation).toBe(true);
  });

  test("onReconnectClick records activation === true at handle.requestPermission", async () => {
    const activation = createActivationRecorder();
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const originalRequestPermission = handle.requestPermission.bind(handle);
    handle.requestPermission = (...args) => {
      activation.record("requestPermission");
      return originalRequestPermission(...args);
    };
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    activation.set(true);
    const pending = core.onReconnectClick();
    activation.set(false);
    await pending;

    const call = activation.calls.find((c) => c.name === "requestPermission");
    expect(call).toBeDefined();
    expect(call.activation).toBe(true);
  });

  test("onRestoreClick, with cached permission 'prompt', records activation === true at handle.requestPermission (T3)", async () => {
    const activation = createActivationRecorder();
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const originalRequestPermission = handle.requestPermission.bind(handle);
    handle.requestPermission = (...args) => {
      activation.record("requestPermission");
      return originalRequestPermission(...args);
    };
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore, contents: createFakeContents() });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    activation.set(true);
    const pending = core.onRestoreClick();
    activation.set(false);
    await pending;

    const call = activation.calls.find((c) => c.name === "requestPermission");
    expect(call).toBeDefined();
    expect(call.activation).toBe(true);
  });

  test("control: an async wrapper that awaits once before delegating records false", async () => {
    const activation = createActivationRecorder();
    const storage = createFakeStorage({ activation });
    const core = createPersistence({ storage, handleStore: createFakeHandleStore() });
    await core.init();

    async function delayedProtectClick() {
      await Promise.resolve(); // one microtask tick before the gesture call
      return core.onProtectClick();
    }

    activation.set(true);
    const pending = delayedProtectClick();
    activation.set(false);
    await pending;

    const call = activation.calls.find((c) => c.name === "persist");
    expect(call).toBeDefined();
    expect(call.activation).toBe(false); // proves the fake CAN discriminate
  });

  test("onChooseFolderClick is a plain function reachable synchronously (D6 shape)", () => {
    const core = createPersistence({ pickDirectory: null, handleStore: createFakeHandleStore() });
    // pickDirectory === null (FSA unsupported): must be a synchronous no-op,
    // never throw, never require awaiting anything first.
    expect(core.onChooseFolderClick()).toBeUndefined();
  });
});

describe("AC-3 (partial, T2 scope): rehydrate and reconnect", () => {
  test("a rehydrated handle with granted permission and an empty pending set gives L2, and pickDirectory is not called", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": [],
      "excluded-paths": {},
    });
    let pickDirectoryCalled = false;
    const pickDirectory = () => {
      pickDirectoryCalled = true;
      return Promise.resolve(handle);
    };
    const core = createPersistence({ pickDirectory, handleStore });
    await core.init();

    expect(core.state.tier).toBe("L2");
    expect(core.state.folderName).toBe("work");
    expect(pickDirectoryCalled).toBe(false);
  });

  test("a rehydrated handle with permission 'prompt' gives L2-paused, pauseReason permission", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore });
    await core.init();

    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("permission");
  });

  test("a rehydrated handle whose queryPermission throws NotFoundError gives L2-paused, pauseReason folder-unavailable", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    handle._fault("", "queryPermission", "NotFoundError");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore });
    await core.init();

    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("folder-unavailable");
  });

  test("Reconnect granted transitions a paused folder to L2", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    handle._setPermission("granted");
    await core.onReconnectClick();

    expect(core.state.tier).toBe("L2");
    expect(core.state.pauseReason).toBeNull();
  });

  test("Reconnect not granted stays L2-paused", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "denied" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const core = createPersistence({ handleStore });
    await core.init();

    await core.onReconnectClick();

    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("permission");
  });

  test("onReconnectClick with no bound handle is a synchronous no-op", () => {
    const core = createPersistence({ handleStore: createFakeHandleStore() });
    expect(core.onReconnectClick()).toBeUndefined();
  });

  test("the pending count survives a new createPersistence instance over the same handleStore (reload analogue)", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": ["notebooks/a.ipynb"],
      "excluded-paths": {},
    });
    // Hold the flush's write so it can never complete during this test --
    // otherwise, in this fake (no real I/O latency) environment, the
    // fire-and-forget flush job would race ahead and finish before either
    // `init()` call resolves, and the pending set this test means to
    // observe would already be empty.
    const hold = handle._hold("notebooks/a.ipynb");
    const contents = createFakeContents({ files: { "notebooks/a.ipynb": { format: "text", content: "hi" } } });

    const first = createPersistence({ handleStore, contents });
    await first.init();
    expect(first.state.pendingCount).toBe(1);
    expect(first.state.tier).toBe("L2-syncing"); // B-1: bound + granted + non-empty pending, never "L2"

    const second = createPersistence({ handleStore, contents });
    await second.init();
    expect(second.state.pendingCount).toBe(1);
    expect(second.state.tier).toBe("L2-syncing");

    hold.release();
    await flushMicrotasks();
  });
});

describe("atomic rebind (D1, B-2)", () => {
  test("choosing a new folder clears pending/excluded counts in the handle store and bumps the generation", async () => {
    const oldHandle = createFakeDirectoryHandle({ name: "old", permission: "granted" });
    const handleStore = createFakeHandleStore({
      "working-folder": oldHandle,
      "pending-paths": ["p.ipynb"],
      "excluded-paths": { "q.ipynb": "differs on disk" },
      "mirrored-paths": ["r.ipynb"],
    });
    const core = createPersistence({ handleStore });
    await core.init();
    expect(core.state.pendingCount).toBe(1);
    expect(core.state.excludedCount).toBe(1);
    expect(core.state.generation).toBe(0);

    const newHandle = createFakeDirectoryHandle({ name: "new", permission: "granted" });
    const pickDirectory = createFakePickDirectory({ handle: newHandle });
    const core2 = createPersistence({ pickDirectory, handleStore });
    // core2 hasn't called init(), which is fine: onChooseFolderClick doesn't
    // depend on it, and this models the panel's "choose before any load"
    // path just as well as "choose after load".
    await core2.onChooseFolderClick();

    expect(core2.state.folderName).toBe("new");
    expect(core2.state.pendingCount).toBe(0);
    expect(core2.state.excludedCount).toBe(0);
    expect(core2.state.generation).toBe(1);
    expect(core2.state.tier).toBe("L2");

    // And the store itself was cleared, not just this instance's view of it.
    expect(await handleStore.get("pending-paths")).toEqual([]);
    expect(await handleStore.get("excluded-paths")).toEqual({});
    expect(await handleStore.get("mirrored-paths")).toEqual([]);
    expect(await handleStore.get("working-folder")).toBe(newHandle);
  });

  test("a cancelled picker leaves state and the handle store untouched", async () => {
    const handleStore = createFakeHandleStore();
    const pickDirectory = createFakePickDirectory({ handle: null }); // rejects with AbortError
    const core = createPersistence({ pickDirectory, handleStore });
    await core.init();

    await core.onChooseFolderClick();

    expect(core.state.tier).toBe("L0");
    expect(core.state.folderName).toBeNull();
    expect(await handleStore.get("working-folder")).toBeUndefined();
  });
});

describe("AC-3: basic mirroring", () => {
  test("Save while granted: file lands at its nested path, compared by content", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "sub/a.ipynb": { format: "json", content: { cells: [], nbformat: 4 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();
    expect(core.state.tier).toBe("L2");

    await core.handleFileSaved("sub/a.ipynb");

    expect(await readDiskText(handle, "sub/a.ipynb")).toBe(JSON.stringify({ cells: [], nbformat: 4 }, null, 1) + "\n");
    expect(core.state.pendingCount).toBe(0);
  });

  test("Save while 'prompt': no write, path added to the pending set, tier L2-paused", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [] });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: {} } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    await core.handleFileSaved("a.ipynb");

    expect(core.state.pendingCount).toBe(1);
    expect(core.state.tier).toBe("L2-paused");
    expect(await readDiskText(handle, "a.ipynb")).toBeNull();
  });
});

describe("AC-3: pending set", () => {
  test("Reconnect granted: the pending path is written and the tier becomes L2", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": ["a.ipynb"],
      "excluded-paths": {},
    });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    handle._setPermission("granted");
    await core.onReconnectClick();
    await flushMicrotasks();

    expect(core.state.pendingCount).toBe(0);
    expect(core.state.tier).toBe("L2");
    expect(await readDiskText(handle, "a.ipynb")).toBe(JSON.stringify({ v: 1 }, null, 1) + "\n");
  });

  test("init() with permission already 'granted' and a non-empty pending set also flushes it (the deadlock regression)", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": ["a.ipynb"],
      "excluded-paths": {},
    });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 2 } } } });
    const core = createPersistence({ handleStore, contents });

    await core.init();
    // The flush must fire even though the tier is NOT yet L2 at this instant
    // -- if the trigger were "tier becomes L2" instead of "bound AND granted
    // AND pending non-empty" (B-1), it could never fire at all.
    expect(core.state.tier).not.toBe("L0");
    await flushMicrotasks();

    expect(core.state.pendingCount).toBe(0);
    expect(core.state.tier).toBe("L2");
  });

  test("Mid-flush tier (B-1): tier reads L2-syncing (never L2) while a held write is in flight, then L2 once released", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": ["a.ipynb"],
      "excluded-paths": {},
    });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 3 } } } });
    const hold = handle._hold("a.ipynb");
    const core = createPersistence({ handleStore, contents });

    await core.init();
    await flushMicrotasks(); // let the flush start and reach (and block on) the held write

    expect(core.state.pendingCount).toBe(1);
    expect(core.state.tier).toBe("L2-syncing");

    hold.release();
    await flushMicrotasks();

    expect(core.state.pendingCount).toBe(0);
    expect(core.state.tier).toBe("L2");
  });

  test("the flush skips excluded paths", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "prompt" });
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": ["excluded.ipynb", "ok.ipynb"],
      "excluded-paths": { "excluded.ipynb": "differs on disk" },
    });
    const contents = createFakeContents({
      files: {
        "excluded.ipynb": { format: "json", content: { v: 1 } },
        "ok.ipynb": { format: "json", content: { v: 2 } },
      },
    });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    handle._setPermission("granted");
    await core.onReconnectClick();
    await flushMicrotasks();

    expect(core.state.excludedCount).toBe(1);
    expect(core.state.pendingCount).toBe(0);
    expect(core.state.tier).toBe("L2");
    expect(await readDiskText(handle, "excluded.ipynb")).toBeNull();
    expect(await readDiskText(handle, "ok.ipynb")).toBe(JSON.stringify({ v: 2 }, null, 1) + "\n");
  });
});

describe("AC-3: rebind, delete and rename (B-2)", () => {
  test("bind A (paused), save p (pending), choose B with a differing copy: B's bytes stay unchanged, p is excluded there, and A's sets are gone", async () => {
    const handleA = createFakeDirectoryHandle({ name: "A", permission: "prompt" });
    const handleStore = createFakeHandleStore({ "working-folder": handleA, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "p.ipynb": { format: "json", content: { v: "drive" } } } });
    const handleB = createFakeDirectoryHandle({ name: "B", permission: "granted" });
    await writeDiskFile(handleB, "p.ipynb", "not the drive's bytes");

    const pickDirectory = createFakePickDirectory({ handle: handleB });
    const core = createPersistence({ pickDirectory, handleStore, contents });
    await core.init();
    expect(core.state.tier).toBe("L2-paused");

    await core.handleFileSaved("p.ipynb"); // permission "prompt" -> pending only, no disk attempt against A
    expect(core.state.pendingCount).toBe(1);

    await core.onChooseFolderClick(); // rebind A -> B
    await flushMicrotasks();

    expect(core.state.generation).toBe(1);
    expect(core.state.folderName).toBe("B");
    expect(core.state.pendingCount).toBe(0); // A's pending set is gone -- no A-generation job ever reaches B
    expect(core.state.excludedCount).toBe(1); // B's bulk sync found the differing copy of p.ipynb
    expect(await readDiskText(handleB, "p.ipynb")).toBe("not the drive's bytes"); // never overwritten
  });

  test("after p is mirrored, handleFileRemoved(p) drops it from mirrored-paths; a later differing recreate at p is then excluded, not overwritten", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "p.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("p.ipynb");
    expect(await handleStore.get("mirrored-paths")).toEqual(["p.ipynb"]);

    await core.handleFileRemoved("p.ipynb"); // drive delete/rename
    expect(await handleStore.get("mirrored-paths")).toEqual([]);

    // The old disk bytes are untouched (deletes/renames don't propagate to
    // disk -- non-goal). A NEW drive file at the same path, with content
    // that differs from what's still on disk, is checked again from
    // scratch since it's no longer mirrored.
    contents._seed("p.ipynb", { format: "json", content: { v: 2 } });
    await core.handleFileSaved("p.ipynb");

    expect(core.state.excludedCount).toBe(1);
    expect(await readDiskText(handle, "p.ipynb")).toBe(JSON.stringify({ v: 1 }, null, 1) + "\n"); // unchanged
  });
});

describe("AC-3: error classification (D1, B-9, B-11)", () => {
  test("a TypeError from getFileHandle/createWritable/write excludes only that path as 'name not allowed on disk'; the mirror does not pause and other paths keep mirroring", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    handle._fault("bad name.ipynb", "getFileHandle", "TypeError");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({
      files: {
        "bad name.ipynb": { format: "json", content: { v: 1 } },
        "ok.ipynb": { format: "json", content: { v: 2 } },
      },
    });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("bad name.ipynb");
    await core.handleFileSaved("ok.ipynb");

    expect(core.state.tier).toBe("L2"); // excluding does NOT pause the mirror
    expect(core.state.excludedCount).toBe(1);
    expect(await readDiskText(handle, "ok.ipynb")).toBe(JSON.stringify({ v: 2 }, null, 1) + "\n");
  });

  test("a TypeError from contents.get pauses the mirror instead of excluding: path stays pending, is NOT excluded (B-9)", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = {
      async get() {
        throw new TypeError("contents.get: boom");
      },
      async save() {},
    };
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("a.ipynb");

    expect(core.state.pendingCount).toBe(1);
    expect(core.state.excludedCount).toBe(0);
    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("error");
  });

  test("a write throwing NotAllowedError pauses with pauseReason 'permission'; the path stays pending", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    handle._fault("a.ipynb", "write", "NotAllowedError");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("a.ipynb");

    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("permission");
    expect(core.state.pendingCount).toBe(1);
  });

  test("a NotFoundError on write pauses with pauseReason 'folder-unavailable' -- never a Reconnect loop", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    handle._fault("a.ipynb", "getFileHandle", "NotFoundError");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("a.ipynb");

    expect(core.state.tier).toBe("L2-paused");
    expect(core.state.pauseReason).toBe("folder-unavailable");
    expect(core.state.pendingCount).toBe(1);
  });
});

describe("AC-3: exclusion, Replace, and mirrored-paths bookkeeping (D7, B-10)", () => {
  test("bulk sync on choose: writes absent files, marks identical copies mirrored, excludes differing copies without touching their bytes; both outcomes book-keep mirrored-paths", async () => {
    const drive = createFakeContents({
      files: {
        "absent.ipynb": { format: "json", content: { v: "absent" } },
        "same.txt": { format: "text", content: "same bytes" },
        "diff.ipynb": { format: "json", content: { v: "drive" } },
      },
    });
    const handle = createFakeDirectoryHandle({ name: "work" });
    await writeDiskFile(handle, "same.txt", "same bytes");
    await writeDiskFile(handle, "diff.ipynb", "not the drive's bytes");

    const pickDirectory = createFakePickDirectory({ handle });
    const handleStore = createFakeHandleStore();
    const core = createPersistence({ pickDirectory, handleStore, contents: drive });
    await core.onChooseFolderClick();
    await flushMicrotasks();

    expect(core.state.excludedCount).toBe(1);
    expect(await readDiskText(handle, "absent.ipynb")).toBe(JSON.stringify({ v: "absent" }, null, 1) + "\n");
    expect(await readDiskText(handle, "same.txt")).toBe("same bytes");
    expect(await readDiskText(handle, "diff.ipynb")).toBe("not the drive's bytes");

    const mirrored = await handleStore.get("mirrored-paths");
    expect(new Set(mirrored)).toEqual(new Set(["absent.ipynb", "same.txt"]));
    expect(await handleStore.get("excluded-paths")).toEqual({ "diff.ipynb": "differs on disk" });
  });

  test("onReplaceDiskCopyClick removes the exclusion, writes the drive bytes, and adds the path to mirrored-paths", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    await writeDiskFile(handle, "diff.ipynb", "old disk bytes");
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": [],
      "excluded-paths": { "diff.ipynb": "differs on disk" },
    });
    const contents = createFakeContents({ files: { "diff.ipynb": { format: "json", content: { v: "drive" } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();
    expect(core.state.excludedCount).toBe(1);

    await core.onReplaceDiskCopyClick("diff.ipynb");

    expect(core.state.excludedCount).toBe(0);
    expect(await readDiskText(handle, "diff.ipynb")).toBe(JSON.stringify({ v: "drive" }, null, 1) + "\n");
    expect(await handleStore.get("mirrored-paths")).toEqual(["diff.ipynb"]);
  });

  test("a save of an excluded path leaves the disk bytes unchanged (the per-save mirror skips excluded paths)", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    await writeDiskFile(handle, "diff.ipynb", "original disk bytes");
    const handleStore = createFakeHandleStore({
      "working-folder": handle,
      "pending-paths": [],
      "excluded-paths": { "diff.ipynb": "differs on disk" },
    });
    const contents = createFakeContents({ files: { "diff.ipynb": { format: "json", content: { v: "drive-2" } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    // core doesn't distinguish an explicit save from autosave -- panel.js
    // routes BOTH through the same `handleFileSaved`, so this one call
    // covers both AC-3 bullets.
    await core.handleFileSaved("diff.ipynb");

    expect(await readDiskText(handle, "diff.ipynb")).toBe("original disk bytes");
    expect(core.state.excludedCount).toBe(1);
  });

  test("a path created after bulk sync, whose disk copy already differs, is excluded on its first save and not overwritten", async () => {
    const handle = createFakeDirectoryHandle({ name: "work" });
    await writeDiskFile(handle, "new.ipynb", "pre-existing disk bytes");

    const drive = createFakeContents(); // empty at bulk-sync time
    const pickDirectory = createFakePickDirectory({ handle });
    const handleStore = createFakeHandleStore();
    const core = createPersistence({ pickDirectory, handleStore, contents: drive });
    await core.onChooseFolderClick();
    await flushMicrotasks();
    expect(core.state.excludedCount).toBe(0);

    drive._seed("new.ipynb", { format: "json", content: { v: "new drive content" } });
    await core.handleFileSaved("new.ipynb");

    expect(core.state.excludedCount).toBe(1);
    expect(await readDiskText(handle, "new.ipynb")).toBe("pre-existing disk bytes");
  });
});

describe("AC-3: ordering (D7)", () => {
  test("two saves fired back-to-back with different content leave the disk holding the second content", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    const p1 = core.handleFileSaved("a.ipynb");
    contents._seed("a.ipynb", { format: "json", content: { v: 2 } });
    const p2 = core.handleFileSaved("a.ipynb");
    await Promise.all([p1, p2]);

    expect(await readDiskText(handle, "a.ipynb")).toBe(JSON.stringify({ v: 2 }, null, 1) + "\n");
  });

  test("three fileChanged events for one path (chunked-upload analogue) end with the disk equal to the final contents.get content", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "a.txt": { format: "text", content: "chunk1" } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    const p1 = core.handleFileSaved("a.txt");
    contents._seed("a.txt", { format: "text", content: "chunk1chunk2" });
    const p2 = core.handleFileSaved("a.txt");
    contents._seed("a.txt", { format: "text", content: "chunk1chunk2chunk3" });
    const p3 = core.handleFileSaved("a.txt");
    await Promise.all([p1, p2, p3]);

    expect(await readDiskText(handle, "a.txt")).toBe("chunk1chunk2chunk3");
  });
});

describe("AC-3: restore", () => {
  test("restore writes only drive-absent paths, creates parent directories first, and never overwrites the drive", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    await writeDiskFile(handle, "sub/restore-me.ipynb", JSON.stringify({ v: "disk" }, null, 1) + "\n");
    await writeDiskFile(handle, "existing.ipynb", JSON.stringify({ v: "disk-existing" }, null, 1) + "\n");

    const contents = createFakeContents({ files: { "existing.ipynb": { format: "json", content: { v: "drive-existing" } } } });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    const result = await core.onRestoreClick();

    expect(result).toEqual({ restored: 1, skipped: 1 });
    const restored = await contents.get("sub/restore-me.ipynb", { content: true });
    expect(restored.content).toEqual({ v: "disk" });
    const untouched = await contents.get("existing.ipynb", { content: true });
    expect(untouched.content).toEqual({ v: "drive-existing" }); // never overwritten
    expect(await handleStore.get("mirrored-paths")).toEqual(["sub/restore-me.ipynb"]);
  });

  test("restore skips dot-prefixed paths", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    await writeDiskFile(handle, ".hidden", "secret");
    await writeDiskFile(handle, "visible.ipynb", `${JSON.stringify({ v: 1 }, null, 1)}\n`);

    const contents = createFakeContents();
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    const result = await core.onRestoreClick();

    expect(result.restored).toBe(1); // only visible.ipynb
    await expect(contents.get(".hidden")).rejects.toThrow();
  });

  test("a fileChanged fired for a path in the active restore set causes no folder write", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    await writeDiskFile(handle, "r.ipynb", `${JSON.stringify({ v: "disk" }, null, 1)}\n`);

    const contents = createFakeContents();
    const holdSave = contents._holdSave("r.ipynb");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    const restorePromise = core.onRestoreClick();
    await flushMicrotasks(); // let restore reach (and block on) contents.save("r.ipynb", ...)

    // Simulate panel.js routing the drive's own fileChanged "save" echo
    // that restore's own contents.save produces, while it's mid-write.
    const echoPromise = core.handleFileSaved("r.ipynb");

    holdSave.release();
    await restorePromise;
    await echoPromise;
    await flushMicrotasks();

    expect(core.state.pendingCount).toBe(0);
    expect(await handleStore.get("mirrored-paths")).toEqual(["r.ipynb"]);
  });
});

describe("AC-3: bulk sync skips dot-prefixed drive paths", () => {
  test("bulk sync skips dot-prefixed paths", async () => {
    const handle = createFakeDirectoryHandle({ name: "work" });
    const contents = createFakeContents({
      files: {
        ".hidden": { format: "text", content: "secret" },
        "visible.ipynb": { format: "json", content: { v: 1 } },
      },
    });
    const pickDirectory = createFakePickDirectory({ handle });
    const handleStore = createFakeHandleStore();
    const core = createPersistence({ pickDirectory, handleStore, contents });
    await core.onChooseFolderClick();
    await flushMicrotasks();

    expect(await readDiskText(handle, "visible.ipynb")).toBe(`${JSON.stringify({ v: 1 }, null, 1)}\n`);
    expect(await readDiskText(handle, ".hidden")).toBeNull();
  });
});

describe("AC-3: validation", () => {
  test("handleFileSaved rejects invalid paths ('.', '..', empty segments) as a no-op", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents();
    const core = createPersistence({ handleStore, contents });
    await core.init();

    expect(core.handleFileSaved("")).toBeUndefined();
    expect(core.handleFileSaved(".")).toBeUndefined();
    expect(core.handleFileSaved("..")).toBeUndefined();
    expect(core.handleFileSaved("a//b.ipynb")).toBeUndefined();
    expect(core.state.pendingCount).toBe(0);
  });
});

describe("AC-4: first-save gate logic", () => {
  test("handleExplicitSave() requests the modal iff tier is not L2 and the ack is unset", async () => {
    const core = createPersistence({ handleStore: createFakeHandleStore() });
    await core.init();

    const opened = core.handleExplicitSave();

    expect(opened).toBe(true);
    expect(core.state.modal.open).toBe(true);
  });

  test("handleExplicitSave() does not request the modal when tier is L2", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents: createFakeContents() });
    await core.init();
    expect(core.state.tier).toBe("L2");

    const opened = core.handleExplicitSave();

    expect(opened).toBe(false);
    expect(core.state.modal.open).toBe(false);
  });

  test("handleFileSaved() alone (autosave) never requests the modal", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "a.ipynb": { format: "json", content: {} } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("a.ipynb");

    expect(core.state.modal.open).toBe(false);
    expect(core.state.ack).toBeNull();
  });

  test("onKeepBrowserOnlyClick sets the ack to 'browser-only' and closes the gate", async () => {
    const core = createPersistence({ handleStore: createFakeHandleStore() });
    await core.init();
    core.handleExplicitSave();
    expect(core.state.modal.open).toBe(true);

    core.onKeepBrowserOnlyClick();

    expect(core.state.ack).toBe("browser-only");
    expect(core.state.modal.open).toBe(false);
  });

  // "Any successful choose sets the ack to 'folder'" (B-3): the modal's
  // Choose working folder and the panel's Choose working folder are the
  // SAME `onChooseFolderClick` (D4's "T6" note), so the first case below
  // covers both of those sources; the second exercises the third source,
  // "Choose a folder again" after a denied Reconnect.
  test("any successful choose sets the ack to 'folder' -- panel's/modal's onChooseFolderClick, before any save", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const pickDirectory = createFakePickDirectory({ handle });
    const core = createPersistence({ pickDirectory, handleStore: createFakeHandleStore(), contents: createFakeContents() });
    await core.init();
    expect(core.state.ack).toBeNull();

    await core.onChooseFolderClick();

    expect(core.state.ack).toBe("folder");
  });

  test("any successful choose sets the ack to 'folder' -- 'Choose a folder again' after a denied Reconnect", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "denied" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents: createFakeContents() });
    await core.init();

    await core.onReconnectClick(); // stays denied -- offers "Choose a folder again", not Reconnect
    expect(core.state.ack).toBeNull();

    const newHandle = createFakeDirectoryHandle({ name: "new", permission: "granted" });
    const pickDirectory = createFakePickDirectory({ handle: newHandle });
    const core2 = createPersistence({ pickDirectory, handleStore, contents: createFakeContents() });
    await core2.onChooseFolderClick(); // "Choose a folder again"

    expect(core2.state.ack).toBe("folder");
  });

  test("after a panel choose followed by permission loss (tier L2-paused), an explicit save requests no modal", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    const pickDirectory = createFakePickDirectory({ handle });
    const handleStore = createFakeHandleStore();
    const flags = createFakeFlags();
    const core = createPersistence({ pickDirectory, handleStore, contents: createFakeContents(), flags });
    await core.init();
    await core.onChooseFolderClick();
    expect(core.state.ack).toBe("folder");

    handle._setPermission("prompt"); // permission lapses
    // Reload analogue, sharing the SAME handleStore and flags: this is the
    // faithful way to observe "permission lapsed after a bind" without
    // core proactively re-polling permission mid-session.
    const core2 = createPersistence({ handleStore, contents: createFakeContents(), flags });
    await core2.init();
    expect(core2.state.tier).toBe("L2-paused");
    expect(core2.state.ack).toBe("folder"); // NOT re-armed by permission loss (B-3)

    const opened = core2.handleExplicitSave();

    expect(opened).toBe(false);
    expect(core2.state.modal.open).toBe(false);
  });

  test("a second explicit save after the ack requests nothing", async () => {
    const core = createPersistence({ handleStore: createFakeHandleStore() });
    await core.init();

    expect(core.handleExplicitSave()).toBe(true);
    core.onKeepBrowserOnlyClick();

    expect(core.handleExplicitSave()).toBe(false);
  });

  test("pickDirectory === null hides the choose option in the modal model", async () => {
    const core = createPersistence({ pickDirectory: null, handleStore: createFakeHandleStore() });
    await core.init();

    expect(core.state.modal.choose).toBe(false);
  });

  test("pickDirectory !== null shows the choose option in the modal model", async () => {
    const pickDirectory = createFakePickDirectory({ handle: createFakeDirectoryHandle() });
    const core = createPersistence({ pickDirectory, handleStore: createFakeHandleStore() });
    await core.init();

    expect(core.state.modal.choose).toBe(true);
  });
});

// 260922 remediation pass: core.state.excludedPaths (spec-facing array form
// of T3's excluded-paths Map, so panel.js never reads handleStore directly),
// core.state.lastBulkSync (section 3.3 tallies) and core.state.reconnectRefused
// (D1 row 50, distinguishing a denied Reconnect from the pre-attempt paused
// state).
describe("excludedPaths, lastBulkSync and reconnectRefused (260922 remediation)", () => {
  test("excludedPaths carries {path, reason} for a differs-on-disk bulk-sync exclusion, and lastBulkSync tallies written/identical/differs", async () => {
    const drive = createFakeContents({
      files: {
        "absent.ipynb": { format: "json", content: { v: "absent" } },
        "same.txt": { format: "text", content: "same bytes" },
        "diff.ipynb": { format: "json", content: { v: "drive" } },
      },
    });
    const handle = createFakeDirectoryHandle({ name: "work" });
    await writeDiskFile(handle, "same.txt", "same bytes");
    await writeDiskFile(handle, "diff.ipynb", "not the drive's bytes");

    const pickDirectory = createFakePickDirectory({ handle });
    const handleStore = createFakeHandleStore();
    const core = createPersistence({ pickDirectory, handleStore, contents: drive });

    expect(core.state.lastBulkSync).toBeNull(); // null before any bulk sync

    await core.onChooseFolderClick();
    await flushMicrotasks();

    expect(core.state.excludedPaths).toEqual([{ path: "diff.ipynb", reason: "differs on disk" }]);
    expect(core.state.lastBulkSync).toEqual({ written: 1, identical: 1, differs: 1 });
  });

  test("excludedPaths carries {path, reason} for a TypeError ('name not allowed on disk') exclusion", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "granted" });
    handle._fault("bad name.ipynb", "getFileHandle", "TypeError");
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const contents = createFakeContents({ files: { "bad name.ipynb": { format: "json", content: { v: 1 } } } });
    const core = createPersistence({ handleStore, contents });
    await core.init();

    await core.handleFileSaved("bad name.ipynb");

    expect(core.state.excludedPaths).toEqual([{ path: "bad name.ipynb", reason: "name not allowed on disk" }]);
  });

  test("reconnectRefused is set when a Reconnect click resolves non-granted, and cleared by a later successful choose", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "denied" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents: createFakeContents() });
    await core.init();
    expect(core.state.reconnectRefused).toBe(false); // pre-attempt paused state -- Reconnect still offered

    await core.onReconnectClick();
    expect(core.state.reconnectRefused).toBe(true);
    expect(core.state.tier).toBe("L2-paused");

    const newHandle = createFakeDirectoryHandle({ name: "new", permission: "granted" });
    const pickDirectory = createFakePickDirectory({ handle: newHandle });
    const core2 = createPersistence({ pickDirectory, handleStore, contents: createFakeContents() });
    await core2.onChooseFolderClick();

    expect(core2.state.reconnectRefused).toBe(false);
    expect(core2.state.tier).toBe("L2");
  });

  test("reconnectRefused is cleared on a subsequent granted Reconnect", async () => {
    const handle = createFakeDirectoryHandle({ name: "work", permission: "denied" });
    const handleStore = createFakeHandleStore({ "working-folder": handle, "pending-paths": [], "excluded-paths": {} });
    const core = createPersistence({ handleStore, contents: createFakeContents() });
    await core.init();

    await core.onReconnectClick();
    expect(core.state.reconnectRefused).toBe(true);

    handle._setPermission("granted");
    await core.onReconnectClick();

    expect(core.state.reconnectRefused).toBe(false);
    expect(core.state.tier).toBe("L2");
  });
});

describe("constructor validation", () => {
  test("requires a handleStore with a rebind method", () => {
    expect(() => createPersistence({ handleStore: {} })).toThrow();
    expect(() => createPersistence({})).toThrow();
  });
});
