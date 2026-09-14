// card_state.js -- DOM-free field validation state machine (§3.1), card_revision
// increments, confirm_enabled derivation, and confirmation-phrase matching glue.
//
// THIS is where AC-4's JS half is tested: dispatching Confirm while a symbolic
// field is `revalidating` must emit NO execute message. A test that only asserts
// a CSS class or aria-disabled attribute does NOT satisfy AC-4 -- these tests
// assert on emitted messages.

import { describe, expect, test } from "bun:test";

import {
  FIELD_STATES,
  attachConfirmation,
  confirmEnabled,
  createCardState,
  dismissClarification,
  editField,
  groundField,
  markRevalidating,
  setGateInFlight,
  setTypedPhrase,
  stampValidatedRevision,
  submitConfirm,
} from "../card_state.js";

function reversibleCard() {
  return createCardState({
    tier: "reversible",
    fields: [
      { name: "volume_ul", value: 50 },
      { name: "source", value: "A1" },
      { name: "destination", value: "B3" },
    ],
  });
}

function irreversibleCard() {
  const state = createCardState({
    tier: "irreversible",
    fields: [{ name: "at", value: "C3" }],
  });
  attachConfirmation(state, { phrase: "discard tips at C3" });
  return state;
}

describe("createCardState", () => {
  test("starts fully validated at revision 0", () => {
    const state = reversibleCard();
    expect(state.card_revision).toBe(0);
    expect(state.fields.every((f) => f.state === "validated")).toBe(true);
    expect(confirmEnabled(state)).toBe(true);
  });

  test("FIELD_STATES is exactly §3.1's five-state vocabulary", () => {
    expect(FIELD_STATES).toEqual([
      "validated",
      "dirty_unvalidated",
      "revalidating",
      "awaiting_clarification",
      "invalid",
    ]);
  });
});

describe("edit -> revalidate lifecycle (FR-4/§3.1)", () => {
  test("an edit marks dirty_unvalidated and increments card_revision", () => {
    const state = reversibleCard();
    editField(state, "destination", "C7");
    expect(state.field("destination").state).toBe("dirty_unvalidated");
    expect(state.card_revision).toBe(1);
    expect(confirmEnabled(state)).toBe(false);
  });

  test("each edit increments the revision (two edits = +2)", () => {
    const state = reversibleCard();
    editField(state, "volume_ul", 60);
    editField(state, "volume_ul", 70);
    expect(state.card_revision).toBe(2);
  });

  test("markRevalidating moves a dirty symbolic field to revalidating", () => {
    const state = reversibleCard();
    editField(state, "source", "D4");
    markRevalidating(state, "source");
    expect(state.field("source").state).toBe("revalidating");
    expect(confirmEnabled(state)).toBe(false); // only validated counts (§3.1)
  });

  test("grounding to validated restores confirm_enabled and stamps validated_revision", () => {
    const state = reversibleCard();
    editField(state, "source", "D4");
    markRevalidating(state, "source");
    groundField(state, "source", { status: "validated" });
    expect(state.field("source").state).toBe("validated");
    expect(state.validated_revision).toBe(1);
    expect(confirmEnabled(state)).toBe(true);
  });

  test("grounding to invalid fails closed and keeps confirm blocked", () => {
    const state = reversibleCard();
    editField(state, "source", "nowhere");
    markRevalidating(state, "source");
    groundField(state, "source", { status: "invalid" });
    expect(state.field("source").state).toBe("invalid");
    expect(confirmEnabled(state)).toBe(false);
  });

  test("awaiting_clarification blocks confirm WITHOUT changing card_revision (§3.1/C16)", () => {
    const state = reversibleCard();
    const before = state.card_revision;
    editField(state, "destination", "the plate carrier");
    const afterEdit = state.card_revision;
    markRevalidating(state, "destination");
    groundField(state, "destination", { status: "awaiting_clarification" });
    expect(state.field("destination").state).toBe("awaiting_clarification");
    expect(state.card_revision).toBe(afterEdit);
    expect(afterEdit).toBe(before + 1); // the edit was already counted once
    expect(confirmEnabled(state)).toBe(false);
  });

  test("dismissing a clarification reverts to the last validated value", () => {
    const state = reversibleCard();
    editField(state, "destination", "the plate carrier");
    markRevalidating(state, "destination");
    groundField(state, "destination", { status: "awaiting_clarification" });
    dismissClarification(state, "destination");
    const field = state.field("destination");
    expect(field.state).toBe("validated");
    expect(field.value).toBe("B3"); // never a resolved-looking unresolved field
    expect(confirmEnabled(state)).toBe(true);
  });
});

describe("gate_in_flight participates in the derivation (§3.1 layer 2)", () => {
  test("confirm_enabled is false while any gate pass is in flight", () => {
    const state = reversibleCard();
    setGateInFlight(state, true);
    expect(confirmEnabled(state)).toBe(false);
    setGateInFlight(state, false);
    expect(confirmEnabled(state)).toBe(true);
  });

  test("one unvalidated field among validated ones still blocks", () => {
    const state = reversibleCard();
    editField(state, "volume_ul", 55); // dirty_unvalidated; others untouched
    expect(confirmEnabled(state)).toBe(false);
  });
});

describe("AC-4 JS half: Confirm dispatch emits NO execute message while blocked", () => {
  test("a field in revalidating swallows the dispatch", () => {
    const state = reversibleCard();
    editField(state, "source", "B9");
    markRevalidating(state, "source"); // <-- re-grounding in flight

    const emitted = [];
    const handled = submitConfirm(
      state,
      (msg) => emitted.push(msg),
      { turn_id: "cx-1-abc123", session_id: "sess-1" }
    );

    expect(handled).toBe(false);
    expect(emitted).toEqual([]); // no execute message, not a weakened one
  });

  test("a fast click during dirty_unvalidated is swallowed too", () => {
    const state = reversibleCard();
    editField(state, "destination", "C2");
    const emitted = [];
    const handled = submitConfirm(state, (msg) => emitted.push(msg), {});
    expect(handled).toBe(false);
    expect(emitted).toEqual([]);
  });

  test("a programmatic dispatch with gate_in_flight is swallowed", () => {
    const state = reversibleCard();
    setGateInFlight(state, true);
    const emitted = [];
    submitConfirm(state, (msg) => emitted.push(msg), {});
    expect(emitted).toEqual([]);
  });

  test("a fully validated card emits exactly one execute request carrying both revisions", () => {
    const state = reversibleCard();
    editField(state, "source", "B9");
    markRevalidating(state, "source");
    groundField(state, "source", { status: "validated" }); // all validated again

    const emitted = [];
    const handled = submitConfirm(
      state,
      (msg) => emitted.push(msg),
      { turn_id: "cx-1-abc123", session_id: "sess-1" }
    );
    expect(handled).toBe(true);
    expect(emitted).toHaveLength(1);
    expect(emitted[0].kind).toBe("coxswain.execute_request");
    expect(emitted[0].turn_id).toBe("cx-1-abc123");
    expect(emitted[0].payload.card_revision).toBe(1);
    expect(emitted[0].payload.validated_revision).toBe(1);
  });
});

describe("irreversible tier: typed phrase gates the handler (AC-13 JS half)", () => {
  test("empty / prefix / one-char-off / different-call phrases emit nothing", () => {
    for (const typed of ["", "discard tips at", "discard tips at C4", "transfer to B1 +2 more"]) {
      const state = irreversibleCard();
      setTypedPhrase(state, typed);
      const emitted = [];
      const handled = submitConfirm(state, (m) => emitted.push(m), { turn_id: "t" });
      expect(handled).toBe(false);
      expect(emitted).toEqual([]);
    }
  });

  test("the exact phrase (and its normalized form) emits one message", () => {
    for (const typed of ["discard tips at C3", "  DISCARD   TIPS AT c3 "]) {
      const state = irreversibleCard();
      setTypedPhrase(state, typed);
      const emitted = [];
      const handled = submitConfirm(state, (m) => emitted.push(m), { turn_id: "t" });
      expect(handled).toBe(true);
      expect(emitted).toHaveLength(1);
    }
  });

  test("phrase correctness cannot substitute for validated fields", () => {
    const state = irreversibleCard();
    setTypedPhrase(state, "discard tips at C3");
    editField(state, "at", "C5"); // now dirty
    const emitted = [];
    submitConfirm(state, (m) => emitted.push(m), {});
    expect(emitted).toEqual([]);
  });
});

describe("stampValidatedRevision", () => {
  test("records the current revision as fully validated", () => {
    const state = reversibleCard();
    stampValidatedRevision(state);
    expect(state.validated_revision).toBe(0);
    editField(state, "volume_ul", 10);
    stampValidatedRevision(state);
    expect(state.validated_revision).toBe(1);
  });
});
