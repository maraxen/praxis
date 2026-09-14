// FR-3 phrase.js -- browser-side mirror of coxswain/src/coxswain/phrase.py.
// Both sides must agree on the SAME fixtures in
// coxswain/tests/fixtures/parsed_calls/*.json (asserted from BOTH directions:
// bun test here, and a live bun subprocess inside test_phrase_parity.py).

import { describe, expect, test } from "bun:test";
import { readdirSync, readFileSync } from "node:fs";
import { join } from "node:path";

import {
  PHRASE_MAX_CHARS,
  TARGET_KEYS,
  VERBS,
  derivePhrase,
  normalizePhrase,
  phraseMatches,
  schemaVerb,
} from "../phrase.js";

const FIXTURE_DIR = join(
  import.meta.dir,
  "..",
  "..",
  "..",
  "..",
  "coxswain",
  "tests",
  "fixtures",
  "parsed_calls"
);

function fixtures() {
  return readdirSync(FIXTURE_DIR)
    .filter((f) => f.endsWith(".json"))
    .sort()
    .map((f) => ({
      file: f,
      fx: JSON.parse(readFileSync(join(FIXTURE_DIR, f), "utf8")),
    }));
}

describe("derivePhrase vs the shared fixture corpus", () => {
  for (const { file, fx } of fixtures()) {
    test(`${file} -> ${fx.expected_phrase}`, () => {
      const got = derivePhrase({ verb: fx.verb, params: fx.params });
      expect(got).toBe(fx.expected_phrase);
      expect(got.length).toBeLessThanOrEqual(PHRASE_MAX_CHARS);
    });
  }

  test("the embedded verb table agrees with every fixture's schema-sourced verb", () => {
    for (const { file, fx } of fixtures()) {
      expect(VERBS[fx.name]).toBe(fx.verb);
    }
    // and derivePhrase can therefore work straight off the call name:
    const discard = fixtures().find((f) => f.fx.name === "discard_tips");
    expect(derivePhrase(discard.fx)).toBe(discard.fx.expected_phrase);
  });
});

describe("FR-3 derivation rules", () => {
  test("multi-target: first target as-given + '+<n-1> more'", () => {
    expect(
      derivePhrase({ verb: "transfer to", params: { destination: ["B1", "B2", "B3"] } })
    ).toBe("transfer to B1 +2 more");
    expect(
      derivePhrase({ verb: "transfer to", params: { destination: ["B3", "B2", "B1"] } })
    ).toBe("transfer to B3 +2 more"); // as-given order is preserved, never sorted
    expect(
      derivePhrase({
        verb: "discard",
        params: { what: "tips", at: ["W1", "W2", "W3", "W4"] },
      })
    ).toBe("discard tips at W1 +3 more");
  });

  test("quantities never appear in the phrase", () => {
    expect(() => derivePhrase({ verb: "read", params: { at: 50 } })).toThrow();
    expect(() => derivePhrase({ verb: "read", params: { at: true } })).toThrow();
    expect(
      derivePhrase({ verb: "transfer to", params: { destination: "B3", volume_ul: 5000 } })
    ).toBe("transfer to B3"); // volume param simply never consulted
  });

  test("60-char cap regenerates from the truncated descriptor", () => {
    const long = "Waste reservoir station number twelve on deck seven";
    const out = derivePhrase({ verb: "discard", params: { what: "tips", at: long } });
    expect(out).toBe("discard tips at Waste reservoir station number twelve on");
    expect(out.length).toBeLessThanOrEqual(PHRASE_MAX_CHARS);
  });

  test("unknown call names refuse loudly instead of deriving from a raw name", () => {
    expect(() => schemaVerb("definitely_not_a_call")).toThrow(/no tool schema entry/);
    expect(() =>
      derivePhrase({ name: "definitely_not_a_call", params: {} })
    ).toThrow(/no tool schema entry/);
  });

  test("TARGET_KEYS order beats param insertion order (destination over source)", () => {
    expect(TARGET_KEYS.indexOf("destination")).toBeLessThan(TARGET_KEYS.indexOf("source"));
    expect(
      derivePhrase({ verb: "transfer to", params: { source: "A9", destination: "C1" } })
    ).toBe("transfer to C1");
  });
});

describe("normalizePhrase / phraseMatches (FR-3 matching)", () => {
  test("case-insensitive, collapsed internal whitespace, trimmed ends", () => {
    expect(normalizePhrase("  DISCARD   tips AT c3 ")).toBe("discard tips at c3");
    expect(phraseMatches("  discard   TIPS at C3 ", "discard tips at C3")).toBe(true);
    expect(phraseMatches("discard\ttips\nat C3", "DISCARD TIPS AT C3")).toBe(true);
  });

  test("no other normalization: punctuation and content differences fail", () => {
    expect(phraseMatches("discard tips at C3!", "discard tips at C3")).toBe(false);
    expect(phraseMatches("discard tips at", "discard tips at C3")).toBe(false);
    expect(phraseMatches("discard tips at C33", "discard tips at C3")).toBe(false);
    expect(phraseMatches("", "discard tips at C3")).toBe(false);
    expect(phraseMatches(null, "x")).toBe(false); // type: ignore
    expect(phraseMatches(undefined, "x")).toBe(false);
    expect(phraseMatches(42, "42")).toBe(false);
  });
});
