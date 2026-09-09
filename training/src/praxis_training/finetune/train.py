"""P2.6 fine-tune CLI: ``python -m praxis_training.finetune``.

One run = one ablation arm under the pinned recipe (``versions.py``):

    python -m praxis_training.finetune --arm B --out-dir training/out/p26/B
    python -m praxis_training.finetune --arm B --dry-run          # L1 gate
    python -m praxis_training.finetune --arm B --smoke --out-dir $TMPDIR/s   # L2/L3
    python -m praxis_training.finetune --arm B --eval-after --out-dir ...    # tracked run

Outputs under ``--out-dir``:

- ``train_manifest.json`` -- everything needed to reproduce + audit the run
  (selected record_ids, dedup drops, max_length + length stats, effective
  hyperparameters, library versions, git state, checkpoint sha256, eval headline).
- ``checkpoint/`` -- HF-format weights + tokenizer (NOT committed; ~540 MB).
- ``eval_report.json`` -- ``baseline_eval`` report over the eval split (``--eval-after``).
- ``result.json`` -- flat results dict; also written to ``$BTH_RESULTS_PATH`` for bathos.

Heavy imports (torch/transformers/trl/datasets) happen inside functions.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
import os
import platform
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, Sequence

from . import mixing
from .render import RenderedPair, render_all
from .versions import (
    ARMS,
    BASE_MODEL,
    BASE_REVISION,
    CORPUS_REL,
    EVAL_MAX_NEW_TOKENS,
    HYPERPARAMS,
    RECIPE_VERSION,
    SIDECAR_REL,
)

log = logging.getLogger("praxis_training.finetune")

SMOKE_MAX_ROWS = 8
SMOKE_MAX_STEPS = 2
SMOKE_EVAL_ROWS = 8


def repo_root() -> Path:
    return Path(__file__).resolve().parents[4]


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def checkpoint_digest(ckpt_dir: Path) -> dict[str, Any]:
    """sha256 over (relative name, file sha256) of every file, plus byte total."""
    files = sorted(p for p in ckpt_dir.rglob("*") if p.is_file())
    lines = []
    total = 0
    for p in files:
        lines.append(f"{p.relative_to(ckpt_dir).as_posix()}:{_sha256_file(p)}")
        total += p.stat().st_size
    combined = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    return {"sha256": combined, "bytes": total, "n_files": len(files)}


def _git_state(root: Path) -> dict[str, Any]:
    """Code provenance for the manifest.

    On the Engaging rsync mirror there is no ``.git``; the P2.6 manifests
    therefore carried an EMPTY git block (promotion doc §2). The submitter
    can pass the local HEAD through ``PRAXIS_GIT_SHA`` / ``PRAXIS_GIT_BRANCH``
    (``scripts/slurm/bth_run.sh`` forwards them); when neither git nor the
    override is available the block says so instead of looking like a
    silently blank field.
    """

    def run(*args: str) -> str | None:
        try:
            return subprocess.run(
                ["git", *args], cwd=root, capture_output=True, text=True, check=True
            ).stdout.strip()
        except Exception:  # noqa: BLE001 - provenance is best-effort off-repo
            return None

    sha = run("rev-parse", "HEAD")
    if sha:
        return {
            "sha": sha,
            "branch": run("rev-parse", "--abbrev-ref", "HEAD") or "",
            "dirty": bool(run("status", "--porcelain", "--untracked-files=no")),
            "available": True,
            "source": "git",
        }
    env_sha = os.environ.get("PRAXIS_GIT_SHA", "").strip()
    if env_sha:
        return {
            "sha": env_sha,
            "branch": os.environ.get("PRAXIS_GIT_BRANCH", "").strip(),
            "dirty": None,
            "available": True,
            "source": "env:PRAXIS_GIT_SHA",
            "note": "no git checkout at root (rsync mirror); sha supplied by the submitter",
        }
    return {
        "sha": "",
        "branch": "",
        "dirty": None,
        "available": False,
        "source": "none",
        "note": "no git checkout at root and PRAXIS_GIT_SHA unset -- provenance unknown",
    }


def _lib_versions() -> dict[str, str]:
    out: dict[str, str] = {"python": platform.python_version()}
    for name in ("torch", "transformers", "trl", "datasets", "accelerate"):
        try:
            out[name] = __import__(name).__version__
        except Exception:  # noqa: BLE001
            out[name] = "unavailable"
    return out


def _load_tokenizer(model_id: str, revision: str):
    from transformers import AutoTokenizer

    if Path(model_id).is_dir():
        return AutoTokenizer.from_pretrained(model_id, local_files_only=True)
    return AutoTokenizer.from_pretrained(model_id, revision=revision)


def length_stats(tokenizer, pairs: Sequence[RenderedPair]) -> dict[str, Any]:
    """Token lengths of prompt+completion, tokenized exactly as TRL does
    (default special tokens: the tokenizer prepends the single <bos>)."""
    lengths = [len(tokenizer(p.prompt + p.completion)["input_ids"]) for p in pairs]
    prompt_lengths = [len(tokenizer(p.prompt)["input_ids"]) for p in pairs]
    lengths_sorted = sorted(lengths)
    n = len(lengths)
    p95 = lengths_sorted[min(n - 1, int(0.95 * n))] if n else 0
    return {
        "n": n,
        "max": max(lengths) if n else 0,
        "min": min(lengths) if n else 0,
        "mean": (sum(lengths) / n) if n else 0.0,
        "p95": p95,
        "prompt_max": max(prompt_lengths) if n else 0,
        "over_1024": sum(1 for x in lengths if x > 1024),
        "over_2048": sum(1 for x in lengths if x > 2048),
        "over_4096": sum(1 for x in lengths if x > 4096),
    }


def select_training_rows(corpus: Path, sidecar: Path, arm: str, seed: int,
                         max_rows: int | None = None) -> tuple[list[mixing.CorpusRow], dict[str, Any]]:
    rows = mixing.load_corpus(corpus, sidecar)
    train = mixing.train_rows(rows)
    kept, dropped = mixing.dedup_rows(train)
    selected = mixing.select_arm(kept, arm, seed)
    summary = mixing.arm_summary(selected, dedup_dropped=dropped, train_total=len(train), arm=arm, seed=seed)
    if max_rows is not None:
        selected = selected[:max_rows]
        summary["smoke_truncated_to"] = len(selected)
    return selected, summary


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=False) + "\n", encoding="utf-8")


def run_training(*, pairs: Sequence[RenderedPair], tokenizer, model_id: str, revision: str,
                 out_dir: Path, max_length: int, seed: int, device: str,
                 max_steps: int | None, smoke: bool) -> dict[str, Any]:
    import torch
    from datasets import Dataset
    from transformers import AutoModelForCausalLM
    from trl import SFTConfig, SFTTrainer

    use_cuda = device.startswith("cuda") and torch.cuda.is_available()
    use_bf16 = bool(use_cuda and torch.cuda.is_bf16_supported())
    hp = dict(HYPERPARAMS)
    margin = hp.pop("max_length_margin")
    hp["bf16"] = use_bf16
    # Fused AdamW is a CUDA-path choice; on CPU (smoke) the plain kernel is the
    # supported one. Recorded in the manifest either way.
    if not use_cuda:
        hp["optim"] = "adamw_torch"
    if smoke:
        hp["per_device_train_batch_size"] = 1
        hp["gradient_accumulation_steps"] = 1
        hp["gradient_checkpointing"] = False

    load_kwargs: dict[str, Any] = (
        {"local_files_only": True} if Path(model_id).is_dir() else {"revision": revision}
    )
    model = AutoModelForCausalLM.from_pretrained(
        model_id,
        torch_dtype=torch.bfloat16 if use_bf16 else torch.float32,
        attn_implementation="eager",
        **load_kwargs,
    )

    ds = Dataset.from_dict({
        "prompt": [p.prompt for p in pairs],
        "completion": [p.completion for p in pairs],
    })

    cfg = SFTConfig(
        output_dir=str(out_dir / "trainer"),
        learning_rate=hp["learning_rate"],
        lr_scheduler_type=hp["lr_scheduler_type"],
        warmup_ratio=hp["warmup_ratio"],
        num_train_epochs=hp["num_train_epochs"],
        per_device_train_batch_size=hp["per_device_train_batch_size"],
        gradient_accumulation_steps=hp["gradient_accumulation_steps"],
        bf16=hp["bf16"],
        gradient_checkpointing=hp["gradient_checkpointing"],
        optim=hp["optim"],
        completion_only_loss=hp["completion_only_loss"],
        packing=hp["packing"],
        max_length=max_length,
        seed=seed,
        data_seed=seed,
        max_steps=max_steps if max_steps is not None else -1,
        logging_steps=5,
        save_strategy="no",
        report_to=[],
        dataloader_num_workers=0,
        use_cpu=not use_cuda,
    )
    trainer = SFTTrainer(model=model, args=cfg, train_dataset=ds, processing_class=tokenizer)

    # Guard the tokenization contract before spending a single step: exactly
    # one <bos>, and the completion mask covers only the completion tokens.
    sample = trainer.train_dataset[0]
    bos_id = tokenizer.bos_token_id
    n_bos = sum(1 for t in sample["input_ids"] if t == bos_id)
    if n_bos != 1:
        raise RuntimeError(f"tokenization contract violated: {n_bos} <bos> tokens in the first example")
    mask = sample.get("completion_mask")
    if mask is None or not any(mask) or all(mask):
        raise RuntimeError("tokenization contract violated: completion_mask missing or degenerate")
    prompt_len = len(tokenizer(pairs[0].prompt)["input_ids"])
    if sum(1 for m in mask if m == 0) != prompt_len:
        raise RuntimeError(
            f"tokenization contract violated: {sum(1 for m in mask if m == 0)} masked tokens "
            f"vs prompt length {prompt_len}"
        )

    t0 = time.time()
    result = trainer.train()
    runtime = time.time() - t0

    ckpt_dir = out_dir / "checkpoint"
    trainer.save_model(str(ckpt_dir))
    tokenizer.save_pretrained(str(ckpt_dir))

    history = [h for h in trainer.state.log_history if "loss" in h or "train_loss" in h]
    metrics = dict(result.metrics)
    info = {
        "device": "cuda" if use_cuda else "cpu",
        "cuda_device_name": torch.cuda.get_device_name(0) if use_cuda else None,
        "effective_hyperparams": hp | {"max_length": max_length, "seed": seed,
                                      "max_steps": max_steps if max_steps is not None else -1},
        "global_steps": trainer.state.global_step,
        "epochs_completed": trainer.state.epoch,
        "train_loss": metrics.get("train_loss"),
        "train_runtime_s": runtime,
        "trainer_metrics": metrics,
        "log_history": history,
        "checkpoint_dir": str(ckpt_dir),
    }
    del trainer, model
    if use_cuda:
        torch.cuda.empty_cache()
    return info


def run_eval(*, ckpt_dir: Path, corpus: Path, sidecar: Path, device: str, label: str,
             max_rows: int | None, out_path: Path, dump_outputs: Path | None = None) -> dict[str, Any]:
    """Score ``ckpt_dir`` on the eval split of (corpus, sidecar). ``dump_outputs``
    (P2.6b) persists the raw generations as a recorded-outputs artifact so the
    report can be re-scored without inference (260902 amendment practice)."""
    import torch

    from praxis_training.baseline_eval.runner import PairSet, load_pair_set, run_local

    use_cuda = device.startswith("cuda") and torch.cuda.is_available()
    pair_set = load_pair_set(corpus, sidecar).filter_split("eval")
    if max_rows is not None:
        pair_set = PairSet(pairs=pair_set.pairs[:max_rows], intents=pair_set.intents[:max_rows])
    report = run_local(
        pair_set, str(ckpt_dir), revision="local",
        device="cuda" if use_cuda else "cpu",
        dtype="bfloat16" if (use_cuda and torch.cuda.is_bf16_supported()) else None,
        max_new_tokens=EVAL_MAX_NEW_TOKENS, split=None, model_label=label,
        dump_outputs=dump_outputs,
    )
    _write_json(out_path, report)
    return report


def _headline(report: dict[str, Any]) -> dict[str, Any]:
    def stat(key: str) -> dict[str, Any]:
        s = report[key]
        return {"value": s["value"], "successes": s["successes"], "n": s["n"], "wilson95": s["wilson95"]}

    return {
        "n_examples": report["n_examples"],
        "exact_match_accuracy": stat("exact_match_accuracy"),
        "clarify_recall": stat("clarify_recall"),
        "clarify_precision": stat("clarify_precision"),
        "tripwire_out_of_surface_tool_calls": report["tripwire_out_of_surface_tool_calls"],
        "per_class_exact": {k: v["exact_match"]["value"] for k, v in report["per_class"].items()},
    }


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="python -m praxis_training.finetune",
        description="P2.6 FunctionGemma fine-tune: one pre-registered ablation arm per run.",
    )
    p.add_argument("--arm", required=True, choices=sorted(ARMS), help="mixing arm (versions.ARMS)")
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--out-dir", type=Path, default=None, help="run directory (required unless --dry-run)")
    p.add_argument("--corpus", type=Path, default=None, help=f"default {CORPUS_REL}")
    p.add_argument("--sidecar", type=Path, default=None, help=f"default {SIDECAR_REL}")
    p.add_argument("--model", default=BASE_MODEL, help="HF id or local checkpoint dir")
    p.add_argument("--revision", default=BASE_REVISION)
    p.add_argument("--device", default=None, help="cuda|cpu (default: cuda if available)")
    p.add_argument("--dry-run", action="store_true", help="L1: select + render + lengths, no model load")
    p.add_argument("--smoke", action="store_true",
                   help=f"L2/L3: {SMOKE_MAX_ROWS} rows, {SMOKE_MAX_STEPS} steps, real max_length, eval on {SMOKE_EVAL_ROWS}")
    p.add_argument("--eval-after", action="store_true", help="score the checkpoint on the eval split")
    p.add_argument("--compare-report", type=Path, default=None,
                   help="P2.6b: OLD report on the same split; fills the pre-registered prediction fields")
    p.add_argument("--probe-pairs", type=Path, default=None, help="P2.6b: probe corpus (scored as a second report)")
    p.add_argument("--probe-sidecar", type=Path, default=None)
    p.add_argument("--results-out", type=Path, default=None, help="flat results JSON (default out-dir/result.json)")
    p.add_argument("-v", "--verbose", action="store_true")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
        stream=sys.stderr,
    )
    root = repo_root()
    corpus = args.corpus or (root / CORPUS_REL)
    sidecar = args.sidecar or (root / SIDECAR_REL)
    if not args.dry_run and args.out_dir is None:
        log.error("--out-dir is required unless --dry-run")
        return 2

    device = args.device
    if device is None:
        try:
            import torch

            device = "cuda" if torch.cuda.is_available() else "cpu"
        except Exception:  # noqa: BLE001
            device = "cpu"

    started = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    selected, summary = select_training_rows(
        corpus, sidecar, args.arm, args.seed, max_rows=SMOKE_MAX_ROWS if args.smoke else None
    )
    log.info("arm %s: selected %d rows (%s); dedup dropped %d",
             args.arm, summary["selected_total"], summary["selected_by_class"], summary["dedup_dropped"])

    tokenizer = _load_tokenizer(args.model, args.revision)
    pairs = render_all(tokenizer, selected)
    lengths = length_stats(tokenizer, pairs)
    max_length = lengths["max"] + int(HYPERPARAMS["max_length_margin"])
    log.info("lengths: max=%d p95=%d mean=%.1f prompt_max=%d -> max_length=%d",
             lengths["max"], lengths["p95"], lengths["mean"], lengths["prompt_max"], max_length)

    manifest: dict[str, Any] = {
        "artifact": "praxis-p26-train-manifest",
        "recipe_version": RECIPE_VERSION,
        "arm": args.arm,
        "seed": args.seed,
        "base_model": args.model,
        "base_revision": args.revision if not Path(args.model).is_dir() else "local",
        "pinned_base_revision": BASE_REVISION,
        "corpus": {"path": str(corpus.relative_to(root) if corpus.is_relative_to(root) else corpus),
                   "sha256": _sha256_file(corpus)},
        "sidecar": {"path": str(sidecar.relative_to(root) if sidecar.is_relative_to(root) else sidecar),
                    "sha256": _sha256_file(sidecar)},
        "mixing": summary,
        "lengths": lengths,
        "max_length": max_length,
        "hyperparams_pinned": dict(HYPERPARAMS),
        "mode": "dry_run" if args.dry_run else ("smoke" if args.smoke else "full"),
        "device_requested": device,
        "git": _git_state(root),
        "libs": _lib_versions(),
        "started_utc": started,
    }

    if args.dry_run:
        print(json.dumps({k: v for k, v in manifest.items() if k != "mixing"} |
                         {"mixing": {k: v for k, v in summary.items() if not k.endswith("record_ids")}},
                         indent=2))
        if args.out_dir is not None:
            _write_json(args.out_dir / "train_manifest.json", manifest)
        return 0

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    _write_json(out_dir / "train_manifest.json", manifest)  # pre-training snapshot

    train_info = run_training(
        pairs=pairs, tokenizer=tokenizer, model_id=args.model, revision=args.revision,
        out_dir=out_dir, max_length=max_length, seed=args.seed, device=device,
        max_steps=SMOKE_MAX_STEPS if args.smoke else None, smoke=args.smoke,
    )
    ckpt_dir = Path(train_info["checkpoint_dir"])
    digest = checkpoint_digest(ckpt_dir)
    manifest["training"] = train_info
    manifest["checkpoint"] = digest | {"dir": str(ckpt_dir)}
    _write_json(out_dir / "train_manifest.json", manifest)
    log.info("trained: steps=%s loss=%s runtime=%.0fs checkpoint sha256=%s (%d bytes)",
             train_info["global_steps"], train_info["train_loss"], train_info["train_runtime_s"],
             digest["sha256"][:12], digest["bytes"])

    results: dict[str, Any] = {
        "arm": args.arm,
        "seed": args.seed,
        "recipe_version": RECIPE_VERSION,
        "mode": manifest["mode"],
        "n_train": summary["selected_total"],
        "negative_fraction": summary["negative_fraction"],
        "max_length": max_length,
        "global_steps": train_info["global_steps"],
        "train_loss": train_info["train_loss"],
        "checkpoint_sha256": digest["sha256"],
    }

    if args.eval_after:
        label = f"p26 arm {args.arm} seed {args.seed} recipe {RECIPE_VERSION} sha256:{digest['sha256']}"
        report = run_eval(
            ckpt_dir=ckpt_dir, corpus=corpus, sidecar=sidecar, device=device, label=label,
            max_rows=SMOKE_EVAL_ROWS if args.smoke else None, out_path=out_dir / "eval_report.json",
            dump_outputs=out_dir / "eval_dump.json",
        )
        head = _headline(report)
        manifest["eval"] = head | {"report": str(out_dir / "eval_report.json")}
        _write_json(out_dir / "train_manifest.json", manifest)
        results.update({
            "n_eval": head["n_examples"],
            "exact_match_accuracy": head["exact_match_accuracy"]["value"],
            "clarify_recall": head["clarify_recall"]["value"],
            "clarify_precision": head["clarify_precision"]["value"],
            "tripwire_out_of_surface_tool_calls": head["tripwire_out_of_surface_tool_calls"],
        })
        log.info("eval n=%d acc=%.3f recall=%s prec=%s tripwire=%d",
                 head["n_examples"], head["exact_match_accuracy"]["value"] or 0.0,
                 head["clarify_recall"]["value"], head["clarify_precision"]["value"],
                 head["tripwire_out_of_surface_tool_calls"])
        if args.compare_report is not None:
            # P2.6c superset of the P2.6b checks (same field names; adds tripwire3_recovered).
            from praxis_training.finetune.p26c_predictions import evaluate_predictions

            old_report = json.loads(Path(args.compare_report).read_text(encoding="utf-8"))
            pred = evaluate_predictions(old_report, report)
            _write_json(out_dir / "predictions.json", pred | {"compare_report": str(args.compare_report)})
            manifest["predictions"] = {k: v for k, v in pred.items() if not k.endswith("_ids") and not k.endswith("categories")}
            results.update({
                "surface6_recovered": pred["surface6_recovered"],
                "verb_category_migrated": pred["verb_category_migrated"],
                "flips_hit_to_miss": pred["flips_hit_to_miss"],
                "tripwire3_recovered": pred["tripwire3_recovered"],
            })
            log.info("predictions: surface6=%d/6 verb_migrated=%d/22 hit->miss=%d miss->hit=%d",
                     pred["surface6_recovered"], pred["verb_category_migrated"],
                     pred["flips_hit_to_miss"], pred["flips_miss_to_hit"])
        if args.probe_pairs is not None:
            from praxis_training.finetune.p26c_predictions import probe_split

            probe_sidecar = args.probe_sidecar or args.probe_pairs.with_name(args.probe_pairs.stem + "_sidecar.jsonl")
            probe = run_eval(
                ckpt_dir=ckpt_dir, corpus=args.probe_pairs, sidecar=probe_sidecar, device=device,
                label=label + " [probe]", max_rows=SMOKE_EVAL_ROWS if args.smoke else None,
                out_path=out_dir / "probe_report.json", dump_outputs=out_dir / "probe_dump.json",
            )
            phead = _headline(probe)
            manifest["probe_eval"] = phead | {"report": str(out_dir / "probe_report.json")}
            results.update({
                "probe_n": phead["n_examples"],
                "probe_exact_match_accuracy": phead["exact_match_accuracy"]["value"],
            } | probe_split(probe))
            log.info("probe n=%d acc=%.3f", phead["n_examples"], phead["exact_match_accuracy"]["value"] or 0.0)
        _write_json(out_dir / "train_manifest.json", manifest)

    manifest["finished_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    _write_json(out_dir / "train_manifest.json", manifest)

    results_out = args.results_out or (out_dir / "result.json")
    _write_json(results_out, results)
    bth_path = os.environ.get("BTH_RESULTS_PATH")
    if bth_path:
        _write_json(Path(bth_path), results)
    print(json.dumps(results, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
