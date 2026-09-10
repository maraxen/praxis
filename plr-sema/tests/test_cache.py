"""Spec 260903 §13.3 (`260903_plr-sema-families-cache-increment.md`), #4922:
the content-addressed report cache. Covers AC-13.5 through AC-13.8 as named
in the #4922 task row (§13.9) -- note this numbering is the task row's own,
and differs from the full spec document's §13.8 numbering in one place: the
task's "AC-13.7" (key components independently load-bearing, including
``env``) corresponds to no single spec-document AC by that number (the
closest existing coverage is ``test_ir.py``'s
``test_cache_key_components_are_independently_load_bearing``, extended
here with the ``env`` dimension that test predates); the task's "AC-13.8"
(targeted invalidation) is the spec document's own AC-13.7. Both are tested
here under the task's numbering, and the spec document's own AC-13.8 (a
moved pin misses, and the drift test covers it) is included too since it is
a real, separately-stated normative requirement (§13.3.5).
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import sys
from pathlib import Path

import pytest

from plr_sema._provenance import SurveyStamp
from plr_sema._provenance.git_state import GitState
from plr_sema.check import _build_param_names, check_graph, ir
from plr_sema.check import cache as cache_mod
from plr_sema.check.cache import CacheStore, canonical_key
from plr_sema.verdict import Finding, PlrSite, Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]

# T40 (spec 260909 §16.2/§16.2.3, observation increment, backlog #5023):
# `observation_env_members` lives in `plr-sema/eval/oracle_common.py`, the
# harness package -- same sys.path pattern `test_oracle_replay.py` already
# uses to import it from `tests/`.
sys.path.insert(0, str(PLR_SEMA_ROOT / "eval"))
FIXTURES = PLR_SEMA_ROOT / "tests" / "fixtures"
CONTRACTS_JSON_PATH = PLR_SEMA_ROOT / "data" / "derived_contracts.json"

# Same pin as tests/test_fork_drift.py's EXPECTED_SUBMODULE_PIN and
# tests/test_check_graph.py's _PLR_PIN_SHA -- pinned as a local literal
# (not a cross-module import of a test file) for the same reason
# test_check_graph.py does it: this module should not depend on another
# test module's import-time side effects to define its own fixtures.
_EXPECTED_SUBMODULE_PIN = "dd79c4c89bc008629a1c598ea614be5e6067d1f9"


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_JSON_PATH.read_text(encoding="utf-8")


def _graph_json(name: str) -> str:
    return (FIXTURES / f"{name}.json").read_text(encoding="utf-8")


def _dummy_finding(operation_id: str = "0") -> Finding:
    return Finding(
        verdict=Verdict.UNKNOWN,
        operation_id=operation_id,
        category="",
        plr_site=PlrSite(file="a.py", lineno=1, qualname="A.b"),
        reason="no_contract_derived",
        detail="synthetic, test_cache.py",
        evidence=(),
    )


def _fake_stamp(surface_pin: str | None = _EXPECTED_SUBMODULE_PIN) -> SurveyStamp:
    return SurveyStamp(
        plr=GitState(hash="plr_sha", branch="main", dirty=False),
        praxis=GitState(hash="praxis_sha", branch="main", dirty=False),
        pylabrobot_version="0.2.2",
        stamped_at="2026-09-03T00:00:00+00:00",
        surface="legacy_pinned",
        surface_pin=surface_pin,
    )


# ---------------------------------------------------------------------------
# AC-13.5 -- a hit equals a miss; cache=None (default) creates no files.
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "fixture_name",
    ["simple_transfer_graph", "loop_double_pickup_graph"],
)
def test_hit_equals_miss(
    tmp_path: Path, contracts_json: str, fixture_name: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    graph_json = _graph_json(fixture_name)
    store = CacheStore(root=tmp_path / "cache")

    import plr_sema.check as check_mod

    calls: list[int] = []
    original_check_ir = check_mod.check_ir

    def counting_check_ir(*args, **kwargs):
        calls.append(1)
        return original_check_ir(*args, **kwargs)

    monkeypatch.setattr(check_mod, "check_ir", counting_check_ir)

    report_miss = check_graph(graph_json, contracts_json, cache=store)
    report_hit = check_graph(graph_json, contracts_json, cache=store)

    # The stub-defeating half: check_ir ran exactly once -- the second call
    # was satisfied entirely from the store, not recomputed and merely
    # happening to agree.
    assert len(calls) == 1, "check_ir must not run again on the second (hit) call"

    assert report_miss.findings == report_hit.findings
    assert report_miss.verdict is report_hit.verdict


def test_default_cache_none_creates_no_files(contracts_json: str) -> None:
    graph_json = _graph_json("simple_transfer_graph")
    root = cache_mod.DEFAULT_CACHE_ROOT
    existed_before = root.exists()
    listing_before = sorted(p.name for p in root.glob("*")) if existed_before else []

    check_graph(graph_json, contracts_json)  # cache defaults to None

    existed_after = root.exists()
    assert existed_after == existed_before, (
        "check_graph(cache=None) must not create plr-sema/.cache/ -- it must "
        "not even be touched"
    )
    if existed_after:
        listing_after = sorted(p.name for p in root.glob("*"))
        assert listing_after == listing_before


# ---------------------------------------------------------------------------
# AC-13.6 -- the stored findings are pre-relabel, and a second graph proves
# it; a receiver_state-only diff still changes the key.
# ---------------------------------------------------------------------------


def _retag_operation_ids(payload: dict, suffix: str) -> dict:
    """Rename every ``OperationNode.id`` (and every other quoted occurrence
    of that exact id string anywhere in the payload -- ``execution_order``
    included) by appending ``suffix``. A whole-text quoted-string
    replacement rather than a targeted field walk, so it is correct even
    for a fixture this test does not enumerate the schema of."""
    op_ids = [op["id"] for op in payload["operations"]]
    text = json.dumps(payload)
    for op_id in op_ids:
        text = text.replace(f'"{op_id}"', f'"{op_id}{suffix}"')
    return json.loads(text)


def test_pre_relabel_storage_two_graphs_same_bytecode_hash(
    tmp_path: Path, contracts_json: str
) -> None:
    graph_json_a = _graph_json("simple_transfer_graph")
    payload_a = json.loads(graph_json_a)
    payload_b = _retag_operation_ids(payload_a, "_v2")
    graph_json_b = json.dumps(payload_b)

    contracts = json.loads(contracts_json).get("contracts", {})
    param_names = _build_param_names(contracts)
    bc_a = ir.lower_graph(payload_a, param_names=param_names)
    bc_b = ir.lower_graph(payload_b, param_names=param_names)
    assert ir.bytecode_hash(bc_a) == ir.bytecode_hash(bc_b), (
        "two graphs differing only in OperationNode ids must lower to the "
        "same bytecode_hash -- sideband/origin is excluded from the hash"
    )

    ids_a = {op["id"] for op in payload_a["operations"]}
    ids_b = {op["id"] for op in payload_b["operations"]}
    assert ids_a.isdisjoint(ids_b)

    store = CacheStore(root=tmp_path / "cache")
    report_a = check_graph(graph_json_a, contracts_json, cache=store)  # cold: miss
    report_b = check_graph(graph_json_b, contracts_json, cache=store)  # warm: hit

    b_operation_ids = {f.operation_id for f in report_b.findings}
    assert b_operation_ids, "the fixture must produce >=1 finding for this test to mean anything"
    # The stub-defeating half: every operation_id on the SECOND graph's
    # report is one of the SECOND graph's own ids. An implementation that
    # stored POST-relabel findings would return the FIRST graph's ids here.
    assert b_operation_ids <= ids_b
    assert b_operation_ids.isdisjoint(ids_a)


def test_key_covers_receiver_state_not_just_contracts_subdict(contracts_json: str) -> None:
    graph_json = _graph_json("simple_transfer_graph")
    contracts_payload = json.loads(contracts_json)
    param_names = _build_param_names(contracts_payload.get("contracts", {}))
    bytecode = ir.lower_graph(json.loads(graph_json), param_names=param_names)
    bc_hash = ir.bytecode_hash(bytecode)
    stamp = _fake_stamp()

    key_base = ir.cache_key(bc_hash, contracts_json, stamp)

    contracts_payload_2 = copy.deepcopy(contracts_payload)
    receiver_state = contracts_payload_2.setdefault("receiver_state", {})
    receiver_state["_test_cache_marker"] = {"synthetic": True}
    contracts_json_2 = json.dumps(contracts_payload_2)

    key_receiver_state_changed = ir.cache_key(bc_hash, contracts_json_2, stamp)

    assert key_receiver_state_changed != key_base, (
        "contracts_sha is a sha256 of the WHOLE contracts_json string -- a "
        "key computed over the contracts sub-dict alone would miss a "
        "receiver_state-only change"
    )


# ---------------------------------------------------------------------------
# AC-13.7 (task-row numbering) -- every key component is independently
# load-bearing, `env` included.
# ---------------------------------------------------------------------------


def test_key_changes_on_one_byte_of_contracts_json() -> None:
    stamp = _fake_stamp()
    key_a = ir.cache_key("bc", '{"a":1}', stamp)
    key_b = ir.cache_key("bc", '{"a":2}', stamp)
    assert key_a[1] != key_b[1]
    assert key_a[0] == key_b[0]
    assert key_a[2] == key_b[2]
    assert key_a[3] == key_b[3]
    assert key_a[4] == key_b[4]


def test_key_changes_on_ir_version() -> None:
    stamp = _fake_stamp()
    key_a = ir.cache_key("bc", "{}", stamp, ir_version=2)
    key_b = ir.cache_key("bc", "{}", stamp, ir_version=3)
    assert key_a[3] != key_b[3]
    assert key_a[:3] == key_b[:3]
    assert key_a[4] == key_b[4]


def test_key_changes_on_surface_identity() -> None:
    stamp_a = _fake_stamp(surface_pin="pin_a")
    stamp_b = _fake_stamp(surface_pin="pin_b")
    key_a = ir.cache_key("bc", "{}", stamp_a)
    key_b = ir.cache_key("bc", "{}", stamp_b)
    assert key_a[2] != key_b[2]
    assert key_a[0] == key_b[0]
    assert key_a[1] == key_b[1]
    assert key_a[3] == key_b[3]
    assert key_a[4] == key_b[4]


def test_key_changes_on_env() -> None:
    stamp = _fake_stamp()
    key_default = ir.cache_key("bc", "{}", stamp)
    key_empty = ir.cache_key("bc", "{}", stamp, env=frozenset())
    key_nonempty = ir.cache_key("bc", "{}", stamp, env=frozenset({"volume_tracking"}))

    assert key_default == key_empty, "the default env component is the empty set"
    assert key_default[4] == ()
    assert key_nonempty[4] != key_default[4]
    assert key_nonempty[:3] == key_default[:3]
    assert key_nonempty[3] == key_default[3]

    # order-independence: two callers passing the same set in different
    # insertion/iteration order must produce the same key.
    key_order_a = ir.cache_key("bc", "{}", stamp, env=frozenset({"x", "y"}))
    key_order_b = ir.cache_key("bc", "{}", stamp, env=frozenset({"y", "x"}))
    assert key_order_a == key_order_b


# ---------------------------------------------------------------------------
# 260903 T27 (spec §14.6/§14.13, backlog #4959) -- AC-14.7's cache clause:
# `env` now reaches the `cache_key` call `check_graph` makes (T26 built the
# key-level `env` component and deliberately did NOT thread it into that
# call, per that call site's own T26-era comment). A hit under one `env`
# must never be served under another, and the default `env` must not
# invalidate anything a pre-T27 caller already wrote.
# ---------------------------------------------------------------------------


def test_env_partitions_the_cache(
    tmp_path: Path, contracts_json: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """AC-14.7's cache clause: the SAME graph under two different `env`s
    produces two DISTINCT `cache_key` entries and the second call is a
    MISS (recomputes under its own `env`), not a HIT (silently returns the
    first `env`'s findings) -- `check_ir`'s own call-count and observed
    `env` argument are the stub-defeating proof, not just the file count.
    Repeating the FIRST `env` afterwards must be a HIT again, and the
    default-`env` entry's on-disk path must be byte-identical to the path
    a pre-T27 caller (one that never passes `env=` to `ir.cache_key` at
    all) would have computed -- i.e. this change partitions the cache by
    hypothesis, it does not invalidate what is already there (§14.14 item
    6).
    """
    graph_json = _graph_json("simple_transfer_graph")
    store = CacheStore(root=tmp_path / "cache")

    import plr_sema.check as check_mod

    observed_envs: list[frozenset[str]] = []
    original_check_ir = check_mod.check_ir

    def counting_check_ir(*args, **kwargs):
        observed_envs.append(kwargs.get("env", frozenset()))
        return original_check_ir(*args, **kwargs)

    monkeypatch.setattr(check_mod, "check_ir", counting_check_ir)

    nonempty_env = frozenset({"does_volume_tracking"})

    report_default = check_graph(graph_json, contracts_json, cache=store)
    report_nonempty = check_graph(graph_json, contracts_json, cache=store, env=nonempty_env)

    assert len(observed_envs) == 2, (
        f"a different env must be a cache MISS, not a HIT -- check_ir ran "
        f"{len(observed_envs)} time(s), expected 2"
    )
    assert observed_envs == [frozenset(), nonempty_env]

    entries = sorted(store.root.glob("*.json"))
    assert len(entries) == 2, f"expected two distinct cache entries (one per env), got: {entries}"

    # Repeating the FIRST env is a HIT (no third check_ir call) -- proves
    # the miss above was about env specifically, not "every call misses".
    report_default_again = check_graph(graph_json, contracts_json, cache=store)
    assert len(observed_envs) == 2, "repeating the first env must be a cache HIT"
    assert report_default_again.findings == report_default.findings
    assert report_nonempty.findings is not None  # sanity: the second call did complete

    # The default-env entry's own on-disk path is BYTE-IDENTICAL to the
    # path a pre-T27 caller -- one that never passes env= to cache_key at
    # all -- would compute, so no cache entry written before this
    # increment is invalidated by this change.
    from plr_sema.check import _stamp_from_dict

    contracts_payload = json.loads(contracts_json)
    param_names = _build_param_names(contracts_payload.get("contracts", {}))
    bytecode = ir.lower_graph(json.loads(graph_json), param_names=param_names)
    bc_hash = ir.bytecode_hash(bytecode)
    stamp = _stamp_from_dict(contracts_payload["stamp"])

    pre_t27_key = ir.cache_key(bc_hash, contracts_json, stamp)  # no env= kwarg at all
    post_t27_default_key = ir.cache_key(bc_hash, contracts_json, stamp, env=frozenset())
    assert pre_t27_key == post_t27_default_key, "the default env component must still be the empty set"

    pre_t27_path = store._path_for(canonical_key(pre_t27_key))
    assert pre_t27_path in entries, (
        "the default-env check_graph(cache=store) entry must live at the "
        "SAME path a pre-T27 (no env=) cache_key call would compute"
    )


# ---------------------------------------------------------------------------
# AC-13.8 (task-row numbering; spec document's own AC-13.7) -- targeted
# invalidation deletes what changed and only what changed.
# ---------------------------------------------------------------------------


def test_invalidate_by_methods_deletes_only_matching_entries(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "cache")
    key_aspirate = ("bc_a", "sha_a", (None, None, None), 2, ())
    key_dispense = ("bc_d", "sha_d", (None, None, None), 2, ())
    key_both = ("bc_ad", "sha_ad", (None, None, None), 2, ())

    store.put(key_aspirate, (_dummy_finding("0"),), methods=frozenset({"aspirate"}))
    store.put(key_dispense, (_dummy_finding("0"),), methods=frozenset({"dispense"}))
    store.put(
        key_both,
        (_dummy_finding("0"),),
        methods=frozenset({"aspirate", "dispense"}),
    )

    count = store.invalidate_by_methods(frozenset({"aspirate"}))

    assert count == 2
    assert store.get(key_aspirate) is None
    assert store.get(key_both) is None
    assert store.get(key_dispense) is not None


def _write_contracts(path: Path, contracts: dict) -> None:
    path.write_text(
        json.dumps({"contracts": contracts, "receiver_state": {}, "schema_version": 1}),
        encoding="utf-8",
    )


def test_invalidation_cli_on_a_synthetic_two_table_diff(tmp_path: Path, capsys) -> None:
    old_contracts = {
        "LiquidHandler.aspirate": {"guards": [{"raises": "TooLittleLiquidError"}]},
        "LiquidHandler.dispense": {"guards": [{"raises": "TooLittleVolumeError"}]},
        "LiquidHandler.pick_up_tips": {"guards": []},
    }
    new_contracts = copy.deepcopy(old_contracts)
    # exactly one entry changes.
    new_contracts["LiquidHandler.aspirate"]["guards"][0]["raises"] = "SomethingElseError"

    old_path = tmp_path / "old_contracts.json"
    new_path = tmp_path / "new_contracts.json"
    _write_contracts(old_path, old_contracts)
    _write_contracts(new_path, new_contracts)

    cache_root = tmp_path / "cache"
    store = CacheStore(root=cache_root)
    key_aspirate = ("bc_a", "sha_a", (None, None, None), 2, ())
    key_dispense = ("bc_d", "sha_d", (None, None, None), 2, ())
    key_pickup = ("bc_p", "sha_p", (None, None, None), 2, ())
    store.put(key_aspirate, (_dummy_finding("0"),), methods=frozenset({"aspirate"}))
    store.put(key_dispense, (_dummy_finding("0"),), methods=frozenset({"dispense"}))
    store.put(key_pickup, (_dummy_finding("0"),), methods=frozenset({"pick_up_tips"}))

    rc = cache_mod.main(
        [
            "invalidate",
            "--old",
            str(old_path),
            "--new",
            str(new_path),
            "--cache-dir",
            str(cache_root),
        ]
    )
    assert rc == 0

    captured = capsys.readouterr()
    result = json.loads(captured.out)
    assert result["changed_keys"] == ["LiquidHandler.aspirate"]
    assert result["changed_methods"] == ["aspirate"]
    assert result["stale_count"] == 1

    assert store.get(key_aspirate) is None
    assert store.get(key_dispense) is not None
    assert store.get(key_pickup) is not None


def test_invalidation_cli_spec_flag_form(tmp_path: Path, capsys) -> None:
    """§13.3.4's own literal invocation form: no subcommand, `--root` not
    `--cache-dir`. Both forms must work (module-path-only invocation is
    what the spec names; `invalidate`/`--cache-dir` is the task row's
    phrasing)."""
    old_contracts = {"LiquidHandler.aspirate": {"guards": []}}
    new_contracts = {"LiquidHandler.aspirate": {"guards": [{"raises": "X"}]}}
    old_path = tmp_path / "old.json"
    new_path = tmp_path / "new.json"
    _write_contracts(old_path, old_contracts)
    _write_contracts(new_path, new_contracts)

    cache_root = tmp_path / "cache2"
    rc = cache_mod.main(
        ["--old", str(old_path), "--new", str(new_path), "--root", str(cache_root)]
    )
    assert rc == 0
    result = json.loads(capsys.readouterr().out)
    assert result["changed_keys"] == ["LiquidHandler.aspirate"]
    assert result["root"] == str(cache_root)


# ---------------------------------------------------------------------------
# Spec document's own AC-13.8 (§13.3.5) -- a moved pin misses, and the
# drift test covers it. test_fork_drift.py itself is unmodified (this test
# lives here, not there); HM-23 is untouched.
# ---------------------------------------------------------------------------


def test_moved_pin_is_a_miss(tmp_path: Path) -> None:
    stamp_at_pin = _fake_stamp(surface_pin=_EXPECTED_SUBMODULE_PIN)
    perturbed_pin = "e" + _EXPECTED_SUBMODULE_PIN[1:]  # differs by one character
    assert perturbed_pin != _EXPECTED_SUBMODULE_PIN
    assert len(perturbed_pin) == len(_EXPECTED_SUBMODULE_PIN)
    stamp_perturbed = dataclasses.replace(stamp_at_pin, surface_pin=perturbed_pin)

    key_at_pin = ir.cache_key("bc", "{}", stamp_at_pin)
    key_perturbed = ir.cache_key("bc", "{}", stamp_perturbed)
    assert key_at_pin != key_perturbed

    store = CacheStore(root=tmp_path / "cache")
    store.put(key_at_pin, (_dummy_finding("0"),))

    assert store.get(key_at_pin) is not None
    assert store.get(key_perturbed) is None


# ---------------------------------------------------------------------------
# CacheStore internals: atomic writes, corrupt-entry-is-a-miss, never
# raises into the checker.
# ---------------------------------------------------------------------------


def test_corrupt_entry_is_a_miss(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "cache")
    key = ("bc", "sha", (None, None, None), 2, ())
    store.root.mkdir(parents=True, exist_ok=True)
    path = store._path_for(canonical_key(key))
    path.write_text("{ not json", encoding="utf-8")
    assert store.get(key) is None


def test_key_mismatch_is_a_miss(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "cache")
    key = ("bc", "sha", (None, None, None), 2, ())
    other_key = ("bc2", "sha2", (None, None, None), 2, ())
    store.put(other_key, (_dummy_finding("0"),))
    # Force a filename collision by writing OTHER_KEY's entry at KEY's path
    # (simulates a hash collision / a filename-truncating filesystem).
    path_for_key = store._path_for(canonical_key(key))
    path_for_other = store._path_for(canonical_key(other_key))
    path_for_key.write_text(path_for_other.read_text(encoding="utf-8"), encoding="utf-8")
    assert store.get(key) is None


def test_put_never_raises_when_root_cannot_be_created(tmp_path: Path) -> None:
    blocked = tmp_path / "blocked"
    blocked.write_text("not a directory", encoding="utf-8")
    store = CacheStore(root=blocked / "cache")
    store.put(("bc", "sha", (None, None, None), 2, ()), (_dummy_finding("0"),))  # must not raise


def test_get_never_raises_on_missing_root(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "does_not_exist" / "cache")
    assert store.get(("bc", "sha", (None, None, None), 2, ())) is None


def test_invalidate_by_methods_on_missing_root_returns_zero(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "does_not_exist" / "cache")
    assert store.invalidate_by_methods(frozenset({"aspirate"})) == 0


def test_put_is_atomic_no_leftover_temp_files(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "cache")
    key = ("bc", "sha", (None, None, None), 2, ())
    store.put(key, (_dummy_finding("0"),))
    names = [p.name for p in store.root.iterdir()]
    assert all(".tmp-" not in name for name in names)
    assert len(names) == 1


def test_default_root_is_plr_sema_cache_never_tmpdir() -> None:
    store = CacheStore()
    assert store.root == cache_mod.DEFAULT_CACHE_ROOT
    assert store.root.name == ".cache"
    assert store.root.parent.name == "plr-sema"


# ---------------------------------------------------------------------------
# Roundtrip fidelity: a Finding with evidence and every field populated
# survives put()/get() bit-for-bit.
# ---------------------------------------------------------------------------


def test_finding_roundtrip_with_evidence(tmp_path: Path) -> None:
    store = CacheStore(root=tmp_path / "cache")
    finding = Finding(
        verdict=Verdict.WILL_FAIL,
        operation_id="3",
        category="precondition_state",
        plr_site=PlrSite(file="x.py", lineno=10, qualname="X.y"),
        reason="",
        detail="some detail",
        evidence=(
            PlrSite(file="x.py", lineno=11, qualname="X.z"),
            PlrSite(file="w.py", lineno=1, qualname="W.q"),
        ),
    )
    key = ("bc", "sha", (None, None, None), 2, ())
    store.put(key, (finding,))
    got = store.get(key)
    assert got == (finding,)


# ---------------------------------------------------------------------------
# T40 (spec 260909 §16.2/§16.2.3, observation increment, backlog #5023):
# the observation record's cache-key partition -- AC-16.1. `env` gains no
# sixth `cache_key` component (§16.2.3's own normative box, verified by
# `test_key_changes_on_env`/`test_env_partitions_the_cache` above still
# passing unmodified); the observation instead enters the EXISTING `env`
# frozenset as `obs:<key>=<value>` string members, built by
# `oracle_common.observation_env_members`.
# ---------------------------------------------------------------------------

_SAMPLE_OBSERVATION = {
    "backend_class": "LiquidHandlerChatterboxBackend",
    "num_channels": 8,
    "head_channels": [0, 1, 2, 3, 4, 5, 6, 7],
    "deck_resource_names": ["tip_rack", "source_plate", "dest_plate"],
    "arm_slots": [0],
}


def test_observation_env_members_none_is_empty() -> None:
    """§16.2.1's fail-closed default: no `plr_observation` (the deck-build
    early return, or any raising read inside `verify()`'s own capture
    window) adds NOTHING to `env` -- a caller that never passes it is
    byte-identical to every pre-T40 caller's empty-`env` cache key.
    """
    from oracle_common import observation_env_members

    assert observation_env_members(None, {}) == frozenset()
    assert observation_env_members({}, {"tip_rack": {}}) == frozenset()


def test_observation_env_members_json_encoding_and_int_sort() -> None:
    """§16.2.3's canonical encoding: `json.dumps(value, sort_keys=True,
    separators=(",", ":"))` of the field's own value, `head_channels`
    sorted NUMERICALLY (never string-sorted -- a 16-channel head would
    otherwise put channel 10 before channel 2 under string order).
    """
    from oracle_common import observation_env_members

    unsorted = dict(_SAMPLE_OBSERVATION, head_channels=[10, 2, 0, 1, 9, 3, 4, 5, 6, 7, 8, 11])
    members = observation_env_members(dict(unsorted, num_channels=12), {})

    assert 'obs:backend_class="LiquidHandlerChatterboxBackend"' in members
    assert "obs:num_channels=12" in members
    assert "obs:head_channels=[0,1,2,3,4,5,6,7,8,9,10,11]" in members
    # never the string-sort order [0,1,10,11,2,3,...]
    assert "obs:head_channels=[0,1,10,11,2,3,4,5,6,7,8,9]" not in members


def test_observation_env_members_arm_slots_numeric_sort() -> None:
    """§17.3's identical `head_channels` numeric-sort rule, applied to
    `arm_slots` (spec 260909_plr-sema-move-family-increment.md §17.3, T51):
    NEVER string-sorted -- a 16-arm backend would otherwise put arm 10
    before arm 2."""
    from oracle_common import observation_env_members

    unsorted = dict(_SAMPLE_OBSERVATION, arm_slots=[10, 2, 0, 1, 9])
    members = observation_env_members(unsorted, {})

    assert "obs:arm_slots=[0,1,2,9,10]" in members
    assert "obs:arm_slots=[0,1,10,2,9]" not in members


def test_observation_env_members_head_channels_mismatch_raises() -> None:
    """T40's own harness-side invariant (spec §16.13's T40 row): the
    harness asserts ``len(head_channels) == num_channels`` when reading
    the record -- a malformed record (produced by a future caller that
    bypasses `verify()`'s own capture) must fail loudly, not silently.
    """
    from oracle_common import observation_env_members

    malformed = dict(_SAMPLE_OBSERVATION, num_channels=99)
    with pytest.raises(AssertionError):
        observation_env_members(malformed, {})


def test_observation_env_members_deck_digest_is_injective_on_comma_and_equals() -> None:
    """§16.2.3's withdrawn-comma-joined-encoding argument, applied to the
    per-slot deck map: two distinct observations over resource names that
    would collide under a naive ``,``/``=``-joined encoding (one carrying
    a literal ``,``, the other a literal ``=``) must still produce
    DISTINCT `obs:deck_resources` digests -- JSON's own escaping closes
    the hazard spec_version 1's withdrawn encoding could not. AC-16.1's
    named fixture.
    """
    from oracle_common import observation_env_members

    resources = {"a,b": {}, "c=d": {}}
    obs_a = dict(_SAMPLE_OBSERVATION, deck_resource_names=["a,b"])
    obs_b = dict(_SAMPLE_OBSERVATION, deck_resource_names=["c=d"])

    members_a = observation_env_members(obs_a, resources)
    members_b = observation_env_members(obs_b, resources)

    digest_a = next(m for m in members_a if m.startswith("obs:deck_resources="))
    digest_b = next(m for m in members_b if m.startswith("obs:deck_resources="))
    assert digest_a != digest_b

    # the digest is exactly sha256 of the JSON-encoded per-slot bool map.
    expected_map_a = {"a,b": True, "c=d": False}
    expected_digest_a = "obs:deck_resources=" + hashlib.sha256(
        json.dumps(expected_map_a, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert expected_digest_a in members_a


def test_observation_partitions_cache_key_via_env(contracts_json: str) -> None:
    """AC-16.1: `env` carrying `obs:` members changes `ir.cache_key`'s
    fifth component exactly the way any other `env` member does (no sixth
    component, `tuple(sorted(env))` unchanged) -- the SAME mechanism
    `test_key_changes_on_env` already covers, exercised here with a REAL
    `observation_env_members(...)` output rather than a hand-typed set.
    """
    from oracle_common import observation_env_members

    stamp = _fake_stamp()
    obs_env = observation_env_members(_SAMPLE_OBSERVATION, {"tip_rack": {}, "source_plate": {}})

    key_empty = ir.cache_key("bc", "{}", stamp)
    key_observed = ir.cache_key("bc", "{}", stamp, env=obs_env)

    assert key_empty[4] == (), "the empty-env key must be asserted unchanged"
    assert key_observed[4] != key_empty[4]
    assert key_observed[:4] == key_empty[:4]
    assert len(key_observed) == 5, "cache_key stays exactly five-tuple-shaped -- no sixth component"


def test_observation_record_closed_refusal_list() -> None:
    """§16.2.1's CLOSED record, extended by §17.3 (move-family increment,
    T51) with `arm_slots`: exactly these five keys, no others. This is the
    "fails if `plr_observation` grows an unnamed key" test the T40 task
    row names -- against :data:`oracle_common.OBSERVATION_KEYS`, the same
    constant `observation_env_members` and
    `training/tests/test_verify_postconditions.py`'s own closed-list
    assertion (against a REAL `verify()` run) both key off.
    """
    from oracle_common import OBSERVATION_KEYS

    assert OBSERVATION_KEYS == {
        "backend_class", "num_channels", "head_channels", "deck_resource_names",
        "arm_slots",
    }
    assert set(_SAMPLE_OBSERVATION) == OBSERVATION_KEYS, (
        "a sixth key on the sample fixture itself would mean this test file's "
        "own fixture has drifted from the closed record -- fix the fixture, "
        "not the constant"
    )


def test_obs_prefix_never_satisfies_e_uncond_way2() -> None:
    """§16.2.3's reservation claim: `E-UNCOND` way (2) matches a bare
    zero-argument callee NAME against `env` via
    ``_HYPOTHESIS_ENTRY_RE = re.compile(r"^if (\\w+)\\(\\)$")``
    (`plr_sema/src/plr_sema/check/predicate.py:721`). ``\\w+`` admits
    neither ``:`` nor ``=``, so no ``obs:<key>=<value>`` member can ever
    equal the captured group -- no observation can manufacture
    reachability. Checked against the REAL regex, not a restatement of it.
    """
    from oracle_common import observation_env_members
    from plr_sema.check.predicate import _HYPOTHESIS_ENTRY_RE

    members = observation_env_members(
        _SAMPLE_OBSERVATION, {"tip_rack": {}, "source_plate": {}, "dest_plate": {}}
    )
    assert members, "sanity: the fixture record must actually produce members"
    for member in members:
        assert member.startswith("obs:")
        assert _HYPOTHESIS_ENTRY_RE.match(f"if {member}()") is None
    # `does_volume_tracking` (the one existing member) is untouched: it has
    # no `obs:` prefix and is exactly the shape way (2) is meant to match.
    assert _HYPOTHESIS_ENTRY_RE.match("if does_volume_tracking()") is not None


# ---------------------------------------------------------------------------
# AC-17.5 (spec 260909_plr-sema-move-family-increment.md S17.5.1, T54, M3):
# the `caller_args_sites` wire round trip. `caller_args_sites` participates
# in `contracts_sha` automatically (an additive top-level-guard field, same
# as `caller_args`/`bindings`/`reachability_clear` before it), so no
# separate cache-key plumbing is needed for that half -- these two tests
# check the two things that ARE new: the per-site data survives a JSON
# round trip, and a table carrying only the OLD `caller_args` key still
# decides `:375` exactly as before T54.
# ---------------------------------------------------------------------------


def test_t54_caller_args_sites_round_trip_preserves_linenos(contracts_json: str) -> None:
    """The real, unmodified `LiquidHandler.move_resource` contract entry's
    `:375` guard carries `caller_args_sites` with all THREE admitted
    `_check_args` call-site linenos (`:2079`, `:2345`, `:2364`), and a
    plain `json.dumps`/`json.loads` round trip preserves every one of
    them, plus each site's own `caller_qualname` string -- the wire shape
    is ordinary JSON, no custom encoding step."""
    payload = json.loads(contracts_json)
    entry = payload["contracts"]["LiquidHandler.move_resource"]
    (guard_375,) = [g for g in entry["guards"] if g["site"]["lineno"] == 375]
    sites = guard_375["caller_args_sites"]
    assert sites is not None
    linenos = sorted(s["lineno"] for s in sites)
    assert linenos == [2079, 2345, 2364]
    round_tripped = json.loads(json.dumps(sites))
    assert sorted(s["lineno"] for s in round_tripped) == linenos
    assert all(isinstance(s["caller_qualname"], str) and s["caller_qualname"] for s in round_tripped)


_T54_PICK_UP_TIPS_GRAPH = json.dumps(
    {
        "protocol_fqn": "test.t54_fallback",
        "operations": [
            {
                "id": "op_1",
                "method_name": "pick_up_tips",
                "receiver_variable": "lh",
                "receiver_type": "LiquidHandler",
                "arguments": {"use_channels": "[0, 1]"},
            }
        ],
        "resources": {},
    }
)


def _t54_obs_env() -> "frozenset[str]":
    return frozenset(
        {
            'obs:backend_class="LiquidHandlerChatterboxBackend"',
            "obs:num_channels=8",
            "obs:head_channels=[0,1,2,3,4,5,6,7]",
        }
    )


def test_t54_pre_t54_table_missing_caller_args_sites_still_decides_pick_up_tips_375(contracts_json: str) -> None:
    """AC-17.5's wire round trip, second half: with `LiquidHandler.pick_up_
    tips`'s own `:375` guard's `caller_args_sites` forced back to `None`
    (simulating a pre-T54 table, or a closure whose own site set S17.5.1's
    fail-closed conditions declined), `check_graph` still decides `:375`
    `SAFE` -- `_eval_check_args_missing_site_rule` falls back to the
    unchanged `caller_args` field exactly as it did before T54."""
    from plr_sema.verdict import Verdict

    payload = json.loads(contracts_json)
    entry = payload["contracts"]["LiquidHandler.pick_up_tips"]
    (guard_375,) = [g for g in entry["guards"] if g["site"]["lineno"] == 375]
    assert guard_375["caller_args_sites"] is not None  # sanity: T54 populates it today.
    assert guard_375["caller_args"] is not None  # sanity: the OLD field is still there too.
    stripped_guard = dict(guard_375)
    stripped_guard["caller_args_sites"] = None
    new_entry = dict(entry)
    new_entry["guards"] = [stripped_guard if g["site"]["lineno"] == 375 else g for g in entry["guards"]]
    payload["contracts"] = dict(payload["contracts"])
    payload["contracts"]["LiquidHandler.pick_up_tips"] = new_entry
    synthetic = json.dumps(payload)

    report = check_graph(_T54_PICK_UP_TIPS_GRAPH, synthetic, env=_t54_obs_env())
    findings = [
        f
        for f in report.findings
        if f.plr_site.lineno == 375 and f.plr_site.qualname == "LiquidHandler._check_args" and f.operation_id == "op_1"
    ]
    assert len(findings) == 1
    assert findings[0].verdict is Verdict.SAFE
