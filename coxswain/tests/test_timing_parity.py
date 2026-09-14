"""H1 / §4.7 timing parity: coxswain/src/coxswain/timing.py and
web-repl/shell/coxswain/timing.js must agree on all three constants, so a
one-sided edit fails here instead of silently desynchronizing the two sides.
"""

import re
from pathlib import Path

COXSWAIN_ROOT = Path(__file__).resolve().parents[1]
PY_TIMING = COXSWAIN_ROOT / "src" / "coxswain" / "timing.py"
JS_TIMING = COXSWAIN_ROOT.parent / "web-repl" / "shell" / "coxswain" / "timing.js"

EXPECTED_VALUES = {
    "EDIT_DEBOUNCE_MS": 300,
    "REGROUND_TIMEOUT_MS": 2000,
    "KERNEL_RTT_TIMEOUT_MS": 5000,
}


def _parse_python(text: str) -> dict[str, int]:
    found = {}
    pattern = re.compile(
        r"^([A-Z][A-Z0-9_]*)(?::\s*Final\[int\])?\s*=\s*(\d+)\s*$", re.MULTILINE
    )
    for name, value in pattern.findall(text):
        found[name] = int(value)
    return found


def _parse_javascript(text: str) -> dict[str, int]:
    found = {}
    pattern = re.compile(r"^export const ([A-Z][A-Z0-9_]*) = (\d+);", re.MULTILINE)
    for name, value in pattern.findall(text):
        found[name] = int(value)
    return found


def test_both_sides_define_exactly_the_three_constants() -> None:
    py_values = _parse_python(PY_TIMING.read_text())
    js_values = _parse_javascript(JS_TIMING.read_text())

    assert set(py_values) == set(EXPECTED_VALUES), f"python side: {py_values}"
    assert set(js_values) == set(EXPECTED_VALUES), f"js side: {js_values}"
    assert py_values == EXPECTED_VALUES
    assert js_values == EXPECTED_VALUES


def test_edit_debounce_and_reground_timeout_differ() -> None:
    """§4.7: 300 ms is a typing pause, 2 s is a work budget; collapsing them
    into one number is how a debounce silently becomes a timeout."""
    assert EXPECTED_VALUES["EDIT_DEBOUNCE_MS"] != EXPECTED_VALUES["REGROUND_TIMEOUT_MS"]
