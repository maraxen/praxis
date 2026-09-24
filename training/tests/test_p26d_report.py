"""P2.6d decision tables: the P2.6c checks re-labelled (A3 control, A4 new) plus
the near-surface probe check with its ceiling rule (task 260903_p26d_near_surface)."""

import json
from pathlib import Path

import pytest
from praxis_training.finetune.p26d_report import NEAR_PROBE_CEILING, decision_tables, near_probe_check, render_markdown

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "training" / "eval" / "reports"


def _probe(value: float, n: int = 24, tripwire: int = 0) -> dict:
    s = round(value * n)
    return {"exact_match_accuracy": {"value": s / n, "successes": s, "n": n, "wilson95": [0.0, 1.0]},
            "tripwire_out_of_surface_tool_calls": tripwire}


def test_near_probe_delta_rule_on_known_inputs():
    c = near_probe_check(_probe(0.5, tripwire=12), _probe(0.75, tripwire=6))
    assert c["holds"] is True and c["control_at_ceiling"] is False and c["delta"] == pytest.approx(0.25)
    assert c["control_tripwire"] == 12 and c["new_tripwire"] == 6
    assert near_probe_check(_probe(0.5), _probe(0.55))["holds"] is False


def test_near_probe_is_void_when_control_at_ceiling():
    c = near_probe_check(_probe(NEAR_PROBE_CEILING), _probe(1.0))
    assert c["control_at_ceiling"] is True and c["holds"] is None
    assert near_probe_check(None, _probe(1.0)) is None


def test_near_probe_n_mismatch_is_loud():
    with pytest.raises(AssertionError, match="near probe n differs"):
        near_probe_check(_probe(0.5, n=24), _probe(0.5, n=20))


def test_decision_tables_render_on_committed_reports():
    """Stand-in: A2 as control, A3 as new (the real A4 report does not exist yet);
    proves the plumbing and that P4 moves to the near probe."""
    control = json.loads((REPORTS / "260902_p26b_A.json").read_text())
    new = json.loads((REPORTS / "260903_p26c_A3.json").read_text())
    probe_c = json.loads((REPORTS / "260903_p26c_probe_A2.json").read_text())
    probe_n = json.loads((REPORTS / "260903_p26c_probe_A3.json").read_text())
    t = decision_tables(control, new, probe_control=probe_c, probe_new=probe_n,
                        near_control=_probe(0.5, tripwire=12), near_new=_probe(0.8, tripwire=5))
    assert "P4_oos_probe" not in t["checks"] and "natural_oos_probe" in t["exploratory"]
    assert t["checks"]["P4_near_probe"]["holds"] is True
    assert t["checks"]["P1_tripwire"]["holds"] is False  # A3 kept the tripwire at 3
    md = render_markdown(t)
    assert "A3 (P2.6c, corpus 0.1.5)" in md and "A4 (P2.6d, corpus 0.1.6)" in md and "P4 near-surface probe (n=24)" in md
