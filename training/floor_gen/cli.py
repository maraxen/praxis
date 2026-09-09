"""CLI for the P2.3 coverage-floor generator.

Run from training/ (or anywhere floor_gen is importable):

    # live titanix smoke batch over 12 round-robin cells:
    uv run --no-project python -m floor_gen.cli generate --backend titanix --limit 12

    # full-scale pass via Gemini 3.7 Flash (agy CLI; no API key needed;
    # --batch-size groups many items per teacher call, default GEMINI_BATCH_SIZE):
    uv run --no-project python -m floor_gen.cli generate --backend gemini --batch-size 20

    # write ox-alpha worker batch files instead of calling any HTTP backend:
    uv run --no-project python -m floor_gen.cli batches --limit 12

    # rebuild the corpus from cache ONLY; loud error on any miss; the output
    # must be byte-identical to the original run (R4/D9 proof):
    uv run --no-project python -m floor_gen.cli regenerate --manifest out/manifest.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from floor_gen.cache import TeacherCache, TeacherCacheError, compute_cache_key
from floor_gen.corpus import (
    CorpusError,
    build_manifest,
    generate_corpus,
    parse_teacher_raw,
    validate_class_shape,
    write_outputs,
)
from floor_gen.matrix import MatrixError, committed_matrix_path, load_matrix
from floor_gen.prompts import build_prompt
from floor_gen.synth import synthesize_example
from floor_gen.teachers import FakeTeacher, GeminiTeacher, OxAlphaBatchWriter, TitanixTeacher
from floor_gen.versions import GEMINI_BATCH_SIZE, PROMPT_VERSION

_TRAINING_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CACHE_DIR = _TRAINING_ROOT / "cache"
DEFAULT_OUT_DIR = _TRAINING_ROOT / "out"
DEFAULT_BATCH_DIR = _TRAINING_ROOT / "floor_gen" / "oxalpha_batches"


def _selected_cells(args: argparse.Namespace):
    matrix = load_matrix(committed_matrix_path())
    if args.cells:
        ids = [c.strip() for c in args.cells.split(",") if c.strip()]
        by_id = {cell.cell_id: cell for cell in matrix.cells}
        unknown = set(ids) - set(by_id)
        if unknown:
            raise CorpusError(f"unknown cell ids: {sorted(unknown)}")
        return matrix, tuple(by_id[cid] for cid in ids)
    from floor_gen.matrix import cells_round_robin

    ordered = cells_round_robin(matrix.cells)
    if args.limit is not None:
        ordered = ordered[: args.limit]
    return matrix, ordered


def _backend(args: argparse.Namespace) -> "TitanixTeacher | GeminiTeacher | FakeTeacher":
    timeout = getattr(args, "teacher_timeout", None)
    if args.backend == "titanix":
        return TitanixTeacher(**({"timeout_s": timeout} if timeout else {}))
    if args.backend == "gemini":
        return GeminiTeacher(**({"timeout_s": timeout} if timeout else {}))
    if args.backend == "fake":
        return FakeTeacher()
    raise ValueError(f"unknown backend {args.backend}")  # pragma: no cover - argparse guards


def cmd_generate(args: argparse.Namespace) -> int:
    matrix, cells = _selected_cells(args)
    cache = TeacherCache(Path(args.cache_dir))
    backend = _backend(args)

    rows, stats = generate_corpus(
        matrix, backend, cache, selected_cell_ids=tuple(cells), batch_size=args.batch_size,
        verify_execution=not args.skip_execution_verify,
    )
    manifest = build_manifest(
        matrix, stats, [cell.cell_id for cell in cells]
    )
    corpus_path, manifest_path = write_outputs(
        Path(args.out_dir), rows, manifest, corpus_name=args.corpus_name
    )
    print(
        f"cells={len(cells)} examples={stats.examples_total} accepted={stats.accepted} "
        f"rejected={stats.rejected} (execution_rejected={stats.execution_rejected} "
        f"by_category={json_compact(stats.execution_rejected_by_category)} "
        f"execution_skipped={stats.execution_skipped}) pass_rate={stats.pass_rate:.3f} "
        f"cache_hits={stats.cache_hits} cache_misses={stats.cache_misses} "
        f"teacher={stats.teacher_model_version} per_class={json_compact(stats.per_class)}"
    )
    print(f"corpus={corpus_path}")
    print(f"manifest={manifest_path}")
    return 0


def json_compact(obj: dict) -> str:
    import json

    return json.dumps(obj, sort_keys=True)


def cmd_batches(args: argparse.Namespace) -> int:
    matrix, cells = _selected_cells(args)
    items: list[dict[str, str]] = []
    for cell in cells:
        for index in range(cell.examples_per_cell):
            example = synthesize_example(cell, index)
            prompt = build_prompt(example)
            items.append(
                {
                    "input_hash": compute_cache_key(PROMPT_VERSION, prompt["input_hash"]),
                    "system": prompt["system"],
                    "user": prompt["user"],
                }
            )
    paths = OxAlphaBatchWriter().write_batches(
        items, Path(args.out_dir), prompt_version=PROMPT_VERSION, batch_size=args.batch_size
    )
    print(f"wrote {len(paths)} batch file(s) covering {len(items)} item(s) -> {Path(args.out_dir)}")
    return 0


def cmd_generate_natural(args: argparse.Namespace) -> int:
    """Natural-phrasing variants of every accepted floor row (in-surface and out-of-surface lanes)."""
    import json

    from floor_gen.natural import (
        build_natural_manifest,
        eval_utterances_from_sidecar,
        generate_natural_corpus,
    )

    base_corpus = Path(args.base_corpus)
    base_rows = [json.loads(l) for l in base_corpus.read_text(encoding="utf-8").splitlines() if l.strip()]
    if args.only_class:
        base_rows = [r for r in base_rows if r["matrix_cell"]["ambiguity_class"] == args.only_class]
    if args.offset:
        base_rows = base_rows[args.offset:]
    if args.limit is not None:
        base_rows = base_rows[: args.limit]  # first-batch acceptance check (prereg §4) / parallel slices
    base_manifest = json.loads((base_corpus.parent / "manifest.json").read_text(encoding="utf-8"))
    matrix = load_matrix(committed_matrix_path())
    backend = _backend(args)
    cache = TeacherCache(Path(args.cache_dir))
    eval_utts = eval_utterances_from_sidecar(Path(args.eval_sidecar)) if args.eval_sidecar else frozenset()
    rows, stats = generate_natural_corpus(
        base_rows, matrix, backend, cache, batch_size=args.batch_size, eval_utterances=eval_utts
    )
    manifest = build_natural_manifest(stats, base_corpus=str(base_corpus), base_manifest=base_manifest)
    corpus_path, manifest_path = write_outputs(
        Path(args.out_dir), rows, manifest, corpus_name=args.corpus_name, manifest_name=args.manifest_name
    )
    print(
        f"natural: base={stats.base_rows} per_class={json_compact(stats.per_class)} "
        f"teachers={json_compact(stats.teacher_model_versions)} "
        f"accepted={stats.accepted} rejected_shape={stats.rejected_shape} "
        f"rejected_filter={stats.rejected_filter} by_reason={json_compact(stats.rejected_by_reason)} "
        f"acceptance={stats.acceptance_rate:.3f} cache_hits={stats.cache_hits} cache_misses={stats.cache_misses}"
    )
    print(f"corpus={corpus_path}\nmanifest={manifest_path}")
    return 0


def cmd_regenerate(args: argparse.Namespace) -> int:
    """Rebuild purely from cache; byte-identity is the acceptance bar."""
    import json

    manifest_path = Path(args.manifest)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("prompt_version") != PROMPT_VERSION:
        raise CorpusError(
            f"manifest prompt_version {manifest.get('prompt_version')!r} != pinned {PROMPT_VERSION!r}"
        )
    matrix = load_matrix(committed_matrix_path())
    cache = TeacherCache(Path(args.cache_dir))

    class CacheOnlyBackend:
        teacher_model_version = manifest["teacher_model_version"]

        def complete(self, system: str, user: str) -> str:
            raise CorpusError("regenerate() must never call a teacher")

    # Selection order is recorded in the manifest (explicit, not re-derived).
    # verify_execution must match whatever the ORIGINAL run used, or
    # examples_total (below) will legitimately mismatch (a skip-vs-run
    # execution-verify difference changes rejected, not teacher calls) --
    # --skip-execution-verify lets the caller reproduce that choice exactly.
    rows, stats = generate_corpus(
        matrix,
        CacheOnlyBackend(),  # type: ignore[arg-type]
        cache,
        selected_cell_ids=list(manifest["selected_cell_ids"]),
        verify_execution=not args.skip_execution_verify,
    )

    expected_total = manifest["examples_total"]
    if stats.examples_total != expected_total or stats.cache_misses != 0:
        raise CorpusError(
            f"regeneration incomplete: total={stats.examples_total}/{expected_total} "
            f"misses={stats.cache_misses}"
        )
    rebuilt_manifest = build_manifest(matrix, stats, list(manifest["selected_cell_ids"]))
    corpus_path, manifest_path_out = write_outputs(
        Path(args.out_dir), rows, rebuilt_manifest, corpus_name=args.corpus_name
    )
    print(f"regenerated {stats.examples_total} examples from cache with ZERO teacher calls")
    print(f"corpus={corpus_path}")
    print("byte-compare against the original corpus to confirm R4/D9 identity")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="floor_gen", description="P2.3 coverage-floor generator")
    sub = parser.add_subparsers(dest="command", required=True)

    gen = sub.add_parser("generate", help="synthesize + NL-ify through the content-hash cache")
    gen.add_argument("--backend", choices=["titanix", "gemini", "fake"], default="titanix")
    gen.add_argument(
        "--batch-size",
        type=int,
        default=GEMINI_BATCH_SIZE,
        help="items grouped per teacher call (batch-capable backends only, e.g. gemini); ignored otherwise",
    )
    gen.add_argument("--limit", type=int, default=None, help="max CELLS (round-robin order)")
    gen.add_argument("--cells", default=None, help="explicit comma-separated cell_id selection")
    gen.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    gen.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    gen.add_argument("--corpus-name", default="corpus_p23_floor.jsonl")
    gen.add_argument(
        "--skip-execution-verify",
        action="store_true",
        help=(
            "skip the P2.2 execution-verify gate (shape validation only, pre-P2.2-wiring "
            "behavior) for fast local iteration; execution-verify is ON by default because "
            "teacher-shape validity is not proof a call actually executes correctly"
        ),
    )
    gen.set_defaults(func=cmd_generate)

    bat = sub.add_parser("batches", help="write ox-alpha spawned-worker batch files (offline)")
    bat.add_argument("--limit", type=int, default=None)
    bat.add_argument("--cells", default=None)
    bat.add_argument("--out-dir", default=str(DEFAULT_BATCH_DIR))
    bat.add_argument("--batch-size", type=int, default=8)
    bat.set_defaults(func=cmd_batches)

    nat = sub.add_parser("generate-natural", help="natural-phrasing variants of the accepted floor rows (P2.6b lane)")
    nat.add_argument("--backend", choices=["titanix", "gemini", "fake"], default="gemini")
    nat.add_argument("--batch-size", type=int, default=GEMINI_BATCH_SIZE)
    nat.add_argument("--base-corpus", default=str(DEFAULT_OUT_DIR / "corpus_p23_floor.jsonl"))
    nat.add_argument("--eval-sidecar", default=str(_TRAINING_ROOT / "assemble" / "out" / "corpus_p25_sidecar.jsonl"),
                     help="assembled sidecar whose split=eval utterances must not be duplicated ('' to disable)")
    nat.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    nat.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    nat.add_argument("--corpus-name", default="corpus_p23_floor_natural.jsonl")
    nat.add_argument("--manifest-name", default="manifest_natural.json")
    nat.add_argument("--limit", type=int, default=None, help="first N base rows only (acceptance check)")
    nat.add_argument("--offset", type=int, default=0, help="skip the first N base rows (parallel cache warming)")
    nat.add_argument("--only-class", choices=["none", "missing-slot", "ambiguous-referent", "out-of-surface"],
                     default=None, help="restrict to base rows of one ambiguity class (cache warming per lane)")
    nat.add_argument("--teacher-timeout", type=float, default=None,
                     help="per-call teacher timeout in seconds (default: backend's 180)")
    nat.set_defaults(func=cmd_generate_natural)

    regen = sub.add_parser("regenerate", help="rebuild corpus from cache only (zero calls)")
    regen.add_argument("--manifest", required=True)
    regen.add_argument("--cache-dir", default=str(DEFAULT_CACHE_DIR))
    regen.add_argument("--out-dir", default=str(DEFAULT_OUT_DIR))
    regen.add_argument("--corpus-name", default="corpus_p23_floor.jsonl")
    regen.add_argument(
        "--skip-execution-verify",
        action="store_true",
        help="must match the ORIGINAL generate run's choice, or examples_total/rejected won't reproduce",
    )
    regen.set_defaults(func=cmd_regenerate)

    args = parser.parse_args(argv)
    try:
        return int(args.func(args) or 0)
    except (CorpusError, MatrixError, TeacherCacheError) as exc:
        print(f"FATAL: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
