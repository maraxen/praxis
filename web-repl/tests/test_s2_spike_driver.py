"""No-browser plumbing checks for the S2 spike driver (epic 260929_notebook-display-design, A2).

``scripts/spikes/260929_s2_sanitizer.py`` is the pre-registered S2 probe. Nothing here launches
Playwright or Chromium and nothing here measures S2: it proves the DRIVER, UNIT, STAMP, RESUME,
COMPLETENESS and OUTCOME-GATING plumbing (D17) against a stub probe registry, and the
DERIVATIONS (chosen mimetype, survivorship, trust corroboration, the D1 branch, the controls)
against synthetic reads, so that when the real run happens a plumbing bug cannot be mistaken for
a finding.

Every unit runs as a REAL subprocess (``scripts/unit_runner.run_unit``, real ``Watchdog``, real
stamps), started through a tiny stub launcher that loads the driver by path and swaps in the
stub probes / session / input environment. Timeouts are shrunk through the
``main(..., unit_timeout_s=, driver_extra_s=)`` parameters (never a CLI flag: the real budget is
fixed at 5 min and pre-registered).

Positive and negative controls, both present:

* the live positive control passes for a fully intact trusted render and FAILS when an element,
  an attribute, a style declaration or the ``onclick`` sentinel is missing;
* the negative control passes for a sanitized render and FAILS when the ``<script>`` survives
  while the model says untrusted (the trust read is then uncorroborated), when nothing rendered,
  and when it errored.

The in-page reader (``readOutput``) runs under ``bun`` against a real DOM from jsdom when both
resolve (skipped otherwise, e.g. in CI, which has no jsdom): once over the unsanitized bundle
and once over simulated sanitizers, so a typo in the JS or a mismatch between the JS keys and
the Python derivations cannot survive to the real run.
"""

from __future__ import annotations

import importlib.util
import json
import os
import re
import shutil
import subprocess
import sys
import textwrap
import types
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

import pytest
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[2]
DRIVER_PATH = REPO_ROOT / "scripts" / "spikes" / "260929_s2_sanitizer.py"
SIDECAR_PATH = DRIVER_PATH.with_suffix(".bth.toml")

pytestmark = pytest.mark.timeout(180)


@pytest.fixture(scope="module")
def s2():
    spec = importlib.util.spec_from_file_location("s2_driver_under_test", DRIVER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["s2_driver_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# Synthetic raw reads (what ``S2_JS.readOutput`` returns) and the unit fields built from them
# --------------------------------------------------------------------------- #


def raw_read(
    m: Any,
    *,
    trusted: bool,
    mime: str = "text/html",
    drop_tags: tuple[str, ...] = (),
    drop_attrs: tuple[str, ...] = (),
    alter: dict[tuple[str, str], str] | None = None,
    onclick: bool | None = None,
    cell_trusted: bool | str | None = "same",
    neg: bool = False,
    rendered: bool = True,
) -> dict[str, Any]:
    """A raw read of one output. ``drop_tags`` removes elements, ``drop_attrs`` removes an
    attribute name from every carrier, ``alter`` rewrites one ``(tag, attr)`` value. ``onclick``
    defaults to the sanitizer rule: the corroborator's onclick survives iff trusted.
    """
    onclick = trusted if onclick is None else onclick
    reads = {
        "output_model_trusted": trusted,
        "cell_model_trusted": trusted if cell_trusted == "same" else cell_trusted,
        "notebook_model_trusted": None,
        "metadata_trusted": None,
    }
    read: dict[str, Any] = {
        "found_cell": True, "rendered": rendered, "root_found": rendered, "selector_used": "x",
        "mime_nodes": [{"mime": mime, "trusted_class": False}] if rendered else [],
        "chosen_mime": mime if rendered else None, "model": {}, "trust_reads": reads,
        "corroborator": {"found": False, "onclick": None, "kind": None}, "tags": {}, "neg": {},
        "tag_names_seen": [], "text_content": "", "root_html": "",
    }
    if not rendered:
        return read
    if mime == "text/plain":
        read["text_content"] = m.PLAIN_TEXT
        return read
    if neg:
        read["corroborator"] = {"found": True, "onclick": onclick, "kind": "neg"}
        read["neg"] = {
            "script_count": 1 if trusted else 0,
            "onclick_attr_count": 1 if onclick else 0,
            "neg_sentinel_found": True, "onclick_div_found": True, "script_ran": trusted,
        }
        for tag in m.TAGS:
            read["tags"][tag] = {"count": 0, "present": False, "ns": None, "attrs": {}}
        return read
    read["corroborator"] = {"found": True, "onclick": onclick, "kind": "main"}
    read["text_content"] = "S2 probe name line S2-SENTINEL S2 title S2 text S2 ledger cell"
    for tag in m.TAGS:
        if tag in drop_tags:
            read["tags"][tag] = {"count": 0, "present": False, "ns": None, "attrs": {}}
            continue
        attrs = {k: v for k, v in m.CARRIERS[tag].items() if k not in drop_attrs}
        for (t, name), value in (alter or {}).items():
            if t == tag:
                attrs[name] = value
        ns = m.SVG_NS if tag in m.SVG_TAGS else m.XHTML_NS
        read["tags"][tag] = {"count": 1, "present": True, "ns": ns, "attrs": attrs}
    return read


GOOD_FILE = {
    "ok": True, "n_cells": 1, "cell0_n_outputs": 1, "cell0_data_keys": ["text/html", "text/plain"],
    "cell0_execution_count": None, "cell0_trusted_flag": None, "nb_trusted_flag": None,
    "cell0_output_trusted_flags": [None], "cell0_output_types": ["display_data"],
}


def good_file(m: Any, html_text: str) -> dict[str, Any]:
    return {**GOOD_FILE, "data_html_len": len(html_text)}


def live_fields(m: Any, main: dict[str, Any], negr: dict[str, Any], **over: Any) -> dict[str, Any]:
    facts = m.derive_path_facts(main)
    neg_live = m.derive_live_neg(negr, m.derive_path_facts(negr))
    fields = {
        "path": m.PATH_LIVE, "kernel_ready": True, "executed_ok": True,
        "reads": {"main": main, "neg": negr}, "facts": facts, "neg_bundle_live": neg_live,
        "positive_control_ok": m.live_positive_control_ok(facts, neg_live), "reason": None,
    }
    fields.update(over)
    return fields


def static_fields(m: Any, read: dict[str, Any], html_text: str, path: str, **over: Any) -> dict[str, Any]:
    facts = m.derive_path_facts(read)
    fr = good_file(m, html_text)
    fields = {
        "path": path, "file_readback": fr, "file_ok": m.crafted_file_ok(fr, len(html_text)),
        "read": read, "facts": facts, "reason": m.explain(facts),
    }
    fields.update(over)
    return fields


def neg_fields(m: Any, read: dict[str, Any], **over: Any) -> dict[str, Any]:
    fields = static_fields(m, read, m.NEG_HTML, m.PATH_NEG)
    neg = m.derive_neg(read, fields["facts"])
    fields["neg"] = neg
    fields["negative_control_failed_as_required"] = neg["failed_as_required"]
    fields.update(over)
    return fields


def exec_fields(m: Any, close: dict[str, Any], reload: dict[str, Any], **over: Any) -> dict[str, Any]:
    fc, fr_ = m.derive_path_facts(close), m.derive_path_facts(reload)
    merged, agree = m.merge_reopen(fc, fr_)
    saved = {**GOOD_FILE, "cell0_execution_count": 1}
    fields = {
        "path": m.PATH_EXEC, "kernel_ready": True, "executed_ok": True,
        "live_read": raw_read(m, trusted=True), "live_trust_before_save": True,
        "save_method": "context.save", "saved_file": saved, "saved_file_ok": m.saved_file_ok(saved),
        "close_ok": True, "reopen_close": close, "reload_reopen_method": "docmanager_open",
        "reopen_reload": reload, "facts_close": fc, "facts_reload": fr_, "reopen_agree": agree,
        "facts": merged, "reason": None,
    }
    fields.update(over)
    return fields


def scenario_fields(
    m: Any, *, crafted: dict[str, Any] | None = None, executed_trusted: bool = True,
    exec_kw: dict[str, Any] | None = None,
) -> dict[str, dict[str, Any]]:
    """A complete, internally consistent run: live trusted intact, the crafted path as given
    (default: an untrusted render with everything but the onclick kept, i.e. S2-A), the
    executed path trusted (S2-T) or matching the crafted path, and a sanitized negative bundle.
    """
    crafted_kw = crafted if crafted is not None else {}
    crafted_read = raw_read(m, trusted=False, **crafted_kw)
    if executed_trusted:
        ex = raw_read(m, trusted=True)
    else:
        ex = raw_read(m, trusted=False, **{**crafted_kw, **(exec_kw or {})})
    neg_mime = crafted_kw.get("mime", "text/html")
    neg_read = raw_read(m, trusted=False, neg=True, mime=neg_mime)
    return {
        "live": live_fields(m, raw_read(m, trusted=True), raw_read(m, trusted=True, neg=True)),
        "crafted": static_fields(m, crafted_read, m.MAIN_HTML, m.PATH_CRAFTED),
        "executed_saved_reopened": exec_fields(m, ex, ex),
        "neg_script_onclick": neg_fields(m, neg_read),
    }


def arts_from(m: Any, fields: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
    return {u: {**f, "error": None} for u, f in fields.items()}


# --------------------------------------------------------------------------- #
# Stub launcher: the real driver code, stub probes/session/env
# --------------------------------------------------------------------------- #

STUB_SCRIPT = textwrap.dedent(
    """
    import importlib.util, json, os, sys, time
    from pathlib import Path

    spec = importlib.util.spec_from_file_location("s2_driver", os.environ["S2_DRIVER"])
    m = importlib.util.module_from_spec(spec)
    sys.modules["s2_driver"] = m
    spec.loader.exec_module(m)
    PLAN = json.loads(os.environ["S2_STUB_PLAN"])
    FAKE = json.loads(os.environ["S2_STUB_ENV"])
    m.build_env = lambda args: m.InputEnv(**FAKE)


    class Sess:
        pageerrors = ["stub pageerror"]

        def __init__(self, unit, out_dir):
            self.unit, self.out = unit, Path(out_dir)

        def close(self):
            paths = m.unit_paths(self.out, self.unit)
            (self.out / f"closed.{self.unit}.json").write_text(json.dumps({
                "saw_artifact": paths["artifact"].exists(),
                "saw_stamp": paths["stamp"].exists(),
                "t": time.time(),
            }))
            if self.unit in PLAN.get("close_hang", []):
                time.sleep(600)


    m.SESSION_FACTORY = lambda unit, args, env: Sess(unit, args.out_dir)


    def make_probe(unit):
        def probe(sess, ctx):
            out = Path(ctx.args.out_dir)
            with open(out / f"count.{unit}", "a") as fh:
                fh.write("x\\n")
            if unit in PLAN.get("hang", []):
                time.sleep(600)
            if unit in PLAN.get("raise", {}):
                raise ValueError(PLAN["raise"][unit])
            return dict(PLAN["fields"][unit])
        return probe


    m.PROBES = {u: make_probe(u) for u in m.UNIT_NAMES}
    sys.exit(m.main(
        sys.argv[1:],
        unit_argv_prefix=[sys.executable, os.path.abspath(__file__)],
        unit_timeout_s=float(os.environ.get("S2_STUB_TIMEOUT", "300")),
        driver_extra_s=float(os.environ.get("S2_STUB_EXTRA", "60")),
    ))
    """
)

FAKE_ENV = {
    "script": "s" * 64, "runner": "r" * 64, "harness": "h" * 64, "dist": "d" * 64, "fixture": "f" * 64,
    "chrome": "c" * 64, "driver": "v" * 64, "base_path": "/", "chrome_path": "", "chrome_version": "stub",
}


class Harness:
    def __init__(self, m: Any, tmp_path: Path) -> None:
        self.m = m
        self.tmp = tmp_path
        self.out = tmp_path / "out"
        self.stub = tmp_path / "stub_launcher.py"
        self.stub.write_text(STUB_SCRIPT)
        self.results = tmp_path / "bth_results.json"
        self.plan: dict[str, Any] = {"fields": scenario_fields(m)}
        self.fake_env = dict(FAKE_ENV)
        self.timeout = "300"
        self.extra = "60"

    def env(self) -> dict[str, str]:
        env = {k: v for k, v in os.environ.items() if k != "PRAXIS_UNIT_TOKEN"}
        env.update(
            S2_DRIVER=str(DRIVER_PATH), S2_STUB_PLAN=json.dumps(self.plan),
            S2_STUB_ENV=json.dumps(self.fake_env), S2_STUB_TIMEOUT=self.timeout,
            S2_STUB_EXTRA=self.extra, BTH_RESULTS_PATH=str(self.results),
        )
        return env

    def cmd(self, *extra: str) -> list[str]:
        return [sys.executable, str(self.stub), "--out-dir", str(self.out), "--dist", str(self.tmp), *extra]

    def driver(self, *extra: str) -> tuple[int, dict[str, Any]]:
        proc = subprocess.run(self.cmd(*extra), env=self.env(), capture_output=True, text=True, timeout=170)
        lines = [ln for ln in proc.stdout.splitlines() if ln.strip().startswith("{")]
        assert lines, f"no aggregate JSON on stdout.\nstdout={proc.stdout!r}\nstderr={proc.stderr[-3000:]}"
        return proc.returncode, json.loads(lines[-1])

    def unit(self, name: str) -> int:
        return subprocess.run(
            self.cmd("--unit", name), env=self.env(), capture_output=True, text=True, timeout=120
        ).returncode

    def count(self, unit: str) -> int:
        p = self.out / f"count.{unit}"
        return len(p.read_text().split()) if p.exists() else 0

    def artifact(self, unit: str) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, unit)["artifact"].read_text())

    def stamp(self, unit: str) -> dict[str, Any]:
        return json.loads(self.m.unit_paths(self.out, unit)["stamp"].read_text())

    def flat(self) -> dict[str, Any]:
        return json.loads(self.results.read_text())


@pytest.fixture
def h(s2, tmp_path):
    return Harness(s2, tmp_path)


# --------------------------------------------------------------------------- #
# The unit table is the D17 S2 row; the sidecar pre-registers it
# --------------------------------------------------------------------------- #


def test_unit_table_is_the_d17_s2_row(s2):
    assert s2.UNIT_NAMES == ("live", "crafted", "executed_saved_reopened", "neg_script_onclick")
    assert s2.UNIT_TIMEOUT_S == 300.0 and s2.DRIVER_EXTRA_S == 60.0


def test_sidecar_preregisters_the_design(s2):
    text = SIDECAR_PATH.read_text()
    sidecar = tomllib.loads(text)
    design = sidecar["design"]
    assert design["unit_list"] == list(s2.UNIT_NAMES)
    for unit in s2.UNITS:
        spec = design["units"][unit.name]
        assert spec["timeout_s"] == 300 and spec["required_fields"] == list(unit.required)
        assert spec["upstream"] == []
    assert design["timeouts"]["unit_s"] == 300 and design["timeouts"]["driver_kill_s"] == 360
    assert design["timeouts"]["whole_run_timeout"] == "none"
    assert design["fact_keys"]["keys"] == list(s2.FACT_KEYS)
    inputs = " ".join(design["hashed_inputs"])
    for name in ("script", "runner", "harness", "dist", "fixture", "chrome", "driver"):
        assert name in inputs, name
    for phrase in (
        "stamp.exit == 0", "no error finding", "every field pre-registered", "os._exit",
        "unit_runner.Watchdog", "exits 3", "regardless of reuse",
    ):
        assert phrase in text, phrase
    # completeness and error-finding semantics
    assert "error finding" in design["completeness"] and "never reused" in design["completeness"]
    assert "has NOT failed as required" in text
    assert design["authored"]["elements"] == list(s2.TAGS)
    assert design["authored"]["data_attribute_names"] == list(s2.DATA_ATTR_NAMES)
    assert "bth run" in design["real_run_command"] and "--out " not in design["real_run_command"]


def _clauses(condition: str) -> list[tuple[str, str, Any]]:
    out: list[tuple[str, str, Any]] = []
    for clause in condition.split(" AND "):
        match = re.fullmatch(r"(\w+) (=|<>) (true|false|'[^']*')", clause.strip())
        assert match, clause
        field, op, raw = match.groups()
        value: Any = {"true": True, "false": False}.get(raw, raw.strip("'"))
        out.append((field, op, value))
    return out


def _matches(condition: str, flat: dict[str, Any]) -> bool:
    for field, op, value in _clauses(condition):
        got = flat.get(field)
        if op == "=" and got != value:
            return False
        if op == "<>" and got == value:
            return False
    return True


def test_sidecar_outcomes_read_only_driver_fields_and_have_one_residual(s2):
    sidecar = tomllib.loads(SIDECAR_PATH.read_text())
    schema = set(sidecar["result_schema"])
    arts = arts_from(s2, scenario_fields(s2))
    flat = s2.derive_outcome_fields(arts)["flat"]
    assert set(flat) == schema, (set(flat) ^ schema)
    residual = [k for k, v in sidecar["outcomes"].items() if v["is_residual"]]
    assert residual == ["invalid"]
    for name, outcome in sidecar["outcomes"].items():
        assert outcome["decision"] and outcome["reasoning"], name
        for field, _op, _v in _clauses(outcome["condition"]):
            assert field in schema, (name, field)
    # every D1 branch is a pre-registered outcome, for both executed-path cases
    for key in ("a", "ap", "b", "c", "unmapped"):
        for suffix in ("t", "u"):
            assert f"s2_{key}_exec_{suffix}" in sidecar["outcomes"]
    assert "s2_crafted_trusted" in sidecar["outcomes"]


BRANCH_SCENARIOS = {
    "S2-A": dict(crafted={}),
    "S2-A-prime": dict(crafted={"drop_attrs": ("class",)}),
    "S2-B": dict(crafted={"drop_tags": ("svg", "g", "path", "rect", "text", "title")}),
    "S2-C": dict(crafted={"mime": "text/plain"}),
    "S2-unmapped": dict(crafted={"drop_tags": ("path",)}),
}


@pytest.mark.parametrize("executed_trusted", [True, False])
@pytest.mark.parametrize("branch", list(BRANCH_SCENARIOS))
def test_every_valid_scenario_matches_exactly_one_preregistered_outcome(s2, branch, executed_trusted):
    """The sidecar's outcomes partition the valid world: one and only one outcome fires."""
    sidecar = tomllib.loads(SIDECAR_PATH.read_text())
    fields = scenario_fields(s2, executed_trusted=executed_trusted, **BRANCH_SCENARIOS[branch])
    flat = s2.derive_outcome_fields(arts_from(s2, fields))["flat"]
    assert flat["measurement_valid"] is True, s2.derive_outcome_fields(arts_from(s2, fields))["details"]
    assert flat["crafted_branch"] == branch and flat["exec_trusted"] is executed_trusted
    fired = [n for n, o in sidecar["outcomes"].items() if _matches(o["condition"], flat)]
    suffix = "t" if executed_trusted else "u"
    key = {"S2-A": "a", "S2-A-prime": "ap", "S2-B": "b", "S2-C": "c", "S2-unmapped": "unmapped"}[branch]
    assert fired == [f"s2_{key}_exec_{suffix}"]


def test_crafted_trusted_world_fires_only_its_own_outcome(s2):
    sidecar = tomllib.loads(SIDECAR_PATH.read_text())
    trusted = raw_read(s2, trusted=True)
    fields = scenario_fields(s2)
    fields["crafted"] = static_fields(s2, trusted, s2.MAIN_HTML, s2.PATH_CRAFTED)
    fields["neg_script_onclick"] = neg_fields(s2, raw_read(s2, trusted=True, neg=True))
    derived = s2.derive_outcome_fields(arts_from(s2, fields))
    flat = derived["flat"]
    assert flat["crafted_branch"] == "crafted-trusted" and flat["measurement_valid"] is True, derived["details"]
    assert flat["negative_control_failed_as_required"] is False  # not observed stripped, by construction
    assert [n for n, o in sidecar["outcomes"].items() if _matches(o["condition"], flat)] == ["s2_crafted_trusted"]


def test_an_invalid_run_fires_only_the_residual(s2):
    sidecar = tomllib.loads(SIDECAR_PATH.read_text())
    fields = scenario_fields(s2)
    arts = arts_from(s2, fields)
    arts["crafted"]["error"] = {"type": "X", "message": "m", "traceback_tail": ""}
    flat = s2.derive_outcome_fields(arts)["flat"]
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert [n for n, o in sidecar["outcomes"].items() if _matches(o["condition"], flat)] == ["invalid"]


def test_dry_run_prints_the_plan_and_launches_nothing(s2):
    proc = subprocess.run(
        [sys.executable, str(DRIVER_PATH), "--dry-run", "--out-dir", "unused"],
        capture_output=True, text=True, timeout=60,
    )
    assert proc.returncode == 0, proc.stderr[-2000:]
    plan = json.loads(proc.stdout)
    assert [u["name"] for u in plan["units"]] == list(s2.UNIT_NAMES)
    assert plan["unit_timeout_s"] == 300.0 and plan["driver_timeout_s"] == 360.0
    assert plan["fixture_sha256"] == s2.fixture_sha256()
    assert set(plan["notebooks"]) == {s2.PATH_CRAFTED, s2.PATH_NEG, s2.PATH_LIVE, s2.PATH_EXEC}


# --------------------------------------------------------------------------- #
# The authored fixture covers every D1 element and attribute
# --------------------------------------------------------------------------- #


class _Collect(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.elements: dict[str, dict[str, str]] = {}
        self.counts: dict[str, int] = {}
        self.every: list[tuple[str, dict[str, str]]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.counts[tag] = self.counts.get(tag, 0) + 1
        self.every.append((tag, {k: (v or "") for k, v in attrs}))
        self.elements.setdefault(tag, {k: (v or "") for k, v in attrs})


def test_crafted_html_covers_every_d1_element_and_attribute_once(s2):
    parser = _Collect()
    parser.feed(s2.MAIN_HTML)
    for tag in s2.TAGS:
        assert parser.counts.get(tag) == 1, f"{tag}: one carrier instance per tag"
    seen: set[str] = set()
    for tag, authored in s2.CARRIERS.items():
        got = parser.elements[tag]
        # html.parser lower-cases attribute names; the authored table holds the real spelling
        assert {k.lower(): v for k, v in authored.items()} == got, tag
        seen |= set(authored)
    for attr in s2.D1_ATTRS:
        if attr == "data-*":
            assert set(s2.DATA_ATTR_NAMES) <= seen and all(n.startswith("data-") for n in s2.DATA_ATTR_NAMES)
        else:
            assert attr in seen, attr
    assert "viewBox" in s2.CARRIERS["svg"]
    assert set(s2.D1_ATTRS) - {"data-*"} <= seen
    assert set(s2.GEOMETRY_ATTRS) <= seen
    # the sentinel is a span with an onclick attribute and the bundle has a plain-text pair
    assert 'id="s2-sentinel" onclick="void(0)"' in s2.MAIN_HTML and s2.SENTINEL_TEXT in s2.MAIN_HTML
    assert "<script" not in s2.MAIN_HTML.lower()
    for name, attr in (("style", "style"),):
        assert all(p in s2.CARRIERS["svg"][attr] for p in s2.STYLE_PROPS), name


def test_negative_html_has_a_script_element_and_an_onclick_attribute(s2):
    parser = _Collect()
    parser.feed(s2.NEG_HTML)
    assert parser.counts.get("script") == 1
    assert any("onclick" in attrs for _tag, attrs in parser.every) and s2.NEG_ONCLICK_TEXT in s2.NEG_HTML
    assert s2.NEG_SENTINEL_TEXT in s2.NEG_HTML


def test_crafted_and_negative_notebooks_are_untrusted_by_construction(s2):
    for nb in (s2.crafted_notebook(), s2.neg_notebook()):
        blob = json.dumps(nb)
        assert "trusted" not in blob, "no trusted flag anywhere in the crafted file"
        cell = nb["cells"][0]
        assert cell["execution_count"] is None and cell["cell_type"] == "code"
        out = cell["outputs"][0]
        assert out["output_type"] == "display_data" and set(out["data"]) == {"text/html", "text/plain"}
    assert s2.crafted_notebook()["cells"][0]["outputs"][0]["data"]["text/html"] == s2.MAIN_HTML
    assert s2.neg_notebook()["cells"][0]["outputs"][0]["data"]["text/html"] == s2.NEG_HTML
    assert s2.crafted_notebook()["nbformat"] == 4


def test_display_source_round_trips_the_exact_bundle(s2, monkeypatch):
    """The kernel cells display exactly the bundle the crafted notebook stores (quoting proof)."""
    for source, html_text, plain in (
        (s2.display_source(s2.MAIN_HTML, s2.PLAIN_TEXT), s2.MAIN_HTML, s2.PLAIN_TEXT),
        (s2.display_source(s2.NEG_HTML, s2.NEG_PLAIN), s2.NEG_HTML, s2.NEG_PLAIN),
    ):
        seen: dict[str, Any] = {}
        ipython = types.ModuleType("IPython")
        display_mod = types.ModuleType("IPython.display")

        def display(obj: Any, raw: bool = False, _seen: dict[str, Any] = seen) -> None:
            _seen["obj"], _seen["raw"] = obj, raw

        display_mod.display = display
        ipython.display = display_mod
        monkeypatch.setitem(sys.modules, "IPython", ipython)
        monkeypatch.setitem(sys.modules, "IPython.display", display_mod)
        exec(compile(source, "<cell>", "exec"), {})
        assert seen["raw"] is True
        assert seen["obj"] == {"text/html": html_text, "text/plain": plain}
    live = s2.live_notebook()
    assert [c["source"] for c in live["cells"]] == [
        s2.display_source(s2.MAIN_HTML, s2.PLAIN_TEXT).splitlines(True),
        s2.display_source(s2.NEG_HTML, s2.NEG_PLAIN).splitlines(True),
    ]
    assert all(c["outputs"] == [] for c in live["cells"])


def test_fixture_hash_tracks_the_authored_bytes(s2, monkeypatch):
    before = s2.fixture_sha256()
    assert before == s2.fixture_sha256()
    monkeypatch.setattr(s2, "PLAIN_TEXT", "changed")
    assert s2.fixture_sha256() != before, "the text/plain of the crafted notebook is part of the fixture"
    monkeypatch.undo()
    assert s2.fixture_sha256() == before
    monkeypatch.setattr(s2, "PLAIN_TEXT", s2.PLAIN_TEXT)
    monkeypatch.setitem(s2.CARRIERS["svg"], "viewBox", "0 0 1 1")
    assert s2.fixture_sha256() != before


# --------------------------------------------------------------------------- #
# Derivations: positive and negative controls over synthetic reads
# --------------------------------------------------------------------------- #


def test_live_positive_control_passes_for_a_fully_intact_trusted_render(s2):
    main, negr = raw_read(s2, trusted=True), raw_read(s2, trusted=True, neg=True)
    fields = live_fields(s2, main, negr)
    facts = fields["facts"]
    assert facts["trust_state"] is True and facts["corroboration"] == "onclick"
    assert facts["all_present_intact"] is True and facts["svg_state"] == "full"
    assert facts["svg_drawing_ok"] is True and facts["chosen_mime"] == "text/html"
    assert fields["neg_bundle_live"]["script_present"] and fields["neg_bundle_live"]["onclick_present"]
    assert fields["positive_control_ok"] is True
    assert s2.path_branch(facts, "executed") == "S2-T"
    assert s2.path_branch(facts, "crafted") == "crafted-trusted"


@pytest.mark.parametrize(
    "kw",
    [
        {"drop_tags": ("title",)},
        {"drop_tags": ("details",)},
        {"drop_attrs": ("viewBox",)},
        {"drop_attrs": ("data-praxis-grid",)},
        {"alter": {("rect", "fill"): "#000000"}},
        {"alter": {("svg", "style"): "fill:#2266aa"}},  # a style declaration lost
        {"onclick": False},  # the sentinel's onclick was stripped from a "trusted" render
    ],
)
def test_live_positive_control_fails_when_the_instrument_cannot_see_the_whole_bundle(s2, kw):
    main = raw_read(s2, trusted=True, **kw)
    fields = live_fields(s2, main, raw_read(s2, trusted=True, neg=True))
    assert fields["positive_control_ok"] is False


def test_live_positive_control_fails_when_the_negative_bundle_is_not_visible_live(s2):
    negr = raw_read(s2, trusted=True, neg=True)
    negr["neg"]["script_count"] = 0
    assert live_fields(s2, raw_read(s2, trusted=True), negr)["positive_control_ok"] is False


def test_untrusted_sanitized_render_is_s2_a_only_if_class_and_style_survive_everywhere(s2):
    facts = s2.derive_path_facts(raw_read(s2, trusted=False))
    assert facts["trust_state"] is False and facts["svg_state"] == "full" and facts["svg_drawing_ok"] is True
    assert facts["svg_class_all"] is True and facts["svg_style_all"] is True
    assert s2.path_branch(facts, "crafted") == "S2-A" and s2.path_branch(facts, "executed") == "S2-A"
    one_carrier = s2.derive_path_facts(raw_read(s2, trusted=False, alter={("g", "class"): "other"}))
    assert one_carrier["svg_class_all"] is False and s2.path_branch(one_carrier, "crafted") == "S2-A-prime"
    style_lost = s2.derive_path_facts(raw_read(s2, trusted=False, drop_attrs=("style",)))
    assert style_lost["svg_style_all"] is False and s2.path_branch(style_lost, "crafted") == "S2-A-prime"
    partial_style = s2.derive_path_facts(
        raw_read(s2, trusted=False, alter={("path", "style"): "fill:#2266aa;stroke-width:3px"})
    )
    assert partial_style["svg_style_all"] is False, "a declaration the sanitizer dropped is not survival"


@pytest.mark.parametrize(
    ("kw", "branch"),
    [
        ({"drop_tags": ("svg", "g", "path", "rect", "text", "title")}, "S2-B"),
        ({"drop_tags": ("svg", "g", "path", "rect", "text", "title", "table")}, "S2-unmapped"),
        ({"drop_tags": ("path",)}, "S2-unmapped"),
        ({"drop_tags": ("svg",)}, "S2-unmapped"),  # children surviving without the svg root is partial
        ({"drop_attrs": ("fill",)}, "S2-unmapped"),  # tags survive but the drawing lost its paint
        ({"drop_attrs": ("d",)}, "S2-unmapped"),
        ({"mime": "text/plain"}, "S2-C"),
        ({"mime": "image/svg+xml"}, "S2-unmapped"),
    ],
)
def test_branch_table_untrusted(s2, kw, branch):
    if kw.get("mime") == "image/svg+xml":
        read = raw_read(s2, trusted=False, mime="text/plain")
        read["chosen_mime"] = "image/svg+xml"
        read["mime_nodes"] = [{"mime": "image/svg+xml", "trusted_class": False}]
        read["corroborator"] = {"found": True, "onclick": False, "kind": "main"}
        facts = s2.derive_path_facts(read)
    else:
        facts = s2.derive_path_facts(raw_read(s2, trusted=False, **kw))
    assert facts["trust_state"] is False
    assert s2.path_branch(facts, "crafted") == branch


def test_text_plain_without_the_summary_text_is_unmapped_not_s2_c(s2):
    read = raw_read(s2, trusted=False, mime="text/plain")
    read["text_content"] = "something else entirely"
    facts = s2.derive_path_facts(read)
    assert facts["chosen_mime"] == "text/plain" and facts["corroboration"] == "plain_choice"
    assert s2.path_branch(facts, "crafted") == "S2-unmapped"


@pytest.mark.parametrize(
    "mutate",
    [
        lambda r: r["trust_reads"].update(output_model_trusted=None),  # unreadable
        lambda r: r["trust_reads"].update(cell_model_trusted=True),  # cell model disagrees
        lambda r: r["corroborator"].update(onclick=True),  # onclick survived but model says untrusted
        lambda r: r["corroborator"].update(found=False),  # no corroborator rendered
        lambda r: r.update(rendered=False),
    ],
)
def test_uncorroborated_or_unreadable_trust_is_null_and_never_a_branch(s2, mutate):
    read = raw_read(s2, trusted=False)
    mutate(read)
    facts = s2.derive_path_facts(read)
    assert facts["trust_state"] is None and facts["trust_corroborated"] is False
    assert s2.path_branch(facts, "crafted") is None and s2.path_branch(facts, "executed") is None


def test_trusted_claim_needs_the_onclick_to_have_survived(s2):
    facts = s2.derive_path_facts(raw_read(s2, trusted=True, onclick=False))
    assert facts["trust_state"] is None  # a "trusted" read whose onclick was stripped is not believed


def test_plain_choice_corroboration_is_vetoed_by_a_trusted_class(s2):
    read = raw_read(s2, trusted=False, mime="text/plain")
    read["mime_nodes"][0]["trusted_class"] = True
    assert s2.derive_path_facts(read)["trust_state"] is None


def test_negative_control_passes_when_script_and_onclick_are_observed_stripped(s2):
    read = raw_read(s2, trusted=False, neg=True)
    facts = s2.derive_path_facts(read)
    neg = s2.derive_neg(read, facts)
    assert neg["rendered_ok"] and neg["script_stripped"] is True and neg["onclick_stripped"] is True
    assert neg["failed_as_required"] is True and neg["consistent_with_trust"] is True


def test_negative_control_fails_when_the_script_survives_an_untrusted_render(s2):
    read = raw_read(s2, trusted=False, neg=True)
    read["neg"]["script_count"] = 1
    neg = s2.derive_neg(read, s2.derive_path_facts(read))
    assert neg["script_stripped"] is False
    assert neg["failed_as_required"] is False and neg["consistent_with_trust"] is False


def test_negative_control_fails_when_the_onclick_survives_an_untrusted_read(s2):
    read = raw_read(s2, trusted=False, neg=True, onclick=True)
    facts = s2.derive_path_facts(read)
    assert facts["trust_state"] is None  # model says untrusted, onclick survived: not corroborated
    neg = s2.derive_neg(read, facts)
    assert neg["failed_as_required"] is False and neg["consistent_with_trust"] is False


def test_negative_control_is_not_failed_as_required_when_nothing_rendered(s2):
    read = raw_read(s2, trusted=False, neg=True, rendered=False)
    neg = s2.derive_neg(read, s2.derive_path_facts(read))
    assert neg["rendered_ok"] is False and neg["script_stripped"] is None
    assert neg["failed_as_required"] is False and neg["consistent_with_trust"] is False


def test_negative_control_is_vacuous_but_consistent_for_a_text_plain_render(s2):
    read = raw_read(s2, trusted=False, neg=True, mime="text/plain")
    facts = s2.derive_path_facts(read)
    neg = s2.derive_neg(read, facts)
    assert neg["plain_render"] is True and neg["failed_as_required"] is False
    assert neg["consistent_with_trust"] is True


def test_reopen_reads_must_agree_or_trust_becomes_null(s2):
    a = s2.derive_path_facts(raw_read(s2, trusted=True))
    b = s2.derive_path_facts(raw_read(s2, trusted=False))
    merged, agree = s2.merge_reopen(a, b)
    assert agree is False and merged["trust_state"] is None and merged["trust_corroborated"] is False
    merged, agree = s2.merge_reopen(b, s2.derive_path_facts(raw_read(s2, trusted=False)))
    assert agree is True and merged["trust_state"] is False
    other = s2.derive_path_facts(raw_read(s2, trusted=False, drop_attrs=("class",)))
    assert s2.merge_reopen(b, other)[1] is False, "same trust but a different survivorship is disagreement"


def test_file_readbacks(s2):
    assert s2.crafted_file_ok(good_file(s2, s2.MAIN_HTML), len(s2.MAIN_HTML))
    assert not s2.crafted_file_ok({**good_file(s2, s2.MAIN_HTML), "cell0_trusted_flag": True}, len(s2.MAIN_HTML))
    assert not s2.crafted_file_ok({**good_file(s2, s2.MAIN_HTML), "cell0_execution_count": 3}, len(s2.MAIN_HTML))
    assert not s2.crafted_file_ok({**good_file(s2, s2.MAIN_HTML), "data_html_len": 5}, len(s2.MAIN_HTML))
    assert not s2.crafted_file_ok({"ok": False, "error": "x"}, 1)
    saved = {**GOOD_FILE, "cell0_execution_count": 2}
    assert s2.saved_file_ok(saved)
    assert not s2.saved_file_ok({**saved, "cell0_execution_count": None})
    assert not s2.saved_file_ok({**saved, "cell0_output_types": ["error"]})


def test_paths_consistent_rule(s2):
    f = s2.paths_consistent
    assert f("S2-A", "S2-T") and f("crafted-trusted", "S2-T") and f("S2-A", "S2-A")
    assert not f("S2-A", "S2-B") and not f("crafted-trusted", "S2-A")
    assert not f(None, "S2-T") and not f("S2-A", None)


@pytest.mark.parametrize(
    ("unit", "mutate"),
    [
        ("live", lambda f: f.update(executed_ok=False)),
        ("live", lambda f: f.update(positive_control_ok=False)),
        ("crafted", lambda f: f.update(file_ok=False)),
        ("neg_script_onclick", lambda f: f.update(file_ok=False)),
        ("neg_script_onclick", lambda f: f["neg"].update(consistent_with_trust=False)),
        ("executed_saved_reopened", lambda f: f.update(executed_ok=False)),
        ("executed_saved_reopened", lambda f: f.update(saved_file_ok=False)),
        ("executed_saved_reopened", lambda f: f.update(close_ok=False)),
        ("executed_saved_reopened", lambda f: f.update(reopen_agree=False)),
        ("crafted", lambda f: f["facts"].update(rendered=False)),
        ("crafted", lambda f: f["facts"].update(trust_corroborated=False)),
    ],
)
def test_an_uncontrolled_or_inconsistent_measurement_makes_the_run_invalid(s2, unit, mutate):
    arts = arts_from(s2, scenario_fields(s2))
    assert s2.derive_outcome_fields(arts)["flat"]["measurement_valid"] is True
    mutate(arts[unit])
    assert s2.derive_outcome_fields(arts)["flat"]["measurement_valid"] is False


def test_crafted_and_negative_notebooks_must_agree_on_trust_and_mimetype(s2):
    fields = scenario_fields(s2)
    fields["neg_script_onclick"] = neg_fields(s2, raw_read(s2, trusted=False, neg=True, mime="text/plain"))
    flat = s2.derive_outcome_fields(arts_from(s2, fields))
    assert flat["details"]["validity_checks"]["crafted_neg_mime_agree"] is False
    assert flat["flat"]["measurement_valid"] is False


def test_exec_untrusted_on_a_different_branch_than_crafted_is_invalid(s2):
    fields = scenario_fields(s2, executed_trusted=False, exec_kw={"drop_attrs": ("class",)})
    flat = s2.derive_outcome_fields(arts_from(s2, fields))["flat"]
    assert flat["crafted_branch"] == "S2-A" and flat["exec_branch"] == "S2-A-prime"
    assert flat["paths_consistent"] is False and flat["measurement_valid"] is False


def test_survivorship_table_is_recorded_for_the_three_paths(s2):
    d = s2.derive_outcome_fields(arts_from(s2, scenario_fields(s2, **BRANCH_SCENARIOS["S2-A-prime"])))["details"]
    table = d["survivorship"]
    assert set(table) == {"trusted_live", "untrusted_reopened_crafted", "executed_saved_reopened"}
    assert table["trusted_live"]["elements"]["svg"] is True and table["trusted_live"]["trust_state"] is True
    crafted = table["untrusted_reopened_crafted"]
    assert crafted["attributes"]["svg"]["class"] is False and crafted["attributes"]["svg"]["viewBox"] is True
    assert crafted["chosen_mime"] == "text/html"


# --------------------------------------------------------------------------- #
# Driver / unit / stamp / completeness / outcome gating (real subprocesses)
# --------------------------------------------------------------------------- #


def test_full_run_completes_stamps_and_evaluates_outcome_fields(h):
    code, agg = h.driver()
    assert code == 0
    assert agg["all_units_complete"] and agg["outcome_evaluated"]
    assert agg["recomputed"] == list(h.m.UNIT_NAMES) and agg["reused"] == []
    for unit in h.m.UNIT_NAMES:
        art, stamp = h.artifact(unit), h.stamp(unit)
        raw = h.m.unit_paths(h.out, unit)["artifact"].read_bytes()
        assert stamp["artifact_sha256"] == h.m.sha256_bytes(raw)
        assert stamp["exit"] == 0 and stamp["unit"] == unit and stamp["timeout_s"] == 300.0
        assert art["error"] is None and art["pageerrors"] == ["stub pageerror"]
        assert set(stamp["inputs"]) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    flat = h.flat()
    assert flat["measurement_valid"] is True and flat["crafted_branch"] == "S2-A"
    assert flat["exec_trusted"] is True and flat["live_trusted"] is True
    assert flat["negative_control_failed_as_required"] is True and flat["live_positive_control_ok"] is True
    assert flat["crafted_chosen_mime"] == "text/html" and flat["crafted_svg_state"] == "full"
    assert agg["survivorship"]["untrusted_reopened_crafted"]["svg_state"] == "full"


def test_a_complete_but_invalid_run_exits_zero_and_still_writes_its_result(h):
    h.plan["raise"] = {"live": "boom"}
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"] and h.flat()["measurement_valid"] is False


def test_teardown_order_artifact_then_close_then_stamp(h):
    h.driver()
    for unit in h.m.UNIT_NAMES:
        closed = json.loads((h.out / f"closed.{unit}.json").read_text())
        assert closed["saw_artifact"] is True, f"{unit}: artifact must exist before teardown"
        assert closed["saw_stamp"] is False, f"{unit}: stamp must be committed AFTER teardown"
        assert h.stamp(unit)["finished"] >= closed["t"]


def test_resume_reuses_verified_units_and_records_source_and_hashes(h):
    h.driver()
    code, agg = h.driver("--resume")
    assert code == 0 and agg["recomputed"] == [] and len(agg["reused"]) == 4
    for rec in agg["reused"]:
        assert rec["source"].endswith(f"units/{rec['unit']}.json")
        assert rec["artifact_sha256"] == h.stamp(rec["unit"])["artifact_sha256"]
        assert set(rec["inputs"]) >= {"script", "runner", "harness", "dist", "fixture", "chrome", "driver"}
    assert all(h.count(u) == 1 for u in h.m.UNIT_NAMES), "a reused unit must not run again"
    # outcomes are still evaluated over the FULL unit set when everything was reused
    assert agg["outcome_evaluated"] and h.flat()["measurement_valid"] is True


def test_without_resume_everything_is_recomputed(h):
    h.driver()
    _, agg = h.driver()
    assert len(agg["recomputed"]) == 4 and all(h.count(u) == 2 for u in h.m.UNIT_NAMES)


@pytest.mark.parametrize("changed", ["chrome", "driver", "dist", "fixture", "runner", "script", "harness"])
def test_input_mismatch_forces_recompute(h, changed):
    h.driver()
    h.fake_env[changed] = "0" * 64
    _, agg = h.driver("--resume")
    assert agg["reused"] == [] and len(agg["recomputed"]) == 4
    assert all(h.count(u) == 2 for u in h.m.UNIT_NAMES)
    assert all(changed in rec["mismatched"] for rec in agg["stale"])


def test_a_changed_base_path_forces_recompute(h):
    h.driver()
    h.fake_env["base_path"] = "/praxis/"
    _, agg = h.driver("--resume")
    assert len(agg["recomputed"]) == 4 and all("args" in rec["mismatched"] for rec in agg["stale"])


def test_build_env_hashes_repl_smoke_as_the_harness_input(s2, tmp_path, monkeypatch):
    """D17 / AC-2 "Units": the driver loads ``repl_smoke.py`` (``ServedDir``,
    ``chromium_launch_args``, ``resolve_chrome_path``, ``_open_existing_notebook``), so its
    sha256 is the ``harness`` input, in driver mode and ``--unit`` mode alike (both call
    ``build_env``); the fixture input is the authored fixture hash, and headless_shell is refused.
    """
    import argparse

    smoke = tmp_path / "repl_smoke_stub.py"
    smoke.write_text("# harness v1\n")
    chrome = tmp_path / "chrome"
    chrome.write_text("#!/bin/sh\necho stub-chrome 1\n")
    chrome.chmod(0o755)
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "a.txt").write_text("a")
    monkeypatch.setattr(s2, "REPL_SMOKE_PATH", smoke)
    # ``uv.lock`` is gitignored (absent in a fresh worktree); this test is about ``harness``
    monkeypatch.setattr(s2.unit_runner, "driver_input", lambda **kw: "v" * 64)
    monkeypatch.setattr(s2, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda explicit: chrome))
    args = argparse.Namespace(chrome_path=None, dist=str(dist), base_path="/")
    env1 = s2.build_env(args)
    assert env1.harness == s2.sha256_file(smoke) and env1.fixture == s2.fixture_sha256()
    assert env1.harness != env1.runner and env1.harness != env1.script
    smoke.write_text("# harness v2\n")
    env2 = s2.build_env(args)
    assert env2.harness != env1.harness and env2.runner == env1.runner and env2.script == env1.script
    inputs = s2.compute_inputs("crafted", env2)
    assert inputs["harness"] == env2.harness
    assert set(inputs) == {"script", "runner", "harness", "dist", "fixture", "chrome", "driver", "args"}
    headless = tmp_path / "chrome-headless-shell"
    headless.write_text("#!/bin/sh\n")
    headless.chmod(0o755)
    monkeypatch.setattr(s2, "repl_smoke", lambda: types.SimpleNamespace(resolve_chrome_path=lambda explicit: headless))
    with pytest.raises(RuntimeError, match="headless shell"):
        s2.build_env(args)


def test_a_tampered_artifact_is_not_reused(h):
    h.driver()
    path = h.m.unit_paths(h.out, "crafted")["artifact"]
    text = path.read_text()
    assert '"reason": null' in text
    path.write_text(text.replace('"reason": null', '"reason": "tampered"', 1))
    _, agg = h.driver("--resume")
    assert agg["recomputed"] == ["crafted"] and len(agg["reused"]) == 3
    assert h.count("crafted") == 2


def test_error_finding_is_complete_counts_against_outcomes_and_is_never_reused(h):
    h.plan["raise"] = {"crafted": "probe blew up"}
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"], "a raised probe is a COMPLETE unit"
    err = h.artifact("crafted")["error"]
    assert err["type"] == "ValueError" and err["message"] == "probe blew up"
    assert 0 < len(err["traceback_tail"].encode()) <= 4096
    assert h.stamp("crafted")["exit"] == 1
    assert agg["error_findings"]["crafted"]["type"] == "ValueError"
    # it blocks nothing it should not: every other unit still ran, completed and stamped
    assert agg["incomplete"] == [] and all(h.stamp(u)["exit"] == 0 for u in h.m.UNIT_NAMES if u != "crafted")
    assert all(h.count(u) == 1 for u in h.m.UNIT_NAMES)
    flat = h.flat()
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert flat["crafted_branch"] is None
    assert agg["validity_checks"]["no_error_findings"] is False
    # resume: the errored unit is recomputed, everything else reused
    h.plan.pop("raise")
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == ["crafted"] and len(agg2["reused"]) == 3
    assert h.count("crafted") == 2 and h.flat()["measurement_valid"] is True


@pytest.mark.parametrize("unit", ["live", "crafted", "executed_saved_reopened", "neg_script_onclick"])
def test_an_error_in_any_unit_is_a_complete_invalid_run_never_a_crash(h, unit):
    """Outcome derivation must survive a unit whose artifact has no facts at all."""
    h.plan["raise"] = {unit: "probe blew up"}
    code, agg = h.driver()
    assert code == 0 and agg["outcome_evaluated"] and agg["incomplete"] == []
    flat = h.flat()
    assert flat["measurement_valid"] is False and flat["n_error_units"] == 1
    assert agg["error_findings"][unit]["message"] == "probe blew up"
    assert h.stamp(unit)["exit"] == 1 and h.artifact(unit)["error"]["type"] == "ValueError"


def test_negative_control_that_errors_has_not_failed_as_required(h):
    h.plan["raise"] = {"neg_script_onclick": "boom"}
    code, agg = h.driver()
    assert code == 0
    flat = h.flat()
    assert flat["measurement_valid"] is False
    assert flat["negative_control_failed_as_required"] is False
    assert agg["validity_checks"]["neg_consistent_with_trust"] is False
    assert agg["validity_checks"]["no_error_findings"] is False


def test_negative_control_that_did_not_strip_is_invalid_not_a_branch(h):
    read = raw_read(h.m, trusted=False, neg=True)
    read["neg"]["script_count"] = 1
    h.plan["fields"]["neg_script_onclick"] = neg_fields(h.m, read)
    _, agg = h.driver()
    flat = h.flat()
    assert flat["measurement_valid"] is False and flat["negative_control_failed_as_required"] is False


def test_missing_preregistered_field_is_exit_1_and_not_reusable(h):
    del h.plan["fields"]["crafted"]["file_ok"]
    _, agg = h.driver()
    assert h.stamp("crafted")["exit"] == 1 and h.artifact("crafted")["missing_fields"] == ["file_ok"]
    h.plan["fields"]["crafted"]["file_ok"] = True
    _, agg2 = h.driver("--resume")
    assert agg2["recomputed"] == ["crafted"]


def test_timeout_leaves_no_stamp_no_artifact_and_blocks_outcome_evaluation(h):
    h.plan["hang"] = ["neg_script_onclick"]
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3
    assert agg["all_units_complete"] is False and agg["outcome_evaluated"] is False
    assert agg["timed_out"] == ["neg_script_onclick"] and agg["incomplete"] == ["neg_script_onclick"]
    paths = h.m.unit_paths(h.out, "neg_script_onclick")
    assert not paths["stamp"].exists() and not paths["artifact"].exists()
    marker = json.loads(paths["timeout"].read_text())
    assert marker["unit"] == "neg_script_onclick" and marker["budget_s"] == 6.0
    assert agg["units"]["neg_script_onclick"]["exit"] == 124
    assert not h.results.exists(), "no outcome may be written for an incomplete run"
    assert "outcome_fields" not in agg
    # the other three units are complete and reusable by the next run
    h.plan.pop("hang")
    code2, agg2 = h.driver("--resume")
    assert code2 == 0 and agg2["recomputed"] == ["neg_script_onclick"] and len(agg2["reused"]) == 3
    assert h.results.exists()


def test_hang_in_teardown_is_a_timeout_not_a_stamp(h):
    h.plan["close_hang"] = ["crafted"]
    h.timeout, h.extra = "6", "20"
    code, agg = h.driver()
    assert code == 3 and agg["timed_out"] == ["crafted"]
    paths = h.m.unit_paths(h.out, "crafted")
    assert not paths["stamp"].exists() and not paths["artifact"].exists(), "teardown hangs are bounded BEFORE the stamp"
    assert not h.results.exists()


def test_run_unit_timeout_over_a_valid_stamp_defers_to_the_stamp(s2, h, monkeypatch, caplog):
    import argparse

    class Wrapper:
        """The real runner, but it reports a timeout even though the unit stamped."""

        def run_unit(self, argv, timeout_s, **kw):
            real = s2.unit_runner.run_unit(argv, timeout_s, **kw)
            return real._replace(timed_out=True, killed=True)

    for k, v in h.env().items():
        monkeypatch.setenv(k, v)
    args = argparse.Namespace(out_dir=str(h.out), resume=False, dist=str(h.tmp), base_path="/", chrome_path=None)
    with caplog.at_level("WARNING"):
        code = s2.run_driver(
            args, unit_argv_prefix=[sys.executable, str(h.stub)], runner=Wrapper(),
            env=s2.InputEnv(**FAKE_ENV), unit_timeout_s=300.0, driver_extra_s=60.0,
        )
    assert code == 0
    agg = json.loads((h.out / "result.json").read_text())
    assert agg["timed_out"] == [] and agg["recomputed"] == list(s2.UNIT_NAMES)
    assert "the stamp governs" in caplog.text


def test_missing_repl_smoke_only_affects_real_browser_mode(s2, tmp_path, monkeypatch, caplog):
    """The driver loads ``repl_smoke.py`` lazily, only in real browser mode: the stub-registry
    runs above never load it. If it fails to load for ANY reason (a stand-in that raises at
    import here) ``--dry-run`` degrades to a ``chrome_error`` note and a real driver run exits
    2 with nothing started.
    """
    import argparse

    broken = tmp_path / "repl_smoke_broken.py"
    broken.write_text("class VizCheckError(RuntimeError): pass\nraise VizCheckError('no submodule')\n")
    monkeypatch.setattr(s2, "REPL_SMOKE_PATH", broken)
    monkeypatch.setattr(s2, "_REPL_SMOKE", None)
    args = argparse.Namespace(out_dir=str(tmp_path / "out"), resume=False, dist=str(tmp_path),
                              base_path="/", chrome_path=None, dry_run=True)
    assert s2._dry_run(args) == 0
    monkeypatch.setattr(s2, "_REPL_SMOKE", None)
    args.dry_run = False
    with caplog.at_level("ERROR"):
        assert s2.run_driver(args) == 2
    assert "cannot build the input set" in caplog.text
    assert not list((tmp_path / "out" / "units").glob("*")), "no unit may be started"


# --------------------------------------------------------------------------- #
# The in-page reader under bun + jsdom (skipped when either does not resolve)
# --------------------------------------------------------------------------- #


def _find_jsdom() -> str | None:
    candidates = [os.environ.get("S2_JSDOM_PATH"), str(Path.home() / "node_modules" / "jsdom")]
    for cand in candidates:
        if cand and (Path(cand) / "package.json").is_file():
            return cand
    return None


BUN = shutil.which("bun")
JSDOM = _find_jsdom()
needs_dom = pytest.mark.skipif(BUN is None or JSDOM is None, reason="needs bun and a jsdom install")

JS_HARNESS = r"""
const fs = require('fs');
const {JSDOM} = require(process.env.S2_JSDOM);
const cfg = JSON.parse(fs.readFileSync(process.argv[2], 'utf8'));
const dom = new JSDOM('<!doctype html><body></body>', {runScripts: 'outside-only', pretendToBeVisual: true});
const w = dom.window;
const doc = w.document;
const cellNode = doc.createElement('div'); cellNode.className = 'jp-Cell';
const area = doc.createElement('div'); area.className = 'jp-OutputArea';
const outNode = doc.createElement('div');
outNode.className = 'jp-OutputArea-output';
outNode.setAttribute('data-mime-type', cfg.mime);
if (cfg.mime === 'text/html') {
  outNode.innerHTML = cfg.html;
  const strip = new Set(cfg.strip_attrs || []);
  const dropTags = cfg.drop_tags || [];
  for (const el of Array.from(outNode.querySelectorAll('*'))) {
    if (cfg.sanitize) for (const name of el.getAttributeNames()) if (name.startsWith('on')) el.removeAttribute(name);
    for (const name of strip) if (el.hasAttribute(name)) el.removeAttribute(name);
  }
  if (cfg.sanitize) for (const el of Array.from(outNode.querySelectorAll('script'))) el.remove();
  for (const tag of dropTags) for (const el of Array.from(outNode.getElementsByTagName(tag))) {
    // like sanitize-html's discard mode: the element goes, its children stay
    const parent = el.parentNode;
    while (el.firstChild) parent.insertBefore(el.firstChild, el);
    parent.removeChild(el);
  }
} else {
  outNode.textContent = cfg.plain;
}
area.appendChild(outNode); cellNode.appendChild(area);
const output0 = {trusted: cfg.trusted};
const cell = {node: cellNode, model: {
  toJSON: () => ({outputs: [{output_type: 'display_data', data: {'text/html': cfg.html, 'text/plain': cfg.plain}, metadata: {}}], metadata: {}}),
  outputs: {length: 1, get: (i) => output0}, trusted: cfg.trusted, executionCount: null}};
const panelNode = doc.createElement('div'); panelNode.className = 'jp-NotebookPanel';
const panel = {node: panelNode, content: {widgets: [cell], model: {trusted: cfg.trusted}}, context: {path: 'dir/x.ipynb'}};
w.jupyterapp = {shell: {widgets: () => [panel][Symbol.iterator]()}};
w.eval(cfg.s2js);
const read = w.__s2.readOutput({p: 'x.ipynb', i: 0});
const missing = w.__s2.readOutput({p: 'nope.ipynb', i: 0});
console.log(JSON.stringify({read, missing, has: Object.keys(w.__s2).sort()}));
"""


def _run_dom(s2: Any, tmp_path: Path, **cfg: Any) -> dict[str, Any]:
    script = tmp_path / "s2_dom_harness.js"
    script.write_text(JS_HARNESS)
    conf = tmp_path / "s2_dom_cfg.json"
    base = {
        "s2js": s2.S2_JS, "html": s2.MAIN_HTML, "plain": s2.PLAIN_TEXT, "mime": "text/html",
        "trusted": True, "sanitize": False,
    }
    conf.write_text(json.dumps({**base, **cfg}))
    env = {**os.environ, "S2_JSDOM": str(JSDOM)}
    proc = subprocess.run([str(BUN), "run", str(script), str(conf)], capture_output=True, text=True, timeout=90, env=env)
    assert proc.returncode == 0, proc.stderr[-3000:]
    return json.loads(proc.stdout.strip().splitlines()[-1])


@needs_dom
def test_reader_over_the_unsanitized_bundle_is_the_live_positive_control(s2, tmp_path):
    out = _run_dom(s2, tmp_path)
    assert {"readOutput", "nbPanel", "runCell", "readFile", "saveContext", "closePanel"} <= set(out["has"])
    assert out["missing"]["found_cell"] is False and out["missing"]["rendered"] is False
    read = out["read"]
    assert read["rendered"] and read["chosen_mime"] == "text/html" and read["selector_used"].startswith(".jp-OutputArea-output")
    facts = s2.derive_path_facts(read)
    assert facts["trust_state"] is True and facts["corroboration"] == "onclick"
    assert facts["all_present_intact"] is True and facts["svg_state"] == "full"
    assert facts["svg_class_all"] and facts["svg_style_all"] and facts["svg_data_all"] and facts["svg_drawing_ok"]
    assert all(facts["tags_present"][t] for t in s2.TAGS)
    assert s2.path_branch(facts, "executed") == "S2-T"


@needs_dom
def test_reader_over_a_simulated_sanitizer_finds_the_stripped_pieces(s2, tmp_path):
    def run(**cfg: Any) -> dict[str, Any]:
        out = _run_dom(s2, tmp_path, trusted=False, sanitize=True, **cfg)
        return s2.derive_path_facts(out["read"])

    a = run()
    assert a["trust_state"] is False and a["corroborator_onclick"] is False
    assert s2.path_branch(a, "crafted") == "S2-A", "reader and derivation agree on a benign sanitizer"
    no_class = run(strip_attrs=["class"])
    assert no_class["svg_class_all"] is False and s2.path_branch(no_class, "crafted") == "S2-A-prime"
    no_svg = run(drop_tags=["svg"])
    # children of a stripped svg survive (discard mode keeps them): partial, NOT S2-B
    assert no_svg["svg_state"] == "partial" and s2.path_branch(no_svg, "crafted") == "S2-unmapped"
    no_svg_family = run(drop_tags=["title", "text", "rect", "path", "g", "svg"])
    assert no_svg_family["svg_state"] == "absent" and s2.path_branch(no_svg_family, "crafted") == "S2-B"


@needs_dom
def test_reader_negative_control_over_a_simulated_sanitizer(s2, tmp_path):
    kw = dict(html=s2.NEG_HTML, plain=s2.NEG_PLAIN, trusted=False)
    stripped = _run_dom(s2, tmp_path, sanitize=True, **kw)["read"]
    neg = s2.derive_neg(stripped, s2.derive_path_facts(stripped))
    assert neg["failed_as_required"] is True and neg["script_count"] == 0 and neg["onclick_attr_count"] == 0
    # negative: a "sanitizer" that does nothing leaves the script and onclick, so the control fails
    kept = _run_dom(s2, tmp_path, sanitize=False, **kw)["read"]
    neg_kept = s2.derive_neg(kept, s2.derive_path_facts(kept))
    assert neg_kept["script_count"] == 1 and neg_kept["onclick_attr_count"] == 1
    assert neg_kept["failed_as_required"] is False and neg_kept["consistent_with_trust"] is False
    # and the same content under a trusted model is consistent (nothing stripped, trusted)
    live = _run_dom(s2, tmp_path, sanitize=False, html=s2.NEG_HTML, plain=s2.NEG_PLAIN, trusted=True)["read"]
    live_facts = s2.derive_path_facts(live)
    assert live_facts["trust_state"] is True
    assert s2.derive_live_neg(live, live_facts)["script_present"] and s2.derive_live_neg(live, live_facts)["onclick_present"]


@needs_dom
def test_reader_on_a_plain_text_render(s2, tmp_path):
    out = _run_dom(s2, tmp_path, mime="text/plain", trusted=False)["read"]
    facts = s2.derive_path_facts(out)
    assert facts["chosen_mime"] == "text/plain" and facts["plain_text_ok"] is True
    assert facts["corroboration"] == "plain_choice" and s2.path_branch(facts, "crafted") == "S2-C"


def test_the_installed_js_library_is_syntactically_valid_and_idempotent():
    if BUN is None:
        pytest.skip("needs bun")
    script = (
        "globalThis.window = globalThis; globalThis.requestAnimationFrame = (f) => setTimeout(f, 0);\n"
        "const src = " + json.dumps(_js_src()) + ";\n"
        "const a = eval(src); const first = window.__s2; const b = eval(src);\n"
        "console.log(JSON.stringify({a, b, same: first === window.__s2, n: Object.keys(window.__s2).length}));\n"
    )
    proc = subprocess.run([str(BUN), "-e", script], capture_output=True, text=True, timeout=60)
    assert proc.returncode == 0, proc.stderr[-2000:]
    out = json.loads(proc.stdout.strip().splitlines()[-1])
    assert out["a"] is True and out["b"] is True and out["same"] is True and out["n"] > 10


def _js_src() -> str:
    text = DRIVER_PATH.read_text()
    match = re.search(r'S2_JS = r"""(.*?)"""', text, re.DOTALL)
    assert match
    return match.group(1)
