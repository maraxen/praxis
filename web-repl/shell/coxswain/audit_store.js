// audit_store.js -- the L0 IndexedDB backend (W5) for the two object stores
// `coxswain_turns` and `coxswain_overrides`.
//
// This is the browser half of coxswain/src/coxswain/persistence/store.py: it
// implements THE SAME lifecycle/eviction/schema-version semantics, not new
// ones -- §2.3 turn lifecycle with abandon-on-load, FIFO eviction over whole
// closed turn records only (an open turn is NEVER evicted; open turns alone
// reaching cap + OPEN_TURN_HEADROOM refuse loudly instead), the
// override-store exemption, and §2.5's loud read-only degrade on ANY schema
// mismatch (no migration, no silent coercion, no flag to soften it).
//
// FR-9 durability claim: an ack for a write resolves ONLY from the IndexedDB
// transaction's `complete` event -- never from an individual request's
// `success`. Callers (the praxis_coxswain message layer) send `audit.ack`
// carrying request.write_id once applyWriteRequest() resolves, and
// `audit.nack` plus a loud system line when it rejects.
//
// AC-17: QuotaExceededError and ANY other abort surface as an explicit write
// failure AND a loud system line naming the store and the failed turn_id --
// never swallowed, never partially applied (the in-memory view is updated
// only after the transaction committed).
//
// DOM-free except for the injected IndexedDB factory (NFR-3); zero
// dependencies so bun test runs it bare (AC-3).

export const SCHEMA_VERSION = 1; // mirror of coxswain.records.SCHEMA_VERSION
export const DEFAULT_TURN_CAP = 1000; // §2.3 / store.py DEFAULT_TURN_CAP
export const OPEN_TURN_HEADROOM = 16; // §2.3 / store.py OPEN_TURN_HEADROOM

export const DB_NAME = "praxis_coxswain_audit";
export const TURNS_STORE = "coxswain_turns";
export const OVERRIDES_STORE = "coxswain_overrides";

const WRITE_KINDS = [
  "begin_turn",
  "close_turn",
  "abandon_turn",
  "attach_intent",
  "decision",
  "fingerprint",
  "override",
  "attach_outcome",
];

export class ReadOnlyStoreError extends Error {
  constructor(statusMessage) {
    super(
      statusMessage ||
        "Coxswain's audit store is read-only (§2.5 schema-version degrade)",
    );
    this.name = "ReadOnlyStoreError";
  }
}

export class OpenTurnCapacityExceeded extends Error {
  constructor(detail) {
    super(detail);
    this.name = "OpenTurnCapacityExceeded";
  }
}

function blankTurnRecord(turnId, sessionId, openedAtSeconds) {
  return {
    schema_version: SCHEMA_VERSION,
    turn_id: turnId,
    session_id: sessionId,
    state: "open",
    opened_at: openedAtSeconds,
    closed_at: null,
    transcript: [],
    pending_intents: [],
    decisions: [],
    fingerprints: [],
    outcome: null,
  };
}

function newerBuildMessage(recordVersion, buildVersion) {
  return (
    `Coxswain's audit store was written by a newer build ` +
    `(schema ${recordVersion}, this build understands ${buildVersion}). ` +
    "Existing records are readable; Coxswain will not run until you update."
  );
}

function olderBuildMessage(recordVersion, buildVersion) {
  return (
    `Coxswain's audit store was written by an older build ` +
    `(schema ${recordVersion}, this build understands ${buildVersion}). ` +
    "Existing records are readable; no migration is performed."
  );
}

/** FIFO over closed/abandoned records, oldest closed_at first; an open turn
 * is never a victim regardless of age (§2.3). Pure over a Map of records. */
function computeEvictionVictims(records, cap) {
  const excess = records.size - cap;
  if (excess <= 0) return [];
  const evictable = [...records.values()]
    .filter((r) => r.state !== "open")
    .sort(
      (a, b) =>
        a.closed_at - b.closed_at ||
        a.opened_at - b.opened_at ||
        (a.turn_id < b.turn_id ? -1 : 1),
    );
  return evictable.slice(0, excess).map((r) => r.turn_id);
}

export class AuditStore {
  /**
   * @param {object} options
   * @param {IDBFactory} options.idbFactory injectable (tests pass the fake)
   * @param {string} [options.dbName]
   * @param {() => number} [options.nowMs] milliseconds, like Date.now()
   * @param {(line: string) => void} [options.onSystemLine] loud failures
   * @param {number} [options.turnCap]
   */
  constructor({
    idbFactory = globalThis.indexedDB,
    dbName = DB_NAME,
    nowMs = Date.now,
    onSystemLine = () => {},
    turnCap = DEFAULT_TURN_CAP,
  } = {}) {
    if (!idbFactory) {
      throw new Error(
        "AuditStore requires an IndexedDB factory (no indexedDB in this environment)",
      );
    }
    this._idbFactory = idbFactory;
    this._dbName = dbName;
    this._nowMs = nowMs;
    this._onSystemLine = onSystemLine;
    this._turnCap = turnCap;

    this._db = null;
    this._mode = "read_write";
    this._statusMessage = null;
    /** @type {Map<string, object>} */
    this._turns = new Map();
    /** @type {object[]} */
    this._overrides = [];
  }

  // -- open ------------------------------------------------------------------

  /** Open the database, load both stores, run §2.5 checks, abandon-on-load,
   * and evict over cap. Resolves even in the read-only degraded modes. */
  async open() {
    try {
      await this._openAt(SCHEMA_VERSION);
    } catch (error) {
      if (error && error.name === "VersionError") {
        // A NEWER build wrote this store. Reopen WITHOUT a version request
        // (always allowed), keep it readable, refuse all writes (§2.5).
        await this._openAt(null);
        this._degradeReadOnly(
          newerBuildMessage(this._storedDbVersion ?? "?", SCHEMA_VERSION),
        );
        await this._loadAndScan({ allowLifecycle: false });
        return this;
      }
      throw error;
    }
    await this._loadAndScan({ allowLifecycle: true });
    return this;
  }

  /** Mirrors store.py._load exactly: §2.5 body scan FIRST (a foreign build
   * owns the records' lifecycle -- leave them untouched), then
   * abandon-on-load, then eviction. */
  async _loadAndScan({ allowLifecycle }) {
    const { turns, overrides } = await this._loadAll();
    this._turns = new Map(turns.map((r) => [r.turn_id, r]));
    this._overrides = [...overrides];

    // A VersionError-degraded open has already named both numbers; loading is
    // all that remains (AC-21: readable + exportable).
    if (this._mode === "read_only") return;

    const foreignVersions = new Set(
      [...this._turns.values(), ...this._overrides]
        .map((r) => r.schema_version)
        .filter((v) => v !== SCHEMA_VERSION),
    );
    if (foreignVersions.size > 0) {
      const above = [...foreignVersions].filter((v) => v > SCHEMA_VERSION);
      if (above.length > 0) {
        this._degradeReadOnly(newerBuildMessage(Math.max(...above), SCHEMA_VERSION));
      } else {
        this._degradeReadOnly(
          olderBuildMessage(Math.min(...foreignVersions), SCHEMA_VERSION),
        );
      }
      return; // no lifecycle bookkeeping against foreign-schema records
    }
    if (!allowLifecycle) return;

    // §2.3 abandon-on-load: turns still open at session init were orphaned
    // mid-turn; close them as abandoned at the load time.
    const opened = [...this._turns.values()].filter((r) => r.state === "open");
    if (opened.length > 0) {
      const closedAt = this._nowMs / 1000;
      const tx = this._db.transaction([TURNS_STORE], "readwrite");
      const store = tx.objectStore(TURNS_STORE);
      for (const record of opened) {
        const abandoned = { ...record, state: "abandoned", closed_at: closedAt };
        this._turns.set(record.turn_id, abandoned);
        store.put(abandoned);
      }
      await AuditStore._txDone(tx);
    }

    await this._evictOverCap();
  }

  static _txDone(tx) {
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => resolve();
      tx.onabort = () => reject(tx.error ?? new Error("IndexedDB transaction aborted"));
      tx.onerror = () => {}; // onabort carries the failure
    });
  }

  async _evictOverCap() {
    const victims = computeEvictionVictims(this._turns, this._turnCap);
    if (victims.length === 0) return [];
    const tx = this._db.transaction([TURNS_STORE], "readwrite");
    const store = tx.objectStore(TURNS_STORE);
    for (const victim of victims) store.delete(victim);
    await AuditStore._txDone(tx);
    for (const victim of victims) this._turns.delete(victim);
    return victims;
  }

  _openAt(version) {
    return new Promise((resolve, reject) => {
      const request =
        version === null
          ? this._idbFactory.open(this._dbName)
          : this._idbFactory.open(this._dbName, version);
      request.onerror = () => reject(request.error);
      request.onupgradeneeded = (event) => {
        const db = event.target.result;
        if (!db.objectStoreNames.contains(TURNS_STORE)) {
          db.createObjectStore(TURNS_STORE, { keyPath: "turn_id" });
        }
        if (!db.objectStoreNames.contains(OVERRIDES_STORE)) {
          db.createObjectStore(OVERRIDES_STORE, { keyPath: "override_id" });
        }
      };
      request.onsuccess = () => {
        this._db = request.result;
        this._storedDbVersion = request.result.version;
        resolve();
      };
    });
  }

  async _loadAll() {
    const tx = this._db.transaction([TURNS_STORE, OVERRIDES_STORE], "readonly");
    const turnsRequest = tx.objectStore(TURNS_STORE).getAll();
    const overridesRequest = tx.objectStore(OVERRIDES_STORE).getAll();
    await Promise.all([
      new Promise((resolve, reject) => {
        turnsRequest.onsuccess = resolve;
        turnsRequest.onerror = () => reject(turnsRequest.error);
      }),
      new Promise((resolve, reject) => {
        overridesRequest.onsuccess = resolve;
        overridesRequest.onerror = () => reject(overridesRequest.error);
      }),
    ]);
    return { turns: turnsRequest.result ?? [], overrides: overridesRequest.result ?? [] };
  }

  _degradeReadOnly(message) {
    this._mode = "read_only";
    this._statusMessage = message;
    this._onSystemLine(`SYSTEM: ${message}`);
  }

  // -- introspection -----------------------------------------------------------

  get mode() {
    return this._mode;
  }

  get statusMessage() {
    return this._statusMessage;
  }

  get turnCount() {
    return this._turns.size;
  }

  get _dbNameForTest() {
    return this._dbName;
  }

  // -- reads -------------------------------------------------------------------

  getTurn(turnId) {
    return this._turns.get(turnId) ?? null;
  }

  /** AC-7 join half: ONE call returning the aggregate plus every override
   * joined by turn_id. Null when nothing carries that turn_id. */
  queryTurn(turnId) {
    const turn = this.getTurn(turnId);
    if (turn === null) return null;
    return { turn, overrides: this.overridesForTurn(turnId) };
  }

  overridesForTurn(turnId) {
    return this._overrides.filter((o) => o.turn_id === turnId);
  }

  /** Self-describing L3 bundle, same shape as store.py export_bundle(). */
  exportBundle() {
    const turns = {};
    for (const [id, record] of this._turns) turns[id] = record;
    return {
      exported_by_schema_version: SCHEMA_VERSION,
      turns,
      overrides: [...this._overrides],
    };
  }

  // -- the FR-9 write protocol ----------------------------------------------------

  /**
   * Apply one kernel-side write request ({type:"audit.write", write_id,
   * kind, turn_id, payload}) durably. Resolves {type:"audit.ack", write_id}
   * ONLY from transaction `complete`; rejects on any failure (after emitting
   * the loud system line) so the caller can answer `audit.nack`.
   */
  async applyWriteRequest(request) {
    if (!request || request.type !== "audit.write" || request.write_id === undefined) {
      throw new Error("malformed audit write request (expected type 'audit.write')");
    }
    const kind = request.kind;
    if (!WRITE_KINDS.includes(kind)) {
      this._onSystemLine(
        `SYSTEM: audit_store rejected unknown write kind "${kind}" for turn ${request.turn_id}`,
      );
      throw new Error(`audit_store: unknown write kind "${kind}"`);
    }
    await this._write(kind, request.turn_id, request.payload ?? {});
    return { type: "audit.ack", write_id: request.write_id };
  }

  // -- typed convenience wrappers (same durability guarantees). Declared
  // async so validation failures reject consistently for await-style callers.

  async beginTurn(turnId, sessionId) {
    return this._write("begin_turn", turnId, { session_id: sessionId });
  }

  async closeTurn(turnId) {
    return this._write("close_turn", turnId, {});
  }

  async abandonTurn(turnId) {
    return this._write("abandon_turn", turnId, {});
  }

  async attachPendingIntent(turnId, intent) {
    return this._write("attach_intent", turnId, { intent });
  }

  async attachOutcome(turnId, outcome) {
    return this._write("attach_outcome", turnId, { outcome });
  }

  async addOverride(record) {
    return this._write("override", record.turn_id, { record });
  }

  // -- internals -----------------------------------------------------------------

  _ensureWritable() {
    if (this._mode !== "read_write") {
      throw new ReadOnlyStoreError(this._statusMessage ?? undefined);
    }
  }

  _requireOpenTurn(turnId) {
    const record = this._turns.get(turnId);
    if (record === undefined || record.state !== "open") {
      throw new Error(
        `audit_store: no open turn ${turnId}; refusing to persist a record that matches nothing`,
      );
    }
    return record;
  }

  /** Issue ALL requests for one logical write inside ONE transaction, then
   * resolve exclusively via `complete` (FR-9). The in-memory view is updated
   * only after that resolution, so an aborted transaction leaves NO partial
   * state behind (AC-17's third property). */
  _write(kind, turnId, payload) {
    this._ensureWritable();

    // Validation + victim computation happen against the CURRENT mirror, so
    // every rejection below happens BEFORE the transaction exists.
    let nextTurns = null;
    let nextOverrides = null;
    let touchedStores;

    switch (kind) {
      case "begin_turn": {
        const openCount = [...this._turns.values()].filter(
          (r) => r.state === "open",
        ).length;
        if (openCount >= this._turnCap + OPEN_TURN_HEADROOM) {
          const detail =
            `${openCount} open turns have reached the retention cap ` +
            `(${this._turnCap}) + headroom (${OPEN_TURN_HEADROOM}); Coxswain ` +
            "stopped accepting new turns. Turns are being minted and never " +
            "resolved -- this is a pathological state and must be visible.";
          this._onSystemLine(`SYSTEM: ${detail}`);
          throw new OpenTurnCapacityExceeded(detail);
        }
        if (this._turns.has(turnId)) {
          throw new Error(`audit_store: turn ${turnId} already exists`);
        }
        nextTurns = new Map(this._turns);
        nextTurns.set(
          turnId,
          blankTurnRecord(turnId, payload.session_id, this._nowMs / 1000),
        );
        touchedStores = [TURNS_STORE];
        break;
      }
      case "close_turn":
      case "abandon_turn": {
        const record = this._turns.get(turnId);
        if (record === undefined) {
          throw new Error(`audit_store: no turn ${turnId} to ${kind}`);
        }
        if (kind === "close_turn" && record.state !== "open") {
          // Idempotent, like store.py close_turn: nothing to write.
          return Promise.resolve({ ok: true, kind, turn_id: turnId, victims: [] });
        }
        nextTurns = new Map(this._turns);
        nextTurns.set(turnId, {
          ...record,
          state: kind === "close_turn" ? "closed" : "abandoned",
          closed_at: this._nowMs / 1000,
        });
        touchedStores = [TURNS_STORE];
        break;
      }
      case "attach_intent": {
        const record = this._requireOpenTurn(turnId);
        nextTurns = new Map(this._turns);
        nextTurns.set(turnId, {
          ...record,
          pending_intents: [...record.pending_intents, payload.intent],
        });
        touchedStores = [TURNS_STORE];
        break;
      }
      case "decision": {
        const record = this._requireOpenTurn(turnId);
        nextTurns = new Map(this._turns);
        nextTurns.set(turnId, {
          ...record,
          decisions: [...record.decisions, payload.record],
        });
        touchedStores = [TURNS_STORE];
        break;
      }
      case "fingerprint": {
        const record = this._requireOpenTurn(turnId);
        nextTurns = new Map(this._turns);
        nextTurns.set(turnId, {
          ...record,
          fingerprints: [...record.fingerprints, payload.record],
        });
        touchedStores = [TURNS_STORE];
        break;
      }
      case "override": {
        this._requireOpenTurn(turnId);
        nextOverrides = [...this._overrides, payload.record];
        touchedStores = [OVERRIDES_STORE];
        break;
      }
      case "attach_outcome": {
        const record = this._requireOpenTurn(turnId);
        // §2.3: writing an ExecutionOutcome closes the turn -- any status.
        nextTurns = new Map(this._turns);
        nextTurns.set(turnId, {
          ...record,
          outcome: payload.outcome,
          state: "closed",
          closed_at: this._nowMs / 1000,
        });
        touchedStores = [TURNS_STORE];
        break;
      }
      default:
        throw new Error(`audit_store: unhandled write kind "${kind}"`);
    }

    // §2.3 eviction: atomic per turn record, computed from the post-write
    // population so a write can immediately evict its own predecessors.
    const victims =
      nextTurns !== null ? computeEvictionVictims(nextTurns, this._turnCap) : [];

    return new Promise((resolve, reject) => {
      const storeNames = new Set(touchedStores);
      if (victims.length > 0) storeNames.add(TURNS_STORE);
      const tx = this._db.transaction([...storeNames], "readwrite");

      tx.oncomplete = () => {
        // Durability claimed: NOW (and only now) the mirror follows.
        if (nextTurns !== null) {
          this._turns = nextTurns;
          for (const victim of victims) this._turns.delete(victim);
        }
        if (nextOverrides !== null) this._overrides = nextOverrides;
        resolve({ ok: true, kind, turn_id: turnId, victims });
      };
      tx.onabort = () => {
        const error = tx.error ?? new Error("IndexedDB transaction aborted");
        this._reportAbort(error, touchedStores, turnId);
        reject(error);
      };
      tx.onerror = () => {}; // onabort carries the failure; avoid double paths

      try {
        if (nextTurns !== null) {
          const updatedIds = [...nextTurns.keys()];
          const changed = updatedIds.filter((id) => {
            if (victims.includes(id)) return false;
            const previous = this._turns.get(id);
            return !previous || previous !== nextTurns.get(id);
          });
          const store = tx.objectStore(TURNS_STORE);
          for (const id of changed) store.put(nextTurns.get(id));
          for (const victim of victims) store.delete(victim);
        } else if (kind === "override") {
          tx.objectStore(OVERRIDES_STORE).put(payload.record);
        }
      } catch (issueRequestError) {
        // Request construction failed (e.g. injected quota fault): real IDB
        // would fail the request inside the transaction; model the same
        // outcome -- explicit failure + loud line, no ack.
        this._reportAbort(issueRequestError, touchedStores, turnId);
        reject(issueRequestError);
      }
    });
  }

  _reportAbort(error, touchedStores, turnId) {
    const names = touchedStores.join(", ");
    this._onSystemLine(
      `SYSTEM: audit write FAILED -- store(s) [${names}], turn_id ${turnId}: ` +
        `${error?.name ?? "Error"}: ${error?.message ?? error}`,
    );
  }

  // -- import (L3 half of export.js's bundle contract) ----------------------------

  /** Import a bundle produced by exportBundle()/store.py export_bundle().
   * Read-only stores refuse. Both stores are treated as ONE bundle. */
  async importBundle(bundle) {
    this._ensureWritable();
    if (
      !bundle ||
      typeof bundle !== "object" ||
      typeof bundle.turns !== "object" ||
      !Array.isArray(bundle.overrides)
    ) {
      throw new Error("audit_store: malformed bundle (need {turns, overrides})");
    }
    const foreign = new Set(
      [
        ...Object.values(bundle.turns),
        ...bundle.overrides,
      ]
        .map((r) => r.schema_version)
        .filter((v) => v !== SCHEMA_VERSION),
    );
    // The bundle header is part of the self-describing contract (§2.5): a
    // document written by another build refuses to import even when empty.
    if (
      typeof bundle.exported_by_schema_version === "number" &&
      bundle.exported_by_schema_version !== SCHEMA_VERSION
    ) {
      foreign.add(bundle.exported_by_schema_version);
    }
    if (foreign.size > 0) {
      const version = [...foreign][0];
      // Same loud refusal as §2.5 -- importing foreign-schema records would be
      // exactly the silent coercion the spec forbids.
      throw new ReadOnlyStoreError(
        version > SCHEMA_VERSION
          ? newerBuildMessage(version, SCHEMA_VERSION)
          : olderBuildMessage(version, SCHEMA_VERSION),
      );
    }

    const nextTurns = new Map([
      ...this._turns,
      ...Object.entries(bundle.turns),
    ]);
    const nextOverrides = [...this._overrides, ...bundle.overrides];
    const seenOverrideIds = new Set(nextOverrides.map((o) => o.override_id));
    if (seenOverrideIds.size !== nextOverrides.length) {
      throw new Error("audit_store: bundle contains duplicate override_ids");
    }

    const tx = this._db.transaction([TURNS_STORE, OVERRIDES_STORE], "readwrite");
    return new Promise((resolve, reject) => {
      tx.oncomplete = () => {
        this._turns = nextTurns;
        this._overrides = nextOverrides;
        resolve({ imported_turns: Object.keys(bundle.turns).length });
      };
      tx.onabort = () => {
        const error = tx.error ?? new Error("import transaction aborted");
        this._reportAbort(error, [TURNS_STORE, OVERRIDES_STORE], "(import)");
        reject(error);
      };
      tx.onerror = () => {};
      const turnsStore = tx.objectStore(TURNS_STORE);
      const overridesStore = tx.objectStore(OVERRIDES_STORE);
      for (const record of Object.values(bundle.turns)) turnsStore.put(record);
      for (const record of bundle.overrides) overridesStore.put(record);
    });
  }
}
