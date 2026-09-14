import { describe, expect, test } from "bun:test";

import { STRING_CAPS, capText, setText, truncateText } from "../text.js";

describe("STRING_CAPS", () => {
  test("mirrors NFR-7's stated maximums exactly", () => {
    expect(STRING_CAPS).toEqual({
      nl_restatement: 400,
      candidate_label: 120,
      warning_badge_text: 64,
      edited_field_value: 200,
      override_justification: 500,
      confirmation_phrase: 60,
    });
  });
});

describe("truncateText", () => {
  test("passes short strings through unchanged", () => {
    expect(truncateText("short", 10)).toBe("short");
    expect(truncateText("exactly10!", 10)).toBe("exactly10!");
  });

  test("truncates on a word boundary with an ellipsis", () => {
    const out = truncateText("transfer four plates to the hotel", 20);
    expect(out.length).toBeLessThanOrEqual(20);
    expect(out.endsWith("…")).toBe(true);
    // word boundary: the trailing word before … is complete
    expect(out).toBe("transfer four…");
  });

  test("hard-cuts a single token longer than the cap", () => {
    const out = truncateText("ABCDEFGHIJKLMNOP", 8);
    expect(out.endsWith("…")).toBe(true);
    expect(out.length).toBeLessThanOrEqual(8);
  });

  test("never rejects silently -- every input yields a string within cap", () => {
    for (const [s, cap] of [["x".repeat(999), 64], ["a b c d e f g", 5], ["héllo wörld", 6]]) {
      const out = truncateText(s, cap);
      expect(typeof out).toBe("string");
      expect(out.length).toBeLessThanOrEqual(cap);
    }
  });

  test("degrades non-string input to empty string", () => {
    expect(truncateText(null, 5)).toBe("");
    expect(truncateText(undefined, 5)).toBe("");
    expect(truncateText(42, 5)).toBe("");
  });
});

describe("capText", () => {
  test("caps by NFR-7 string class", () => {
    const long = "w".repeat(500);
    expect(capText("warning_badge_text", long).length).toBeLessThanOrEqual(64);
    expect(capText("candidate_label", long).length).toBeLessThanOrEqual(120);
    expect(capText("nl_restatement", long).length).toBeLessThanOrEqual(400);
    expect(capText("edited_field_value", long).length).toBeLessThanOrEqual(200);
    expect(capText("override_justification", long).length).toBeLessThanOrEqual(500);
    expect(capText("confirmation_phrase", long).length).toBeLessThanOrEqual(60);
  });

  test("throws on an unknown class rather than writing uncapped", () => {
    expect(() => capText("made_up_kind", "x")).toThrow(/unknown string-cap class/);
  });
});

describe("setText", () => {
  test("writes via textContent only -- node gains zero element children", () => {
    const node = { textContent: "", children: [], title: undefined };
    setText(node, "<img src=x onerror=alert(1)>");
    expect(node.textContent).toBe("<img src=x onerror=alert(1)>");
    expect(node.children.filter((c) => c && c.tagName)).toHaveLength(0);
  });

  test("sets title property to the full untruncated value when given", () => {
    const node = { textContent: "", children: [], title: undefined };
    setText(node, "visible", { title: "full value of considerable length" });
    expect(node.title).toBe("full value of considerable length");
    expect(node.textContent).toBe("visible");
  });
});
