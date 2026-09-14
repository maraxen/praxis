// AC-17: forcing an IndexedDB QuotaExceededError (or any abort) on an audit
// write must (1) not silently drop -- the write FAILS explicitly, (2) render a
// loud system line naming the store and the failed turn_id, and (3) leave the
// store usable for later writes rather than poisoned. The kernel-side half of
// AC-17 (the gate exits blocked:audit_unavailable with zero PLR calls) is
// asserted in coxswain/tests/test_audit_ordering.py.

import { describe, expect, test } from "bun:test";

import { SCHEMA_VERSION, AuditStore } from "../audit_store.js";
import { FakeIndexedDBFactory } from "./fake_indexeddb.js";

const TURN_ID = "cx-1700000000000-quota1";
const SESSION = "cx-sess-1700000000000-abcd1234";

function steppedClock() {
  let now = 1_700_000_000_000;
  return () => (now += 1000);
}

function decisionRecord(turnId = TURN_ID) {
  return {
    turn_id: turnId,
    session_id: SESSION,
    gate_seq: 0,
    cue: 0,
    category: "initial",
    disposition: "continue",
    payload_kind: "",
    card_revision: 0,
    ts: 1700000000,
    fingerprint_id: null,
    override_id: null,
  };
}

async function openedStore() {
  const idbFactory = new FakeIndexedDBFactory();
  const systemLines = [];
  const store = new AuditStore({
    idbFactory,
    nowMs: steppedClock(),
    onSystemLine: (line) => systemLines.push(line),
  });
  await store.open();
  await store.beginTurn(TURN_ID, SESSION);
  systemLines.length = 0; // only failures from here on
  return { idbFactory, store, systemLines };
}

describe("QuotaExceededError path (AC-17)", () => {
  test("a quota-aborted decision write rejects explicitly and names store + turn_id", async () => {
    const { idbFactory, store, systemLines } = await openedStore();
    // Arm the fault INSIDE the fake before the write goes out.
    idbFactory._dbs.get(store._dbName).__failNextPut("coxswain_turns", () => {
      const err = new Error(
        "Encountered full disk while accessing the Indexed Database API",
      );
      err.name = "QuotaExceededError";
      return err;
    });

    let caught = null;
    try {
      await store.applyWriteRequest({
        type: "audit.write",
        write_id: 7,
        kind: "decision",
        turn_id: TURN_ID,
        payload: { record: decisionRecord() },
      });
    } catch (error) {
      caught = error;
    }

    // (1) NOT silently dropped: an explicit failure surfaced to the caller
    // -- the gate maps this onto blocked:audit_unavailable.
    expect(caught).not.toBeNull();
    expect(caught.name).toBe("QuotaExceededError");
    // The record never entered the durable store NOR the local mirror.
    expect(store.queryTurn(TURN_ID).turn.decisions).toHaveLength(0);

    // (2) Loud system line naming the store and the failed turn_id.
    const loud = systemLines.join("\n");
    expect(loud).toContain("coxswain_turns");
    expect(loud).toContain(TURN_ID);
    expect(loud.toLowerCase()).toContain("quotaexceedederror");
  });

  test("an override-store abort names coxswain_overrides", async () => {
    const { idbFactory, store, systemLines } = await openedStore();
    idbFactory._dbs.get(store._dbName).__failNextPut("coxswain_overrides", () => {
      const err = new Error("quota");
      err.name = "QuotaExceededError";
      return err;
    });

    await expect(
      store.applyWriteRequest({
        type: "audit.write",
        write_id: 8,
        kind: "override",
        turn_id: TURN_ID,
        payload: {
          record: {
            schema_version: SCHEMA_VERSION,
            override_id: `${TURN_ID}:3:ovr`,
            turn_id: TURN_ID,
            gate_seq: 3,
            cue: 3,
            justification: "confirmed safe",
            ts: 1700000001,
          },
        },
      }),
    ).rejects.toMatchObject({ name: "QuotaExceededError" });

    const loud = systemLines.join("\n");
    expect(loud).toContain("coxswain_overrides");
    expect(loud).toContain(TURN_ID);
    // The override was not applied locally either.
    expect(store.overridesForTurn(TURN_ID)).toHaveLength(0);
  });

  test("an aborted write leaves no partial state behind; later writes still work", async () => {
    const { idbFactory, store, systemLines } = await openedStore();
    idbFactory._dbs.get(store._dbName).__failNextPut("coxswain_turns", () => {
      const err = new Error("abort");
      err.name = "QuotaExceededError";
      return err;
    });

    await expect(
      store.applyWriteRequest({
        type: "audit.write",
        write_id: 9,
        kind: "decision",
        turn_id: TURN_ID,
        payload: { record: decisionRecord() },
      }),
    ).rejects.toBeTruthy();

    // A subsequent healthy write succeeds normally -- one aborted tx does not
    // poison the store.
    await store.applyWriteRequest({
      type: "audit.write",
      write_id: 10,
      kind: "decision",
      turn_id: TURN_ID,
      payload: { record: { ...decisionRecord(), gate_seq: 1 } },
    });
    const decisions = store.queryTurn(TURN_ID).turn.decisions;
    expect(decisions).toHaveLength(1);
    expect(decisions[0].gate_seq).toBe(1);
  });

  test("tx.error surfaces when a request fails without a named DOMException", async () => {
    const { idbFactory, store } = await openedStore();
    idbFactory._dbs.get(store._dbName).__failNextPut("coxswain_turns", () =>
      new Error("UnknownError: storage corrupted"),
    );
    await expect(
      store.applyWriteRequest({
        type: "audit.write",
        write_id: 11,
        kind: "decision",
        turn_id: TURN_ID,
        payload: { record: decisionRecord() },
      }),
    ).rejects.toThrow(/storage corrupted/);
  });
});
