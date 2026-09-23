// fakes.js -- Test doubles for web-repl/shell/persistence's DI seams
// (spec .praxia/docs/specs/260922_repl-persistence-ladder.md section 4,
// fakes.js row).
//
// The FSA directory-handle fake is modelled on the Map-backed pattern at
// web-repl/shell/coxswain/__tests__/audit_store.test.js:497-532, extended per
// the spec with getDirectoryHandle, values(), settable
// queryPermission/requestPermission, per-path fault injection and a
// mid-write "hold" hook (for reading tier state while a flush is paused
// mid-write -- built now so T3's write-chain tests only need to call these
// hooks, not change this file's shape).
//
// T2 uses: createFakeDirectoryHandle, createFakeHandleStore,
// createFakeStorage, createActivationRecorder.
// T3 EXTENSION POINT: a `createFakeContents` fake for the JupyterLab
// contents adapter (get/save/fileChanged) is expected to land alongside T3,
// which needs it for the write chain, restore and the AC-3 tests.

function throwNamed(name, message) {
  const error = new Error(message);
  error.name = name;
  throw error;
}

function maybeFault(faults, path, method) {
  const errorName = faults.get(`${path}::${method}`);
  if (errorName) throwNamed(errorName, `fake fault: ${errorName} at ${method}(${path})`);
}

function makeFileHandle(dirNode, fileName, filePath, shared) {
  return {
    kind: "file",
    name: fileName,

    async getFile() {
      const node = dirNode.children.get(fileName);
      if (!node || node.kind !== "file" || node.bytes == null) {
        throwNamed("NotFoundError", `${fileName} not found`);
      }
      const bytes = node.bytes;
      return {
        async text() {
          return typeof bytes === "string" ? bytes : new TextDecoder().decode(bytes);
        },
        async arrayBuffer() {
          if (bytes instanceof Uint8Array) return bytes.buffer;
          return new TextEncoder().encode(String(bytes)).buffer;
        },
      };
    },

    // T3 EXTENSION POINT: this is the write half of the mirror chain. The
    // "hold" hook (shared.holds) already pauses here so a test can read
    // `core.state.tier` mid-flush; T3's write chain is what calls this.
    async createWritable() {
      maybeFault(shared.faults, filePath, "createWritable");
      let buffer = null;
      return {
        async write(chunk) {
          maybeFault(shared.faults, filePath, "write");
          const hold = shared.holds.get(filePath);
          if (hold) await hold.promise;
          buffer = chunk;
        },
        async close() {
          dirNode.children.set(fileName, { kind: "file", name: fileName, bytes: buffer ?? new Uint8Array() });
        },
        async abort() {},
      };
    },
  };
}

function makeNodeHandle(node, path, shared) {
  const fullPath = (name) => (path ? `${path}/${name}` : name);

  return {
    kind: node.kind,
    name: node.name,

    async getDirectoryHandle(childName, { create = false } = {}) {
      const childPath = fullPath(childName);
      maybeFault(shared.faults, childPath, "getDirectoryHandle");
      let child = node.children.get(childName);
      if (!child) {
        if (!create) throwNamed("NotFoundError", `${childName} not found`);
        child = { kind: "directory", name: childName, children: new Map() };
        node.children.set(childName, child);
      }
      if (child.kind !== "directory") throwNamed("TypeMismatchError", `${childName} is not a directory`);
      return makeNodeHandle(child, childPath, shared);
    },

    async getFileHandle(fileName, { create = false } = {}) {
      const filePath = fullPath(fileName);
      maybeFault(shared.faults, filePath, "getFileHandle");
      let child = node.children.get(fileName);
      if (!child) {
        if (!create) throwNamed("NotFoundError", `${fileName} not found`);
        child = { kind: "file", name: fileName, bytes: null };
        node.children.set(fileName, child);
      }
      if (child.kind !== "file") throwNamed("TypeMismatchError", `${fileName} is not a file`);
      return makeFileHandle(node, fileName, filePath, shared);
    },

    async *values() {
      for (const child of node.children.values()) {
        yield makeNodeHandle(child, fullPath(child.name), shared);
      }
    },

    async queryPermission() {
      maybeFault(shared.faults, path, "queryPermission");
      return shared.permissionState.value;
    },

    async requestPermission() {
      maybeFault(shared.faults, path, "requestPermission");
      return shared.permissionState.value;
    },
  };
}

/**
 * A Map-backed nested FSA directory handle fake.
 *
 * @param {object} [options]
 * @param {string} [options.name] The root directory's display name.
 * @param {"granted"|"prompt"|"denied"} [options.permission] Initial
 *   queryPermission()/requestPermission() answer.
 * @returns {object} A handle exposing the real FSA surface
 *   (getFileHandle/getDirectoryHandle/values/queryPermission/requestPermission)
 *   plus test-only control methods prefixed `_`:
 *   - `_setPermission(value)` -- change what queryPermission/requestPermission answer.
 *   - `_fault(path, method, errorName)` -- make one call throw a named error.
 *     `path` is `""` for the root handle itself (e.g. root queryPermission).
 *   - `_clearFault(path, method)`
 *   - `_hold(path)` -- pauses that path's `write()` until `.release()` is
 *     called, so a test can inspect `core.state` mid-flush. Returns `{release}`.
 */
export function createFakeDirectoryHandle({ name = "root", permission = "granted" } = {}) {
  const root = { kind: "directory", name, children: new Map() };
  const shared = {
    faults: new Map(),
    holds: new Map(),
    permissionState: { value: permission },
  };
  const handle = makeNodeHandle(root, "", shared);

  handle._setPermission = (value) => {
    shared.permissionState.value = value;
  };
  handle._fault = (path, method, errorName) => {
    shared.faults.set(`${path}::${method}`, errorName);
  };
  handle._clearFault = (path, method) => {
    shared.faults.delete(`${path}::${method}`);
  };
  handle._hold = (path) => {
    let release;
    const promise = new Promise((resolve) => {
      release = resolve;
    });
    shared.holds.set(path, { promise });
    return {
      release: () => {
        release();
        shared.holds.delete(path);
      },
    };
  };

  return handle;
}

/**
 * An in-memory handle store: the four `praxis-repl-persistence` keys
 * (`working-folder`, `pending-paths`, `excluded-paths`, `mirrored-paths`).
 * Reusing the SAME instance across two `createPersistence(...)` calls models
 * a reload (the data survives; nothing else does).
 *
 * @param {object} [initial] Seed key/value pairs.
 */
export function createFakeHandleStore(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    async get(key) {
      return data.has(key) ? data.get(key) : undefined;
    },
    async set(key, value) {
      data.set(key, value);
    },
    async rebind(handle) {
      data.set("working-folder", handle);
      data.set("pending-paths", []);
      data.set("excluded-paths", {});
      data.set("mirrored-paths", []);
    },
    // Test-only introspection, not part of the real HandleStore contract.
    _raw: data,
  };
}

/**
 * A fake `localStorage`-shaped flags store (T4: `praxis-repl-persistence-ack`).
 * Reusing the SAME instance across two `createPersistence(...)` calls models
 * a reload, the same way `createFakeHandleStore` does for the handle store.
 *
 * @param {Record<string, string>} [initial]
 */
export function createFakeFlags(initial = {}) {
  const data = new Map(Object.entries(initial));
  return {
    getItem(key) {
      return data.has(key) ? data.get(key) : null;
    },
    setItem(key, value) {
      data.set(key, value);
    },
    removeItem(key) {
      data.delete(key);
    },
  };
}

/**
 * A fake `navigator.storage`. `persist()` records to `activation` (if given)
 * at CALL time, synchronously -- the AC-2 gesture-synchrony mechanism.
 *
 * @param {object} [options]
 * @param {boolean} [options.persistedResult] What `persisted()` answers.
 * @param {boolean} [options.persistResult] What `persist()` resolves.
 * @param {{record: (name: string) => void}} [options.activation]
 */
export function createFakeStorage({ persistedResult = false, persistResult = true, activation = null } = {}) {
  let currentPersisted = persistedResult;
  let currentPersistResult = persistResult;
  return {
    async persisted() {
      activation?.record("persisted");
      return currentPersisted;
    },
    async persist() {
      activation?.record("persist");
      if (currentPersistResult === true) currentPersisted = true;
      return currentPersistResult;
    },
    setPersisted(value) {
      currentPersisted = value;
    },
    setPersistResult(value) {
      currentPersistResult = value;
    },
  };
}

/**
 * A fake `pickDirectory` (the injected `showDirectoryPicker.bind(window)`,
 * D6). Records to `activation` (if given) at CALL time, synchronously, then
 * resolves with `handle` -- or rejects with an `AbortError` if `handle` is
 * `null`, modelling a cancelled/dismissed native picker.
 *
 * @param {object} [options]
 * @param {object|null} [options.handle]
 * @param {{record: (name: string) => void}} [options.activation]
 */
export function createFakePickDirectory({ handle = null, activation = null } = {}) {
  return function pickDirectory() {
    activation?.record("pickDirectory");
    if (!handle) {
      const error = new Error("picker cancelled");
      error.name = "AbortError";
      return Promise.reject(error);
    }
    return Promise.resolve(handle);
  };
}

// -- T3: fake JupyterLab contents adapter -----------------------------------
//
// A Map-backed nested tree, mirroring the FSA fake's own shape above, so
// core.js's bulk sync (which recurses through `get(path, {content:true})`'s
// `.content` array of shallow child models -- the real
// `ServiceManager.IContents.get` directory-listing contract) and restore
// (which calls `save(path, {type:"directory"})` for missing parents, then
// `save(path, fileModel)`) can be exercised without a browser. `fileChanged`
// is a minimal Lumino-signal-shaped emitter (`connect`/`disconnect`, sender
// `null`); nothing in core.js subscribes to it directly -- that routing is
// panel.js's job (T6) -- but T3's restore-echo-suppression test drives it by
// calling `handleFileSaved` itself, as panel.js's routing would.

function splitContentsPath(path) {
  return path ? path.split("/") : [];
}

function findContentsNode(root, path) {
  let node = root;
  for (const seg of splitContentsPath(path)) {
    if (!node || node.kind !== "directory") return undefined;
    node = node.children.get(seg);
  }
  return node;
}

function ensureContentsDir(root, path) {
  let node = root;
  for (const seg of splitContentsPath(path)) {
    if (node.kind !== "directory") throwNamed("TypeMismatchError", `${seg} is not a directory`);
    let child = node.children.get(seg);
    if (!child) {
      child = { kind: "directory", name: seg, children: new Map() };
      node.children.set(seg, child);
    }
    node = child;
  }
  return node;
}

function shallowContentsModel(node, parentPath) {
  const path = parentPath ? `${parentPath}/${node.name}` : node.name;
  return { name: node.name, path, type: node.kind === "directory" ? "directory" : "file" };
}

/**
 * A fake JupyterLab contents adapter (`get`/`save`/`fileChanged`), in-memory,
 * modelled on the same Map-backed nested-tree pattern as
 * `createFakeDirectoryHandle` above.
 *
 * @param {object} [options]
 * @param {Record<string, {format?: string, content: any}>} [options.files]
 *   Seed files, keyed by path, applied WITHOUT emitting `fileChanged` (initial
 *   drive state, not a live save).
 */
export function createFakeContents({ files = {} } = {}) {
  const root = { kind: "directory", name: "", children: new Map() };
  const listeners = [];
  const saveHolds = new Map();

  function emit(type, newValue, oldValue = null) {
    for (const fn of listeners) fn(null, { type, newValue, oldValue });
  }

  function writeFileNode(path, { format = "text", content }) {
    const segments = splitContentsPath(path);
    const name = segments.pop();
    const parent = segments.length ? ensureContentsDir(root, segments.join("/")) : root;
    parent.children.set(name, { kind: "file", name, format, content });
  }

  for (const [path, model] of Object.entries(files)) {
    writeFileNode(path, model);
  }

  return {
    async get(path, { content = false } = {}) {
      const node = path === "" ? root : findContentsNode(root, path);
      if (!node) throwNamed("NotFoundError", `${path} not found`);
      if (node.kind === "directory") {
        return {
          path,
          type: "directory",
          content: content ? Array.from(node.children.values()).map((c) => shallowContentsModel(c, path)) : null,
        };
      }
      return { path, type: "file", format: node.format, content: content ? node.content : null };
    },

    async save(path, model) {
      const hold = saveHolds.get(path);
      if (hold) await hold.promise;

      if (model && model.type === "directory") {
        ensureContentsDir(root, path);
        const saved = { path, type: "directory" };
        emit("save", saved);
        return saved;
      }
      writeFileNode(path, { format: model.format ?? "text", content: model.content });
      const saved = { path, type: "file", format: model.format ?? "text", content: model.content };
      emit("save", saved);
      return saved;
    },

    fileChanged: {
      connect(fn) {
        listeners.push(fn);
      },
      disconnect(fn) {
        const i = listeners.indexOf(fn);
        if (i >= 0) listeners.splice(i, 1);
      },
    },

    // Test-only helpers, not part of the real contents-manager contract.
    _seed(path, { format = "text", content } = {}) {
      writeFileNode(path, { format, content });
    },
    _delete(path) {
      const segments = splitContentsPath(path);
      const name = segments.pop();
      const parent = segments.length ? findContentsNode(root, segments.join("/")) : root;
      const existed = parent && parent.children.delete(name);
      if (existed) emit("delete", null, { path, type: "file" });
    },
    _rename(oldPath, newPath) {
      const node = findContentsNode(root, oldPath);
      if (!node) throwNamed("NotFoundError", `${oldPath} not found`);
      this._delete(oldPath);
      const segments = splitContentsPath(newPath);
      const name = segments.pop();
      node.name = name;
      const parent = segments.length ? ensureContentsDir(root, segments.join("/")) : root;
      parent.children.set(name, node);
      emit("rename", { path: newPath, type: node.kind }, { path: oldPath, type: node.kind });
    },
    /** Pause `save(path, ...)` until `.release()` is called -- for testing the
     * restore-in-progress `fileChanged` echo-suppression guard. */
    _holdSave(path) {
      let release;
      const promise = new Promise((resolve) => {
        release = resolve;
      });
      saveHolds.set(path, { promise });
      return {
        release: () => {
          release();
          saveHolds.delete(path);
        },
      };
    },
  };
}

/**
 * Records whether a "gesture" was active at the moment each fake API was
 * called (D6, AC-2). A test drives it manually around an `on*Click` call:
 *
 *   activation.set(true);
 *   const p = core.onProtectClick();
 *   activation.set(false); // synchronously, right after the call returns
 *   await p;
 *   expect(activation.calls.at(-1)).toEqual({ name: "persist", activation: true });
 *
 * A DELAYED call (one that awaits before invoking the fake API) records
 * `false` here, which is the discrimination control AC-2 requires.
 */
export function createActivationRecorder() {
  let active = false;
  const calls = [];
  return {
    set(value) {
      active = Boolean(value);
    },
    get value() {
      return active;
    },
    record(name) {
      calls.push({ name, activation: active });
    },
    get calls() {
      return calls;
    },
  };
}
