"""FR-3 phrase parity (W3): the Python ``derive_phrase`` and the browser-side
``web-repl/shell/coxswain/phrase.js`` must agree on the SAME fixtures, including
the multi-target ``+<n-1> more`` rule and the 60-char regenerate-from-truncated-
descriptor rule.

Three layers are asserted here:

1. **Schema drift guard** -- every fixture's ``verb`` equals the W2 tool
   schema's verb for that call name. Fixtures are generated from the schema
   (RISK-8), so if the schema's verb changes, this fails instead of letting
   both sides silently agree on a stale fixture.
2. **Python derivation** -- ``coxswain.phrase.derive_phrase`` reproduces each
   fixture's ``expected_phrase`` exactly.
3. **JS derivation (true cross-implementation parity)** -- when ``bun`` is
   available, the same fixtures are evaluated through ``phrase.js`` in a
   subprocess; any disagreement between the two implementations fails here,
   not just against the frozen expected strings.

The fixtures double as the ``FixtureParseSource`` corpus (§7), so the
ParseSource round-trip is proven over the same data.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from coxswain.parse_source import FixtureParseSource, ParseError
from coxswain.phrase import PHRASE_MAX_CHARS, derive_phrase, phrase_matches
from coxswain.plr.tool_schema import TOOL_SCHEMA

_REPO_ROOT = Path(__file__).resolve().parents[2]
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "parsed_calls"
PHRASE_JS = _REPO_ROOT / "web-repl" / "shell" / "coxswain" / "phrase.js"


def _fixtures() -> list[dict]:
    entries = []
    for path in sorted(FIXTURE_DIR.glob("*.json")):
        entry = json.loads(path.read_text())
        entry["_fixture_file"] = path.name
        entries.append(entry)
    assert entries, "no parsed_calls fixtures found -- the corpus is empty"
    return entries


# --- layer 1: fixtures stay glued to the live tool schema -----------------------


@pytest.mark.parametrize("entry", _fixtures(), ids=lambda e: e["_fixture_file"])
def test_fixture_verb_matches_tool_schema(entry: dict) -> None:
    spec = TOOL_SCHEMA[entry["name"]]
    assert entry["verb"] == spec.verb
    # The tier floor matters to which fixtures exist at all: an irreversible
    # fixture must never drift onto a call the schema no longer treats as
    # irreversible (AC-13's subject would silently vanish).
    if "irreversible" in entry["_fixture_file"]:
        assert spec.risk_tier.value == "irreversible"


# --- layer 2: Python derivation ---------------------------------------------------


@pytest.mark.parametrize("entry", _fixtures(), ids=lambda e: e["_fixture_file"])
def test_derive_phrase_matches_fixture(entry: dict) -> None:
    derived = derive_phrase({"verb": entry["verb"], "params": entry["params"]})
    assert derived == entry["expected_phrase"]


@pytest.mark.parametrize("entry", _fixtures(), ids=lambda e: e["_fixture_file"])
def test_every_expected_phrase_is_within_cap_and_typeable(entry: dict) -> None:
    phrase = entry["expected_phrase"]
    assert len(phrase) <= PHRASE_MAX_CHARS


def test_matching_normalization_only_as_fr3_specifies() -> None:
    """Case-insensitive, collapsed internal whitespace, trimmed ends. No other
    normalization (no punctuation folding, no unicode folding)."""
    required = "discard tips at C3"
    for typed in ("discard tips at C3", "  DISCARD   TIPS AT c3  ", "discard\ttips\nat C3"):
        assert phrase_matches(typed, required), typed
    for typed in ("discard tips at C33", "discard", "discardtipsatC3", "discard tips at Ⅽ3"):
        assert not phrase_matches(typed, required), typed
    assert not phrase_matches("", required)
    assert not phrase_matches(None, required)  # type: ignore[arg-type]


def test_multi_target_suffix_counts_all_targets() -> None:
    derived = derive_phrase(
        {"verb": "transfer to", "params": {"destination": ["B1", "B2", "B3", "B4"]}}
    )
    assert derived == "transfer to B1 +3 more"


def test_quantity_values_never_render_into_a_phrase() -> None:
    with pytest.raises(ValueError):
        derive_phrase({"verb": "transfer to", "params": {"destination": 50}})
    with pytest.raises(ValueError):
        derive_phrase({"verb": "transfer to", "params": {"destination": True}})


# --- ParseSource (§7): interface + fixture-backed stub ----------------------------


def test_fixture_parse_source_round_trips_the_corpus() -> None:
    source = FixtureParseSource(fixture_dir=FIXTURE_DIR)
    for entry in _fixtures():
        call = source.parse(entry["utterance"])
        assert call.name == entry["name"]
        assert dict(call.params) == entry["params"]
        assert call.receiver_type == entry["receiver_type"]
        assert tuple(call.missing_required) == tuple(entry.get("missing_required", ()))


def test_fixture_parse_source_normalizes_whitespace_and_case() -> None:
    source = FixtureParseSource(fixture_dir=FIXTURE_DIR)
    call = source.parse("  DISCARD   THE TIPS AT C3 ")
    assert call.name == "discard_tips"


def test_fixture_parse_source_fails_loud_on_unknown_utterance() -> None:
    source = FixtureParseSource(fixture_dir=FIXTURE_DIR)
    with pytest.raises(ParseError):
        source.parse("reformat the entire deck")


def test_fixture_parse_source_default_dir_resolves_without_argument() -> None:
    source = FixtureParseSource()
    call = source.parse("transfer from A1 to B1, B2 and B3")
    assert call.name == "transfer"


# --- layer 3: true cross-implementation parity via bun ----------------------------


@pytest.mark.skipif(shutil.which("bun") is None, reason="bun not installed")
def test_javascript_phrase_impl_agrees_on_the_same_fixtures() -> None:
    assert PHRASE_JS.is_file(), f"{PHRASE_JS} missing"
    script = f"""
    import {{ derivePhrase }} from "{PHRASE_JS.as_posix()}";
    import {{ readdirSync, readFileSync }} from "node:fs";
    const dir = "{FIXTURE_DIR.as_posix()}";
    const failures = [];
    let count = 0;
    for (const f of readdirSync(dir).sort()) {{
      if (!f.endsWith(".json")) continue;
      const fx = JSON.parse(readFileSync(dir + "/" + f, "utf8"));
      const got = derivePhrase({{ verb: fx.verb, params: fx.params }});
      count += 1;
      if (got !== fx.expected_phrase) {{
        failures.push(`${{f}}: derivePhrase=${{JSON.stringify(got)}} want=${{JSON.stringify(fx.expected_phrase)}}`);
      }}
    }}
    if (failures.length > 0) {{
      console.error(failures.join("\\n"));
      process.exit(1);
    }}
    console.log(`js derivePhrase agreed on ${{count}} fixture(s)`);
    """
    result = subprocess.run(
        ["bun", "-e", script], cwd=str(_REPO_ROOT), capture_output=True, text=True, timeout=120
    )
    assert result.returncode == 0, (
        "phrase.js disagrees with the shared fixtures:\n"
        f"{result.stdout}\n{result.stderr}"
    )
