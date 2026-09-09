"""260901 T14 (backlog #4862): permanent end-to-end verification of
``check_graph`` against the NON-LEGACY contract table specifically
(``plr-sema/data/derived_contracts.upstream_nonlegacy.json``, produced by
T13's ``upstream_nonlegacy`` surface).

**Why this file exists, not just more cases in ``test_check_graph.py``.**
Every existing end-to-end test in that file loads
``data/derived_contracts.json`` -- the ``legacy_pinned`` surface's table.
Earlier spot-checks during T13/T14 recon (``VSpinBackend.spin``,
``BioShake.start_shaking``) were run against that OLD pin's table, not this
surface's own -- passing there proves nothing about whether ``check_graph``
actually resolves real operations through THIS contract table. This file is
the missing direct confirmation, kept permanent (not a one-off script) so a
future regeneration of ``derived_contracts.upstream_nonlegacy.json`` that
silently breaks the lookup shape gets caught by CI, not by a human
re-running an ad hoc snippet.

**Surface facts asserted, not assumed** (T13's own measurements, restated
here as the load-bearing assumptions this file's fixtures depend on):
``upstream_nonlegacy`` has NO ``class_name == "LiquidHandler"`` record at
all (``machines/`` is a bare ``__init__.py``; ``LiquidHandler`` exists only
under ``legacy/``), so its contract table has zero ``LiquidHandler.*`` keys
-- ``test_liquid_handler_is_genuinely_absent_from_this_surface`` pins that
fact directly, since every other test in this module silently depends on it
(a real ``LiquidHandler.<name>`` operation resolving here, post-regen, would
mean the surfaces were accidentally re-merged, not that this file's cases
were wrong).

**Family selection.** One real, finding-bearing, guard-populated
``(receiver_type, method_name)`` pair from each of the eight families named
in the T14 brief (``revvity``, ``agilent``, ``hamilton``, ``brooks``,
``molecular_devices``, ``high_res``, ``io``, ``resources``), chosen by
inspecting ``derived_contracts.upstream_nonlegacy.json`` directly (not
guessed) so each op is guaranteed to exercise a real, populated contract
entry -- the same "must not be satisfiable via ``receiver_type_unknown``
alone" discipline ``test_check_graph.py``'s D1 flag already established for
the legacy fixture (see ``test_fixture_exercises_contract_table_lookup``
there).

**Site-path assertion, not existence.** T13's ``upstream_nonlegacy``
extraction used ``git archive <sha> | tar -x`` into an ephemeral
``--plr-root`` (a temp directory) rather than a stable, committed tree like
``external/pylabrobot`` -- the guard ``site.file`` paths recorded in the
committed ``derived_contracts.upstream_nonlegacy.json`` therefore point at a
path that no longer exists on disk (confirmed 260901: the T13 extraction
directory is gone). Asserting ``Path(f.plr_site.file).exists()`` would
therefore be a FALSE negative on every future checkout, not a real check.
What IS load-bearing and stable is the path's SUFFIX -- the PLR-relative
module path (e.g. ``pylabrobot/revvity/celigo/camera.py``) -- which is a
property of PLR's own source layout at the pinned commit, not of where the
extraction happened to land. Every site assertion below checks that suffix.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from plr_sema.check import check_graph
from plr_sema.verdict import AnalysisReport, Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
CONTRACTS_JSON = PLR_SEMA_ROOT / "data" / "derived_contracts.upstream_nonlegacy.json"

# 260901 T13's own measured surface facts (commit 51446375): the
# upstream_nonlegacy pin and its degraded ("nogit") PLR git state -- an
# out-of-repo git-archive extraction has no .git to introspect.
_EXPECTED_SURFACE_NAME = "upstream_nonlegacy"
_EXPECTED_SURFACE_PIN = "3a50a567fe537d3a7b8ecdc84858191ee3c19637"

# One real, finding-bearing (receiver_type, method_name, expected PLR-relative
# site-file suffix) triple per family named in the T14 brief. Picked by
# direct inspection of derived_contracts.upstream_nonlegacy.json (260901),
# not guessed -- each entry has >=1 guard in the real, committed table.
_FAMILY_CASES: tuple[tuple[str, str, str, str], ...] = (
    ("revvity", "CameraFrame", "statistics", "pylabrobot/revvity/celigo/camera.py"),
    ("agilent", "BenchCel4R", "_read_frame", "pylabrobot/agilent/benchcel/benchcel.py"),
    (
        "hamilton",
        "Autoload",
        "track_range",
        "pylabrobot/hamilton/star/driver/features/autoload.py",
    ),
    (
        "brooks",
        "PreciseFlex",
        "set_response_mode",
        "pylabrobot/brooks/precise_flex/precise_flex.py",
    ),
    (
        "molecular_devices",
        "Pico",
        "channel",
        "pylabrobot/molecular_devices/imageXpress/pico/pico.py",
    ),
    ("high_res", "HighResLidValet", "setup", "pylabrobot/high_res/lid_valet.py"),
    ("io", "Reader", "u8", "pylabrobot/io/binary.py"),
    ("resources", "Carrier", "assign_child_resource", "pylabrobot/resources/carrier.py"),
)


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_JSON.read_text(encoding="utf-8")


def _graph_json(operations: list[dict]) -> str:
    return json.dumps(
        {
            "protocol_fqn": "test.t14_nonlegacy_families",
            "operations": operations,
            "resources": {},
        }
    )


def _op(op_id: str, receiver_type: str, method_name: str) -> dict:
    return {
        "id": op_id,
        "method_name": method_name,
        "receiver_variable": "x",
        "receiver_type": receiver_type,
    }


# ---------------------------------------------------------------------------
# Surface sanity: the assumption every other test in this module depends on.
# ---------------------------------------------------------------------------


def test_liquid_handler_is_genuinely_absent_from_this_surface(contracts_json: str) -> None:
    """T13's headline fact (module docstring), pinned directly: NOT ONE
    contract-table key starts with ``LiquidHandler.`` on this surface. Every
    other test below relies on this to distinguish "genuinely unknown" from
    "architecturally absent" -- if this ever fails, the surfaces have been
    accidentally merged and every other assertion in this file needs
    re-reading, not just this one."""
    contracts = json.loads(contracts_json)["contracts"]
    lh_keys = [k for k in contracts if k.startswith("LiquidHandler.")]
    assert lh_keys == [], (
        f"expected zero LiquidHandler.* keys in {CONTRACTS_JSON.name} -- found "
        f"{lh_keys[:5]}; the non-legacy surface is supposed to have no "
        f"orchestration layer at all (T13)"
    )


# ---------------------------------------------------------------------------
# Item 1 -- one real operation per family, end to end.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "family,receiver_type,method_name,site_suffix",
    _FAMILY_CASES,
    ids=[case[0] for case in _FAMILY_CASES],
)
def test_family_operation_resolves_end_to_end(
    contracts_json: str,
    family: str,
    receiver_type: str,
    method_name: str,
    site_suffix: str,
) -> None:
    """One real operation from each of the eight named families
    (``revvity``, ``agilent``, ``hamilton``, ``brooks``,
    ``molecular_devices``, ``high_res``, ``io``, ``resources``) resolves
    through a REAL, populated ``derived_contracts.upstream_nonlegacy.json``
    entry: verdict UNKNOWN, >=1 finding grounded at a real PLR site (module
    docstring's "suffix, not existence" note), and the finding's
    ``operation_id`` is the real graph id, never fabricated."""
    graph_json = _graph_json([_op("op_1", receiver_type, method_name)])
    report = check_graph(graph_json, contracts_json)

    assert report.verdict is Verdict.UNKNOWN
    assert report.findings, f"{receiver_type}.{method_name} produced no findings at all"
    assert {f.operation_id for f in report.findings} == {"op_1"}
    assert "unsupported_tool" not in {f.reason for f in report.findings}, (
        f"{receiver_type}.{method_name} fired unsupported_tool -- expected a "
        f"real, populated contract-table entry"
    )

    grounded = [f for f in report.findings if f.plr_site is not None]
    assert grounded, (
        f"{receiver_type}.{method_name} produced no finding with a plr_site -- "
        f"the contract table entry was never actually exercised"
    )
    assert any(site_suffix in f.plr_site.file for f in grounded), (
        f"no finding for {receiver_type}.{method_name} has a plr_site.file "
        f"ending in {site_suffix!r}; got "
        f"{[f.plr_site.file for f in grounded]}"
    )


def test_all_eight_families_together_in_one_graph(contracts_json: str) -> None:
    """The eight family operations combined into a single multi-op graph
    (rather than eight isolated single-op graphs, as the parametrized test
    above uses) -- AC-6.4-style surjectivity: every operation_id present in
    the graph must receive >=1 finding, and no fabricated id may appear."""
    operations = [
        _op(f"op_{i}", receiver_type, method_name)
        for i, (_family, receiver_type, method_name, _suffix) in enumerate(_FAMILY_CASES)
    ]
    graph_json = _graph_json(operations)
    report = check_graph(graph_json, contracts_json)

    assert report.verdict is Verdict.UNKNOWN
    real_ids = {op["id"] for op in operations}
    finding_ids = {f.operation_id for f in report.findings}
    assert finding_ids == real_ids, (
        f"finding operation_id set {sorted(finding_ids)} != real graph id set "
        f"{sorted(real_ids)}"
    )
    reasons = {f.reason for f in report.findings}
    assert "unsupported_tool" not in reasons

    grounded = [f for f in report.findings if f.plr_site is not None]
    grounded_suffixes = {f.plr_site.file for f in grounded}
    for _family, receiver_type, method_name, site_suffix in _FAMILY_CASES:
        assert any(site_suffix in f for f in grounded_suffixes), (
            f"no grounded finding in the combined-graph run points at "
            f"{site_suffix!r} ({receiver_type}.{method_name})"
        )


# ---------------------------------------------------------------------------
# Item 1 -- a genuinely-unknown method still yields unsupported_tool.
# ---------------------------------------------------------------------------


def test_genuinely_unknown_method_yields_unsupported_tool(contracts_json: str) -> None:
    """Two independent ways a method can be genuinely unknown to this
    surface's contract table -- both must fire ``unsupported_tool``, never
    fall through some other reason:

    * a fake method name on a REAL family class (``PreciseFlex`` from the
      brooks case above) -- proves the miss is about the METHOD, not the
      class.
    * ``LiquidHandler.aspirate`` -- a real method name on legacy_pinned, but
      architecturally absent here (T13) -- proves "unsupported_tool" is
      keyed off THIS table's actual contents, not off some allowlist that
      might still recognize a legacy-surface name.
    """
    fake_method_report = check_graph(
        _graph_json([_op("op_1", "PreciseFlex", "definitely_fake_method_xyz")]),
        contracts_json,
    )
    assert {f.reason for f in fake_method_report.findings} == {"unsupported_tool"}

    absent_orchestration_report = check_graph(
        _graph_json([_op("op_1", "LiquidHandler", "aspirate")]), contracts_json
    )
    assert {f.reason for f in absent_orchestration_report.findings} == {"unsupported_tool"}


# ---------------------------------------------------------------------------
# Stamp/provenance sanity -- confirms this file is actually exercising the
# surface it claims to (trap 1: liquid_handler_present must keep degrading
# loudly, and the stamp is the mechanism that names which surface ran).
# ---------------------------------------------------------------------------


def test_report_stamp_names_the_nonlegacy_surface(contracts_json: str) -> None:
    report: AnalysisReport = check_graph(
        _graph_json([_op("op_1", "Reader", "u8")]), contracts_json
    )
    assert report.stamp.surface == _EXPECTED_SURFACE_NAME
    assert report.stamp.surface_pin == _EXPECTED_SURFACE_PIN
    # T13: an out-of-repo git-archive extraction has no .git to introspect --
    # capture_git_state degrades to the explicit "nogit" sentinel rather than
    # fabricating a hash. This must keep degrading loudly (T14 trap 1): a
    # future regen that silently starts reporting a real-looking hash here
    # without actually having a .git dir would be a provenance regression.
    assert report.stamp.plr.hash == "nogit"
    assert report.stamp.plr.provenance_source == "nogit"
