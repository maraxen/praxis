"""Eval split management and leak detection for the ingest pipeline.

This module provides:
- The split rule (§4.2): per-chapter stratified holdout with seedless determinism
- Authority and change control (§4.4): seven assertions that guard the committed split
- The leak gate (§4.5): three-rule detector that catches unattributable material

Key design points:
- The split is committed as data, never recomputed (PM-4, §4.1–4.2)
- Assertions 0–5 guard the data file against drift; assertion 6 runs everywhere (no clone needed)
- EvalSplitLeak is NOT a subclass of cli.IngestError (§4.5) — it maps to exit 6 via a handler
- The leak gate runs in Task 8; Task 4 owns the gate infrastructure and the exit-6 test
"""

import hashlib
import json
import sys
from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_EVEN
from pathlib import Path
from typing import Any, Final, Iterable, Mapping, Sequence, Tuple

from . import cli, io, recipes, sources

__all__ = [
    "EvalSplitLeak",
    "is_held_out",
    "check_corpus_for_leak",
    "assert_no_leak",
    "load_sidecar_rows",
    "compute_split",
    "SIDECAR_RELPATH",
    "default_sidecar_path",
]


# ============================================================================
# Constants
# ============================================================================

EVAL_SPLIT_VERSION: Final[str] = "1"
SIDECAR_RELPATH: Final[str] = "training/assemble/out/corpus_p25_sidecar.jsonl"


# ============================================================================
# Exception class — deliberately NOT a subclass of cli.IngestError
# ============================================================================


class EvalSplitLeak(RuntimeError):
    """Raised when check_corpus_for_leak finds a violation.

    This is the ONE error class in the package that deliberately does NOT
    subclass cli.IngestError. The --check-leak handler catches this and
    returns 6 (§4.5, C1, rev 8). If it escapes uncaught, the interpreter
    exits 1, which would mask a real leak as a measurement error (G5).
    """

    pass


# ============================================================================
# Path resolution
# ============================================================================


def default_sidecar_path() -> Path:
    """Derive the default sidecar path from the project root.

    Mirrors recipes.py's default_recipes_path() pattern (§4.5).

    Returns:
        Path to the sidecar file.

    Raises:
        cli.IngestError: If the sidecar does not exist.
    """
    path = Path.cwd() / SIDECAR_RELPATH
    if not path.exists():
        raise cli.IngestError(f"Sidecar not found: {path}")
    return path


# ============================================================================
# Sidecar reader
# ============================================================================


def load_sidecar_rows(path: Path) -> Tuple[Mapping[str, Any], ...]:
    """Read a JSONL sidecar into a tuple of row mappings, in file order.

    A missing, unreadable or unparseable sidecar is a MEASUREMENT error, never
    a leak: it raises cli.IngestError (the root class itself, because eval_split.py
    declares no subclass of it per §7.1's table) which cli.run maps to exit 1.
    It must NEVER raise EvalSplitLeak: 6 means "a leak was found", and a file
    that could not be read found nothing (§4.5, rev 8).

    Args:
        path: Path to the sidecar JSONL file.

    Returns:
        Tuple of row mappings in file order.

    Raises:
        cli.IngestError: If the file is missing, unreadable, or contains invalid JSON.
    """
    path = Path(path)
    if not path.exists():
        raise cli.IngestError(f"Sidecar not found: {path}")

    rows = []
    try:
        with open(path) as f:
            for line_no, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    row = json.loads(line)
                    rows.append(row)
                except json.JSONDecodeError as e:
                    raise cli.IngestError(
                        f"Sidecar parse error at line {line_no}: {e}"
                    ) from e
    except (IOError, OSError) as e:
        raise cli.IngestError(f"Could not read sidecar: {e}") from e

    return tuple(rows)


# ============================================================================
# Split rule computation
# ============================================================================


def _round_half_even(n: float) -> int:
    """Round to nearest integer, ties to even (banker's rounding).

    §4.2 specifies round_half_even(0.20 * n_c).
    """
    d = Decimal(str(n))
    rounded = d.quantize(Decimal("1"), rounding=ROUND_HALF_EVEN)
    return int(rounded)


def compute_split(recipes_list: Sequence[recipes.Recipe]) -> Tuple[str, ...]:
    """Compute the eval split held-out paths for a given recipe list.

    The split rule (§4.2):
      For each chapter c with n_c recipes:
        n_held(c) = 0                                    if n_c < 3
                  = max(1, round_half_even(0.20 * n_c))  otherwise
      Within chapter c, sort recipes by (path, line_no) ascending;
      hold out the LAST n_held(c).

    Args:
        recipes_list: Sequence of Recipe objects.

    Returns:
        Tuple of held-out recipe paths (sorted).
    """
    # Group by chapter
    by_chapter: dict[int, list[recipes.Recipe]] = {}
    for rec in recipes_list:
        if rec.chapter not in by_chapter:
            by_chapter[rec.chapter] = []
        by_chapter[rec.chapter].append(rec)

    held_out = []
    for chapter in sorted(by_chapter.keys()):
        chapter_recipes = by_chapter[chapter]
        n_c = len(chapter_recipes)

        # Compute n_held for this chapter
        if n_c < 3:
            n_held = 0
        else:
            n_held = max(1, _round_half_even(0.20 * n_c))

        # Sort by (path, line_no) and hold out the LAST n_held
        sorted_recipes = sorted(chapter_recipes, key=lambda r: (r.path, r.line_no))
        for i, rec in enumerate(sorted_recipes):
            if i >= n_c - n_held:
                held_out.append(rec.path)

    return tuple(sorted(held_out))


# ============================================================================
# Leak detection
# ============================================================================


def is_held_out(recipe_path: str) -> bool:
    """Check if a recipe path is in the held-out set.

    Loads the eval_split.json file and checks held_out_ever (§4.5).

    Args:
        recipe_path: Path to check (e.g. "part1/01_robot_on_screen.qmd#setup").

    Returns:
        True if the path is in held_out_ever, False otherwise.
    """
    data_dir = Path(__file__).parent / "data"
    eval_split_path = data_dir / "eval_split.json"

    with open(eval_split_path) as f:
        data = json.load(f)

    return recipe_path in data.get("held_out_ever", [])


def check_corpus_for_leak(
    sidecar_rows: Iterable[Mapping[str, Any]],
) -> Tuple[str, ...]:
    """Check a sidecar for leaks and contract violations.

    FAIL-CLOSED: returns one message per leaking row; empty tuple => clean.

    Rule 1: a row whose lineage.source_id == "chory-lab__plr-cookbook" and
            which carries NO lineage.recipe_path is a leak.
    Rule 2: a row with split == "train" whose lineage.recipe_path is in
            held_out_ever is a leak.
    Rule 3 (W3): a row carrying any lineage key outside
            data/lineage_contract.json's known_keys | reserved_cookbook_keys
            is a CONTRACT VIOLATION, reported as a leak.

    Keying on held_out_ever rather than held_out_paths makes the monotonicity
    invariant (§4.4) load-bearing (§4.5).

    Args:
        sidecar_rows: Iterable of row mappings from the sidecar.

    Returns:
        Tuple of violation messages (empty if clean).
    """
    messages = []

    # Load the contract
    data_dir = Path(__file__).parent / "data"
    contract_path = data_dir / "lineage_contract.json"
    with open(contract_path) as f:
        contract = json.load(f)

    known_keys = set(contract.get("known_keys", []))
    reserved_keys = set(contract.get("reserved_cookbook_keys", []))
    allowed_keys = known_keys | reserved_keys

    # Load the held_out_ever set
    eval_split_path = data_dir / "eval_split.json"
    with open(eval_split_path) as f:
        eval_split = json.load(f)
    held_out_ever = set(eval_split.get("held_out_ever", []))

    for i, row in enumerate(sidecar_rows, start=1):
        lineage = row.get("lineage", {})

        # Rule 1: cookbook source without recipe_path
        source_id = lineage.get("source_id")
        recipe_path = lineage.get("recipe_path")
        if source_id == "chory-lab__plr-cookbook" and recipe_path is None:
            messages.append(
                f"Row {i}: cookbook lineage.source_id without lineage.recipe_path"
            )

        # Rule 2: train-split row on held-out path
        split = row.get("split")
        if split == "train" and recipe_path in held_out_ever:
            messages.append(
                f"Row {i}: split=train on held-out path {recipe_path}"
            )

        # Rule 3: undeclared lineage key
        for key in lineage.keys():
            if key not in allowed_keys:
                messages.append(
                    f"Row {i}: undeclared lineage key '{key}' (allowed: {sorted(allowed_keys)})"
                )

    return tuple(messages)


def assert_no_leak(sidecar_rows: Iterable[Mapping[str, Any]]) -> None:
    """Raise EvalSplitLeak if any leaks are found.

    Called by --check-leak (G5, §4.5).

    Args:
        sidecar_rows: Iterable of row mappings from the sidecar.

    Raises:
        EvalSplitLeak: If any violations are found.
    """
    # Convert to tuple in case it's an iterator
    rows = tuple(sidecar_rows) if not isinstance(sidecar_rows, tuple) else sidecar_rows

    messages = check_corpus_for_leak(rows)
    if messages:
        raise EvalSplitLeak("\n".join(messages))


# ============================================================================
# CLI subcommands
# ============================================================================


def _check_leak(args: Any) -> int:
    """Handler for --check-leak: load sidecar and verify no leaks.

    This is the normative code block (§4.5, rev 8, C1) that maps
    EvalSplitLeak to exit 6. The try/except is essential: without it,
    EvalSplitLeak escapes as an uncaught traceback (exit 1), silently
    breaking G5.

    Args:
        args: Parsed arguments (args.sidecar is the path).

    Returns:
        0 if clean, 6 if leak found.
    """
    rows = load_sidecar_rows(args.sidecar)
    try:
        assert_no_leak(rows)
    except EvalSplitLeak as exc:
        print(exc, file=sys.stderr)
        return 6
    return 0


def _emit(args: Any) -> int:
    """Handler for --emit: regenerate eval_split.json.

    Requires the cookbook clone to be present at the pinned HEAD.

    Args:
        args: Parsed arguments (args.out is the output directory).

    Returns:
        Exit code (0 on success).

    Raises:
        cli.CookbookUnavailable: If the clone is absent or at wrong HEAD.
        cli.IngestError: On other errors.
    """
    # Load the recipes (CookbookUnavailable if not present)
    try:
        recs = recipes.load_recipes()
    except recipes.CookbookUnavailable as e:
        raise cli.CookbookUnavailable(str(e)) from e

    # Verify the clone's HEAD
    cookbook_path = recipes.default_recipes_path().parent.parent
    head_sha = _resolve_git_head(cookbook_path)

    registry_row = sources.by_id("chory-lab__plr-cookbook")
    if head_sha != registry_row.pinned_sha:
        raise cli.CookbookUnavailable(
            f"Cookbook clone at {cookbook_path} has HEAD {head_sha}, "
            f"but registry pinned_sha is {registry_row.pinned_sha}. "
            f"This is an input change, not corruption. "
            f"Re-pin pinned_sha in sources.json with a recorded reason (§2.5), "
            f"then follow the re-split procedure."
        )

    # Compute the split
    held_out_paths = compute_split(recs)

    # Compute the recipes.yml SHA256
    recipes_path = recipes.default_recipes_path()
    with open(recipes_path, "rb") as f:
        recipes_sha = hashlib.sha256(f.read()).hexdigest()

    # Build the eval_split.json data
    eval_split_data = {
        "eval_split_version": EVAL_SPLIT_VERSION,
        "source_id": "chory-lab__plr-cookbook",
        "source_sha": registry_row.pinned_sha,
        "recipes_yml_sha256": recipes_sha,
        "rule": "per chapter: n_held = 0 if n < 3 else max(1, round_half_even(0.20*n)); within chapter sort by (path, line_no) asc, hold out the LAST n_held",
        "n_recipes": len(recs),
        "n_held_out": len(held_out_paths),
        "held_out_paths": sorted(held_out_paths),
        "held_out_extra": {},
        "held_out_ever": sorted(held_out_paths),
        "retired_paths": {},
    }

    io.write_artifact(Path(args.out), "eval_split.json", json.dumps(eval_split_data, indent=1, ensure_ascii=False))

    return 0


def _emit_lineage_contract(args: Any) -> int:
    """Handler for --emit-lineage-contract: compute and emit the contract.

    Reads the live sidecar to compute known_keys (the observed union of all
    lineage keys). This does NOT require the cookbook clone.

    Args:
        args: Parsed arguments (args.out is the output directory).

    Returns:
        Exit code (0 on success).

    Raises:
        cli.IngestError: On read/parse errors.
    """
    # Resolve the sidecar path (uses default if not provided)
    sidecar_path = default_sidecar_path()
    rows = load_sidecar_rows(sidecar_path)

    # Compute the union of all lineage keys
    known_keys = set()
    for row in rows:
        lineage = row.get("lineage", {})
        known_keys.update(lineage.keys())

    # Build the contract
    contract_data = {
        "lineage_contract_version": "1",
        "known_keys": sorted(known_keys),
        "reserved_cookbook_keys": ["source_id", "recipe_path"],
        "note": "Any lineage key outside these two sets fails G5. Adding a key is a reviewed diff to this file; that diff is the moment someone must decide whether the new field carries cookbook attribution.",
        "vocabulary_collisions": {
            "receiver_type": "The naturalness rows' lineage carries a key literally named receiver_type. It is UNRELATED to ingest.recipes.ReceiverType (§3.2), which is a closed enum over cookbook DOTTED receivers. Same word, different vocabularies, no conversion between them."
        },
    }

    io.write_artifact(Path(args.out), "lineage_contract.json", json.dumps(contract_data, indent=1, ensure_ascii=False))

    return 0


# ============================================================================
# Git helpers (no subprocess)
# ============================================================================


def _resolve_git_head(git_dir: Path) -> str:
    """Resolve the current HEAD SHA without using git command.

    Implements the chain from §4.4, assertion 0, rev 4: .git/HEAD → refs → packed-refs.
    Returns a 40-character hex SHA.

    Args:
        git_dir: Path to the repository root.

    Returns:
        The HEAD commit SHA (40 hex digits).

    Raises:
        cli.IngestError: If HEAD cannot be resolved.
    """
    git_path = git_dir / ".git"
    if not git_path.exists():
        raise cli.IngestError(f"Not a git repository: {git_dir}")

    head_file = git_path / "HEAD"
    if not head_file.exists():
        raise cli.IngestError(f"Missing .git/HEAD: {git_dir}")

    # Read HEAD file
    with open(head_file) as f:
        head_content = f.read().strip()

    # If it's a direct SHA, return it
    if len(head_content) == 40 and all(c in "0123456789abcdef" for c in head_content):
        return head_content

    # Otherwise, it's a symbolic ref like "ref: refs/heads/main"
    if head_content.startswith("ref: "):
        ref_path = head_content[5:]  # Remove "ref: " prefix
        return _resolve_ref(git_path, ref_path)

    raise cli.IngestError(f"Could not parse HEAD: {head_content}")


def _resolve_ref(git_path: Path, ref_path: str) -> str:
    """Resolve a ref (e.g. refs/heads/main) to a SHA.

    Tries loose ref first, then packed-refs (§4.4, rev 4).

    Args:
        git_path: Path to the .git directory.
        ref_path: The ref path (e.g. "refs/heads/main").

    Returns:
        The commit SHA (40 hex digits).

    Raises:
        cli.IngestError: If the ref cannot be resolved.
    """
    # Try loose ref first
    loose_ref = git_path / ref_path
    if loose_ref.exists():
        with open(loose_ref) as f:
            sha = f.read().strip()
            if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                return sha

    # Try packed-refs
    packed_refs = git_path / "packed-refs"
    if packed_refs.exists():
        with open(packed_refs) as f:
            for line in f:
                line = line.strip()
                if line.startswith("#"):
                    continue
                if not line:
                    continue
                parts = line.split()
                if len(parts) >= 2:
                    sha, ref = parts[0], parts[1]
                    if ref == ref_path:
                        if len(sha) == 40 and all(c in "0123456789abcdef" for c in sha):
                            return sha

    raise cli.IngestError(
        f"Could not resolve ref {ref_path} in {git_path}"
    )


# ============================================================================
# Main entry point
# ============================================================================


def _make_parser() -> cli.IngestArgumentParser:
    """Create and return the argument parser for the eval_split subcommand.

    Declares --check-leak, --emit, and --emit-lineage-contract as mutually
    exclusive, with --out required for --emit and --emit-lineage-contract.
    """
    parser = cli.IngestArgumentParser(
        prog="python -m ingest.eval_split",
        description="Eval split management and leak detection",
        out_required_for=("emit", "emit_lineage_contract"),
    )

    # Mutually exclusive: --check-leak, --emit, --emit-lineage-contract
    g = parser.add_mutually_exclusive_group(required=True)
    g.add_argument(
        "--check-leak",
        type=Path,
        dest="sidecar",
        metavar="SIDECAR",
        help="Check a sidecar for leaks (required argument: path)",
    )
    g.add_argument(
        "--emit",
        action="store_true",
        help="Regenerate eval_split.json (requires --out)",
    )
    g.add_argument(
        "--emit-lineage-contract",
        action="store_true",
        help="Emit lineage_contract.json (requires --out)",
    )

    parser.add_argument(
        "--out",
        type=Path,
        help="Output directory (required for --emit and --emit-lineage-contract)",
    )

    return parser


def _dispatch_handler(args: Any) -> int:
    """Dispatch to the appropriate subcommand based on parsed args."""
    if args.sidecar is not None:
        return _check_leak(args)
    elif args.emit:
        return _emit(args)
    elif args.emit_lineage_contract:
        return _emit_lineage_contract(args)
    else:
        # Should not reach here due to mutually_exclusive_group(required=True)
        return cli.EXIT_USAGE


if __name__ == "__main__":
    parser = _make_parser()
    sys.exit(cli.run(_dispatch_handler, parser))
