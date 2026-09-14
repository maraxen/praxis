// W5 relay.js -- best-effort transduction_log relay.
//
// FR-9's fourth clause and AC-19's third assertion live here on the browser
// side: the relay is fire-and-forget, never in the ack path, its latency
// never observable in any disposition. AC-10/RISK-10: ZERO network calls when
// no relay endpoint was configured at build time (the default, see
// relay_config.js). Failures are counted and surfaced in a DEBUG LINE --
// never a toast, never a modal.

import { describe, expect, test } from "bun:test";

import { AuditStore } from "../audit_store.js";
import { createRelay, RELAY_QUEUE_CAP } from "../relay.js";
import { RELAY_ENDPOINT } from "../relay_config.js";

const ENDPOINT = "https://logs.example.invalid/transduction";
const RECORD = { turn_id: "cx-1700000000000-rl01", kind: "decision", payload: {} };

function neverFetch() {
  return new Promise(() => {}); // hangs forever
}

function okFetch(calls) {
  return async (url, init) => {
    calls.push({ url, init });
    return { ok: true, status: 202 };
  };
}

test("tracked relay_config.js defaults to null: builds are inert unless flagged", () => {
  expect(RELAY_ENDPOINT).toBeNull();
});

// --- AC-10: the unconfigured path issues zero network requests -------------------

describe("unconfigured relay (default build)", () => {
  test("enqueue does nothing and fetch is never called", async () => {
    let calls = 0;
    const relay = createRelay({
      endpoint: null,
      fetchImpl: async () => {
        calls += 1;
        throw new Error("network used while unconfigured!");
      },
    });
    expect(relay.isConfigured).toBe(false);
    const result = relay.enqueue(RECORD);
    expect(result.queued).toBe(false);
    await relay.flush(); // explicit flush attempt must still be a no-op
    await Promise.resolve();
    await Promise.resolve();
    expect(calls).toBe(0);
  });

  test("debugLine names the unconfigured state instead of counters-as-toast", () => {
    const relay = createRelay({ endpoint: null });
    const line = relay.debugLine();
    expect(line).toContain("unconfigured");
  });
});

// --- configured: fire-and-forget delivery -----------------------------------------

describe("configured relay", () => {
  test("delivers enqueued records as one POST batch", async () => {
    const calls = [];
    const relay = createRelay({ endpoint: ENDPOINT, fetchImpl: okFetch(calls) });
    relay.enqueue(RECORD);
    relay.enqueue({ ...RECORD, turn_id: "cx-1700000000000-rl02" });
    // Fire-and-forget: enqueue returned BEFORE any flush completed.
    await relay.flush();
    expect(calls).toHaveLength(1);
    expect(calls[0].url).toBe(ENDPOINT);
    expect(JSON.parse(calls[0].init.body).records).toHaveLength(2);
    const line = relay.debugLine();
    expect(line).toContain("relayed=2");
    expect(line).toContain("failures=0");
  });

  test("an unreachable endpoint increments the visible failure counter and drops the batch without throwing", async () => {
    const relay = createRelay({
      endpoint: ENDPOINT,
      fetchImpl: async () => {
        throw new TypeError("fetch failed: ENOTFOUND logs.example.invalid");
      },
    });
    relay.enqueue(RECORD);
    await expect(relay.flush()).resolves.toBeUndefined(); // never throws out
    const line = relay.debugLine();
    expect(line).toContain("failures=1");
    expect(line).toContain("dropped=1");
  });

  test("a hanging endpoint delays NOTHING for callers (fire-and-forget)", async () => {
    const relay = createRelay({ endpoint: ENDPOINT, fetchImpl: neverFetch });
    relay.enqueue(RECORD);
    const result = relay.enqueue({ ...RECORD, turn_id: "cx-1700000000000-rl03" });
    // enqueue returned synchronously; the hang lives entirely inside the
    // detached flush. No await, no observable latency, no toast path.
    expect(result.queued).toBe(true);
    expect(relay.failureCount).toBe(0); // still pending, not failed
  });

  test(`the queue is bounded at ${RELAY_QUEUE_CAP}; overflow drops oldest`, async () => {
    let calls = 0;
    const relay = createRelay({
      endpoint: ENDPOINT,
      fetchImpl: async () => {
        calls += 1;
        throw new Error("down");
      },
    });
    for (let i = 0; i < RELAY_QUEUE_CAP + 5; i += 1) {
      relay.enqueue({ ...RECORD, seq: i });
    }
    expect(relay.pendingCount).toBe(RELAY_QUEUE_CAP);
    await relay.flush();
    expect(calls).toBe(1); // one batch attempt
    expect(relay.failureCount).toBe(1);
  });
});

// --- AC-19 third clause, structural half -------------------------------------------

describe("the relay is structurally absent from the ack path", () => {
  test("audit_store.js never imports or references the relay", async () => {
    const { readFileSync } = await import("node:fs");
    const storeSource = readFileSync(new URL("../audit_store.js", import.meta.url), "utf8");
    expect(storeSource.includes("relay")).toBe(false);
    expect(storeSource.includes("fetch(")).toBe(false);
  });
});

// --- integration shape with the audit store ------------------------------------------

describe("wiring shape", () => {
  test("a slow relay never blocks a local audit write completing", async () => {
    // The intended composition, proven against the real store: writes go to
    // IndexedDB; relay.enqueue is called AFTER durability resolves.
    const { FakeIndexedDBFactory } = await import("./fake_indexeddb.js");
    const idbFactory = new FakeIndexedDBFactory();
    const store = new AuditStore({
      idbFactory,
      nowMs: () => 1_700_000_000_000,
      onSystemLine: () => {},
    });
    await store.open();

    const relay = createRelay({ endpoint: ENDPOINT, fetchImpl: neverFetch });
    const ack = await store.applyWriteRequest({
      type: "audit.write",
      write_id: 1,
      kind: "begin_turn",
      turn_id: "cx-1700000000000-rl04",
      payload: { session_id: "cx-sess-x" },
    });
    expect(ack.type).toBe("audit.ack"); // durability claimed...

    relay.enqueue({ decision: "example", turn_id: "cx-1700000000000-rl04" }); // ...THEN relay
    expect(relay.pendingCount).toBe(1);
  });
});
