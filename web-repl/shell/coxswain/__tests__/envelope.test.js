import { describe, expect, test } from "bun:test";

import {
  ENVELOPE_VERSION,
  SESSION_SCOPED_KINDS,
  assertValidEnvelope,
  buildEnvelope,
  validateEnvelope,
} from "../envelope.js";

const TURN_ENVELOPE = {
  v: 1,
  session_id: "sess-1",
  turn_id: "cx-1700000000000-q7x9p2",
  kind: "coxswain.gate_result",
  seq: 0,
  ts: 1700000000000,
  payload: { disposition: "continue" },
};

describe("buildEnvelope", () => {
  test("fills in the §2.2 envelope shape with v: 1", () => {
    const env = buildEnvelope({
      session_id: "sess-1",
      turn_id: "cx-1-abc123",
      kind: "coxswain.gate_result",
      seq: 3,
      ts: 1000,
      payload: { a: 1 },
    });
    expect(env).toEqual({
      v: 1,
      session_id: "sess-1",
      turn_id: "cx-1-abc123",
      kind: "coxswain.gate_result",
      seq: 3,
      ts: 1000,
      payload: { a: 1 },
    });
  });

  test("rejects a missing turn_id loudly (throw)", () => {
    // §2.2 point 2: a turn-scoped message missing turn_id is rejected
    // loudly, never defaulted or auto-minted downstream.
    expect(() =>
      buildEnvelope({
        session_id: "sess-1",
        kind: "coxswain.gate_result",
        seq: 0,
        ts: 1000,
        payload: {},
      })
    ).toThrow(/turn_id/);
  });

  test("session-scoped kinds carry turn_id null", () => {
    const env = buildEnvelope({
      session_id: "sess-1",
      turn_id: null,
      kind: "coxswain.hello",
      seq: 0,
      ts: 1000,
    });
    expect(env.turn_id).toBeNull();
  });
});

describe("validateEnvelope", () => {
  test("accepts a well-formed turn-scoped message", () => {
    const result = validateEnvelope(TURN_ENVELOPE);
    expect(result.ok).toBe(true);
    if (result.ok) expect(result.envelope.kind).toBe("coxswain.gate_result");
  });

  test("rejects a missing turn_id loudly", () => {
    const withoutTurn = { ...TURN_ENVELOPE };
    delete withoutTurn.turn_id;
    const result = validateEnvelope(withoutTurn);
    expect(result.ok).toBe(false);
    if (!result.ok) {
      expect(result.errors.join(" ")).toMatch(/turn_id/);
    }
  });

  test("rejects an empty-string turn_id", () => {
    const result = validateEnvelope({ ...TURN_ENVELOPE, turn_id: "" });
    expect(result.ok).toBe(false);
  });

  test("turn_id may be null only for the two whitelisted handshake kinds", () => {
    for (const kind of ["coxswain.hello", "coxswain.hello_ack"]) {
      const result = validateEnvelope({ ...TURN_ENVELOPE, kind, turn_id: null, payload: undefined });
      expect(result.ok).toBe(true);
    }
    // an unrecognized kind with a null turn_id is rejected exactly as before
    const impostor = validateEnvelope({ ...TURN_ENVELOPE, kind: "coxswain.sneaky", turn_id: null });
    expect(impostor.ok).toBe(false);
  });

  test("session-scoped kinds must not smuggle a payload (§2.2 point 3)", () => {
    const result = validateEnvelope({
      ...TURN_ENVELOPE,
      kind: "coxswain.hello",
      turn_id: null,
      payload: { execute: true },
    });
    expect(result.ok).toBe(false);
  });

  test("rejects wrong envelope version", () => {
    const result = validateEnvelope({ ...TURN_ENVELOPE, v: 2 });
    expect(result.ok).toBe(false);
    if (!result.ok) expect(result.errors.join(" ")).toMatch(/v/);
  });

  test("rejects non-object input", () => {
    for (const bad of [null, undefined, 42, "envelope", []]) {
      const result = validateEnvelope(bad);
      expect(result.ok).toBe(false);
    }
  });

  test("rejects missing or malformed required fields", () => {
    for (const field of ["v", "session_id", "kind", "seq", "ts"]) {
      const partial = { ...TURN_ENVELOPE };
      delete partial[field];
      const result = validateEnvelope(partial);
      expect(result.ok).toBe(false);
      if (!result.ok) expect(result.errors.join(" ")).toMatch(new RegExp(field));
    }
    expect(validateEnvelope({ ...TURN_ENVELOPE, session_id: "" }).ok).toBe(false);
    expect(validateEnvelope({ ...TURN_ENVELOPE, seq: -1 }).ok).toBe(false);
    expect(validateEnvelope({ ...TURN_ENVELOPE, seq: 1.5 }).ok).toBe(false);
    expect(validateEnvelope({ ...TURN_ENVELOPE, ts: Number.NaN }).ok).toBe(false);
  });

  test("assertValidEnvelope throws with the error list joined", () => {
    expect(() => assertValidEnvelope({ ...TURN_ENVELOPE, turn_id: null })).toThrow(
      /turn_id/
    );
  });

  test("the exemption is a whitelist constant, not a nullable field", () => {
    // §2.2 point 3: the whitelist cannot widen by accident.
    expect(SESSION_SCOPED_KINDS).toEqual(["coxswain.hello", "coxswain.hello_ack"]);
    expect(ENVELOPE_VERSION).toBe(1);
  });
});
