"""Recipe reader and API tokenizer for the PLR cookbook.

This module provides the line-oriented reader for recipes.yml (§3.1), the API
tokenizer with its closed classifier (§3.2), receiver classification (§3.3),
and two emitter subcommands.

Key design points:
- §3.1: hand-rolled reader (not PyYAML), validates path regex per recipe, handles
  #-at-line-start-only comments to preserve anchor fragments in paths.
- §3.2: five independent positive predicates for TokenKind, exactly one must match.
- §3.3: exact 31-receiver table, hand-authored values (not derived).
- CookbookUnavailable is imported from cli.py (re-export, no redeclaration).
"""

import json
import re
import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Final, Mapping, Sequence

from . import cli, io, sources

from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

# Re-export CookbookUnavailable (declared in cli.py, not here)
from .cli import CookbookUnavailable  # noqa: F401

__all__ = [
    "Recipe",
    "RecipesError",
    "CookbookUnavailable",
    "ReceiverType",
    "TokenKind",
    "ApiToken",
    "RECIPES_RELPATH",
    "default_recipes_path",
    "load_recipes",
    "split_apis",
    "classify_api_token",
    "method_shaped",
    "in_surface_verbs",
]


# ============================================================================
# Constants and paths
# ============================================================================

RECIPES_RELPATH: Final[str] = "cookbook/recipes.yml"

_PATH_REGEX: Final[re.Pattern] = re.compile(r"^[a-z0-9_/]+\.qmd#[a-z0-9-]+$")


# ============================================================================
# Exception class
# ============================================================================


class RecipesError(cli.IngestError):
    """Raised on parse errors in recipes.yml or API tokenization.

    Maps to exit 1 via cli.run(). This is the module's ONE declared error class.
    """

    pass


# ============================================================================
# Recipe dataclass
# ============================================================================


@dataclass(frozen=True)
class Recipe:
    """A single recipe from recipes.yml.

    Args:
        title: Tier-2 expression (display name). NEVER written to any output file.
        path: Tier-0 identifier (e.g. "part1/04_pipetting.qmd#mix").
        chapter: Int in 1..18.
        line_no: File line of this record's "- title:" line (sort key).
        apis_raw: Verbatim comma-separated string as authored.
        api_tokens: Parsed and classified API tokens.
    """

    title: str
    path: str
    chapter: int
    line_no: int
    apis_raw: str
    api_tokens: tuple["ApiToken", ...]


# ============================================================================
# Path resolution
# ============================================================================


def default_recipes_path() -> Path:
    """Derive the default recipes.yml path from the registry.

    This ensures the path is derived from sources.by_id() rather than
    hardcoded, so moving the clone is a one-field registry edit.

    Returns:
        Path to the recipes.yml file.

    Raises:
        RecipesError: If the registry entry is not found.
    """
    try:
        row = sources.by_id("chory-lab__plr-cookbook")
    except sources.RegistryError as e:
        raise RecipesError(f"Failed to resolve cookbook path: {e}") from e
    return Path(row.clone_path).expanduser() / RECIPES_RELPATH


# ============================================================================
# File reading (line-oriented, not PyYAML)
# ============================================================================


def load_recipes(path: Path | None = None) -> tuple[Recipe, ...]:
    """Load and parse recipes.yml with line-oriented reader.

    The reader enforces the grammar specified in §3.1: classifies every line,
    validates record shape, parses chapter as int in 1..18, validates paths
    against the anchor regex, unescapes quoted scalars, and reconciles line
    counts.

    No count invariant is enforced: this reader parses synthetic fixtures of
    any size as validly as the live 91-record file (rev 5, R4-B1).

    Args:
        path: Path to recipes.yml (default: derived from registry).

    Returns:
        Tuple of Recipe objects.

    Raises:
        CookbookUnavailable: If the file does not exist.
        RecipesError: On any parse failure.
    """
    if path is None:
        path = default_recipes_path()

    path = Path(path)

    # Check existence first
    if not path.exists():
        raise CookbookUnavailable(f"Cookbook not found: {path}")

    with open(path) as f:
        lines = f.readlines()

    # Parse the file
    recipes: list[Recipe] = []
    current_record: dict = {}
    n_comment_lines = 0
    n_blank_lines = 0
    n_record_lines = 0

    for line_no, raw_line in enumerate(lines, start=1):
        stripped = raw_line.rstrip("\n\r")

        # Classify: comment, blank, or content
        if stripped and stripped[0] == "#":
            # Comment line
            n_comment_lines += 1
            continue

        if not stripped or stripped.isspace():
            # Blank line
            n_blank_lines += 1
            continue

        # Content line: must match one of the record patterns
        if stripped.startswith("- title:"):
            # Start a new record
            if current_record:
                # Finalize the previous record
                recipes.append(_finalize_record(current_record))
            current_record = {"line_no": line_no}
            n_record_lines += 1

            # Parse the title
            title_part = stripped[8:].lstrip()
            current_record["title"] = _parse_scalar(title_part)

        elif stripped.startswith("  path:"):
            # Path field
            if not current_record:
                raise RecipesError(f"Line {line_no}: path field without record start")
            n_record_lines += 1

            path_part = stripped[7:].lstrip()
            path_val = _parse_scalar(path_part)

            # Validate path regex
            if not _PATH_REGEX.match(path_val):
                raise RecipesError(
                    f"Line {line_no}: path does not match regex: {path_val!r}"
                )

            current_record["path"] = path_val

        elif stripped.startswith("  chapter:"):
            # Chapter field
            if not current_record:
                raise RecipesError(f"Line {line_no}: chapter field without record start")
            n_record_lines += 1

            chapter_part = stripped[10:].lstrip()
            chapter_val = _parse_scalar(chapter_part)

            try:
                chapter_int = int(chapter_val)
            except ValueError:
                raise RecipesError(f"Line {line_no}: chapter is not an int: {chapter_val!r}")

            if not (1 <= chapter_int <= 18):
                raise RecipesError(
                    f"Line {line_no}: chapter must be in 1..18, got {chapter_int}"
                )

            current_record["chapter"] = chapter_int

        elif stripped.startswith("  apis:"):
            # APIs field
            if not current_record:
                raise RecipesError(f"Line {line_no}: apis field without record start")
            n_record_lines += 1

            apis_part = stripped[7:].lstrip()
            apis_val = _parse_scalar(apis_part)
            current_record["apis_raw"] = apis_val

        else:
            raise RecipesError(f"Line {line_no}: cannot classify line: {stripped!r}")

    # Finalize the last record if any
    if current_record:
        recipes.append(_finalize_record(current_record))

    # Reconciliation: verify line counts
    expected_total = n_comment_lines + n_blank_lines + n_record_lines
    if expected_total != len(lines):
        raise RecipesError(
            f"Line count mismatch: {expected_total} classified, {len(lines)} total"
        )

    return tuple(recipes)


def _parse_scalar(value_str: str) -> str:
    """Parse a YAML scalar (quoted or bare).

    Quoted: must start and end with "; unescapes \\ and \".
    Bare: verbatim with trailing whitespace stripped.
    """
    value_str = value_str.rstrip()

    if value_str.startswith('"') and value_str.endswith('"'):
        # Quoted scalar
        if len(value_str) < 2:
            raise RecipesError(f"Invalid quoted scalar: {value_str!r}")

        content = value_str[1:-1]

        # Unescape only \" and \\
        result = []
        i = 0
        while i < len(content):
            if content[i] == "\\":
                if i + 1 < len(content) and content[i + 1] in ('"', "\\"):
                    result.append(content[i + 1])
                    i += 2
                else:
                    result.append(content[i])
                    i += 1
            else:
                result.append(content[i])
                i += 1

        return "".join(result)
    else:
        # Bare scalar: trailing whitespace already stripped
        return value_str


def _finalize_record(record: dict) -> Recipe:
    """Finalize a parsed record into a Recipe object.

    Ensures all four required fields are present and parses APIs.
    """
    required = {"title", "path", "chapter", "apis_raw", "line_no"}
    if not required.issubset(set(record.keys())):
        missing = required - set(record.keys())
        raise RecipesError(f"Record at line {record.get('line_no', '?')}: missing {missing}")

    # Parse APIs
    apis_raw = record["apis_raw"]
    api_tokens_raw = split_apis(apis_raw, record["path"])
    api_tokens = tuple(classify_api_token(t) for t in api_tokens_raw)

    return Recipe(
        title=record["title"],
        path=record["path"],
        chapter=record["chapter"],
        line_no=record["line_no"],
        apis_raw=apis_raw,
        api_tokens=api_tokens,
    )


# ============================================================================
# API tokenization (§3.2)
# ============================================================================


class TokenKind(str, Enum):
    """API token classification (§3.2, C22).

    Five independent, positive predicates. Exactly one must match.
    """

    DOTTED = "dotted"  # lh.summary, STARBackend.aspirate
    IDENT = "ident"  # setup, mix, blow_out
    CLASSISH = "classish"  # LiquidHandler, Mix
    PROSE = "prose"  # "naming convention", "async with"
    OTHER = "other"  # cor_96_wellplate_360uL_Fb, __setitem__


# Regexes for tokenization
_WS = re.compile(r"\s")
_IDENT = re.compile(r"[a-z_][a-z0-9_]*")
_CLASSISH = re.compile(r"[A-Z][A-Za-z0-9]*")

# Other shapes (positive predicates, not complement-based)
_MIXED_SNAKE = re.compile(r"[a-z_][A-Za-z0-9_]*[A-Z][A-Za-z0-9_]*")
_UPPER_SNAKE = re.compile(r"[A-Z][A-Za-z0-9]*_[A-Za-z0-9_]*")
_DIGIT_LED = re.compile(r"[0-9][A-Za-z0-9_]*")
_PUNCT_TOKEN = re.compile(r"[^\s.]*[^\s.A-Za-z0-9_][^\s.]*")

_OTHER_SHAPES = (_MIXED_SNAKE, _UPPER_SNAKE, _DIGIT_LED, _PUNCT_TOKEN)

# Predicates (all must be positive and mutually exclusive)
_PREDICATES = {
    TokenKind.PROSE: lambda t: bool(_WS.search(t)),
    TokenKind.DOTTED: lambda t: "." in t and not _WS.search(t),
    TokenKind.IDENT: lambda t: bool(_IDENT.fullmatch(t)),
    TokenKind.CLASSISH: lambda t: bool(_CLASSISH.fullmatch(t)),
    TokenKind.OTHER: lambda t: (
        not _WS.search(t)
        and "." not in t
        and any(r.fullmatch(t) for r in _OTHER_SHAPES)
    ),
}


def split_apis(apis_raw: str, recipe_path: str) -> tuple[str, ...]:
    """Split and validate a comma-separated APIs string.

    An empty token (trailing or doubled comma) raises RecipesError with the
    recipe named, guarding against silent downstream failures.

    Args:
        apis_raw: Verbatim comma-separated string from the recipe.
        recipe_path: Recipe path, for error messages.

    Returns:
        Tuple of trimmed token strings.

    Raises:
        RecipesError: If any token is empty.
    """
    parts = [p.strip() for p in apis_raw.split(",")]
    if any(p == "" for p in parts):
        raise RecipesError(f"{recipe_path}: empty token in apis: {apis_raw!r}")
    return tuple(parts)


class ReceiverType(str, Enum):
    """Receiver type classification (§3.2, W4).

    CLOSED vocabulary. NONE is for tokens with no receiver (non-DOTTED).
    OTHER is for DOTTED tokens whose receiver is unmapped.
    """

    LIQUID_HANDLER = "liquid_handler"
    PLATE_READER = "plate_reader"
    HEATER_SHAKER = "heater_shaker"
    OTHER = "other"
    NONE = "none"


@dataclass(frozen=True)
class ApiToken:
    """A single API token extracted from an apis field.

    Args:
        raw: The original token string.
        kind: TokenKind classification.
        receiver: DOTTED only: everything before the last '.'; else None.
        receiver_type: ReceiverType (NONE if receiver is None).
        member: DOTTED -> after last '.'; IDENT/CLASSISH -> the token; else "".
    """

    raw: str
    kind: TokenKind
    receiver: str | None
    receiver_type: ReceiverType
    member: str


def classify_api_token(raw: str) -> ApiToken:
    """Classify an API token and extract receiver/member.

    Applies the five predicates in _PREDICATES; exactly one must match.

    Args:
        raw: The token string to classify.

    Returns:
        ApiToken with kind, receiver, receiver_type, and member set.

    Raises:
        RecipesError: If the token matches zero or >1 predicates.
    """
    t = raw.strip()
    hits = [k for k, p in _PREDICATES.items() if p(t)]

    if len(hits) != 1:
        raise RecipesError(f"token {t!r} matched {len(hits)} kinds: {hits}")

    kind = hits[0]
    receiver = None
    receiver_type = ReceiverType.NONE
    member = ""

    if kind == TokenKind.DOTTED:
        # Extract receiver (everything before last '.') and member (after)
        parts = t.rsplit(".", 1)
        receiver = parts[0]
        member = parts[1] if len(parts) > 1 else ""

        # Look up receiver type in aliases
        receiver_type = _lookup_receiver_type(receiver)

    elif kind == TokenKind.IDENT or kind == TokenKind.CLASSISH:
        member = t

    # (PROSE and OTHER have member = "")

    return ApiToken(
        raw=raw,
        kind=kind,
        receiver=receiver,
        receiver_type=receiver_type,
        member=member,
    )


def in_surface_verbs(recipe: Recipe) -> frozenset[str]:
    """The set of in-surface verbs a recipe's `apis` field names (§5.2, §6.4).

    `{t.member for t in recipe.api_tokens if method_shaped(t) and t.member in
    PHASE2_TOOL_NAMES}` — one definition, two callers: `ingest.audit`'s
    `param_candidate` cross-product (§5.2) needs the positive form (which verbs
    is this recipe in-surface for); `ingest.gap`'s T3 out-of-surface-anchor
    predicate (§6.4) asks whether that set is empty. Matching is over
    `ApiToken.member`, exact and case-sensitive, and only method-shaped tokens
    participate — CLASSISH/PROSE/OTHER tokens are never matched against
    PHASE2_TOOL_NAMES. A recipe can name two or more in-surface verbs
    (recipes.yml 207, 432, 452), which is why this returns a set rather than
    at most one verb.
    """
    return frozenset(
        t.member for t in recipe.api_tokens
        if method_shaped(t) and t.member in PHASE2_TOOL_NAMES
    )


def method_shaped(t: ApiToken) -> bool:
    """Check if an ApiToken is comparable to TOOL_SCHEMA methods.

    Returns True for IDENT tokens, or DOTTED tokens whose member is a
    lowercase identifier (matches [a-z_][a-z0-9_]*).

    Args:
        t: The ApiToken to check.

    Returns:
        True if the token looks method-shaped.
    """
    if t.kind == TokenKind.IDENT:
        return True

    if t.kind == TokenKind.DOTTED:
        return bool(re.fullmatch(r"[a-z_][a-z0-9_]*", t.member))

    return False


# ============================================================================
# Receiver classification (§3.3)
# ============================================================================


def load_receiver_aliases(path: Path | None = None) -> dict:
    """Load the receiver aliases map from JSON.

    Args:
        path: Path to receiver_aliases.json (default: ingest/data/receiver_aliases.json).

    Returns:
        Dict with 'receiver_aliases_version', 'default', and 'exact' keys.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the JSON is malformed.
    """
    if path is None:
        path = Path(__file__).parent / "data" / "receiver_aliases.json"

    with open(path) as f:
        return json.load(f)


_RECEIVER_ALIASES_CACHE: dict | None = None


def _lookup_receiver_type(receiver: str) -> ReceiverType:
    """Look up a receiver in the aliases map and return its type.

    An unmapped receiver defaults to 'other' and should emit an advisory
    'unmapped_receiver' finding (handled by audit.py in Task 5).

    Args:
        receiver: The receiver string from a DOTTED token.

    Returns:
        ReceiverType for this receiver.
    """
    global _RECEIVER_ALIASES_CACHE

    if _RECEIVER_ALIASES_CACHE is None:
        try:
            _RECEIVER_ALIASES_CACHE = load_receiver_aliases()
        except FileNotFoundError:
            # If the file doesn't exist, return other for all receivers
            return ReceiverType.OTHER

    exact_map = _RECEIVER_ALIASES_CACHE.get("exact", {})
    value = exact_map.get(receiver, _RECEIVER_ALIASES_CACHE.get("default", "other"))

    try:
        return ReceiverType(value)
    except ValueError:
        return ReceiverType.OTHER


# ============================================================================
# CLI subcommands and argument parsing
# ============================================================================


def _make_parser() -> cli.IngestArgumentParser:
    """Create and return the argument parser for the recipes subcommand.

    Declares --emit-histogram and --emit-receiver-alias-keys as mutually exclusive
    options, with --out required for both.
    """
    parser = cli.IngestArgumentParser(
        prog="python -m ingest.recipes",
        description="Recipe extraction and API tokenization for PLR cookbook",
        out_required_for=("emit_histogram", "emit_receiver_alias_keys"),
    )

    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--emit-histogram",
        action="store_true",
        help="Emit token histogram to --out directory",
    )
    group.add_argument(
        "--emit-receiver-alias-keys",
        action="store_true",
        help="Emit receiver alias keys proposal to --out directory",
    )

    parser.add_argument(
        "--out",
        type=str,
        help="Output directory for emitted files (required for emitters)",
    )

    return parser


def emit_histogram(args) -> int:
    """Emit token histogram to --out directory.

    Computes per-kind token counts over the default recipes.yml and writes
    to <out>/token_histogram.json. This is a merge-proposal-style emitter.
    """
    if args.out is None:
        return cli.EXIT_USAGE

    out_dir = Path(args.out)

    try:
        recipes = load_recipes()
    except CookbookUnavailable:
        return cli.EXIT_INCONCLUSIVE
    except RecipesError as e:
        print(f"Error: {e}", file=sys.stderr)
        return cli.EXIT_MEASUREMENT_ERROR

    # Compute histogram
    counts = {kind.value: 0 for kind in TokenKind}
    for recipe in recipes:
        for token in recipe.api_tokens:
            counts[token.kind.value] += 1

    histogram = {
        "token_histogram_version": "2",
        "n_recipes": len(recipes),
        "counts": counts,
    }

    io.write_artifact(out_dir, "token_histogram.json", json.dumps(histogram, indent=1, ensure_ascii=False))

    return cli.EXIT_OK


def emit_receiver_alias_keys(args) -> int:
    """Emit proposed receiver alias updates to --out directory.

    This is a merge-proposal-style emitter. It:
    - Reads the committed receiver_aliases.json (must exist)
    - Collects all DOTTED receivers from the cookbook
    - Preserves all liquid_handler values verbatim
    - Adds new receivers with value 'other' in 'needs_review'
    - Moves removed receivers into 'unused'

    If the clone is absent, exits 5 (EXIT_INCONCLUSIVE).
    If the clone is present but no committed file exists, exits 1 (EXIT_MEASUREMENT_ERROR).
    If clone is absent AND no file exists, exits 5 (clone check runs first).
    """
    if args.out is None:
        return cli.EXIT_USAGE

    out_dir = Path(args.out)

    # Try to load recipes (clone check runs first per R5-S3)
    try:
        recipes = load_recipes()
    except CookbookUnavailable:
        return cli.EXIT_INCONCLUSIVE
    except RecipesError as e:
        print(f"Error: {e}", file=sys.stderr)
        return cli.EXIT_MEASUREMENT_ERROR

    # Collect live DOTTED receivers
    live_receivers = set()
    for recipe in recipes:
        for token in recipe.api_tokens:
            if token.kind == TokenKind.DOTTED and token.receiver:
                live_receivers.add(token.receiver)

    # Try to load the committed receiver_aliases.json
    aliases_path = Path(__file__).parent / "data" / "receiver_aliases.json"

    if not aliases_path.exists():
        raise RecipesError(f"receiver_aliases.json not found: {aliases_path}")

    with open(aliases_path) as f:
        committed = json.load(f)

    committed_exact = committed.get("exact", {})
    committed_values = set(committed_exact.values())

    # Build the proposal
    new_exact = dict(committed_exact)  # Start with committed values

    needs_review = []
    unused = []

    # Add or identify new receivers
    for receiver in sorted(live_receivers):
        if receiver not in new_exact:
            needs_review.append(receiver)
            new_exact[receiver] = "other"

    # Identify unused receivers
    for receiver, value in sorted(committed_exact.items()):
        if receiver not in live_receivers:
            unused.append(receiver)

    # Build proposal document
    proposal = {
        "receiver_aliases_version": committed.get("receiver_aliases_version", "2"),
        "default": committed.get("default", "other"),
        "exact": new_exact,
    }

    if needs_review:
        proposal["needs_review"] = needs_review

    if unused:
        proposal["unused"] = unused

    io.write_artifact(out_dir, "receiver_aliases_proposal.json", json.dumps(proposal, indent=1, ensure_ascii=False))

    return cli.EXIT_OK


def _dispatch_handler(args) -> int:
    """Dispatch to the appropriate subcommand based on parsed args."""
    if args.emit_histogram:
        return emit_histogram(args)
    elif args.emit_receiver_alias_keys:
        return emit_receiver_alias_keys(args)
    else:
        # Should not reach here due to mutually_exclusive_group(required=True)
        return cli.EXIT_USAGE


if __name__ == "__main__":
    parser = _make_parser()
    sys.exit(cli.run(_dispatch_handler, parser))
