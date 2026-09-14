"""Prompt/completion rendering for TRL, byte-identical to the eval prompt.

The eval lane (``baseline_eval.local_infer.make_generate``) builds its prompt
as ``apply_chat_template([developer, user], tools=row["tools"],
add_generation_prompt=True)``. Training MUST supervise a completion that
follows exactly that prompt, so this module renders the same two messages the
same way and takes the completion as the suffix of the full three-message
render (research §2b, Mobile-Actions notebook).

With FunctionGemma's template the completion is either
``<start_function_call>call:...<end_function_call><start_function_response>``
(tool-call rows; no end-of-turn after a call) or ``<text><end_of_turn>\\n``
(NL clarification rows) -- both end on a string the eval decoder stops at.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping, Sequence

__all__ = ["RenderedPair", "render_pair", "render_all", "split_messages"]


@dataclass(frozen=True)
class RenderedPair:
    record_id: str
    prompt: str
    completion: str


def split_messages(native_row: Mapping[str, Any]) -> tuple[dict, dict, dict]:
    """Return ``(developer, user, assistant)`` exactly as the eval lane picks them."""
    msgs = native_row["messages"]
    dev = next(m for m in msgs if m["role"] == "developer")
    user = next(m for m in msgs if m["role"] == "user")
    assistant = next(m for m in msgs if m["role"] == "assistant")
    return dev, user, assistant


def render_pair(tokenizer: Any, native_row: Mapping[str, Any], record_id: str) -> RenderedPair:
    dev, user, assistant = split_messages(native_row)
    tools = native_row["tools"]
    prompt = tokenizer.apply_chat_template(
        [dev, user], tools=tools, tokenize=False, add_generation_prompt=True,
    )
    full = tokenizer.apply_chat_template(
        [dev, user, assistant], tools=tools, tokenize=False, add_generation_prompt=False,
    )
    if not full.startswith(prompt):
        raise ValueError(f"{record_id}: full render does not extend the prompt render")
    completion = full[len(prompt):]
    if not completion:
        raise ValueError(f"{record_id}: empty completion")
    # TRL's prompt-completion path tokenizes the PROMPT STRING with the
    # tokenizer's default special-token handling (sft_trainer.tokenize_fn),
    # which prepends <bos>. The chat template already wrote a literal <bos>,
    # so strip it here: the tokenizer adds exactly one back, and the ids equal
    # the eval lane's apply_chat_template(tokenize=True) ids (pinned by test).
    bos = getattr(tokenizer, "bos_token", None)
    if not bos or not prompt.startswith(bos):
        raise ValueError(f"{record_id}: rendered prompt does not start with the bos token")
    prompt = prompt[len(bos):]
    return RenderedPair(record_id=record_id, prompt=prompt, completion=completion)


def render_all(tokenizer: Any, rows: Sequence[Any]) -> list[RenderedPair]:
    """``rows`` are :class:`mixing.CorpusRow`; order is preserved."""
    return [render_pair(tokenizer, r.native, r.record_id) for r in rows]
