"""Teacher-output content-hash cache (task deliverable 4; defender R4/D9).

Raw teacher responses are cached on disk keyed by the composite of
``(prompt_version, input_hash)``. Regeneration with identical inputs re-reads
these records and rebuilds a BYTE-IDENTICAL corpus without calling any
teacher. Cache records store the raw assistant string verbatim plus
``teacher_model_version``; volatile fields (fetched_at) live ONLY here,
never in corpus rows.
"""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Final

__all__ = ["TeacherCache", "TeacherCacheError", "compute_cache_key"]


class TeacherCacheError(RuntimeError):
    """Loud failure: corrupt cache entries never silently regenerate."""


def compute_cache_key(prompt_version: str, input_hash: str) -> str:
    """The R4/D9 composite content address: sha256(prompt_version : input_hash)."""
    material = f"{prompt_version}:{input_hash}".encode("utf-8")
    return hashlib.sha256(material).hexdigest()


class TeacherCache:
    """JSON-file-per-key cache directory. Atomic writes; loud corruption."""

    SCHEMA_VERSION: Final[int] = 1

    def __init__(self, cache_dir: Path) -> None:
        self._dir = Path(cache_dir)
        self._dir.mkdir(parents=True, exist_ok=True)

    @property
    def cache_dir(self) -> Path:
        return self._dir

    def path_for(self, key: str) -> Path:
        return self._dir / f"{key}.json"

    def get(self, key: str) -> dict[str, Any] | None:
        path = self.path_for(key)
        if not path.exists():
            return None
        try:
            record = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise TeacherCacheError(f"corrupt cache entry {path.name}: {exc}") from exc
        if record.get("cache_key") != key or "raw_response" not in record:
            raise TeacherCacheError(f"cache entry {path.name} failed identity check")
        return record

    def put(
        self,
        key: str,
        *,
        prompt_version: str,
        input_hash: str,
        teacher_model_version: str,
        raw_response: str,
    ) -> None:
        record = {
            "schema_version": self.SCHEMA_VERSION,
            "cache_key": key,
            "prompt_version": prompt_version,
            "input_hash": input_hash,
            "teacher_model_version": teacher_model_version,
            # The raw assistant text VERBATIM -- the unit being cached.
            "raw_response": raw_response,
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        }
        self._atomic_write(self.path_for(key), record)

    @staticmethod
    def _atomic_write(path: Path, record: dict[str, Any]) -> None:
        payload = json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True)
        fd, tmp_name = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as handle:
                handle.write(payload)
                handle.write("\n")
            os.replace(tmp_name, path)
        except BaseException:
            try:
                os.unlink(tmp_name)
            except FileNotFoundError:
                pass
            raise
