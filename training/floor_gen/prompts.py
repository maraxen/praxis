"""Teacher NL-ification prompt builder (task deliverable 3).

Pure function of (example, declarations). The FULL prompt text -- system +
user -- is versioned by ``PROMPT_VERSION``; any text change bumps that
constant, which changes every cache key, which is exactly how R4/D9
idempotency stays honest.

The user block embeds the FunctionGemma tool declarations rendered from the
namespace table (juror finding 6a) so the teacher sees the same tools[] the
training rows will carry, plus the pinned value-format conventions (finding
6b) phrased for natural language.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Final

from floor_gen.declarations import render_declarations
from floor_gen.synth import SynthExample
from floor_gen.value_formats import VALUE_FORMAT_CONVENTIONS
from floor_gen.versions import PROMPT_VERSION_NATURAL_OOS, PROMPT_VERSION, PROMPT_VERSION_NATURAL, VERB_PARAPHRASE_LEXICON

__all__ = [
    "build_prompt",
    "build_prompt_natural",
    "build_prompt_natural_oos",
    "compute_input_hash",
    "response_shape_instructions",
]


#: Shared contract for BOTH backends: the assistant-under-test must reply with
#: EXACTLY one minified JSON object on a single line.
_RESPONSE_SHAPE: Final[str] = (
    "Respond with EXACTLY ONE JSON object and nothing else -- no markdown, no "
    "code fences, no commentary. Shape:\n"
    '{"utterance": "<the user utterance>", "clarification": <string or null>}\n'
    '"utterance": one single-turn user message, quoted speech only.\n'
    '"clarification": null unless instructions below require an assistant '
    "clarification turn."
)


def response_shape_instructions() -> str:
    return _RESPONSE_SHAPE


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def compute_input_hash(payload: dict[str, Any]) -> str:
    """input_hash over the SEMANTIC inputs (version-independent); the cache
    composes it with prompt_version into the full key."""
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


_CLASS_INSTRUCTIONS: Final[dict[str, str]] = {
    "none": (
        "Write a natural, specific user utterance asking for EXACTLY this call. "
        "Mention every parameter: quantities as '<n> microliters', locations using "
        "the given names/positions verbatim."
    ),
    "missing-slot": (
        "Write a natural user utterance that requests this call but OMITS the "
        "parameter '{missing_param}' entirely -- never mention it, never hint at a "
        "value for it. All other parameters MUST appear naturally."
    ),
    "ambiguous-referent": (
        "Write a natural user utterance requesting this call, but refer to the "
        "'{slot_param}' argument ONLY with a vague phrase such as '{vague_hint}' -- "
        "NEVER its concrete id. All other parameters appear normally and concretely."
    ),
    "out-of-surface": (
        "The request below is OUTSIDE the supported tool surface. Write (1) a "
        "natural user utterance asking for it, and (2) 'clarification': a short "
        "friendly assistant reply that says the request is not something the lab "
        "copilot can do, and offers the closest supported alternative from the "
        "tool list if one exists. Do NOT invent any tool call."
    ),
}


def build_prompt(example: SynthExample) -> dict[str, str]:
    """Build {system, user, input_hash} for one example."""
    cell = example.cell
    cls = cell.ambiguity_class

    if cls == "out-of-surface":
        supported = ", ".join(sorted(d["name"] for d in render_declarations()))
        user = "\n".join(
            [
                f"Task context (prompt_version={PROMPT_VERSION}, class=out-of-surface):",
                f"Off-surface request seed: {cell.off_surface_request}",
                f"Supported tools (for the alternative offer): {supported}",
                _CLASS_INSTRUCTIONS["out-of-surface"],
                _RESPONSE_SHAPE,
            ]
        )
    else:
        assert cell.verb is not None
        declarations = render_declarations([cell.verb])
        instruction = _CLASS_INSTRUCTIONS[cls]
        if cls == "missing-slot":
            assert cell.missing_param is not None
            instruction = instruction.replace("{missing_param}", cell.missing_param)
        if cls == "ambiguous-referent":
            vague = "the plate"
            instruction = instruction.replace("{slot_param}", cell.slot_param or "?").replace(
                "{vague_hint}", vague
            )
        calls_block = canonical_json({"calls": example.structured_calls})
        formats_block = json.dumps(VALUE_FORMAT_CONVENTIONS, sort_keys=True)
        user = "\n".join(
            [
                f"Task context (prompt_version={PROMPT_VERSION}, cell={cell.cell_id}):",
                "Tool declaration for this row (FunctionGemma shape):",
                canonical_json(declarations[0]),
                "Structured call(s) to NL-ify (corpus-B keyword style kwargs):",
                calls_block,
                "Value-format conventions (volumes uL floats; wells A1-style):",
                formats_block,
                "Instruction:",
                instruction,
                _RESPONSE_SHAPE,
            ]
        )

    system = (
        "You are a data-generation teacher for a liquid-handling lab copilot "
        "(FunctionGemma training corpus, coverage floor). You convert structured "
        "tool calls into realistic single-turn user utterances under exact "
        "ambiguity-class constraints. You follow the output contract literally."
    )
    payload = {
        "prompt_version": PROMPT_VERSION,
        "cell_id": cell.cell_id,
        "example_index": example.index,
        "ambiguity_class": cls,
        "structured_calls": example.structured_calls,
    }
    return {"system": system, "user": user, "input_hash": compute_input_hash(payload)}


# ---------------------------------------------------------------------------
# Natural-phrasing lane (task 260902_p26b_surface_data) -- SEPARATE builder so
# the base prompt text above (and every cached row keyed on PROMPT_VERSION)
# never changes. Same declaration + structured-call blocks; different
# instruction: natural location phrasing and everyday verbs, never the raw
# identifiers or the tool name.
# ---------------------------------------------------------------------------

_NATURAL_LOCATION_RULE: Final[str] = (
    "LOCATION PHRASING: never write a raw identifier (no underscores, no dotted "
    "well ids, no brackets). Say locations the way a lab scientist speaks: "
    "'well D1 of plate 1', 'plate 1, D1', 'the C5 spot on the tip rack', "
    "'reservoir 1', 'the hotel stack', 'the scale station', 'lid 2'. Keep the "
    "exact well letter+number and the exact plate/reservoir number so the "
    "location is still unambiguous."
)
_NATURAL_VERB_RULE: Final[str] = (
    "ACTION PHRASING: never write the tool name '{verb}' or its words. Describe "
    "the action with an everyday phrasing such as: {lexicon}."
)
_NATURAL_CLASS: Final[dict[str, str]] = {
    "none": (
        "Write a natural, specific user utterance asking for EXACTLY this call. "
        "Mention every parameter: quantities as '<n> microliters'."
    ),
    "missing-slot": (
        "Write a natural user utterance that requests this call but OMITS the "
        "parameter '{missing_param}' entirely -- never mention it, never hint at a "
        "value for it. All other parameters MUST appear naturally."
    ),
    "ambiguous-referent": (
        "Write a natural user utterance requesting this call, but refer to the "
        "'{slot_param}' argument ONLY with the vague phrase '{vague_hint}' (use it "
        "verbatim) -- NEVER a concrete id. All other parameters appear naturally."
    ),
}


#: The natural lane's system prompt (byte-identical to what produced every
#: cached p23_nlify_v2_natural row; prewarm_prompts assumes one system string
#: per chunk, so the oos lane reuses it verbatim).
_NATURAL_SYSTEM: Final[str] = (
    "You are a data-generation teacher for a liquid-handling lab copilot "
    "(FunctionGemma training corpus, natural-phrasing lane). You convert "
    "structured tool calls into realistic single-turn user utterances that "
    "sound like a scientist talking, under exact ambiguity-class constraints. "
    "You follow the output contract literally."
)

# Out-of-surface natural lane (task 260903_p26c_oos_natural). No structured
# call to NL-ify: the seed is the cell's off-surface request plus the base
# row's own utterance; the assistant reply is COPIED from the base row by the
# lane, so the teacher is asked for the utterance only.
_NATURAL_OOS_INSTRUCTION: Final[str] = (
    "The original request below is OUTSIDE the supported tool surface (the "
    "copilot will decline it). Rewrite it as the SAME request, phrased the way a "
    "scientist casually asks a colleague in the lab. Keep every concrete detail "
    "of the original (wells, plates, volumes, temperatures, speeds, counts, "
    "timings) and keep it asking for the same off-surface thing -- do NOT turn "
    "it into something the copilot could do instead, and do NOT name any tool. "
    "Vary the sentence shape (a question, an imperative, or a 'could you ...' "
    "ask). Set 'clarification' to null: the assistant reply is supplied "
    "separately."
)


def build_prompt_natural_oos(example: SynthExample, base_utterance: str) -> dict[str, str]:
    """Natural-phrasing prompt for an OUT-OF-SURFACE example (never in-surface)."""
    cell = example.cell
    if cell.ambiguity_class != "out-of-surface":
        raise ValueError("oos natural lane is for out-of-surface cells only")
    user = "\n".join(
        [
            f"Task context (prompt_version={PROMPT_VERSION_NATURAL_OOS}, cell={cell.cell_id}, class=out-of-surface):",
            f"Off-surface request seed: {cell.off_surface_request}",
            f"Original request: {base_utterance}",
            "Instruction:",
            _NATURAL_OOS_INSTRUCTION,
            _NATURAL_LOCATION_RULE,
            _RESPONSE_SHAPE,
        ]
    )
    payload = {
        "prompt_version": PROMPT_VERSION_NATURAL_OOS,
        "cell_id": cell.cell_id,
        "example_index": example.index,
        "ambiguity_class": cell.ambiguity_class,
        "base_utterance": base_utterance,
    }
    return {"system": _NATURAL_SYSTEM, "user": user, "input_hash": compute_input_hash(payload)}


def _vague_hint_from_call(example: SynthExample) -> str:
    cell = example.cell
    if cell.slot_param and example.schema_calls:
        value = example.schema_calls[0]["params"].get(cell.slot_param)
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return value
    return "the plate"


def build_prompt_natural(example: SynthExample) -> dict[str, str]:
    """Natural-phrasing prompt for an IN-SURFACE example (never out-of-surface)."""
    cell = example.cell
    cls = cell.ambiguity_class
    if cls == "out-of-surface":
        raise ValueError("natural lane has no out-of-surface variants")
    assert cell.verb is not None
    declarations = render_declarations([cell.verb])
    instruction = _NATURAL_CLASS[cls]
    if cls == "missing-slot":
        assert cell.missing_param is not None
        instruction = instruction.replace("{missing_param}", cell.missing_param)
    if cls == "ambiguous-referent":
        instruction = instruction.replace("{slot_param}", cell.slot_param or "?").replace(
            "{vague_hint}", _vague_hint_from_call(example)
        )
    lexicon = ", ".join(f"'{p}'" for p in VERB_PARAPHRASE_LEXICON.get(cell.verb, ("do it",)))
    verb_rule = _NATURAL_VERB_RULE.replace("{verb}", cell.verb).replace("{lexicon}", lexicon)
    calls_block = canonical_json({"calls": example.structured_calls})
    formats_block = json.dumps(VALUE_FORMAT_CONVENTIONS, sort_keys=True)
    user = "\n".join(
        [
            f"Task context (prompt_version={PROMPT_VERSION_NATURAL}, cell={cell.cell_id}):",
            "Tool declaration for this row (FunctionGemma shape):",
            canonical_json(declarations[0]),
            "Structured call(s) to NL-ify (corpus-B keyword style kwargs):",
            calls_block,
            "Value-format conventions (volumes uL floats; wells A1-style):",
            formats_block,
            "Instruction:",
            instruction,
            _NATURAL_LOCATION_RULE,
            verb_rule,
            _RESPONSE_SHAPE,
        ]
    )
    system = _NATURAL_SYSTEM
    payload = {
        "prompt_version": PROMPT_VERSION_NATURAL,
        "cell_id": cell.cell_id,
        "example_index": example.index,
        "ambiguity_class": cls,
        "structured_calls": example.structured_calls,
    }
    return {"system": system, "user": user, "input_hash": compute_input_hash(payload)}
