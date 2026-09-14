// clarify_card.js -- §4.3's clarification card renderer (W4, FR-7/N5-B).
//
// Each exit payload kind renders DISTINCTLY:
//   clarify:disambiguate -> candidate picker (+ N5-B sections) + typed answer
//   clarify:not_found    -> rephrase prompt for the failed reference
//   clarify:incomplete   -> missing-field prompt, one labelled input per field
//   clarify:precondition -> plain explanation; the override affordance lives
//                           ONLY here and ONLY when payload.overridable is
//                           true (FR-10: cues 0/1/2 expose none at all)
//   blocked:concurrent   -> plain explanation with NO affordances whatsoever
//
// FR-8: clicks AND typed answers leave through ONE envelope kind,
// "clarify.answer"; neither path emits any parse/model request. The kernel's
// deterministic matcher (coxswain/clarify.py) resolves both against the
// already-fetched candidate set -- this module never decides a match itself.
//
// DOM-free (NFR-3): trees built via vdom.h; every string write is a text node
// through text.js caps (NFR-7/AC-15). This file contains no HTML literals.

import { capText } from "./text.js";
import { h, mountTree } from "./vdom.js";

/** The dispositions this card knows how to render. Unknown -> throw. */
const RENDERABLE = new Set([
  "clarify:disambiguate",
  "clarify:not_found",
  "clarify:incomplete",
  "clarify:precondition",
  "blocked:concurrent",
]);

function section(title, lines) {
  if (!lines || lines.length === 0) return null;
  return h(
    "div",
    { class: `cx-clarity-section cx-clarity-${title.toLowerCase()}` },
    h("span", { class: "cx-clarity-title" }, title),
    ...lines.map((line) =>
      h("p", { class: "cx-clarity-line" }, capText("nl_restatement", String(line))),
    ),
  );
}

function candidateLabel(candidate) {
  const name = typeof candidate?.name === "string" ? candidate.name : "";
  const position =
    typeof candidate?.position === "string" && candidate.position.length > 0
      ? candidate.position
      : null;
  return position ? `${name} on ${position}` : name;
}

function disambiguateChildren(args) {
  const candidates = args.candidates;
  const children = [
    h(
      "header",
      { class: "cx-clarify-head" },
      h("h3", { class: "cx-clarify-title" },
        `Which ${args.slot || "resource"}?`),
      h("p", { class: "cx-clarify-lead" },
        `Coxswain found ${candidates.length} match${candidates.length === 1 ? "" : "es"}. Pick one or type an answer.`),
    ),
  ];

  const cat = args.categorization;
  if (cat && typeof cat === "object") {
    const sections = [
      section("Matches", cat.matches),
      section("Conflicts", cat.conflicts),
      section("Omissions", cat.omissions),
    ].filter(Boolean);
    if (sections.length > 0) {
      children.push(h("div", { class: "cx-clarity" }, ...sections));
    }
  }

  children.push(
    h(
      "div",
      { class: "cx-picker", role: "group", "aria-label": "candidate choices" },
      ...candidates.map((c, i) =>
        h(
          "button",
          {
            type: "button",
            class: "cx-pick",
            "data-action": "pick",
            "data-candidate-index": String(i),
          },
          capText("candidate_label", candidateLabel(c)),
        ),
      ),
    ),
    h("input", {
      type: "text",
      class: "cx-answer-input",
      "data-action": "clarify-input",
      placeholder: `or type which ${(args.slot || "resource").replace("_", " ")}`,
      autocomplete: "off",
      spellcheck: "false",
    }),
    h("button", { type: "button", class: "cx-submit", "data-action": "clarify-submit" }, "Answer"),
  );
  return children;
}

function notFoundChildren(args) {
  return [
    h(
      "header",
      { class: "cx-clarify-head" },
      h("h3", { class: "cx-clarify-title" }, "Coxswain cannot resolve that."),
      h("p", { class: "cx-clarify-lead" }, capText("nl_restatement", String(args.message ?? ""))),
    ),
    h("input", {
      type: "text",
      class: "cx-answer-input",
      "data-action": "clarify-input",
      placeholder: `name a different ${(args.slot || "resource").replace("_", " ")}`,
      autocomplete: "off",
      spellcheck: "false",
    }),
    h("button", { type: "button", class: "cx-submit", "data-action": "clarify-submit" }, "Try again"),
  ];
}

function incompleteChildren(args) {
  const fields = Array.isArray(args.missing_fields) ? args.missing_fields : [];
  return [
    h(
      "header",
      { class: "cx-clarify-head" },
      h("h3", { class: "cx-clarify-title" }, "Some required information is missing."),
      h("p", { class: "cx-clarify-lead" }, "Fill in the highlighted field(s) to continue."),
    ),
    h(
      "div",
      { class: "cx-fields" },
      ...fields.map((f) =>
        h("div", { class: "cx-field-row", "data-field-name": String(f) },
          h("label", { for: `cx-missing-${f}` }, String(f)),
          h("input", {
            id: `cx-missing-${f}`,
            type: "text",
            class: "cx-field-input",
            "data-field-input": String(f),
            autocomplete: "off",
            spellcheck: "false",
          }),
        ),
      ),
    ),
    h("button", { type: "button", class: "cx-submit", "data-action": "clarify-submit" }, "Submit"),
  ];
}

function preconditionChildren(args) {
  const unmet = Array.isArray(args.unmet_preconditions)
    ? args.unmet_preconditions.map(String)
    : [];
  const children = [
    h(
      "header",
      { class: "cx-clarify-head" },
      h("h3", { class: "cx-clarify-title" }, "A precondition is not met."),
      ...unmet.map((u) => h("p", { class: "cx-unmet" }, capText("warning_badge_text", u))),
    ),
  ];
  // FR-10: ONLY cue 3 exits carry an override affordance, ONLY when the gate
  // said overridable -- and never a disabled one.
  if (args.overridable === true) {
    children.push(
      h("p", { class: "cx-override-prompt" },
        capText("nl_restatement", String(args.override_prompt ?? ""))),
      h("div", { class: "cx-confirm-row cx-override-row" },
        h("input", {
          type: "text",
          class: "cx-justification",
          "data-action": "justification",
          placeholder: "type why this check can be skipped",
          autocomplete: "off",
          spellcheck: "false",
        }),
        h("button", { type: "button", class: "cx-override", "data-action": "override" }, "Override"),
      ),
    );
  }
  return children;
}

function blockedChildren(args) {
  const reason = args.concurrency_active === false || args.concurrency_active == null
    ? "Coxswain cannot tell whether another run is active, so it must wait."
    : "Another protocol run is active right now.";
  return [
    h(
      "header",
      { class: "cx-clarify-head" },
      h("h3", { class: "cx-clarify-title" }, "Blocked."),
      h("p", { class: "cx-clarify-lead" }, reason),
      h("p", { class: "cx-blocked-note" }, "Wait for it to finish, then submit this request again."),
    ),
  ];
}

/**
 * Build §4.3's clarification card as a virtual tree.
 * Disposition-specific inputs are read from flat `args` so callers need not
 * know payload dataclass shapes; unknown dispositions throw loudly.
 */
export function renderClarifyCard(args) {
  if (!args || !RENDERABLE.has(args.disposition)) {
    throw new Error(`renderClarifyCard: unknown disposition ${String(args?.disposition)}`);
  }
  let children;
  switch (args.disposition) {
    case "clarify:disambiguate": {
      const candidates = Array.isArray(args.candidates) ? args.candidates : [];
      if (candidates.length === 0) {
        throw new Error("a disambiguate card requires a non-empty candidate set");
      }
      children = disambiguateChildren({ ...args, candidates });
      break;
    }
    case "clarify:not_found":
      children = notFoundChildren(args);
      break;
    case "clarify:incomplete":
      children = incompleteChildren(args);
      break;
    case "clarify:precondition":
      children = preconditionChildren(args);
      break;
    default:
      children = blockedChildren(args); // blocked:concurrent
  }
  return h("article", {
    class: `cx-card cx-clarify-card`,
    "data-disposition": args.disposition,
    ...(args.slot ? { "data-slot": String(args.slot) } : {}),
  }, ...children);
}

/**
 * Materialize + collect refs. `wire({emit, identity})` attaches handlers;
 * FR-10's no-affordance guarantee holds structurally: cards rendered without
 * a control simply have no ref to wire, so nothing can fire.
 */
export function buildClarifyCard(tree, doc) {
  const root = mountTree(tree, doc);
  const refs = {
    root,
    pickButtons: [],
    answerInput: null,
    submitButton: null,
    fieldInputs: {},
    justificationInput: null,
    overrideButton: null,
    clickableCount: 0,
    wire,
  };

  const walk = (node) => {
    const action = node.getAttribute ? node.getAttribute("data-action") : null;
    if (action === "pick") {
      refs.pickButtons.push(node);
      refs.clickableCount += 1;
    }
    if (action === "clarify-input") refs.answerInput = node;
    if (action === "clarify-submit") {
      refs.submitButton = node;
      refs.clickableCount += 1;
    }
    if (action === "justification") refs.justificationInput = node;
    if (action === "override") {
      refs.overrideButton = node;
      refs.clickableCount += 1;
    }
    const fieldName = node.getAttribute ? node.getAttribute("data-field-input") : null;
    if (fieldName) refs.fieldInputs[fieldName] = node;
    for (const child of node.childNodes || []) {
      if (child.tagName) walk(child);
    }
  };
  walk(root);

  function wire({ emit, identity }) {
    if (typeof emit !== "function") throw new Error("clarify card wire requires an emit sink");
    const turn_id = identity?.turn_id ?? null;
    const session_id = identity?.session_id ?? null;
    let seq = Number(identity?.seq ?? 0);

    const send = (kind, payload) => {
      emit({
        v: 1,
        session_id,
        turn_id,
        kind,
        seq: seq++,
        ts: Date.now(),
        payload,
      });
    };

    for (const button of refs.pickButtons) {
      button.onclick = () => {
        send("clarify.answer", {
          slot: treeSlot(),
          answer: null,
          candidate_index: Number(button.getAttribute("data-candidate-index")),
        });
      };
    }

    if (refs.submitButton) {
      refs.submitButton.onclick = () => {
        const disposition = root.getAttribute("data-disposition");
        if (disposition === "clarify:incomplete") {
          const supplies = {};
          for (const [name, input] of Object.entries(refs.fieldInputs)) {
            supplies[name] = typeof input.value === "string" ? input.value.trim() : "";
          }
          send("clarify.answer", { supplies });
          return;
        }
        const text = refs.answerInput && typeof refs.answerInput.value === "string"
          ? refs.answerInput.value.trim()
          : "";
        if (!text) return; // empty answer: emit NOTHING rather than guess
        send("clarify.answer", {
          slot: treeSlot(),
          answer: text,
          candidate_index: null,
        });
      };
    }

    if (refs.overrideButton) {
      refs.overrideButton.onclick = () => {
        const justification =
          refs.justificationInput && typeof refs.justificationInput.value === "string"
            ? refs.justificationInput.value.trim()
            : "";
        if (!justification) return; // FR-10: overrides require non-empty justification
        send("coxswain.override_request", { justification });
      };
    }
  }

  function treeSlot() {
    // The slot under question travels with the card args; recover it from the
    // lead copy is fragile, so the builder stashes it as a data attribute.
    return root.getAttribute("data-slot") || "";
  }

  return refs;
}
