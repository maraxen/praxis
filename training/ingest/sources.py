"""Registry loading and invariant verification for the ingest pipeline.

The sources.json data file is the single source of truth for all 21 registry rows
(1 admitted cookbook + 20 pending/rejected repos). load_registry() enforces all
ten load-time invariants (I1–I10), raising RegistryError on violation.

§2.1–2.4 defines SourceRow, the three enums, and the invariants.
§7.1's hierarchy table: RegistryError is defined here but subclasses cli.IngestError,
which is imported to prevent circular imports.
"""

import json
import re
from dataclasses import dataclass
from datetime import datetime, date as dateclass
from enum import Enum
from pathlib import Path
from typing import Final, Mapping, Sequence, Tuple

from . import cli

# Enum classes (closed sets per spec)


class Genre(str, Enum):
    """Source genre — an EXPLANATION, never a score (TRIAGE-3)."""

    COOKBOOK = "cookbook"
    WET_LAB_PROTOCOL = "wet_lab_protocol"
    ORCHESTRATION_PLATFORM = "orchestration_platform"
    HARDWARE_BACKEND = "hardware_backend"
    LABWARE_DATA = "labware_data"
    PROTOCOL_FORMAT = "protocol_format"
    NOVELTY_DEMO = "novelty_demo"
    LLM_ADJACENT = "llm_adjacent"
    UNCLEAR = "unclear"


class ExtractorKind(str, Enum):
    """OBSERVED extractability, independent of admission (C17)."""

    RECIPES_YML = "recipes_yml"
    QMD = "qmd"
    NOTEBOOK = "notebook"
    PYTHON = "python"
    NONE = "none"


class AdmissionState(str, Enum):
    """The DECISION axis (C17) — reject-by-default is normative at Increment 1."""

    ADMITTED = "admitted"
    PENDING_RECON = "pending_recon"
    REJECTED_PERMANENT = "rejected_permanent"


# SourceRow dataclass


@dataclass(frozen=True)
class SourceRow:
    """A single registry row: metadata, admission decision, and tier ceilings.

    All fields are documented in §2.1. frozen=True enforces immutability.
    """

    source_id: str
    repo_url: str
    clone_path: str
    pinned_sha: str
    genre: Genre
    extractor_kind: ExtractorKind
    admission_state: AdmissionState
    admission_argument: str
    rejection_reason: str
    tier_ceiling: int
    tier_ceiling_reason: str
    license_scan_dirs: Tuple[str, ...] = ()
    stars: int = 0
    last_push: str = ""
    license_request_issue_url: str = ""
    license_request_due: str = ""
    license_request_due_extensions: Tuple[Mapping[str, str], ...] = ()
    notes: str = ""


# Exception class


class RegistryError(cli.IngestError):
    """Raised when sources.json violates a load-time invariant (I1–I10).

    Maps to exit 1 via cli.run(). Rev 7 (C1): this class is defined here and
    subclasses cli.IngestError, which is imported to prevent circular imports
    (cli.py imports nothing from this package).
    """

    pass


# Invariant constants (I6)

# The closed set of valid tier_ceiling_reason prefixes (I6)
CEILING_PREFIXES: Final[Tuple[str, ...]] = (
    "contamination:",
    "vendored:",
    "consent:",
    "stale:",
    "duplicate:",
)

# Word-boundary regex for license-related keywords in tier_ceiling_reason (I6)
# Matches word boundaries to avoid false positives like "mit" in "permit"
LICENSE_KEYWORDS_REGEX: Final[re.Pattern] = re.compile(
    r"\b(mit|bsd|gpl|agpl|lgpl|apache|spdx|copyleft|proprietary|unlicensed)\b",
    re.IGNORECASE,
)


def registry_path() -> Path:
    """Return the absolute path to sources.json."""
    return Path(__file__).parent / "data" / "sources.json"


def load_registry(path: Path | None = None) -> Tuple[SourceRow, ...]:
    """Load and validate the sources registry.

    Enforces all ten load-time invariants (I1–I10). Raises RegistryError on violation.

    Args:
        path: Path to sources.json (default: ingest/data/sources.json).

    Returns:
        A tuple of validated SourceRow objects.

    Raises:
        RegistryError: If any invariant is violated.
    """
    if path is None:
        path = registry_path()

    # Load JSON
    try:
        with open(path) as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        raise RegistryError(f"Failed to load registry: {e}") from e

    sources = data.get("sources", [])

    # I1: exactly 21 rows; source_id unique
    if len(sources) != 21:
        raise RegistryError(
            f"I1 violation: expected exactly 21 rows, got {len(sources)}"
        )

    seen_ids = set()
    for i, row_data in enumerate(sources):
        source_id = row_data.get("source_id")
        if source_id in seen_ids:
            raise RegistryError(
                f"I1 violation: duplicate source_id at row {i}: {source_id}"
            )
        seen_ids.add(source_id)

    rows = []
    for i, row_data in enumerate(sources):
        try:
            row = _validate_row(row_data, i)
            rows.append(row)
        except RegistryError:
            raise

    return tuple(rows)


def _validate_row(row_data: dict, row_index: int) -> SourceRow:
    """Validate a single row and convert to SourceRow.

    Raises RegistryError if any invariant is violated.
    """
    try:
        source_id = row_data["source_id"]
        repo_url = row_data["repo_url"]
        clone_path = row_data["clone_path"]
        pinned_sha = row_data["pinned_sha"]
        genre_str = row_data["genre"]
        extractor_kind_str = row_data["extractor_kind"]
        admission_state_str = row_data["admission_state"]
        admission_argument = row_data["admission_argument"]
        rejection_reason = row_data["rejection_reason"]
        tier_ceiling = row_data["tier_ceiling"]
        tier_ceiling_reason = row_data["tier_ceiling_reason"]
        license_scan_dirs = tuple(row_data.get("license_scan_dirs", []))
        stars = row_data.get("stars", 0)
        last_push = row_data.get("last_push", "")
        license_request_issue_url = row_data.get("license_request_issue_url", "")
        license_request_due = row_data.get("license_request_due", "")
        license_request_due_extensions = tuple(
            row_data.get("license_request_due_extensions", [])
        )
        notes = row_data.get("notes", "")
    except KeyError as e:
        raise RegistryError(
            f"Row {row_index} ({row_data.get('source_id', '?')}): missing field {e}"
        ) from e

    # I2: pinned_sha matches ^[0-9a-f]{40}$
    if not re.match(r"^[0-9a-f]{40}$", pinned_sha):
        raise RegistryError(
            f"I2 violation ({source_id}): invalid pinned_sha: {pinned_sha}"
        )

    # I3: clone_path starts with ~/projects/repos/ and resolves outside praxis repo root
    if not clone_path.startswith("~/projects/repos/"):
        raise RegistryError(
            f"I3 violation ({source_id}): clone_path must start with ~/projects/repos/: {clone_path}"
        )

    clone_path_resolved = Path(clone_path).expanduser().resolve()
    # The praxis repo root is the parent of training/ingest
    praxis_root = Path(__file__).parent.parent.parent.resolve()
    try:
        clone_path_resolved.relative_to(praxis_root)
        raise RegistryError(
            f"I3 violation ({source_id}): clone_path must be outside praxis repo: {clone_path}"
        )
    except ValueError:
        # Good — clone_path is outside praxis_root
        pass

    # Parse enums
    try:
        genre = Genre(genre_str)
    except ValueError:
        raise RegistryError(
            f"Row {row_index} ({source_id}): invalid genre: {genre_str}"
        ) from None

    try:
        extractor_kind = ExtractorKind(extractor_kind_str)
    except ValueError:
        raise RegistryError(
            f"Row {row_index} ({source_id}): invalid extractor_kind: {extractor_kind_str}"
        ) from None

    try:
        admission_state = AdmissionState(admission_state_str)
    except ValueError:
        raise RegistryError(
            f"Row {row_index} ({source_id}): invalid admission_state: {admission_state_str}"
        ) from None

    # I4: admission_state is ADMITTED ⟺ admission_argument != ""; != ADMITTED ⟺ rejection_reason != ""
    if admission_state == AdmissionState.ADMITTED:
        if not admission_argument:
            raise RegistryError(
                f"I4 violation ({source_id}): ADMITTED requires non-empty admission_argument"
            )
        if rejection_reason:
            raise RegistryError(
                f"I4 violation ({source_id}): ADMITTED requires empty rejection_reason"
            )
    else:
        if admission_argument:
            raise RegistryError(
                f"I4 violation ({source_id}): non-ADMITTED requires empty admission_argument"
            )
        if not rejection_reason:
            raise RegistryError(
                f"I4 violation ({source_id}): non-ADMITTED requires non-empty rejection_reason"
            )

    # I5: admission_state is ADMITTED ⇒ extractor_kind is not NONE
    if admission_state == AdmissionState.ADMITTED and extractor_kind == ExtractorKind.NONE:
        raise RegistryError(
            f"I5 violation ({source_id}): ADMITTED requires extractor_kind != NONE"
        )

    # I6: tier_ceiling in (0,1,2); if < 2, tier_ceiling_reason must start with valid prefix
    if tier_ceiling not in (0, 1, 2):
        raise RegistryError(
            f"I6 violation ({source_id}): tier_ceiling must be 0, 1, or 2, got {tier_ceiling}"
        )

    if tier_ceiling < 2:
        if not any(
            tier_ceiling_reason.startswith(prefix) for prefix in CEILING_PREFIXES
        ):
            raise RegistryError(
                f"I6 violation ({source_id}): tier_ceiling_reason must start with one of {CEILING_PREFIXES}"
            )
        # Check for license-related keywords (case-insensitive substring match on casefolded text)
        if "licen" in tier_ceiling_reason.casefold():
            raise RegistryError(
                f"I6 violation ({source_id}): tier_ceiling_reason contains 'licen' (license reasons belong on the license axis)"
            )
        # Check for word-boundary license keywords
        if LICENSE_KEYWORDS_REGEX.search(tier_ceiling_reason):
            raise RegistryError(
                f"I6 violation ({source_id}): tier_ceiling_reason contains license keywords (license reasons belong on the license axis)"
            )

    # I7: last_push parses as YYYY-MM-DD
    if last_push and not re.match(r"^\d{4}-\d{2}-\d{2}$", last_push):
        raise RegistryError(
            f"I7 violation ({source_id}): last_push must be YYYY-MM-DD, got: {last_push}"
        )

    # I8: cookbook row satisfies AC-1.12's live-deadline rule (if this is the cookbook)
    if source_id == "chory-lab__plr-cookbook":
        _validate_cookbook_deadline(source_id, license_request_due)

    # I9: every license_scan_dirs entry is a relative path with no .. segment
    for scan_dir in license_scan_dirs:
        if not scan_dir or scan_dir.startswith("/"):
            raise RegistryError(
                f"I9 violation ({source_id}): license_scan_dirs must be relative: {scan_dir}"
            )
        if ".." in Path(scan_dir).parts:
            raise RegistryError(
                f"I9 violation ({source_id}): license_scan_dirs must not contain ..: {scan_dir}"
            )

    # I10: license_request_due_extensions is append-only-shaped
    prev_to = None
    for ext in license_request_due_extensions:
        if not isinstance(ext, dict) or not all(k in ext for k in ("from", "to", "reason")):
            raise RegistryError(
                f"I10 violation ({source_id}): each extension must have from/to/reason"
            )
        try:
            from_date = datetime.strptime(ext["from"], "%Y-%m-%d").date()
            to_date = datetime.strptime(ext["to"], "%Y-%m-%d").date()
        except ValueError as e:
            raise RegistryError(
                f"I10 violation ({source_id}): invalid date format in extension: {e}"
            ) from e

        if to_date <= from_date:
            raise RegistryError(
                f"I10 violation ({source_id}): extension to-date must be > from-date"
            )

        delta = (to_date - from_date).days
        if delta > 30:
            raise RegistryError(
                f"I10 violation ({source_id}): extension delta must be ≤ 30 days, got {delta}"
            )

        if prev_to is not None and from_date < prev_to:
            raise RegistryError(
                f"I10 violation ({source_id}): extensions must be non-overlapping"
            )
        prev_to = to_date

    return SourceRow(
        source_id=source_id,
        repo_url=repo_url,
        clone_path=clone_path,
        pinned_sha=pinned_sha,
        genre=genre,
        extractor_kind=extractor_kind,
        admission_state=admission_state,
        admission_argument=admission_argument,
        rejection_reason=rejection_reason,
        tier_ceiling=tier_ceiling,
        tier_ceiling_reason=tier_ceiling_reason,
        license_scan_dirs=license_scan_dirs,
        stars=stars,
        last_push=last_push,
        license_request_issue_url=license_request_issue_url,
        license_request_due=license_request_due,
        license_request_due_extensions=license_request_due_extensions,
        notes=notes,
    )


def _validate_cookbook_deadline(source_id: str, license_request_due: str) -> None:
    """Validate the cookbook's license request due date (I8 / AC-1.12).

    The deadline must be in the future relative to today's date.
    """
    if not license_request_due:
        raise RegistryError(
            f"I8 violation ({source_id}): cookbook requires license_request_due"
        )

    try:
        due_date = datetime.strptime(license_request_due, "%Y-%m-%d").date()
    except ValueError as e:
        raise RegistryError(
            f"I8 violation ({source_id}): invalid license_request_due format: {e}"
        ) from e

    today = dateclass.today()
    if due_date <= today:
        raise RegistryError(
            f"I8 violation ({source_id}): license_request_due must be in the future (today: {today}, due: {due_date})"
        )


def by_id(source_id: str, registry: Tuple[SourceRow, ...] | None = None) -> SourceRow:
    """Look up a source by source_id.

    Args:
        source_id: The source_id to look up.
        registry: The registry tuple (default: load_registry()).

    Returns:
        The SourceRow with the given source_id.

    Raises:
        RegistryError: If the source_id is not found.
    """
    if registry is None:
        registry = load_registry()

    for row in registry:
        if row.source_id == source_id:
            return row

    raise RegistryError(f"Source not found: {source_id}")
