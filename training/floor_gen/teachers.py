"""Teacher backends (task deliverable 3; spec rev2 F6 amendment).

Three sanctioned backends:

(a) ``OxAlphaBatchWriter`` -- writes self-contained prompt-batch files with
    expected-response-shape instructions so an orchestrator can later fan
    them to spawned ox-alpha jcode workers (ambiguity-injection / golden
    authoring lane). No network, fully offline.

(b) ``TitanixTeacher`` -- DIRECT HTTP to the verified-live localhost vLLM
    endpoint (OpenAI-compatible ``/v1/chat/completions``, model
    ``titanix-vllm-primary``), implemented end-to-end now for bulk
    mechanical passes. stdlib urllib only: no new dependencies. Smoke-scale
    lane only as of 260827 (see F6 amendment (c) below).

(c) ``GeminiTeacher`` -- shells to the LOCAL ``agy`` CLI (``agy --print ...
    --model gemini-3.7-flash-medium --output-format json --json-schema
    ...``), the full-scale-pass teacher chosen 260827 after
    titanix-vllm-primary was flagged as not viable at that scale. No API key
    is managed by this repo -- ``agy`` owns its own auth (260827, corrected
    from an earlier raw-HTTP-API design that assumed direct key management).
    Uses ``--json-schema`` guided decoding to enforce the exact response
    contract at the decoding layer instead of by free-text instruction +
    hopeful parsing -- the model is structurally unable to emit markdown
    fences, commentary, or a malformed shape. Supports batched requests
    (``complete_batch``) so a full-scale pass issues one ``agy`` call per
    ``GEMINI_BATCH_SIZE`` items instead of one per item (260827
    user-directed: empirically, per-call fixed overhead dominates at batch
    size 1 -- see the decision doc).

    EMPIRICAL CAVEAT (found during smoke-testing, load-bearing for the code
    below): ``--json-schema``'s ``nullable: true`` does NOT reliably produce
    a real JSON ``null`` for an absent ``clarification`` -- TWO DISTINCT
    non-null stand-ins observed across separate calls: an empty string
    ``""``, and separately the literal four-character STRING ``"null"``
    (quoted text, not the JSON literal). Both ``complete`` and
    ``complete_batch`` normalize any such stand-in back to real ``None``
    before returning (``_NULL_STANDINS``), because downstream
    (``corpus.py::validate_class_shape``) treats "clarification present" as
    "this must be an out-of-surface row" -- an un-normalized stand-in would
    silently misclassify an in-surface row as carrying a clarification.
    Given two independent failure modes surfaced in a handful of manual
    calls, treat this as an open reliability question, not a closed one --
    the full-scale run should watch for a third shape this normalization
    doesn't catch (e.g. checked at manifest-review time, not asserted here).
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Final, Protocol

from floor_gen.prompts import response_shape_instructions
from floor_gen.versions import AGY_BIN, GEMINI_MODEL, TITANIX_BASE_URL, TITANIX_MODEL

__all__ = [
    "FakeTeacher",
    "GeminiError",
    "GeminiTeacher",
    "OxAlphaBatchWriter",
    "TeacherBackend",
    "TitanixError",
    "TitanixTeacher",
]

#: The exact two-field contract from ``response_shape_instructions()``,
#: expressed as a JSON Schema object for ``agy --json-schema`` guided
#: decoding. Any change to the free-text shape in ``prompts.py`` MUST be
#: mirrored here AND bump ``PROMPT_VERSION`` (versions.py) -- the two are one
#: contract described twice, not two independent contracts.
_GEMINI_RESPONSE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "utterance": {"type": "string"},
        "clarification": {"type": "string", "nullable": True},
    },
    "required": ["utterance", "clarification"],
}

#: Batched-request schema: agy's ``--json-schema`` requires a top-level
#: OBJECT (a bare top-level ARRAY schema was rejected in smoke-testing, exit
#: 1, 0 tokens billed -- rejected before reaching the model), so batches wrap
#: the per-item array under a ``results`` key. Each item carries its own
#: ``id`` (the caller's cache key) so responses join back to requests by id,
#: not by array position -- defensive against the model reordering.
_GEMINI_BATCH_RESPONSE_SCHEMA: Final[dict[str, Any]] = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "string"},
                    "utterance": {"type": "string"},
                    "clarification": {"type": "string", "nullable": True},
                },
                "required": ["id", "utterance", "clarification"],
            },
        }
    },
    "required": ["results"],
}


class TeacherBackend(Protocol):
    """Minimal backend surface the corpus driver consumes."""

    @property
    def teacher_model_version(self) -> str: ...

    def complete(self, system: str, user: str) -> str:
        """Return the RAW assistant text verbatim."""
        ...


class TitanixError(RuntimeError):
    """Loud transport/shape failure against the titanix vLLM endpoint."""


class TitanixTeacher:
    """Direct OpenAI-compatible chat-completions client for localhost:8020/v1."""

    def __init__(
        self,
        base_url: str = TITANIX_BASE_URL,
        model: str = TITANIX_MODEL,
        timeout_s: float = 180.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._model = model
        self._timeout_s = timeout_s
        self._resolved_version: str | None = None

    @property
    def teacher_model_version(self) -> str:
        if self._resolved_version is None:
            self._resolved_version = self._resolve_model_version()
        return self._resolved_version

    def _resolve_model_version(self) -> str:
        payload = self._request_json("GET", "/models")
        for entry in payload.get("data", []):
            if entry.get("id") == self._model:
                root = entry.get("root") or entry.get("id")
                return f"{self._model}@{root}"
        raise TitanixError(f"model {self._model!r} not served at {self._base_url}")

    def complete(self, system: str, user: str) -> str:
        body = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            # Greedy decode for reproducibility-on-regeneration intent; the
            # cache is what guarantees byte-identity across teacher drift.
            "temperature": 0,
            # Thinking-capable served models can spend budget before answering;
            # 1024 leaves ample room for the small mandated JSON object.
            "max_tokens": 1024,
            "stream": False,
            # Qwen3-family served models: disable chain-of-thought so the
            # budget goes to the mandated JSON object (verified against the
            # live titanix endpoint; ignored by non-thinking templates).
            "chat_template_kwargs": {"enable_thinking": False},
        }
        last_error: TitanixError | None = None
        for _attempt in range(2):  # one bounded retry on empty content
            payload = self._request_json("POST", "/chat/completions", body)
            try:
                message = payload["choices"][0]["message"]
                content = message["content"]
            except (KeyError, IndexError, TypeError) as exc:
                raise TitanixError(f"unexpected completion shape: {json.dumps(payload)[:400]}") from exc
            if isinstance(content, str) and content.strip():
                return content
            reasoning = str(message.get("reasoning") or message.get("reasoning_content") or "")[:200]
            last_error = TitanixError(
                f"empty completion content from titanix (finish={payload['choices'][0].get('finish_reason')!r}, reasoning={reasoning!r})"
            )
        raise last_error  # type: ignore[misc]

    def _request_json(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        url = f"{self._base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body is not None else None
        request = urllib.request.Request(url, data=data, method=method)
        request.add_header("Content-Type", "application/json")
        try:
            with urllib.request.urlopen(request, timeout=self._timeout_s) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            snippet = exc.read().decode("utf-8", errors="replace")[:300]
            raise TitanixError(f"{method} {url} -> HTTP {exc.code}: {snippet}") from exc
        except urllib.error.URLError as exc:
            raise TitanixError(f"{method} {url} failed: {exc.reason}") from exc
        except TimeoutError as exc:
            raise TitanixError(f"{method} {url} timed out after {self._timeout_s}s") from exc


class GeminiError(RuntimeError):
    """Loud transport/shape failure against the agy-shelled Gemini backend."""


#: Observed stand-ins for a real JSON null on a ``nullable: true`` string
#: field (see the module docstring's EMPIRICAL CAVEAT): an empty string, AND
#: separately the literal four-character string "null" (not the JSON
#: literal) -- two distinct failure modes caught in smoke-testing, not one.
_NULL_STANDINS: Final[frozenset[str]] = frozenset({"", "null", "none"})


def _normalize_clarification(value: Any) -> str | None:
    """Fold observed non-null stand-ins for an absent clarification back to
    real ``None`` (see the module docstring's EMPIRICAL CAVEAT)."""
    if isinstance(value, str) and value.strip().lower() in _NULL_STANDINS:
        return None
    return value


class GeminiTeacher:
    """Gemini 3.7 Flash via the ``agy`` CLI, with guided-decoding JSON
    contract enforcement and optional request batching.

    Full-scale-pass teacher (F6 amendment (c), 260827, agy-corrected same
    day). No API key: auth is entirely ``agy``'s own (whatever it already
    uses interactively). Every call is a fresh, stateless ``agy --print``
    invocation -- no ``--continue``/``--conversation``, so nothing here
    depends on agy conversation state persisting between calls.
    """

    def __init__(
        self,
        model: str = GEMINI_MODEL,
        agy_bin: str = AGY_BIN,
        timeout_s: float = 180.0,
    ) -> None:
        self._model = model
        self._agy_bin = agy_bin
        self._timeout_s = timeout_s

    @property
    def teacher_model_version(self) -> str:
        return self._model

    def complete(self, system: str, user: str) -> str:
        prompt = f"{system}\n\n{user}"
        payload = self._run_agy(prompt, _GEMINI_RESPONSE_SCHEMA)
        structured = payload.get("structured_output") or {}
        if not isinstance(structured.get("utterance"), str):
            raise GeminiError(f"unexpected completion shape: {json.dumps(payload)[:400]}")
        result = {
            "utterance": structured["utterance"],
            "clarification": _normalize_clarification(structured.get("clarification")),
        }
        # complete() returns raw text verbatim per the TeacherBackend
        # protocol; the JSON text below IS that raw text, already
        # schema-shaped and null-normalized.
        return json.dumps(result, sort_keys=True)

    def complete_batch(self, system: str, users: list[str], ids: list[str]) -> dict[str, str]:
        """One ``agy`` call for MANY items (260827 user-directed: group many
        into one rather than issue an individual call per item). ``ids``
        MUST be the caller's cache keys, one per ``users`` entry, same
        order; the model is instructed to echo them back so results join by
        id, not by array position. Returns ``{id: raw_response_text}`` for
        every id -- loudly errors if any id is missing, duplicated, or
        unrequested (defensive: nothing here trusts the model to be
        well-behaved about echoing ids)."""
        if len(users) != len(ids):
            raise GeminiError(f"users/ids length mismatch: {len(users)} != {len(ids)}")
        items_block = "\n\n".join(
            f'--- ITEM id="{item_id}" ---\n{user}' for item_id, user in zip(ids, users)
        )
        prompt = (
            f"{system}\n\n"
            f"You will process {len(ids)} INDEPENDENT items below, each with its own "
            "instructions. For EACH item, follow ONLY that item's own instructions and "
            "produce one entry in `results`, with `id` copied EXACTLY from that item's "
            "id. Every item must appear exactly once in `results`; do not merge, skip, "
            "or reorder items.\n\n" + items_block
        )
        payload = self._run_agy(prompt, _GEMINI_BATCH_RESPONSE_SCHEMA)
        structured = payload["structured_output"]
        results = structured.get("results")
        if not isinstance(results, list):
            raise GeminiError(f"batch response missing 'results' array: {json.dumps(structured)[:400]}")
        by_id: dict[str, str] = {}
        for entry in results:
            entry_id = entry.get("id")
            if entry_id in by_id:
                raise GeminiError(f"batch response duplicated id {entry_id!r}")
            by_id[entry_id] = json.dumps(
                {
                    "utterance": entry.get("utterance"),
                    "clarification": _normalize_clarification(entry.get("clarification")),
                },
                sort_keys=True,
            )
        requested = set(ids)
        got = set(by_id)
        if got != requested:
            raise GeminiError(
                f"batch response id mismatch: missing {sorted(requested - got)}, "
                f"unrequested {sorted(got - requested)}"
            )
        return by_id

    def _run_agy(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        cmd = [
            self._agy_bin,
            "--model",
            self._model,
            "--output-format",
            "json",
            "--json-schema",
            json.dumps(schema),
            f"--print={prompt}",
        ]
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=self._timeout_s,
            )
        except FileNotFoundError as exc:
            raise GeminiError(f"{self._agy_bin!r} not found on PATH") from exc
        except subprocess.TimeoutExpired as exc:
            raise GeminiError(f"agy timed out after {self._timeout_s}s") from exc
        try:
            payload = json.loads(proc.stdout)
        except json.JSONDecodeError as exc:
            raise GeminiError(
                f"agy stdout is not JSON (exit={proc.returncode}): {proc.stdout[:300]!r} "
                f"stderr={proc.stderr[:300]!r}"
            ) from exc
        if payload.get("status") != "SUCCESS" or "structured_output" not in payload:
            raise GeminiError(
                f"agy call failed (exit={proc.returncode}): {json.dumps(payload)[:400]}"
            )
        return payload


class FakeTeacher:
    """Offline scripted backend for tests + offline pipeline checks."""

    def __init__(
        self,
        responder: Callable[[str, str], str] | None = None,
        model_version: str = "fake-teacher@test",
    ) -> None:
        self._responder = responder or self._default_responder
        self._model_version = model_version
        self.call_count = 0

    @property
    def teacher_model_version(self) -> str:
        return self._model_version

    def complete(self, system: str, user: str) -> str:
        self.call_count += 1
        return self._responder(system, user)

    @staticmethod
    def _default_responder(system: str, user: str) -> str:
        if '"clarification"' in user and "OUTSIDE" in user:
            return json.dumps(
                {
                    "utterance": "Can you do this off-list request for me?",
                    "clarification": "I can't do that with the tools I have, but I can help with pipetting, deck moves, or plate reads.",
                },
                sort_keys=True,
            )
        return json.dumps(
            {"utterance": "Aspirate 50 microliters from plate_1_A1.", "clarification": None},
            sort_keys=True,
        )


class OxAlphaBatchWriter:
    """Write fan-out-ready prompt batch files for ox-alpha jcode workers."""

    HEADER: Final[str] = """# ox-alpha NL-ification batch {batch_no} ({n_items} items)

prompt_version={prompt_version}

You are one of several spawned ox-alpha workers producing teacher text for the
Coxswain P2.3 coverage floor. For EACH item below, read `system` and `user`,
compose the assistant reply exactly per the output contract, then APPEND one
line to `responses.jsonl` next to your batch file:

{{"input_hash": "<item input_hash>", "response": <your reply as a JSON string>}}

Rules:
- `response` is the EXACT assistant text (a single JSON object per the
  contract) serialized as a JSON string. No markdown fences around it.
- One line per item, keyed by `input_hash`. Do not reorder, do not merge.
- Do not edit any other field or file.

Output contract (verbatim):
{shape}
"""

    def write_batches(
        self,
        items: list[dict[str, str]],
        out_dir: Path,
        *,
        prompt_version: str,
        batch_size: int = 8,
    ) -> list[Path]:
        out_dir.mkdir(parents=True, exist_ok=True)
        paths: list[Path] = []
        for start in range(0, len(items), batch_size):
            chunk = items[start : start + batch_size]
            batch_no = start // batch_size
            lines = [
                self.HEADER.format(
                    batch_no=batch_no,
                    n_items=len(chunk),
                    prompt_version=prompt_version,
                    shape=response_shape_instructions(),
                )
            ]
            for offset, item in enumerate(chunk):
                lines.append(
                    "\n--- ITEM {no} (input_hash={ih}) ---\nsystem:\n{system}\n\nuser:\n{user}\n".format(
                        no=start // batch_size * batch_size + offset,
                        ih=item["input_hash"],
                        system=item["system"],
                        user=item["user"],
                    )
                )
            path = out_dir / f"batch_{batch_no:04d}.md"
            path.write_text("\n".join(lines), encoding="utf-8")
            paths.append(path)
        return paths
