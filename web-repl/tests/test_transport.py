"""CPython tests for ``web-repl/bootstrap/transport.py`` -- P3.7's D2 fetch
loop and D1 handshake half.

Pure CPython, no browser/Pyodide dependency: every function under test takes
its browser object (an XHR-like factory, a BroadcastChannel-like
register/post pair) as an injected callable, per ADR
``.praxia/docs/decisions/260817_repl-layout-and-delivery-mechanism.md``
Sec 2.1 ("``transport.py``: ... no ``import js``"). ``transport.py`` never
imports ``js`` itself, so none of these tests need to fake that module --
contrast ``test_praxis_bootstrap_loader.py``, which does, because
``praxis_bootstrap.py`` is the file that owns the real browser objects.

Proves, per this task's brief:
  - the fetch loop is driven by whatever ``manifest.json`` lists, not a
    hardcoded literal list (``test_fetch_sources_is_manifest_driven_not_hardcoded``)
  - a sha256 mismatch raises ``PraxisDriftError``, OBSERVED failing
    (``test_fetch_sources_sha_mismatch_raises_drift_closed``)
  - a missing manifest raises ``PraxisUnavailableError``, OBSERVED failing
    (``test_fetch_manifest_404_raises_unavailable``)

Per ADR Sec 2.4, this file must NOT append ``web-repl/overlay/assets/python``
to ``sys.path`` (it shadows the real top-level ``praxis`` package) -- and it
does not: it only imports ``web-repl/bootstrap/transport.py`` (and,
transitively, ``stages.py``), both outside that subtree.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from pathlib import Path

import pytest

_BOOTSTRAP_DIR = Path(__file__).resolve().parents[1] / "bootstrap"
if str(_BOOTSTRAP_DIR) not in sys.path:
    sys.path.insert(0, str(_BOOTSTRAP_DIR))

import stages  # noqa: E402 -- path setup must precede this import
import transport  # noqa: E402


class FakeXHR:
    """Stand-in for ``js.XMLHttpRequest`` -- an object with ``.open``,
    ``.send``, ``.status``, ``.responseText``, driven by a URL->(status,
    text) routing table shared across every fake XHR instance a given
    ``xhr_new`` factory produces (mirrors real ``XMLHttpRequest``: a fresh
    instance per call, one shared server behind them all).
    """

    def __init__(self, routes: dict[str, tuple[int, str]]):
        self._routes = routes
        self._url = None
        self.status = 0
        self.responseText = ""

    def open(self, method, url, async_):
        assert method == "GET"
        assert async_ is False, "the bootstrap must always fetch synchronously"
        self._url = url

    def send(self, body):
        assert body is None
        status, text = self._routes.get(self._url, (404, ""))
        self.status = status
        self.responseText = text


def make_xhr_new(routes: dict[str, tuple[int, str]]):
    def _xhr_new():
        return FakeXHR(routes)

    return _xhr_new


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


HOST_ROOT = "https://example.invalid/repl/"


# ---------------------------------------------------------------------------
# fetch_manifest
# ---------------------------------------------------------------------------


def test_fetch_manifest_404_raises_unavailable() -> None:
    """REQUIRED: a missing manifest raises PraxisUnavailableError. OBSERVED
    failing, not merely asserted -- routes has no entry for manifest.json at
    all, so FakeXHR's default (404, "") fires and this must raise.
    """
    xhr_new = make_xhr_new({})  # no route registered -> 404
    with pytest.raises(stages.PraxisUnavailableError) as exc_info:
        transport.fetch_manifest(HOST_ROOT, xhr_new)
    assert "HTTP 404" in str(exc_info.value)


def test_fetch_manifest_bad_json_raises_unavailable() -> None:
    url = HOST_ROOT + transport.MANIFEST_REL_PATH
    xhr_new = make_xhr_new({url: (200, "{not valid json")})
    with pytest.raises(stages.PraxisUnavailableError, match="not valid JSON"):
        transport.fetch_manifest(HOST_ROOT, xhr_new)


def test_fetch_manifest_missing_required_key_raises_unavailable() -> None:
    url = HOST_ROOT + transport.MANIFEST_REL_PATH
    xhr_new = make_xhr_new({url: (200, json.dumps({"wheels": [], "sources": []}))})
    with pytest.raises(stages.PraxisUnavailableError, match="praxis_git_sha"):
        transport.fetch_manifest(HOST_ROOT, xhr_new)


def test_fetch_manifest_success_returns_parsed_dict() -> None:
    url = HOST_ROOT + transport.MANIFEST_REL_PATH
    manifest = {"praxis_git_sha": "dev", "wheels": [], "sources": []}
    xhr_new = make_xhr_new({url: (200, json.dumps(manifest))})
    assert transport.fetch_manifest(HOST_ROOT, xhr_new) == manifest


# ---------------------------------------------------------------------------
# fetch_sources -- the manifest-driven loop
# ---------------------------------------------------------------------------


def test_fetch_sources_is_manifest_driven_not_hardcoded(tmp_path) -> None:
    """REQUIRED: the fetch loop reads whatever manifest.json lists.

    Deliberately uses paths that match NONE of the old file's seven
    hardcoded literals (four shims, web_bridge.py, praxis/__init__.py,
    praxis/interactive.py) -- a wholly invented module name and a nested
    "experimental" path -- and proves both get fetched, verified, and
    written correctly anyway, because the loop iterates manifest["sources"],
    never a literal list.
    """
    content_a = "class TotallyInventedShim:\n    pass\n"
    content_b = "MARKER = 'experimental'\n"
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [],
        "sources": [
            {"path": "assets/shims/totally_invented_shim.py", "sha256": _sha(content_a)},
            {"path": "assets/python/experimental/nested_thing.py", "sha256": _sha(content_b)},
        ],
    }
    routes = {
        HOST_ROOT + "assets/shims/totally_invented_shim.py": (200, content_a),
        HOST_ROOT + "assets/python/experimental/nested_thing.py": (200, content_b),
    }
    xhr_new = make_xhr_new(routes)

    written = transport.fetch_sources(manifest, HOST_ROOT, xhr_new, dest_root=str(tmp_path))

    assert sorted(written) == sorted(
        [
            str(tmp_path / "totally_invented_shim.py"),
            str(tmp_path / "experimental" / "nested_thing.py"),
        ]
    )
    assert (tmp_path / "totally_invented_shim.py").read_text() == content_a
    assert (tmp_path / "experimental" / "nested_thing.py").read_text() == content_b


def test_fetch_sources_404_raises_unavailable(tmp_path) -> None:
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [],
        "sources": [{"path": "assets/shims/missing.py", "sha256": "0" * 64}],
    }
    xhr_new = make_xhr_new({})  # 404 on everything
    with pytest.raises(stages.PraxisUnavailableError, match="HTTP 404"):
        transport.fetch_sources(manifest, HOST_ROOT, xhr_new, dest_root=str(tmp_path))


def test_fetch_sources_sha_mismatch_raises_drift_closed(tmp_path) -> None:
    """REQUIRED: a sha256 mismatch raises PraxisDriftError. OBSERVED
    failing -- the server returns content that does NOT match the manifest's
    declared sha256 (simulating a stale CDN cache or partial deploy), and
    this must raise rather than silently write the wrong content.
    """
    served_content = "print('this is not what the manifest expects')\n"
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [],
        "sources": [
            {
                "path": "assets/shims/web_serial_shim.py",
                "sha256": _sha("print('the real, expected content')\n"),
            }
        ],
    }
    url = HOST_ROOT + "assets/shims/web_serial_shim.py"
    xhr_new = make_xhr_new({url: (200, served_content)})

    with pytest.raises(stages.PraxisDriftError) as exc_info:
        transport.fetch_sources(manifest, HOST_ROOT, xhr_new, dest_root=str(tmp_path))
    message = str(exc_info.value)
    assert "web_serial_shim.py" in message
    # Nothing should have been written for the mismatched file -- fail
    # closed means fail BEFORE the write, not write-then-complain.
    assert not (tmp_path / "web_serial_shim.py").exists()


def test_fetch_sources_verifies_before_writing_later_entries(tmp_path) -> None:
    """A drift on entry N must stop the loop before entry N+1 is written --
    otherwise a partially-verified VFS could still get imported.
    """
    good_content = "GOOD = True\n"
    bad_content = "this does not match its manifest sha256\n"
    manifest = {
        "praxis_git_sha": "dev",
        "wheels": [],
        "sources": [
            {"path": "assets/shims/web_serial_shim.py", "sha256": _sha(bad_content)},
            {"path": "assets/shims/web_usb_shim.py", "sha256": _sha(good_content)},
        ],
    }
    routes = {
        HOST_ROOT
        + "assets/shims/web_serial_shim.py": (200, "wrong content served"),
        HOST_ROOT + "assets/shims/web_usb_shim.py": (200, good_content),
    }
    xhr_new = make_xhr_new(routes)
    with pytest.raises(stages.PraxisDriftError):
        transport.fetch_sources(manifest, HOST_ROOT, xhr_new, dest_root=str(tmp_path))
    assert not (tmp_path / "web_usb_shim.py").exists()


# ---------------------------------------------------------------------------
# dest_for_source
# ---------------------------------------------------------------------------


def test_dest_for_source_flattens_shims_to_vfs_root() -> None:
    assert transport.dest_for_source("assets/shims/web_serial_shim.py") == "web_serial_shim.py"


def test_dest_for_source_strips_python_prefix_preserving_structure() -> None:
    assert (
        transport.dest_for_source("assets/python/praxis/interactive.py")
        == "praxis/interactive.py"
    )
    assert (
        transport.dest_for_source("assets/python/experimental/machines.py")
        == "experimental/machines.py"
    )


def test_dest_for_source_unexpected_prefix_raises() -> None:
    with pytest.raises(stages.PraxisUnavailableError):
        transport.dest_for_source("assets/wheels/manifest.json")


def test_dest_for_source_no_real_manifest_source_lands_at_vfs_root() -> None:
    """F-VFS regression guard: run every source path in the REAL, on-disk
    manifest.json through dest_for_source() and assert none of them resolve
    to the VFS root (dest_root itself) as a bare __init__.py -- that would
    silently turn the bootstrap's own working directory into a Python
    package. Reads the actual generated manifest rather than a synthetic one
    so this fails the moment build_manifest.py's collect_sources() ever
    regresses and reintroduces assets/shims/__init__.py as a source.
    """
    manifest_path = (
        Path(__file__).resolve().parents[1]
        / "overlay"
        / "assets"
        / "wheels"
        / "manifest.json"
    )
    manifest = json.loads(manifest_path.read_text())
    assert manifest["sources"], "manifest has no sources -- nothing to check"
    for entry in manifest["sources"]:
        dest = transport.dest_for_source(entry["path"])
        assert dest != "__init__.py", (
            f"{entry['path']!r} resolves to a bare __init__.py at the VFS "
            "root -- this is exactly the F-VFS defect."
        )


def test_dest_for_source_flattening_shims_init_py_is_caught() -> None:
    """Break it on purpose: feed the exact offending path
    (assets/shims/__init__.py) that used to reach the manifest before
    build_manifest.py's collect_sources() excluded it, and prove
    dest_for_source() now fails closed instead of silently returning
    '__init__.py' (which os.path.join('.', '__init__.py') would plant at the
    VFS root).
    """
    with pytest.raises(stages.PraxisUnavailableError, match="VFS root"):
        transport.dest_for_source("assets/shims/__init__.py")


# ---------------------------------------------------------------------------
# shell_ping -- D1 handshake, bootstrap side
# ---------------------------------------------------------------------------


class FakeChannel:
    """Bare stand-in for the injected BroadcastChannel handle -- records
    posted messages and, when armed, synchronously invokes whatever handler
    was registered with a canned pong (mirrors a same-process
    BroadcastChannel loopback closely enough for this handshake's logic).
    """

    def __init__(self, pong_sha: str | None):
        self.pong_sha = pong_sha
        self.posted: list[dict] = []
        self._handler = None

    def register(self, cb) -> None:
        self._handler = cb

    def post(self, msg: dict) -> None:
        self.posted.append(msg)
        if msg.get("type") == "praxis:shell-ping" and self.pong_sha is not None and self._handler:
            self._handler({"type": "praxis:shell-pong", "praxis_git_sha": self.pong_sha})


def test_shell_ping_returns_pong_value() -> None:
    channel = FakeChannel(pong_sha="c3a95c1eeb9701a1085f85940d68690b32b0079a")
    result = asyncio.run(transport.shell_ping(channel.register, channel.post))
    assert result == "c3a95c1eeb9701a1085f85940d68690b32b0079a"
    assert channel.posted == [{"type": "praxis:shell-ping"}]


def test_shell_ping_no_pong_times_out_raises_unavailable() -> None:
    """OBSERVED failing: no shell answers (pong_sha=None), so the future
    never resolves and the short timeout must fire as PraxisUnavailableError
    -- not hang, not silently return None.
    """
    channel = FakeChannel(pong_sha=None)
    with pytest.raises(stages.PraxisUnavailableError, match="shell-ping timed out"):
        asyncio.run(transport.shell_ping(channel.register, channel.post, timeout_s=0.05))


class MultiShellChannel:
    """Every same-origin tab's shell answers a ping on the shared
    ``praxis_repl`` BroadcastChannel, so one ping can draw several pongs --
    e.g. a still-open tab from an older deploy AND this tab's own shell.
    Replays *pong_shas* in order, each as its own pong (debt #1858).
    """

    def __init__(self, pong_shas: list[str]):
        self.pong_shas = pong_shas
        self._handler = None

    def register(self, cb) -> None:
        self._handler = cb

    def post(self, msg: dict) -> None:
        if msg.get("type") == "praxis:shell-ping" and self._handler:
            for sha in self.pong_shas:
                self._handler({"type": "praxis:shell-pong", "praxis_git_sha": sha})


STALE_SHA = "0000000000000000000000000000000000000001"
CURRENT_SHA = "c3a95c1eeb9701a1085f85940d68690b32b0079a"


def test_shell_ping_skips_stale_tab_pong_when_expected_sha_given() -> None:
    """Debt #1858: a stale tab's pong arriving FIRST must not win. With the
    manifest's sha supplied, the matching pong is the answer."""
    channel = MultiShellChannel([STALE_SHA, CURRENT_SHA])
    result = asyncio.run(
        transport.shell_ping(channel.register, channel.post, expected_sha=CURRENT_SHA)
    )
    assert result == CURRENT_SHA


def test_shell_ping_matching_pong_returns_without_waiting_for_timeout() -> None:
    channel = MultiShellChannel([CURRENT_SHA])
    start = time.monotonic()
    result = asyncio.run(
        transport.shell_ping(
            channel.register, channel.post, timeout_s=5.0, expected_sha=CURRENT_SHA
        )
    )
    assert result == CURRENT_SHA
    assert time.monotonic() - start < 1.0


def test_shell_ping_only_stale_pongs_returns_first_seen_so_d1_still_fails_closed() -> None:
    """No matching shell answered but some shell did: return what was seen
    (not a timeout error), so the caller's assert_praxis_git_sha raises the
    real sha-mismatch diagnosis exactly as before this fix."""
    channel = MultiShellChannel([STALE_SHA, "0000000000000000000000000000000000000002"])
    result = asyncio.run(
        transport.shell_ping(
            channel.register, channel.post, timeout_s=0.05, expected_sha=CURRENT_SHA
        )
    )
    assert result == STALE_SHA
    with pytest.raises(stages.PraxisDriftError, match=STALE_SHA):
        stages.assert_praxis_git_sha(CURRENT_SHA, result)


def test_shell_ping_expected_sha_no_pong_still_times_out() -> None:
    channel = MultiShellChannel([])
    with pytest.raises(stages.PraxisUnavailableError, match="shell-ping timed out"):
        asyncio.run(
            transport.shell_ping(
                channel.register, channel.post, timeout_s=0.05, expected_sha=CURRENT_SHA
            )
        )
