"""AC-42 runner cases for ``scripts/unit_runner.py`` (epic 260929_notebook-display-design, A1a).

``unit_runner`` is the one module that starts and kills harness/spike units
(D16 "Shared unit runner"). Playwright launches Chromium ``detached: true``, so
Chromium leads its own process group and a group kill of the unit leaves a hung
browser alive; the runner walks the process tree, sweeps ``/proc/*/environ`` for
the unit's ``PRAXIS_UNIT_TOKEN`` and freezes/kills everything it finds.

Every case here uses REAL short-lived process trees (small python children that
spawn ``setsid`` grandchildren, ignore ``SIGTERM``, hang after a stamp, ...).
Nothing mocks the kernel side of the behavior. The few injected seams
(``environ_reader``, ``children_reader``, ``stat_reader``, ``pid_lister``,
``exit_fn``, ``kill_fn``) exist so the spec's fault cases (unreadable environ,
pid reuse, ``KeyboardInterrupt`` mid-walk, the watchdog's ``os._exit``) can be
provoked deterministically; the processes under them are still real.

Safety, because a bug in a process killer must not take the box with it:
  * every child sleeps at most 120 s, and every test has a hard timeout;
  * an autouse fixture tags every process a test spawns with a per-test mark
    (``UR_TEST_MARK``) and, on teardown, SIGCONT+SIGKILLs everything carrying it
    with its OWN sweep (deliberately not ``unit_runner.kill_tree``: a broken
    runner cannot be trusted to clean up after its own test);
  * the CLI ``--reap`` cases restrict themselves with ``--token`` so they cannot
    touch another session's units (an unrestricted ``--reap`` kills every token
    on the box; its unrestricted logic is covered in-process over an injected pid
    universe instead).

The real-Chromium case (C9-5) runs in CI only (``CI`` set) and never locally.
The scaffolding it uses (positive control, survivor scan) is exercised locally
against a stub process tree so the CI-only case is not the first time it runs.
"""

from __future__ import annotations

import hashlib
import importlib.util
import json
import logging
import os
import re
import signal
import stat
import subprocess
import sys
import textwrap
import threading
import time
import uuid
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
RUNNER_PATH = REPO_ROOT / "scripts" / "unit_runner.py"
REPL_SMOKE_PATH = REPO_ROOT / "scripts" / "repl_smoke.py"

TOKEN_ENV = "PRAXIS_UNIT_TOKEN"
MARK_ENV = "UR_TEST_MARK"

#: Hard per-test bound (pytest-timeout): a runaway test must fail, not hang.
pytestmark = pytest.mark.timeout(120)

# --------------------------------------------------------------------------- #
# module under test
# --------------------------------------------------------------------------- #


@pytest.fixture(scope="session")
def ur():
    """``scripts/unit_runner.py`` loaded BY PATH, as its real consumers load it."""
    assert RUNNER_PATH.is_file(), f"scripts/unit_runner.py is missing ({RUNNER_PATH})"
    spec = importlib.util.spec_from_file_location("unit_runner_under_test", RUNNER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["unit_runner_under_test"] = module
    spec.loader.exec_module(module)
    return module


# --------------------------------------------------------------------------- #
# independent /proc helpers (never routed through the module under test)
# --------------------------------------------------------------------------- #


def _stat(pid: int) -> dict | None:
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except (FileNotFoundError, ProcessLookupError, PermissionError):
        return None
    rest = raw.rsplit(")", 1)[1].split()
    return {
        "state": rest[0],
        "ppid": int(rest[1]),
        "pgrp": int(rest[2]),
        "sid": int(rest[3]),
        "starttime": int(rest[19]),
    }


def proc_state(pid: int) -> str | None:
    st = _stat(pid)
    return st["state"] if st else None


def is_running(pid: int) -> bool:
    """Alive for our purposes: present and neither zombie nor dead."""
    state = proc_state(pid)
    return state is not None and state not in ("Z", "X")


def wait_gone(pid: int, within: float) -> bool:
    deadline = time.monotonic() + within
    while time.monotonic() < deadline:
        if not is_running(pid):
            return True
        time.sleep(0.05)
    return not is_running(pid)


def wait_not_stopped(pid: int, within: float = 3.0) -> str | None:
    deadline = time.monotonic() + within
    state = proc_state(pid)
    while state == "T" and time.monotonic() < deadline:
        time.sleep(0.05)
        state = proc_state(pid)
    return state


def _all_pids() -> list[int]:
    return [int(n) for n in os.listdir("/proc") if n.isdigit()]


def pids_with_environ_entry(entry: bytes) -> list[int]:
    """Every readable process whose environ holds exactly ``entry`` (NUL-delimited)."""
    found = []
    me = os.getpid()
    for pid in _all_pids():
        if pid == me:
            continue
        try:
            raw = Path(f"/proc/{pid}/environ").read_bytes()
        except OSError:
            continue
        if entry in raw.split(b"\0"):
            found.append(pid)
    return found


def procs_with_token(token: str) -> list[int]:
    return pids_with_environ_entry(f"{TOKEN_ENV}={token}".encode())


def token_of(pid: int) -> str | None:
    try:
        raw = Path(f"/proc/{pid}/environ").read_bytes()
    except OSError:
        return None
    prefix = f"{TOKEN_ENV}=".encode()
    for entry in raw.split(b"\0"):
        if entry.startswith(prefix):
            return entry[len(prefix) :].decode()
    return None


def comm_of(pid: int) -> str:
    try:
        return Path(f"/proc/{pid}/comm").read_text().strip()
    except OSError:
        return ""


def exe_basename(pid: int) -> str:
    try:
        return os.path.basename(os.readlink(f"/proc/{pid}/exe"))
    except OSError:
        return ""


# --------------------------------------------------------------------------- #
# per-test process tracking and teardown
# --------------------------------------------------------------------------- #

PRELUDE = """\
import importlib.util, json, os, signal, subprocess, sys, threading, time
_spec = importlib.util.spec_from_file_location("unit_runner", os.environ["UR_PATH"])
ur = importlib.util.module_from_spec(_spec)
sys.modules["unit_runner"] = ur
_spec.loader.exec_module(ur)
SLEEPER = "import time; time.sleep(120)"
IGNORER = "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)"


def put(path, text):
    with open(path + ".t", "w") as f:
        f.write(text)
    os.replace(path + ".t", path)


"""


class Procs:
    """Spawns real subprocesses tagged for guaranteed cleanup."""

    def __init__(self, tmp: Path, mark: str) -> None:
        self.tmp = tmp
        self.mark = mark
        self.popens: list[subprocess.Popen] = []

    def env(self, **extra: str) -> dict[str, str]:
        env = dict(os.environ)  # carries MARK_ENV and UR_PATH (autouse fixture)
        env.update(extra)
        return env

    def script(self, name: str, body: str) -> Path:
        path = self.tmp / name
        path.write_text(PRELUDE + textwrap.dedent(body))
        return path

    def spawn(
        self,
        argv: list[str],
        *,
        env: dict[str, str] | None = None,
        new_session: bool = False,
        **kwargs,
    ) -> subprocess.Popen:
        proc = subprocess.Popen(
            argv,
            env=env if env is not None else self.env(),
            start_new_session=new_session,
            **kwargs,
        )
        self.popens.append(proc)
        return proc

    def sleeper(
        self,
        *,
        token: str | None = None,
        extra_env: dict[str, str] | None = None,
        ignore_sigterm: bool = False,
        new_session: bool = True,
    ) -> subprocess.Popen:
        env = self.env(**(extra_env or {}))
        if token is not None:
            env[TOKEN_ENV] = token
        code = (
            "import signal, time; signal.signal(signal.SIGTERM, signal.SIG_IGN); time.sleep(120)"
            if ignore_sigterm
            else "import time; time.sleep(120)"
        )
        return self.spawn([sys.executable, "-c", code], env=env, new_session=new_session)

    def wait_file(self, path: Path | str, timeout: float = 15.0) -> str:
        path = Path(path)
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            if path.exists():
                return path.read_text()
            time.sleep(0.02)
        raise AssertionError(f"{path} never appeared within {timeout}s")

    def teardown(self) -> None:
        entry = f"{MARK_ENV}={self.mark}".encode()
        for _ in range(4):
            pids = pids_with_environ_entry(entry)
            if not pids:
                break
            for pid in pids:
                for sig in (signal.SIGCONT, signal.SIGKILL):
                    try:
                        os.kill(pid, sig)
                    except OSError:
                        pass
            time.sleep(0.05)
        for proc in self.popens:
            try:
                proc.wait(timeout=2)
            except Exception:
                pass


@pytest.fixture(autouse=True)
def procs(tmp_path, monkeypatch):
    mark = uuid.uuid4().hex
    monkeypatch.setenv(MARK_ENV, mark)
    monkeypatch.setenv("UR_PATH", str(RUNNER_PATH))
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    tracker = Procs(tmp_path, mark)
    try:
        yield tracker
    finally:
        tracker.teardown()


class SignalSpy:
    """Records every signal kill_tree sends, whichever syscall carries it."""

    def __init__(self, monkeypatch) -> None:
        self.calls: list[tuple[str, int, int]] = []  # (kind, pid-or-pgid, sig)
        real_kill, real_killpg = os.kill, os.killpg

        def kill(pid, sig):
            self.calls.append(("kill", pid, int(sig)))
            return real_kill(pid, sig)

        def killpg(pgid, sig):
            self.calls.append(("killpg", pgid, int(sig)))
            return real_killpg(pgid, sig)

        monkeypatch.setattr(os, "kill", kill)
        monkeypatch.setattr(os, "killpg", killpg)
        if hasattr(signal, "pidfd_send_signal"):
            real_pidfd = signal.pidfd_send_signal

            def pidfd_send_signal(fd, sig, *args, **kwargs):
                pid = -1
                try:
                    for line in Path(f"/proc/self/fdinfo/{fd}").read_text().splitlines():
                        if line.startswith("Pid:"):
                            pid = int(line.split()[1])
                except OSError:
                    pass
                self.calls.append(("pidfd", pid, int(sig)))
                return real_pidfd(fd, sig, *args, **kwargs)

            monkeypatch.setattr(signal, "pidfd_send_signal", pidfd_send_signal)

    def real_signals(self) -> list[tuple[str, int, int]]:
        return [c for c in self.calls if c[2] != 0]

    def to_pid(self, pid: int) -> list[int]:
        return [s for k, p, s in self.real_signals() if k in ("kill", "pidfd") and p == pid]

    def group_signals(self, pgid: int) -> list[int]:
        return [s for k, p, s in self.real_signals() if k == "killpg" and p == pgid]

    def count(self, sig: int) -> int:
        return sum(1 for _, _, s in self.real_signals() if s == int(sig))


def _children_of(pid: int) -> list[int]:
    kids: list[int] = []
    try:
        for tid in os.listdir(f"/proc/{pid}/task"):
            try:
                kids += [int(x) for x in Path(f"/proc/{pid}/task/{tid}/children").read_text().split()]
            except OSError:
                pass
    except OSError:
        pass
    return kids


def _read_environ_real(pid: int) -> bytes:
    return Path(f"/proc/{pid}/environ").read_bytes()


# --------------------------------------------------------------------------- #
# run_unit
# --------------------------------------------------------------------------- #


def test_run_unit_reports_exit_code_without_timeout(ur):
    out = ur.run_unit([sys.executable, "-c", "raise SystemExit(7)"], 20, env=None, cwd=None)
    assert (out.exit, out.timed_out, out.killed) == (7, False, False)


def test_run_unit_mints_a_fresh_token_into_environ_at_exec(ur, procs, tmp_path):
    script = procs.script(
        "tok.py",
        """
        wanted = (b"PRAXIS_UNIT_TOKEN=", b"UR_FOO=")
        entries = [e.decode() for e in open("/proc/self/environ", "rb").read().split(b"\\0")
                   if e.startswith(wanted)]
        put(sys.argv[1], json.dumps({"entries": entries, "sid": os.getsid(0), "pid": os.getpid()}))
        """,
    )
    seen = []
    for i in range(2):
        out_file = tmp_path / f"tok{i}.json"
        base_env = procs.env(UR_FOO="bar", **{TOKEN_ENV: "stale-token-must-be-replaced"})
        out = ur.run_unit([sys.executable, str(script), str(out_file)], 20, env=base_env, cwd=None)
        assert out.exit == 0
        data = json.loads(out_file.read_text())
        tokens = [e for e in data["entries"] if e.startswith(f"{TOKEN_ENV}=")]
        assert len(tokens) == 1, "exactly one token entry: the fresh one replaces any preset"
        token = tokens[0].split("=", 1)[1]
        assert token != "stale-token-must-be-replaced" and re.fullmatch(r"[0-9a-f]{32}", token)
        assert "UR_FOO=bar" in data["entries"], "the caller's env is passed through"
        # start_new_session=True: the child leads its own session (kill_tree may then
        # signal its group without touching the caller's).
        assert data["sid"] == data["pid"]
        seen.append(token)
    assert seen[0] != seen[1], "each unit gets its own token"


def test_run_unit_timeout_kills_setsid_grandchild(ur, procs, tmp_path):
    """The Playwright shape: a detached grandchild in its own session and group."""
    info = tmp_path / "info.json"
    script = procs.script(
        "hang_setsid.py",
        """
        gp = subprocess.Popen([sys.executable, "-c", SLEEPER], start_new_session=True)
        put(sys.argv[1], json.dumps({"child": os.getpid(), "gp": gp.pid,
                                     "child_pgrp": os.getpgrp(), "gp_pgrp": os.getpgid(gp.pid)}))
        time.sleep(120)
        """,
    )
    t0 = time.monotonic()
    out = ur.run_unit([sys.executable, str(script), str(info)], 3, env=None, cwd=None, grace_s=2)
    elapsed = time.monotonic() - t0
    data = json.loads(procs.wait_file(info))
    assert data["gp_pgrp"] != data["child_pgrp"], "control: the grandchild really is detached"
    assert out.timed_out and out.killed and out.exit != 0
    assert elapsed < 3 + 2 + 5
    assert wait_gone(data["gp"], 3), "the detached grandchild survived run_unit's timeout"
    assert wait_gone(data["child"], 3)
    assert wait_not_stopped(data["gp"]) != "T" and wait_not_stopped(data["child"]) != "T"


def test_run_unit_timeout_kills_orphan_reparented_out_of_the_tree(ur, procs, tmp_path):
    """The intermediate parent exits first, so the walk cannot find the grandchild:
    only the PRAXIS_UNIT_TOKEN sweep can.
    """
    info = tmp_path / "info.json"
    inter = procs.script(
        "inter.py",
        """
        gp = subprocess.Popen([sys.executable, "-c", SLEEPER], start_new_session=True)
        put(sys.argv[1], str(gp.pid))
        """,
    )
    script = procs.script(
        "hang_reparent.py",
        f"""
        subprocess.run([sys.executable, {str(inter)!r}, sys.argv[1] + ".gp"], check=True)
        gp = int(open(sys.argv[1] + ".gp").read())
        time.sleep(0.3)
        ppid = int(open("/proc/%d/stat" % gp).read().rsplit(")", 1)[1].split()[1])
        put(sys.argv[1], json.dumps({{"child": os.getpid(), "gp": gp, "gp_ppid": ppid}}))
        time.sleep(120)
        """,
    )
    out = ur.run_unit([sys.executable, str(script), str(info)], 4, env=None, cwd=None, grace_s=2)
    data = json.loads(procs.wait_file(info))
    assert data["gp_ppid"] != data["child"], "control: the grandchild is outside the child's tree"
    assert out.timed_out and out.killed
    assert wait_gone(data["gp"], 3), "the re-parented orphan survived the token sweep"
    assert wait_gone(data["child"], 3)


def test_run_unit_timeout_escalates_past_sigterm_ignorers(ur, procs, tmp_path):
    info = tmp_path / "info.json"
    script = procs.script(
        "ignorers.py",
        """
        signal.signal(signal.SIGTERM, signal.SIG_IGN)
        gp = subprocess.Popen([sys.executable, "-c", IGNORER], start_new_session=True)
        put(sys.argv[1], json.dumps({"child": os.getpid(), "gp": gp.pid}))
        time.sleep(120)
        """,
    )
    t0 = time.monotonic()
    out = ur.run_unit([sys.executable, str(script), str(info)], 3, env=None, cwd=None, grace_s=1)
    data = json.loads(procs.wait_file(info))
    assert out.timed_out and out.killed
    assert time.monotonic() - t0 < 3 + 1 + 6
    assert wait_gone(data["gp"], 3) and wait_gone(data["child"], 3), "SIGKILL after the grace"


def test_run_unit_does_not_kill_a_unit_that_finishes_in_time(ur, procs, tmp_path):
    marker = tmp_path / "done"
    out = ur.run_unit(
        [sys.executable, "-c", f"import time; time.sleep(0.3); open({str(marker)!r}, 'w').write('x')"],
        20,
        env=None,
        cwd=None,
    )
    assert marker.exists() and (out.exit, out.timed_out, out.killed) == (0, False, False)


# --------------------------------------------------------------------------- #
# kill_tree
# --------------------------------------------------------------------------- #

_TREE_BODY = """
kids = [
    subprocess.Popen([sys.executable, "-c", SLEEPER]),
    subprocess.Popen([sys.executable, "-c", SLEEPER], start_new_session=True),
]
nested = subprocess.Popen(
    [sys.executable, "-c",
     "import subprocess, sys, time\\n"
     "p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\\n"
     "print(p.pid, flush=True)\\n"
     "time.sleep(120)"],
    stdout=subprocess.PIPE, text=True)
grandkid = int(nested.stdout.readline())
put(sys.argv[1], json.dumps({"root": os.getpid(),
                             "pids": [k.pid for k in kids] + [nested.pid, grandkid]}))
time.sleep(120)
"""


def _spawn_tree(procs, tmp_path, *, token: str | None) -> tuple[subprocess.Popen, dict]:
    info = tmp_path / "tree.json"
    script = procs.script("tree.py", _TREE_BODY)
    env = procs.env(**({TOKEN_ENV: token} if token else {}))
    root = procs.spawn([sys.executable, str(script), str(info)], env=env, new_session=True)
    return root, json.loads(procs.wait_file(info))


def test_kill_tree_walk_alone_kills_root_and_every_descendant(ur, procs, tmp_path):
    """Token deliberately NOT matching anything: the walk by itself must do it."""
    root, data = _spawn_tree(procs, tmp_path, token=None)
    members = [data["root"], *data["pids"]]
    assert all(is_running(p) for p in members), "control: the whole tree is up"
    ur.kill_tree(root.pid, "not-any-tokens-value", 2)
    for pid in members:
        assert wait_gone(pid, 3), f"{pid} survived kill_tree"
        assert proc_state(pid) != "T"


def test_kill_tree_fixpoint_catches_a_child_forked_during_the_grace_window(ur, procs, tmp_path):
    """C9-2: a sweep-found setsid orphan whose SIGTERM handler forks a child that
    ignores SIGTERM. The child inherits the token, appears only during the grace
    window, and must still die.
    """
    token = uuid.uuid4().hex
    forked = tmp_path / "forked.pid"
    orphan = procs.script(
        "fp_orphan.py",
        f"""
        CHILD = (
            "import os, signal, sys, time\\n"
            "signal.signal(signal.SIGTERM, signal.SIG_IGN)\\n"
            "open(sys.argv[1] + '.t', 'w').write(str(os.getpid()))\\n"
            "os.replace(sys.argv[1] + '.t', sys.argv[1])\\n"
            "time.sleep(120)\\n"
        )

        def on_term(signum, frame):
            # its own session: the group SIGKILL cannot reach it, only the second fixpoint can
            subprocess.Popen([sys.executable, "-c", CHILD, {str(forked)!r}], start_new_session=True)

        signal.signal(signal.SIGTERM, on_term)
        put(sys.argv[1], str(os.getpid()))
        time.sleep(120)
        """,
    )
    launcher = procs.script(
        "fp_launcher.py",
        f"""
        subprocess.Popen([sys.executable, {str(orphan)!r}, sys.argv[1]], start_new_session=True)
        while not os.path.exists(sys.argv[1]):
            time.sleep(0.02)
        """,
    )
    orphan_pidfile = tmp_path / "orphan.pid"
    lp = procs.spawn(
        [sys.executable, str(launcher), str(orphan_pidfile)],
        env=procs.env(**{TOKEN_ENV: token}),
        new_session=True,
    )
    assert lp.wait(timeout=20) == 0, "the launcher exits, orphaning its child"
    orphan_pid = int(orphan_pidfile.read_text())
    assert _stat(orphan_pid)["ppid"] != lp.pid and is_running(orphan_pid), "control: a live orphan"

    ur.kill_tree(lp.pid, token, 1)

    assert forked.exists(), (
        "control: the orphan's SIGTERM handler never ran, so no child was forked during the "
        "grace window (a stopped process cannot run its handler; SIGCONT must follow SIGTERM)"
    )
    forked_pid = int(forked.read_text())
    assert wait_gone(orphan_pid, 3), "the sweep-found orphan survived"
    assert wait_gone(forked_pid, 3), "the child forked during the grace window survived"
    assert [p for p in procs_with_token(token) if is_running(p)] == []


def test_kill_tree_survives_unreadable_and_empty_environs(ur, procs):
    """C9-2: PermissionError / ProcessLookupError / empty environ are skipped, not fatal,
    and the token-carrying grandchild is still killed.
    """
    token = uuid.uuid4().hex
    victim = procs.sleeper(token=token)
    b_perm, b_gone, b_empty = (procs.sleeper() for _ in range(3))

    def reader(pid: int) -> bytes:
        if pid == b_perm.pid:
            raise PermissionError(13, "injected")
        if pid == b_gone.pid:
            raise ProcessLookupError(3, "injected")
        if pid == b_empty.pid:
            return b""
        return _read_environ_real(pid)

    assert is_running(victim.pid)
    ur.kill_tree(None, token, 1, environ_reader=reader)

    assert wait_gone(victim.pid, 3), "the token-carrying process survived"
    for bystander in (b_perm, b_gone, b_empty):
        assert is_running(bystander.pid) and proc_state(bystander.pid) != "T"


def test_kill_tree_sweep_matches_the_whole_environ_entry_only(ur, procs):
    """C9-2: `PRAXIS_UNIT_TOKEN=<token>x`, `X_PRAXIS_UNIT_TOKEN=<token>`, a prefix and a
    substring inside another value must not be signalled.
    """
    token = uuid.uuid4().hex
    victim = procs.sleeper(token=token)
    decoys = [
        procs.sleeper(extra_env={TOKEN_ENV: token + "x"}),
        procs.sleeper(extra_env={f"X_{TOKEN_ENV}": token}),
        procs.sleeper(extra_env={TOKEN_ENV: "x" + token}),
        procs.sleeper(extra_env={"UR_WRAP": f"{TOKEN_ENV}={token}"}),
    ]
    ur.kill_tree(None, token, 1)
    assert wait_gone(victim.pid, 3)
    for decoy in decoys:
        assert is_running(decoy.pid), "a non-matching environ entry was killed"
        assert proc_state(decoy.pid) != "T", "a non-matching process was left frozen"


def test_kill_tree_sigcont_in_finally_leaves_nothing_stopped(ur, procs, tmp_path, monkeypatch):
    """C9-2: an interrupt mid-walk re-raises and never leaves a process in state T."""
    token = uuid.uuid4().hex
    root, data = _spawn_tree(procs, tmp_path, token=token)
    members = [data["root"], *data["pids"]]
    spy = SignalSpy(monkeypatch)

    def walker(pid: int) -> list[int]:
        if spy.count(signal.SIGSTOP) >= 2:
            raise KeyboardInterrupt
        return _children_of(pid)

    with pytest.raises(KeyboardInterrupt):
        ur.kill_tree(root.pid, token, 1, children_reader=walker)

    assert spy.count(signal.SIGSTOP) >= 2, "control: processes really were frozen mid-walk"
    # SIGSTOP/SIGCONT take effect asynchronously: settle first, or a process that has
    # been signalled but not yet stopped reads as "not T" and the check passes vacuously.
    time.sleep(0.5)
    stuck = [p for p in members if wait_not_stopped(p) == "T"]
    assert stuck == [], f"processes left in state T after an interrupted walk: {stuck}"


def test_kill_tree_pid_reuse_guard_without_pidfd(ur, procs, monkeypatch):
    """C9-3: a collected pid whose starttime changed is treated as reused: it gets no
    signal, and its group gets none when no other verified live member remains.
    """
    token = uuid.uuid4().hex
    reused = procs.sleeper(token=token)  # leads its own group
    real_victim = procs.sleeper(token=token)
    reused_pgid = os.getpgid(reused.pid)
    reads: dict[int, int] = {}

    def stat_reader(pid: int):
        st = ur.read_proc_stat(pid)
        if st is not None and pid == reused.pid:
            reads[pid] = reads.get(pid, 0) + 1
            if reads[pid] > 1:  # first read (discovery) real; every later read "reused"
                return st._replace(starttime=st.starttime + 1)
        return st

    spy = SignalSpy(monkeypatch)
    ur.kill_tree(None, token, 0.5, use_pidfd=False, stat_reader=stat_reader)

    assert reads.get(reused.pid, 0) > 1, "control: the guard re-read the starttime"
    assert wait_gone(real_victim.pid, 3), "control: the guard is selective, not a no-op"
    assert is_running(reused.pid), "the reused pid was killed"
    assert spy.to_pid(reused.pid) == [], "a pid whose starttime changed received a signal"
    assert spy.group_signals(reused_pgid) == [], "group signalled with no verified live member"


def test_kill_tree_sends_every_per_pid_signal_through_pidfd_when_available(ur, procs, monkeypatch):
    if not hasattr(os, "pidfd_open") or not hasattr(signal, "pidfd_send_signal"):
        pytest.skip("no pidfd support on this platform")
    try:
        os.close(os.pidfd_open(os.getpid()))
    except OSError:
        pytest.skip("pidfd_open is not permitted here")
    token = uuid.uuid4().hex
    victims = [procs.sleeper(token=token) for _ in range(2)]
    spy = SignalSpy(monkeypatch)

    ur.kill_tree(None, token, 0.5)

    for v in victims:
        assert wait_gone(v.pid, 3)
        kinds = {k for k, p, s in spy.real_signals() if p == v.pid and k in ("kill", "pidfd")}
        assert kinds == {"pidfd"}, f"per-pid signals to {v.pid} did not all use pidfd: {kinds}"
    assert any(k == "pidfd" for k, _, _ in spy.real_signals())


def test_kill_tree_never_signals_the_caller_or_its_process_group(ur, procs, tmp_path):
    """The Watchdog case: the caller itself carries the token and shares a process group
    with one of its descendants.
    """
    token = uuid.uuid4().hex
    out = tmp_path / "caller.json"
    script = procs.script(
        "caller.py",
        """
        calls = []
        real_killpg = os.killpg
        os.killpg = lambda pg, sig: (calls.append([pg, int(sig)]), real_killpg(pg, sig))[1]
        same_group = subprocess.Popen([sys.executable, "-c", SLEEPER])
        other_group = subprocess.Popen([sys.executable, "-c", SLEEPER], start_new_session=True)
        assert os.getpgid(same_group.pid) == os.getpgrp() != os.getpgid(other_group.pid)
        ur.kill_tree(os.getpid(), os.environ["PRAXIS_UNIT_TOKEN"], 1)
        put(sys.argv[1], json.dumps({"alive": True, "killpg": calls, "own_pgrp": os.getpgrp(),
                                     "same": same_group.pid, "other": other_group.pid}))
        """,
    )
    proc = procs.spawn(
        [sys.executable, str(script), str(out)], env=procs.env(**{TOKEN_ENV: token}), new_session=True
    )
    assert proc.wait(timeout=30) == 0, "the caller died (or its assertion failed)"
    data = json.loads(out.read_text())
    assert data["alive"]
    assert data["own_pgrp"] not in [pg for pg, _ in data["killpg"]]
    assert wait_gone(data["same"], 3) and wait_gone(data["other"], 3)


def test_kill_tree_logs_a_survivor_and_returns_it(ur, procs, monkeypatch, caplog):
    token = uuid.uuid4().hex
    victim = procs.sleeper(token=token)
    with monkeypatch.context() as m:
        m.setattr(os, "kill", lambda pid, sig: None)
        m.setattr(os, "killpg", lambda pgid, sig: None)
        with caplog.at_level(logging.ERROR):
            survivors = ur.kill_tree(None, token, 0.3, use_pidfd=False)
    assert victim.pid in list(survivors)
    assert any(r.levelno >= logging.ERROR and str(victim.pid) in r.getMessage() for r in caplog.records)
    assert is_running(victim.pid)


# --------------------------------------------------------------------------- #
# ensure_token
# --------------------------------------------------------------------------- #

_ENSURE_BODY = """
with open(os.path.join(sys.argv[1], "runs"), "a") as f:
    f.write("run\\n")
tok = ur.ensure_token()
entries = open("/proc/self/environ", "rb").read().split(b"\\0")
put(os.path.join(sys.argv[1], "out.json"), json.dumps({
    "tok": tok,
    "in_environ": (b"PRAXIS_UNIT_TOKEN=" + tok.encode()) in entries,
    "os_environ": os.environ.get("PRAXIS_UNIT_TOKEN"),
    "optimize": sys.flags.optimize,
}))
"""


def test_ensure_token_reexecs_so_the_token_is_in_proc_self_environ(ur, procs, tmp_path):
    """C9-4 and C10-4: re-exec (a token assigned to os.environ after exec is invisible in
    /proc/self/environ), from sys.orig_argv so interpreter flags survive.
    """
    script = procs.script("ensure.py", _ENSURE_BODY)
    outdir = tmp_path / "e1"
    outdir.mkdir()
    proc = procs.spawn([sys.executable, "-O", str(script), str(outdir)], env=procs.env())
    assert proc.wait(timeout=30) == 0
    data = json.loads((outdir / "out.json").read_text())
    assert data["in_environ"], "the token is not in /proc/self/environ after ensure_token()"
    assert re.fullmatch(r"[0-9a-f]{32}", data["tok"]) and data["os_environ"] == data["tok"]
    assert (outdir / "runs").read_text().count("run") == 2, "control: it really re-exec'd"
    assert data["optimize"] == 1, "interpreter flags (-O) were lost across the re-exec"


def test_ensure_token_is_a_noop_when_the_token_is_already_set(ur, procs, tmp_path):
    script = procs.script("ensure.py", _ENSURE_BODY)
    outdir = tmp_path / "e2"
    outdir.mkdir()
    preset = uuid.uuid4().hex
    proc = procs.spawn([sys.executable, str(script), str(outdir)], env=procs.env(**{TOKEN_ENV: preset}))
    assert proc.wait(timeout=30) == 0
    data = json.loads((outdir / "out.json").read_text())
    assert data["tok"] == preset and data["in_environ"]
    assert (outdir / "runs").read_text().count("run") == 1, "no re-exec when the token is set"


# --------------------------------------------------------------------------- #
# Watchdog
# --------------------------------------------------------------------------- #

_WD_BODY = """
ur.ensure_token()
outdir, mode = sys.argv[1], sys.argv[2]
result = os.path.join(outdir, "result.json")
stamp = os.path.join(outdir, "stamp.json")
marker = os.path.join(outdir, "timeout.json")


def on_expire():
    try:
        os.unlink(result)
    except FileNotFoundError:
        pass
    ur.write_atomic(marker, b'{"unit": "u"}')
    ur.emit_line(json.dumps({"unit": "u", "status": "timeout"}))


if mode in ("hang", "hang_stdout_full", "hang_after_result"):
    if mode == "hang_stdout_full":
        os.set_blocking(1, False)
        try:
            while True:
                os.write(1, b"x" * 4096)
        except BlockingIOError:
            pass
        os.set_blocking(1, True)  # a plain print() would now block forever
    wd = ur.Watchdog(1, on_expire, grace_s=1)
    if mode == "hang_after_result":
        wd.write_result(lambda: ur.write_atomic(result, b'{"ok": true}'))
    gp = subprocess.Popen([sys.executable, "-c", SLEEPER], start_new_session=True)
    put(os.path.join(outdir, "gp.json"), json.dumps({"gp": gp.pid, "child": os.getpid()}))
    time.sleep(120)
else:  # stamp_os_exit / stamp_sys_exit
    import atexit
    atexit.register(lambda: time.sleep(10 ** 6))
    threading.Thread(target=lambda: threading.Event().wait(), daemon=False).start()
    wd = ur.Watchdog(1, on_expire, grace_s=1)
    committed = wd.commit(lambda: ur.write_atomic(stamp, b'{"exit": 3}'))
    put(os.path.join(outdir, "committed.json"), json.dumps(committed))
    if mode == "stamp_os_exit":
        os._exit(3)
    sys.exit(3)
"""


def _run_wd_child(procs, tmp_path, mode: str, **popen_kwargs):
    outdir = tmp_path / f"wd_{mode}"
    outdir.mkdir()
    script = procs.script(f"wd_{mode}.py", _WD_BODY)
    proc = procs.spawn(
        [sys.executable, str(script), str(outdir), mode], env=procs.env(), new_session=True, **popen_kwargs
    )
    return proc, outdir


def test_watchdog_child_exits_124_at_budget_and_its_setsid_grandchild_is_gone(ur, procs, tmp_path):
    proc, outdir = _run_wd_child(procs, tmp_path, "hang_after_result", stdout=subprocess.PIPE)
    t0 = time.monotonic()
    code = proc.wait(timeout=20)
    elapsed = time.monotonic() - t0
    gp = json.loads((outdir / "gp.json").read_text())
    assert code == 124
    assert elapsed < 1 + 1 + 6, f"exit took {elapsed:.1f}s: budget 1 s + grace 1 s + slack"
    assert wait_gone(gp["gp"], 3), "the detached grandchild survived the watchdog"
    assert (outdir / "timeout.json").exists(), "the timeout marker is the authoritative record"
    assert not (outdir / "stamp.json").exists(), "a timeout never writes a stamp"
    assert not (outdir / "result.json").exists(), "C9-6: the watchdog deleted the result under the lock"
    lines = [json.loads(x) for x in proc.stdout.read().decode().splitlines() if x.strip()]
    assert {"unit": "u", "status": "timeout"} in lines
    proc.stdout.close()


def test_watchdog_timeout_line_is_nonblocking_when_stdout_is_full(ur, procs, tmp_path):
    """C10-3: the timeout line cannot stall the watchdog behind a full, unread pipe."""
    proc, outdir = _run_wd_child(procs, tmp_path, "hang_stdout_full", stdout=subprocess.PIPE)
    try:
        code = proc.wait(timeout=15)
    except subprocess.TimeoutExpired:
        pytest.fail("the watchdog blocked writing its timeout line to a full stdout pipe")
    assert code == 124
    assert (outdir / "timeout.json").exists()
    proc.stdout.close()


def test_hang_after_the_stamp_still_exits_with_the_stamp_exit(ur, procs, tmp_path):
    """C9-1: an atexit handler that sleeps forever and a non-daemon thread that blocks
    forever must not matter, because only os._exit(stamp.exit) follows the commit.
    """
    proc, outdir = _run_wd_child(procs, tmp_path, "stamp_os_exit")
    t0 = time.monotonic()
    code = proc.wait(timeout=20)
    assert code == 3
    assert time.monotonic() - t0 < 1 + 1 + 6
    assert json.loads((outdir / "committed.json").read_text()) is True
    assert (outdir / "stamp.json").exists()
    assert not (outdir / "timeout.json").exists(), "a committed unit must not time out"


def test_negative_control_sys_exit_after_the_stamp_does_hang(ur, procs, tmp_path):
    """The hang-after-stamp case above would pass vacuously if its atexit handler and
    thread did not actually hang an ordinary exit. This is that check: it must hang.
    """
    proc, outdir = _run_wd_child(procs, tmp_path, "stamp_sys_exit")
    with pytest.raises(subprocess.TimeoutExpired):
        proc.wait(timeout=4)
    assert (outdir / "stamp.json").exists(), "control: the stamp was committed before the hang"
    assert proc.poll() is None, "control: the process is still alive, hung after its stamp"


class _Recorder:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.exited = threading.Event()

    def exit_fn(self, code: int) -> None:
        self.calls.append(("exit", code))
        self.exited.set()

    def kill_fn(self, *args) -> None:
        self.calls.append(("kill", *args))


def _watchdog(ur, budget, rec, on_expire=None, **kwargs):
    return ur.Watchdog(
        budget, on_expire, token="tok", grace_s=0, exit_fn=rec.exit_fn, kill_fn=rec.kill_fn, **kwargs
    )


def test_watchdog_expiry_kills_its_own_descendants_then_exits_124(ur):
    rec = _Recorder()
    expired = []
    wd = _watchdog(ur, 0.2, rec, on_expire=lambda: expired.append(1))
    try:
        assert rec.exited.wait(3), "the watchdog never fired"
    finally:
        wd.disarm()
    assert expired == [1]
    kills = [c for c in rec.calls if c[0] == "kill"]
    assert len(kills) == 1 and kills[0][1] == os.getpid() and kills[0][2] == "tok"
    assert rec.calls[-1] == ("exit", 124), "kill_tree runs first, os._exit(124) last"


def test_watchdog_commit_owns_the_lock_so_a_concurrent_expiry_does_nothing(ur, tmp_path):
    rec = _Recorder()
    expired = []
    wd = _watchdog(ur, 0.2, rec, on_expire=lambda: expired.append(1))
    stamp = tmp_path / "stamp.json"

    def slow_stamp():
        time.sleep(0.7)  # the timer fires (0.2 s) while the stamp is being written
        stamp.write_text("{}")

    assert wd.commit(slow_stamp) is True
    time.sleep(0.6)
    assert stamp.exists()
    assert expired == [] and rec.calls == [], "expiry acted after a stamp was committed"


def test_watchdog_commit_and_write_result_are_refused_once_fired(ur, tmp_path):
    rec = _Recorder()
    wd = _watchdog(ur, 0.2, rec)
    assert rec.exited.wait(3)
    wrote = []
    assert wd.commit(lambda: wrote.append("stamp")) is False
    assert wd.write_result(lambda: wrote.append("result")) is False
    assert wrote == [], "a refused write must not run its writer"


def test_watchdog_write_result_runs_under_the_lock_and_is_deleted_by_a_later_expiry(ur, tmp_path):
    """C10-2: a result write in flight when the budget expires completes first, and the
    expiry's on_expire then deletes it, so 'no result after a timeout' is guaranteed.
    """
    rec = _Recorder()
    result = tmp_path / "result.json"

    def on_expire():
        result.unlink(missing_ok=True)

    wd = _watchdog(ur, 0.2, rec, on_expire=on_expire)

    def slow_result():
        time.sleep(0.7)
        result.write_text('{"ok": true}')

    try:
        assert wd.write_result(slow_result) is True
        assert rec.exited.wait(3)
    finally:
        wd.disarm()
    assert not result.exists(), "the result written under the lock survived the expiry"
    assert [c for c in rec.calls if c[0] == "exit"] == [("exit", 124)]


def test_watchdog_a_raising_on_expire_still_kills_and_exits(ur):
    rec = _Recorder()

    def boom():
        raise RuntimeError("marker write failed")

    wd = _watchdog(ur, 0.2, rec, on_expire=boom)
    try:
        assert rec.exited.wait(3), "an on_expire exception must not strand the watchdog"
    finally:
        wd.disarm()
    assert [c[0] for c in rec.calls] == ["kill", "exit"]


def test_watchdog_lock_is_released_before_the_kill(ur):
    """kill_tree runs after the lock is released, so a unit thread finishing its commit
    at that instant is refused rather than deadlocked.
    """
    rec = _Recorder()
    results: list[bool] = []
    box: dict = {}

    def kill_fn(*args):
        t = threading.Thread(target=lambda: results.append(box["wd"].commit(lambda: None)))
        t.start()
        t.join(2)
        results.append(t.is_alive())
        rec.kill_fn(*args)

    wd = ur.Watchdog(0.2, None, token="tok", grace_s=0, exit_fn=rec.exit_fn, kill_fn=kill_fn)
    box["wd"] = wd
    assert rec.exited.wait(5)
    assert results == [False, False], "commit was not refused promptly (deadlock or accepted)"


def test_watchdog_requires_the_token_to_be_in_the_environment(ur, monkeypatch):
    monkeypatch.delenv(TOKEN_ENV, raising=False)
    rec = _Recorder()
    with pytest.raises(RuntimeError, match="ensure_token"):
        ur.Watchdog(30, None, exit_fn=rec.exit_fn, kill_fn=rec.kill_fn)
    monkeypatch.setenv(TOKEN_ENV, "from-env")
    wd = ur.Watchdog(30, None, exit_fn=rec.exit_fn, kill_fn=rec.kill_fn)
    try:
        assert wd.token == "from-env"
    finally:
        wd.disarm()


def test_emit_line_never_blocks_on_a_full_pipe_and_restores_blocking_mode(ur):
    r, w = os.pipe()
    try:
        os.set_blocking(w, False)
        try:
            while True:
                os.write(w, b"x" * 4096)
        except BlockingIOError:
            pass
        os.set_blocking(w, True)
        t0 = time.monotonic()
        ur.emit_line("dropped", fd=w)
        assert time.monotonic() - t0 < 1.0, "emit_line blocked on a full pipe"
        assert os.get_blocking(w) is True, "the fd's blocking mode was not restored"
        os.set_blocking(r, False)
        try:
            while os.read(r, 1 << 20):
                pass
        except BlockingIOError:
            pass
        ur.emit_line("kept", fd=w)
        assert os.read(r, 100).endswith(b"kept\n")
    finally:
        os.close(r)
        os.close(w)


# --------------------------------------------------------------------------- #
# --reap
# --------------------------------------------------------------------------- #


def _reap(args: list[str], *, ci: bool) -> subprocess.CompletedProcess:
    env = {k: v for k, v in os.environ.items() if k != "CI"}
    if ci:
        env["CI"] = "1"
    return subprocess.run(
        [sys.executable, str(RUNNER_PATH), "--reap", *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )


def test_reap_refuses_without_ci_or_force_and_signals_nothing(ur, procs):
    token = uuid.uuid4().hex
    orphan = procs.sleeper(token=token)
    for args in ([], ["--token", token]):
        result = _reap(args, ci=False)
        assert result.returncode == 2, result.stderr
        assert is_running(orphan.pid) and proc_state(orphan.pid) != "T", "a refused --reap signalled"


@pytest.mark.parametrize("mode", ["ci", "force"])
def test_reap_kills_the_token_carrying_orphan_and_nothing_else(ur, procs, mode):
    token = uuid.uuid4().hex
    orphan = procs.sleeper(token=token)
    tokenless = procs.sleeper()
    other_token = procs.sleeper(token=uuid.uuid4().hex)
    args = ["--token", token] + (["--force"] if mode == "force" else [])
    result = _reap(args, ci=(mode == "ci"))
    assert result.returncode == 0, result.stderr
    assert wait_gone(orphan.pid, 5), "--reap left the token-carrying orphan alive"
    assert is_running(tokenless.pid) and proc_state(tokenless.pid) != "T"
    assert is_running(other_token.pid), "--token must restrict the reap to that token"


def test_reap_function_runs_kill_tree_once_per_token_found(ur, procs):
    """The unrestricted CLI form kills every token on the box, so its logic is checked
    in-process over an injected pid universe instead.
    """
    tok_a, tok_b = uuid.uuid4().hex, uuid.uuid4().hex
    a, b = procs.sleeper(token=tok_a), procs.sleeper(token=tok_b)
    tokenless = procs.sleeper()
    stray = procs.sleeper(token=uuid.uuid4().hex)  # a token, but outside the injected universe

    found = ur.reap(pid_lister=lambda: [a.pid, b.pid, tokenless.pid], grace_s=1)

    assert set(found) == {tok_a, tok_b}
    assert wait_gone(a.pid, 3) and wait_gone(b.pid, 3)
    assert is_running(tokenless.pid) and is_running(stray.pid)


# --------------------------------------------------------------------------- #
# write_atomic / dist_hash / driver_input
# --------------------------------------------------------------------------- #


def test_write_atomic_writes_fsyncs_replaces_and_leaves_no_temp_file(ur, tmp_path, monkeypatch):
    target = tmp_path / "out" / "result.json"
    target.parent.mkdir()
    target.write_bytes(b"old")
    synced: list[bool] = []  # one entry per fsync: was the fd a regular file?
    real_fsync = os.fsync
    monkeypatch.setattr(
        os,
        "fsync",
        lambda fd: (synced.append(stat.S_ISREG(os.fstat(fd).st_mode)), real_fsync(fd))[1],
    )
    ur.write_atomic(target, b"new-bytes")
    assert target.read_bytes() == b"new-bytes"
    assert any(synced), "the file itself was never fsynced before the rename"
    assert [p.name for p in target.parent.iterdir()] == ["result.json"], "temp file left behind"


def test_write_atomic_failure_keeps_the_old_file_and_cleans_up(ur, tmp_path, monkeypatch):
    target = tmp_path / "result.json"
    target.write_bytes(b"old")

    def boom(src, dst):
        raise OSError("disk on fire")

    monkeypatch.setattr(os, "replace", boom)
    with pytest.raises(OSError, match="disk on fire"):
        ur.write_atomic(target, b"new")
    monkeypatch.undo()
    assert target.read_bytes() == b"old", "a failed write must never expose partial content"
    assert [p.name for p in tmp_path.iterdir()] == ["result.json"]


def _expected_dist_hash(root: Path) -> str:
    lines = sorted(
        (p.relative_to(root).as_posix(), hashlib.sha256(p.read_bytes()).hexdigest())
        for p in root.rglob("*")
        if p.is_file()
    )
    return hashlib.sha256("".join(f"{rel}\t{sha}\n" for rel, sha in lines).encode()).hexdigest()


def test_dist_hash_is_the_sha256_of_sorted_path_tab_sha256_lines(ur, tmp_path):
    root = tmp_path / "dist"
    (root / "assets" / "deep").mkdir(parents=True)
    (root / "b.txt").write_bytes(b"bee")
    (root / "a.txt").write_bytes(b"ay")
    (root / "assets" / "deep" / "c.js").write_bytes(b"see")
    base = ur.dist_hash(root)
    assert base == _expected_dist_hash(root)

    os.utime(root / "a.txt", (1, 1))
    assert ur.dist_hash(root) == base, "mtime must not matter"
    (root / "a.txt").write_bytes(b"ay!")
    changed = ur.dist_hash(root)
    assert changed != base, "a content change must change the hash"
    (root / "a.txt").write_bytes(b"ay")
    (root / "a.txt").rename(root / "z.txt")
    assert ur.dist_hash(root) not in (base, changed), "a rename must change the hash"
    (root / "z.txt").rename(root / "a.txt")
    (root / "extra.txt").write_bytes(b"")
    assert ur.dist_hash(root) != base, "an added file must change the hash"


def test_dist_hash_of_an_empty_directory_is_the_hash_of_nothing(ur, tmp_path):
    (tmp_path / "empty").mkdir()
    assert ur.dist_hash(tmp_path / "empty") == hashlib.sha256(b"").hexdigest()


def test_driver_input_changes_with_the_playwright_version_and_with_uv_lock(ur):
    def expected(version: str, lock: bytes) -> str:
        inner = f"{version}\n{hashlib.sha256(lock).hexdigest()}"
        return hashlib.sha256(inner.encode()).hexdigest()

    base = ur.driver_input(playwright_version="1.60.0", uv_lock_bytes=b"lock-v1")
    assert base == expected("1.60.0", b"lock-v1")
    assert ur.driver_input(playwright_version="1.60.0", uv_lock_bytes=b"lock-v1") == base
    assert ur.driver_input(playwright_version="1.61.0", uv_lock_bytes=b"lock-v1") != base
    assert ur.driver_input(playwright_version="1.60.0", uv_lock_bytes=b"lock-v2") != base


def test_driver_input_defaults_read_the_installed_playwright_and_the_repo_uv_lock(ur):
    pytest.importorskip("playwright")
    if not (REPO_ROOT / "uv.lock").is_file():
        pytest.skip("uv.lock is gitignored and absent in this checkout")
    value = ur.driver_input()
    assert re.fullmatch(r"[0-9a-f]{64}", value)


# --------------------------------------------------------------------------- #
# a browser tree under run_unit: scaffolding (local, stub) and real Chromium (CI only)
# --------------------------------------------------------------------------- #


def _browser_tree_case(
    ur,
    procs: Procs,
    tmp_path: Path,
    child_body: str,
    *,
    comm_pattern: str,
    timeout_s: float,
    ready_wait_s: float,
    extra_env: dict[str, str] | None = None,
) -> dict:
    """A child launches a browser-like tree and then hangs.

    Positive control (C10-1), BEFORE the timeout: a live process whose comm/exe matches
    ``comm_pattern`` carries the unit's token and sits in a process group different from
    the child's. Only then is the post-timeout assertion meaningful: a runner that kills
    nothing, or a browser that never started, cannot pass.
    """
    ready, childpid = tmp_path / "ready", tmp_path / "childpid"
    script = procs.script("browser_child.py", child_body)
    box: dict = {}
    env = procs.env(**(extra_env or {}))

    def target() -> None:
        box["outcome"] = ur.run_unit(
            [sys.executable, str(script), str(ready), str(childpid)], timeout_s, env=env, cwd=None
        )

    runner = threading.Thread(target=target, daemon=True)
    runner.start()
    try:
        procs.wait_file(ready, timeout=ready_wait_s)
        child = int(childpid.read_text())
        token = token_of(child)
        assert token, "control: the unit's token is not in the child's /proc/<pid>/environ"
        browsers = [
            p
            for p in procs_with_token(token)
            if re.search(comm_pattern, comm_of(p)) or re.search(comm_pattern, exe_basename(p))
        ]
        assert browsers, "control: no browser process carries the unit's token before the timeout"
        child_pgrp = _stat(child)["pgrp"]
        assert any(
            _stat(p) and _stat(p)["pgrp"] != child_pgrp for p in browsers
        ), "control: the browser is not in its own process group (the detached case)"
    finally:
        runner.join(timeout=timeout_s + 30)
    assert not runner.is_alive(), "run_unit never returned"

    outcome = box["outcome"]
    assert outcome.timed_out and outcome.killed
    for pid in browsers:
        assert wait_gone(pid, 8), f"browser process {pid} ({comm_of(pid)}) survived run_unit's timeout"
    deadline = time.monotonic() + 8
    survivors = [p for p in procs_with_token(token) if is_running(p)]
    while survivors and time.monotonic() < deadline:
        time.sleep(0.1)
        survivors = [p for p in procs_with_token(token) if is_running(p)]
    assert survivors == [], f"processes still carrying the unit token after the grace: {survivors}"
    return {"token": token, "browsers": browsers, "child": child}


_STUB_BODY = """
import shutil
stub = os.path.join(os.path.dirname(sys.argv[1]), "chrome-stub")
if not os.path.exists(stub):
    os.symlink(shutil.which("sleep"), stub)
subprocess.Popen([stub, "120"], start_new_session=True)
time.sleep(0.5)
put(sys.argv[2], str(os.getpid()))
put(sys.argv[1], "1")
time.sleep(120)
"""

_STUB_BODY_NO_BROWSER = """
put(sys.argv[2], str(os.getpid()))
put(sys.argv[1], "1")
time.sleep(120)
"""


def test_browser_case_scaffolding_with_a_stub_tree(ur, procs, tmp_path):
    """Runs the CI-only case's scaffolding locally, with a `chrome-stub` process standing
    in for Chromium, so the real-Chromium case is not the first run of its own harness.
    """
    info = _browser_tree_case(
        ur, procs, tmp_path, _STUB_BODY, comm_pattern=r"chrom", timeout_s=4, ready_wait_s=3.5
    )
    assert info["browsers"]


def test_browser_case_positive_control_fails_when_no_browser_process_exists(ur, procs, tmp_path):
    """Negative control for the scaffolding: with no browser-like process the positive
    control must fail, so a run that starts no browser cannot pass.
    """
    with pytest.raises(AssertionError, match="control: no browser process"):
        _browser_tree_case(
            ur, procs, tmp_path, _STUB_BODY_NO_BROWSER, comm_pattern=r"chrom", timeout_s=4, ready_wait_s=3.5
        )


_CHROMIUM_BODY = """
from playwright.sync_api import sync_playwright
pw = sync_playwright().start()
browser = pw.chromium.launch(
    executable_path=os.environ["UR_CHROME"],
    headless=True,
    args=json.loads(os.environ["UR_CHROME_ARGS"]),
)
page = browser.new_page()
page.goto("about:blank")
put(sys.argv[2], str(os.getpid()))
put(sys.argv[1], "1")
time.sleep(600)
"""


@pytest.mark.skipif(
    not os.environ.get("CI"),
    reason="C9-5: real Chromium runs in CI only, never locally (local compute rule)",
)
def test_real_chromium_under_run_unit_leaves_no_process_carrying_the_token(ur, procs, tmp_path):
    """CI only. Fails, never skips, if Chromium cannot be resolved (C9-5). Playwright
    launches Chromium detached, so this is the case the whole runner exists for.
    """
    spec = importlib.util.spec_from_file_location("repl_smoke_for_unit_runner", REPL_SMOKE_PATH)
    assert spec is not None and spec.loader is not None
    smoke = importlib.util.module_from_spec(spec)
    sys.modules["repl_smoke_for_unit_runner"] = smoke
    spec.loader.exec_module(smoke)
    try:
        chrome = smoke.resolve_chrome_path()
    except FileNotFoundError as exc:
        pytest.fail(f"CI must have Chromium (playwright install chromium): {exc}")

    _browser_tree_case(
        ur,
        procs,
        tmp_path,
        _CHROMIUM_BODY,
        comm_pattern=r"chrom|headless",
        timeout_s=30,
        ready_wait_s=26,
        extra_env={
            "UR_CHROME": str(chrome),
            "UR_CHROME_ARGS": json.dumps(smoke.chromium_launch_args(offline=False)),
        },
    )
