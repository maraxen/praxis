"""plr_sema.check.cache: the content-addressed report cache (spec 260903
§13.3, `260903_plr-sema-families-cache-increment.md`, #4922).

**Stdlib only** -- same import boundary as the rest of `check/` (module
docstring of `plr_sema.check`): no `pylabrobot`, no `libcst`, no
`pydantic`.

**What this module is.** §13.3.3's `CacheStore`: one JSON file per entry
under a configurable root (default `plr-sema/.cache/`, **never**
`$TMPDIR` -- a cache under a temp dir is silently emptied between runs,
turning a persistence bug into a performance mystery). An entry stores the
**pre-relabel** findings a `check_ir` call produced for one `cache_key`
(`plr_sema.check.ir.cache_key`), plus the `created` timestamp and the
sorted, distinct `Call.method` names the checked bytecode invoked --
the last field is what makes §13.3.4's targeted invalidation possible.

**Why pre-relabel.** `bytecode.sideband` (which carries the
`operation_id`-to-real-graph-id `origin` map) is excluded from
`bytecode_hash` (spec §11.3.2) -- two graphs differing only in their
`OperationNode` ids share a `bytecode_hash` and therefore a cache key, but
have different origin maps. Storing post-relabel findings would silently
return the first graph's operation ids for the second graph. The read-
through hook (`plr_sema.check.check_graph`'s `cache=` keyword) relabels a
cache HIT with its own graph's `origin` map, exactly as it would a miss --
see that function, not this module, for the relabel step.

**Read-through is opt-in.** Nothing in this module is reachable unless a
caller constructs a `CacheStore` and passes it explicitly -- `check_graph`
defaults `cache=None`, under which no file is read, written, or created
anywhere (AC-13.5).

**Never raises into the checker.** A corrupt, truncated, or key-mismatched
entry is a miss, not an exception -- `get()` catches every `Exception` a
malformed file could raise (`json.JSONDecodeError`, `KeyError`, `OSError`,
...) and returns `None`. `put()` likewise never raises: a cache WRITE
failure (disk full, permission denied, a root that doesn't exist and can't
be created) must not break analysis that would otherwise have succeeded.

**Invalidation is a human-run tool, not an automatic mechanism.** §13.3.4:
nothing calls `invalidate_by_methods` during `check_graph`. It is exposed
here as a CLI (`python -m plr_sema.check.cache`) for the human who
regenerated a contract table at the same PLR pin (which changes
`contracts_sha` and therefore misses every cached entry, correctly but
wastefully) and does not want to discard a corpus-sized cache over a
change to one method's guards.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from plr_sema.verdict import Finding, PlrSite, Verdict, vocabulary_reason

__all__ = ["CacheStore", "canonical_key", "main"]

#: §13.3.3: the default cache root -- inside the package tree, gitignored,
#: and never `$TMPDIR`/a system temp dir (see module docstring).
DEFAULT_CACHE_ROOT = Path(__file__).resolve().parents[3] / ".cache"


def canonical_key(key: tuple[Any, ...]) -> str:
    """§13.3.3: `json.dumps(key, sort_keys=True, separators=(",", ":"),
    ensure_ascii=False)` -- the same canonicalisation
    `plr_sema.check.ir.canonical_text` already uses (§11.3.1 item 6), so
    there is one serialisation convention in the package, not two.
    """
    return json.dumps(key, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _plr_site_to_dict(site: PlrSite | None) -> dict[str, Any] | None:
    if site is None:
        return None
    return {"file": site.file, "lineno": site.lineno, "qualname": site.qualname}


def _plr_site_from_dict(d: dict[str, Any] | None) -> PlrSite | None:
    if d is None:
        return None
    return PlrSite(file=d["file"], lineno=d["lineno"], qualname=d["qualname"])


def _finding_to_dict(finding: Finding) -> dict[str, Any]:
    return {
        "verdict": finding.verdict.value,
        "operation_id": finding.operation_id,
        "category": finding.category,
        "plr_site": _plr_site_to_dict(finding.plr_site),
        "reason": finding.reason,
        "detail": finding.detail,
        "evidence": [_plr_site_to_dict(site) for site in finding.evidence],
    }


def _finding_from_dict(d: dict[str, Any]) -> Finding:
    return Finding(
        verdict=Verdict(d["verdict"]),
        operation_id=d["operation_id"],
        category=d["category"],
        plr_site=_plr_site_from_dict(d["plr_site"]),
        reason=vocabulary_reason(d["reason"]),  # §3.3: validated, never trusted
        detail=d.get("detail", ""),
        evidence=tuple(_plr_site_from_dict(site) for site in d.get("evidence", ())),
    )


class CacheStore:
    """§13.3.3: a small stdlib-only store, one JSON file per entry.

    `put`'s `methods` keyword is additive over the illustrative signature
    in §13.3.3's normative block (which shows only `(key, findings)`): the
    entry format there ALSO specifies a `"methods"` field ("sorted distinct
    `CALL.method` in the bytecode"), and nothing else the store receives
    carries that information, so it has to arrive as an explicit argument
    from the caller (`check_graph`, which has the bytecode). Defaulting it
    to `frozenset()` keeps `put(key, findings)` callable exactly as shown
    for any caller that doesn't need §13.3.4's invalidation.
    """

    def __init__(self, root: Path | str = DEFAULT_CACHE_ROOT) -> None:
        self.root = Path(root)

    def _path_for(self, key_str: str) -> Path:
        digest = hashlib.sha256(key_str.encode("utf-8")).hexdigest()
        return self.root / f"{digest}.json"

    def get(self, key: tuple[Any, ...]) -> tuple[Finding, ...] | None:
        """A miss on: no file, a corrupt/truncated file, or a stored `key`
        that does not match the requested one (a hash collision or a
        filename-truncating filesystem -- a loud mismatch here rather than
        a silently wrong answer). Never raises.
        """
        key_str = canonical_key(key)
        path = self._path_for(key_str)
        try:
            with open(path, encoding="utf-8") as fh:
                entry = json.load(fh)
            if entry.get("key") != key_str:
                return None
            return tuple(_finding_from_dict(d) for d in entry["findings"])
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def put(
        self,
        key: tuple[Any, ...],
        findings: tuple[Finding, ...],
        *,
        methods: frozenset[str] = frozenset(),
    ) -> None:
        """Atomic write: build the entry, write it to a sibling temp file,
        then `os.replace` it into place -- a reader never observes a
        partially-written entry. Never raises into the checker: a write
        failure (missing/unwritable root, disk full, ...) is swallowed,
        matching `get`'s "corrupt entry is a miss" discipline on the other
        side of the same store.
        """
        key_str = canonical_key(key)
        entry = {
            "key": key_str,
            "created": datetime.now(timezone.utc).isoformat(),
            "findings": [_finding_to_dict(f) for f in findings],
            "methods": sorted(methods),
        }
        path = self._path_for(key_str)
        tmp_path = path.with_name(f"{path.name}.tmp-{os.getpid()}-{uuid.uuid4().hex}")
        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with open(tmp_path, "w", encoding="utf-8") as fh:
                json.dump(entry, fh, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
            os.replace(tmp_path, path)
        except OSError:
            try:
                tmp_path.unlink(missing_ok=True)
            except OSError:
                pass

    def invalidate_by_methods(self, methods: frozenset[str]) -> int:
        """§13.3.4: delete every entry whose stored `"methods"` list
        intersects `methods`; return the count deleted. A corrupt entry is
        skipped (not counted, not deleted-and-miscounted) rather than
        raising -- the same "corrupt entry is inert" discipline as `get`.
        """
        if not self.root.is_dir():
            return 0
        deleted = 0
        for path in sorted(self.root.glob("*.json")):
            try:
                with open(path, encoding="utf-8") as fh:
                    entry = json.load(fh)
                entry_methods = frozenset(entry.get("methods", ()))
            except (OSError, ValueError, TypeError):
                continue
            if entry_methods & methods:
                try:
                    path.unlink()
                    deleted += 1
                except OSError:
                    pass
        return deleted


def _changed_receiver_methods(old_contracts: dict[str, Any], new_contracts: dict[str, Any]) -> list[str]:
    """§13.3.4: diff two contract tables. A `receiver.method` key whose
    entry's canonical JSON differs between the two tables -- including a
    key present in one and absent from the other -- counts as changed.
    Returns the sorted list of changed keys (`"LiquidHandler.aspirate"`
    form), for publication; callers wanting `invalidate_by_methods`'
    bare-method-name input should take `.rsplit(".", 1)[-1]` of each.
    """
    changed: list[str] = []
    for key in sorted(set(old_contracts) | set(new_contracts)):
        old_entry = old_contracts.get(key)
        new_entry = new_contracts.get(key)
        if canonical_key(old_entry) != canonical_key(new_entry):
            changed.append(key)
    return changed


def _bare_method_names(receiver_methods: list[str]) -> frozenset[str]:
    return frozenset(key.rsplit(".", 1)[-1] for key in receiver_methods)


def main(argv: list[str] | None = None) -> int:
    """§13.3.4's CLI: `python -m plr_sema.check.cache --old A.json --new
    B.json --root plr-sema/.cache` (an optional leading `invalidate`
    positional is accepted and ignored, for a caller that prefers a
    subcommand-shaped invocation; `--cache-dir` is accepted as a synonym
    for `--root`). Publishes the changed `receiver.method` keys and the
    count of cache entries marked stale; never touches a cache entry the
    diff did not name.
    """
    parser = argparse.ArgumentParser(prog="python -m plr_sema.check.cache")
    parser.add_argument("command", nargs="?", default="invalidate", choices=["invalidate"])
    parser.add_argument("--old", required=True, help="the OLD derived_contracts.json path")
    parser.add_argument("--new", required=True, help="the NEW derived_contracts.json path")
    parser.add_argument(
        "--root",
        "--cache-dir",
        dest="root",
        default=str(DEFAULT_CACHE_ROOT),
        help="the cache store root (default: plr-sema/.cache)",
    )
    args = parser.parse_args(argv)

    old_payload = json.loads(Path(args.old).read_text(encoding="utf-8"))
    new_payload = json.loads(Path(args.new).read_text(encoding="utf-8"))
    old_contracts = old_payload.get("contracts", {})
    new_contracts = new_payload.get("contracts", {})

    changed = _changed_receiver_methods(old_contracts, new_contracts)
    methods = _bare_method_names(changed)

    store = CacheStore(root=Path(args.root))
    stale_count = store.invalidate_by_methods(methods)

    result = {
        "changed_keys": changed,
        "changed_methods": sorted(methods),
        "stale_count": stale_count,
        "root": str(store.root),
    }
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
