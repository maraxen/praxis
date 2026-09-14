// propose_card.js -- thin DOM adapter over card_state.js (§4.2's card shape).
//
// ALL safety-load-bearing behavior lives in the DOM-free modules this file
// wires together: the confirm derivation in card_state.confirmEnabled, the
// handler guard in card_state.submitConfirm, phrase matching in phrase.js.
// What lives HERE is presentation only -- and even that routes every string
// through text.js's caps (NFR-7) and builds structure through vdom.js. This
// file contains no HTML string literals (AC-15's structural grep enforces
// that across shell/coxswain/).
//
// §3.1 layer 1 (presentation): the Confirm control carries `disabled` and
// aria-disabled="true" whenever confirm_enabled is false, and each affected
// field renders its visible re-checking state. These cues DISCLOSE the block;
// the block itself is layers 2 and 3.

import {
  attachConfirmation,
  confirmEnabled,
  editField,
  groundField,
  markRevalidating,
  setTypedPhrase,
  submitConfirm,
} from "./card_state.js";
import { capText } from "./text.js";
import { h, mountTree } from "./vdom.js";

const FIELD_NOTES = {
  dirty_unvalidated: "unvalidated — re-checking",
  revalidating: "re-checking…",
  awaiting_clarification: "needs a choice — Coxswain found matches",
  invalid: "could not be validated",
};

function fieldNoteText(state) {
  return FIELD_NOTES[state] !== undefined ? FIELD_NOTES[state] : "";
}

/**
 * Render §4.2's propose/confirm card as a virtual tree.
 *
 *   state          card_state instance (tier drives the Confirm row)
 *   restatement    NL restatement, primary reading (cap 400)
 *   warnings       [{kind, text}] advisory badges; never change friction
 *   literal_call   collapsed secondary detail ("Show the call")
 *   disclosure     one line, present ONLY when a clarification preceded
 *   field_overrides display-value overrides keyed by field name (tests)
 *   required_phrase irreversible only; rendered verbatim on the card (FR-3)
 */
export function renderProposeCard({
  state,
  restatement,
  warnings = [],
  literal_call = null,
  disclosure = null,
  field_overrides = {},
  required_phrase = null,
}) {
  if (state.tier === "irreversible") {
    if (typeof required_phrase !== "string" || required_phrase.length === 0) {
      throw new Error("irreversible cards render the required phrase verbatim (FR-3)");
    }
    attachConfirmation(state, { phrase: required_phrase });
  }

  const children = [
    h("header", { class: "cx-propose-head" },
      h("h3", { class: "cx-restatement" }, capText("nl_restatement", restatement)),
      h("span", { class: `cx-tier-badge cx-tier-${state.tier}` }, state.tier),
    ),
  ];

  if (warnings.length > 0) {
    children.push(
      h("ul", { class: "cx-warnings", "aria-label": "advisory warnings" },
        ...warnings.map((w) =>
          h("li", { class: "cx-warning-badge", "data-warning-kind": String(w.kind ?? "") },
            capText("warning_badge_text", typeof w.text === "string" ? w.text : String(w)),
          ),
        ),
      ),
    );
  }

  const fieldInputs = {};
  const fieldRows = state.fields.map((f) => {
    const inputId = `cx-field-${f.name}`;
    const display =
      field_overrides[f.name] !== undefined ? field_overrides[f.name] : f.value;
    const noteClass = `cx-field-note cx-note-${f.state}`;
    return h("div", { class: `cx-field-row cx-field-${f.state}`, "data-field-name": f.name },
      h("label", { for: inputId }, f.name),
      h("input", {
        id: inputId,
        type: "text",
        value: capText("edited_field_value", typeof display === "string" ? display : JSON.stringify(display)),
        "data-field-input": f.name,
      }),
      h("span", { class: noteClass, "data-field-note": f.name }, fieldNoteText(f.state)),
    );
  });
  children.push(h("div", { class: "cx-fields" }, ...fieldRows));

  if (typeof disclosure === "string" && disclosure.length > 0) {
    // FR-7: one-line disclosure when a clarification preceded this proposal.
    children.push(h("p", { class: "cx-disclosure" }, capText("nl_restatement", disclosure)));
  }

  if (literal_call !== null && typeof literal_call === "object") {
    const literal = JSON.stringify(literal_call, null, 2);
    children.push(
      h("details", { class: "cx-call-details" },
        h("summary", {}, "Show the call"),
        h("pre", { class: "cx-call-pre" }, capText("nl_restatement", literal)),
      ),
    );
  }

  const enabled = confirmEnabled(state);
  // NOTE: an EMPTY disabled attribute still disables; presence is what
  // matters, so the attribute is included only while blocked.
  const confirmAttrs = {
    type: "button",
    class: "cx-confirm",
    "data-action": "confirm",
    "aria-disabled": enabled ? "false" : "true",
  };
  if (!enabled) confirmAttrs.disabled = "disabled";
  const cancelAttrs = { type: "button", class: "cx-cancel", "data-action": "cancel" };

  if (state.tier === "irreversible") {
    children.push(
      h("div", { class: "cx-confirm-row cx-confirm-irreversible" },
        h("label", { for: "cx-typed-phrase" },
          `Type "${required_phrase}" to confirm:`),
        h("input", {
          id: "cx-typed-phrase",
          type: "text",
          class: "cx-typed-phrase",
          "data-action": "typed-phrase",
          autocomplete: "off",
          spellcheck: "false",
        }),
        h("button", confirmAttrs, "Confirm"),
        h("button", cancelAttrs, "Cancel"),
      ),
    );
  } else {
    children.push(
      h("div", { class: "cx-confirm-row" },
        h("button", cancelAttrs, "Cancel"),
        h("button", confirmAttrs, "Confirm"),
      ),
    );
  }

  return h("article", {
    class: "cx-card cx-propose-card",
    "data-tier": state.tier,
  }, ...children);
}

/**
 * Materialize + collect direct element references (no querySelector needed,
 * so the same path runs under bun's fake DOM and the real one).
 */
export function buildProposeCard(args, doc) {
  const tree = renderProposeCard(args);
  const root = mountTree(tree, doc);

  const refs = { root, fields: {}, notes: {}, confirm: null, cancel: null, typedPhrase: null };
  const walk = (node) => {
    const name = node.getAttribute ? node.getAttribute("data-field-input") : null;
    if (name) refs.fields[name] = node;
    const noteName = node.getAttribute ? node.getAttribute("data-field-note") : null;
    if (noteName) refs.notes[noteName] = node;
    const action = node.getAttribute ? node.getAttribute("data-action") : null;
    if (action === "confirm") refs.confirm = node;
    if (action === "cancel") refs.cancel = node;
    if (action === "typed-phrase") refs.typedPhrase = node;
    for (const child of node.childNodes || []) {
      if (child.tagName) walk(child);
    }
  };
  walk(root);
  return refs;
}

/** Refresh layer-1 presentation after any state change. */
export function refreshProposeCard(refs, state) {
  const enabled = confirmEnabled(state);
  if (refs.confirm) {
    if (enabled) refs.confirm.removeAttribute("disabled");
    else refs.confirm.setAttribute("disabled", "disabled");
    refs.confirm.setAttribute("aria-disabled", enabled ? "false" : "true");
  }
  for (const f of state.fields) {
    const rowNote = refs.notes[f.name];
    if (rowNote) {
      rowNote.textContent = fieldNoteText(f.state);
      rowNote.setAttribute("class", `cx-field-note cx-note-${f.state}`);
    }
  }
  return enabled;
}

/**
 * Wire events. Handlers delegate ALL decisions to card_state:
 *   emit      envelope sink (the praxis_coxswain channel)
 *   identity  {turn_id, session_id} minted at input capture
 *   reground  async (name, value) => {status, value?}; injected by the shell
 *   timers    {setTimeout, clearTimeout} injectable for tests
 * Blur flushes the edit debounce immediately (§4.7/H1).
 */
export function wireProposeCard(refs, state, { emit, identity, reground, timers } = {}) {
  const setTimeoutFn = (timers && timers.setTimeout) || globalThis.setTimeout.bind(globalThis);
  const clearTimeoutFn = (timers && timers.clearTimeout) || globalThis.clearTimeout.bind(globalThis);

  let debounceHandle = null;

  const scheduleReground = (name, value) => {
    if (debounceHandle !== null) clearTimeoutFn(debounceHandle);
    debounceHandle = setTimeoutFn(() => {
      debounceHandle = null;
      startReground(name, value);
    }, 300 /* EDIT_DEBOUNCE_MS, mirrored from timing.js to avoid a runtime dep here */);
  };

  const startReground = (name, value) => {
    markAndReground(state, name, value, reground, refs);
  };

  for (const [name, input] of Object.entries(refs.fields)) {
    if (!input || typeof input.addEventListener !== "function") continue;
    input.addEventListener("input", () => {
      editField(state, name, input.value);
      refreshProposeCard(refs, state);
      scheduleReground(name, input.value);
    });
    input.addEventListener("blur", () => {
      // Blur flushes immediately without waiting out the interval (§4.7).
      if (debounceHandle !== null) {
        clearTimeoutFn(debounceHandle);
        debounceHandle = null;
        startReground(name, input.value);
      }
    });
  }

  if (refs.typedPhrase && typeof refs.typedPhrase.addEventListener === "function") {
    refs.typedPhrase.addEventListener("input", () => {
      setTypedPhrase(state, refs.typedPhrase.value);
      refreshProposeCard(refs, state);
    });
  }

  if (refs.confirm && typeof refs.confirm.addEventListener === "function") {
    // The handler recomputes confirm_enabled and returns early WITHOUT
    // emitting when false -- §3.1 layer 2, catching fast clicks, stale-focus
    // Enter presses, and programmatic dispatches alike (AC-4 JS half).
    refs.confirm.addEventListener("click", () => {
      submitIfEnabled();
    });
    rootKeydownEnter(refs, () => submitIfEnabled());
  }

  function submitIfEnabled() {
    submitGuarded(state, emit, identity);
  }

  return { refresh: () => refreshProposeCard(refs, state), dispose() { if (debounceHandle !== null) clearTimeoutFn(debounceHandle); } };
}

// (All card_state helpers are imported statically at the top.)
function markAndReground(state, name, value, reground, refs) {
  markRevalidating(state, name);
  refreshProposeCard(refs, state);
  Promise.resolve()
    .then(() => reground(name, value))
    .then((outcome) => {
      groundField(state, name, outcome);
      refreshProposeCard(refs, state);
    })
    .catch(() => {
      // Fail closed: an unreachable re-grounding is invalid, never validated
      // (NFR-5 / REGROUND_TIMEOUT_MS expiry lands in the same place).
      groundField(state, name, { status: "invalid" });
      refreshProposeCard(refs, state);
    });
}

function submitGuarded(state, emit, identity) {
  submitConfirm(state, emit, identity);
}

function rootKeydownEnter(refs, onEnter) {
  if (refs.root && typeof refs.root.addEventListener === "function") {
    refs.root.addEventListener("keydown", (event) => {
      if (event && event.key === "Enter") onEnter();
    });
  }
}
