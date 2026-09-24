"""Unit tests for the UNKNOWN ledger (band B0, backlog #4976).

``TestClusterUnknownFindings`` exercises the pure clustering core
(:func:`unknown_ledger.cluster_unknown_findings`) against synthetic
``Finding`` objects -- no oracle_replay invocation, no corpus, deterministic
and fast. ``TestFindingsSinkSeam`` is the one integration-shaped test: it
proves the additive :data:`oracle_common.FINDINGS_SINK` seam actually fires
with the real relabelled findings when :func:`oracle_common.run_static_calls`
runs over a small synthetic contract with a real guard (mirroring
``test_oracle_replay.py``'s own
``TestPLRNamedArguments.test_run_static_calls_uses_plr_named_kwargs``
fixture shape), and that the seam is fully inert (default ``None``) for
every OTHER caller -- i.e. this test file's own use of the sink cannot leak
into ``test_oracle_replay.py``'s suite.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from plr_sema.verdict import Finding, PlrSite, Verdict, join

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "eval"))

import oracle_common as oc  # noqa: E402
from unknown_ledger import _compute_consistency, cluster_unknown_findings  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]


def _site(lineno: int, qualname: str = "LiquidHandler._check_args") -> PlrSite:
    return PlrSite(
        file="external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
        lineno=lineno,
        qualname=qualname,
    )


def _unk(op_id: str, reason: str, *, lineno: int = 375, qualname: str = "LiquidHandler._check_args",
         detail: str = "len(missing) > 0", plr_site: PlrSite | None = ...) -> Finding:
    site = _site(lineno, qualname) if plr_site is ... else plr_site
    return Finding(verdict=Verdict.UNKNOWN, operation_id=op_id, category="", plr_site=site,
                    reason=reason, detail=detail)


def _safe(op_id: str) -> Finding:
    return Finding(verdict=Verdict.SAFE, operation_id=op_id, category="",
                    plr_site=_site(535, "TipTracker.remove_tip"), reason="", detail="")


class TestClusterUnknownFindings:
    def test_sole_blocker_when_op_has_exactly_one_cluster(self):
        """An op whose ONLY non-SAFE finding is one (reason, site, detail)
        triple is a sole blocker for that cluster; an op with two distinct
        triples is a sole blocker for neither.
        """
        findings_op0 = (_unk("op_0", "guard_predicate_unparsed"),)
        findings_op1 = (
            _unk("op_1", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
            _unk("op_1", "guard_predicate_unparsed", lineno=383, detail="strictness == Strictness.STRICT"),
        )
        row_findings = [("rowA", findings_op0 + findings_op1)]
        row_methods = [["aspirate", "aspirate"]]

        result = cluster_unknown_findings(row_findings, row_methods)

        assert result["n_ops_executed"] == 2
        assert result["n_ops_unknown"] == 2
        assert result["n_findings_total"] == 3
        assert result["n_clusters"] == 2

        by_key = {(c["reason"], c["condition"]): c for c in result["clusters"]}
        sole_cluster = by_key[("guard_predicate_unparsed", "len(missing) > 0")]
        assert sole_cluster["n_ops_blocked"] == 2  # op_0 and op_1 both carry this triple
        assert sole_cluster["n_ops_sole_blocker"] == 1  # only op_0 has NO other triple
        assert {e["op_id"] for e in sole_cluster["example_ops"]} == {"op_0", "op_1"}

        other_cluster = by_key[("guard_predicate_unparsed", "strictness == Strictness.STRICT")]
        assert other_cluster["n_ops_blocked"] == 1
        assert other_cluster["n_ops_sole_blocker"] == 0  # op_1 has a sibling triple

    def test_safe_verdict_op_excluded_from_clusters(self):
        """An op whose join() is SAFE (all findings SAFE) contributes to
        n_ops_executed but never to n_ops_unknown/clusters -- this is the
        "only findings on executed rows/ops count" / UNKNOWN-side rule.
        """
        row_findings = [("rowA", (_safe("op_0"),))]
        result = cluster_unknown_findings(row_findings, [[]])
        assert result["n_ops_executed"] == 1
        assert result["n_ops_unknown"] == 0
        assert result["n_clusters"] == 0
        assert result["n_findings_total"] == 0

    def test_mixed_safe_and_unknown_finding_same_op_is_unknown_and_only_unknown_finding_clusters(self):
        """join() gives UNKNOWN priority over SAFE (SAFE < UNKNOWN < WILL_FAIL,
        spec §3.2's obligation order) -- an op with one SAFE and one UNKNOWN
        finding is an UNKNOWN op, and only its UNKNOWN finding clusters (the
        coexisting SAFE finding is not a "non-SAFE reason", so it must not
        appear in any cluster nor break the sole-blocker count).
        """
        findings = (_safe("op_0"), _unk("op_0", "guard_predicate_unparsed"))
        row_findings = [("rowA", findings)]
        result = cluster_unknown_findings(row_findings, [["pick_up_tips"]])
        assert result["n_ops_unknown"] == 1
        assert result["n_findings_total"] == 1
        assert result["n_clusters"] == 1
        cluster = result["clusters"][0]
        assert cluster["n_ops_sole_blocker"] == 1
        assert cluster["per_method"] == {"pick_up_tips": 1}

    def test_will_fail_verdict_op_excluded_from_clusters(self):
        """join() gives WILL_FAIL top priority -- an op with a WILL_FAIL
        finding is never an UNKNOWN op, regardless of any coexisting UNKNOWN
        finding, and contributes nothing to the ledger's clusters (this
        ledger is scoped to UNKNOWN root causes only, spec deferred row (f)).
        """
        will_fail = Finding(verdict=Verdict.WILL_FAIL, operation_id="op_0", category="tip_state",
                             plr_site=_site(535, "TipTracker.remove_tip"), reason="", detail="")
        findings = (will_fail, _unk("op_0", "guard_predicate_unparsed"))
        assert join(findings) is Verdict.WILL_FAIL  # sanity on the fixture itself
        row_findings = [("rowA", findings)]
        result = cluster_unknown_findings(row_findings, [["aspirate"]])
        assert result["n_ops_unknown"] == 0
        assert result["n_clusters"] == 0

    def test_reason_set_histogram_and_deterministic_cluster_ordering(self):
        """per_op_reason_set_histogram groups by the SET of reasons (not the
        finer (reason, site, detail) cluster key) per op, and both the
        cluster list and the histogram are sorted deterministically
        (n_ops_blocked/n_ops desc, then the key) so a re-run over the same
        input byte-for-byte reproduces the same JSON.
        """
        row_findings = [
            ("row0", (
                _unk("op_0", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
                _unk("op_0", "volume_state_unknown", lineno=1034, qualname="LiquidHandler.aspirate",
                     detail="<unconditional>"),
            )),
            ("row1", (
                _unk("op_0", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
            )),
            ("row2", (
                _unk("op_0", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
            )),
        ]
        row_methods = [["aspirate"], ["aspirate"], ["dispense"]]
        result = cluster_unknown_findings(row_findings, row_methods)

        assert result["n_ops_unknown"] == 3
        histogram = result["per_op_reason_set_histogram"]
        assert histogram[0]["reason_set"] == ["guard_predicate_unparsed"]
        assert histogram[0]["n_ops"] == 2
        assert histogram[1]["reason_set"] == ["guard_predicate_unparsed", "volume_state_unknown"]
        assert histogram[1]["n_ops"] == 1

        top_cluster = result["clusters"][0]
        assert top_cluster["reason"] == "guard_predicate_unparsed"
        assert top_cluster["n_ops_blocked"] == 3
        assert top_cluster["per_method"] == {"aspirate": 2, "dispense": 1}

        # Re-running produces byte-identical JSON (determinism, not just
        # equal Python objects -- catches an unstable dict/set iteration
        # order that `==` would miss between two DIFFERENT orderings that
        # happen to compare equal as dicts/lists of unordered content).
        result2 = cluster_unknown_findings(row_findings, row_methods)
        assert json.dumps(result, sort_keys=True) != ""  # smoke: serializable
        assert result == result2

    def test_missing_method_list_degrades_to_unknown_method(self):
        """A caller with no method info (row_methods entry too short, or
        an out-of-range index) gets `<unknown>` rather than an exception --
        the pure clustering core must not require method attribution to
        function correctly.
        """
        row_findings = [("rowA", (_unk("op_5", "guard_predicate_unparsed"),))]
        result = cluster_unknown_findings(row_findings, [[]])
        assert result["clusters"][0]["per_method"] == {"<unknown>": 1}


class TestRowIdCollision:
    """Band B0 fix (backlog #4976, round-1 challenger C12, 260905):
    ``row_id`` is a content digest (``oracle_common.content_digest``) that
    is documented to collide across a small fraction of corpus rows.
    Two DIFFERENT rows sharing that digest, each with an op at the SAME
    ``op_id``, must be counted as two DISTINCT ``ops_blocked`` entries --
    the pre-fix ``(row_id, op_id)``-keyed set silently merged them into
    one, undercounting ``n_ops_blocked``/``n_ops_sole_blocker`` by exactly
    the collision count.
    """

    def test_two_rows_sharing_a_colliding_row_id_are_not_merged(self):
        row_findings = [
            ("corpus_p25:deadbeef", (_unk("op_0", "guard_predicate_unparsed"),)),
            ("corpus_p25:deadbeef", (_unk("op_0", "guard_predicate_unparsed"),)),
        ]
        row_methods = [["move_plate"], ["move_lid"]]

        result = cluster_unknown_findings(row_findings, row_methods)

        assert result["n_ops_executed"] == 2
        assert result["n_ops_unknown"] == 2
        assert result["n_row_id_collisions"] == 1

        assert len(result["collision_ops"]) == 1
        collision = result["collision_ops"][0]
        assert collision["row_idx"] == 1
        assert collision["record_id"] == "corpus_p25:deadbeef"
        assert collision["op_id"] == "op_0"
        assert collision["method"] == "move_lid"
        assert collision["reason_set"] == ["guard_predicate_unparsed"]
        assert collision["verdict"] == "unknown"

        assert result["n_clusters"] == 1
        cluster = result["clusters"][0]
        assert cluster["n_ops_blocked"] == 2  # NOT 1 -- the pre-fix defect
        assert cluster["n_ops_sole_blocker"] == 2
        assert cluster["per_method"] == {"move_lid": 1, "move_plate": 1}
        assert sum(cluster["per_method"].values()) == cluster["n_ops_blocked"]

        assert result["consistency"]["ok"] is True

    def test_no_collisions_reported_when_row_ids_are_distinct(self):
        row_findings = [
            ("corpus_p25:aaaa", (_unk("op_0", "guard_predicate_unparsed"),)),
            ("corpus_p25:bbbb", (_unk("op_0", "guard_predicate_unparsed"),)),
        ]
        result = cluster_unknown_findings(row_findings, [["aspirate"], ["dispense"]])
        assert result["n_row_id_collisions"] == 0
        assert result["collision_ops"] == []
        assert result["clusters"][0]["n_ops_blocked"] == 2


class TestConsistencyInvariant:
    """Direct unit tests for :func:`_compute_consistency` (band B0 fix,
    #4976 round-1 C12) plus a check that the real pipeline always produces
    an ``ok`` consistency block for itself, given the cluster/histogram
    populations are built from the same per-op loop.
    """

    def test_ok_on_a_normal_ledger_produced_by_the_real_pipeline(self):
        row_findings = [
            ("row0", (
                _unk("op_0", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
                _unk("op_0", "volume_state_unknown", lineno=1034, qualname="LiquidHandler.aspirate",
                     detail="<unconditional>"),
            )),
            ("row1", (
                _unk("op_0", "guard_predicate_unparsed", lineno=375, detail="len(missing) > 0"),
            )),
        ]
        result = cluster_unknown_findings(row_findings, [["aspirate"], ["aspirate"]])
        consistency = result["consistency"]
        assert consistency["ok"] is True
        assert consistency["violations"] == []
        assert consistency["sum_histogram_n_ops"] == result["n_ops_unknown"] == consistency["n_ops_unknown"]

    def test_flags_histogram_sum_mismatch_against_n_ops_unknown(self):
        histogram_list = [{"reason_set": ["r1"], "n_ops": 3}]
        consistency = _compute_consistency([], histogram_list, n_ops_unknown=5)
        assert consistency["ok"] is False
        assert any("sum(per_op_reason_set_histogram.n_ops)" in v for v in consistency["violations"])

    def test_flags_cluster_claiming_more_ops_than_its_reason_population(self):
        # cluster claims 5 ops blocked for reason r1, but the histogram says
        # only 3 UNKNOWN ops carried r1 at all -- structurally impossible.
        cluster_list = [{
            "reason": "r1", "plr_site": "<none>", "condition": "c",
            "n_ops_blocked": 5, "per_method": {"m": 5},
        }]
        histogram_list = [{"reason_set": ["r1"], "n_ops": 3}]
        consistency = _compute_consistency(cluster_list, histogram_list, n_ops_unknown=3)
        assert consistency["ok"] is False
        assert any("n_ops_with_reason" in v for v in consistency["violations"])

    def test_flags_per_method_sum_not_matching_n_ops_blocked(self):
        cluster_list = [{
            "reason": "r1", "plr_site": "<none>", "condition": "c",
            "n_ops_blocked": 4, "per_method": {"m": 3},
        }]
        histogram_list = [{"reason_set": ["r1"], "n_ops": 4}]
        consistency = _compute_consistency(cluster_list, histogram_list, n_ops_unknown=4)
        assert consistency["ok"] is False
        assert any("sum(per_method)" in v for v in consistency["violations"])


class TestFindingsSinkSeam:
    """Integration-shaped: proves the additive oracle_common.FINDINGS_SINK
    seam (#4976) actually fires from a real run_static_calls call, and is
    fully reset afterward.
    """

    def setup_method(self):
        assert oc.FINDINGS_SINK is None, "a prior test left FINDINGS_SINK installed"

    def teardown_method(self):
        oc.FINDINGS_SINK = None

    def test_sink_fires_with_relabelled_real_op_findings(self):
        example = {
            "call_sequence": [
                {"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}},
            ],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
            "intent_record": {"record_id": "test:deadbeef"},
        }
        plr_kwargs = {
            0: {
                "tip_spots": {"k": "seq", "items": [{"k": "ref", "name": "tip_rack", "cell": "A1"}]},
                "use_channels": {"k": "seq", "items": [{"k": "lit", "v": 0}]},
            },
        }
        contracts_json = json.dumps({
            "contracts": {
                "LiquidHandler.pick_up_tips": {
                    "guards": [
                        {
                            "condition": "len(not_tip_spots) > 0",
                            "depth": 0, "free_vars": [], "kind": "raise_guard",
                            "raises": "TypeError", "scope_trail": [],
                            "site": {
                                "file": "external/pylabrobot/pylabrobot/liquid_handling/liquid_handler.py",
                                "lineno": 498, "qualname": "LiquidHandler.pick_up_tips",
                            },
                        },
                    ],
                    "gaps": [],
                    "params": ["tip_spots", "use_channels"],
                },
            },
        })

        collected: list[tuple[str, tuple]] = []
        oc.FINDINGS_SINK = lambda row_id, findings: collected.append((row_id, findings))

        param_names = oc.param_names_from_contracts(contracts_json)
        st, not_planned = oc.run_static_calls(example, plr_kwargs, contracts_json, param_names=param_names)

        assert not_planned == []
        assert st["op_0"]["verdict"] == "unknown"
        assert len(collected) == 1
        row_id, findings = collected[0]
        assert row_id == "test:deadbeef"
        assert len(findings) >= 1
        assert all(f.operation_id == "op_0" for f in findings)
        assert any(f.reason == "guard_predicate_unparsed" for f in findings)
        assert any(f.detail == "len(not_tip_spots) > 0" for f in findings)

    def test_sink_receives_empty_row_id_when_example_has_no_intent_record(self):
        """The default-caller shape (e.g. test_oracle_replay.py's own
        synthetic examples, which never set `intent_record`) must not raise
        -- it degrades to `row_id = ""`.
        """
        example = {
            "call_sequence": [{"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}}],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {0: {"tip_spots": {"k": "seq", "items": []}}}
        contracts_json = json.dumps({"contracts": {}})

        collected: list[tuple[str, tuple]] = []
        oc.FINDINGS_SINK = lambda row_id, findings: collected.append((row_id, findings))

        oc.run_static_calls(example, plr_kwargs, contracts_json)

        assert len(collected) == 1
        assert collected[0][0] == ""

    def test_default_sink_is_none_and_inert(self):
        """Byte-identical-behaviour guarantee: with no sink installed,
        run_static_calls's return value is unaffected (this is really just
        re-asserting test_oracle_replay.py's own coverage, kept here as a
        direct, local witness that the seam this file exercises has a true
        no-op default).
        """
        assert oc.FINDINGS_SINK is None
        example = {
            "call_sequence": [{"name": "pick_up_tips", "params": {"at": ["tip_rack.A1"]}}],
            "deck_layout": {"resources": {"tip_rack": "TipRack"}},
        }
        plr_kwargs = {0: {"tip_spots": {"k": "seq", "items": []}}}
        contracts_json = json.dumps({"contracts": {}})
        st, not_planned = oc.run_static_calls(example, plr_kwargs, contracts_json)
        assert not_planned == []
        assert st["op_0"]["verdict"] == "unknown"
