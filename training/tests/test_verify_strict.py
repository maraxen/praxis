"""AC-2.2.1 STRICT-mode tests: anomalies must fail loudly.

The anomaly class: params outside the canonical namespace.  PLR's own
_check_args STRICT enforcement is inert for chatterbox backends (their
methods accept **backend_kwargs), so the harness mirrors the semantics --
see verify/dispatcher.py docstring.
"""

import asyncio
import json
from pathlib import Path

from pylabrobot.liquid_handling.strictness import Strictness, get_strictness

from verify import verify

EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def _load(name):
    data = json.loads((EXAMPLES / name).read_text())
    return data["call_sequence"], data["intent_record"], data.get("deck_layout")


def test_strict_anomaly_fails_verification():
    seq, intent, layout = _load("clean_transfer.json")
    anomalous = [dict(seq[0])]
    anomalous[0] = {
        "name": "pick_up_tips",
        "params": {"at": ["tip_rack.A1", "tip_rack.B1"], "grip_force": 42},
    }
    seq = [anomalous[0]] + list(seq[1:])
    r = asyncio.run(verify(seq, intent, layout=layout, strict=True))
    assert not r["passed"]
    assert r["error"] and "Extra arguments" in r["error"]
    exec_ok = next(c for c in r["checks"] if c["name"] == "execution_ok")
    assert not exec_ok["passed"]


def test_same_anomaly_passes_under_warn():
    """Control: identical sequence under WARN rides the **backend_kwargs
    channel and EXECUTES cleanly -- proving STRICT is what catches it.
    (The agreement layers still flag the unknown param; that is their job.)"""
    seq, intent, layout = _load("clean_transfer.json")
    seq = [{
        "name": "pick_up_tips",
        "params": {"at": ["tip_rack.A1", "tip_rack.B1"], "grip_force": 42},
    }] + list(seq[1:])
    r = asyncio.run(verify(seq, intent, layout=layout, strict=False))
    checks = {c["name"]: c for c in r["checks"]}
    assert r["error"] is None
    assert checks["execution_ok"]["passed"]
    # the anomaly is still visible at the agreement layer:
    assert not checks["intent_agreement_parse_layer"]["passed"]


def test_strictness_restored_even_on_failure():
    seq, intent, layout = _load("clean_transfer.json")
    bad = [{"name": "read_absorbance", "params": {"wavelength_nm": 450}}]
    asyncio.run(verify(bad, {"calls": [], "expected_effects": []}, layout=layout))
    assert get_strictness() is Strictness.WARN


def test_unsupported_backend_rejected():
    import pytest
    from verify.verifier import UnsupportedBackendError

    with pytest.raises(UnsupportedBackendError):
        asyncio.run(
            verify([{"name": "discard_tips", "params": {}}],
                   {"calls": [], "expected_effects": []},
                   backend="PlateReaderChatterboxBackend")
        )
