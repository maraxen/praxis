"""Entry point for 'python -m ingest' — a signpost, not a dispatcher.

This module prints usage instructions and exits. It does NOT import or dispatch to
any of the five command modules (licenses, recipes, eval_split, audit, gap).

§7.1 (rev 5, R4-B2) and rev 6 (R5-W3): there is no central dispatcher, only module-per-command.
Each command is invoked as `python -m ingest.{module}` with its own argument parser.
"""

import sys


def main() -> int:
    """Print usage and exit.

    Returns 0 for --help or no arguments.
    Returns 1 for any other invocation (unrecognized command).
    """
    # Check argv
    if len(sys.argv) == 1:
        # No arguments — print signpost
        print("Coxswain corpus ingest pipeline", file=sys.stdout)
        print("", file=sys.stdout)
        print("Usage: python -m ingest.<module> [options]", file=sys.stdout)
        print("", file=sys.stdout)
        print("Modules:", file=sys.stdout)
        print("  licenses    License scanning and descend-rule verification", file=sys.stdout)
        print("  recipes     Recipe extraction and token classification", file=sys.stdout)
        print("  eval_split  Eval split commitment and leak verification", file=sys.stdout)
        print("  audit       Drift audit and canonical table verification", file=sys.stdout)
        print("  gap         Coverage-gap analysis", file=sys.stdout)
        print("", file=sys.stdout)
        print("No dispatcher: each module is independent. Use --help with any module for details.", file=sys.stdout)
        return 0

    if len(sys.argv) == 2 and sys.argv[1] in ("--help", "-h"):
        # Help flag
        print("Coxswain corpus ingest pipeline", file=sys.stdout)
        print("", file=sys.stdout)
        print("Usage: python -m ingest.<module> [options]", file=sys.stdout)
        print("", file=sys.stdout)
        print("Modules:", file=sys.stdout)
        print("  licenses    License scanning and descend-rule verification", file=sys.stdout)
        print("  recipes     Recipe extraction and token classification", file=sys.stdout)
        print("  eval_split  Eval split commitment and leak verification", file=sys.stdout)
        print("  audit       Drift audit and canonical table verification", file=sys.stdout)
        print("  gap         Coverage-gap analysis", file=sys.stdout)
        print("", file=sys.stdout)
        print("No dispatcher: each module is independent. Use --help with any module for details.", file=sys.stdout)
        return 0

    # Any other invocation (e.g., 'python -m ingest licenses' without a flag)
    # is an error. Print the correct form and exit 1.
    first_arg = sys.argv[1]
    print(
        f"Error: unrecognized argument '{first_arg}'",
        file=sys.stderr,
    )
    print("", file=sys.stderr)
    print("Did you mean: python -m ingest.{module} [options]?", file=sys.stderr)
    print("", file=sys.stderr)
    print("Modules: licenses, recipes, eval_split, audit, gap", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
