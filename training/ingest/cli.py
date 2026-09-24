"""Shared CLI plumbing for the ingest pipeline.

This module defines the exception hierarchy and the custom argument parser that ensures
usage errors exit 64 (EX_USAGE) rather than 2, preventing confusion with verdict codes.

§7.1's hierarchy table is the normative specification of all error classes. cli.py imports
NOTHING from this package — not just no command module, but no sibling ingest module at all.
This prevents circular imports when command modules import cli for EXIT_* and run().
"""

import argparse
import sys
from typing import Any, Final, NoReturn, Sequence

# Exit codes — the eight decision codes (0–7) plus the non-decision code 64 (EX_USAGE).
# §9 and rev 6 (R5-W2): only 64 is not a gate decision.
EXIT_OK: Final[int] = 0  # Proceed
EXIT_MEASUREMENT_ERROR: Final[int] = 1  # Measurement or input error
EXIT_UNADJUDICATED_BLOCKING: Final[int] = 2  # Unadjudicated blocking finding
EXIT_STOP_LICENSING: Final[int] = 3  # STOP: licensing gate failed
EXIT_STOP_COVERAGE: Final[int] = 4  # STOP: coverage gate failed
EXIT_INCONCLUSIVE: Final[int] = 5  # Inconclusive — measurement could not be taken
EXIT_EVAL_LEAK: Final[int] = 6  # Eval leak or lineage-contract violation
EXIT_CONTESTED: Final[int] = 7  # CONTESTED: two readings disagree
EXIT_USAGE: Final[int] = 64  # Malformed command line (EX_USAGE from sysexits.h)


# The exception hierarchy — defined once, in this file, and never redeclared.
# §7.1's hierarchy table is the normative specification. Rev 7 (C1) and rev 8 (C6):
# cli.py imports NOTHING from this package to prevent circular imports.

class IngestError(Exception):
    """Base exception for all ingest pipeline errors. Maps to exit 1."""

    pass


class CookbookUnavailable(IngestError):
    """The cookbook clone is absent or at the wrong commit. Maps to exit 5."""

    pass


class UsageError(IngestError):
    """A malformed command line. NOT a measurement, NOT a verdict. Maps to exit 64."""

    pass


class IngestArgumentParser(argparse.ArgumentParser):
    """Custom argument parser that raises UsageError instead of calling sys.exit(2).

    This ensures usage errors (missing required args, typos, unrecognized args)
    exit 64 (EX_USAGE) rather than 2, preventing confusion with the gate verdict
    for "unadjudicated blocking finding".

    §7.1 (rev 6, R5-W2) and rev 8 (C3): enforces --out for specific emitter flags
    via the out_required_for parameter.
    """

    def __init__(
        self, *args: Any, out_required_for: Sequence[str] = (), **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self._out_required_for = tuple(out_required_for)

    def error(self, message: str) -> NoReturn:
        """Override to raise UsageError instead of calling sys.exit(2).

        This is argparse's only error funnel.
        """
        raise UsageError(f"{self.prog}: {message}\n\n{self.format_usage()}")

    def parse_args(self, args: Any = None, namespace: Any = None) -> Any:
        """Parse args and enforce --out requirement for emitter flags.

        Signature mirrors argparse.ArgumentParser.parse_args exactly (rev 7, C3):
        do not rename args to argv, as argparse itself calls parse_args(args=..., ...)
        by keyword internally.
        """
        ns = super().parse_args(args, namespace)
        for dest in self._out_required_for:
            if getattr(ns, dest, False) and getattr(ns, "out", None) is None:
                self.error(f"--out is required with --{dest.replace('_', '-')}")
        return ns


def run(handler: Any, parser: IngestArgumentParser, argv: Sequence[str] | None = None) -> int:
    """Execute a command handler with exception mapping.

    Maps exceptions to exit codes:
      - CookbookUnavailable → 5 (checked FIRST, as it's a subclass of IngestError)
      - UsageError → 64 (caught before handler is invoked)
      - Any other IngestError → 1

    Args:
        handler: A callable that takes parsed args and returns an int (exit code).
        parser: An IngestArgumentParser instance.
        argv: Command-line arguments (None = sys.argv[1:]).

    Returns:
        Exit code (0–7, or 64 for usage errors).
    """
    try:
        args = parser.parse_args(argv)
    except UsageError as exc:
        print(exc, file=sys.stderr)
        return EXIT_USAGE

    try:
        return handler(args)
    except CookbookUnavailable as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_INCONCLUSIVE
    except IngestError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return EXIT_MEASUREMENT_ERROR
