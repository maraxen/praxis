"""Pyodide has no threads: PLR's reader "threads" must run as tasks on the kernel's loop.

What it guards (2026-10-07): with the device picker fixed, ``await lh.setup()`` on a
Hamilton STAR got as far as ``HamiltonLiquidHandler.setup()`` and died with
``RuntimeError: can't start new thread``. PLR reads firmware replies on a
``threading.Thread`` that runs ``_continuously_read()`` on a private event loop, and
a Pyodide kernel (a Web Worker) cannot start threads. In the browser that thread
could not work even if it started: the WebUSB shim's ``read()`` awaits JavaScript
promises that only the kernel's own loop can drive.

``stages.install_loop_threads()`` replaces ``threading.Thread`` (in Pyodide only)
with ``stages.LoopTaskThread``, which runs exactly that reader pattern as an asyncio
task on the running loop and leaves every other thread target to the original
``Thread.start()`` (which fails as before in Pyodide). These tests emulate Pyodide
in CPython by making the real ``Thread.start`` raise the same error.

Three layers:
  * the shim on synthetic owners (task scheduling, is_alive/join, crash visibility,
    fallback for every other target);
  * the real PLR ``HamiltonLiquidHandler`` reading path with a fake transport -- fails
    with the user's exact error without the shim, round-trips a command with it;
  * a contract scan of the pinned PLR source: every ``threading.Thread(target=...)``
    site is either the supported reader shape or listed as known-unsupported, so a
    new thread site cannot reach users unnoticed.
"""

from __future__ import annotations

import ast
import asyncio
import sys
import threading
from pathlib import Path

import pytest

_BOOTSTRAP_DIR = Path(__file__).resolve().parents[1] / "bootstrap"
if str(_BOOTSTRAP_DIR) not in sys.path:
  sys.path.insert(0, str(_BOOTSTRAP_DIR))

import stages  # noqa: E402

REPO_ROOT = Path(__file__).resolve().parents[2]
PLR_SRC = REPO_ROOT / "external" / "pylabrobot" / "pylabrobot"
PYODIDE_ERROR = "can't start new thread"


@pytest.fixture
def no_threads(monkeypatch):
  """Emulate Pyodide: the real Thread.start raises exactly what the kernel raised."""

  def _refuse(self):
    raise RuntimeError(PYODIDE_ERROR)

  monkeypatch.setattr(stages._REAL_THREAD, "start", _refuse)


@pytest.fixture
def pyodide_threading(monkeypatch, no_threads):
  """Install the shim as the browser boot does; monkeypatch restores threading.Thread."""
  monkeypatch.setattr(threading, "Thread", stages._REAL_THREAD)
  assert stages.install_loop_threads(platform="emscripten") is True


class _Reader:
  """The PLR reader shape: ``_reading_thread_main`` runs ``_continuously_read`` on a
  fresh loop; ``_continuously_read`` resolves waiting futures with
  ``call_soon_threadsafe``."""

  def __init__(self):
    self.stop = threading.Event()
    self.waiting: list[asyncio.Future] = []
    self.main_called = False
    self.loops_seen: list[asyncio.AbstractEventLoop] = []

  def _reading_thread_main(self):
    self.main_called = True  # the shim must never call this (it would block the kernel)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    loop.run_until_complete(self._continuously_read())

  async def _continuously_read(self):
    self.loops_seen.append(asyncio.get_running_loop())
    while not self.stop.is_set():
      while self.waiting:
        fut = self.waiting.pop()
        fut.get_loop().call_soon_threadsafe(fut.set_result, "reply")
      await asyncio.sleep(0.001)


# --- the shim on synthetic owners ------------------------------------------------


def test_without_the_shim_the_reader_fails_like_the_kernel_did(no_threads):
  reader = _Reader()
  thread = threading.Thread(target=reader._reading_thread_main, daemon=True)
  with pytest.raises(RuntimeError, match=PYODIDE_ERROR):
    thread.start()


def test_reader_runs_as_a_task_on_the_running_loop(no_threads):
  reader = _Reader()

  async def main():
    thread = stages.LoopTaskThread(target=reader._reading_thread_main, daemon=True)
    thread.start()
    assert thread.is_alive()
    fut = asyncio.get_running_loop().create_future()
    reader.waiting.append(fut)
    reply = await asyncio.wait_for(fut, 2)
    loop = asyncio.get_running_loop()
    reader.stop.set()
    thread.join(timeout=10)
    await asyncio.sleep(0.01)
    return reply, loop, thread

  reply, loop, thread = asyncio.run(main())
  assert reply == "reply"
  assert reader.loops_seen == [loop], "the reader must run on the caller's loop, not a new one"
  assert not reader.main_called
  assert not thread.is_alive()


def test_join_cancels_a_reader_stuck_in_a_read(no_threads):
  class Stuck(_Reader):
    async def _continuously_read(self):
      await asyncio.Event().wait()  # e.g. a transferIn that never resolves

  reader = Stuck()

  async def main():
    thread = stages.LoopTaskThread(target=reader._reading_thread_main)
    thread.start()
    await asyncio.sleep(0)
    thread.join(timeout=10)  # must not block the loop
    await asyncio.sleep(0)
    return thread

  assert not asyncio.run(main()).is_alive()


def test_starting_twice_is_refused_like_a_thread(no_threads):
  reader = _Reader()

  async def main():
    thread = stages.LoopTaskThread(target=reader._reading_thread_main)
    thread.start()
    try:
      with pytest.raises(RuntimeError, match="only be started once"):
        thread.start()
    finally:
      thread.join()

  asyncio.run(main())


def test_start_outside_a_running_loop_explains_itself(no_threads):
  thread = stages.LoopTaskThread(target=_Reader()._reading_thread_main)
  with pytest.raises(RuntimeError, match="running event loop"):
    thread.start()


def test_a_crashing_reader_is_reported_not_swallowed(no_threads, capsys):
  class Crashing(_Reader):
    async def _continuously_read(self):
      raise ValueError("bad firmware frame")

  async def main():
    thread = stages.LoopTaskThread(target=Crashing()._reading_thread_main)
    thread.start()
    await asyncio.sleep(0.01)
    return thread

  thread = asyncio.run(main())
  assert not thread.is_alive()
  err = capsys.readouterr().err
  assert "bad firmware frame" in err and "_continuously_read" in err


@pytest.mark.parametrize(
  "target_factory",
  [
    pytest.param(lambda: lambda: None, id="plain-function"),
    pytest.param(lambda: _NoCoroutine()._reading_thread_main, id="reader-name-without-coroutine"),
    pytest.param(lambda: _Reader()._continuously_read, id="other-method-name"),
  ],
)
def test_every_other_target_falls_back_to_the_real_start(no_threads, target_factory):
  async def main():
    stages.LoopTaskThread(target=target_factory()).start()

  with pytest.raises(RuntimeError, match=PYODIDE_ERROR):
    asyncio.run(main())


class _NoCoroutine:
  def _reading_thread_main(self):
    pass

  def _continuously_read(self):  # sync: not the supported shape
    pass


def test_fallback_still_starts_real_threads_where_threads_exist():
  ran = threading.Event()
  thread = stages.LoopTaskThread(target=ran.set)
  thread.start()
  thread.join(5)
  assert ran.is_set()


# --- installation ------------------------------------------------------------------


def test_install_is_a_noop_outside_pyodide(monkeypatch):
  monkeypatch.setattr(threading, "Thread", stages._REAL_THREAD)
  assert stages.install_loop_threads(platform="linux") is False
  assert threading.Thread is stages._REAL_THREAD


def test_install_in_pyodide_replaces_thread_idempotently(monkeypatch):
  monkeypatch.setattr(threading, "Thread", stages._REAL_THREAD)
  assert stages.install_loop_threads(platform="emscripten") is True
  assert stages.install_loop_threads(platform="emscripten") is True
  assert threading.Thread is stages.LoopTaskThread
  assert issubclass(stages.LoopTaskThread, stages._REAL_THREAD)


def test_bootstrap_installs_loop_threads_before_pylabrobot_is_imported():
  src = (_BOOTSTRAP_DIR / "praxis_bootstrap.py").read_text()
  body = src[src.index("async def praxis_main") :]
  install = body.index("stages.install_loop_threads()")
  assert install < body.index("import micropip"), "install before any wheel / PLR import"
  assert install < body.index("stages.apply()")


# --- the real PLR reading path -------------------------------------------------------


class _FakeHamiltonUSB:
  """Answers each written firmware command once, with the id PLR assigned to it."""

  def __init__(self):
    self.written: list[str] = []
    self._replies: list[bytes] = []

  async def setup(self):
    pass

  async def stop(self):
    pass

  async def write(self, data: bytes, timeout=None):
    cmd = data.decode()
    self.written.append(cmd)
    ident = cmd[cmd.index("id") : cmd.index("id") + 6]
    self._replies.append(f"{cmd[:4]}{ident}er00/00rf7.6S 35 2025-01-01".encode())

  async def read(self, timeout=None):
    await asyncio.sleep(0.001)
    if not self._replies:
      raise TimeoutError
    return self._replies.pop(0)


def _star_with_fake_usb():
  from pylabrobot.legacy.liquid_handling.backends.hamilton.STAR_backend import STARBackend
  from pylabrobot.resources.hamilton import STARLetDeck

  backend = STARBackend()
  backend.set_deck(STARLetDeck())
  backend.io = _FakeHamiltonUSB()
  return backend


async def _setup_send_stop(backend):
  from pylabrobot.legacy.liquid_handling.backends.hamilton.base import HamiltonLiquidHandler

  await HamiltonLiquidHandler.setup(backend)  # io.setup() + start the reader
  try:
    reply = await asyncio.wait_for(backend.send_command(module="C0", command="RF"), 10)
  finally:
    await HamiltonLiquidHandler.stop(backend)
  return reply


def test_real_hamilton_reader_fails_without_the_shim(no_threads):
  with pytest.raises(RuntimeError, match=PYODIDE_ERROR):
    asyncio.run(_setup_send_stop(_star_with_fake_usb()))


def test_real_hamilton_reader_round_trips_a_command_with_the_shim(pyodide_threading):
  backend = _star_with_fake_usb()
  reply = asyncio.run(_setup_send_stop(backend))
  assert backend.io.written and backend.io.written[0].startswith("C0RFid")
  assert "rf7.6S" in reply
  assert backend._reading_thread is None


# --- contract over the pinned PLR source ---------------------------------------------

# Thread sites the shim deliberately does not convert, with the reason. A Pyodide user
# reaching one gets the original "can't start new thread" error.
KNOWN_UNSUPPORTED = {
  ("visualizer/visualizer.py", "start_loop"): "browser visualizer server; not used in the REPL",
  ("visualizer/visualizer.py", "start_server"): "file server thread for the visualizer",
  ("visualizer3D/server.py", "serve"): "3D visualizer HTTP server; not used in the REPL",
  ("agrowpumps/agrow_pump_array.py", "manage_async_keep_alive"): (
    "keep-alive closure, not the reader shape; needs a PLR-side change"
  ),
  ("legacy/pumps/agrowpumps/agrowdosepump_backend.py", "manage_async_keep_alive"): (
    "keep-alive closure, not the reader shape; needs a PLR-side change"
  ),
  ("legacy/plate_reading/byonoy/byonoy_backend.py", "_background_ping_worker"): (
    "its coroutine blocks on threading.Event.wait(); as a task it would freeze the kernel"
  ),
  ("revvity/celigo/camera.py", "_run"): "native camera calls; needs real threads",
}


def _thread_target(call: ast.Call) -> str | None:
  for kw in call.keywords:
    if kw.arg == "target":
      if isinstance(kw.value, ast.Attribute):
        return kw.value.attr
      if isinstance(kw.value, ast.Name):
        return kw.value.id
      return "<call>"
  return None


def _is_thread_ctor(node: ast.AST) -> bool:
  return (
    isinstance(node, ast.Call)
    and isinstance(node.func, ast.Attribute)
    and node.func.attr == "Thread"
    and isinstance(node.func.value, ast.Name)
    and node.func.value.id == "threading"
  )


def _reader_shape_problem(cls: ast.ClassDef, classes: dict[str, ast.ClassDef]) -> str | None:
  """None when ``cls`` has the shape the shim relies on: ``_reading_thread_main`` only
  runs ``self._continuously_read()`` on a fresh loop, and ``_continuously_read`` is a
  coroutine function. The shim skips ``_reading_thread_main`` entirely, so anything
  else it did would silently not happen."""
  methods = {}
  for c in [cls] + [
    classes[b.id] for b in cls.bases if isinstance(b, ast.Name) and b.id in classes
  ]:
    for node in c.body:
      if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
        methods.setdefault(node.name, node)
  main, read = methods.get("_reading_thread_main"), methods.get("_continuously_read")
  if main is None:
    return "no _reading_thread_main"
  if not isinstance(read, ast.AsyncFunctionDef):
    return "_continuously_read is missing or not async"
  allowed = {
    "loop = asyncio.new_event_loop()",
    "asyncio.set_event_loop(loop)",
    "loop.run_until_complete(self._continuously_read())",
  }
  body = [
    ast.unparse(s)
    for s in main.body
    if not isinstance(s, ast.Expr) or not isinstance(s.value, ast.Constant)
  ]
  if set(body) != allowed or len(body) != len(allowed):
    return f"_reading_thread_main does more than run _continuously_read: {body}"
  return None


def thread_sites(root: Path) -> list[dict]:
  sites = []
  for path in sorted(root.rglob("*.py")):
    rel = path.relative_to(root).as_posix()
    if "/tests/" in f"/{rel}" or path.name.endswith("_tests.py") or path.name.startswith("test_"):
      continue
    tree = ast.parse(path.read_text())
    classes = {n.name: n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    for cls_or_mod in [tree, *classes.values()]:
      for node in ast.walk(cls_or_mod):
        if not _is_thread_ctor(node):
          continue
        target = _thread_target(node)
        owner = cls_or_mod if isinstance(cls_or_mod, ast.ClassDef) else None
        sites.append(
          {"file": rel, "target": target, "line": node.lineno, "owner": owner, "classes": classes}
        )
  # a site is found once per enclosing scope; keep the innermost (class) one
  best: dict[tuple, dict] = {}
  for s in sites:
    key = (s["file"], s["line"])
    if key not in best or s["owner"] is not None:
      best[key] = s
  return list(best.values())


def classify(sites: list[dict]) -> tuple[list[str], list[str]]:
  supported, problems = [], []
  for s in sites:
    where = f"{s['file']}:{s['line']}"
    if s["target"] in stages.LOOP_TASK_TARGETS:
      problem = (
        "not inside a class"
        if s["owner"] is None
        else _reader_shape_problem(s["owner"], s["classes"])
      )
      if problem:
        problems.append(f"{where}: reader-named target, but {problem}")
      else:
        supported.append(where)
    elif (s["file"], s["target"]) not in KNOWN_UNSUPPORTED:
      problems.append(
        f"{where}: new threading.Thread(target={s['target']}) -- Pyodide cannot start it; "
        "convert it to the reader shape or add it to KNOWN_UNSUPPORTED with a reason"
      )
  return supported, problems


def test_every_plr_thread_site_is_supported_or_known():
  supported, problems = classify(thread_sites(PLR_SRC))
  assert not problems, "\n".join(problems)
  # The three Hamilton readers (legacy backend, text router, USB driver), two sites each.
  assert len(supported) == 6, supported
  assert {p.split(":")[0] for p in supported} == {
    "legacy/liquid_handling/backends/hamilton/base.py",
    "hamilton/protocol/text/router.py",
    "hamilton/transport/usb/usb.py",
  }


def test_known_unsupported_has_no_stale_entries():
  present = {(s["file"], s["target"]) for s in thread_sites(PLR_SRC)}
  stale = set(KNOWN_UNSUPPORTED) - present
  assert not stale, f"no longer in PLR, drop from KNOWN_UNSUPPORTED: {sorted(stale)}"


def test_contract_flags_a_new_thread_site_and_a_reader_that_does_more(tmp_path):
  """Negative control: the scan must fail on the two shapes it exists to catch."""
  (tmp_path / "new_device.py").write_text(
    "import threading\n"
    "class Pinger:\n"
    "  def start(self):\n"
    "    threading.Thread(target=self._ping, daemon=True).start()\n"
  )
  (tmp_path / "busy_reader.py").write_text(
    "import asyncio, threading\n"
    "class Busy:\n"
    "  def setup(self):\n"
    "    threading.Thread(target=self._reading_thread_main).start()\n"
    "  def _reading_thread_main(self):\n"
    "    self.calibrate()\n"
    "    loop = asyncio.new_event_loop()\n"
    "    asyncio.set_event_loop(loop)\n"
    "    loop.run_until_complete(self._continuously_read())\n"
    "  async def _continuously_read(self):\n"
    "    pass\n"
  )
  supported, problems = classify(thread_sites(tmp_path))
  assert supported == []
  assert len(problems) == 2
  assert any("new threading.Thread(target=_ping)" in p for p in problems)
  assert any("does more than run _continuously_read" in p for p in problems)
