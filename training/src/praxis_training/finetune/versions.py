"""Pinned recipe constants for the P2.6 fine-tune (spec D5, prereg 260901).

Everything a training run's manifest must be able to reproduce from lives
here as DATA, so a run is fully described by ``(RECIPE_VERSION, arm, seed)``
plus the corpus sha. Change a number -> bump ``RECIPE_VERSION``.
"""

from __future__ import annotations

from typing import Final, Mapping

RECIPE_VERSION: Final[str] = "0.1.0"

#: Base checkpoint and the revision every P2.5/P2.6 report is pinned to.
BASE_MODEL: Final[str] = "google/functiongemma-270m-it"
BASE_REVISION: Final[str] = "39eccb091651513a5dfb56892d3714c1b5b8276c"

#: Assembled P2.5 corpus (repo-relative). The sidecar is line-aligned.
CORPUS_REL: Final[str] = "training/assemble/out/corpus_p25.jsonl"
SIDECAR_REL: Final[str] = "training/assemble/out/corpus_p25_sidecar.jsonl"

POSITIVE_CLASS: Final[str] = "clean_parse"
NEGATIVE_CLASSES: Final[tuple[str, ...]] = (
    "missing_slot",
    "ambiguous_referent",
    "out_of_surface",
)

#: Ablation arms: negatives-per-positive ratio after dedup. ``None`` = raw
#: split (every train row). B: negatives == positives (50% negative);
#: C: negatives == positives / 2 (33% negative). Positives are never
#: subsampled; negative quotas are split across classes proportionally to
#: the assembled class counts (largest-remainder rounding).
ARMS: Final[Mapping[str, float | None]] = {"A": None, "B": 1.0, "C": 0.5}

#: Fixed across every arm so the ablation isolates mixing. Mobile-Actions
#: (research §2b) values except epochs/effective batch: their 2 epochs x
#: batch 32 on 9.6k rows is ~600 optimizer steps; on <=584 rows that would be
#: ~36 steps, so effective batch 16 x 8 epochs (~120-290 steps by arm) is the
#: one recorded recipe deviation (prereg doc).
HYPERPARAMS: Final[Mapping[str, object]] = {
    "learning_rate": 1e-5,
    "lr_scheduler_type": "cosine",
    "warmup_ratio": 0.1,
    "num_train_epochs": 8,
    "per_device_train_batch_size": 4,
    "gradient_accumulation_steps": 4,
    "bf16": True,
    "gradient_checkpointing": True,
    "optim": "adamw_torch_fused",
    "completion_only_loss": True,
    "packing": False,
    "max_length_margin": 100,
}

#: Greedy decode settings shared with the eval harness (F4/D3).
EVAL_MAX_NEW_TOKENS: Final[int] = 128

__all__ = [
    "RECIPE_VERSION",
    "BASE_MODEL",
    "BASE_REVISION",
    "CORPUS_REL",
    "SIDECAR_REL",
    "POSITIVE_CLASS",
    "NEGATIVE_CLASSES",
    "ARMS",
    "HYPERPARAMS",
    "EVAL_MAX_NEW_TOKENS",
]
