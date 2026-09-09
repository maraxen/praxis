"""P2.5 corpus assembly + slice gate (backlog 480, task_id 260825_copilot_pipeline_spec).

Merges the three landed generation branches into ONE FunctionGemma-native
JSONL corpus under ``training/assemble/out/``:

- ``training/golden/golden_pairs.jsonl``        P2.1 human-authored golden set (88)
- ``training/out/corpus_p23_smoke.jsonl``       P2.3 coverage-floor generator output
- ``training/overlay_gen/out/overlay_smoke.jsonl`` P2.4 naturalness-overlay output

Every emitted row carries EXACTLY the keys ``{metadata, tools, messages}``
(mobile-actions convention, research doc §2a): ``metadata`` is the FINAL
assembled split ("train" | "eval") assigned here per split rules -- this is
the metadata normalization deliverable; nothing downstream may guess it.
Everything else (provenance, ambiguity class, verb, lineage) rides in a
parallel sidecar JSONL, line N <-> corpus line N, mirroring the golden set's
own pairs/sidecar pattern.

Split policy (D7/D8 + task AC):
- golden-provenance rows ALL land in eval (human-authored instruments stay
  out of training by construction);
- synthetic rows stratify by (provenance x ambiguity-class x verb), sorted by
  record_id, with the LAST k rows of each stratum going to eval,
  k = min(n - 1, floor(n * EVAL_FRACTION)) bumped to >= 1 when n >= 4 --
  train-first bias keeps D7 negative mixing stocked while every stratum big
  enough to matter gets held-out representation.
Eval and train are disjoint BY CONSTRUCTION: each record is assigned exactly
once from its stratum membership.

The developer turn of EVERY row byte-matches
``training/assemble/developer_scaffold_template.txt`` (research §2a scaffold
verbatim, date/timestamp injection OMITTED per D6-rev2).

Determinism / idempotency (D9, R4): assembly is a pure function of the three
committed input files plus this package's constants. Teacher outputs were
already cached content-addressed upstream ((prompt_version, input_hash) keys),
so same inputs => same corpus bytes; no timestamps enter any artifact byte.
"""

from .build import (
    ASSEMBLY_VERSION,
    CLASS_MAP,
    CORPUS_NAME,
    EVAL_FRACTION,
    MANIFEST_NAME,
    SIDECAR_NAME,
    build_artifacts,
    main,
)

__all__ = [
    "ASSEMBLY_VERSION",
    "CLASS_MAP",
    "CORPUS_NAME",
    "EVAL_FRACTION",
    "MANIFEST_NAME",
    "SIDECAR_NAME",
    "build_artifacts",
    "main",
]
