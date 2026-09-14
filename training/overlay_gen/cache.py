"""Content-hash teacher-output cache (spec rev2 AC-2.3/2.4.x, R4 fix).

Same sha => same corpus: a teacher response is keyed on
``(prompt_version, teacher_model_version, prompt_text)`` hashed with SHA-256;
a cache hit short-circuits the HTTP call, so re-running the generator is
idempotent even though the teacher samples at nonzero temperature.

DUPLICATION NOTE (deliberate): P2.3's coverage-floor generator was specced to
own "the" teacher cache and may share this util eventually, but as of
260825 P2.3 is NOT merged (no ``training/coverage_floor/`` exists). Per the
P2.4 dispatch constraints this is a small self-contained implementation here;
when P2.3 lands, reconcile the two into one shared module and delete the
loser -- until then both carry this note.

Cache entries are small JSON files committed beside the code so any run can
replay exactly the same overlay generation without network access.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

__all__ = ["TeacherCache"]


class TeacherCache:
    """File-backed content-addressed store of raw teacher completions."""

    SCHEMA_VERSION = 1

    def __init__(self, cache_dir: Path) -> None:
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    @staticmethod
    def key(prompt_version: str, teacher_model_version: str, prompt: str) -> str:
        material = "\x00".join((prompt_version, teacher_model_version, prompt))
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _path(self, key: str) -> Path:
        return self.cache_dir / f"{key}.json"

    def get(self, prompt_version: str, teacher_model_version: str, prompt: str) -> str | None:
        path = self._path(self.key(prompt_version, teacher_model_version, prompt))
        if not path.is_file():
            return None
        try:
            entry = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None  # corrupt entry behaves as a miss; put() will rewrite
        if entry.get("prompt_sha256") != self.key(prompt_version, teacher_model_version, prompt):
            return None  # hash collision / tamper: refuse to serve stale text
        return entry.get("response")

    def put(
        self,
        prompt_version: str,
        teacher_model_version: str,
        prompt: str,
        response: str,
        served_model_version: str | None = None,
    ) -> None:
        key = self.key(prompt_version, teacher_model_version, prompt)
        entry = {
            "schema_version": self.SCHEMA_VERSION,
            "key": key,
            "prompt_version": prompt_version,
            "teacher_model_version": teacher_model_version,
            "served_model_version": served_model_version,
            "prompt_sha256": key,
            "response": response,
            "created_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        tmp = self._path(key).with_suffix(".tmp")
        tmp.write_text(json.dumps(entry, indent=1, sort_keys=True), encoding="utf-8")
        tmp.replace(self._path(key))  # atomic-ish on POSIX
