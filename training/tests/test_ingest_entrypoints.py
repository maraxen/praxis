"""The `if __name__ == "__main__":` guard, executed not assumed (R5-B1).

Every other test in this spec drives a handler in-process (§5.5's injection
note, §7.4, §7.5, Task 6's "every assertion drives audit.gate(...) in-process"),
which left the `if __name__ == "__main__": raise SystemExit(_main())` block as
the one link in the chain no test crossed. Omit it from a command module and
`python -m ingest.<module> --gate` imports the module, ignores the flag, and
exits 0 -- R4-B2's failure mode surviving inside R4-B2's own fix.

Two assertions, both in-process via `runpy` -- no subprocess, so F3 and §7.3
are untouched. `runpy` is banned INSIDE `training/ingest/` (§7.3(a)); this file
is `training/tests/**`, explicitly exempt.

Mechanics worth restating: `run_module(..., run_name="__main__")` re-executes
the module body in a fresh namespace, but the fresh copy re-imports its
siblings (e.g. `ingest.recipes`) from `sys.modules` -- so it SEES a monkeypatch
applied via `monkeypatch.setattr(recipes, "default_recipes_path", ...)`
(patching the module attribute), not a rebound local name the test imported.
"""

import runpy
import sys

import pytest

from ingest import cli, recipes

COMMAND_MODULES = ["licenses", "recipes", "eval_split", "audit", "gap"]


class TestNoArgsExitsUsage:
    """Every module's required mutually-exclusive group makes no-flags a usage
    error. A MISSING `if __name__ == "__main__":` guard raises NOTHING at all
    (`run_module` just returns a namespace) -- that DID NOT RAISE failure,
    naming the module, is exactly the historical bug this test exists to catch."""

    @pytest.mark.parametrize("module_name", COMMAND_MODULES)
    def test_no_args_exits_usage(self, module_name, monkeypatch):
        monkeypatch.setattr(sys, "argv", [f"ingest.{module_name}"])
        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module(f"ingest.{module_name}", run_name="__main__")
        assert exc_info.value.code == cli.EXIT_USAGE, (
            f"ingest.{module_name}: expected SystemExit({cli.EXIT_USAGE}) on "
            f"no-args invocation, got {exc_info.value.code!r}"
        )


class TestAuditGateEndToEnd:
    """AC-1.7's contract observed for the first time: with the cookbook clone
    absent, `python -m ingest.audit --gate` (driven via runpy, as a real
    command-line invocation would reach it) raises SystemExit(5) -- not 0
    (guard missing / wrong function wired), not 64 (guard wired to the wrong
    thing). audit --gate is the sharpest case because it is the only gate
    whose CLI form writes NO artifact, so nothing else would catch a missing
    guard incidentally."""

    def test_audit_gate_clone_absent_exits_5(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            recipes,
            "default_recipes_path",
            lambda: tmp_path / "no_such_clone" / "cookbook" / "recipes.yml",
        )
        monkeypatch.setattr(sys, "argv", ["ingest.audit", "--gate"])

        with pytest.raises(SystemExit) as exc_info:
            runpy.run_module("ingest.audit", run_name="__main__")

        assert exc_info.value.code == cli.EXIT_INCONCLUSIVE


class TestEveryModuleHasAMainGuard:
    """A companion sanity check, independent of the SystemExit-code assertion
    above: every command module's source literally contains an
    `if __name__ == "__main__":` block. This does not replace the runpy
    assertions (a guard that's present but wired wrong would still pass this
    one) -- it exists so a failure here points straight at "the guard is
    missing" rather than requiring a reader to interpret a DID NOT RAISE."""

    @pytest.mark.parametrize("module_name", COMMAND_MODULES)
    def test_module_has_main_guard(self, module_name):
        import importlib
        mod = importlib.import_module(f"ingest.{module_name}")
        source = open(mod.__file__).read()
        assert 'if __name__ == "__main__":' in source, (
            f"ingest.{module_name} has no `if __name__ == \"__main__\":` guard"
        )
