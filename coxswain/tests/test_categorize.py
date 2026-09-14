"""categorize.py -- FR-7's N5-B Matches / Conflicts / Omissions derivation.

RED phase: fails against a tree without coxswain/src/coxswain/categorize.py.

Contract under test:

- categorize_grounding derives the three sections from Layer 2/3 output ONLY
  (a GroundingExitPayload: candidates, slot, message) plus nothing else --
  no kernel reads, no model, no new grounding lookups.
- disambiguate: one Match line per candidate in as-given order (FR-3);
  Conflicts name how candidates differ from each other; Omissions name the
  distinguishing information the utterance left out.
- not_found: the kernel's own message is the Conflict; there are no matches.
- The propose-card path NEVER invokes this module (FR-7: "applies to
  clarification cards only") -- asserted structurally over the kernel gate/
  execute/parse modules and over the propose-card JS sources.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from coxswain.categorize import Categorization, categorize_grounding
from coxswain.fft.context import KernelInstance
from coxswain.plr.grounding import KernelInstance as KI

# KernelInstance is re-exported identically from both modules; prove the two
# spellings are the same type so payload candidates categorize regardless of
# which import a caller used.
assert KI is KernelInstance


def _candidates() -> tuple[KernelInstance, ...]:
    return (
        KernelInstance(name="PLT_CAR_L5AC_A00", resource_type="plate_carrier", position="rails 7"),
        KernelInstance(name="PLT_CAR_P3AC_A00", resource_type="plate_carrier", position="rails 13"),
    )


def _payload(**overrides):
    from coxswain.schema.types import GroundingExitPayload

    fields = {"slot": "source", "candidates": _candidates(), "message": ""}
    fields.update(overrides)
    return GroundingExitPayload(**fields)


class TestDisambiguateCategorization:
    def test_one_match_line_per_candidate_in_as_given_order(self):
        cat = categorize_grounding(_payload())
        assert cat.matches == (
            "PLT_CAR_L5AC_A00 on rails 7",
            "PLT_CAR_P3AC_A00 on rails 13",
        )

    def test_candidate_without_position_renders_name_only(self):
        cat = categorize_grounding(
            _payload(
                candidates=(KernelInstance(name="TIP_RACK", resource_type="tip_rack"),)
            )
        )
        assert cat.matches == ("TIP_RACK",)

    def test_conflicts_name_the_differing_attribute(self):
        cat = categorize_grounding(_payload())
        assert any("different" in line for line in cat.conflicts)

    def test_omissions_name_the_slot_left_unspecified(self):
        cat = categorize_grounding(_payload(slot="source"))
        assert cat.omissions == ("You did not say which source.",)

    def test_identical_candidates_produce_no_conflict_line(self):
        twins = (
            KernelInstance(name="A1", resource_type="plate", position="rails 7"),
            KernelInstance(name="A2", resource_type="plate", position="rails 7"),
        )
        cat = categorize_grounding(_payload(candidates=twins))
        # Names differ but every categorized attribute matches: nothing to
        # conflict on, so Conflicts is empty rather than fabricated.
        assert cat.conflicts == ()


class TestNotFoundCategorization:
    def test_kernel_message_is_the_conflict_and_there_are_no_matches(self):
        cat = categorize_grounding(
            _payload(candidates=(), message='no plate_carrier matching "lane C"')
        )
        assert cat.matches == ()
        assert cat.conflicts == ('no plate_carrier matching "lane C"',)

    def test_empty_payload_fails_loud(self):
        with pytest.raises(ValueError):
            categorize_grounding(_payload(candidates=(), message=""))


class TestPureLayer23:
    def test_derivation_reads_only_payload_fields(self):
        """No source/kernel/ctx parameter exists to fetch anything with."""
        import inspect

        sig = inspect.signature(categorize_grounding)
        assert list(sig.parameters) == ["payload"]

    def test_categorization_shape_is_closed(self):
        cat = categorize_grounding(_payload())
        assert isinstance(cat, Categorization)
        assert tuple(cat.__dataclass_fields__) == ("matches", "conflicts", "omissions")


# --- FR-7's scoping clause: NEVER invoked from the propose-card path ----------


_KERNEL_ROOT = Path(__file__).resolve().parents[1] / "src" / "coxswain"
_PROPOSE_PATH_MODULES = (
    "fft/gate.py",
    "fft/cues.py",
    "execute.py",
    "parse_source.py",
    "phrase.py",
)


class TestNeverOnProposePath:
    @pytest.mark.parametrize("rel", _PROPOSE_PATH_MODULES)
    def test_no_propose_path_module_imports_or_calls_categorize(self, rel: str):
        tree = ast.parse((_KERNEL_ROOT / rel).read_text())
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = [a.name for a in node.names]
            elif isinstance(node, ast.ImportFrom):
                names = [node.module or ""]
            else:
                continue
            for name in names:
                assert "categorize" not in name.lower(), (
                    f"{rel} imports {name}; categorize.py applies to clarification "
                    "cards only (FR-7)"
                )

    @pytest.mark.parametrize("rel", _PROPOSE_PATH_MODULES)
    def test_no_propose_path_module_mentions_categorize_at_all(self, rel: str):
        text = (_KERNEL_ROOT / rel).read_text()
        assert "categoriz" not in text.lower(), (
            f"{rel} mentions categorize; FR-7 scopes it to clarification cards only"
        )

    def test_propose_card_js_sources_never_reference_categorize(self):
        shell_root = Path(__file__).resolve().parents[2] / "web-repl" / "shell" / "coxswain"
        for name in ("propose_card.js", "card_state.js"):
            text = (shell_root / name).read_text()
            assert "categoriz" not in text.lower(), (
                f"{name} references categorization; N5-B applies to clarification "
                "cards only (FR-7)"
            )
