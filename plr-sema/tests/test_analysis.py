"""plr_sema.analyze (spec 261002 §5)."""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

pytest.importorskip("libcst")
pytest.importorskip("pydantic")

from plr_sema import Verdict  # noqa: E402
from plr_sema.analysis import Analyzed, NotAnalyzed, NotAnalyzedReason, analyze  # noqa: E402
from plr_sema.contracts import ENV_VAR, load_contracts  # noqa: E402

PKG = Path(__file__).resolve().parents[1]
FIX = PKG / "eval" / "fixtures" / "regions"
WILL_FAIL_SRC = (FIX / "for_pickup_no_drop_raises.py").read_text(encoding="utf-8")
CLEAN_SRC = (FIX / "straightline_clean.py").read_text(encoding="utf-8")


@pytest.fixture(scope="session")
def contracts():
    return load_contracts(PKG / "data" / "derived_contracts.json")


def test_will_fail_fixture_is_analyzed_as_will_fail(contracts) -> None:
    out = analyze(WILL_FAIL_SRC, "protocol", contracts=contracts)
    assert isinstance(out, Analyzed)
    assert out.report.verdict is Verdict.WILL_FAIL
    assert out.function_name == "protocol"
    assert all(isinstance(v, int) and v > 0 for v in out.op_lines.values())
    assert {f.operation_id for f in out.report.findings} <= set(out.op_lines)


def test_clean_fixture_has_no_will_fail(contracts) -> None:
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, Analyzed)
    assert out.report.verdict is not Verdict.WILL_FAIL


def test_function_name_defaults_to_the_only_top_level_def(contracts) -> None:
    out = analyze(CLEAN_SRC, contracts=contracts)
    assert isinstance(out, Analyzed) and out.function_name == "protocol"


@pytest.mark.parametrize(
    "source,fn,reason",
    [
        ("def f(:\n", "f", NotAnalyzedReason.SYNTAX_ERROR),
        ("import os\n", None, NotAnalyzedReason.FUNCTION_NOT_FOUND),
        ("def a(): pass\n", "b", NotAnalyzedReason.FUNCTION_NOT_FOUND),
        ("def a(): pass\ndef b(): pass\n", None, NotAnalyzedReason.AMBIGUOUS_FUNCTION),
        ("def a(): pass\ndef a(): pass\n", "a", NotAnalyzedReason.AMBIGUOUS_FUNCTION),
        ("", None, NotAnalyzedReason.FUNCTION_NOT_FOUND),
    ],
    ids=["syntax", "no-defs", "wrong-name", "two-defs-no-name", "duplicate-name", "empty"],
)
def test_not_analyzed_reasons(contracts, source, fn, reason) -> None:
    out = analyze(source, fn, contracts=contracts)
    assert isinstance(out, NotAnalyzed), out
    assert out.reason is reason
    assert out.detail


def test_nested_def_with_the_target_name_is_not_picked(contracts) -> None:
    src = "def outer():\n    def protocol():\n        pass\n"
    out = analyze(src, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.FUNCTION_NOT_FOUND


def test_extractor_crash_is_extract_failed(contracts, monkeypatch) -> None:
    import plr_sema.extract.computation_graph_extractor as ex

    def boom(*a, **k):
        raise RuntimeError("synthetic extractor crash")

    monkeypatch.setattr(ex, "extract_graph_from_function", boom)
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.EXTRACT_FAILED
    assert "RuntimeError" in out.detail


def test_odd_but_valid_calls_never_raise(contracts) -> None:
    src = (
        "async def protocol(lh, plate, args, kw):\n"
        "    await lh.aspirate(*args, **kw)\n"
        "    await (lambda: lh)().dispense(plate['A1'], [10])\n"
        "    getattr(lh, 'drop_tips')()\n"
    )
    out = analyze(src, "protocol", contracts=contracts)
    assert isinstance(out, (Analyzed, NotAnalyzed))
    if isinstance(out, NotAnalyzed):
        assert out.reason in (NotAnalyzedReason.EXTRACT_FAILED, NotAnalyzedReason.CHECK_FAILED)


def test_check_crash_is_check_failed(contracts, monkeypatch) -> None:
    import plr_sema.analysis as an

    def boom(*a, **k):
        raise KeyError("synthetic check crash")

    monkeypatch.setattr(an, "check_graph", boom)
    out = analyze(CLEAN_SRC, "protocol", contracts=contracts)
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CHECK_FAILED


def test_contracts_unavailable(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv(ENV_VAR, "none")
    out = analyze(CLEAN_SRC, "protocol")
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CONTRACTS_UNAVAILABLE
    bad = tmp_path / "c.json.gz"
    bad.write_bytes(b"\x1f\x8b\x08\x00truncated")
    monkeypatch.setenv(ENV_VAR, str(bad))
    out = analyze(CLEAN_SRC, "protocol")
    assert isinstance(out, NotAnalyzed) and out.reason is NotAnalyzedReason.CONTRACTS_UNAVAILABLE


def test_extractor_unavailable_on_a_base_install() -> None:
    code = (
        "import sys\n"
        "sys.modules['libcst'] = None\n"  # makes `import libcst` raise ImportError
        "import plr_sema\n"
        "out = plr_sema.analyze('def f(): pass\\n', 'f')\n"
        "print(type(out).__name__, out.reason.value)\n"
    )
    r = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True)
    assert r.returncode == 0, r.stderr
    assert r.stdout.split() == ["NotAnalyzed", "extractor_unavailable"]


def test_lazy_top_level_names() -> None:
    import plr_sema

    assert plr_sema.analyze is analyze
    assert plr_sema.NotAnalyzedReason is NotAnalyzedReason


# ---- VerdictKey -------------------------------------------------------------

TWO_FNS = (
    "def protocol(lh, plate):\n"
    "    lh.aspirate(plate['A1'], [10])\n"
    "\n"
    "\n"
    "def helper():\n"
    "    return 1\n"
)


def _key(src: str, contracts, fn: str = "protocol"):
    out = analyze(src, fn, contracts=contracts)
    assert isinstance(out, Analyzed), out
    return out.key


def test_key_is_stable(contracts) -> None:
    assert _key(TWO_FNS, contracts) == _key(TWO_FNS, contracts)


def test_key_changes_when_the_function_changes(contracts) -> None:
    edited = TWO_FNS.replace("[10]", "[20]")
    assert _key(TWO_FNS, contracts).source_sha256 != _key(edited, contracts).source_sha256


def test_key_ignores_sibling_functions_and_spacing(contracts) -> None:
    sibling = TWO_FNS.replace("return 1", "return 2")
    spaced = "# header comment\n\n\n" + TWO_FNS.replace("\n\n\ndef helper", "\n\n\n\n# note\ndef helper")
    base = _key(TWO_FNS, contracts).source_sha256
    assert _key(sibling, contracts).source_sha256 == base
    assert _key(spaced, contracts).source_sha256 == base


def test_key_same_for_json_and_gz_contracts(contracts, tmp_path) -> None:
    from plr_sema.contracts import build_gz

    gz = load_contracts(build_gz(PKG / "data" / "derived_contracts.json", tmp_path / "c.json.gz"))
    assert _key(TWO_FNS, contracts) == _key(TWO_FNS, gz)


def test_key_string_form(contracts) -> None:
    k = _key(TWO_FNS, contracts)
    assert k.as_str() == f"v{k.schema_version}:{k.source_sha256}:{k.contracts_sha256}:{k.analyzer_sha256}"
    assert all(len(h) == 64 for h in (k.source_sha256, k.contracts_sha256, k.analyzer_sha256))


def test_key_ignores_comments_and_blank_lines_directly_above_the_function(contracts) -> None:
    # A comment at the very top of a file is the module header, not the def's
    # leading_lines; put the comment after a statement so it attaches to the def.
    plain = "import os\n" + TWO_FNS
    commented = "import os\n\n\n# the protocol under test\n\n" + TWO_FNS
    assert _key(plain, contracts).source_sha256 == _key(commented, contracts).source_sha256
