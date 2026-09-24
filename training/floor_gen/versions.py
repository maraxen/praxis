"""Version pins + provenance-tag factory (AC-2.3.x: versions in provenance).

R4/D9: teacher outputs are cached content-addressed by
``(prompt_version, input_hash)`` with ``teacher_model_version`` recorded in
the manifest and on every row's provenance tags -- same inputs + same cache
=> byte-identical corpus, no re-calling of teachers.
"""

from __future__ import annotations

from typing import Final

__all__ = [
    "AGY_BIN",
    "AMBIGUITY_CLASSES",
    "GEMINI_BATCH_SIZE",
    "GEMINI_MODEL",
    "GENERATOR_VERSION",
    "SYNTH_SEED_VERSION",
    "PROMPT_VERSION_NATURAL",
    "VERB_PARAPHRASE_LEXICON",
    "MATRIX_VERSION",
    "PLR_SUBMODULE_SHA",
    "PROMPT_VERSION",
    "SUPERVISION_NL_CLARIFICATION",
    "SUPERVISION_TOOL_CALL",
    "TITANIX_BASE_URL",
    "TITANIX_MODEL",
    "provenance_tags",
]

#: Bump on ANY change to synthesis logic or value pools (part of the RNG
#: seed, so bumps deliberately reshuffle the floor corpus).
#: 0.2.0 (260828): execution-verify wiring fixes in synth.py -- dotted
#: <name>.<id> ref grammar (was flat <name>_<id>, ungroundable) and
#: resource-list/volume-list cardinality coordination (was independently
#: sampled, producing internally-inconsistent "clean" calls). See
#: _grounded_symbolic/_literal_value docstrings.
#: 0.2.1 (260902, task 260902_p26b_surface_data): post-synthesis coercion to
#: the declared scalar/ARRAY surface (DECLARED_ARRAY_PARAMS) so the 60 rows
#: assembly 0.1.3 excluded become valid. DELIBERATE EXCEPTION to "bumps
#: reshuffle": the RNG seed now uses SYNTH_SEED_VERSION (frozen at 0.2.0) so
#: every previously accepted row stays byte-identical and the pinned
#: 228-row eval split is untouched (training/floor_gen/data/
#: floor_0.2.0_accepted_digests.json is the alarm).
GENERATOR_VERSION: Final[str] = "0.2.1"

#: RNG seed component (synth._rng). Frozen at 0.2.0 on purpose: bumping it
#: reshuffles EVERY synthesized call and therefore the eval split; do that
#: only under a new pre-registration that re-measures the baseline.
SYNTH_SEED_VERSION: Final[str] = "0.2.0"

#: Bump on ANY change to prompt text (changes every cache key by construction).
PROMPT_VERSION: Final[str] = "p23_nlify_v1"

#: Natural-phrasing lane (task 260902_p26b_surface_data): a SECOND prompt
#: version over the SAME structured calls. Its text lives in
#: prompts.build_prompt_natural, separate from build_prompt so the base
#: prompt (and its 685 cached rows) never changes. Bump on ANY change to the
#: natural prompt text or to VERB_PARAPHRASE_LEXICON.
PROMPT_VERSION_NATURAL: Final[str] = "p23_nlify_v2_natural"

#: Out-of-surface natural lane (task 260903_p26c_oos_natural): a THIRD prompt
#: version whose text lives in prompts.build_prompt_natural_oos, separate so
#: neither the base prompt nor the in-surface natural prompt (and their cached
#: rows) ever changes. Bump on ANY change to the oos natural prompt text.
PROMPT_VERSION_NATURAL_OOS: Final[str] = "p23_nlify_v2_natural_oos"

#: Everyday phrasings per verb, offered to the teacher instead of the tool
#: name (P2.6 finding: golden eval says "pull / put / toss / copy", floor
#: training rows say "aspirate / dispense / discard_tips / stamp").
VERB_PARAPHRASE_LEXICON: Final[dict[str, tuple[str, ...]]] = {
    "aspirate": ("pull", "draw up", "suck up", "take up"),
    "dispense": ("put", "deliver", "drop", "add"),
    "transfer": ("move", "shuttle", "carry", "bring over"),
    "stamp": ("copy the plate", "replicate the plate", "stamp the layout"),
    "mix": ("mix", "stir", "pipette up and down"),
    "blow_out": ("blow out", "push out the last of the liquid"),
    "touch_tip": ("touch the tip off", "tap the tip on the wall"),
    "dispense_to_waste": ("dump into waste", "empty the tip into the waste", "throw the liquid away"),
    "pick_up_tips": ("grab tips", "load tips", "pick up fresh tips", "get tips"),
    "drop_tips": ("put the tips back", "return the tips", "drop the tips off"),
    "discard_tips": ("toss the tips", "throw away the tips", "bin the tips", "get rid of the tips"),
    "move_plate": ("place the plate", "put the plate", "shift the plate", "set the plate down"),
    "move_resource": ("carry", "transport", "bring", "relocate"),
    "move_lid": ("cover", "uncover", "put the lid", "take the lid"),
    "read_absorbance": ("measure absorbance", "read the OD", "scan absorbance"),
    "read_fluorescence": ("measure fluorescence", "read the signal", "scan fluorescence"),
    "read_luminescence": ("measure luminescence", "read the glow", "scan luminescence"),
    "set_temperature": ("warm", "heat", "bring to", "set the heater to"),
    "shake": ("shake", "agitate", "start shaking"),
    "stop_shaking": ("stop shaking", "stop the shaker", "halt the shaking"),
}

#: Matrix data revision (committed ambiguity_matrix.json).
#: 2 (260901): examples_per_cell 3 -> 15 (out-of-surface cells 20) so the
#: assembly split rule (k=floor(0.2n), n>=4) yields >=40 eval rows per
#: clarify class; cell set unchanged. Cache keys ignore this value, so the
#: first 3 rows per cell stay cache hits.
#: 3 (260903, task 260903_p26d_near_surface): six near-surface out-of-surface
#: cells APPENDED (``appended_in_matrix_version: "3"``); ``cells_round_robin``
#: keeps the original cells' order and iterates appended cells after them, so
#: every pre-existing ordinal / record id is unchanged (the eval pin depends on
#: it). Cache keys ignore this value and the base prompt text is unchanged, so
#: only the new cells' rows are teacher misses.
MATRIX_VERSION: Final[str] = "3"

#: Vendored PLR the namespace table is parity-pinned to (param_namespace.py).
PLR_SUBMODULE_SHA: Final[str] = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"

#: F6 amendment backend (b): titanix vLLM, OpenAI-compatible, verified live.
#: Kept for the smoke-scale lane; NOT used for the full-scale pass (260827
#: user-flagged blocker -- titanix-vllm-primary doesn't work at that scale).
TITANIX_BASE_URL: Final[str] = "http://localhost:8020/v1"
TITANIX_MODEL: Final[str] = "titanix-vllm-primary"

#: F6 amendment backend (c), 260827 (revised same day): Gemini 3.7 Flash via
#: the ``agy`` CLI (NOT the raw HTTP API -- no API key managed by this repo;
#: auth is agy's own). Chosen teacher for the full-scale floor_gen/
#: overlay_gen pass. Non-Gemma model -- D13's teacher-derivative gate
#: (gemma-license-deployment-gate.md §1) does NOT apply; F6's non-Gemma-
#: teacher assumption still holds. ``agy models`` lists effort-tiered IDs
#: (``-high``/``-medium``/``-low``); bare ``gemini-3.7-flash`` is not a valid
#: ``--model`` value. "medium" balances teacher-quality against the fixed
#: per-call overhead observed empirically (~16-22K tokens/call before any
#: content, heavily cache-discounted on repeat calls within a session).
GEMINI_MODEL: Final[str] = "gemini-3.7-flash-medium"
AGY_BIN: Final[str] = "agy"

#: Cells/items grouped into ONE ``agy`` invocation for the full-scale pass
#: (260827 user-directed: batch rather than issue ~800 individual calls).
#: Empirically, per-call fixed overhead (large cached system-prompt-ish
#: context, ~7-11s wall-clock) dominates at batch size 1; batching amortizes
#: it. 20 is a starting point, not measured against the real full corpus --
#: retune after the first live full-scale run.
GEMINI_BATCH_SIZE: Final[int] = 20

#: The four ambiguity classes (task deliverable 1).
AMBIGUITY_CLASSES: Final[tuple[str, ...]] = (
    "none",
    "missing-slot",
    "ambiguous-referent",
    "out-of-surface",
)

#: Supervision kinds per D7/D11.
SUPERVISION_TOOL_CALL: Final[str] = "tool_call"
SUPERVISION_NL_CLARIFICATION: Final[str] = "nl_clarification"


def provenance_tags(teacher_model_version: str) -> dict[str, str]:
    """The exact provenance tag set required on EVERY example (deliverable 5)."""
    return {
        "provenance": "coverage",
        "generator_version": GENERATOR_VERSION,
        "prompt_version": PROMPT_VERSION,
        "teacher_model_version": teacher_model_version,
    }
