"""AC-6 tests for ``web-repl/scripts/check_gesture_invariant.py`` (D6, T5).

Seven negative fixtures, each written to its own ``tmp_path`` scan root so a
fixture's own violation is isolated from the others, must each exit nonzero.
One positive fixture -- a synchronous cached-state conditional before the
gesture call, the shape D6 explicitly allows -- must exit 0. A final test
proves the checker is clean over the REAL tree: at the time this task was
written ``core.js`` is already committed (with ``onProtectClick`` /
``onChooseFolderClick`` / ``onReconnectClick`` / ``onRestoreClick``), while
``panel.js`` is being written concurrently by another fixer task and may or
may not exist yet -- this test must pass in either state.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import check_gesture_invariant  # noqa: E402 -- path setup must precede this import


def _run(fixture_dir: Path) -> int:
    return check_gesture_invariant.main(["--root", str(fixture_dir)])


def _write(tmp_path: Path, name: str, source: str) -> Path:
    fixture_dir = tmp_path / name
    fixture_dir.mkdir()
    (fixture_dir / "sample.js").write_text(source)
    return fixture_dir


def test_negative_await_before_call(tmp_path: Path) -> None:
    """1: an `await` token between the function's opening brace and the
    gesture call must fail, even though the enclosing function is otherwise
    a correctly named, non-async, non-arrow on*Click function.
    """
    fixture = _write(
        tmp_path,
        "await_before",
        """
        function onProtectClick() {
          const ready = await checkReady();
          storage.persist();
        }
        """,
    )
    assert _run(fixture) != 0


def test_negative_async_function(tmp_path: Path) -> None:
    """2: an `async` function must fail even with nothing else between its
    brace and the call.
    """
    fixture = _write(
        tmp_path,
        "async_function",
        """
        async function onProtectClick() {
          storage.persist();
        }
        """,
    )
    assert _run(fixture) != 0


def test_negative_then_before_call(tmp_path: Path) -> None:
    """3: a `.then(` token before the call must fail."""
    fixture = _write(
        tmp_path,
        "then_before",
        """
        function onProtectClick() {
          somePromise.then(() => {});
          storage.persist();
        }
        """,
    )
    assert _run(fixture) != 0


def test_negative_arrow_function(tmp_path: Path) -> None:
    """4: an arrow function, even named on*Click via assignment, must fail
    -- D6 requires a named `function`/method, never an arrow.
    """
    fixture = _write(
        tmp_path,
        "arrow_function",
        """
        const onProtectClick = () => {
          storage.persist();
        };
        """,
    )
    assert _run(fixture) != 0


def test_negative_wrong_name(tmp_path: Path) -> None:
    """5: a plain, synchronous, non-arrow function whose name does not
    match `on[A-Z]\\w*Click` must fail.
    """
    fixture = _write(
        tmp_path,
        "wrong_name",
        """
        function protectClick() {
          storage.persist();
        }
        """,
    )
    assert _run(fixture) != 0


def test_negative_pick_directory_from_non_on_click(tmp_path: Path) -> None:
    """6: `pickDirectory(` called from a function that is not a named
    on*Click function must fail -- this is why `pickDirectory\\(` has to be
    in GESTURE_CALLS at all (Revision 1 A-3): leaving it out would make the
    checker falsely green here.
    """
    fixture = _write(
        tmp_path,
        "pick_directory_wrong_fn",
        """
        function helperChoose() {
          pickDirectory({ mode: "readwrite" });
        }
        """,
    )
    assert _run(fixture) != 0


def test_negative_forbidden_test_string(tmp_path: Path) -> None:
    """7 (B-11): the smoke-harness-only `__praxis_test_force_prompt` switch
    must never appear in scanned product code, even inside a comment or
    string, and even when the file's gesture call is otherwise correct.
    """
    fixture = _write(
        tmp_path,
        "forbidden_string",
        """
        // Smoke-only: localStorage["__praxis_test_force_prompt"] toggles the
        // forced-prompt path. It must never ship here (B-11).
        function onChooseFolderClick() {
          pickDirectory({ mode: "readwrite" });
        }
        """,
    )
    assert _run(fixture) != 0


def test_positive_cached_state_conditional(tmp_path: Path) -> None:
    """A synchronous conditional reading already-cached state, guarding the
    gesture call, is explicitly allowed by D6 and must pass.
    """
    fixture = _write(
        tmp_path,
        "cached_state_conditional",
        """
        function onReconnectClick() {
          if (cachedPermission !== "granted") {
            handle.requestPermission({ mode: "readwrite" });
          }
        }
        """,
    )
    assert _run(fixture) == 0


def test_real_tree_passes() -> None:
    """The checker must exit 0 over the real
    `web-repl/shell/persistence/*.js` tree, whether or not `panel.js` has
    landed yet from the concurrent T6 fixer task.
    """
    assert check_gesture_invariant.main([]) == 0
