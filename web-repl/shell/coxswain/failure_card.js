// failure_card.js -- §4.1's fourth message kind: the execution-failure card.
//
// Its data was fully specified before any UI existed -- ExecutionOutcome
// .status/.detail (§2.4), the PendingIntent history, the joined FftDecision[]
// (AC-7) -- but without this renderer a `failed` or `aborted_stale` outcome
// would have rendered nothing. Renders the outcome status, the failure
// detail, the call AS ATTEMPTED, and, for aborted_stale, §4.4's drift line
// naming the specific drift.
//
// READ-ONLY by design: it offers NO retry affordance in MVP. A retry is a new
// turn typed by the user, so it re-runs the whole gate; a retry button would
// invite treating a failed hardware operation as idempotent (§7).
//
// All string writes flow through text.js's setText (NFR-7/AC-15): markup is
// built with createElement-style structure, never string concatenation. This
// file contains no HTML string literals.

import { capText } from "./text.js";
import { h } from "./vdom.js";

const STATUS_HEADINGS = {
  ok: "Execution finished",
  failed: "Execution failed",
  aborted_stale: "Execution stopped",
};

/** §4.4's exact drift copy, keyed by which compared fingerprint field moved. */
const DRIFT_LINES = {
  concurrency: "A protocol run started while this proposal was open.",
  precondition: "The tip state on channel 1 changed since Coxswain checked.",
};

export function driftLine(driftKind) {
  return Object.prototype.hasOwnProperty.call(DRIFT_LINES, driftKind)
    ? DRIFT_LINES[driftKind]
    : null;
}

/**
 * Build the card as a plain virtual tree (DOM-free, unit-testable).
 *   outcome        ExecutionOutcome-shaped: {status, detail, turn_id, gate_seq}
 *   attempted_call the parsed/resolved call as attempted (rendered collapsed)
 *   drift_kind     "concurrency" | "precondition" | null (aborted_stale only)
 */
export function renderFailureCard({ outcome, attempted_call = null, drift_kind = null }) {
  if (!outcome || typeof outcome.status !== "string") {
    throw new Error("renderFailureCard requires an outcome carrying status");
  }
  const heading =
    STATUS_HEADINGS[outcome.status] !== undefined
      ? STATUS_HEADINGS[outcome.status]
      : `Outcome`;

  const children = [
    h("header", { class: "cx-failure-head" }, h("span", { class: "cx-failure-title" }, heading)),
    h(
      "p",
      { class: "cx-failure-status" },
      `${capText("warning_badge_text", outcome.status)} · turn ${capText("edited_field_value", String(outcome.turn_id))}`
    ),
  ];

  const detail =
    typeof outcome.detail === "string" && outcome.detail.length > 0
      ? outcome.detail
      : "Coxswain has no further detail about this outcome.";
  children.push(h("p", { class: "cx-failure-detail" }, capText("nl_restatement", detail)));

  if (attempted_call !== null && typeof attempted_call === "object") {
    const literal = JSON.stringify(attempted_call, null, 2);
    children.push(
      h("details", { class: "cx-attempted-call" },
        h("summary", {}, "The call as attempted"),
        h("pre", { class: "cx-attempted-call-pre" }, capText("nl_restatement", literal)),
      ),
    );
  }

  if (outcome.status === "aborted_stale") {
    const line = driftLine(drift_kind);
    if (line !== null) {
      children.push(h("p", { class: "cx-drift-line" }, line));
    }
  }

  // Read-only: deliberately no buttons, inputs, links, retry affordances.
  return h("article", {
    class: "cx-card cx-failure-card",
    "data-outcome-status": outcome.status,
    "data-turn-id": String(outcome.turn_id),
  }, ...children);
}
