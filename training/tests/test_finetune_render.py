"""P2.6 render: train prompts are byte/token-identical to the eval prompt and
the supervised completion parses back to the sidecar intent.

Needs the FunctionGemma tokenizer from the local HF cache (offline). Skips,
loudly, when it is not there -- it never downloads.
"""

import os
from pathlib import Path

import pytest

from praxis_training.baseline_eval.fgml_parser import parse_function_calls
from praxis_training.baseline_eval.local_infer import StopStrings
from praxis_training.baseline_eval.metrics import _normalize
from praxis_training.finetune import mixing
from praxis_training.finetune.render import render_pair, split_messages
from praxis_training.finetune.versions import BASE_MODEL, BASE_REVISION, CORPUS_REL, SIDECAR_REL

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def tokenizer():
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    transformers = pytest.importorskip("transformers")
    try:
        return transformers.AutoTokenizer.from_pretrained(BASE_MODEL, revision=BASE_REVISION)
    except Exception as exc:  # noqa: BLE001 - cache miss / gated
        pytest.skip(f"FunctionGemma tokenizer not in local HF cache: {exc}")


def _value_shape(row) -> str:
    """Coarse shape of the call's argument values: the round-trip test must
    cover every shape the template serialises differently (260902: the first
    25 rows in corpus order had no list-valued argument, and the parser's
    missing list decoding went unnoticed)."""
    shapes = set()
    for call in row.sidecar["calls"]:
        for v in call["params"].values():
            shapes.add("list" if isinstance(v, list) else "dict" if isinstance(v, dict)
                       else "bool" if isinstance(v, bool) else "num" if isinstance(v, (int, float)) else "str")
    return "+".join(sorted(shapes)) or "none"


@pytest.fixture(scope="module")
def sample_rows():
    rows = mixing.load_corpus(ROOT / CORPUS_REL, ROOT / SIDECAR_REL)
    per_shape: dict[str, list] = {}
    nl = []
    for r in rows:
        if r.supervision_kind == "tool_call":
            per_shape.setdefault(_value_shape(r), [])
            if len(per_shape[_value_shape(r)]) < 12:
                per_shape[_value_shape(r)].append(r)
        elif len(nl) < 25:
            nl.append(r)
    picked = [r for rs in per_shape.values() for r in rs]
    assert any("list" in _value_shape(r) for r in picked), "corpus has no list-valued argument rows?"
    return picked + nl


def _strip_stops(text: str) -> str:
    for stop in StopStrings:
        idx = text.find(stop)
        if idx != -1:
            text = text[:idx]
    return text


def test_prompt_matches_eval_lane_token_for_token(tokenizer, sample_rows):
    for row in sample_rows:
        pair = render_pair(tokenizer, row.native, row.record_id)
        dev, user, _ = split_messages(row.native)
        eval_ids = tokenizer.apply_chat_template(
            [dev, user], tools=row.native["tools"], tokenize=True, add_generation_prompt=True,
        )
        # Default special-token handling == what TRL's tokenize_fn does.
        train_ids = tokenizer(pair.prompt)["input_ids"]
        assert list(eval_ids) == list(train_ids), row.record_id
        assert train_ids.count(tokenizer.bos_token_id) == 1
        assert not pair.prompt.startswith(tokenizer.bos_token)
        assert pair.prompt.endswith("<start_of_turn>model\n")
        # And prompt+completion tokenizes as prompt ids followed by completion ids.
        full_ids = tokenizer(pair.prompt + pair.completion)["input_ids"]
        assert full_ids[: len(train_ids)] == train_ids, row.record_id


def test_completion_shapes_end_on_eval_stop_strings(tokenizer, sample_rows):
    for row in sample_rows:
        pair = render_pair(tokenizer, row.native, row.record_id)
        if row.supervision_kind == "tool_call":
            assert pair.completion.startswith("<start_function_call>call:"), row.record_id
            assert pair.completion.endswith("<end_function_call><start_function_response>"), row.record_id
        else:
            assert "<start_function_call>" not in pair.completion, row.record_id
            assert pair.completion.endswith("<end_of_turn>\n"), row.record_id


def test_tool_call_completion_round_trips_through_parser(tokenizer, sample_rows):
    """Labels must be what the eval parser expects: name + params equal after
    the same normalization the scorer applies."""
    checked = 0
    for row in sample_rows:
        if row.supervision_kind != "tool_call":
            continue
        pair = render_pair(tokenizer, row.native, row.record_id)
        parsed = parse_function_calls(_strip_stops(pair.completion))
        intent_calls = row.sidecar["calls"]
        assert len(parsed.calls) == len(intent_calls), row.record_id
        for got, want in zip(parsed.calls, intent_calls):
            assert got.name == want["name"], row.record_id
            assert _normalize(got.params) == _normalize(want["params"]), (row.record_id, got.params, want["params"])
        checked += 1
    assert checked >= 20
