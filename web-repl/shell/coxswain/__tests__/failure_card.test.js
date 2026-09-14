// failure_card.js -- §4.1's fourth message kind: the execution-failure card.
// Renders ExecutionOutcome.status/detail, the call as attempted, and §4.4's
// drift line for aborted_stale. READ-ONLY: it offers no retry affordance in
// MVP (a retry is a new turn, typed by the user, so it re-runs the whole gate).

import { describe, expect, test } from "bun:test";

import { renderFailureCard } from "../failure_card.js";
import { mountTree } from "../vdom.js";
import { createFakeDocument } from "./dom_stub.js";

const doc = createFakeDocument();

function mounted(tree) {
  return mountTree(tree, doc);
}

function outcome(overrides = {}) {
  return {
    turn_id: "cx-1-abc123",
    gate_seq: 3,
    status: "failed",
    detail: "LiquidHandler.dispatch raised: tip not picked up",
    ts: 1700000000000,
    ...overrides,
  };
}

describe("renderFailureCard", () => {
  test("renders the outcome status and failure detail as text", () => {
    const tree = renderFailureCard({ outcome: outcome() });
    const html = mounted(tree).textContent;
    expect(html).toContain("failed");
    expect(html).toContain("tip not picked up");
  });

  test("renders the attempted call", () => {
    const tree = renderFailureCard({
      outcome: outcome(),
      attempted_call: { name: "aspirate", params: { source: "A1", volume_ul: 10 } },
    });
    expect(mounted(tree).textContent).toContain('"aspirate"');
    expect(mounted(tree).textContent).toContain('"A1"');
  });

  test("aborted_stale with concurrency drift renders §4.4's exact drift line", () => {
    const tree = renderFailureCard({
      outcome: outcome({
        status: "aborted_stale",
        detail: "concurrency became active since proposal",
      }),
      drift_kind: "concurrency",
    });
    expect(mounted(tree).textContent).toContain(
      "A protocol run started while this proposal was open."
    );
  });

  test("aborted_stale with precondition drift renders the digest drift line", () => {
    const tree = renderFailureCard({
      outcome: outcome({ status: "aborted_stale" }),
      drift_kind: "precondition",
    });
    expect(mounted(tree).textContent).toContain(
      "The tip state on channel 1 changed since Coxswain checked."
    );
  });

  test("a failed outcome renders NO drift line", () => {
    const tree = renderFailureCard({ outcome: outcome(), drift_kind: null });
    expect(mounted(tree).textContent).not.toContain("A protocol run started");
    expect(mounted(tree).textContent).not.toContain("The tip state on channel 1");
  });

  test("READ-ONLY: no button or input element anywhere in the card", () => {
    const tags = [];
    const walk = (node) => {
      if (node.tagName) tags.push(node.tagName.toLowerCase());
      (node.children || []).forEach(walk);
    };
    for (const args of [
      { outcome: outcome() },
      { outcome: outcome({ status: "aborted_stale" }), drift_kind: "precondition" },
    ]) {
      walk(renderFailureCard(args));
      expect(tags).not.toContain("button");
      expect(tags).not.toContain("input");
      expect(tags).not.toContain("a");
      // and no retry affordance smuggled in as a click-handler class either
      expect(JSON.stringify(tags)).not.toMatch(/retry/i);
    }
  });
});
