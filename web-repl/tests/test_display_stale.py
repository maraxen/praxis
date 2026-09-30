"""Browserless tests for ``praxis/display/stale.py`` (task B7, backlog #5639): the kernel side of
staleness. Per-resource ``rev``, the display session, the debounced announcer, the drawn-state digest
filter and the R21 check. Closes AC-18, and the kernel-side part of AC-19 / AC-23 (the ``rev`` and
``session`` a stamp carries, and the ``praxis:resource-changed`` message the shell listens for).

Spec: ``260929_notebook-display-epic.md`` D7 (stamps, "Rev bumps are filtered on the drawn state",
settling, the announcement, the "R21 check"), D2 (stamp fields ``resource``, ``rev``, ``session``,
``exec``), section 4 (the ``stale.py`` row), AC-18, and the sprint notes (S3-D: ``post_run_cell`` does
not fire for top-level-``await`` cells, so the announcer runs from debounced PLR callbacks).

**PyLabRobot.** Every PLR object is the REAL 1.0.0b1 pin, built with the constructors of the ported
design fixture (``web-repl/design/notebook-display/make_fixture.py``), on the chatterbox backend. The
venv's editable PLR can be the old 0.2.2, which fires none of the callbacks the digest filter exists
for, so the first test asserts the version. Run with ``PYTHONPATH=<PLR 1.0.0b1 source>`` prepended
when the venv is not on the pin.

**Seams.** ``stale.py`` takes an injected ``post(str)``, an injected ``loop`` (anything with
``call_later(delay, cb) -> handle`` and ``handle.cancel()``) and an injected ``exec_count()``, so a
fake loop with virtual time and a recording poster drive it deterministically. ``import js`` is
allowed in ``make_repl_poster()`` only, which is tested against a fake ``js`` module.

**Import discipline** (ADR 260817 Sec 2.4). ``praxis/display`` is loaded by path under the synthetic
package ``_praxis_display_under_test``; ``web-repl/overlay/assets/python`` is never put on
``sys.path`` (its ``praxis/`` would shadow the repo's real package; ``test_rid_invariant.py`` guards
it).

**Controls.** Every check that could pass vacuously has a control that must FAIL: the R21 gate is run
against synthetic code uses of the channel name (four forms, and a same-line documentation mention),
against a missing path (the first ``grep`` exits 2, which a plain pipeline would read as a pass) and
against a documentation-only tree; the import lints against snippets that break each rule; the
"callbacks fired" claims against recording callbacks; the rollback case against a succeeding op and
against a rollback that DOES change what is drawn (residue).
"""

from __future__ import annotations

import ast
import asyncio
import functools
import importlib
import importlib.util
import json
import re
import subprocess
import sys
import textwrap
import types
from pathlib import Path

import pytest

import pylabrobot

_TESTS_DIR = Path(__file__).resolve().parent
_WEB_REPL = _TESTS_DIR.parent
_REPO_ROOT = _WEB_REPL.parent
_DISPLAY_DIR = _WEB_REPL / "overlay" / "assets" / "python" / "praxis" / "display"
_STALE_PATH = _DISPLAY_DIR / "stale.py"
_FIXTURE_PATH = _WEB_REPL / "design" / "notebook-display" / "make_fixture.py"
_PKG = "_praxis_display_under_test"

CHANNEL = "praxis_repl"
MESSAGE_TYPE = "praxis:resource-changed"
JSON_CAP = 4096
DEBOUNCE = 0.1

# The three paths of AC-18's R21 check, relative to the repo root.
R21_PATHS = (
    "web-repl/overlay/assets/python/praxis/viz/",
    "web-repl/overlay/assets/visualizer/",
    "web-repl/overlay/assets/visualizer-augmentations/",
)

# D7 "R21 check", verbatim (Revision 11, C11-8). ``<paths>`` is the path list.
R21_LINE_1 = (
    """grep -rn "praxis_repl" <paths> | sed 's/``praxis_repl``//g' | grep "praxis_repl"; """
    """s=("${PIPESTATUS[@]}")"""
)
R21_LINE_2 = """[ "${s[0]}" -le 1 ] && [ "${s[1]}" -eq 0 ] && [ "${s[2]}" -eq 1 ]"""

_THIRD_PARTY = {"pylabrobot", "IPython", "js", "pyodide"}


# --------------------------------------------------------------------------- loading


def _package():
    """The synthetic package for praxis/display (no __init__ is run, sys.path is untouched)."""
    if _PKG not in sys.modules:
        module = types.ModuleType(_PKG)
        module.__path__ = [str(_DISPLAY_DIR)]
        module.__package__ = _PKG
        sys.modules[_PKG] = module
    return sys.modules[_PKG]


@pytest.fixture(scope="module", autouse=True)
def _plr_is_the_pin():
    """A wrong PLR must fail loudly, never pass silently (the venv may carry 0.2.2)."""
    version = str(getattr(pylabrobot, "__version__", ""))
    assert version.startswith("1.0.0b1"), (
        f"PyLabRobot {version!r} at {pylabrobot.__file__} is not the 1.0.0b1 pin; "
        "run with PYTHONPATH=<PLR 1.0.0b1 source> prepended"
    )
    assert Path(pylabrobot.__file__).is_file()


@pytest.fixture(scope="module")
def st():
    """praxis/display/stale.py. A missing module is the RED reason."""
    if not _STALE_PATH.is_file():
        pytest.fail(f"praxis/display/stale.py does not exist yet: {_STALE_PATH}")
    _package()
    return importlib.import_module(f"{_PKG}.stale")


@pytest.fixture(scope="module")
def lw(st):
    return importlib.import_module(f"{_PKG}.labware")


@pytest.fixture(scope="module")
def fx():
    """The ported design fixture module (its constructors are the ones the tests build with)."""
    spec = importlib.util.spec_from_file_location("_praxis_make_fixture_under_test", _FIXTURE_PATH)
    module = importlib.util.module_from_spec(spec)
    sys.modules["_praxis_make_fixture_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- world and fakes


def _async_test(fn):
    """Run an ``async def`` test to completion (pytest-asyncio is not a dependency)."""

    @functools.wraps(fn)
    def run(*args, **kwargs):
        return asyncio.run(fn(*args, **kwargs))

    return run


class _World(types.SimpleNamespace):
    """The fixture layout after its three column transfers, plus a trough holding 100 uL.

    ``source`` A1 holds 150 uL, ``assay`` A1 holds 50 uL (committed), 8 tips are gone from
    ``tips_300`` (columns 1-3), and ``trough`` sits on its own carrier at track 15.
    """


async def _world(fx) -> _World:
    from pylabrobot.resources.hamilton import Trough_CAR_5R60_A00, hamilton_1_trough_60mL_Vb

    deck, lh = await fx.assemble()
    await fx.run_transfers(lh, deck)
    carrier = Trough_CAR_5R60_A00(name="trough_carrier")
    carrier[0] = trough = hamilton_1_trough_60mL_Vb(name="trough")
    deck.assign_child_resource(carrier, track=15)
    trough.tracker.set_volume(100.0)
    return _World(
        deck=deck,
        lh=lh,
        source=deck.get_resource("source"),
        assay=deck.get_resource("assay"),
        tips=deck.get_resource("tips_300"),
        trough=trough,
    )


class _Handle:
    def __init__(self, when, cb, args):
        self.when, self.cb, self.args, self.cancelled_flag = when, cb, args, False

    def cancel(self):
        self.cancelled_flag = True

    def cancelled(self):
        return self.cancelled_flag


class FakeLoop:
    """``call_later`` with virtual time: ``advance(dt)`` runs every live timer that falls due."""

    def __init__(self):
        self.now = 0.0
        self.handles: list[_Handle] = []
        self.delays: list[float] = []
        self.fired = 0

    def call_later(self, delay, cb, *args):
        handle = _Handle(self.now + delay, cb, args)
        self.handles.append(handle)
        self.delays.append(delay)
        return handle

    def live(self) -> list[_Handle]:
        return [h for h in self.handles if not h.cancelled_flag]

    def advance(self, dt):
        target = self.now + dt
        while True:
            due = sorted((h for h in self.live() if h.when <= target + 1e-12), key=lambda h: h.when)
            if not due:
                break
            handle = due[0]
            self.now = max(self.now, handle.when)
            handle.cancelled_flag = True  # consumed
            self.fired += 1
            handle.cb(*handle.args)
        self.now = target


class _Exec:
    """A settable ``get_ipython().execution_count``."""

    def __init__(self, n=1):
        self.n = n

    def __call__(self):
        return self.n


class _Posts(list):
    """A recording poster: appends the raw ``json`` string, ``.msgs`` parses them."""

    def __call__(self, payload):
        self.append(payload)

    @property
    def msgs(self) -> list[dict]:
        return [json.loads(p) for p in self]


def _session(st, *, loop="fake", exec_count=None, session_id="sess-test", posts=None):
    posts = _Posts() if posts is None else posts
    if loop == "fake":
        loop = FakeLoop()
    session = st.DisplaySession(
        posts, loop=loop, exec_count=exec_count or _Exec(1), session_id=session_id
    )
    return session, posts, loop


def _count_state_callbacks(*resources):
    """Register a recording callback on each resource; ``n[0]`` counts every fire."""
    n = [0]
    for res in resources:
        res.register_state_update_callback(lambda _state, n=n: n.__setitem__(0, n[0] + 1))
    return n


def _all_nodes(res):
    return [res, *res.get_all_children()]


# --------------------------------------------------------------------------- module shape


def test_constants_are_the_spec_values(st):
    assert st.CHANNEL == CHANNEL
    assert st.MESSAGE_TYPE == MESSAGE_TYPE
    assert st.JSON_CAP == JSON_CAP == 4 * 1024
    assert st.DEBOUNCE_SECONDS == DEBOUNCE == 0.1


_BLOCKER_HARNESS = textwrap.dedent(
    """
    import importlib.abc, importlib.util, sys

    BLOCKED = {blocked!r}

    class Block(importlib.abc.MetaPathFinder):
        def find_spec(self, name, path=None, target=None):
            if name.split(".")[0] in BLOCKED:
                raise ImportError("blocked at import time: " + name)
            return None

    sys.meta_path.insert(0, Block())
    spec = importlib.util.spec_from_file_location("_stale_iso", {path!r})
    module = importlib.util.module_from_spec(spec)
    sys.modules["_stale_iso"] = module
    spec.loader.exec_module(module)
    leaked = sorted(k for k in sys.modules if k.split(".")[0] in BLOCKED)
    assert not leaked, leaked
    print("IMPORT-OK")
    """
)


def _import_in_isolation(path: Path) -> subprocess.CompletedProcess:
    code = _BLOCKER_HARNESS.format(blocked=sorted(_THIRD_PARTY), path=str(path))
    return subprocess.run(
        [sys.executable, "-c", code], capture_output=True, text=True, timeout=120, cwd=str(_TESTS_DIR)
    )


def test_stale_imports_in_plain_cpython_with_no_plr_ipython_or_js(st):
    result = _import_in_isolation(_STALE_PATH)
    assert result.returncode == 0 and "IMPORT-OK" in result.stdout, result.stderr


def test_isolation_harness_control_rejects_a_module_that_imports_js_at_import_time(tmp_path):
    bad = tmp_path / "bad_stale.py"
    bad.write_text("import js\n")
    result = _import_in_isolation(bad)
    assert result.returncode != 0 and "blocked at import time: js" in result.stderr
    bad.write_text("from pylabrobot.resources import Plate\n")
    assert _import_in_isolation(bad).returncode != 0
    ok = tmp_path / "ok_stale.py"
    ok.write_text("import json\n")
    assert _import_in_isolation(ok).returncode == 0


def _import_sites(source: str, top: str) -> list[str | None]:
    """The enclosing function name (None at module level) of every import of ``top``."""
    tree = ast.parse(source)
    sites: list[str | None] = []

    def visit(node, enclosing):
        for child in ast.iter_child_nodes(node):
            inner = child.name if isinstance(child, ast.FunctionDef | ast.AsyncFunctionDef) else enclosing
            if isinstance(child, ast.Import):
                sites.extend(inner for a in child.names if a.name.split(".")[0] == top)
            elif isinstance(child, ast.ImportFrom) and child.level == 0 and child.module:
                if child.module.split(".")[0] == top:
                    sites.append(inner)
            visit(child, inner)

    visit(tree, None)
    return sites


def test_import_js_appears_only_inside_make_repl_poster(st):
    source = _STALE_PATH.read_text()
    sites = _import_sites(source, "js")
    assert sites, "make_repl_poster must import js (the kernel-only seam)"
    assert set(sites) == {"make_repl_poster"}, sites


def test_no_plr_or_ipython_import_at_module_level(st):
    source = _STALE_PATH.read_text()
    for top in ("pylabrobot", "IPython"):
        assert None not in _import_sites(source, top), f"module-level import of {top}"
    assert None not in _import_sites(source, "js")


def test_import_lint_controls():
    assert _import_sites("import js\n", "js") == [None]
    assert _import_sites("def f():\n    import js\n", "js") == ["f"]
    assert _import_sites("from pylabrobot.resources import Plate\n", "pylabrobot") == [None]
    assert _import_sites("def f():\n    from pylabrobot.resources import Plate\n", "pylabrobot") == ["f"]
    assert _import_sites("import json\n", "js") == []


def _files_naming_channel(directory: Path) -> list[str]:
    return sorted(p.name for p in directory.glob("*.py") if CHANNEL in p.read_text())


def test_the_channel_name_appears_in_stale_py_only(st):
    assert _files_naming_channel(_DISPLAY_DIR) == ["stale.py"]


def test_channel_scan_control_finds_another_module(tmp_path):
    (tmp_path / "other.py").write_text('CH = "praxis_repl"\n')
    (tmp_path / "quiet.py").write_text("x = 1\n")
    assert _files_naming_channel(tmp_path) == ["other.py"]


# --------------------------------------------------------------------------- the R21 check


def _gate_script(paths: str, *, echo_status=False) -> str:
    script = R21_LINE_1.replace("<paths>", paths) + "\n"
    script += 'echo "${s[@]}"\n' if echo_status else R21_LINE_2 + "\n"
    return script


def _run_gate(paths: str, *, echo_status=False, cwd=_REPO_ROOT):
    """``bash -c`` with no ``-e`` and no ``pipefail``: exactly how the spec runs the gate."""
    return subprocess.run(
        ["bash", "-c", _gate_script(paths, echo_status=echo_status)],
        capture_output=True,
        text=True,
        cwd=str(cwd),
        timeout=120,
    )


def _pipestatus(paths: str, *, cwd=_REPO_ROOT) -> list[int]:
    out = _run_gate(paths, echo_status=True, cwd=cwd).stdout.strip().splitlines()
    return [int(x) for x in out[-1].split()]


def test_r21_paths_exist():
    for rel in R21_PATHS:
        assert (_REPO_ROOT / rel).is_dir(), rel


def test_plain_grep_hits_exactly_the_three_documentation_mentions_in_transport_py():
    plain = subprocess.run(
        ["grep", "-rn", CHANNEL, *R21_PATHS], capture_output=True, text=True, cwd=str(_REPO_ROOT)
    )
    assert plain.returncode == 0, "the plain grep is non-empty on main (Revision 10, BLOCKER-3)"
    hits = sorted(line.split(":")[0:2] for line in plain.stdout.splitlines())
    transport = "web-repl/overlay/assets/python/praxis/viz/transport.py"
    assert hits == [[transport, "10"], [transport, "11"], [transport, "26"]], hits
    assert all(f"``{CHANNEL}``" in line for line in plain.stdout.splitlines())


def test_r21_check_passes_on_the_real_paths_and_is_not_vacuous():
    real = " ".join(R21_PATHS)
    assert _run_gate(real).returncode == 0
    # first grep 0 (the three hits ARE found), sed 0, final grep exactly 1 (nothing left after the strip).
    assert _pipestatus(real) == [0, 0, 1]
    assert _run_gate(real, echo_status=True).stdout.strip() == "0 0 1", "no residual line is printed"


@pytest.mark.parametrize(
    "line",
    [
        'CHANNEL = "praxis_repl"\n',
        "CHANNEL = 'praxis_repl'\n",
        "const c = new BroadcastChannel(`praxis_repl`);\n",
        "praxis_repl = 1\n",
        'see ``praxis_repl`` and post to "praxis_repl"\n',
    ],
)
def test_r21_check_control_fires_on_a_code_use_of_the_channel_name(tmp_path, line):
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "use.py").write_text(line)
    assert _run_gate(str(bad)).returncode != 0
    assert _pipestatus(str(bad))[2] == 0, "the final grep finds the residual code use"


def test_r21_check_control_ignores_the_documentation_form_and_an_empty_tree(tmp_path):
    doc = tmp_path / "doc"
    doc.mkdir()
    (doc / "d.py").write_text('"""rides praxis_viz, NOT ``praxis_repl``."""\n')
    assert _run_gate(str(doc)).returncode == 0
    assert _pipestatus(str(doc)) == [0, 0, 1]
    empty = tmp_path / "empty"
    empty.mkdir()
    (empty / "e.py").write_text("x = 1\n")
    assert _run_gate(str(empty)).returncode == 0  # first grep exits 1 (no hit): allowed
    assert _pipestatus(str(empty)) == [1, 0, 1]


def test_r21_check_control_a_missing_path_fails_where_a_plain_pipeline_would_pass(tmp_path):
    missing = str(tmp_path / "does-not-exist")
    assert _pipestatus(missing)[0] == 2, "an unreadable path makes the first grep exit 2"
    assert _run_gate(missing).returncode != 0
    plain_pipeline = R21_LINE_1.split("; s=")[0].replace("<paths>", missing)  # no PIPESTATUS capture
    naive = subprocess.run(["bash", "-c", plain_pipeline], capture_output=True, text=True, timeout=60)
    assert naive.returncode == 1, "a plain pipeline reads that error as a clean pass (C11-8)"


# --------------------------------------------------------------------------- the digest


@_async_test
async def test_digest_is_a_sha256_hex_string_and_is_deterministic(st, fx):
    w = await _world(fx)
    d1, d2 = st.state_digest(w.source), st.state_digest(w.source)
    assert d1 == d2 and re.fullmatch(r"[0-9a-f]{64}", d1)
    assert st.state_digest(w.assay) != d1, "different resources draw different things"


@_async_test
async def test_digest_follows_exactly_what_an_output_draws(st, fx):
    w = await _world(fx)
    base = st.state_digest(w.source)
    a1 = w.source.get_item("A1")
    assert a1.tracker.get_used_volume() == 150.0

    a1.tracker.set_volume(150.0)  # nothing drawn changed
    assert st.state_digest(w.source) == base

    a1.tracker.set_volume(120.0)  # committed and pending
    committed = st.state_digest(w.source)
    assert committed != base

    a1.tracker.remove_liquid(10.0)  # pending only: committed stays 120, drawn 110
    assert (a1.tracker.volume, a1.tracker.get_used_volume()) == (120.0, 110.0)
    assert st.state_digest(w.source) not in (base, committed)

    a1.tracker.rollback()  # back to committed
    assert st.state_digest(w.source) == committed

    # float noise far below anything the figure can draw does not change the digest
    a1.tracker.set_volume(120.0 + 1e-9)
    assert st.state_digest(w.source) == committed

    # a container outside the subtree does not enter it
    w.assay.get_item("A1").tracker.set_volume(7.0)
    assert st.state_digest(w.source) == committed

    # tip spots enter as `spot.tip is not None` (the tree the figure draws)
    tips = w.tips
    spot = tips.get_item("A5")
    tip_base = st.state_digest(tips)
    assert spot.tip is not None
    tip = spot.tip
    spot.unassign_child_resource(tip)
    assert spot.tip is None
    assert st.state_digest(tips) != tip_base


@_async_test
async def test_digest_includes_structure_child_name_parent_and_location(st, fx):
    w = await _world(fx)
    base = st.state_digest(w.deck)
    carrier = w.deck.get_resource("plate_carrier")
    assert carrier.parent is w.deck
    old = carrier.location
    carrier.location = type(old)(x=old.x + 10.0, y=old.y, z=old.z)
    moved = st.state_digest(w.deck)
    assert moved != base, "a moved child is drawn somewhere else"
    carrier.location = old
    assert st.state_digest(w.deck) == base
    w.deck.unassign_child_resource(carrier)
    assert st.state_digest(w.deck) != base, "a removed child is not drawn"


# --------------------------------------------------------------------------- session basics


def test_session_ids_are_random_per_session_and_injectable(st):
    a = st.DisplaySession(lambda s: None, loop=FakeLoop())
    b = st.DisplaySession(lambda s: None, loop=FakeLoop())
    assert isinstance(a.session_id, str) and a.session_id and a.session_id != b.session_id
    assert re.fullmatch(r"[0-9a-f]{16,}", a.session_id), "a random hex id"
    assert st.new_session_id() != st.new_session_id()
    fixed = st.DisplaySession(lambda s: None, loop=FakeLoop(), session_id="abc")
    assert fixed.session_id == "abc"


@_async_test
async def test_drawing_stamps_a_stable_int_rev_and_records_it(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    r = s.draw(w.source)
    assert isinstance(r, int) and not isinstance(r, bool)
    assert s.rev_of("source") == r
    assert s.draw(w.source) == r == s.draw(w.source), "an unchanged resource keeps its rev"
    assert s.rev_of("assay") is None, "not drawn, so it has no rev"
    assert posts == [], "drawing never announces"


@_async_test
async def test_set_volume_other_than_150_bumps_source_and_the_drawn_deck(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    r_src, r_deck = s.draw(w.source), s.draw(w.deck)
    a1 = w.source.get_item("A1")
    assert a1.tracker.get_used_volume() == 150.0  # the fixture's A1; 120 differs
    a1.tracker.set_volume(120.0)
    s.post_run_cell()
    assert len(posts) == 1
    assert posts.msgs[0]["revs"] == {"source": r_src + 1, "deck": r_deck + 1}
    assert s.draw(w.source) == r_src + 1 and s.draw(w.deck) == r_deck + 1


@_async_test
async def test_set_volume_to_the_value_already_held_bumps_nothing_and_posts_nothing(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    r = s.draw(w.source)
    a1 = w.source.get_item("A1")
    n = _count_state_callbacks(a1)
    a1.tracker.set_volume(150.0)  # a callback fires, the drawn state does not change
    assert n[0] == 1
    s.post_run_cell()
    assert posts == [] and s.draw(w.source) == r


@_async_test
async def test_one_post_run_cell_posts_exactly_one_message_with_only_the_changed_revs(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    revs = {n: s.draw(o) for n, o in (("source", w.source), ("assay", w.assay), ("tips_300", w.tips))}
    for wid in ("A1", "B1", "C1"):
        w.source.get_item(wid).tracker.set_volume(11.0)  # three callbacks on one plate
    s.post_run_cell()
    assert len(posts) == 1
    assert posts.msgs[0]["revs"] == {"source": revs["source"] + 1}
    # the next cell changes another resource only
    w.assay.get_item("A2").tracker.set_volume(3.0)
    s.post_run_cell()
    assert len(posts) == 2 and posts.msgs[1]["revs"] == {"assay": revs["assay"] + 1}
    s.post_run_cell()
    assert len(posts) == 2, "a cell with no change posts nothing"


@_async_test
async def test_install_plus_a_cell_with_no_change_posts_nothing_at_all(st, fx):
    w = await _world(fx)
    s, posts, loop = _session(st)
    s.post_run_cell()  # no drawn resource
    s.draw(w.source)
    s.draw(w.tips)
    s.post_run_cell()
    loop.advance(5.0)
    assert posts == [] and loop.delays == []


@_async_test
async def test_the_announcement_json_fields(st, fx):
    w = await _world(fx)
    execs = _Exec(9)
    s, posts, _ = _session(st, exec_count=execs, session_id="sess-xyz")
    r = s.draw(w.source)
    w.source.get_item("H12").tracker.set_volume(1.0)
    payload = s.post_run_cell()
    assert payload == posts[0] and isinstance(payload, str)
    assert set(json.loads(payload)) == {"session", "exec", "revs"}
    assert json.loads(payload) == {"session": "sess-xyz", "exec": 9, "revs": {"source": r + 1}}
    assert len(payload.encode("utf-8")) <= JSON_CAP


@_async_test
async def test_exec_is_the_cell_that_made_the_change_not_the_one_that_flushed(st, fx):
    w = await _world(fx)
    execs = _Exec(5)
    s, posts, loop = _session(st, exec_count=execs)
    s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)  # in cell 5
    execs.n = 6  # a later cell has started by the time the debounced announcer runs
    loop.advance(DEBOUNCE)
    assert posts.msgs[0]["exec"] == 5


@_async_test
async def test_exec_is_null_without_an_execution_count(st, fx):
    w = await _world(fx)
    posts = _Posts()
    s = st.DisplaySession(posts, loop=FakeLoop(), session_id="s")
    s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)
    s.post_run_cell()
    assert posts.msgs[0]["exec"] is None


# --------------------------------------------------------------------------- the 4 KiB cap


def test_announcement_json_switches_to_all_true_past_the_cap(st):
    def make(n):
        return {f"resource_with_a_long_name_{i:04d}": i for i in range(n)}

    forms = []
    for n in range(0, 400):
        payload = st.announcement_json("sess-0123456789ab", 12, make(n))
        assert len(payload.encode("utf-8")) <= JSON_CAP, n
        obj = json.loads(payload)
        assert obj["session"] == "sess-0123456789ab" and obj["exec"] == 12
        if "revs" in obj:
            assert "all" not in obj and obj["revs"] == make(n), "the map is complete when it is sent"
            forms.append("revs")
        else:
            assert obj.get("all") is True and "revs" not in obj
            forms.append("all")
    assert forms[0] == "revs" and forms[-1] == "all"
    flip = forms.index("all")
    assert set(forms[flip:]) == {"all"} and set(forms[:flip]) == {"revs"}, "one switch, no flapping"
    last_revs = st.announcement_json("sess-0123456789ab", 12, make(flip - 1))
    assert len(last_revs.encode("utf-8")) > JSON_CAP - 80, "the switch is not premature"


@_async_test
async def test_a_cell_that_changes_every_drawn_well_announces_all_true_within_the_cap(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    wells = w.source.get_all_items() + w.assay.get_all_items()
    for well in wells:
        s.draw(well)  # one drawn resource per well: 192 revs
    assert len(wells) == 192
    for well in wells:
        well.tracker.set_volume(well.tracker.get_used_volume() + 1.0)
    s.post_run_cell()
    assert len(posts) == 1 and len(posts[0].encode("utf-8")) <= JSON_CAP
    obj = posts.msgs[0]
    assert obj.get("all") is True and "revs" not in obj
    # a few changed wells stay a map
    for well in wells[:5]:
        well.tracker.set_volume(well.tracker.get_used_volume() + 1.0)
    s.post_run_cell()
    assert set(posts.msgs[1]["revs"]) == {wl.name for wl in wells[:5]}


# --------------------------------------------------------------------------- the real poster


class _FakeJs:
    """A fake ``js`` module: ``BroadcastChannel`` (with or without ``.new``) and ``Object.fromEntries``."""

    def __init__(self, *, has_new=True):
        self.created: list[str] = []
        self.posted: list[object] = []
        self.entries: list[list] = []
        outer = self

        class Channel:
            def __init__(self, name):
                outer.created.append(name)

            def postMessage(self, obj):  # noqa: N802 - the JS name
                outer.posted.append(obj)

        if has_new:

            class BroadcastChannel:
                new = staticmethod(lambda name: Channel(name))

        else:

            class BroadcastChannel:
                def __new__(cls, name):
                    return Channel(name)

        self.BroadcastChannel = BroadcastChannel

        def from_entries(pairs):
            pairs = list(pairs)
            outer.entries.append(pairs)
            return dict(pairs)

        self.Object = types.SimpleNamespace(fromEntries=from_entries)
        self.module = types.ModuleType("js")
        self.module.BroadcastChannel = self.BroadcastChannel
        self.module.Object = self.Object


@pytest.mark.parametrize("has_new", [True, False])
def test_make_repl_poster_posts_type_and_json_flat_on_praxis_repl(st, monkeypatch, has_new):
    fake = _FakeJs(has_new=has_new)
    monkeypatch.setitem(sys.modules, "js", fake.module)
    post = st.make_repl_poster()
    assert fake.created == [CHANNEL], "one channel, the praxis_repl one (both constructor forms)"
    post('{"session":"s"}')
    assert fake.posted == [{"type": MESSAGE_TYPE, "json": '{"session":"s"}'}]
    assert [k for k, _ in fake.entries[0]] == ["type", "json"], "built with js.Object.fromEntries"
    other = st.make_repl_poster("some_other_channel")
    assert fake.created[-1] == "some_other_channel"
    other("x")
    assert fake.posted[-1]["json"] == "x"


@_async_test
async def test_a_change_reaches_the_channel_as_one_typed_message(st, fx, monkeypatch):
    fake = _FakeJs()
    monkeypatch.setitem(sys.modules, "js", fake.module)
    w = await _world(fx)
    s = st.DisplaySession(st.make_repl_poster(), loop=FakeLoop(), exec_count=_Exec(4), session_id="s1")
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(120.0)
    s.post_run_cell()
    assert len(fake.posted) == 1
    message = fake.posted[0]
    assert set(message) == {"type", "json"} and message["type"] == MESSAGE_TYPE
    assert isinstance(message["json"], str)
    assert json.loads(message["json"]) == {"session": "s1", "exec": 4, "revs": {"source": r + 1}}
    s.post_run_cell()
    assert len(fake.posted) == 1


# --------------------------------------------------------------------------- null stamps


@_async_test
async def test_a_null_resource_or_null_rev_stamp_subscribes_nothing_and_never_announces(st, fx):
    w = await _world(fx)
    s, posts, loop = _session(st)
    s.draw(w.source)  # a real drawn output, for the announcement half
    before = set(s._subscribed)
    assert before, "drawing subscribes"
    ledger = {"v": 1, "kind": "ledger", "resource": None, "rev": None, "session": s.session_id, "exec": 3}
    error_named = {"v": 1, "kind": "error", "resource": "assay", "rev": None, "session": s.session_id, "exec": 3}
    error_generic = {"v": 1, "kind": "error", "resource": None, "rev": None, "session": s.session_id, "exec": 3}
    half = {"v": 1, "kind": "plate", "resource": None, "rev": 2, "session": s.session_id, "exec": 3}
    for stamp, res in ((ledger, None), (error_named, w.assay), (error_generic, None), (half, w.assay)):
        assert s.note_output(stamp, res) is None
    assert set(s._subscribed) == before, "_subscribed unchanged"
    assert s.rev_of("assay") is None
    w.assay.get_item("A1").tracker.set_volume(9.0)  # would bump assay had it been drawn
    w.source.get_item("A1").tracker.set_volume(9.0)
    s.post_run_cell()
    assert len(posts) == 1 and set(posts.msgs[0]["revs"]) == {"source"}, "nothing of the null stamps"


@_async_test
async def test_a_real_stamp_does_subscribe_control(st, fx):
    w = await _world(fx)
    s, _, _ = _session(st)
    stamp = {"v": 1, "kind": "plate", "resource": "assay", "rev": 0, "session": s.session_id, "exec": 3}
    assert not s._subscribed
    rev = s.note_output(stamp, w.assay)
    assert isinstance(rev, int) and s._subscribed and s.rev_of("assay") == rev


# --------------------------------------------------------------------------- pending, rollback, pick-up


@_async_test
async def test_a_pending_only_change_bumps_the_drawn_resource(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    r = s.draw(w.assay)
    a1 = w.assay.get_item("A1")
    assert (a1.tracker.volume, a1.tracker.pending_volume) == (50.0, 50.0)
    a1.tracker.remove_liquid(10.0)  # queued, not committed
    assert (a1.tracker.volume, a1.tracker.pending_volume) == (50.0, 40.0)
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"assay": r + 1}
    assert s.draw(w.assay) == r + 1


@_async_test
async def test_a_failed_aspirate_rollback_bumps_nothing_and_posts_nothing(st, fx):
    """AC-18 'Rollback does not bump' (the AC-15 E9 setup: 30 uL on 8 channels, trough holds 100)."""
    from pylabrobot.resources.errors import TooLittleLiquidError

    w = await _world(fx)
    await w.lh.pick_up_tips(w.tips["A4:H4"])
    s, posts, loop = _session(st)
    revs = {n: s.draw(o) for n, o in (("trough", w.trough), ("source", w.source), ("assay", w.assay), ("deck", w.deck), ("tips_300", w.tips))}
    fired = _count_state_callbacks(w.trough)  # the recording callback: proves the callbacks DID fire
    with pytest.raises(TooLittleLiquidError):
        await w.lh.aspirate([w.trough] * 8, vols=[30.0] * 8)
    assert fired[0] > 1, "PLR 1.0 rollback fires tracker callbacks; without them the case is vacuous"
    assert (w.trough.tracker.volume, w.trough.tracker.pending_volume) == (100.0, 100.0)
    assert {n: s.rev_of(n) for n in revs} == revs
    s.post_run_cell()
    loop.advance(DEBOUNCE)
    assert posts == []
    assert {n: s.draw(o) for n, o in (("trough", w.trough), ("source", w.source), ("assay", w.assay), ("deck", w.deck), ("tips_300", w.tips))} == revs


@_async_test
async def test_settling_is_lazy_so_the_intermediate_rollback_states_are_never_digested(st, fx, monkeypatch):
    from pylabrobot.resources.errors import TooLittleLiquidError

    w = await _world(fx)
    await w.lh.pick_up_tips(w.tips["A4:H4"])
    s, posts, _ = _session(st)
    s.draw(w.trough)
    calls = []
    real = st.state_digest
    monkeypatch.setattr(st, "state_digest", lambda res: calls.append(res.name) or real(res))
    with pytest.raises(TooLittleLiquidError):
        await w.lh.aspirate([w.trough] * 8, vols=[30.0] * 8)  # pending walks 70, 40, 10 then back to 100
    assert calls == [], "no digest is computed while callbacks fire"
    s.post_run_cell()
    assert calls == ["trough"], "one settle, after the op, of the one dirty drawn resource"
    assert posts == []


@_async_test
async def test_a_succeeding_aspirate_bumps_control(st, fx):
    w = await _world(fx)
    await w.lh.pick_up_tips(w.tips["A4:H4"])
    s, posts, _ = _session(st)
    r = s.draw(w.trough)
    await w.lh.aspirate([w.trough], vols=[30.0], use_channels=[0])
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"trough": r + 1}
    assert w.trough.tracker.get_used_volume() == 70.0


@_async_test
async def test_a_rollback_that_clears_pending_residue_does_bump_correctly(st, fx):
    """D7: residue on an op resource is reset to committed by the rollback, which changes what is drawn."""
    from pylabrobot.resources.errors import TooLittleLiquidError

    w = await _world(fx)
    await w.lh.pick_up_tips(w.tips["A4:H4"])
    s, posts, _ = _session(st)
    r = s.draw(w.trough)
    w.trough.tracker.remove_liquid(10.0)  # E13 step 3: committed 100, pending 90
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"trough": r + 1}
    with pytest.raises(TooLittleLiquidError):
        await w.lh.aspirate([w.trough], vols=[95.0], use_channels=[0])  # 95 > pending 90; rolls back
    assert (w.trough.tracker.volume, w.trough.tracker.pending_volume) == (100.0, 100.0)
    s.post_run_cell()
    assert len(posts) == 2 and posts.msgs[1]["revs"] == {"trough": r + 2}


@_async_test
async def test_a_tip_pick_up_gives_exactly_one_bump_per_settle(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    r_rack, r_deck, r_src = s.draw(w.tips), s.draw(w.deck), s.draw(w.source)
    unassigned = [0]
    w.tips.register_did_unassign_resource_callback(lambda _c: unassigned.__setitem__(0, unassigned[0] + 1))
    fired = _count_state_callbacks(*[sp for sp in w.tips.get_all_items()])
    spots = w.tips["A4:H4"]
    assert all(sp.tip is not None for sp in spots)
    await w.lh.pick_up_tips(spots)
    assert unassigned[0] == 8, "PLR fires did_unassign eight times for one pick-up (tips are tree children)"
    assert fired[0] >= 8
    assert all(sp.tip is None for sp in spots)
    s.post_run_cell()
    assert len(posts) == 1
    assert posts.msgs[0]["revs"] == {"tips_300": r_rack + 1, "deck": r_deck + 1}, "one bump each, not eight"
    assert s.rev_of("source") == r_src
    s.post_run_cell()
    assert len(posts) == 1 and s.draw(w.tips) == r_rack + 1
    await w.lh.discard_tips()
    await w.lh.pick_up_tips(w.tips["A5:H5"])
    s.post_run_cell()
    assert posts.msgs[1]["revs"]["tips_300"] == r_rack + 2, "a second pick-up bumps once more"


# --------------------------------------------------------------------------- settle before render, stamps


@_async_test
async def test_settle_before_render_the_stamp_and_the_announcement_carry_the_same_rev(st, fx, lw):
    w = await _world(fx)
    s, posts, _ = _session(st, exec_count=_Exec(7))
    r = s.draw(w.assay)
    w.assay.get_item("A1").tracker.set_volume(123.0)  # the cell sets a well ...
    assert s.rev_of("assay") == r, "settling is lazy: nothing settled yet"
    data, meta = lw.render(w.assay, **s.render_kwargs(w.assay))  # ... then renders its plate
    stamp = meta["praxis"]
    assert stamp["rev"] == r + 1, "the render settled first, so the stamp matches what it draws"
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"assay": stamp["rev"]}, "the fresh output is not older than the announcement"
    assert set(data) >= {"text/html", "text/plain"}


@_async_test
async def test_stamp_fields_come_from_the_session_and_the_rev(st, fx, lw):
    w = await _world(fx)
    s, _, _ = _session(st, exec_count=_Exec(11), session_id="sess-stamp")
    well = w.assay.get_item("A1")
    for res, kind in ((w.assay, "plate"), (w.tips, "tiprack"), (well, "container"), (w.trough, "container")):
        _data, meta = lw.render(res, **s.render_kwargs(res))
        stamp = meta["praxis"]
        assert stamp == {
            "v": 1,
            "kind": kind,
            "resource": res.name,
            "rev": s.rev_of(res.name),
            "session": "sess-stamp",
            "exec": 11,
        }
        assert isinstance(stamp["rev"], int)
    assert set(s.render_kwargs(w.assay)) == {"rev", "session", "exec_count"}


@_async_test
async def test_a_different_object_drawn_under_a_drawn_name_never_lowers_the_rev(st, fx):
    w = await _world(fx)
    s, _, _ = _session(st)
    r1 = s.draw(w.assay)
    other = await _world(fx)  # a second, equal deck: same names
    assert s.draw(other.assay) == r1, "equal drawn state, same rev"
    other.assay.get_item("A1").tracker.set_volume(1.0)
    assert s.draw(other.assay) == r1 + 1
    assert s.draw(other.assay) == r1 + 1


# --------------------------------------------------------------------------- subscription


@_async_test
async def test_subscription_is_idempotent_through_the_subscribed_set(st, fx, monkeypatch):
    from pylabrobot.resources import Resource

    w = await _world(fx)
    state_regs: dict[int, int] = {}
    assign_regs: dict[int, int] = {}
    orig_state = Resource.register_state_update_callback
    orig_assign = Resource.register_did_assign_resource_callback
    orig_unassign = Resource.register_did_unassign_resource_callback
    unassign_regs: dict[int, int] = {}

    def spy_state(self, cb):
        state_regs[id(self)] = state_regs.get(id(self), 0) + 1
        return orig_state(self, cb)

    def spy_assign(self, cb):
        assign_regs[id(self)] = assign_regs.get(id(self), 0) + 1
        return orig_assign(self, cb)

    def spy_unassign(self, cb):
        unassign_regs[id(self)] = unassign_regs.get(id(self), 0) + 1
        return orig_unassign(self, cb)

    monkeypatch.setattr(Resource, "register_state_update_callback", spy_state)
    monkeypatch.setattr(Resource, "register_did_assign_resource_callback", spy_assign)
    monkeypatch.setattr(Resource, "register_did_unassign_resource_callback", spy_unassign)

    s, _, _ = _session(st)
    nodes = _all_nodes(w.assay)
    for _ in range(3):
        s.draw(w.assay)
    assert all(state_regs.get(id(n)) == 1 for n in nodes), "one state callback per node, not three"
    assert assign_regs.get(id(w.assay)) == 1 and unassign_regs.get(id(w.assay)) == 1
    size = len(s._subscribed)
    assert size >= len(nodes)
    # a nested drawn resource (the deck holds the plate) registers only what is new
    s.draw(w.deck)
    s.draw(w.assay)
    s.draw(w.deck)
    assert all(state_regs.get(id(n)) == 1 for n in _all_nodes(w.deck)), "no node registered twice"
    assert assign_regs.get(id(w.deck)) == 1 and assign_regs.get(id(w.assay)) == 1
    # a callback fires once per change, so a dirty mark is not doubled
    n = _count_state_callbacks(w.assay.get_item("A1"))
    w.assay.get_item("A1").tracker.set_volume(1.0)
    assert n[0] == 1


@_async_test
async def test_a_child_assigned_after_the_draw_is_seen_and_then_subscribed(st, fx):
    from pylabrobot.resources.corning import cor_96_wellplate_360uL_Fb
    from pylabrobot.resources.hamilton import hamilton_plate_carrier_L5_ac

    w = await _world(fx)
    s, posts, _ = _session(st)
    r = s.draw(w.deck)
    carrier = hamilton_plate_carrier_L5_ac(name="carrier_late")
    carrier[0] = late = cor_96_wellplate_360uL_Fb(name="late_plate")
    w.deck.assign_child_resource(carrier, track=25)  # structure change, after the draw
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"deck": r + 1}
    late.get_item("A1").tracker.set_volume(33.0)  # a well of a resource that did not exist at draw time
    s.post_run_cell()
    assert len(posts) == 2 and posts.msgs[1]["revs"] == {"deck": r + 2}
    w.deck.unassign_child_resource(carrier)
    s.post_run_cell()
    assert posts.msgs[2]["revs"] == {"deck": r + 3}


# --------------------------------------------------------------------------- debounce and the announcer


@_async_test
async def test_callbacks_coalesce_into_one_debounced_announcement(st, fx):
    w = await _world(fx)
    s, posts, loop = _session(st)
    r = s.draw(w.source)
    for wid in ("A1", "B1", "C1", "D1", "E1", "F1"):
        w.source.get_item(wid).tracker.set_volume(5.0)
    assert loop.delays and set(loop.delays) == {DEBOUNCE}, "every timer is call_later(0.1, ...)"
    assert len(loop.live()) == 1, "six callbacks, one live timer"
    loop.advance(DEBOUNCE * 0.9)
    assert posts == [], "nothing before the debounce elapses"
    loop.advance(DEBOUNCE * 0.2)
    assert len(posts) == 1 and posts.msgs[0]["revs"] == {"source": r + 1}
    loop.advance(10.0)
    assert len(posts) == 1, "a settled announcement does not repeat"
    w.source.get_item("A2").tracker.set_volume(5.0)  # a separate burst is a separate message
    loop.advance(DEBOUNCE)
    assert len(posts) == 2 and posts.msgs[1]["revs"] == {"source": r + 2}


@_async_test
async def test_the_debounced_announcer_settles_first_then_builds_its_message(st, fx):
    """S3-D: no post_run_cell for top-level-await cells; the timer alone must settle and announce."""
    w = await _world(fx)
    s, posts, loop = _session(st, exec_count=_Exec(3))
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(120.0)
    assert s.rev_of("source") == r, "still unsettled before the timer"
    loop.advance(DEBOUNCE)
    assert loop.fired == 1
    assert posts.msgs[0]["revs"] == {"source": r + 1}, "the message carries the rev the settle produced"
    assert s.rev_of("source") == r + 1


@_async_test
async def test_the_debounced_announcer_posts_nothing_when_the_digest_did_not_change(st, fx):
    from pylabrobot.resources.errors import TooLittleLiquidError

    w = await _world(fx)
    await w.lh.pick_up_tips(w.tips["A4:H4"])
    s, posts, loop = _session(st)
    s.draw(w.trough)
    with pytest.raises(TooLittleLiquidError):
        await w.lh.aspirate([w.trough] * 8, vols=[30.0] * 8)
    assert loop.live(), "the callbacks scheduled the announcer"
    loop.advance(DEBOUNCE)
    assert loop.fired == 1, "the announcer ran (so the empty result is not vacuous)"
    assert posts == []


@_async_test
async def test_post_run_cell_and_the_timer_never_announce_the_same_change_twice(st, fx):
    w = await _world(fx)
    s, posts, loop = _session(st)
    s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)
    loop.advance(DEBOUNCE)
    s.post_run_cell()
    loop.advance(DEBOUNCE)
    assert len(posts) == 1, "timer first, then post_run_cell"
    w.source.get_item("A1").tracker.set_volume(2.0)
    s.post_run_cell()
    assert not loop.live(), "post_run_cell cancels the pending timer"
    loop.advance(10.0)
    assert len(posts) == 2, "post_run_cell first, then the (cancelled) timer"


@_async_test
async def test_post_run_cell_accepts_the_ipython_result_argument(st, fx):
    w = await _world(fx)
    s, posts, _ = _session(st)
    s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)
    s.post_run_cell(object())
    assert len(posts) == 1


@_async_test
async def test_a_real_asyncio_loop_is_used_when_none_is_injected(st, fx):
    w = await _world(fx)
    posts = _Posts()
    s = st.DisplaySession(posts, session_id="real-loop", exec_count=_Exec(2))  # loop=None: the running loop
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)
    assert posts == []
    await asyncio.sleep(0.4)
    assert len(posts) == 1 and posts.msgs[0]["revs"] == {"source": r + 1}


def test_without_any_loop_callbacks_only_mark_dirty_and_post_run_cell_announces(st, fx):
    w = asyncio.run(_world(fx))  # the loop is closed again: no running loop below
    s, posts, _ = _session(st, loop=None)
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)  # must not raise: there is nothing to schedule
    assert posts == []
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"source": r + 1}


# --------------------------------------------------------------------------- failures never break PLR


@_async_test
async def test_a_loop_that_cannot_schedule_never_breaks_a_liquid_handling_call(st, fx):
    class ClosedLoop:
        def call_later(self, *_a, **_k):
            raise RuntimeError("Event loop is closed")

    w = await _world(fx)
    s, posts, _ = _session(st, loop=ClosedLoop())
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)  # PLR calls our callback inside the tracker: no raise
    await w.lh.pick_up_tips(w.tips["A6:H6"])
    s.post_run_cell()
    assert posts.msgs[0]["revs"] == {"source": r + 1}


@_async_test
async def test_a_failing_poster_is_logged_not_raised_and_retried_on_the_next_flush(st, fx, caplog):
    w = await _world(fx)
    delivered = []
    attempts = []

    def flaky(payload):
        attempts.append(payload)
        if len(attempts) == 1:
            raise OSError("channel closed")
        delivered.append(payload)

    s = st.DisplaySession(flaky, loop=FakeLoop(), session_id="s", exec_count=_Exec(1))
    r = s.draw(w.source)
    w.source.get_item("A1").tracker.set_volume(1.0)
    with caplog.at_level("WARNING"):
        s.post_run_cell()  # must not raise into IPython
    assert len(attempts) == 1 and delivered == []
    assert any("channel closed" in rec.getMessage() or "announce" in rec.getMessage().lower() for rec in caplog.records)
    s.post_run_cell()
    assert len(delivered) == 1 and json.loads(delivered[0])["revs"] == {"source": r + 1}
    s.post_run_cell()
    assert len(delivered) == 1
