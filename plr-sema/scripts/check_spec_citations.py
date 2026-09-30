"""Citation-anchor validator for the plr-sema spec (round-6 recommendation).

Round 6 of the adversarial cycle found that the remaining defect class in the
spec was *stale line citations* -- ``file.py:123-145`` ranges that pointed at
lines which had since moved -- and recommended a ~30-line mechanical checker
in place of a seventh review round. This is that checker.

For every citation of the form `` `path.ext:start[-end]` `` in the spec it
checks three things, in order, and reports the first that fails:

1. ``unresolved``  -- the path does not resolve to exactly one file. Bare
   basenames (``models.py``) are searched across the repo; if more than one
   candidate survives the search-root preference order the citation is
   ``ambiguous`` and the fix is to qualify the path in the spec.
2. ``out_of_range`` -- ``end`` (or ``start``) exceeds the file's line count.
3. ``symbol_not_in_range`` -- the same spec line names identifiers in
   backticks (``` `_compute_dirty_content_id` ```) and none of them occurs in
   the cited line range. A citation with no co-named identifier passes on
   bounds alone; this tier exists because a range that is *in bounds but
   points at the wrong code* is exactly the drift a bounds check misses.

Bare ``:197,209`` citations (line numbers with no file, relying on a file
named earlier in the row) are reported as ``unanchored`` informationally and
never fail the run -- they cannot be checked without prose understanding.

**Version pins (260930).** A citation is a claim about the code *as it was when
the sentence was written*. A spec therefore declares the commit its citations
resolve against, and the checker reads that commit's tree through git instead of
today's working tree:

* frontmatter ``citations_at: <rev>`` sets the pin for the whole document;
* a line ``<!-- citations-at: <rev> -->`` re-pins every following line, until
  the next such marker -- the form a later amendment uses, since it cites newer
  code than the text around it;
* ``live`` (also the default when nothing is declared) means today's working
  tree;
* a pin may be an ORDERED list, ``<rev> <rev2> ...``: each citation resolves at
  the first listed rev whose tree contains its file. This exists for one case:
  a measured artifact committed after the code it describes (a gitignored
  ``outputs/`` report force-added later), cited on the same line as that code.
  Order matters -- the code's own commit goes first, so a file present at
  both is checked against the older, pinned version.

At a pinned ``<rev>`` the repo is read with ``git ls-tree``/``git show``, and
``external/pylabrobot`` at the submodule commit that ``<rev>`` itself records, so
one sha pins both our code and the PyLabRobot version it was written against.

Usage::

    uv run python plr-sema/scripts/check_spec_citations.py \
        --spec .praxia/docs/specs/260901_plr-sema-pre-corpus-spec.md

Exit status 1 iff at least one failing (non-informational) violation.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import logging
import re
import subprocess
import sys
from pathlib import Path

log = logging.getLogger("check_spec_citations")

#: ``path.ext:start[-end][,start[-end]...]`` -- the comma tail lets one
#: citation name several ranges of the same file (``derive/__init__.py:400-405,517-543``).
CITATION_RE = re.compile(
    r"`?(?P<path>[A-Za-z0-9_./-]+\.(?:py|md|toml|json|yaml|yml|txt|sh))"
    r":(?P<ranges>\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*)`?"
)
RANGE_RE = re.compile(r"(\d+)(?:-(\d+))?")
UNANCHORED_RE = re.compile(r"`:(?P<lines>\d+(?:[-,]\d+)*)`")
BACKTICK_RE = re.compile(r"`([^`]+)`")
IDENT_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)*$")
FILE_EXT_RE = re.compile(r"\.(?:py|md|toml|json|yaml|yml|txt|sh)$")
#: A co-named identifier must precede the citation on the same line and sit
#: in the same clause: the window stops at a sentence/clause boundary so the
#: identifiers of a *neighbouring* claim are not charged against this range.
CLAUSE_BOUNDARY_RE = re.compile(r"(?:\. |; | — | -- |\) |\| )")

#: Directories never searched when resolving a bare basename.
SKIP_DIRS = frozenset(
    {".git", ".claude", ".venv", "node_modules", "__pycache__", "target", ".praxia/subagent_outputs", ".mypy_cache", ".ruff_cache", ".pytest_cache"}
)
#: When a bare basename matches several files, the first root in this list
#: that contains exactly one match wins. This is lint configuration for one
#: document, not analysis logic -- widen the citation in the spec instead of
#: this list whenever possible.
PREFERRED_ROOTS = (
    "plr-sema/",
    "scripts/",
    "training/verify/",
    "praxis/backend/utils/plr_static_analysis/",
    "praxis/backend/core/simulation/",
    ".praxia/docs/",
    ".praxia/research/",
    "external/pylabrobot/pylabrobot/legacy/",
    "external/pylabrobot/pylabrobot/",
)


@dataclasses.dataclass(frozen=True, slots=True)
class Violation:
    kind: str
    spec_line: int
    citation: str
    detail: str
    informational: bool = False
    #: The pin the citation was resolved against (``live`` = today's tree).
    rev: str = "live"


#: The one submodule a pinned tree descends into (at the gitlink the pinned
#: commit records). Any other gitlink is left out of the snapshot.
SUBMODULE = "external/pylabrobot"
LIVE = "live"


def _skipped(rel: str) -> bool:
    return any(part in SKIP_DIRS for part in rel.split("/")) or any(rel.startswith(s) for s in SKIP_DIRS)


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True, text=True).stdout


class LiveTree:
    """Today's working tree."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.rev = LIVE

    def paths(self):
        for p in self.root.rglob("*"):
            if p.is_file():
                rel = p.relative_to(self.root).as_posix()
                if not _skipped(rel):
                    yield rel

    def read(self, rel: str) -> str:
        return (self.root / rel).read_text(encoding="utf-8", errors="replace")


class GitTree:
    """The repo at ``rev``, read through git, with ``external/pylabrobot`` at the
    submodule commit ``rev`` records. Nothing is checked out."""

    def __init__(self, root: Path, rev: str) -> None:
        self.root = root
        self.rev = _git(root, "rev-parse", "--verify", f"{rev}^{{commit}}").strip()
        self._files: dict[str, tuple[Path, str]] = {}
        for line in _git(root, "ls-tree", "-r", self.rev).splitlines():
            meta, rel = line.split("\t", 1)
            mode, kind, obj = meta.split()
            if kind == "blob" and not _skipped(rel):
                self._files[rel] = (root, f"{self.rev}:{rel}")
            elif kind == "commit" and rel == SUBMODULE:
                sub = root / SUBMODULE
                for sline in _git(sub, "ls-tree", "-r", "--name-only", obj).splitlines():
                    srel = f"{SUBMODULE}/{sline}"
                    if not _skipped(srel):
                        self._files[srel] = (sub, f"{obj}:{sline}")

    def paths(self):
        return iter(self._files)

    def read(self, rel: str) -> str:
        repo, spec = self._files[rel]
        return subprocess.run(["git", "-C", str(repo), "show", spec], check=True, capture_output=True).stdout.decode(
            "utf-8", errors="replace"
        )


def make_tree(root: Path, rev: str):
    return LiveTree(root) if rev == LIVE else GitTree(root, rev)


class Resolver:
    """Resolves citations against one tree (live, or a pinned commit). Paths are
    repo-relative posix strings."""

    def __init__(self, tree) -> None:
        self.tree = tree
        self._all: set[str] = set()
        self._by_basename: dict[str, list[str]] = {}
        for rel in tree.paths():
            self._all.add(rel)
            self._by_basename.setdefault(rel.rsplit("/", 1)[-1], []).append(rel)
        self._lines: dict[str, list[str]] = {}

    def resolve(self, cited: str) -> tuple[str | None, list[str]]:
        """Return (unique path or None, candidate list)."""
        if cited in self._all:
            return cited, [cited]
        base = cited.rsplit("/", 1)[-1]
        cands = [p for p in self._by_basename.get(base, []) if p.endswith(cited)]
        if len(cands) == 1:
            return cands[0], cands
        if len(cands) > 1:
            for pref in PREFERRED_ROOTS:
                under = [p for p in cands if p.startswith(pref)]
                if len(under) == 1:
                    return under[0], cands
        return None, cands

    def lines(self, p: str) -> list[str]:
        if p not in self._lines:
            self._lines[p] = self.tree.read(p).splitlines()
        return self._lines[p]

    def enclosing_defs(self, p: str, start: int, end: int) -> set[str]:
        """Names of every class/def whose body span encloses [start, end] in a
        Python file -- so `` `TipTracker.get_tip` (`tip_tracker.py:65`) `` passes
        when line 65 is the ``raise`` inside ``get_tip``, not its ``def`` line.
        Non-Python files return the empty set (textual match only)."""
        if not p.endswith(".py"):
            return set()
        if not hasattr(self, "_defs"):
            self._defs: dict[str, list[tuple[str, int, int]]] = {}
        if p not in self._defs:
            spans: list[tuple[str, int, int]] = []
            try:
                tree = ast.parse("\n".join(self.lines(p)))
            except SyntaxError:
                tree = None
            if tree is not None:
                for node in ast.walk(tree):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        spans.append((node.name, node.lineno, node.end_lineno or node.lineno))
            self._defs[p] = spans
        return {n for n, a, b in self._defs[p] if a <= start and end <= b}


def _co_named_identifiers(line: str, cite_start: int) -> list[str]:
    """Backticked identifiers in the clause that leads up to the citation."""
    prefix = line[:cite_start]
    # keep only the text after the last clause boundary, but never cut inside
    # an open parenthesis (``(`_compute_dirty_content_id`, `git_state.py:...`)``)
    cut = 0
    for m in CLAUSE_BOUNDARY_RE.finditer(prefix):
        if prefix[m.end():].count("(") >= prefix[m.end():].count(")"):
            cut = m.end()
    window = prefix[cut:]
    out: list[str] = []
    for tok in BACKTICK_RE.findall(window):
        tok = tok.strip().split("(")[0].strip()
        if FILE_EXT_RE.search(tok) or CITATION_RE.fullmatch(tok):
            continue
        if IDENT_RE.match(tok):
            out.append(tok)
    return out


#: Frontmatter pin and in-body re-pin marker (see the module docstring).
_REVS = r"[0-9A-Za-z_.\-/^~]+(?:\s+[0-9A-Za-z_.\-/^~]+)*"
FRONTMATTER_PIN_RE = re.compile(rf"^citations_at:\s*[\"']?(?P<rev>{_REVS})[\"']?\s*$")
MARKER_PIN_RE = re.compile(rf"^\s*<!--\s*citations-at:\s*(?P<rev>{_REVS})\s*-->\s*$")


def line_pins(text: str) -> list[str]:
    """The pin in force on each line (index 0 = line 1): the frontmatter's
    ``citations_at`` (default ``live``), re-set by every marker line."""
    lines = text.splitlines()
    current = LIVE
    if lines and lines[0].strip() == "---":
        for fm in lines[1:]:
            if fm.strip() == "---":
                break
            if m := FRONTMATTER_PIN_RE.match(fm.strip()):
                current = m.group("rev")
    pins: list[str] = []
    for line in lines:
        if m := MARKER_PIN_RE.match(line):
            current = m.group("rev")
        pins.append(current)
    return pins


def declared_pins(spec: Path) -> list[str]:
    """Every distinct pin (a rev, or an ordered rev list) the spec declares, in
    order of first use."""
    seen: list[str] = []
    for p in line_pins(spec.read_text(encoding="utf-8")):
        if p not in seen:
            seen.append(p)
    return seen


def declared_revs(spec: Path) -> list[str]:
    """Every individual rev named by any of the spec's pins."""
    out: list[str] = []
    for pin in declared_pins(spec):
        for rev in pin.split():
            if rev not in out:
                out.append(rev)
    return out


def check(spec: Path, root: Path, *, rev_override: str | None = None) -> list[Violation]:
    """``rev_override`` resolves EVERY line at one rev, ignoring the declared
    pins -- for choosing pins, never for the lint verdict."""
    doc = spec.read_text(encoding="utf-8")
    pins = line_pins(doc) if rev_override is None else [rev_override] * len(doc.splitlines())
    resolvers: dict[str, Resolver] = {}
    violations: list[Violation] = []
    for lineno, line in enumerate(doc.splitlines(), 1):
        pin = pins[lineno - 1]
        for one in pin.split():
            if one not in resolvers:
                resolvers[one] = Resolver(make_tree(root, one))
        for m in UNANCHORED_RE.finditer(line):
            violations.append(Violation("unanchored", lineno, m.group(0), "file-less line citation; cannot check", True, pin))
        for m in CITATION_RE.finditer(line):
            cited, text = m.group("path"), m.group(0)
            ranges = [(int(a), int(b) if b else int(a)) for a, b in RANGE_RE.findall(m.group("ranges"))]
            # an ordered pin list: the first rev whose tree resolves the file
            rev = pin.split()[0]
            resolver = resolvers[rev]
            path, cands = resolver.resolve(cited)
            for alt in pin.split()[1:]:
                if path is not None:
                    break
                alt_path, alt_cands = resolvers[alt].resolve(cited)
                if alt_path is not None:
                    rev, resolver, path, cands = alt, resolvers[alt], alt_path, alt_cands
            if path is None:
                kind = "ambiguous" if cands else "unresolved"
                detail = ", ".join(cands[:6]) or "no file with that name"
                violations.append(Violation(kind, lineno, text, detail, rev=rev))
                continue
            flines = resolver.lines(path)
            rel = path
            bad = [(s, e) for s, e in ranges if s < 1 or e < s or e > len(flines)]
            if bad:
                violations.append(Violation("out_of_range", lineno, text, f"{rel} has {len(flines)} lines; bad range(s) {bad}", rev=rev))
                continue
            idents = _co_named_identifiers(line, m.start())
            if idents:
                body = "\n".join("\n".join(flines[s - 1 : e]) for s, e in ranges)
                enclosing: set[str] = set()
                for s, e in ranges:
                    enclosing |= resolver.enclosing_defs(path, s, e)
                hits = [
                    i for i in idents
                    if i in body or i.rsplit(".", 1)[-1] in body or i.rsplit(".", 1)[-1] in enclosing
                ]
                if not hits:
                    violations.append(Violation("symbol_not_in_range", lineno, text, f"none of {idents} in {rel}:{m.group('ranges')}", rev=rev))
    return violations


def _find_repo_root(start: Path) -> Path:
    for p in [start, *start.parents]:
        if (p / "pyproject.toml").is_file() and (p / ".git").exists():
            return p
    raise SystemExit("could not locate repo root (pyproject.toml + .git) above " + str(start))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--spec", type=Path, required=True)
    ap.add_argument("--repo-root", type=Path, default=None)
    ap.add_argument("--json-out", type=Path, default=None)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO, format="%(levelname)s %(message)s")
    root = (args.repo_root or _find_repo_root(Path(__file__).resolve())).resolve()
    spec = args.spec.resolve()
    violations = check(spec, root)
    failing = [v for v in violations if not v.informational]
    n_cit = sum(1 for _ in CITATION_RE.finditer(spec.read_text(encoding="utf-8")))
    for v in violations:
        (log.debug if v.informational else log.warning)("%s L%d %s -- %s", v.kind, v.spec_line, v.citation, v.detail)
    by_kind: dict[str, int] = {}
    for v in violations:
        by_kind[v.kind] = by_kind.get(v.kind, 0) + 1
    log.info("citations=%d failing=%d by_kind=%s", n_cit, len(failing), by_kind)
    if args.json_out:
        args.json_out.write_text(json.dumps({"spec": str(spec), "citations": n_cit, "violations": [dataclasses.asdict(v) for v in violations]}, indent=2))
    return 1 if failing else 0


if __name__ == "__main__":
    sys.exit(main())
