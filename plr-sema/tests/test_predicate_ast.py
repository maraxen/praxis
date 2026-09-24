"""Spec 260904 (increment 6) §15.2/§15.11, T30a: the typed predicate
mini-AST and its total `parse`. One positive and one negative fixture per
G-rule (G0-G6), plus the round-1 (C15) nested-`Opaque` fixture and a JSON
round-trip. Grammar-only -- no idiom resolution (§15.3, T30b) and no
evaluation (`plr_sema.check.predicate`, T31): every assertion here is about
PARSED STRUCTURE, never about T/F/½.
"""

from __future__ import annotations

import pytest
from plr_sema.derive.predicate_ast import (
    AllOf,
    And,
    AnyOf,
    Attr,
    Cmp,
    EnvRef,
    Filtered,
    Is,
    IsInstance,
    Len,
    Lit,
    Not,
    Opaque,
    Or,
    SetOf,
    TRUE,
    Var,
    Zip,
    contains_env_ref,
    contains_opaque,
    count_var_self,
    from_json,
    parse,
    to_json,
)

# ---------------------------------------------------------------------------
# G0 -- totality: parse(None) = TRUE(), and Opaque is the only escape.
# ---------------------------------------------------------------------------


def test_g0_none_condition_is_true() -> None:
    assert parse(None) == TRUE()


def test_g0_syntax_error_is_opaque_not_a_raise() -> None:
    result = parse("<garbage(")
    assert isinstance(result, Opaque)


def test_g0_unrecognised_shape_is_opaque_identical_to_todays_reason() -> None:
    """AC-15.1's stub-defeating fixture: an unrecognised shape yields
    `Opaque`, never a raise and never a new node kind. `c not in self.head`
    itself is no longer this fixture after the 260907 amendment (G7 EnvRef,
    G8 in/not in, T35) -- see `test_g7_g8_worked_example_409_now_parses`
    below for what it parses to now. `tip.tracker.get_used_volume()` stays
    genuinely unrecognised (a call rooted at a local, not at `self`)."""
    result = parse("tip.tracker.get_used_volume() > 0")
    assert isinstance(result, Opaque)


@pytest.mark.parametrize(
    "condition",
    [
        "",
        "def f(): pass",
        "x = 1",
        "yield x",
    ],
)
def test_g0_total_never_raises_over_a_grab_bag_of_bad_input(condition: str) -> None:
    # Some of these are syntactically invalid as an `eval`-mode expression
    # (statements), some are merely unsupported shapes -- either way `parse`
    # must return a Predicate, never raise.
    result = parse(condition)
    assert result is not None


# ---------------------------------------------------------------------------
# G1 -- Cmp (incl. unsupported-op negative), Var, Lit, Len.
# ---------------------------------------------------------------------------


def test_g1_cmp_positive() -> None:
    assert parse("x == 1") == Cmp(Var("x"), "==", Lit(1))


def test_g1_cmp_membership_ops_g8() -> None:
    """G8(2), 260907 amendment (T35): `in`/`not in` widen Cmp's op set to
    {==, !=, <, <=, >, >=, in, not in} -- Python's `ast.cmpop` set is now
    fully covered, so there is no remaining "unsupported comparison
    operator" shape to test negatively. Every membership `Cmp` evaluates
    1/2 unconditionally this increment (S15.4 E-ENV) -- an EVALUATION fact,
    not this module's; parsing is polarity/value agnostic."""
    assert parse("x in y") == Cmp(Var("x"), "in", Var("y"))
    assert parse("x not in y") == Cmp(Var("x"), "not in", Var("y"))


def test_g1_len_and_var_and_lit() -> None:
    assert parse("len(tip_spots) > 0") == Cmp(Len(Var("tip_spots")), ">", Lit(0))


def test_g1_attr_term() -> None:
    assert parse("resource.name == 'trash'") == Cmp(Attr(Var("resource"), "name"), "==", Lit("trash"))


def test_g1_not_and_or() -> None:
    assert parse("not x == 1") == Not(Cmp(Var("x"), "==", Lit(1)))
    assert parse("x == 1 and y == 2") == And((Cmp(Var("x"), "==", Lit(1)), Cmp(Var("y"), "==", Lit(2))))
    assert parse("x == 1 or y == 2") == Or((Cmp(Var("x"), "==", Lit(1)), Cmp(Var("y"), "==", Lit(2))))


# ---------------------------------------------------------------------------
# G2 -- chained comparisons.
# ---------------------------------------------------------------------------


def test_g2_chained_comparison_positive() -> None:
    """`len(a) == len(b) == len(c)` is `And` of two pairwise `Cmp`s, the
    middle operand (`len(b)`) shared -- not reparsed into two unequal
    objects (they compare equal either way, but this checks the SAME
    structural shape §15.11's fixture names)."""
    result = parse("len(tip_spots) == len(offsets) == len(use_channels)")
    assert result == And(
        (
            Cmp(Len(Var("tip_spots")), "==", Len(Var("offsets"))),
            Cmp(Len(Var("offsets")), "==", Len(Var("use_channels"))),
        )
    )


def test_g2_single_comparison_is_not_wrapped_in_and() -> None:
    """The negative half: a single (non-chained) comparison stays a bare
    `Cmp`, never an `And` of one."""
    result = parse("x == 1")
    assert isinstance(result, Cmp)
    assert not isinstance(result, And)


# ---------------------------------------------------------------------------
# G3 -- the filtered-comprehension emptiness idiom.
# ---------------------------------------------------------------------------


def test_g3_filtered_emptiness_positive_gt_zero() -> None:
    result = parse("len([ts for ts in tip_spots if not isinstance(ts, TipSpot)]) > 0")
    assert result == AnyOf(
        seq=Var("tip_spots"),
        predicate=Not(IsInstance(Var("ts"), ("TipSpot",))),
    )


def test_g3_filtered_emptiness_positive_eq_zero_is_negated() -> None:
    result = parse("len([ts for ts in tip_spots if not isinstance(ts, TipSpot)]) == 0")
    assert result == Not(
        AnyOf(seq=Var("tip_spots"), predicate=Not(IsInstance(Var("ts"), ("TipSpot",))))
    )


def test_g3_filtered_emptiness_negative_unsupported_relation_is_opaque() -> None:
    """Only >0, >=1, ==0, !=0 are recognised over a Filtered term -- a count
    is not an emptiness test, so `>= 2` must be `Opaque`, never a fabricated
    `Cmp`."""
    result = parse("len([ts for ts in tip_spots if not isinstance(ts, TipSpot)]) >= 2")
    assert isinstance(result, Opaque)


def test_g3_non_filtered_len_is_an_ordinary_cmp() -> None:
    """Negative half from the other direction: when `<x>` is NOT a Filtered
    term (e.g. a bare local name -- the un-resolved local-binding-idiom
    case, T30b's job, not this module's), `len(<x>) > 0` stays a plain
    `Cmp`, never `AnyOf`."""
    result = parse("len(not_tip_spots) > 0")
    assert result == Cmp(Len(Var("not_tip_spots")), ">", Lit(0))


# ---------------------------------------------------------------------------
# G4 -- set(P) uniqueness is representable via ordinary Len/SetOf/Cmp; no
# parse-time special-casing (the semantics are the evaluator's, T31).
# ---------------------------------------------------------------------------


def test_g4_setof_uniqueness_shape() -> None:
    result = parse("len(set(use_channels)) == len(use_channels)")
    assert result == Cmp(Len(SetOf(Var("use_channels"))), "==", Len(Var("use_channels")))


# ---------------------------------------------------------------------------
# G5 -- numeric Cmp over volumes stays representable (folding is T31's job).
# ---------------------------------------------------------------------------


def test_g5_numeric_cmp_is_representable_not_folded_at_parse_time() -> None:
    result = parse("tip.tracker.get_used_volume() > 0")
    # `tip.tracker.get_used_volume()` is a Call to something other than
    # len/set/isinstance/all/any -- not a recognised Term -- so the whole
    # Cmp collapses to Opaque. This IS the correct grammar-level behaviour:
    # G5 is about what an evaluator does with a numeric Cmp it CAN build,
    # not about parsing an arbitrary method-call operand.
    assert isinstance(result, Opaque)
    # A genuinely numeric-Term Cmp parses fine and stays a plain Cmp --
    # folding it to 1/2 (or reading the volume domain) is T31's business.
    result2 = parse("volume > 0")
    assert result2 == Cmp(Var("volume"), ">", Lit(0))


# ---------------------------------------------------------------------------
# G1 -- Is / IsNot None.
# ---------------------------------------------------------------------------


def test_is_none_and_is_not_none_are_exact_opposites() -> None:
    assert parse("x is None") == Is(Var("x"), negated=False)
    assert parse("x is not None") == Is(Var("x"), negated=True)


def test_is_negative_non_none_rhs_is_opaque() -> None:
    result = parse("x is y")
    assert isinstance(result, Opaque)


# ---------------------------------------------------------------------------
# IsInstance.
# ---------------------------------------------------------------------------


def test_isinstance_tuple_form_positive() -> None:
    result = parse("isinstance(resource, (TipSpot, Trash))")
    assert result == IsInstance(Var("resource"), ("TipSpot", "Trash"))


def test_isinstance_single_type_positive() -> None:
    result = parse("isinstance(resource, Well)")
    assert result == IsInstance(Var("resource"), ("Well",))


def test_isinstance_negative_wrong_arity_is_opaque() -> None:
    assert isinstance(parse("isinstance(resource)"), Opaque)


# ---------------------------------------------------------------------------
# AllOf / AnyOf over a direct comprehension (not via the Filtered idiom).
# ---------------------------------------------------------------------------


def test_allof_positive() -> None:
    result = parse("all(isinstance(w, Well) for w in resource)")
    assert result == AllOf(seq=Var("resource"), predicate=IsInstance(Var("w"), ("Well",)))


def test_anyof_positive() -> None:
    result = parse("any(bav is not None for bav in blow_out_air_volume)")
    assert result == AnyOf(seq=Var("blow_out_air_volume"), predicate=Is(Var("bav"), negated=True))


def test_allof_zip_g8_worked_example_514() -> None:
    """The real PLR shape at `liquid_handler.py:514`. Before the 260907
    amendment (G7 EnvRef, G8 Zip, T35), `zip(use_channels, tips)` was not a
    recognised Term and the whole `all(...)` stayed Opaque; G8(1) now
    admits `Zip` as the seq of `AllOf`/`AnyOf` (tuple target arity-matched
    positionally), and G7 shape (2) admits the `self.backend.<method>(...)`
    call (`len(path) == 3 >= 3`, never refused by the PLR-layer test)."""
    result = parse(
        "not all(self.backend.can_pick_up_tip(channel, tip) "
        "for channel, tip in zip(use_channels, tips))"
    )
    assert result == Not(
        AllOf(
            seq=Zip((Var("use_channels"), Var("tips"))),
            predicate=EnvRef(
                ("self", "backend", "can_pick_up_tip"), (Var("channel"), Var("tip"))
            ),
        )
    )
    assert not contains_opaque(result)
    assert contains_env_ref(result)


def test_allof_negative_zip_tuple_arity_mismatch_is_opaque() -> None:
    """G8(1)'s tuple-target correspondence: the target's arity must equal
    the Zip's -- a mismatch (here 3 names for a 2-item zip) is Opaque, no
    partial admission."""
    result = parse("all(f(a, b) for a, b, c in zip(x, y))")
    assert isinstance(result, Opaque)


def test_allof_negative_zip_under_len_is_opaque() -> None:
    """G8(1): `Zip` is admissible ONLY as the `seq` of `AllOf`/`AnyOf` --
    a `zip(...)` anywhere else (e.g. under `Len`) is simply unrecognised."""
    result = parse("len(zip(a, b)) > 0")
    assert isinstance(result, Opaque)


def test_anyof_negative_filter_clause_present_is_opaque() -> None:
    """G1's `AllOf`/`AnyOf` production is `all(<pred> for <v> in <seq>)` --
    no `if` clause. A generator with a filter clause is not this shape."""
    result = parse("any(x for x in xs if x > 0)")
    assert isinstance(result, Opaque)


# ---------------------------------------------------------------------------
# TRUE.
# ---------------------------------------------------------------------------


def test_true_only_from_none_condition() -> None:
    assert parse(None) == TRUE()
    # A condition that happens to spell `True` is a Lit(True) Cmp target
    # inside an ordinary expression, not the TRUE predicate -- TRUE is
    # reserved for the "no condition at all" case (G0's normative box: this
    # is a statement about the predicate, never a reachability claim).
    assert parse("True") != TRUE()


# ---------------------------------------------------------------------------
# G6 -- parse() is identical regardless of kind (polarity lives on
# InlinedGuard.kind, not on the Predicate). Sanity check only: this module
# has no `kind` field at all to get wrong.
# ---------------------------------------------------------------------------


def test_g6_parse_is_kind_agnostic() -> None:
    cond = "len(set(use_channels)) == len(use_channels)"
    assert parse(cond) == parse(cond)


# ---------------------------------------------------------------------------
# C15 -- the nested-Opaque rule: contains_opaque walks the WHOLE tree.
# ---------------------------------------------------------------------------


def test_contains_opaque_true_when_nested_inside_filtered_predicate() -> None:
    """§15.7's original worked example (pre-260907): `invalid_channels = [c
    for c in channels if c not in self.head]` -- the `if` clause used to
    parse Opaque; after G7/G8 (T35) it parses to `Cmp(..., EnvRef(...))`,
    so this exact condition no longer exercises a nested-Opaque `Filtered`
    predicate. `not isinstance(e, Foo)` inside the comprehension (a shape
    G7/G8 still do not touch: `Foo` unresolved is fine for IsInstance, but
    a genuinely-still-opaque inner clause -- `e.method()` rooted at the
    comprehension's own local target, not `self` -- keeps the nested-Opaque
    rule exercised)."""
    result = parse("len([e for e in channels if e.method()]) == 0")
    assert not isinstance(result, Opaque)  # the TOP node parsed
    assert contains_opaque(result) is True


def test_g7_g8_worked_example_409_now_parses() -> None:
    """§15.7's worked example, post-260907 (G7 EnvRef, G8 in/not in, T35):
    `c not in self.head` (`:407`'s filter, bound by alpha at `:409`) is no
    longer Opaque -- it is `Cmp(Var("c"), "not in", EnvRef(("self",
    "head"), None))`, and the FULL `:409` guard shape
    (`len([c for c in channels if c not in self.head]) == 0`) now contains
    an EnvRef and no Opaque at all."""
    result = parse("len([c for c in channels if c not in self.head]) == 0")
    assert not contains_opaque(result)
    assert contains_env_ref(result)
    assert result == Not(
        AnyOf(
            seq=Var("channels"),
            predicate=Cmp(Var("c"), "not in", EnvRef(("self", "head"), None)),
        )
    )


def test_contains_opaque_false_on_fully_resolved_predicate() -> None:
    result = parse("len(set(use_channels)) == len(use_channels)")
    assert contains_opaque(result) is False


def test_contains_opaque_true_on_bare_top_level_opaque() -> None:
    assert contains_opaque(Opaque("whatever")) is True


def test_contains_opaque_true_when_and_conjunct_is_opaque() -> None:
    """`And`/`Or` still tolerate a nested `Opaque` conjunct structurally --
    Kleene evaluation of that (an F conjunct still deciding) is T31's job,
    not this module's, but the STRUCTURE must be buildable at all.
    `tip.tracker.get_used_volume()` (a call rooted at a LOCAL, not `self`)
    stays genuinely Opaque after the 260907 amendment -- `c not in
    self.head` no longer is (see `test_g7_g8_worked_example_409_now_parses`)."""
    result = parse("x == 1 and tip.tracker.get_used_volume() > 0")
    assert result == And(
        (Cmp(Var("x"), "==", Lit(1)), Opaque("tip.tracker.get_used_volume() > 0"))
    )
    assert contains_opaque(result) is True


# ---------------------------------------------------------------------------
# G7/G8 -- the 260907 amendment (spec 260904 S15.2, T35). AC-15.1's own
# positive/negative fixture set, one apiece.
# ---------------------------------------------------------------------------


def test_g7_positive_attribute_chain() -> None:
    assert parse("self.head") == EnvRef(("self", "head"), None)
    assert parse("self._resource_pickup.direction") == EnvRef(
        ("self", "_resource_pickup", "direction"), None
    )


def test_g7_positive_call_with_term_args() -> None:
    assert parse("self.backend.can_pick_up_tip(channel, tip)") == EnvRef(
        ("self", "backend", "can_pick_up_tip"), (Var("channel"), Var("tip"))
    )


def test_g7_positive_and_of_two_env_ref_leaves_in_predicate_position() -> None:
    """`self.setup_finished and (not self._resource_pickups)` -- both
    operands are `EnvRef` used bare AS a predicate (a boolean read), not
    nested inside a Cmp/Is."""
    result = parse("self.setup_finished and (not self._resource_pickups)")
    assert result == And(
        (
            EnvRef(("self", "setup_finished"), None),
            Not(EnvRef(("self", "_resource_pickups"), None)),
        )
    )


def test_g7_positive_is_none_normalisation() -> None:
    """Shape (1) SUBSUMES the `Attr(Var("self"), ...)` chain the shipped
    walk used to produce: `self._resource_pickup is None` now parses to
    `Is(EnvRef(...), ...)`, never `Is(Attr(Var("self"), ...), ...)`."""
    result = parse("self._resource_pickup is None")
    assert result == Is(EnvRef(("self", "_resource_pickup"), None), negated=False)


@pytest.mark.parametrize(
    "condition",
    [
        "get_capture_or_validation_active()",  # callee not self-rooted
        "self.head[channel].has_tip",  # self subscripted in the chain
        "isinstance(self, Foo)",  # self as a bare operand (Var("self") invariant)
        "tip.tracker.get_used_volume()",  # rooted at a local, not self
        "volume - self.get_used_volume() > 1e-06",  # self-read under an arithmetic BinOp
    ],
)
def test_g7_negative_closed_list(condition: str) -> None:
    """G7's closed negative list, one fixture per row (AC-15.1): every one
    of these yields `Opaque`, identical to today's behaviour -- an
    implementation that admitted any of them as an `EnvRef` fails here."""
    result = parse(condition)
    assert isinstance(result, Opaque)
    assert count_var_self(result) == 0


def test_g7_call_negative_non_term_argument_is_opaque_no_partial_admission() -> None:
    """G7 shape (2): if ANY argument fails to parse as a Term, the WHOLE
    call is Opaque -- no partial admission, no fallback."""
    result = parse("self.backend.can_pick_up_tip(channel, tip.tracker.get_used_volume())")
    assert isinstance(result, Opaque)


def test_g7_var_self_invariant_whole_table_style() -> None:
    """No parsed predicate may contain a bare `Var("self")` anywhere --
    published as `n_var_self` (S15.9 block (6)), asserted 0 here across a
    grab-bag of shapes that would otherwise leak it."""
    for condition in [
        "self == foo",
        "isinstance(self, Foo)",
        "self is None",
        "f(self)",
    ]:
        result = parse(condition)
        assert count_var_self(result) == 0, condition


def test_g7_args_round_trip_none_vs_empty_tuple() -> None:
    """A-C12: `args is None` (a bare read) and `args == ()` (a zero-argument
    call) are distinct shapes that must not collapse into each other on the
    wire -- JSON `null` vs `[]`."""
    read = parse("self.head")
    assert isinstance(read, EnvRef) and read.args is None
    zero_arg_call = parse("self.backend.method_name()")
    assert isinstance(zero_arg_call, EnvRef) and zero_arg_call.args == ()

    read_json = to_json(read)
    call_json = to_json(zero_arg_call)
    assert read_json["args"] is None
    assert call_json["args"] == []
    assert from_json(read_json) == read
    assert from_json(call_json) == zero_arg_call


# ---------------------------------------------------------------------------
# JSON round-trip -- stable, no Python repr() strings.
# ---------------------------------------------------------------------------


_ROUND_TRIP_CONDITIONS = [
    None,
    "<garbage(",
    "c not in self.head",
    "x == 1",
    "len(tip_spots) == len(offsets) == len(use_channels)",
    "len([ts for ts in tip_spots if not isinstance(ts, TipSpot)]) > 0",
    "len([ts for ts in tip_spots if not isinstance(ts, TipSpot)]) == 0",
    "len(set(use_channels)) == len(use_channels)",
    "x is None",
    "x is not None",
    "isinstance(resource, (TipSpot, Trash))",
    "all(isinstance(w, Well) for w in resource)",
    "not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips))",
    "len([c for c in channels if c not in self.head]) == 0",
    "not x == 1",
    "x == 1 and y == 2",
    "x == 1 or y == 2",
    # G7/G8, 260907 amendment (T35).
    "self.head",
    "self._resource_pickup.direction",
    "self.backend.can_pick_up_tip(channel, tip)",
    "self.backend.method_name()",
    "self.setup_finished and (not self._resource_pickups)",
    "self._resource_pickup is None",
    "x in y",
    "x not in y",
    "not all(self.backend.can_pick_up_tip(channel, tip) for channel, tip in zip(use_channels, tips))",
]


@pytest.mark.parametrize("condition", _ROUND_TRIP_CONDITIONS)
def test_json_round_trip(condition: str | None) -> None:
    predicate = parse(condition)
    encoded = to_json(predicate)
    # No Python repr() strings anywhere in the encoding -- every value is
    # JSON-primitive (dict/list/str/int/float/bool/None).
    _assert_json_safe(encoded)
    decoded = from_json(encoded)
    assert decoded == predicate


def _assert_json_safe(value: object) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            assert isinstance(k, str)
            _assert_json_safe(v)
    elif isinstance(value, list):
        for v in value:
            _assert_json_safe(v)
    else:
        assert value is None or isinstance(value, (bool, int, float, str))


def test_from_json_rejects_unrecognized_node_kind() -> None:
    with pytest.raises(ValueError):
        from_json({"node": "NotARealNode"})
