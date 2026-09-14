// ids.js -- browser-side mirror of coxswain/src/coxswain/ids.py (§2.1).
// Field names and formats are normative: turn_id is
// `cx-<epoch_ms>-<6 chars base36>`, minted ONCE per user command submission,
// at input capture, BEFORE any parse or grounding work starts.

import { describe, expect, test } from "bun:test";

import { fingerprintIdFor, mintSessionId, mintTurnId, overrideIdFor } from "../ids.js";

describe("mintTurnId", () => {
  test("format: cx-<epoch_ms>-<6 base36 chars>", () => {
    const id = mintTurnId({ nowMs: 1700000000000 });
    expect(id.startsWith("cx-1700000000000-")).toBe(true);
    const tail = id.slice("cx-1700000000000-".length);
    expect(tail).toMatch(/^[0-9a-z]{6}$/);
  });

  test("two mints at the same millisecond still differ (6 base36 random chars)", () => {
    const a = mintTurnId({ nowMs: 1000 });
    const b = mintTurnId({ nowMs: 1000 });
    expect(a).not.toBe(b);
  });

  test("randomness is injectable for deterministic tests", () => {
    const id = mintTurnId({ nowMs: 42, randomChar: () => "q" });
    expect(id).toBe("cx-42-qqqqqq");
  });

  test("default path works with no arguments", () => {
    expect(mintTurnId()).toMatch(/^cx-\d+-[0-9a-z]{6}$/);
  });
});

describe("mintSessionId", () => {
  test("distinct sessions get distinct ids", () => {
    expect(mintSessionId()).not.toBe(mintSessionId());
    expect(mintSessionId()).toMatch(/^cx-sess-/);
  });
});

describe("composite ids mirror the python formats exactly", () => {
  test("fingerprint_id_for / overrideIdFor", () => {
    expect(fingerprintIdFor("cx-1-abc123", 4)).toBe("cx-1-abc123:4:fp");
    expect(overrideIdFor("cx-1-abc123", 7)).toBe("cx-1-abc123:7:ovr");
  });
});
