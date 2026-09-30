#!/usr/bin/env python3
"""The shared unit runner: the ONE module that starts and kills harness/spike units.

Playwright launches Chromium with ``detached: true`` on Linux, so Chromium leads its
own process group. Killing a unit's process group therefore leaves a hung Chromium
alive, and so does a CI step timeout. Every unit kind (the ``repl_smoke.py`` harness
units, the D17 spike units and the D17 AC-39 negative units) starts and kills units
through this module, so the three cannot diverge. Nothing else in the repo may kill
a unit process.

Design: ``.praxia/docs/specs/260929_notebook-display-epic.md``, D16 "Shared unit
runner" (Revisions 8 and 9) and the round-10 convergence notes C10-1..C10-4.

Public surface:

* :func:`kill_tree`     descendant walk + ``PRAXIS_UNIT_TOKEN`` environ sweep, to a
                        fixpoint, freezing what it finds; pid-reuse guard; group signals
                        only with a verified live member; ``SIGCONT`` in a ``finally``.
* :func:`run_unit`      fresh token into the child's environment at exec, own session,
                        ``kill_tree`` on expiry.
* :func:`ensure_token`  re-exec (from ``sys.orig_argv``) so the token is in
                        ``/proc/self/environ``.
* :class:`Watchdog`     daemon timer that owns the stamp lock (``commit``,
                        ``write_result``); exits 124 on expiry.
* :func:`emit_line`     non-blocking one-line write (C10-3).
* :func:`write_atomic`, :func:`dist_hash`, :func:`driver_input`.
* CLI ``--reap``        ``kill_tree`` per token found; refuses without ``CI`` or ``--force``.

Bounded teardown order for a unit that uses this module (D16, C9-1), all inside the
watchdog-bounded region::

    ensure_token(); wd = Watchdog(budget, on_expire)      # first acts
    ... clear own files, do the work ...
    wd.write_result(lambda: write_atomic(result, ...))    # 1. result/artifact
    browser.close(); playwright.stop()                    # 2. close (log, don't raise)
    kill_tree(os.getpid(), token)                         # 3. residual descendants
    flush stdout/stderr/logging                           # 4.
    if wd.commit(lambda: write_atomic(stamp, ...)):       # 5. the stamp, last
        os._exit(stamp_exit)                              #    only os._exit follows

Stdlib only, no repo imports, loadable by path (``importlib.util.spec_from_file_location``).
Linux only: it relies on ``/proc``.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import logging
import os
import signal
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Callable, Iterable, Sequence
from pathlib import Path
from typing import NamedTuple

LOG = logging.getLogger("unit_runner")

TOKEN_ENV = "PRAXIS_UNIT_TOKEN"
DEFAULT_GRACE_S = 5.0
#: How long kill_tree waits, after SIGKILL, for its victims to leave /proc (or turn zombie).
_POST_KILL_WAIT_S = 1.5
#: Exit status of a unit stopped by its own watchdog (coreutils ``timeout`` convention).
TIMEOUT_EXIT = 124

_POLL_S = 0.05


# --------------------------------------------------------------------------- #
# /proc readers (the default implementations of kill_tree's injectable seams)
# --------------------------------------------------------------------------- #


class ProcStat(NamedTuple):
    """The fields of ``/proc/<pid>/stat`` the runner needs."""

    state: str
    ppid: int
    pgrp: int
    starttime: int  # field 22, in clock ticks since boot: identifies a process incarnation


def read_proc_stat(pid: int) -> ProcStat | None:
    """Parse ``/proc/<pid>/stat``; ``None`` if the process is gone or unreadable.

    ``comm`` (field 2) may contain spaces and parentheses, so the fields after it are
    split from the LAST ``)``.
    """
    try:
        raw = Path(f"/proc/{pid}/stat").read_text()
    except OSError:  # FileNotFoundError, ProcessLookupError (ESRCH mid-read), PermissionError
        return None
    try:
        rest = raw.rsplit(")", 1)[1].split()
        return ProcStat(rest[0], int(rest[1]), int(rest[2]), int(rest[19]))
    except (IndexError, ValueError):
        return None


def read_environ(pid: int) -> bytes:
    """Raw ``/proc/<pid>/environ``; raises ``OSError`` subclasses for unreadable pids."""
    return Path(f"/proc/{pid}/environ").read_bytes()


def list_pids() -> list[int]:
    try:
        return [int(name) for name in os.listdir("/proc") if name.isdigit()]
    except OSError:
        return []


def read_children(pid: int) -> list[int]:
    """Direct children of every thread of ``pid`` (``/proc/<pid>/task/*/children``).

    Falls back to scanning ``/proc`` for ``ppid == pid`` on a kernel that does not
    expose the ``children`` files.
    """
    try:
        tids = os.listdir(f"/proc/{pid}/task")
    except OSError:
        return []
    kids: set[int] = set()
    have_children_file = False
    for tid in tids:
        try:
            text = Path(f"/proc/{pid}/task/{tid}/children").read_text()
        except OSError:
            continue
        have_children_file = True
        kids.update(int(tok) for tok in text.split())
    if not have_children_file:
        for candidate in list_pids():
            st = read_proc_stat(candidate)
            if st is not None and st.ppid == pid:
                kids.add(candidate)
    return sorted(kids)


def _protected() -> tuple[set[int], set[int]]:
    """The caller and its ancestors, and their process groups: never signalled."""
    pids: set[int] = set()
    pgrps: set[int] = set()
    pid = os.getpid()
    while pid > 1 and pid not in pids:
        pids.add(pid)
        st = read_proc_stat(pid)
        if st is None:
            break
        pgrps.add(st.pgrp)
        pid = st.ppid
    try:
        pgrps.add(os.getpgrp())
    except OSError:  # pragma: no cover
        pass
    return pids, pgrps


# --------------------------------------------------------------------------- #
# kill_tree
# --------------------------------------------------------------------------- #


class _Member:
    """A process the killer has collected and can prove is still the same process."""

    __slots__ = ("pgid", "pid", "pidfd", "starttime", "stopped")

    def __init__(self, pid: int, starttime: int, pgid: int, pidfd: int | None) -> None:
        self.pid = pid
        self.starttime = starttime
        self.pgid = pgid
        self.pidfd = pidfd
        self.stopped = False


class _TreeKiller:
    def __init__(
        self,
        root_pid: int | None,
        token: str,
        grace_s: float,
        *,
        environ_reader: Callable[[int], bytes] | None,
        children_reader: Callable[[int], Iterable[int]] | None,
        stat_reader: Callable[[int], ProcStat | None] | None,
        pid_lister: Callable[[], Iterable[int]] | None,
        use_pidfd: bool,
    ) -> None:
        self.root = root_pid
        self.token = token
        self.grace_s = grace_s
        self.read_env = environ_reader or read_environ
        self.read_kids = children_reader or read_children
        self.stat = stat_reader or read_proc_stat
        self.list_pids = pid_lister or list_pids
        self.use_pidfd = (
            use_pidfd and hasattr(os, "pidfd_open") and hasattr(signal, "pidfd_send_signal")
        )
        self.needle = f"{TOKEN_ENV}={token}".encode()
        self.protected_pids, self.protected_pgrps = _protected()
        self.members: dict[int, _Member] = {}

    # -- liveness and signalling ------------------------------------------------

    def _live_stat(self, m: _Member) -> ProcStat | None:
        """The member's stat if it is verifiably the same, live process; else ``None``."""
        if m.pidfd is not None:
            try:
                signal.pidfd_send_signal(m.pidfd, 0)
            except ProcessLookupError:
                return None
            except OSError:
                pass
        st = self.stat(m.pid)
        if st is None or st.state in ("Z", "X"):
            return None
        if m.pidfd is None and st.starttime != m.starttime:
            return None  # the pid now belongs to a different process
        return st

    def _send(self, m: _Member, sig: int) -> bool:
        """Send ``sig`` to ``m`` only if it is still the process we collected."""
        if m.pidfd is not None:
            try:
                signal.pidfd_send_signal(m.pidfd, sig)
                return True
            except ProcessLookupError:
                return False
            except OSError as exc:
                LOG.warning("pidfd signal %s to %s failed: %s", sig, m.pid, exc)
                return False
        st = self.stat(m.pid)
        if st is None or st.starttime != m.starttime:
            return False
        try:
            os.kill(m.pid, sig)
            return True
        except ProcessLookupError:
            return False
        except PermissionError as exc:
            LOG.warning("signal %s to %s not permitted: %s", sig, m.pid, exc)
            return False

    def _stop(self, m: _Member) -> None:
        if self._send(m, signal.SIGSTOP):
            m.stopped = True

    def _group_has_live_member(self, pgid: int) -> bool:
        for m in self.members.values():
            if m.pgid == pgid:
                st = self._live_stat(m)
                if st is not None and st.pgrp == pgid:
                    return True
        return False

    # -- collection -------------------------------------------------------------

    def _register(self, pid: int) -> bool:
        if pid <= 1 or pid in self.members or pid in self.protected_pids:
            return False
        st = self.stat(pid)
        if st is None or st.state in ("Z", "X"):
            return False
        fd: int | None = None
        if self.use_pidfd:
            try:
                fd = os.pidfd_open(pid)
            except OSError:
                fd = None
            if fd is not None:
                again = self.stat(pid)
                if again is None or again.starttime != st.starttime:
                    os.close(fd)
                    return False
        m = _Member(pid, st.starttime, st.pgrp, fd)
        self.members[pid] = m
        self._stop(m)  # freeze at discovery: nothing forks or re-parents away mid-kill
        return True

    def _discover(self) -> None:
        """Walk descendants and sweep environs, repeated until neither finds a new pid."""
        while True:
            found = False
            if self.root is not None and self._register(self.root):
                found = True
            stack: list[int] = ([self.root] if self.root is not None else []) + list(self.members)
            visited: set[int] = set()
            while stack:
                pid = stack.pop()
                if pid in visited:
                    continue
                visited.add(pid)
                for child in self.read_kids(pid):
                    if self._register(child):
                        found = True
                    if child not in visited and child not in self.protected_pids:
                        stack.append(child)
            for pid in list(self.list_pids()):
                if pid in self.members or pid in self.protected_pids or pid <= 1:
                    continue
                try:
                    env = self.read_env(pid)
                except OSError:  # PermissionError, ProcessLookupError, FileNotFoundError, ...
                    continue
                if not env:  # kernel thread or zombie
                    continue
                if self.needle in env.split(b"\0") and self._register(pid):
                    found = True
            if not found:
                return

    # -- killing ----------------------------------------------------------------

    def _signal_groups(self, sig: int) -> None:
        for pgid in sorted({m.pgid for m in self.members.values()}):
            if pgid <= 1 or pgid in self.protected_pgrps:
                continue
            if not self._group_has_live_member(pgid):
                continue
            try:
                os.killpg(pgid, sig)
            except (ProcessLookupError, PermissionError) as exc:
                LOG.debug("killpg(%s, %s): %s", pgid, sig, exc)

    def _signal_members(self, sig: int) -> None:
        for m in list(self.members.values()):
            if self._live_stat(m) is not None:
                self._send(m, sig)

    def _continue_all(self) -> None:
        for m in self.members.values():
            if m.stopped:
                self._send(m, signal.SIGCONT)
                m.stopped = False

    def _freeze_all(self) -> None:
        for m in self.members.values():
            if self._live_stat(m) is not None:
                self._stop(m)

    def _alive_members(self) -> list[_Member]:
        return [m for m in self.members.values() if self._live_stat(m) is not None]

    def _wait(self, seconds: float) -> None:
        """Wait until every collected member is gone, or ``seconds`` elapse."""
        deadline = time.monotonic() + seconds
        while time.monotonic() < deadline and self._alive_members():
            time.sleep(_POLL_S)

    def run(self) -> list[int]:
        try:
            self._discover()
            # SIGTERM first; a stopped process only acts on it once continued, so SIGCONT
            # follows so that handlers run (they may fork: the fixpoint below catches that).
            self._signal_groups(signal.SIGTERM)
            self._signal_members(signal.SIGTERM)
            self._continue_all()
            self._wait(self.grace_s)
            self._freeze_all()
            self._discover()
            self._signal_groups(signal.SIGKILL)
            self._signal_members(signal.SIGKILL)
            self._wait(_POST_KILL_WAIT_S)
            survivors = sorted(m.pid for m in self._alive_members())
            for pid in survivors:
                LOG.error("kill_tree: pid %s (token %s) survived SIGKILL", pid, self.token)
            return survivors
        finally:
            self._release()

    def _release(self) -> None:
        """SIGCONT everything this call stopped, then drop the pidfds. Never raises."""
        for m in self.members.values():
            if m.stopped:
                try:
                    self._send(m, signal.SIGCONT)
                except Exception:
                    LOG.exception("kill_tree: SIGCONT to %s failed", m.pid)
                m.stopped = False
        for m in self.members.values():
            if m.pidfd is not None:
                try:
                    os.close(m.pidfd)
                except OSError:
                    pass
                m.pidfd = None


def kill_tree(
    root_pid: int | None,
    token: str,
    grace_s: float = DEFAULT_GRACE_S,
    *,
    environ_reader: Callable[[int], bytes] | None = None,
    children_reader: Callable[[int], Iterable[int]] | None = None,
    stat_reader: Callable[[int], ProcStat | None] | None = None,
    pid_lister: Callable[[], Iterable[int]] | None = None,
    use_pidfd: bool = True,
) -> list[int]:
    """Kill ``root_pid``'s descendants and every process carrying ``token``.

    1. Collect to a fixpoint: walk ``/proc/<pid>/task/*/children`` from ``root_pid`` and
       from every pid collected so far, and sweep ``/proc/*/environ`` for the exact
       NUL-delimited entry ``PRAXIS_UNIT_TOKEN=<token>`` (a re-parented ``setsid`` orphan,
       and anything it forked). Each new pid is ``SIGSTOP``ped when found. A pid whose
       environ is unreadable, gone or empty is skipped.
    2. Pid-reuse guard: each pid is recorded with its ``/proc/<pid>/stat`` starttime, and
       with a pidfd where ``os.pidfd_open`` works (every later signal then goes through
       ``signal.pidfd_send_signal``); otherwise the starttime is re-read immediately
       before each signal.
    3. Group signals (``os.killpg``) go only to a group with at least one verified live
       member, and never to the caller's group or an ancestor's.
    4. ``SIGTERM``, then ``SIGCONT`` so a stopped process can act on it; after ``grace_s``
       freeze again, repeat step 1 (catching a child forked during the grace), then
       ``SIGKILL``.

    Everything runs in a ``try`` whose ``finally`` sends ``SIGCONT`` to whatever it still
    holds stopped, so an exception or Ctrl-C mid-walk never leaves a process in state T.
    Never signals the caller, its ancestors or its process group. ``root_pid=None`` means
    "sweep only" (what ``--reap`` uses). Returns the pids that survived (logged with
    ``logging.error``; none is expected).

    The keyword-only readers exist so the fault cases (unreadable environ, pid reuse, an
    interrupted walk) can be provoked deterministically; the defaults read ``/proc``.
    """
    return _TreeKiller(
        root_pid,
        token,
        grace_s,
        environ_reader=environ_reader,
        children_reader=children_reader,
        stat_reader=stat_reader,
        pid_lister=pid_lister,
        use_pidfd=use_pidfd,
    ).run()


# --------------------------------------------------------------------------- #
# run_unit / ensure_token
# --------------------------------------------------------------------------- #


class UnitOutcome(NamedTuple):
    exit: int  # the child's return code (negative: killed by that signal)
    timed_out: bool  # the timeout expired
    killed: bool  # kill_tree ran


def run_unit(
    argv: Sequence[str],
    timeout_s: float,
    *,
    env: dict[str, str] | None = None,
    cwd: str | os.PathLike[str] | None = None,
    grace_s: float = DEFAULT_GRACE_S,
) -> UnitOutcome:
    """Run one unit as a subprocess bounded by ``timeout_s``.

    A fresh ``PRAXIS_UNIT_TOKEN`` (uuid4 hex) goes into the child's environment at exec,
    where it is visible in ``/proc/<pid>/environ`` (Playwright passes its environment on
    to its driver and to Chromium). The child leads its own session. On expiry (or on any
    exception in the caller, e.g. Ctrl-C) ``kill_tree`` removes the whole tree.
    """
    token = uuid.uuid4().hex
    child_env = dict(os.environ if env is None else env)
    child_env[TOKEN_ENV] = token
    proc = subprocess.Popen(list(argv), env=child_env, cwd=cwd, start_new_session=True)
    try:
        try:
            return UnitOutcome(proc.wait(timeout=timeout_s), False, False)
        except subprocess.TimeoutExpired:
            LOG.warning("unit %s exceeded %.1fs; killing its tree", list(argv), timeout_s)
            kill_tree(proc.pid, token, grace_s)
            return UnitOutcome(_reap_child(proc, grace_s), True, True)
    except BaseException:
        if proc.poll() is None:
            kill_tree(proc.pid, token, grace_s)
            _reap_child(proc, grace_s)
        raise


def _reap_child(proc: subprocess.Popen, grace_s: float) -> int:
    try:
        return proc.wait(timeout=grace_s + 5)
    except subprocess.TimeoutExpired:  # pragma: no cover -- kill_tree already SIGKILLed it
        proc.kill()
        return proc.wait()


def ensure_token() -> str:
    """Return this process's unit token, re-exec'ing to acquire one if it has none.

    A token assigned to ``os.environ`` after exec is invisible in ``/proc/self/environ``
    (the kernel keeps the original block), so the sweep could not see it. The re-exec
    puts it there. It uses ``sys.orig_argv`` so interpreter flags (``-O``, ``-X ...``)
    survive (C10-4). A no-op when the token is already set, as it is under ``run_unit``.
    """
    token = os.environ.get(TOKEN_ENV)
    if token:
        return token
    env = dict(os.environ)
    env[TOKEN_ENV] = uuid.uuid4().hex
    argv = list(getattr(sys, "orig_argv", None) or [sys.executable, *sys.argv])
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()
        except (OSError, ValueError):
            pass
    os.execve(sys.executable, argv, env)
    raise AssertionError("unreachable: os.execve returned")  # pragma: no cover


# --------------------------------------------------------------------------- #
# Watchdog / emit_line
# --------------------------------------------------------------------------- #


def emit_line(text: str, fd: int = 1) -> None:
    """Write one line without ever blocking (C10-3).

    A blocked stdout (a full, unread pipe) must not stall the watchdog: the write is
    non-blocking and an ``EAGAIN`` drops the line. The marker file is the authoritative
    record of a timeout; this line is informational. The fd's blocking mode is restored.
    """
    data = (text if text.endswith("\n") else text + "\n").encode()
    try:
        was_blocking = os.get_blocking(fd)
    except OSError:
        return
    try:
        os.set_blocking(fd, False)
        try:
            os.write(fd, data)
        except OSError:  # BlockingIOError (EAGAIN), BrokenPipeError, ...
            pass
    finally:
        try:
            os.set_blocking(fd, was_blocking)
        except OSError:
            pass


class Watchdog:
    """A daemon timer bounding one unit; it also owns the stamp lock.

    Construction arms it: a unit's entry point creates it as its FIRST act, right after
    :func:`ensure_token` and before deleting any file or launching anything (C9-4).

    * :meth:`write_result` and :meth:`commit` run their writer under the lock, and refuse
      (return ``False``, writer not called) once the watchdog has fired.
    * :meth:`commit` runs the stamp write under the lock, then disarms.
    * On expiry, under the same lock, the watchdog does nothing if a stamp was already
      committed. Otherwise it marks itself fired and calls ``on_expire`` (the unit's
      callback: delete the result if present, write the timeout marker, print the timeout
      line with :func:`emit_line`), releases the lock, runs ``kill_tree`` over its own
      descendants and ``os._exit(124)``.

    ``token`` defaults to ``$PRAXIS_UNIT_TOKEN`` and is required (``ensure_token()`` first).
    ``exit_fn`` and ``kill_fn`` default to ``os._exit`` and :func:`kill_tree`; they are
    injectable so the lock semantics can be tested in-process without exiting the tester.
    """

    def __init__(
        self,
        budget_s: float,
        on_expire: Callable[[], None] | None = None,
        *,
        token: str | None = None,
        grace_s: float = DEFAULT_GRACE_S,
        exit_fn: Callable[[int], object] | None = None,
        kill_fn: Callable[..., object] | None = None,
    ) -> None:
        resolved = token or os.environ.get(TOKEN_ENV)
        if not resolved:
            raise RuntimeError(
                f"{TOKEN_ENV} is not set: call unit_runner.ensure_token() before arming a Watchdog"
            )
        self.token = resolved
        self.budget_s = budget_s
        self.grace_s = grace_s
        self.started = time.time()
        self.fired = False
        self.committed = False
        self._on_expire = on_expire
        self._exit_fn = exit_fn or os._exit
        self._kill_fn = kill_fn or kill_tree
        self._disarmed = False
        self._lock = threading.Lock()
        self._timer = threading.Timer(budget_s, self._expire)
        self._timer.daemon = True
        self._timer.start()

    def disarm(self) -> None:
        """Stop the timer without committing (a unit abandoning itself, or a test)."""
        self._disarmed = True
        self._timer.cancel()

    def write_result(self, write: Callable[[], object]) -> bool:
        """Run the result/artifact writer under the lock. ``False`` if fired or committed."""
        with self._lock:
            if self.fired or self.committed:
                return False
            write()
            return True

    def commit(self, write_stamp: Callable[[], object]) -> bool:
        """Run the stamp rename under the lock, then disarm. ``False`` if already fired."""
        with self._lock:
            if self.fired:
                return False
            if self.committed:
                raise RuntimeError("Watchdog.commit called twice")
            write_stamp()
            self.committed = True
            self._timer.cancel()
            return True

    def _expire(self) -> None:
        with self._lock:
            if self.committed or self.fired or self._disarmed:
                return
            self.fired = True
            if self._on_expire is not None:
                try:
                    self._on_expire()
                except BaseException:
                    LOG.exception("watchdog on_expire callback raised")
        try:
            self._kill_fn(os.getpid(), self.token, self.grace_s)
        except BaseException:
            LOG.exception("watchdog kill_tree raised")
        self._exit_fn(TIMEOUT_EXIT)


# --------------------------------------------------------------------------- #
# write_atomic / dist_hash / driver_input
# --------------------------------------------------------------------------- #


def write_atomic(path: str | os.PathLike[str], data: bytes) -> None:
    """Temporary file in the same directory, fsync, rename; the temp file never survives."""
    target = Path(path)
    tmp = target.with_name(f".{target.name}.{os.getpid()}.{uuid.uuid4().hex[:8]}.tmp")
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    try:
        with os.fdopen(fd, "wb") as fh:
            fh.write(data)
            fh.flush()
            os.fsync(fh.fileno())
        os.replace(tmp, target)
    except BaseException:
        try:
            os.unlink(tmp)
        except FileNotFoundError:
            pass
        raise
    try:  # make the rename itself durable; best effort
        dir_fd = os.open(target.parent, os.O_RDONLY)
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
    except OSError:
        pass


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for block in iter(lambda: fh.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def dist_hash(directory: str | os.PathLike[str]) -> str:
    """The ``dist`` input: sha256 of the sorted ``path<TAB>sha256`` lines of every file.

    Paths are relative to ``directory``, posix-style, sorted; each line is terminated by
    ``\\n``. An empty directory hashes to sha256 of nothing; a missing one raises.
    """
    root = Path(directory)
    if not root.is_dir():
        raise FileNotFoundError(f"dist directory not found: {root}")
    lines = sorted(
        (p.relative_to(root).as_posix(), _sha256_file(p)) for p in root.rglob("*") if p.is_file()
    )
    return hashlib.sha256("".join(f"{rel}\t{sha}\n" for rel, sha in lines).encode()).hexdigest()


def driver_input(
    *, playwright_version: str | None = None, uv_lock_bytes: bytes | None = None
) -> str:
    """The ``driver`` input (C8-6): sha256 of ``<playwright version>\\n<sha256 of uv.lock>``.

    The version is read with ``importlib.metadata.version("playwright")`` (no subprocess)
    and ``uv.lock`` from the repo root, unless injected. A Playwright upgrade or any
    lockfile change therefore recomputes every unit. A missing ``uv.lock`` raises rather
    than hashing nothing, which would silently never invalidate.
    """
    if playwright_version is None:
        playwright_version = importlib.metadata.version("playwright")
    if uv_lock_bytes is None:
        uv_lock_bytes = (Path(__file__).resolve().parents[1] / "uv.lock").read_bytes()
    inner = f"{playwright_version}\n{hashlib.sha256(uv_lock_bytes).hexdigest()}"
    return hashlib.sha256(inner.encode()).hexdigest()


# --------------------------------------------------------------------------- #
# --reap
# --------------------------------------------------------------------------- #


def reap(
    *,
    only_tokens: Iterable[str] | None = None,
    grace_s: float = DEFAULT_GRACE_S,
    environ_reader: Callable[[int], bytes] | None = None,
    pid_lister: Callable[[], Iterable[int]] | None = None,
) -> list[str]:
    """``kill_tree`` (sweep only, no root) once per distinct token found.

    The caller and its ancestors are excluded from the census and never signalled.
    ``only_tokens`` restricts the reap to those tokens; ``pid_lister`` restricts the
    universe of processes considered (both exist so tests cannot touch other sessions).
    """
    read_env = environ_reader or read_environ
    lister = pid_lister or list_pids
    protected, _ = _protected()
    prefix = f"{TOKEN_ENV}=".encode()
    found: set[str] = set()
    for pid in list(lister()):
        if pid <= 1 or pid in protected:
            continue
        try:
            env = read_env(pid)
        except OSError:
            continue
        for entry in env.split(b"\0"):
            if entry.startswith(prefix):
                found.add(entry[len(prefix) :].decode(errors="replace"))
    tokens = sorted(found if only_tokens is None else found & set(only_tokens))
    for token in tokens:
        kill_tree(None, token, grace_s, environ_reader=environ_reader, pid_lister=pid_lister)
    return tokens


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Shared unit runner. The only CLI action is --reap: kill every unit "
        "process still carrying a PRAXIS_UNIT_TOKEN (CI's if: always() cleanup step)."
    )
    parser.add_argument("--reap", action="store_true", help="kill_tree once per token found")
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow --reap outside CI (it kills EVERY unit on the machine, other sessions' too)",
    )
    parser.add_argument(
        "--token",
        action="append",
        default=None,
        metavar="TOKEN",
        help="restrict --reap to this token (repeatable); default: every token found",
    )
    parser.add_argument("--grace-s", type=float, default=DEFAULT_GRACE_S)
    parser.add_argument("-v", "--verbose", action="store_true")
    args = parser.parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    if not args.reap:
        parser.print_usage(sys.stderr)
        LOG.error("nothing to do: pass --reap")
        return 2
    if not (os.environ.get("CI") or args.force):
        LOG.error(
            "refusing to --reap: CI is not set and --force was not given. --reap kills every "
            "unit process on this machine, including other sessions' units."
        )
        return 2
    tokens = reap(only_tokens=args.token, grace_s=args.grace_s)
    LOG.info("reaped %d token(s): %s", len(tokens), tokens)
    print(json.dumps({"reaped": tokens}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
