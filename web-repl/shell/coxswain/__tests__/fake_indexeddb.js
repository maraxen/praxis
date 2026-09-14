// fake_indexeddb.js -- in-memory IndexedDB subset for bun test (NFR-3: zero
// installed dependencies; bun ships no IDB implementation).
//
// Implements exactly the surface audit_store.js uses, with the event
// ORDERING that matters for FR-9:
//   - request success fires BEFORE its transaction's complete;
//   - a failed request fires error, then the transaction aborts;
//   - complete NEVER fires once any request in the transaction failed.
// All dispatch happens on the microtask queue, so handlers always run
// asynchronously like a real browser, and FIFO order preserves the above.
//
// A transaction commits automatically once every request scheduled against it
// has settled and no new ones arrive -- mirroring IDB's "no pending requests"
// rule closely enough for these tests.
//
// Test-only extras (namespaced with __):
//   db.__failNextPut(storeName, errorOrFactory)
//       inject QuotaExceededError-style faults to exercise AC-17.
//   factory.__seed(name, version, buildFn)
//       pre-create a database as if a different build had written it,
//       for §2.5 / AC-21 tests.

function makeDOMException(message, name) {
  if (typeof DOMException === "function") {
    return new DOMException(message, name);
  }
  const err = new Error(message);
  err.name = name;
  return err;
}

/** Synchronous dispatch -- callers are responsible for being on the microtask
 * queue already, which keeps relative event ordering obvious. */
function fire(target, type, event) {
  const handler = target[`on${type}`];
  if (typeof handler === "function") handler.call(target, event ?? { type });
}

const clone = (value) =>
  value === undefined ? undefined : JSON.parse(JSON.stringify(value));

class FakeRequest {
  // `kind` labels the event ("success"); the owning tx tracks settlement.
  constructor(tx) {
    this._tx = tx;
    this.result = undefined;
    this.error = null;
    this.onsuccess = null;
    this.onerror = null;
    if (tx) tx._requestScheduled();
  }

  _settle(kind, value, error) {
    if (kind === "success") {
      this.result = clone(value);
      queueMicrotask(() => {
        fire(this, "success", { type: "success", target: this });
        this._tx._requestSettled();
      });
    } else {
      this.error = error;
      queueMicrotask(() => {
        fire(this, "error", { type: "error", target: this, error });
        this._tx._requestFailed(error);
      });
    }
  }
}

class FakeObjectStore {
  constructor(tx, name, keyPath) {
    this._tx = tx;
    this.name = name;
    this.keyPath = keyPath;
  }

  _records() {
    return this._tx._db._stores[this.name];
  }

  _takeFault(op) {
    return this._tx._db.__takeFault(this.name, op);
  }

  put(value) {
    const request = new FakeRequest(this._tx);
    try {
      const fault = this._takeFault("put");
      if (fault) throw fault.error;
      const key = value[this.keyPath];
      if (key === undefined) {
        throw makeDOMException(
          `DataError: keyPath ${this.keyPath} missing from value`,
          "DataError",
        );
      }
      this._records()[key] = clone(value);
      request._settle("success", key);
    } catch (error) {
      request._settle("error", undefined, error);
    }
    return request;
  }

  get(key) {
    const request = new FakeRequest(this._tx);
    try {
      const fault = this._takeFault("get");
      if (fault) throw fault.error;
      request._settle("success", this._records()[key]);
    } catch (error) {
      request._settle("error", undefined, error);
    }
    return request;
  }

  getAll() {
    const request = new FakeRequest(this._tx);
    try {
      const fault = this._takeFault("getAll");
      if (fault) throw fault.error;
      request._settle("success", Object.values(this._records()));
    } catch (error) {
      request._settle("error", undefined, error);
    }
    return request;
  }

  delete(key) {
    const request = new FakeRequest(this._tx);
    try {
      const fault = this._takeFault("delete");
      if (fault) throw fault.error;
      delete this._records()[key];
      request._settle("success", undefined);
    } catch (error) {
      request._settle("error", undefined, error);
    }
    return request;
  }
}

class FakeTransaction {
  constructor(db, storeNames, mode) {
    this._db = db;
    this.mode = mode;
    this.oncomplete = null;
    this.onerror = null;
    this.onabort = null;
    this.error = undefined;
    this._pending = 0;
    this._settled = false;
    this.objectStoreNames = Object.freeze([...storeNames]);
    for (const name of storeNames) {
      if (!db._stores[name]) {
        throw makeDOMException(
          `NotFoundError: no object store named ${name}`,
          "NotFoundError",
        );
      }
    }
    // A transaction with zero requests still commits (real IDB behaviour):
    // give it one microtask for synchronous request issuance to land first.
    queueMicrotask(() => this._maybeCommit());
  }

  objectStore(name) {
    if (!this.objectStoreNames.includes(name)) {
      throw makeDOMException(
        `NotFoundError: ${name} is not part of this transaction`,
        "NotFoundError",
      );
    }
    const spec = this._db._storeSpecs[name];
    return new FakeObjectStore(this, name, spec.keyPath);
  }

  _requestScheduled() {
    this._pending += 1;
  }

  _requestSettled() {
    this._pending -= 1;
    queueMicrotask(() => this._maybeCommit());
  }

  _requestFailed(error) {
    this._pending -= 1;
    queueMicrotask(() => this._abortWith(error));
  }

  _maybeCommit() {
    if (this._settled || this._pending !== 0) return;
    this._settled = true;
    // FR-9's load-bearing property: every request's success handler has
    // already run by now; complete comes after ALL of them.
    fire(this, "complete", { type: "complete", target: this });
  }

  _abortWith(error) {
    if (this._settled) return;
    this._settled = true;
    // Real IDB exposes the failure as transaction.error.
    this.error = error;
    fire(this, "error", { type: "error", target: this, error });
    fire(this, "abort", { type: "abort", target: this, error });
  }
}

export class FakeDatabase {
  constructor(name, version) {
    this.name = name;
    this.version = version;
    this._stores = {}; // name -> { key -> record }
    this._storeSpecs = {}; // name -> { keyPath }
    this.__pendingFaults = [];
  }

  createObjectStore(name, options = {}) {
    this._stores[name] = {};
    this._storeSpecs[name] = { keyPath: options.keyPath ?? "id" };
    return { name };
  }

  get objectStoreNames() {
    const names = Object.keys(this._stores);
    const list = [...names];
    // Real IDB returns a DOMStringList-ish with .contains().
    list.contains = (name) => names.includes(name);
    return Object.freeze(list);
  }

  __failNextPut(storeName, errorOrFactory) {
    this.__pendingFaults.push({ storeName, op: "put", errorOrFactory });
  }

  __takeFault(storeName, op) {
    const index = this.__pendingFaults.findIndex(
      (f) => f.storeName === storeName && f.op === op,
    );
    if (index === -1) return null;
    const [fault] = this.__pendingFaults.splice(index, 1);
    const error =
      typeof fault.errorOrFactory === "function"
        ? fault.errorOrFactory()
        : fault.errorOrFactory;
    return { op, error };
  }

  transaction(storeNames, mode = "readonly") {
    const names = Array.isArray(storeNames) ? storeNames : [storeNames];
    return new FakeTransaction(this, names, mode);
  }

  close() {}
}

export class FakeIDBOpenDBRequest {
  constructor() {
    this.result = null;
    this.error = null;
    this.onsuccess = null;
    this.onerror = null;
    this.onupgradeneeded = null;
  }
}

export class FakeIndexedDBFactory {
  constructor() {
    this._dbs = new Map();
  }

  open(name, requestedVersion) {
    const request = new FakeIDBOpenDBRequest();
    queueMicrotask(() => {
      const existing = this._dbs.get(name) ?? null;
      if (
        requestedVersion != null &&
        existing !== null &&
        requestedVersion < existing.version
      ) {
        request.error = makeDOMException(
          `VersionError: The requested version (${requestedVersion}) is less ` +
            `than the existing version (${existing.version}).`,
          "VersionError",
        );
        fire(request, "error", {
          type: "error",
          target: request,
          error: request.error,
        });
        return;
      }
      const oldVersion = existing === null ? 0 : existing.version;
      let db = existing;
      if (db === null) {
        db = new FakeDatabase(name, requestedVersion ?? 1);
        this._dbs.set(name, db);
      } else if (requestedVersion != null && requestedVersion > db.version) {
        db.version = requestedVersion;
      }
      if (db.version > oldVersion || oldVersion === 0) {
        // Real IDB exposes result on the request during upgradeneeded.
        request.result = db;
        fire(request, "upgradeneeded", {
          type: "upgradeneeded",
          target: request,
          result: db,
          oldVersion,
        });
      }
      request.result = db;
      fire(request, "success", { type: "success", target: request });
    });
    return request;
  }

  /** Pre-create a database exactly as some other build would have left it. */
  __seed(name, version, buildFn) {
    const db = new FakeDatabase(name, version);
    buildFn(db);
    this._dbs.set(name, db);
    return db;
  }
}
