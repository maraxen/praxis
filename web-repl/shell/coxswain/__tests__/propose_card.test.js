// propose_card.js -- thin DOM adapter over card_state.js. All string writes go
// through text.js's setText; this file must contain no HTML string literals
// (AC-15's structural grep enforces that across shell/coxswain/).

import { describe, expect, test } from "bun:test";

import { createCardState, attachConfirmation } from "../card_state.js";
import { renderProposeCard } from "../propose_card.js";
import { mountTree } from "../vdom.js";
import { createFakeDocument } from "./dom_stub.js";

const doc = createFakeDocument();

function reversibleState() {
  return createCardState({
    tier: "reversible",
    fields: [
      { name: "volume_ul", value: 50 },
      { name: "source", value: "A1" },
      { name: "destination", value: "B3" },
    ],
  });
}

describe("renderProposeCard", () => {
  test("renders tier badge, restatement, fields, collapsed call, and actions", () => {
    const state = reversibleState();
    const tree = renderProposeCard({
      state,
      restatement: "Transfer 50 uL from A1 to B3.",
      warnings: [{ kind: "large_volume", text: "large volume" }],
      literal_call: { name: "transfer", params: { source: "A1", destination: "B3" } },
      disclosure: 'Coxswain asked which carrier because 2 matched "Hamilton".',
    });
    const root = mountTree(tree, doc);
    expect(root.textContent).toContain("Transfer 50 uL from A1 to B3.");
    expect(root.textContent).toContain("reversible");
    expect(root.textContent).toContain("large volume");
    expect(root.textContent).toContain("Show the call");
    expect(root.textContent).toContain('"transfer"');
    expect(root.textContent).toContain('2 matched "Hamilton"');
    // Confirm + Cancel affordances exist for a reversible card
    const buttons = [];
    const walk = (n) => {
      if ((n.tagName || "").toLowerCase() === "button") buttons.push(n);
      (n.children || []).forEach(walk);
    };
    walk(root);
    const labels = buttons.map((b) => b.textContent);
    expect(labels.some((t) => /confirm/i.test(t))).toBe(true);
    expect(labels.some((t) => /cancel/i.test(t))).toBe(true);
  });

  test("irreversible card renders the labelled phrase input instead of plain Confirm", () => {
    const state = createCardState({ tier: "irreversible", fields: [{ name: "at", value: "C3" }] });
    attachConfirmation(state, { phrase: "discard tips at C3" });
    const tree = renderProposeCard({
      state,
      restatement: "Discard tips at C3.",
      warnings: [],
      literal_call: { name: "discard_tips", params: { what: "tips", at: "C3" } },
      required_phrase: "discard tips at C3",
    });
    const root = mountTree(tree, doc);
    expect(root.textContent).toContain("discard tips at C3"); // rendered verbatim on the card
    const inputs = [];
    const labels = [];
    const walk = (n) => {
      if ((n.tagName || "").toLowerCase() === "input") inputs.push(n);
      if ((n.tagName || "").toLowerCase() === "label") labels.push(n.textContent);
      (n.children || []).forEach(walk);
    };
    walk(root);
    expect(inputs.length).toBeGreaterThan(0);
    expect(labels.join("\n")).toMatch(/type .*to confirm/i);
  });

  test("AC-15: an attacker-controlled field value renders as text with zero element children", () => {
    const state = reversibleState();
    const tree = renderProposeCard({
      state,
      restatement: "Move things.",
      warnings: [],
      field_overrides: { source: '<img src=x onerror=alert(1)>' },
      literal_call: {},
    });
    const root = mountTree(tree, doc);
    const inputs = [];
    const walk = (n) => {
      if ((n.tagName || "").toLowerCase() === "input") inputs.push(n);
      (n.children || []).forEach(walk);
    };
    walk(root);
    const evil = inputs.find((i) => i.value.includes("<img"));
    expect(evil.value).toBe("<img src=x onerror=alert(1)>");
    expect(evil.children).toHaveLength(0); // no element children -- it is TEXT
  });
});
