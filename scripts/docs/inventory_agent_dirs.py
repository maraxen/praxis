"""Inventory the legacy ``.agent/`` directories against ``.praxia/docs/`` (debt #1293).

Answers, from git and the filesystem rather than by sampling:

* per immediate subdirectory of each ``.agent`` root: tracked file count, markdown
  count, and the date of the last commit that touched it (a staleness signal);
* whether the 2026-05-22 migration (``.praxia/docs/migration-manifest.txt``) left any
  source behind, and whether every destination it names still exists;
* exact-content duplicates between ``.agent`` and ``.praxia/docs`` (by SHA-256);
* which tracked files outside ``.agent`` still mention a ``.agent/`` path.

The directories were retired on the strength of this report, run at ``e0869874``; see
``.praxia/docs/archive/agent-dirs-retired.md``. On a later checkout the roots are gone, so
reproduce the numbers from a worktree at that commit.

Usage:
    uv run python scripts/docs/inventory_agent_dirs.py --out inventory.json
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import re
import subprocess
from collections import Counter, defaultdict
from pathlib import Path

logger = logging.getLogger(__name__)

AGENT_ROOTS = (".agent", "praxis/.agent", "praxis/web-client/.agent")
DOCS_ROOT = ".praxia/docs"
MANIFEST = ".praxia/docs/migration-manifest.txt"
_MANIFEST_LINE = re.compile(r"^(?P<src>.+?) → (?P<dst>.+?)(?: \[\w+\])?$")
_AGENT_REF = re.compile(r"(?<![\w.-])(?:praxis/(?:web-client/)?)?\.agent/[\w./-]*")


def _repo_root() -> Path:
    here = Path(__file__).resolve()
    for parent in here.parents:
        if (parent / "pyproject.toml").exists() and (parent / ".git").exists():
            return parent
    raise RuntimeError(f"no repo root above {here}")


def _git(root: Path, *args: str) -> str:
    return subprocess.run(
        ["git", *args], cwd=root, check=True, capture_output=True, text=True
    ).stdout


def _tracked(root: Path, *pathspecs: str) -> list[str]:
    return [p for p in _git(root, "ls-files", "-z", "--", *pathspecs).split("\0") if p]


def _last_commit_date(root: Path, path: str) -> str | None:
    out = _git(root, "log", "-1", "--format=%as", "--", path).strip()
    return out or None


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inventory_roots(root: Path) -> dict[str, dict]:
    """Per-root, per-top-level-entry counts and staleness."""
    result: dict[str, dict] = {}
    for agent_root in AGENT_ROOTS:
        files = _tracked(root, agent_root)
        groups: dict[str, list[str]] = defaultdict(list)
        for f in files:
            rel = Path(f).relative_to(agent_root)
            key = rel.parts[0] + ("/" if len(rel.parts) > 1 else "")
            groups[key].append(f)
        entries = {}
        for key, members in sorted(groups.items(), key=lambda kv: -len(kv[1])):
            exts = Counter(Path(m).suffix or "(none)" for m in members)
            entries[key] = {
                "files": len(members),
                "md": exts.get(".md", 0),
                "top_ext": exts.most_common(3),
                "last_commit": _last_commit_date(root, f"{agent_root}/{key}"),
            }
        result[agent_root] = {"files": len(files), "entries": entries}
        logger.info("%s: %d tracked files in %d entries", agent_root, len(files), len(entries))
    return result


def check_manifest(root: Path) -> dict:
    """Did the 260522 migration leave sources behind or lose destinations?"""
    left_behind, missing_dst, parsed = [], [], 0
    for line in (root / MANIFEST).read_text(encoding="utf-8").splitlines():
        m = _MANIFEST_LINE.match(line.strip())
        if not m:
            continue
        parsed += 1
        if (root / m["src"]).exists():
            left_behind.append(m["src"])
        if not (root / DOCS_ROOT).joinpath(*Path(m["dst"]).parts[2:]).exists():
            missing_dst.append(m["dst"])
    return {
        "entries": parsed,
        "sources_left_behind": left_behind,
        "destinations_missing": missing_dst,
    }


def find_duplicates(root: Path) -> list[dict]:
    """Files in an .agent root whose bytes are identical to a file under .praxia/docs.

    Empty files are skipped: every empty file hashes alike, so a single empty doc would
    otherwise "duplicate" every .gitkeep and empty report in the tree.
    """
    docs_by_hash: dict[str, list[str]] = defaultdict(list)
    for f in _tracked(root, DOCS_ROOT):
        if (root / f).stat().st_size:
            docs_by_hash[_sha256(root / f)].append(f)
    dupes = []
    for f in _tracked(root, *AGENT_ROOTS):
        if not (root / f).stat().st_size:
            continue
        h = _sha256(root / f)
        if h in docs_by_hash:
            dupes.append({"agent": f, "docs": docs_by_hash[h]})
    return dupes


def find_references(root: Path) -> dict[str, list[str]]:
    """Tracked text files outside the .agent roots that mention a .agent/ path."""
    refs: dict[str, list[str]] = {}
    hits = _git(root, "grep", "-l", "-I", "-e", ".agent/", "--", ".", *(f":!{r}" for r in AGENT_ROOTS))
    for f in hits.splitlines():
        text = (root / f).read_text(encoding="utf-8", errors="replace")
        found = sorted(set(_AGENT_REF.findall(text)))
        if found:
            refs[f] = found
    return refs


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--out", type=Path, required=True, help="JSON report path")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")

    root = _repo_root()
    report = {
        "head": _git(root, "rev-parse", "HEAD").strip(),
        "roots": inventory_roots(root),
        "manifest": check_manifest(root),
        "duplicates": find_duplicates(root),
        "empty_docs": [f for f in _tracked(root, DOCS_ROOT) if not (root / f).stat().st_size],
        "references": find_references(root),
    }
    args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    m = report["manifest"]
    logger.info(
        "manifest: %d entries, %d sources left behind, %d destinations missing",
        m["entries"], len(m["sources_left_behind"]), len(m["destinations_missing"]),
    )
    logger.info(
        "duplicates: %d; empty docs: %d; referencing files: %d",
        len(report["duplicates"]), len(report["empty_docs"]), len(report["references"]),
    )


if __name__ == "__main__":
    main()
