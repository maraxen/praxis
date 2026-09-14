// card_state.js -- the DOM-free safety core of the propose/confirm card.
//
// §3.1: every field carries a validation state from the closed five-state
// vocabulary; Confirm is blocked at three independent layers and this module
// OWNS layer 2's derivation (`confirm_enabled`), which the handler
// recomputes before emitting anything. AC-4's JS half is tested against this
// module: a dispatch while any field is not `validated` (or while a gate pass
// is in flight) emits NO execute message. The kernel-side revision guard in
// coxswain/execute.py is layer 3, the authoritative one.
//
// Also lives here: card_revision increments (§2.1), validated_revision
// stamping ("stamped by the last completed validation pass", §3.1 layer 3),
// and the irreversible-tier confirmation-phrase glue via phrase.js.
//
// DOM-free (NFR-3), zero dependencies, unit-testable with bun test.

import { phraseMatches } from "./phrase.js";

/** §3.1's closed per-field validation vocabulary (C16 added the fourth). */
export const FIELD_STATES = Object.freeze([
  "validated",
  "dirty_unvalidated",
  "revalidating",
  "awaiting_clarification",
  "invalid",
]);

const RISKS = Object.freeze(["read_only", "reversible", "irreversible"]);

function assertFieldState(value) {
  if (!FIELD_STATES.includes(value)) {
    throw new Error(`invalid field state ${JSON.stringify(value)}`);
  }
  return value;
}

/**
 * Create one propose/confirm card's state.
 * fields: [{ name, value, state? }] -- state defaults to "validated".
 */
export function createCardState({ tier, fields, card_revision = 0 }) {
  if (!RISKS.includes(tier)) {
    throw new Error(`createCardState: unknown tier ${JSON.stringify(tier)}`);
  }
  const normalized = fields.map((f) => ({
    name: f.name,
    value: f.value,
    state: assertFieldState(f.state === undefined ? "validated" : f.state),
  }));
  const state = {
    tier,
    card_revision,
    validated_revision: card_revision,
    gate_in_flight: false,
    typed_phrase: "",
    required_phrase: null,
    fields: normalized,
    field(name) {
      const found = state.fields.find((f) => f.name === name);
      if (!found) throw new Error(`unknown card field ${JSON.stringify(name)}`);
      return found;
    },
  };
  // Last known-good values per field -- what §3.1's dismissal revert restores.
  Object.defineProperty(state, "last_validated_values", {
    value: Object.fromEntries(normalized.filter((f) => f.state === "validated").map((f) => [f.name, f.value])),
    configurable: true,
  });
  return state;
}

function requireValidated(state, name) {
  return state.field(name);
}

/**
 * FR-4: an inline edit marks the field dirty_unvalidated and increments
 * card_revision -- the edit generation of the proposal (§2.1). The tier and
 * the grounding are unchanged by an edit; whether the new value satisfies the
 * preconditions is what re-validation decides.
 */
export function editField(state, name, value) {
  const field = requireValidated(state, name);
  field.value = value;
  field.state = "dirty_unvalidated";
  state.card_revision += 1;
  return state;
}

/** Debounce expiry (or blur flush): the edit has entered the FFT gate. */
export function markRevalidating(state, name) {
  const field = requireValidated(state, name);
  if (field.state !== "dirty_unvalidated" && field.state !== "revalidating") {
    throw new Error(
      `markRevalidating requires dirty_unvalidated, got ${field.state} for ${name}`
    );
  }
  field.state = "revalidating";
  return state;
}

/**
 * A completed re-grounding pass lands here.
 * outcome.status: "validated" | "invalid" | "awaiting_clarification"
 * (§3.1/C16). awaiting_clarification does NOT change card_revision -- the
 * edit was already counted; resolving or dismissing moves the field on.
 */
export function groundField(state, name, outcome) {
  const field = requireValidated(state, name);
  if (field.state === "awaiting_clarification" && outcome.status === "awaiting_clarification") {
    return state; // idempotent re-entry while the clarification card is open
  }
  switch (outcome.status) {
    case "validated":
      field.state = "validated";
      if (outcome.value !== undefined) field.value = outcome.value;
      state.last_validated_values[field.name] = field.value;
      if (state.fields.every((f) => f.state === "validated")) {
        stampValidatedRevision(state);
      }
      break;
    case "invalid":
      // Fail closed (§4.2: expiry also lands here, never to validated).
      field.state = "invalid";
      break;
    case "awaiting_clarification":
      field.state = "awaiting_clarification";
      break;
    default:
      throw new Error(`groundField: unknown grounding outcome ${outcome.status}`);
  }
  return state;
}

/**
 * Dismissing a clarification without answering reverts the field to its last
 * VALIDATED value and re-renders the original proposal (§3.1) -- it never
 * leaves a resolved-looking field that was never resolved.
 */
export function dismissClarification(state, name) {
  const field = requireValidated(state, name);
  if (field.state !== "awaiting_clarification") {
    throw new Error(`dismissClarification requires awaiting_clarification, got ${field.state}`);
  }
  field.state = "validated";
  if (state.last_validated_values && name in state.last_validated_values) {
    field.value = state.last_validated_values[name];
  }
  if (state.fields.every((f) => f.state === "validated")) {
    stampValidatedRevision(state);
  }
  return state;
}

/** §3.1 layer 3's stamp: the revision whose validation pass last COMPLETED. */
export function stampValidatedRevision(state) {
  state.validated_revision = state.card_revision;
  return state;
}

export function setGateInFlight(state, inFlight) {
  state.gate_in_flight = Boolean(inFlight);
  return state;
}

/**
 * Attach the irreversible-tier confirmation requirement. `phrase.required`
 * is the DERIVED phrase (kernel-derived when available; locally derivable via
 * phrase.js for immediate render). Only `irreversible` cards accept it.
 */
export function attachConfirmation(state, { phrase }) {
  if (state.tier !== "irreversible") {
    throw new Error("attachConfirmation applies only to irreversible cards");
  }
  if (typeof phrase !== "string" || phrase.length === 0) {
    throw new Error("attachConfirmation requires a non-empty required phrase");
  }
  state.required_phrase = phrase;
  return state;
}

export function setTypedPhrase(state, typed) {
  state.typed_phrase = typeof typed === "string" ? typed : "";
  return state;
}

function allFieldsValidated(state) {
  return state.fields.length > 0 && state.fields.every((f) => f.state === "validated");
}

/**
 * §3.1 layer 2's recomputation:
 *   confirm_enabled = all(f.state == "validated") and not gate_in_flight
 * and, for irreversible tiers, additionally the verbatim typed phrase (FR-3).
 */
export function confirmEnabled(state, overrides = {}) {
  const inFlight = "gate_in_flight" in overrides ? overrides.gate_in_flight : state.gate_in_flight;
  if (inFlight) return false;
  if (!allFieldsValidated(state)) return false;
  if (state.tier === "irreversible") {
    if (typeof state.required_phrase !== "string") return false;
    return phraseMatches(state.typed_phrase, state.required_phrase);
  }
  return true;
}

/**
 * THE handler-layer guard (AC-4 JS half). Recomputes confirm_enabled from
 * this DOM-free module and returns WITHOUT emitting anything when it is
 * false -- catching a fast click, an Enter keypress on a stale focus, and a
 * programmatic dispatch alike. Returns true iff a message was emitted.
 *
 * identity: { turn_id, session_id } -- minted at input capture (§2.2).
 */
export function submitConfirm(state, emit, identity = {}) {
  if (!confirmEnabled(state)) {
    return false; // early return, no message of ANY kind emitted
  }
  emit({
    v: 1,
    session_id: identity.session_id ?? null,
    turn_id: identity.turn_id ?? null,
    kind: "coxswain.execute_request",
    seq: identity.seq ?? 0,
    ts: Date.now(),
    payload: {
      card_revision: state.card_revision,
      validated_revision: state.validated_revision,
      fields: state.fields.map((f) => ({ name: f.name, value: f.value })),
    },
  });
  return true;
}
