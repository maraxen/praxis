// clarify_card.js -- §4.3's clarification card renderer (W4).
//
// Each exit payload kind renders DISTINCTLY (FR-7/W4):
//   clarify:disambiguate -> candidate picker (+ N5-B sections) + typed answer
//   clarify:not_found    -> rephrase prompt for the failed reference
//   clarify:incomplete   -> missing-field prompt with one input per field
//   clarify:precondition -> plain explanation; override affordance ONLY here,
//                           ONLY when payload.overridable is true (FR-10)
//   blocked:concurrent   -> plain explanation with NO affordances at all --
//                           no override, no answer controls, not even disabled
// ones.
//
// FR-8: BOTH answer paths -- clicks and typed text -- leave through ONE
// envelope kind ("clarify.answer"); neither carries any parse/model request.
// The kernel-side matcher (coxswain/clarify.py) resolves both against the
// already-fetched candidate set. These tests pin that contract.

import { describe, expect, test } from "bun:test";

import {
  buildClarifyCard,
  renderClarifyCard,
} from "../clarify_card.js";
import { mountTree } from "../vdom.js";
import { createFakeDocument } from "./dom_stub.js";

const doc = createFakeDocument();

const CANDIDATES = [
  { name: "PLT_CAR_L5AC_A00", resource_type: "plate_carrier", position: "rails 7" },
  { name: "PLT_CAR_P3AC_A00", resource_type: "plate_carrier", position: "rails 13" },
];

function disambiguateArgs(overrides = {}) {
  return {
    disposition: "clarify:disambiguate",
    slot: "source",
    candidates: CANDIDATES,
    categorization: {
      matches: ["PLT_CAR_L5AC_A00 on rails 7", "PLT_CAR_P3AC_A00 on rails 13"],
      conflicts: ["They occupy different locations."],
      omissions: ["You did not say which source."],
    },
    ...overrides,
  };
}

function makeCard(args) {
  const refs = buildClarifyCard(renderClarifyCard(args), doc);
  const emitted = [];
  refs.wire({
    emit: (envelope) => emitted.push(envelope),
    identity: { turn_id: "cx-1-abc123", session_id: "sess-1" },
  });
  return { refs, emitted };
}

describe("renderClarifyCard: disambiguate", () => {
  test("renders candidate picker buttons in as-given order with labels", () => {
    const { refs } = makeCard(disambiguateArgs());
    expect(refs.pickButtons.length).toBe(2);
    expect(refs.pickButtons[0].textContent).toContain("PLT_CAR_L5AC_A00");
    expect(refs.pickButtons[1].getAttribute("data-candidate-index")).toBe("1");
  });

  test("renders N5-B Matches/Conflicts/Omissions sections when provided", () => {
    const root = mountTree(renderClarifyCard(disambiguateArgs()), doc);
    expect(root.textContent).toContain("Matches");
    expect(root.textContent).toContain("Conflicts");
    expect(root.textContent).toContain("Omissions");
    expect(root.textContent).toContain("You did not say which source.");
  });

  test("click path emits exactly ONE clarify.answer naming slot + index, nothing else", () => {
    const { refs, emitted } = makeCard(disambiguateArgs());
    refs.pickButtons[1].onclick();
    expect(emitted.length).toBe(1);
    expect(emitted[0].kind).toBe("clarify.answer");
    expect(emitted[0].turn_id).toBe("cx-1-abc123");
    expect(emitted[0].session_id).toBe("sess-1");
    expect(emitted[0].payload).toEqual({ slot: "source", answer: null, candidate_index: 1 });
  });

  test("typed path emits the SAME clarify.answer kind with the raw text", () => {
    const { refs, emitted } = makeCard(disambiguateArgs());
    refs.answerInput.value = "rail 13";
    refs.submitButton.onclick();
    expect(emitted.length).toBe(1);
    expect(emitted[0].kind).toBe("clarify.answer");
    expect(emitted[0].payload).toEqual({ slot: "source", answer: "rail 13", candidate_index: null });
  });

  test("empty typed answer emits NOTHING (never a guess)", () => {
    const { refs, emitted } = makeCard(disambiguateArgs());
    refs.answerInput.value = "   ";
    refs.submitButton.onclick();
    expect(emitted.length).toBe(0);
  });

  test("FR-8: no parse or model-request kind is ever emitted by this card", () => {
    const { refs, emitted } = makeCard(disambiguateArgs());
    refs.pickButtons[0].onclick();
    refs.answerInput.value = "rails 7";
    refs.submitButton.onclick();
    for (const e of emitted) {
      expect(e.kind).toBe("clarify.answer");
      expect(e.kind.startsWith("coxswain.parse")).toBe(false);
    }
  });

  test("NFR-7: a hostile candidate label renders as TEXT with zero element children", () => {
    const hostile = [{ name: '<img src=x onerror=alert(1)>', position: null }];
    const root = mountTree(
      renderClarifyCard(disambiguateArgs({ candidates: hostile })),
      doc,
    );
    const buttons = [];
    const walk = (n) => {
      if (
        n.getAttribute &&
        n.getAttribute("data-action") === "pick"
      )
        buttons.push(n);
      (n.children || []).forEach(walk);
    };
    walk(root);
    expect(buttons.length).toBe(1);
    expect(buttons[0].children.length).toBe(0);
    expect(buttons[0].textContent).toBe("<img src=x onerror=alert(1)>");
  });
});

describe("renderClarifyCard: not_found", () => {
  test("renders the kernel message and a rephrase input", () => {
    const { refs } = makeCard({
      disposition: "clarify:not_found",
      slot: "source",
      message: 'no plate matching "lane C"',
    });
    expect(refs.root.textContent).toContain('no plate matching "lane C"');
    expect(refs.answerInput).not.toBeNull();
  });

  test("typed rephrase emits clarify.answer carrying the new reference", () => {
    const { refs, emitted } = makeCard({
      disposition: "clarify:not_found",
      slot: "source",
      message: "no plate matching",
    });
    refs.answerInput.value = "Plate A";
    refs.submitButton.onclick();
    expect(emitted.length).toBe(1);
    expect(emitted[0].payload).toEqual({ slot: "source", answer: "Plate A", candidate_index: null });
  });

  test("no candidate picker exists for a not-found exit", () => {
    const { refs } = makeCard({
      disposition: "clarify:not_found",
      slot: "source",
      message: "x",
    });
    expect(refs.pickButtons.length).toBe(0);
  });
});

describe("renderClarifyCard: incomplete", () => {
  test("one labelled input per missing field", () => {
    const { refs } = makeCard({
      disposition: "clarify:incomplete",
      missing_fields: ["target", "volume_ul"],
    });
    expect(Object.keys(refs.fieldInputs).sort()).toEqual(["target", "volume_ul"]);
  });

  test("submit emits clarify.answer with supplies keyed by field", () => {
    const { refs, emitted } = makeCard({
      disposition: "clarify:incomplete",
      missing_fields: ["target", "volume_ul"],
    });
    refs.fieldInputs.target.value = "B3";
    refs.submitButton.onclick();
    expect(emitted.length).toBe(1);
    expect(emitted[0].kind).toBe("clarify.answer");
    expect(emitted[0].payload).toEqual({
      supplies: { target: "B3", volume_ul: "" },
    });
  });

  test("incomplete cards render NO override affordance (FR-10)", () => {
    const { refs } = makeCard({
      disposition: "clarify:incomplete",
      missing_fields: ["target"],
    });
    expect(refs.overrideButton).toBeNull();
    expect(refs.justificationInput).toBeNull();
  });
});

describe("renderClarifyCard: precondition", () => {
  function preconditionArgs(overrides = {}) {
    return {
      disposition: "clarify:precondition",
      unmet_preconditions: ["tips_not_loaded"],
      overridable: true,
      override_prompt: "operator asserts the listed preconditions are met by other means",
      ...overrides,
    };
  }

  test("renders each unmet precondition and the override affordance when overridable", () => {
    const { refs } = makeCard(preconditionArgs());
    expect(refs.root.textContent).toContain("tips_not_loaded");
    expect(refs.justificationInput).not.toBeNull();
    expect(refs.overrideButton).not.toBeNull();
    expect(refs.root.textContent).toContain(
      "operator asserts the listed preconditions are met by other means"
    );
  });

  test("override click requires non-empty justification and emits once", () => {
    const { refs, emitted } = makeCard(preconditionArgs());
    refs.overrideButton.onclick(); // empty justification -> nothing
    expect(emitted.length).toBe(0);
    refs.justificationInput.value = "tips were visually confirmed";
    refs.overrideButton.onclick();
    expect(emitted.length).toBe(1);
    expect(emitted[0].kind).toBe("coxswain.override_request");
    expect(emitted[0].payload).toEqual({ justification: "tips were visually confirmed" });
  });

  test("overridable:false renders NO override affordance at all (not a disabled one)", () => {
    const { refs } = makeCard(preconditionArgs({ overridable: false }));
    expect(refs.overrideButton).toBeNull();
    expect(refs.justificationInput).toBeNull();
  });

  test("precondition cards render NO answer controls (cue-3 exits are not answered)", () => {
    const { refs } = makeCard(preconditionArgs());
    expect(refs.answerInput).toBeNull();
    expect(refs.pickButtons.length).toBe(0);
  });
});

describe("renderClarifyCard: blocked:concurrent", () => {
  function blockedArgs(overrides = {}) {
    return {
      disposition: "blocked:concurrent",
      concurrency_active: true,
      ...overrides,
    };
  }

  test("renders a plain explanation naming the block", () => {
    const { refs } = makeCard(blockedArgs());
    expect(refs.root.getAttribute("data-disposition")).toBe("blocked:concurrent");
    expect(refs.root.textContent.toLowerCase()).toContain("another protocol run");
  });

  test("NO affordances anywhere: no override, no answers, not even disabled ones", () => {
    const { refs } = makeCard(blockedArgs());
    expect(refs.overrideButton).toBeNull();
    expect(refs.justificationInput).toBeNull();
    expect(refs.answerInput).toBeNull();
    expect(refs.submitButton).toBeNull();
    expect(refs.pickButtons.length).toBe(0);
  });

  test("wiring a blocked card provides no emitters that could fire", () => {
    const { refs, emitted } = makeCard(blockedArgs());
    // There is literally nothing clickable wired: the card exposes no handlers.
    expect(refs.clickableCount).toBe(0);
    expect(emitted.length).toBe(0);
  });
});

describe("renderClarifyCard: input validation", () => {
  test("unknown disposition throws loudly", () => {
    expect(() =>
      renderClarifyCard({ disposition: "clarify:bogus" })
    ).toThrow();
  });

  test("disambiguate without candidates throws loudly", () => {
    expect(() => renderClarifyCard(disambiguateArgs({ candidates: [] }))).toThrow();
  });
});
