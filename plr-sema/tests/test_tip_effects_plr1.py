"""Spec 260929 §18 (`260929_plr-sema-plr1-tip-effect-increment.md`), backlog
#5622, task T57: the derived tip effects under PLR 1.0's rewritten
`TipTracker` -- R-A (backing-field alias), R-B (argument-classified helper
following), L1 (`effects_unresolved` -> widen in the bridge), R-C (entry reset
and the holder-less conjunct), plus AC-18.17's HM-25 thirteenth unit.

Each `test_ac_18_*` names one acceptance criterion sub-item. **Every synthetic
fixture is an inline source string: no test here reads a sibling worktree, and
none reads `outputs/pr159`** (CI cannot see either). The tests that read the
committed `plr-sema/data/derived_contracts.json` pin the regenerated artifact;
the ones that read `external/pylabrobot` pin the checked facts the derivation
leans on (the callback residual, the empty base closure).

The synthetic controls are the instrument check (rules/BATHOS.md): every
negative control below is written so that removing the rule it guards turns it
red -- (c), (d), (e), (l), (n) and (s) of AC-18.2 are the stub-defeating core.
"""

from __future__ import annotations

import ast
import dataclasses
import inspect
import json
import textwrap
from pathlib import Path

import pytest
from plr_sema._hand_maintained import BUDGET_CAP, REGISTRY, live_rows, resolve_measure
from plr_sema._provenance import survey_stamp
from plr_sema.check import check_graph
from plr_sema.derive import DroppedCall, SurveyRecord, build_index, default_plr_pkg_root
from plr_sema.derive import receiver_state as receiver_state_module
from plr_sema.derive.__main__ import build_derived_contracts_payload
from plr_sema.derive.receiver_state import (
    HAS_TIP,
    NO_TIP,
    UNRESOLVED,
    ReceiverState,
    _base_closure,
    _class_level_names,
    _direct_defs,
    _MethodEval,
    _write_events,
    analyze_tip_effects,
    build_plr_class_index,
    compute_channel_bridge,
    compute_channel_bridge_detailed,
    derive_receiver_states,
    receiver_state_to_json,
    reset_constructions_bind_no_optional_collaborator,
    tip_attribute_writers,
    tip_getter_dependencies,
    tip_getters_that_write,
)
from plr_sema.verdict import Verdict

PLR_SEMA_ROOT = Path(__file__).resolve().parents[1]
FIXTURES = PLR_SEMA_ROOT / "tests" / "fixtures"
CONTRACTS_JSON_PATH = PLR_SEMA_ROOT / "data" / "derived_contracts.json"


# ---------------------------------------------------------------------------
# Fixtures and helpers.
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def payload() -> dict:
    return json.loads(CONTRACTS_JSON_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def contracts_json() -> str:
    return CONTRACTS_JSON_PATH.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def plr_classes() -> dict[str, ast.ClassDef]:
    classes, _modules = build_plr_class_index(default_plr_pkg_root())
    return classes


def _class(source: str, name: str = "C") -> ast.ClassDef:
    tree = ast.parse(textwrap.dedent(source))
    return next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name == name)


#: A holder-less tracker skeleton: `_view` is the bool-view property, backed
#: by `_carried`; `T` (the tip type) derives to "Tip" from the annotation.
_HEADER = '''
class C:
    def __init__(self):
        self._carried: Optional["Tip"] = None

    @property
    def _view(self):
        return self._carried

    def _put(self, tip):
        self._carried = tip
'''


def _tracker(methods: str, *, header: str = _HEADER, **kw):
    """`analyze_tip_effects` over `header` + `methods` (already 4-space
    indented relative to a class body), state fields `("_view",)`."""
    src = textwrap.dedent(header) + textwrap.indent(textwrap.dedent(methods), "    ")
    fields = kw.pop("fields", ("_view",))
    class_nodes = kw.pop("class_nodes", None)
    return analyze_tip_effects(_class(src), fields, class_nodes, **kw)


# ---------------------------------------------------------------------------
# AC-18.1 -- R-A, the backing-field alias.
# ---------------------------------------------------------------------------


def test_ac_18_1_regenerated_artifact_pins_the_backing_field(payload: dict) -> None:
    assert payload["receiver_state"]["LiquidHandler"]["effect_backing_fields"] == ["_carried"]
    assert payload["receiver_state"]["LiquidHandlerBackend"]["effect_backing_fields"] == ["_carried"]


def _alias(getter_body: str, *, extra: str = "") -> tuple[str, ...]:
    src = f"class C:\n    def __init__(self):\n        pass\n    @property\n    def _view(self):\n{textwrap.indent(textwrap.dedent(getter_body), '        ')}\n{extra}"
    return analyze_tip_effects(_class(src), ("_view",)).backing_fields


def test_ac_18_1_a_bare_self_return_aliases() -> None:
    assert _alias("return self._x") == ("_x",)


def test_ac_18_1_b_cast_wrapped_return_does_not_alias() -> None:
    """The stub-defeating half: an implementation that aliases every
    `self.X` anywhere in the getter passes (a), (c), (d) and fails here."""
    assert _alias("return cast(Optional['Tip'], self._before)") == ()


def test_ac_18_1_c_property_chain_aliases_the_backing_field_once() -> None:
    src = """
    class C:
        def __init__(self):
            pass
        @property
        def _pending_tip(self):
            return self._carried
        @property
        def _tip(self):
            if self._before is _SENTINEL:
                return self._pending_tip
            return cast(Optional["Tip"], self._before)
    """
    result = analyze_tip_effects(_class(src), ("_pending_tip", "_tip"))
    assert result.backing_fields == ("_carried",)


def test_ac_18_1_d_holder_attribute_return_contributes_nothing() -> None:
    body = """
    holder = self._holder
    if holder is None:
        return self._carried
    return holder.tip
    """
    assert _alias(body) == ("_carried",)  # `holder.tip` adds nothing; only `_carried` joins


def test_ac_18_1_e_two_property_cycle_terminates() -> None:
    src = """
    class C:
        @property
        def _a(self):
            return self._b
        @property
        def _b(self):
            return self._a
    """
    assert analyze_tip_effects(_class(src), ("_a",)).backing_fields == ()


def test_ac_18_1_f_direct_method_return_is_not_a_tip() -> None:
    body = "return self.helper"
    extra = "    def helper(self):\n        return None\n"
    assert _alias(body, extra=extra) == ()


def test_ac_18_1_tripwires_hold_over_the_pinned_tracker(plr_classes: dict[str, ast.ClassDef]) -> None:
    tt = plr_classes["TipTracker"]
    result = analyze_tip_effects(tt, ("_pending_tip", "_tip"), plr_classes)
    assert result.backing_fields == ("_carried",)
    bool_view = tip_getter_dependencies(tt, "_pending_tip", result.backing_fields)
    all_getters = bool_view | tip_getter_dependencies(tt, "_tip", result.backing_fields)
    assert bool_view == frozenset({"_holder_ref"})
    assert all_getters == frozenset({"_holder_ref", "_before"})
    writers = tip_attribute_writers(tt, all_getters)
    assert writers["_holder_ref"] == ("__init__",)
    assert writers["_before"] == ("__init__", "_hold", "_tip (setter)", "clear", "commit", "load_state", "rollback")
    # tripwire (i): the bool-view getter's own dependencies are written by nobody but __init__.
    assert all(set(writers[a]) <= {"__init__"} for a in bool_view)
    # tripwire (ii): no getter writes a self attribute.
    assert tip_getters_that_write(tt) == ()


_LOCAL_THROUGH = '''
class C:
    def __init__(self):
        self._holder_ref = None
        self._carried = None

    @property
    def _holder(self):
        return self._holder_ref

    @property
    def _view(self):
        holder = self._holder
        if holder is None:
            return self._carried
        return holder.tip

    def rebind(self, h):
        self._holder_ref = h
'''


def test_ac_18_1_local_through_dependency_is_seen_and_a_rebind_fails_tripwire_i() -> None:
    """The r2 C8 control: a scan of return expressions alone would miss
    `holder = self._holder`; the scan covers the whole getter body, so
    `_holder_ref` is a dependency and `rebind` -- its second writer -- is
    visible."""
    cls = _class(_LOCAL_THROUGH)
    backing = analyze_tip_effects(cls, ("_view",)).backing_fields
    deps = tip_getter_dependencies(cls, "_view", backing)
    assert deps == frozenset({"_holder_ref"})
    writers = tip_attribute_writers(cls, deps)["_holder_ref"]
    assert writers == ("__init__", "rebind")
    assert not set(writers) <= {"__init__"}, "tripwire (i) must fail on this counter-class"


def test_ac_18_1_new_writer_of_before_breaks_the_snapshot(plr_classes: dict[str, ast.ClassDef]) -> None:
    """A synthetic new writer of `_before` changes the pinned snapshot (r2 C9)."""
    src = ast.unparse(plr_classes["TipTracker"]) + "\n    def sneaky(self, t):\n        self._before = t\n"
    mutated = _class(src, "TipTracker")
    pinned = ("__init__", "_hold", "_tip (setter)", "clear", "commit", "load_state", "rollback")
    assert tip_attribute_writers(mutated, ("_before",))["_before"] != pinned
    assert "sneaky" in tip_attribute_writers(mutated, ("_before",))["_before"]


def test_ac_18_1_a_getter_that_assigns_makes_tripwire_ii_fail() -> None:
    src = """
    class C:
        @property
        def _view(self):
            self._cache = 1
            return self._carried
    """
    assert tip_getters_that_write(_class(src)) == ("_view",)


def test_ac_18_1_assignment_to_setter_bearing_state_field_is_unresolved() -> None:
    """M3: `_tip`'s setter writes only `_before`, so `self._tip = t` is NOT a
    write of the merged cell. It classifies UNRESOLVED, never `HAS_TIP`."""
    src = """
    class C:
        def __init__(self):
            self._carried: Optional["Tip"] = None
        @property
        def _pending_tip(self):
            return self._carried
        @property
        def _tip(self):
            return self._pending_tip
        @_tip.setter
        def _tip(self, tip):
            self._before = tip
        def set_tip(self, t: Tip):
            self._tip = t
    """
    result = analyze_tip_effects(_class(src), ("_pending_tip", "_tip"))
    assert result.effects == {}
    assert result.effects_unresolved == ("set_tip",)


# ---------------------------------------------------------------------------
# AC-18.2 -- R-B, helper following, and its synthetic controls.
# ---------------------------------------------------------------------------


def test_ac_18_2_regenerated_artifact_pins_effects(payload: dict) -> None:
    """If any value differs, T57 stops and records the measured value with
    its cause; it does not edit the expectation to match."""
    for receiver in ("LiquidHandler", "LiquidHandlerBackend"):
        rs = payload["receiver_state"][receiver]
        assert rs["effects"] == {"add_tip": "HAS_TIP", "clear": "NO_TIP", "remove_tip": "NO_TIP"}
        assert rs["effects_unresolved"] == ["load_state"]
        assert rs["effects_max_depth"] == 2
    assert payload["receiver_state"]["LiquidHandler"]["entry_reset"] == {"method": "setup", "post": "no_tip"}


def test_ac_18_2_real_tracker_selection_matches_the_reading(plr_classes: dict[str, ast.ClassDef]) -> None:
    """§18.4.9's per-method table, measured on the real 1.0 class."""
    result = analyze_tip_effects(plr_classes["TipTracker"], ("_pending_tip", "_tip"), plr_classes)
    r = result.results
    assert (r["add_tip"], r["remove_tip"], r["clear"]) == (HAS_TIP, NO_TIP, NO_TIP)
    assert r["load_state"] == UNRESOLVED
    assert (r["rollback"], r["commit"]) == ("UNTOUCHED", "UNTOUCHED")
    assert (r["_hold"], r["_put"]) == (UNRESOLVED, UNRESOLVED)  # entry `Optional["Tip"]`
    assert r["__init__"] == NO_TIP
    assert result.constructor_state == NO_TIP
    assert result.tip_type == "Tip"
    assert result.effects_max_depth == 2  # add_tip -> _hold -> _put


def test_ac_18_2_a_depth_three_chain_is_unbounded() -> None:
    result = _tracker(
        """
        def add(self, tip: Tip):
            self._a(tip)
        def _a(self, t):
            self._b(t)
        def _b(self, t):
            self._c(t)
        def _c(self, t):
            self._carried = t
        """
    )
    assert result.effects == {"add": HAS_TIP}
    assert result.effects_max_depth == 3, "the depth is unbounded, not fixed at 2"


def test_ac_18_2_b_no_alias_no_effect() -> None:
    result = _tracker(
        """
        def add(self, tip: Tip):
            self._a(tip)
        def _a(self, t):
            self._b(t)
        def _b(self, t):
            self._c(t)
        def _c(self, t):
            self._other = t
        """
    )
    assert result.backing_fields == ("_carried",)
    assert result.effects == {} and result.effects_unresolved == ()


_OLD_SHAPE = '''
class C:
    def __init__(self):
        self._pending_tip: Optional["Tip"] = None
        self._tip: Optional["Tip"] = None
'''


def test_ac_18_2_c_zero_argument_copy_helper_does_not_poison() -> None:
    result = _tracker(
        """
        def commit(self):
            self._tip = self._pending_tip
        def add(self, tip: Tip):
            self._pending_tip = tip
            self.commit()
        """,
        header=_OLD_SHAPE,
        fields=("_pending_tip", "_tip"),
    )
    assert result.effects == {"add": HAS_TIP}
    assert result.results["commit"] == "UNTOUCHED"


def test_ac_18_2_d_zero_argument_constant_helper_propagates() -> None:
    """The recon's >=1-argument filter fails this one."""
    result = _tracker(
        """
        def clear(self):
            self._put(None)
        def reset(self):
            self.clear()
        """
    )
    assert result.effects == {"clear": NO_TIP, "reset": NO_TIP}


def test_ac_18_2_e_both_kinds_is_unresolved_not_omitted() -> None:
    result = _tracker(
        """
        def m(self, c, t: Tip):
            if c:
                self._carried = None
            else:
                self._carried = t
        """
    )
    assert result.effects == {} and result.effects_unresolved == ("m",)


def test_ac_18_2_f_conditional_none_local_is_unresolved() -> None:
    result = _tracker(
        """
        def load(self, d):
            pending = Tip.deserialize(d) if d is not None else None
            self._put(pending)
        """
    )
    assert result.effects_unresolved == ("load",)


def test_ac_18_2_g_optional_entry_parameter_is_unresolved() -> None:
    result = _tracker(
        """
        def set(self, tip: Optional[Tip]):
            self._put(tip)
        """
    )
    assert result.effects_unresolved == ("set",)


def test_ac_18_2_h_cycle_terminates_unresolved() -> None:
    # Same polarity on both sides on purpose: a mixed-polarity cycle is
    # UNRESOLVED whatever the guard does, so it could not tell the guard's
    # UNRESOLVED from a guard that contributed nothing.
    result = _tracker(
        """
        def a(self):
            self._carried = None
            self.b()
        def b(self):
            self._carried = None
            self.a()
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("a", "b")


#: F3: every case writes a DEFAULTED parameter (or an argument bound to a
#: constant `None`), so that if the binding rule under test were removed the
#: callee would classify `NO_TIP`, not `UNRESOLVED` -- the controls can fail.
_BINDING_CALLEES = """
    def _two(self, a, b=None):
        self._carried = b
    def _va(self, a, *rest):
        self._carried = a
    def _kwa(self, a, **k):
        self._carried = a
    def _po(self, a, /, b=None):
        self._carried = a
    def _one(self, tip=None):
        self._carried = tip
"""

_BINDING_SHAPES = {
    "starred_call_site": "self._two(*xs)",
    "double_star_call_site": "self._two(**kw)",
    "callee_varargs": "self._va(None)",
    "callee_varkwargs": "self._kwa(None)",
    "too_many_positionals": "self._two(None, None, None)",
    "unknown_keyword": "self._two(None, c=None)",
    "keyword_at_positional_only": "self._po(a=None)",
    "same_parameter_bound_twice": "self._one(None, tip=None)",
}


@pytest.mark.parametrize("shape", sorted(_BINDING_SHAPES))
def test_ac_18_2_i_o_binding_rules_refuse_inadmissible_calls(shape: str) -> None:
    result = _tracker(_BINDING_CALLEES + f"\n    def m(self, xs, kw):\n        {_BINDING_SHAPES[shape]}\n")
    assert result.effects == {}, result.effects
    assert result.effects_unresolved == ("m",), shape


@pytest.mark.parametrize(
    "call",
    ["self._two(None, None)", "self._two(None)", "self._two(a=None)", "self._po(None)", "self._one()", "self._one(tip=None)"],
)
def test_ac_18_2_i_o_admissible_calls_bind_normally(call: str) -> None:
    """The positive controls: the same callees, called in a way Python binds,
    give the written value's class (`None` -> NO_TIP), not UNRESOLVED."""
    result = _tracker(_BINDING_CALLEES + f"\n    def m(self):\n        {call}\n")
    assert result.effects == {"m": NO_TIP}, call


def test_ac_18_2_i_o_bound_parameter_takes_the_argument_class_not_the_default() -> None:
    result = _tracker(_BINDING_CALLEES + "\n    def m(self, t: Tip):\n        self._two(None, t)\n")
    assert result.effects == {"m": HAS_TIP}, "b is bound to `t` (HAS_TIP), not left at its `None` default"


def test_ac_18_2_j_callable_attribute_is_not_followed() -> None:
    result = _tracker(
        """
        def fire(self):
            self._callback()
        """
    )
    assert result.results["fire"] == "UNTOUCHED"
    assert result.effects == {} and result.effects_unresolved == ()


def test_ac_18_2_k_inherited_helper_is_not_followed() -> None:
    src = """
    class Base:
        def _h(self, t):
            self._carried = t
    class C(Base):
        def __init__(self):
            self._carried: Optional["Tip"] = None
        @property
        def _view(self):
            return self._carried
        def add(self, tip: Tip):
            self._h(tip)
    """
    tree = ast.parse(textwrap.dedent(src))
    nodes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    result = analyze_tip_effects(nodes["C"], ("_view",), nodes)
    assert result.results["add"] == "UNTOUCHED", "an inherited helper is invisible (old P4's posture)"


def test_ac_18_2_k_no_class_in_the_pinned_base_closure_assigns_a_write_target(
    plr_classes: dict[str, ast.ClassDef],
) -> None:
    """The whole-surface half of (k): the residual becomes a checked fact."""
    tt = plr_classes["TipTracker"]
    result = analyze_tip_effects(tt, ("_pending_tip", "_tip"), plr_classes)
    write_fields = {"_pending_tip", "_tip"} | set(result.backing_fields)
    for base in _base_closure(tt, plr_classes):
        assert not (_class_level_names(base) & write_fields), base.name
        for defs in _direct_defs(base).values():
            for d in defs:
                for ev in _write_events(d):
                    assert ev.attr not in write_fields, (base.name, d.name, ev)


def test_ac_18_2_l_old_pin_load_state_shape_is_unresolved_inline() -> None:
    """The old pin's `load_state`, as an INLINE fixture (no test reads a
    sibling worktree, because CI cannot see one)."""
    result = _tracker(
        """
        def load_state(self, state):
            self._tip = cast(Optional[Tip], deserialize(state.get("tip")))
        """,
        header=_OLD_SHAPE,
        fields=("_pending_tip", "_tip"),
    )
    assert result.effects == {} and result.effects_unresolved == ("load_state",)


def test_ac_18_2_m_value_forms_are_unresolved() -> None:
    result = _tracker(
        """
        def m1(self, x):
            self._carried = f(x)
        def m2(self, state):
            self._carried = state["t"]
        def m3(self, x):
            self._carried = x or None
        async def m4(self):
            self._carried = await g()
        def m5(self):
            self._carried = self.backend.tip
        def m6(self):
            self._carried = "a"
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("m1", "m2", "m3", "m4", "m5", "m6")


def test_ac_18_2_n_rebound_parameter_joins_and_is_unresolved() -> None:
    """The negative control: `tip` rebound to `None` on one path must not stay
    `HAS_TIP` just because the argument was."""
    result = _tracker(
        """
        def _put2(self, tip, c):
            if c:
                tip = None
            self._carried = tip
        def add(self, t: Tip, c):
            self._put2(t, c)
        def _put3(self, tip, xs):
            for tip in xs:
                pass
            self._carried = tip
        def add3(self, t: Tip, xs):
            self._put3(t, xs)
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("add", "add3")


def test_ac_18_2_o_binding_catch_alls() -> None:
    result = _tracker(
        """
        @staticmethod
        def _static(tip):
            pass
        @classmethod
        def _cls(cls, tip):
            pass
        def m_static(self, t: Tip):
            self._static(t)
        def m_cls(self, t: Tip):
            self._cls(t)
        def _imp(self, tip):
            import tip
            self._carried = tip
        def m_imp(self, t: Tip):
            self._imp(t)
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("m_cls", "m_imp", "m_static")
    # The too-many-positionals / unknown-keyword shapes (whose old versions here
    # passed with the rules removed) live in `_BINDING_SHAPES` above.


def test_ac_18_2_p_order_independence() -> None:
    methods_a = ["""
        def add(self, tip: Tip):
            self._a(tip)
        """, """
        def _a(self, t):
            self._b(t)
        """, """
        def _b(self, t):
            self._carried = t
        """, """
        def clear(self):
            self._put(None)
        """]
    outcomes = set()
    for order in (methods_a, list(reversed(methods_a)), methods_a[2:] + methods_a[:2]):
        for memoize in (True, False):
            result = _tracker("".join(order), memoize=memoize)
            outcomes.add((result.effects_max_depth, tuple(sorted(result.effects.items()))))
    assert outcomes == {(2, (("add", HAS_TIP), ("clear", NO_TIP)))}


def test_ac_18_2_q_callback_residual_is_a_checked_fact(plr_classes: dict[str, ast.ClassDef]) -> None:
    """C15 (a): every `register_callback` argument in `LiquidHandler` is
    exactly `self._state_updated`, and `LiquidHandler` defines no
    `_state_updated` of its own (so it resolves to `Resource._state_updated`,
    a notifier that writes no tracker field)."""
    lh = plr_classes["LiquidHandler"]
    calls = [
        n
        for n in ast.walk(lh)
        if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "register_callback"
    ]
    assert calls, "the check would be vacuous"
    for call in calls:
        assert len(call.args) == 1 and not call.keywords
        assert ast.unparse(call.args[0]) == "self._state_updated"
    defined = {n.name for n in lh.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
    assert "_state_updated" not in defined
    resource = plr_classes["Resource"]
    (notifier,) = [
        n for n in resource.body if isinstance(n, ast.FunctionDef) and n.name == "_state_updated"
    ]
    assert [ast.unparse(n.func) for n in ast.walk(notifier) if isinstance(n, ast.Call)] == ["callback", "self.serialize_state"]


def test_ac_18_2_r_local_fixpoint() -> None:
    self_ref = _tracker(
        """
        def m(self):
            tip = tip
            self._carried = tip
        """
    )
    assert self_ref.effects_unresolved == ("m",)
    mutual = _tracker(
        """
        def m(self):
            a = b
            b = a
            self._carried = a
        """
    )
    assert mutual.effects_unresolved == ("m",)
    grounded = _tracker(
        """
        def m(self):
            a = None
            a = a
            self._carried = a
        """
    )
    assert grounded.effects == {"m": NO_TIP}
    kleene = _tracker(
        """
        def m(self):
            a = b
            b = a
            b = None
            self._carried = a
        def m2(self):
            a = b
            b = a
            b = None
            self._carried = b
        """
    )
    assert kleene.effects == {"m": NO_TIP, "m2": NO_TIP}, "Kleene iteration grounds `a` through `b = None`"


def test_ac_18_2_r_fixpoint_is_query_order_independent() -> None:
    fn = ast.parse(
        textwrap.dedent(
            """
            def m(self):
                a = b
                b = a
                b = None
            """
        )
    ).body[0]
    ev = _MethodEval(fn, {}, frozenset({"_carried"}))
    a, b = ast.Name(id="a", ctx=ast.Load()), ast.Name(id="b", ctx=ast.Load())
    first = (ev.classify(a), ev.classify(b))
    ev2 = _MethodEval(fn, {}, frozenset({"_carried"}))
    second = (ev2.classify(b), ev2.classify(a))
    assert first == (NO_TIP, NO_TIP) and second == (NO_TIP, NO_TIP)


_TIP_TYPES = [
    ("def add(self, tip): self._put(tip)", False),
    ("def add(self, tip: Any): self._put(tip)", False),
    ("def add(self, tip: Union[Tip, None]): self._put(tip)", False),
    ("def add(self, tip: MaybeTip): self._put(tip)", False),
    ("def add(self, tip: None | Tip | X): self._put(tip)", False),
    ("def add(self, tip: Optional[Tip]): self._put(tip)", False),
    ("def add(self, tip: 'Optional[Tip]'): self._put(tip)", False),
    ("def add(self, tip: Tip = None): self._put(tip)", False),
    ("def add(self, tip: object): self._put(tip)", False),
    ("def add(self, tip: Other): self._put(tip)", False),
    ("def add(self, tip: Tip): self._put(tip)", True),
    ("def add(self, tip: mod.Tip): self._put(tip)", True),
    ("def add(self, tip: 'Tip'): self._put(tip)", True),
]


@pytest.mark.parametrize(("method", "positive"), _TIP_TYPES)
def test_ac_18_2_s_entry_context_allowlist(method: str, positive: bool) -> None:
    result = _tracker(method)
    if positive:
        assert result.effects == {"add": HAS_TIP}
    else:
        assert result.effects == {} and result.effects_unresolved == ("add",), result


def test_ac_18_2_s_non_singleton_tip_type_gives_nothing_a_tip() -> None:
    header = '''
class C:
    def __init__(self):
        self._carried: Optional["Tip"] = None
        self._other: Optional["Other"] = None
    @property
    def _view(self):
        return self._carried
    @property
    def _view2(self):
        return self._other
    def _put(self, tip):
        self._carried = tip
'''
    result = _tracker(
        """
        def add(self, tip: Tip):
            self._put(tip)
        """,
        header=header,
        fields=("_view", "_view2"),
    )
    assert result.tip_type is None
    assert result.effects == {} and result.effects_unresolved == ("add",)


def test_ac_18_2_t_write_catch_alls_are_unresolved() -> None:
    result = _tracker(
        """
        def t1(self, xs):
            for self._carried in xs:
                pass
        def t2(self, f):
            with f() as self._carried:
                pass
        def t3(self, t):
            setattr(self, "_carried", t)
        def t4(self, name, t):
            setattr(self, name, t)
        def t5(self, t):
            object.__setattr__(self, "_carried", t)
        def t6(self):
            delattr(self, "_carried")
        def t7(self, t):
            self.__dict__["_carried"] = t
        def t8(self, t):
            vars(self)["_carried"] = t
        def t9(self):
            helper(self)
        def t10(self, t):
            self.__setattr__("_carried", t)
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == tuple(f"t{i}" for i in (1, 10, 2, 3, 4, 5, 6, 7, 8, 9))
    fine = _tracker(
        """
        def ok(self):
            helper(self.thing)
        """
    )
    assert fine.results["ok"] == "UNTOUCHED", "an attribute read is not an escape of `self`"


def test_ac_18_2_t_bare_self_escape_x1() -> None:
    result = _tracker(
        """
        def _h(self, p, t):
            p._carried = t
        def add(self, t: Tip):
            self._h(self, t)
        def alias(self, t: Tip):
            me = self
            me._carried = t
        def clear2(self):
            t = self
            t._put(None)
        def _sole(self, tip):
            self._carried = tip
        def add_ok(self, tip: Tip):
            self._sole(tip)
        """
    )
    assert result.effects == {"add_ok": HAS_TIP}, "the 1.0 add_tip shape (attribute bases only) is unaffected"
    assert result.effects_unresolved == ("add", "alias", "clear2")


def test_ac_18_2_u_class_level_bindings_are_not_plain_fields() -> None:
    plain = analyze_tip_effects(
        _class(
            """
            class C:
                def __init__(self):
                    self._pending: Optional["Tip"] = None
                def set_none(self):
                    self._pending = None
                def set_tip(self, t: Tip):
                    self._pending = t
            """
        ),
        ("_pending",),
    )
    assert plain.effects == {"set_none": NO_TIP, "set_tip": HAS_TIP}, "control: a plain field keeps the old rule"

    prop_call = analyze_tip_effects(
        _class(
            """
            class C:
                def __init__(self):
                    self._carried: Optional["Tip"] = None
                _pending = property(get, set)
                def set_tip(self, t: Tip):
                    self._pending = t
            """
        ),
        ("_pending",),
    )
    assert prop_call.effects == {} and prop_call.effects_unresolved == ("set_tip",)

    cached = analyze_tip_effects(
        _class(
            """
            class C:
                @functools.cached_property
                def _pending(self):
                    return 1
                def set_tip(self, t: Tip):
                    self._pending = t
            """
        ),
        ("_pending",),
    )
    assert cached.effects == {} and cached.effects_unresolved == ("set_tip",)

    tree = ast.parse(
        textwrap.dedent(
            """
            class Base:
                @property
                def _pending(self):
                    return self._x
            class C(Base):
                def set_tip(self, t: Tip):
                    self._pending = t
            """
        )
    )
    nodes = {n.name: n for n in tree.body if isinstance(n, ast.ClassDef)}
    inherited = analyze_tip_effects(nodes["C"], ("_pending",), nodes)
    assert inherited.effects == {} and inherited.effects_unresolved == ("set_tip",)


def test_ac_18_2_effects_and_constructor_state_share_one_write_shape_set() -> None:
    """R-C(1): `__init__`'s `AnnAssign`-with-value is classified (over `W`,
    not `S`); an `__init__` with no write of `W` has no constructor state."""
    assert _tracker("").constructor_state == NO_TIP
    none = analyze_tip_effects(_class("class C:\n    def __init__(self):\n        self._other = None\n"), ("_view",))
    assert none.constructor_state is None


# ---------------------------------------------------------------------------
# Review fixes F1, F2, F4, F5, F6, F8 (T57 review, all fail-closed).
# ---------------------------------------------------------------------------


def test_review_f1_escaping_bound_method_is_unresolved() -> None:
    """F1: `f = self._put; f(None)`, `map(self._put, ...)` and
    `partial(self._put, None)()` write the tip cell through a method the call
    scan never sees as a `self.<h>(...)` call."""
    result = _tracker(
        """
        def alias(self):
            f = self._put
            f(None)
        def mapped(self):
            list(map(self._put, [None]))
        def partialed(self):
            functools.partial(self._put, None)()
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("alias", "mapped", "partialed")


def test_review_f1_direct_call_and_property_load_do_not_escape() -> None:
    """The negative controls: a direct call is still followed (NO_TIP, not
    UNRESOLVED) and a property load is not a bound-method escape."""
    result = _tracker(
        """
        def direct(self):
            self._put(None)
        def peek(self):
            x = self._view
            return x
        def peek_public(self):
            return self.mode
        @property
        def mode(self):
            return 1
        """
    )
    assert result.effects == {"direct": NO_TIP}
    assert result.effects_unresolved == ()
    assert result.results["peek"] == "UNTOUCHED" and result.results["peek_public"] == "UNTOUCHED"


def test_review_f2_deferred_write_in_a_nested_scope_is_unresolved() -> None:
    result = _tracker(
        """
        def m_def(self):
            def f():
                self._carried = None
            return f
        def m_lambda(self):
            return lambda: self._put(None)
        def m_class(self):
            class K:
                def go(inner):
                    return self
            return K
        """
    )
    assert result.effects == {}
    assert result.effects_unresolved == ("m_class", "m_def", "m_lambda")


def test_review_f2_nested_scope_not_touching_the_receiver_is_unchanged() -> None:
    result = _tracker(
        """
        def m_def(self):
            def f():
                return 1
            return f
        def m_lambda(self):
            return sorted([2, 1], key=lambda x: x)
        def m_write_and_clean_closure(self):
            self._put(None)
            return (lambda y: y)(1)
        """
    )
    assert result.results["m_def"] == "UNTOUCHED" and result.results["m_lambda"] == "UNTOUCHED"
    assert result.effects == {"m_write_and_clean_closure": NO_TIP}


def test_review_f4_tip_type_must_name_a_class() -> None:
    header = '''
class C:
    def __init__(self):
        self._carried: Optional[Any] = None
    @property
    def _view(self):
        return self._carried
    def _put(self, tip):
        self._carried = tip
'''
    typed_any = _tracker("def add(self, tip: Any):\n    self._put(tip)\n", header=header)
    assert typed_any.tip_type is None, "`Optional[Any]` must not derive T = 'Any'"
    assert typed_any.effects == {} and typed_any.effects_unresolved == ("add",)
    same_name_on_the_object = _tracker("def add(self, tip: object):\n    self._put(tip)\n", header=header.replace("Any", "object"))
    assert same_name_on_the_object.tip_type is None


def test_review_f4_tip_type_must_be_in_the_class_index_when_one_is_given() -> None:
    methods = "def add(self, tip: Tip):\n    self._put(tip)\n"
    absent = _tracker(methods, class_nodes={"Other": _class("class Other: pass", "Other")})
    assert absent.tip_type is None and absent.effects_unresolved == ("add",)
    present = _tracker(methods, class_nodes={"Tip": _class("class Tip: pass", "Tip")})
    assert present.tip_type == "Tip" and present.effects == {"add": HAS_TIP}


def test_review_f5_bottom_never_acts_as_join_identity_inside_ifexp() -> None:
    result = _tracker(
        """
        def m(self, c):
            a = b
            b = a
            self._carried = a if c else None
        """
    )
    assert result.effects == {} and result.effects_unresolved == ("m",)


def test_review_f6_receiver_is_the_first_parameter_not_the_literal_self() -> None:
    result = _tracker(
        """
        def m(this):
            this._carried = None
        def n(me, t: Tip):
            me._put(t)
        def o(this):
            setattr(this, "_carried", None)
        """
    )
    assert result.effects == {"m": NO_TIP, "n": HAS_TIP}
    assert result.effects_unresolved == ("o",)


def test_review_f6_super_setattr_and_delattr_are_setattr_events() -> None:
    result = _tracker(
        """
        def s1(self, t):
            super().__setattr__("_carried", t)
        def s2(self):
            super().__delattr__("_carried")
        def s3(self):
            return super().__repr__()
        """
    )
    assert result.effects_unresolved == ("s1", "s2")
    assert result.results["s3"] == "UNTOUCHED"


def test_review_f8_duplicate_non_property_names_are_unresolved() -> None:
    """Both definitions write the SAME polarity, so joining them would give NO_TIP;
    only the duplicate-name rule makes the result UNRESOLVED. A getter/setter
    pair (`mode`) is unaffected."""
    result = _tracker(
        """
        def wipe(self):
            self._put(None)
        def wipe(self):
            self._put(None)
        @property
        def mode(self):
            return 1
        @mode.setter
        def mode(self, v):
            self._before = v
        """
    )
    assert result.effects_unresolved == ("wipe",)
    assert result.results["mode"] == "UNTOUCHED"


def test_review_n1_method_without_a_positional_receiver_is_unresolved() -> None:
    """N1: with no positional parameter the receiver cannot be named
    (`args[0]._carried = None`), so the whole method is UNRESOLVED, not UNTOUCHED."""
    result = _tracker(
        """
        def n1(*args):
            args[0]._carried = None
        def n2(*, self):
            self._carried = None
        def ok(self):
            self._put(None)
        """
    )
    assert result.effects == {"ok": NO_TIP}, "a normal method is unaffected"
    assert result.effects_unresolved == ("n1", "n2")


def test_review_n2_static_and_class_methods_take_no_receiver() -> None:
    """N2: F6 made the first parameter the receiver, which would publish
    `other._carried = None` in a staticmethod (or `cls._carried = None` in a
    classmethod) as a NO_TIP effect on the instance. Both are UNRESOLVED as an
    entry, like `_followable`'s callee rule; a normal method is unaffected."""
    result = _tracker(
        """
        @staticmethod
        def sm(other):
            other._carried = None
        @classmethod
        def cm(cls):
            cls._carried = None
        @functools.wraps(f)
        @staticmethod
        def sm_wrapped(other):
            pass
        def normal(self):
            self._carried = None
        """
    )
    assert result.effects == {"normal": NO_TIP}
    assert result.effects_unresolved == ("cm", "sm", "sm_wrapped")


# ---------------------------------------------------------------------------
# AC-18.3 -- L1's widen mapping in the bridge.
# ---------------------------------------------------------------------------


def test_ac_18_3_regenerated_table_values(payload: dict) -> None:
    contracts = payload["contracts"]
    assert contracts["LiquidHandler.load_state"]["channel_effect"] == "widen"
    assert contracts["LiquidHandler.pick_up_tips"]["channel_effect"] == "HAS_TIP"
    assert contracts["LiquidHandler.drop_tips"]["channel_effect"] == "NO_TIP"
    assert payload["receiver_state_diagnostics"] == {"n_contracts_depth0_and_deep_coexist": 0}


def _bridge_fixture(
    depth0: list[str],
    depth1: list[str] = (),
    *,
    effects: dict[str, str] | None = None,
    unresolved: tuple[str, ...] = (),
    tracker_methods: set[str] | None = None,
    index_methods: set[str] | None = None,
) -> tuple[list[SurveyRecord], dict, ReceiverState]:
    """The synthetic records, survey index and receiver state for a bridge:
    receiver `R.op` bridges `self.head[c].<m>` at depth 0 (and, through
    delegate `R.helper`, at depth 1) into tracker `T`."""
    everything = set(depth0) | set(depth1)
    index_methods = everything if index_methods is None else index_methods
    tracker_methods = everything if tracker_methods is None else tracker_methods

    def rec(qual: str, cls: str | None, dropped: list[str], delegates: tuple[str, ...] = ()) -> SurveyRecord:
        return SurveyRecord(
            qualname=qual, class_name=cls, module="synthetic", file="<synthetic>", lineno=1, params=(),
            findings=(), delegates_to=delegates, unresolved_calls=(),
            dropped_calls=tuple(DroppedCall(expr=f"self.head[c].{m}", lineno=1, scope_trail=()) for m in dropped),
        )

    records = [rec("R.op", "R", depth0, ("helper",) if depth1 else ()), rec("R.helper", "R", list(depth1))]
    records += [rec(f"T.{m}", "T", []) for m in sorted(index_methods)]
    index = build_index(records)
    state = ReceiverState(
        channel_attr="head", tracker_class="T", tracker_module="synthetic", bool_view_attr="has",
        bool_view_field="_f", true_when="not_none", state_fields=("_f",), effects=dict(effects or {}),
        channel_default_param={}, channel_default_disablers=(), tip_state_exceptions=(),
        effects_unresolved=tuple(unresolved), tracker_methods=frozenset(tracker_methods),
    )
    return records, index, state


def _bridge(*args, **kwargs) -> tuple[str | None, bool]:
    """`(channel_effect, coexist)` of `R.op` over `_bridge_fixture(...)`."""
    _records, index, state = _bridge_fixture(*args, **kwargs)
    _guards, effect, coexist = compute_channel_bridge_detailed(
        ("synthetic", "R.op"), index, receiver_state=state, stamp=survey_stamp()
    )
    assert compute_channel_bridge(("synthetic", "R.op"), index, receiver_state=state, stamp=survey_stamp())[1] == effect
    return effect, coexist


def test_ac_18_3_control_a_resolved_depth0_bridge_keeps_its_effect() -> None:
    """The negative control that keeps every `widen` below honest."""
    assert _bridge(["add"], effects={"add": "HAS_TIP"}) == ("HAS_TIP", False)
    assert _bridge(["nothing"]) == (None, False), "a public method with no effect stays omitted"


def test_ac_18_3_unresolved_bridged_at_depth_0_is_widen_not_none() -> None:
    assert _bridge(["load"], unresolved=("load",)) == ("widen", False)


def test_ac_18_3_unresolved_bridged_at_depth_1_is_widen() -> None:
    assert _bridge([], ["load"], unresolved=("load",))[0] == "widen"


def test_ac_18_3_bridge_to_a_private_method_is_widen() -> None:
    assert _bridge(["_hidden"])[0] == "widen"


def test_ac_18_3_unresolved_takes_precedence_over_a_resolved_effect() -> None:
    assert _bridge(["add", "load"], effects={"add": "HAS_TIP"}, unresolved=("load",))[0] == "widen"


def test_ac_18_3_bridge_the_index_lacks_is_widen_before_the_index_skip() -> None:
    """r1 M1: an implementation that leaves rules 0-3 behind
    `if c_key not in index: continue` fails both of these."""
    assert _bridge(["ghost"], index_methods=set())[0] == "widen"
    # In the index (an inherited or module-level twin) but NOT a direct method of C:
    assert _bridge(["inherited"], tracker_methods=set(), index_methods={"inherited"})[0] == "widen"


def test_ac_18_3_depth0_and_deep_effects_coexisting_widen() -> None:
    """r1 M2: a depth-0 `HAS_TIP` with a depth-1 `NO_TIP` is `widen`, not
    `HAS_TIP` -- and the coexistence is reported for C14's counter."""
    assert _bridge(["add"], ["remove"], effects={"add": "HAS_TIP", "remove": "NO_TIP"}) == ("widen", True)
    assert _bridge([], ["remove"], effects={"remove": "NO_TIP"}) == ("widen", False), "deep-only stays E4.2's widen"


def test_review_f7_bridge_requires_tracker_methods() -> None:
    """F7: rule 0's direct-method half is required; a state that cannot
    supply it fails loudly instead of silently skipping the half."""
    _records, index, state = _bridge_fixture(["add"], effects={"add": "HAS_TIP"})
    bare = dataclasses.replace(state, tracker_methods=None)
    with pytest.raises(ValueError, match="tracker_methods is required"):
        compute_channel_bridge_detailed(("synthetic", "R.op"), index, receiver_state=bare, stamp=survey_stamp())
    with pytest.raises(ValueError, match="tracker_methods is required"):
        compute_channel_bridge(("synthetic", "R.op"), index, receiver_state=bare, stamp=survey_stamp())
    # ... and the same state WITH it bridges normally (the control).
    assert compute_channel_bridge(("synthetic", "R.op"), index, receiver_state=state, stamp=survey_stamp())[1] == "HAS_TIP"


def _coexist_count(depth0: list[str], depth1: list[str], effects: dict[str, str]) -> int:
    records, index, state = _bridge_fixture(depth0, depth1, effects=effects)
    payload = build_derived_contracts_payload(records, index, survey_stamp(), receiver_states={"R": state})
    return payload["receiver_state_diagnostics"]["n_contracts_depth0_and_deep_coexist"]


def test_review_f9_coexistence_counter_reads_one_on_a_coexisting_contract() -> None:
    """F9: the positive control for C14's published counter -- 1 when one
    contract carries a depth-0 and a deep resolved effect, and 0 for the
    depth-0-only, deep-only and empty controls."""
    assert _coexist_count(["add"], ["remove"], {"add": "HAS_TIP", "remove": "NO_TIP"}) == 1
    assert _coexist_count(["add"], [], {"add": "HAS_TIP"}) == 0
    assert _coexist_count([], ["remove"], {"remove": "NO_TIP"}) == 0
    assert _coexist_count([], [], {}) == 0


def _op(op_id: str, method: str, **arguments: str) -> dict:
    return {
        "arguments": dict(arguments), "condition_expr": None, "creates_state": [], "depends_on_params": [],
        "false_branch": [], "foreach_body": [], "foreach_source": None, "id": op_id, "line_number": 0,
        "method_name": method, "node_type": "static", "preconditions": [], "receiver_type": "LiquidHandler",
        "receiver_variable": "lh", "true_branch": [],
    }


def _graph(*ops: dict) -> str:
    base = json.loads((FIXTURES / "double_pickup_graph.json").read_text(encoding="utf-8"))
    base["operations"] = list(ops)
    base["execution_order"] = [o["id"] for o in ops]
    return json.dumps(base)


def _will_fail(report, op_id: str) -> list:
    return [f for f in report.findings if f.operation_id == op_id and f.verdict is Verdict.WILL_FAIL]


def test_ac_18_3_load_state_between_two_pickups_gives_no_will_fail(contracts_json: str) -> None:
    """The check-level fixture: the third operation would be a WILL_FAIL under
    the OLD `HAS_TIP` mapping of `load_state`. That is the old unsoundness."""
    graph = _graph(
        _op("op_1", "pick_up_tips", use_channels="[0]"),
        _op("op_2", "load_state", state="[0]"),
        _op("op_3", "pick_up_tips", use_channels="[0]"),
    )
    report = check_graph(graph, contracts_json)
    assert _will_fail(report, "op_3") == []

    # Negative controls. At this pin `load_state` names no channel parameter,
    # so its channel set is Top and even the OLD `HAS_TIP` mapping widens at
    # check time (E4 condition 1) -- the old unsoundness is only reachable
    # when a channel set resolves. Give the receiver a channel-default
    # parameter for `load_state` (a mutated copy of the table), and the OLD
    # mapping fires on op_3 while the NEW `widen` does not.
    def mutated(effect: str) -> str:
        table = json.loads(contracts_json)
        table["contracts"]["LiquidHandler.load_state"]["channel_effect"] = effect
        table["receiver_state"]["LiquidHandler"]["channel_default_param"]["load_state"] = "state"
        return json.dumps(table)

    assert _will_fail(check_graph(graph, mutated("HAS_TIP")), "op_3"), "the control must be able to fail"
    assert _will_fail(check_graph(graph, mutated("widen")), "op_3") == [], "widen is what removes it"


# ---------------------------------------------------------------------------
# AC-18.4 -- R-C, entry reset, and L7's atomicity.
# ---------------------------------------------------------------------------


def test_ac_18_4_a_entry_reset_on_the_regenerated_table(payload: dict) -> None:
    assert payload["receiver_state"]["LiquidHandler"]["entry_reset"] == {"method": "setup", "post": "no_tip"}
    assert "entry_reset" not in payload["receiver_state"]["LiquidHandlerBackend"]


_RESET_TRACKER = '''
class T:
    def __init__(self, thing, holder=None):
        self._pending_tip = None

    @property
    def has_tip(self):
        return self._pending_tip is not None

class R:
    def __init__(self):
        self.head: "T" = {}

    def setup(self, h):
        self.head = {c: T(%s) for c in range(3)}
'''


def _derive_reset(tmp_path: Path, ctor_args: str):
    (tmp_path / "synth.py").write_text(_RESET_TRACKER % ctor_args, encoding="utf-8")
    return derive_receiver_states(tmp_path, records=[], taxonomy_classes=[])["R"]


def test_ac_18_4_b_holder_bound_reset_yields_no_entry_reset(tmp_path: Path) -> None:
    """The stub-defeating half of R-C(2): binding the `None`-default `holder`
    parameter forfeits `entry_reset`, with the existing ledger value."""
    bound = _derive_reset(tmp_path, "thing=str(c), holder=h")
    assert bound.entry_reset is None and bound.entry_reset_ledger == "absent"


def test_ac_18_4_b_holder_less_reset_keeps_entry_reset(tmp_path: Path) -> None:
    """The positive control: identical source, `holder` left unbound."""
    unbound = _derive_reset(tmp_path, "thing=str(c)")
    assert unbound.entry_reset == {"method": "setup", "post": "no_tip"}


def test_ac_18_4_b_r_c2_binding_shapes() -> None:
    tracker = _class("class T:\n    def __init__(self, thing, holder=None):\n        pass\n", "T")

    def receiver(args: str):
        return _class(f"class R:\n    def reset(self):\n        self.slots = [T({args}) for _ in range(3)]\n", "R")

    def ok(args: str) -> bool:
        return reset_constructions_bind_no_optional_collaborator(
            receiver(args), "reset", "slots", tracker, "T", {"T": tracker}
        )

    assert ok("thing='x'")
    assert not ok("thing='x', holder=None")  # binding it at all, even to None, is refused
    assert not ok("'x', None")  # positionally
    assert not ok("*a")  # starred: inadmissible
    assert not ok("**kw")
    assert not ok("thing='x', nope=1")  # a call Python would not bind


def test_ac_18_4_c_entry_reset_implies_both_polarities(payload: dict) -> None:
    for name, rs in payload["receiver_state"].items():
        if "entry_reset" in rs:
            assert {"HAS_TIP", "NO_TIP"} <= set(rs["effects"].values()), name


def _with_setup(fixture: str) -> str:
    base = json.loads((FIXTURES / f"{fixture}.json").read_text(encoding="utf-8"))
    ops = [_op("op_0", "setup")] + base["operations"]
    base["operations"] = ops
    base["execution_order"] = [o["id"] for o in ops]
    return json.dumps(base)


def _sited(findings: list, qualname: str, verdict: Verdict) -> list:
    return [f for f in findings if f.plr_site is not None and f.plr_site.qualname == qualname and f.verdict is verdict]


def test_ac_18_4_d_setup_then_pickup_is_safe_at_both_tip_guards(contracts_json: str) -> None:
    report = check_graph(_graph(_op("op_0", "setup"), _op("op_1", "pick_up_tips", use_channels="[0]")), contracts_json)
    op1 = [f for f in report.findings if f.operation_id == "op_1"]
    assert _sited(op1, "LiquidHandler.pick_up_tips", Verdict.SAFE), "the own HasTipError guard"
    assert _sited(op1, "TipTracker.add_tip", Verdict.SAFE), "the bridged HasTipError guard"
    assert not [f for f in op1 if f.verdict is Verdict.WILL_FAIL]


def test_ac_18_4_d_second_pickup_is_will_fail(contracts_json: str) -> None:
    report = check_graph(
        _graph(
            _op("op_0", "setup"),
            _op("op_1", "pick_up_tips", use_channels="[0]"),
            _op("op_2", "pick_up_tips", use_channels="[0]"),
        ),
        contracts_json,
    )
    fails = _will_fail(report, "op_2")
    own = [f for f in fails if f.plr_site.qualname == "LiquidHandler.pick_up_tips"]
    assert own and all(f.category == "precondition_state" for f in own)
    assert not _will_fail(report, "op_1"), "the first pickup must stay clean (this is L7's hazard)"


def test_ac_18_4_d_aspirate_after_drop_is_will_fail_at_get_tip(contracts_json: str) -> None:
    report = check_graph(_with_setup("aspirate_after_drop_graph"), contracts_json)
    fails = _will_fail(report, "op_3")  # setup shifts nothing: ids stay op_1..op_3
    assert [f for f in fails if f.plr_site.qualname == "TipTracker.get_tip"], fails
    assert report.verdict is Verdict.WILL_FAIL


# ---------------------------------------------------------------------------
# AC-18.6 (R-E) -- receiver roots. Lands with T57 because the regenerated
# table cannot otherwise be compared against §18.4.8 (the spurious `TipTracker`
# receiver would still be in it).
# ---------------------------------------------------------------------------


def test_ac_18_6_receiver_set_is_pinned(payload: dict) -> None:
    assert set(payload["receiver_state"]) == {"LiquidHandler", "LiquidHandlerBackend"}


def test_ac_18_6_a_tracker_with_an_anchored_attribute_is_not_a_receiver(tmp_path: Path) -> None:
    (tmp_path / "synth.py").write_text(
        textwrap.dedent(
            '''
            class T2:
                def __init__(self):
                    self._f = None
                @property
                def has2(self):
                    return self._f is not None

            class T1:
                def __init__(self):
                    self.inner: "T2" = None
                    self._g = None
                @property
                def has1(self):
                    return self._g is not None

            class R:
                def __init__(self):
                    self.head: "T1" = {}
            '''
        ),
        encoding="utf-8",
    )
    assert set(derive_receiver_states(tmp_path, records=[], taxonomy_classes=[])) == {"R"}


def test_ac_18_6_r_e_implementation_types_no_class_name(plr_classes: dict[str, ast.ClassDef]) -> None:
    tree = ast.parse(textwrap.dedent(inspect.getsource(receiver_state_module.derive_receiver_states)))
    fn = tree.body[0]
    doc = fn.body[0].value if isinstance(fn.body[0], ast.Expr) else None
    strings = {
        n.value for n in ast.walk(fn) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n is not doc
    }
    assert not (strings & set(plr_classes)), sorted(strings & set(plr_classes))


# ---------------------------------------------------------------------------
# The published artifact's shape (§18.4.8) and AC-18.17.
# ---------------------------------------------------------------------------


def test_receiver_state_to_json_always_emits_the_new_keys() -> None:
    state = ReceiverState(
        channel_attr="head", tracker_class="T", tracker_module="m", bool_view_attr="has", bool_view_field="_f",
        true_when="not_none", state_fields=("_f",), effects={}, channel_default_param={},
        channel_default_disablers=(), tip_state_exceptions=(),
    )
    out = receiver_state_to_json(state)
    assert out["effects_unresolved"] == [] and out["effect_backing_fields"] == [] and out["effects_max_depth"] == 0
    assert "tracker_methods" not in out, "the direct-method set is internal, not published"


def test_new_keys_have_the_declared_types(payload: dict) -> None:
    for rs in payload["receiver_state"].values():
        assert isinstance(rs["effects_unresolved"], list) and rs["effects_unresolved"] == sorted(rs["effects_unresolved"])
        assert isinstance(rs["effect_backing_fields"], list) and rs["effect_backing_fields"] == sorted(
            rs["effect_backing_fields"]
        )
        assert isinstance(rs["effects_max_depth"], int) and rs["effects_max_depth"] >= 0
        assert set(rs["effects"].values()) <= {"HAS_TIP", "NO_TIP"}
    assert isinstance(payload["receiver_state_diagnostics"]["n_contracts_depth0_and_deep_coexist"], int)


def test_ac_18_17_hm25_is_thirteen_and_its_probe_exercises_a_three_hop_chain() -> None:
    (hm25,) = (row for row in REGISTRY if row.id == "HM-25")
    assert hm25.declared == 13
    assert resolve_measure(hm25.measure) == 13
    assert len(live_rows()) == 25 and BUDGET_CAP == 25
    # The probe's own synthetic chain, exercised here directly so a
    # classifier that stopped following helpers fails THIS test by name too.
    result = _tracker(
        """
        def add(self, tip: Tip):
            self._a(tip)
        def _a(self, t):
            self._b(t)
        def _b(self, t):
            self._carried = t
        """
    )
    assert result.effects == {"add": HAS_TIP} and result.effects_max_depth == 2
