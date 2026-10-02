"""Browserless tests for ``praxis/display/glossary.py`` (task B4, backlog #5638): the operation
glossary, one name per action. Closes AC-28 (with ``test_display_ledger.py`` for its ledger half).

Spec: ``260929_notebook-display-epic.md`` section 3.5 (the table: PLR method, name in every Praxis
text, verb form in fixes; the ``*96`` variants are the same name plus " (96 head)"; the nouns
channel / well / tip / tip rack / deck panel, never "pip" or "pipette"; "dock" is internal only),
section 4 (``glossary.py``: ``ACTIONS`` and nouns, "the only home of action strings"), D8 (B5's
frame filter reads ``glossary.ACTIONS``), and AC-28:

* every ledger and error action string equals a ``glossary.ACTIONS`` value;
* a scan of ``praxis/display/*.py`` other than ``glossary.py``, with comments and docstrings
  stripped, finds no literal from the table.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the
synthetic package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put
on ``sys.path`` (its ``praxis/`` would shadow the repo's real package).

**Controls.** The AC-28 scan is run against synthetic sources first: a module that spells an action
name in a literal must be flagged, one that only mentions it in a comment or a docstring must not.
The fallback for an unknown op is run against hostile and non-string input.

**PyLabRobot.** The glossary must not import it (B5 imports the glossary from a module that is
loaded before PLR in some paths), but its keys must be REAL method names of the pin's
``LiquidHandler``: ``test_every_glossary_key_is_a_real_liquid_handler_method`` checks that on the
1.0.0b1 pin (run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended when the venv is not on it).
"""

from __future__ import annotations

import ast
import importlib
import re
import sys
import types
from collections.abc import Mapping
from pathlib import Path

import pytest

import pylabrobot

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_GLOSSARY_PATH = _DISPLAY_DIR / "glossary.py"
_PKG = "_praxis_display_under_test"

# Section 3.5, transcribed independently of the module (the oracle).
TABLE = [
    # (PLR method, name in every Praxis text, verb form in fixes)
    ("pick_up_tips", "Pick up tips", "pick up tips"),
    ("drop_tips", "Drop tips", "drop tips"),
    ("return_tips", "Return tips", "return tips"),
    ("discard_tips", "Discard tips", "discard tips"),
    ("aspirate", "Aspirate", "aspirate"),
    ("dispense", "Dispense", "dispense"),
    ("transfer", "Transfer", "transfer"),
]
SUFFIX_96 = " (96 head)"
OPS_96 = [
    "pick_up_tips96", "drop_tips96", "return_tips96", "discard_tips96", "aspirate96", "dispense96",
]


# --------------------------------------------------------------------------- loading


def _package():
    if _PKG not in sys.modules:
        module = types.ModuleType(_PKG)
        module.__path__ = [str(_DISPLAY_DIR)]
        module.__package__ = _PKG
        sys.modules[_PKG] = module
    return sys.modules[_PKG]


@pytest.fixture(scope="module", autouse=True)
def _plr_is_the_pin():
    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )


@pytest.fixture(scope="module")
def gl():
    """praxis/display/glossary.py. A missing module is the RED reason."""
    if not _GLOSSARY_PATH.is_file():
        pytest.fail(f"praxis/display/glossary.py does not exist yet: {_GLOSSARY_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.glossary")


# --------------------------------------------------------------------------- the table


def test_actions_are_exactly_the_section_3_5_table(gl):
    expected = {m: n for m, n, _v in TABLE}
    expected.update({f"{m}96": f"{n}{SUFFIX_96}" for m, n, _v in TABLE if m != "transfer"})
    assert dict(gl.ACTIONS) == expected


def test_there_are_thirteen_actions_seven_plus_six_96_variants(gl):
    assert len(gl.ACTIONS) == 13
    assert {k for k in gl.ACTIONS if k.endswith("96")} == set(OPS_96)


@pytest.mark.parametrize(("method", "name", "_verb"), TABLE)
def test_each_base_action_name(gl, method, name, _verb):
    assert gl.ACTIONS[method] == name
    assert gl.action_name(method) == name


@pytest.mark.parametrize("method", OPS_96)
def test_each_96_variant_is_the_base_name_plus_96_head(gl, method):
    base = method[:-2]
    assert gl.ACTIONS[method] == gl.ACTIONS[base] + SUFFIX_96
    assert gl.action_name(method) == gl.ACTIONS[base] + SUFFIX_96
    assert gl.is_96(method) is True
    assert gl.is_96(base) is False


def test_transfer_has_no_96_variant(gl):
    assert "transfer96" not in gl.ACTIONS


def test_action_values_are_unique(gl):
    values = list(gl.ACTIONS.values())
    assert len(values) == len(set(values))


def test_action_names_have_no_markup_and_read_as_sentence_case(gl):
    for name in gl.ACTIONS.values():
        assert name == name.strip()
        assert not set(name) & set('<>&"\'')
        assert name[0].isupper()
    assert gl.ACTIONS["pick_up_tips"] == "Pick up tips"  # only the first word is capitalised


def test_actions_is_read_only(gl):
    """The one home of action strings must not be editable from a notebook cell or another module."""
    assert isinstance(gl.ACTIONS, Mapping)
    with pytest.raises(TypeError):
        gl.ACTIONS["aspirate"] = "Suck"  # type: ignore[index]
    with pytest.raises(TypeError):
        gl.ACTIONS["home"] = "Home"  # type: ignore[index]
    assert gl.ACTIONS["aspirate"] == "Aspirate"
    assert "home" not in gl.ACTIONS
    with pytest.raises((TypeError, AttributeError)):
        gl.ACTIONS.pop("aspirate")  # type: ignore[attr-defined]


def test_every_glossary_key_is_a_real_liquid_handler_method(gl):
    """The keys are the frame names B5 filters on and the methods B4 shadows, so a typo here is
    a silent no-op. Anchor: PLR 1.0.0b1 ``pylabrobot/legacy/liquid_handling/liquid_handler.py``."""
    from pylabrobot.legacy.liquid_handling import LiquidHandler

    for method in gl.ACTIONS:
        fn = getattr(LiquidHandler, method, None)
        assert callable(fn), f"LiquidHandler has no method {method!r} at the pin"
        assert "lambda" not in getattr(fn, "__qualname__", ""), method


# --------------------------------------------------------------------------- verbs


@pytest.mark.parametrize(("method", "_name", "verb"), TABLE)
def test_each_base_verb_form(gl, method, _name, verb):
    assert gl.VERBS[method] == verb
    assert gl.verb_form(method) == verb


def test_verbs_cover_exactly_the_actions(gl):
    assert set(gl.VERBS) == set(gl.ACTIONS)


@pytest.mark.parametrize("method", OPS_96)
def test_96_verb_forms_follow_the_name_column(gl, method):
    """Section 3.5 says the 96 verb form is "the same". Read as the same construction as the name
    column (base verb + " (96 head)"). No error template uses a 96 verb (D8 step 2)."""
    assert gl.VERBS[method] == gl.VERBS[method[:-2]] + SUFFIX_96


def test_verb_form_is_the_lower_cased_name_for_every_action(gl):
    for method, name in gl.ACTIONS.items():
        assert gl.verb_form(method) == name.lower()
        assert name[0].lower() + name[1:] == gl.verb_form(method)


def test_verbs_is_read_only(gl):
    with pytest.raises(TypeError):
        gl.VERBS["aspirate"] = "suck"  # type: ignore[index]


# --------------------------------------------------------------------------- nouns


def test_nouns_are_the_section_3_5_list(gl):
    assert tuple(gl.NOUNS) == ("channel", "well", "tip", "tip rack", "deck panel")


def test_avoided_terms_point_at_the_noun_to_use_instead(gl):
    """Never "pip" or "pipette" (use channel); "dock" is an internal name only (use deck panel)."""
    assert dict(gl.AVOID) == {"pip": "channel", "pipette": "channel", "dock": "deck panel"}
    for wrong, right in gl.AVOID.items():
        assert right in gl.NOUNS
        assert wrong not in gl.NOUNS


def test_no_action_name_uses_an_avoided_term(gl):
    words = {w for text in (*gl.ACTIONS.values(), *gl.VERBS.values()) for w in re.findall(r"[a-z]+", text.lower())}
    assert not words & set(gl.AVOID)


@pytest.mark.parametrize(
    ("n", "noun", "text"),
    [
        (0, "channel", "0 channels"),
        (1, "channel", "1 channel"),
        (8, "channel", "8 channels"),
        (96, "channel", "96 channels"),
        (1, "tip rack", "1 tip rack"),
        (2, "tip rack", "2 tip racks"),
        (1, "step", "1 step"),
        (12, "step", "12 steps"),
        (3, "tip cycle", "3 tip cycles"),
        (1, "tip cycle", "1 tip cycle"),
        (1200, "well", "1,200 wells"),
    ],
)
def test_plural_counts_with_a_thousands_separator(gl, n, noun, text):
    assert gl.plural(n, noun) == text


# --------------------------------------------------------------------------- roles


def test_every_action_has_exactly_one_role(gl):
    roles = {m: gl.role_of(m) for m in gl.ACTIONS}
    assert all(r is not None for r in roles.values())
    assert set(roles.values()) == {gl.PICK_UP, gl.DROP, gl.ASPIRATE, gl.DISPENSE, gl.TRANSFER}
    assert len({gl.PICK_UP, gl.DROP, gl.ASPIRATE, gl.DISPENSE, gl.TRANSFER}) == 5


def test_role_assignment(gl):
    assert gl.role_of("pick_up_tips") == gl.PICK_UP
    for m in ("drop_tips", "return_tips", "discard_tips"):
        assert gl.role_of(m) == gl.DROP
    assert gl.role_of("aspirate") == gl.ASPIRATE
    assert gl.role_of("dispense") == gl.DISPENSE
    assert gl.role_of("transfer") == gl.TRANSFER


@pytest.mark.parametrize("method", OPS_96)
def test_a_96_variant_has_the_role_of_its_base(gl, method):
    assert gl.role_of(method) == gl.role_of(method[:-2])


@pytest.mark.parametrize("op", ["home", "", None, 3, "Aspirate", "ASPIRATE", " aspirate", b"aspirate"])
def test_role_of_an_unknown_op_is_none(gl, op):
    assert gl.role_of(op) is None


def test_is_96_is_false_for_unknown_and_non_string(gl):
    assert gl.is_96("home96") is False  # not a glossary action, whatever it ends with
    assert gl.is_96(None) is False
    assert gl.is_96(96) is False


# --------------------------------------------------------------------------- unknown ops fall back safely


@pytest.mark.parametrize("op", ["home", "move_plate", "stamp", "some_new_op2", "x"])
def test_unknown_op_falls_back_to_a_readable_sentence_case_name(gl, op):
    name = gl.action_name(op)
    assert isinstance(name, str) and name
    assert name == op.replace("_", " ").capitalize()
    assert gl.verb_form(op) == op.replace("_", " ")


@pytest.mark.parametrize(
    "op",
    [None, "", "   ", 0, 3.5, b"aspirate", object(), ["aspirate"], {"a": 1}, "\x00", "_", "___"],
)
def test_unusable_op_falls_back_to_unknown_action_and_never_raises(gl, op):
    assert gl.action_name(op) == "Unknown action"
    assert gl.verb_form(op) == "unknown action"


HOSTILE = [
    "<script>alert(1)</script>",
    '"><img src=x onerror=alert(1)>',
    "{0.__class__}{name}%s%(x)s",
    "µL \U0001f9ea 日本語",
    "a" * 100_000,
    "line1\nline2",
]


@pytest.mark.parametrize("op", HOSTILE)
def test_hostile_op_names_fall_back_without_raising_and_stay_bounded(gl, op):
    """The glossary never interprets its input as a format string or markup; escaping is the
    renderer's job (D2), so it returns plain text, and never an unbounded one."""
    name = gl.action_name(op)
    verb = gl.verb_form(op)
    assert isinstance(name, str) and isinstance(verb, str)
    assert name and verb
    assert len(name) <= 80 and len(verb) <= 80
    assert "\n" not in name and "\n" not in verb


def test_fallback_is_case_sensitive_on_the_key(gl):
    """``"Aspirate"`` is a name, not a method: it is unknown, never mapped to the table entry."""
    assert gl.action_name("Aspirate") == "Aspirate"  # the humanised fallback happens to agree
    assert gl.role_of("Aspirate") is None
    assert "Aspirate" not in gl.ACTIONS


def test_a_known_action_never_takes_the_fallback_path(gl):
    for method, name in gl.ACTIONS.items():
        assert gl.action_name(method) == name


# --------------------------------------------------------------------------- module purity


def _imports(source: str) -> set[str]:
    tree = ast.parse(source)
    found: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            found.update(a.name.split(".")[0] for a in node.names)
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            found.add(node.module.split(".")[0])
    return found


def test_glossary_imports_no_pylabrobot_and_no_browser_module(gl):
    found = _imports(_GLOSSARY_PATH.read_text())
    assert not found & {"pylabrobot", "js", "pyodide", "IPython", "ipykernel"}, found


def test_glossary_is_standard_library_only(gl):
    stdlib = set(sys.stdlib_module_names)
    assert _imports(_GLOSSARY_PATH.read_text()) <= stdlib | {"__future__"}


# --------------------------------------------------------------------------- AC-28: the literal scan


def _docstring_nodes(tree: ast.AST) -> set[int]:
    """``id`` of every module / class / function docstring ``Constant`` node."""
    out: set[int] = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                out.add(id(body[0].value))
    return out


def literals_from_the_table(source: str, table_strings: set[str]) -> list[str]:
    """The AC-28 scan: string literals of *source* (comments are not in the AST; docstrings are
    skipped) that equal a string from the glossary table. F-string constant parts are literals
    too, and so are strings nested in tuples, lists, dicts and sets."""
    tree = ast.parse(source)
    skip = _docstring_nodes(tree)
    hits = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in skip:
            if node.value in table_strings:
                hits.append(node.value)
    return hits


def _table_strings(gl) -> set[str]:
    return set(gl.ACTIONS) | set(gl.ACTIONS.values()) | set(gl.VERBS.values())


def test_the_scan_flags_a_literal_action_name(gl):
    table = _table_strings(gl)
    for src in (
        'label = "Aspirate"\n',
        'x = ("Pick up tips", 1)\n',
        'def f():\n    return "Discard tips (96 head)"\n',
        'names = {"k": "drop tips"}\n',
        'call("aspirate")\n',
        'op = "pick_up_tips96"\n',
        'msg = f"{n}" "Transfer"\n',
        'msg = f"Dispense"\n',
        'items = ["a", "Return tips"]\n',
    ):
        assert literals_from_the_table(src, table), f"the scan missed: {src!r}"


def test_the_scan_ignores_comments_docstrings_and_other_text(gl):
    table = _table_strings(gl)
    for src in (
        '# label = "Aspirate"\nx = 1\n',
        '"""Aspirate, Dispense and Pick up tips are named here."""\nx = 1\n',
        'def f():\n    """Return tips."""\n    return 1\n',
        'class C:\n    """Drop tips."""\n    y = 2\n',
        'x = "the aspirate asked for 80 µL"\n',
        'x = "Aspirated"\n',
        'x = "Steps"\n',
        'x = "Pick up"\n',
    ):
        assert literals_from_the_table(src, table) == [], f"the scan flagged: {src!r}"


def test_the_scan_control_finds_a_docstring_only_when_it_is_not_the_docstring(gl):
    """A string statement that is not first in its body is NOT a docstring and must be flagged."""
    table = _table_strings(gl)
    src = 'def f():\n    x = 1\n    "Aspirate"\n    return x\n'
    assert literals_from_the_table(src, table) == ["Aspirate"]


def _other_display_sources() -> list[Path]:
    return sorted(p for p in _DISPLAY_DIR.glob("*.py") if p.name != "glossary.py")


def test_the_scan_sees_the_real_modules(gl):
    names = {p.name for p in _other_display_sources()}
    assert {"svg.py", "floor.py", "budget.py", "labware.py"} <= names
    assert "glossary.py" not in names


def test_no_display_module_but_the_glossary_spells_an_action(gl):
    """AC-28, second bullet: the glossary is the only home of action strings."""
    table = _table_strings(gl)
    offenders = {}
    for path in _other_display_sources():
        hits = literals_from_the_table(path.read_text(), table)
        if hits:
            offenders[path.name] = sorted(set(hits))
    assert offenders == {}, f"action strings outside glossary.py: {offenders}"


def test_the_glossary_itself_does_carry_the_table_literals(gl):
    """Control for the scan above: pointed at the glossary it must find the table."""
    table = _table_strings(gl)
    hits = set(literals_from_the_table(_GLOSSARY_PATH.read_text(), table))
    assert {"Aspirate", "pick_up_tips", "discard tips"} <= hits
