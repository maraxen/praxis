"""Local inference lane (transformers) -- LAZY, isolated heavy imports.

BLOCKED-RUN NOTE (surfaced, not faked): ``google/functiongemma-270m-it`` is a
GATED HF repo. Loading it requires (a) accepting Google's Gemma terms on the
hub, and (b) an ``HF_TOKEN`` env var carrying an access token with that
acceptance. Without both, :func:`make_generate` raises a loud, actionable
error; it must NEVER silently fall back to something that only looks like
inference.

Decode config per F4/D3: greedy (``do_sample=False``), max_new_tokens=128,
stop at ``<end_of_turn>`` and ``<start_function_response>``.
"""

from __future__ import annotations

from typing import Any, Callable, Mapping

__all__ = ["make_generate", "HF_REPO_ID", "GATED_REPO_HINT"]

HF_REPO_ID = "google/functiongemma-270m-it"
GATED_REPO_HINT = (
    f"{HF_REPO_ID} is a GATED Hugging Face repo: accept the Gemma terms at "
    f"https://huggingface.co/{HF_REPO_ID} with the account owning the token, "
    "then export HF_TOKEN=<token> and re-run with --model."
)

StopStrings = ("<end_of_turn>", "<start_function_response>")


def make_generate(
    model_id: str,
    *,
    revision: str = "main",
    device: str = "cpu",
    dtype: str | None = None,
    max_new_tokens: int = 128,
) -> Callable[[Mapping[str, Any]], str]:
    """Build a prompt->raw-output callable from transformers AutoModelForCausalLM.

    Heavy imports happen HERE, inside the function, so importing
    praxis_training.baseline_eval never drags torch in.
    """
    import os
    from pathlib import Path

    # A LOCAL checkpoint directory (P2.6 fine-tuned weights) needs no hub
    # access at all: load it offline and skip the gated-repo token guard.
    local_dir = Path(model_id).is_dir()
    # HF_HUB_OFFLINE=1 means "serve from the local cache, never touch the hub":
    # the gate is enforced by the hub, not by the cached files, so no token is
    # needed (a cache miss then fails loudly inside transformers).
    offline = os.environ.get("HF_HUB_OFFLINE", "").strip() in ("1", "true", "True", "yes")
    if (not local_dir and not offline
            and not os.environ.get("HF_TOKEN") and not os.environ.get("HUGGING_FACE_HUB_TOKEN")):
        # Fail BEFORE transformers tries the hub: the error must name the fix.
        raise RuntimeError(
            "HF_TOKEN/HUGGING_FACE_HUB_TOKEN not set (and HF_HUB_OFFLINE not set). " + GATED_REPO_HINT
        )

    import torch  # noqa: F401 - required by transformers model load
    from transformers import AutoModelForCausalLM, AutoTokenizer

    torch_dtype = None
    if dtype:
        torch_dtype = getattr(torch, dtype, None)
        if torch_dtype is None:
            raise ValueError(f"unknown torch dtype {dtype!r}")

    load_kwargs: dict[str, Any] = {"local_files_only": True} if local_dir else {"revision": revision}
    tokenizer = AutoTokenizer.from_pretrained(model_id, **load_kwargs)
    model = AutoModelForCausalLM.from_pretrained(
        model_id, torch_dtype=torch_dtype, **load_kwargs
    ).to(device)
    model.eval()

    def generate(native_row: Mapping[str, Any]) -> str:
        dev = next(m for m in native_row["messages"] if m["role"] == "developer")
        user = next(m for m in native_row["messages"] if m["role"] == "user")
        input_ids = tokenizer.apply_chat_template(
            [dev, user],
            tools=native_row["tools"],
            tokenize=True,
            add_generation_prompt=True,
            return_tensors="pt",
        ).to(device)
        with __import__("torch").no_grad():
            out = model.generate(
                input_ids,
                max_new_tokens=max_new_tokens,
                do_sample=False,
                num_beams=1,
            )
        # Slice off the prompt tokens so the parser sees ONLY generation.
        completion = out[0][input_ids.shape[1]:]
        text = tokenizer.decode(completion, skip_special_tokens=False)
        for stop in StopStrings:
            idx = text.find(stop)
            if idx != -1:
                text = text[:idx]
        return text

    # Recorded beside any dump: the dtype the weights actually run in (a
    # requested None resolves to whatever from_pretrained picked).
    generate.resolved_dtype = str(model.dtype)  # type: ignore[attr-defined]
    return generate
