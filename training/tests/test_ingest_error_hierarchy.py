"""§7.1's exception hierarchy table, checked not trusted (rev 7, C1).

The hierarchy is designed in §7.1 and stated as prose in five other sections;
nothing in the suite verified it until this file. Four assertions: three
import-time, one behavioural.
"""

from types import SimpleNamespace

import pytest

from ingest import audit, cli, eval_split, gap, io, recipes, sources

# ============================================================================
# 1. Parametrized over the five per-module classes: issubclass AND __module__
# ============================================================================

_HIERARCHY_TABLE = [
    (sources.RegistryError, "ingest.sources"),
    (recipes.RecipesError, "ingest.recipes"),
    (audit.AuditError, "ingest.audit"),
    (gap.GapError, "ingest.gap"),
    (io.ProtectedPathError, "ingest.io"),
]


class TestPerModuleClasses:
    @pytest.mark.parametrize(
        "klass,expected_module",
        _HIERARCHY_TABLE,
        ids=[k.__name__ for k, _ in _HIERARCHY_TABLE],
    )
    def test_subclasses_ingest_error_and_lives_in_expected_module(self, klass, expected_module):
        assert issubclass(klass, cli.IngestError), (
            f"{klass.__name__} must subclass cli.IngestError"
        )
        assert klass.__module__ == expected_module, (
            f"{klass.__name__}.__module__ is {klass.__module__!r}, expected "
            f"{expected_module!r} -- declared in the wrong file"
        )


# ============================================================================
# 2. recipes.CookbookUnavailable IS cli.CookbookUnavailable (object identity)
# ============================================================================


class TestCookbookUnavailableIsReexported:
    def test_identity(self):
        """A redeclaration in recipes.py (`class CookbookUnavailable(RecipesError)`)
        satisfies every `from ingest.recipes import CookbookUnavailable` in the
        suite and fails only this -- which is why the assertion is `is`, not
        `issubclass`."""
        assert recipes.CookbookUnavailable is cli.CookbookUnavailable


# ============================================================================
# 3. EvalSplitLeak is the deliberate non-member
# ============================================================================


class TestEvalSplitLeakIsNotAMember:
    def test_not_a_subclass_of_ingest_error(self):
        """Without this, the 'consistent' edit (rebase EvalSplitLeak onto
        IngestError like the other five) would route a leak through cli.run's
        catch-all and turn G5's exit 6 into a 1, silently, with G5 still
        'passing' its own tests. This assertion is static; its behavioural
        half (a leaking fixture -> exactly 6) lives in Task 4's own test
        suite (test_ingest_eval_split.py)."""
        assert not issubclass(eval_split.EvalSplitLeak, cli.IngestError)
        assert issubclass(eval_split.EvalSplitLeak, RuntimeError)


# ============================================================================
# 4. ProtectedPathError -> 1, end-to-end through cli.run (behavioural)
# ============================================================================


class TestProtectedPathErrorEndToEnd:
    def test_write_to_protected_root_returns_1_through_cli_run(self, tmp_path):
        """A handler that calls io.write_artifact against a PROTECTED_ROOTS
        path, driven through cli.run, returns 1 rather than propagating an
        uncaught traceback -- which is what it did while the class was a bare
        RuntimeError."""

        def handler(args: SimpleNamespace) -> int:
            io.write_artifact(io.REPO_ROOT / "training/ingest/data", "should_not_write.json", "{}")
            return cli.EXIT_OK  # unreachable: write_artifact raises first

        parser = cli.IngestArgumentParser(prog="test-protected-path")
        code = cli.run(handler, parser, [])

        assert code == cli.EXIT_MEASUREMENT_ERROR
        # And the write genuinely did not happen.
        assert not (io.REPO_ROOT / "training/ingest/data/should_not_write.json").exists()
