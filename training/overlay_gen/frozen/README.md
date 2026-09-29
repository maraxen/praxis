# Frozen overlay source

`pre_plr1_notebook_rows.jsonl` holds 54 overlay rows, copied verbatim (same
bytes, same order) from the overlay committed at the previous PLR pin
`dd79c4c89bc008629a1c598ea614be5e6067d1f9`. Their source notebooks
(`hamilton-star/basic.ipynb`, `hamilton-star/foil.ipynb`,
`opentrons/ot2/hello-world.ipynb`, `opentrons/ot2/ot2-simulator.ipynb`) were
deleted/moved upstream at PLR 1.0. The calls are still valid legacy
`LiquidHandler` calls, and 6 of the rows sit in the pinned eval split
(`training/assemble/data/eval_split_pin.json`), so dropping them would break
the eval pin and shift train.

- The rows were exec-verified and teacher-paraphrased at that pin. They are
  **not** re-mined, re-verified or re-paraphrased, and keep their original
  provenance (`generator_version d42c53f2`, `prompt_version p24-naturalness-v1`).
  No marker field is added: the assembler folds provenance into corpus lineage,
  so any extra field would change the assembled bytes.
- `pre_plr1_notebook_rows.manifest.json` pins the row count and sha256
  (checked on every load), and records the origin pin and per-source counts.
- `overlay_gen/frozen.py` merges them into `overlay_full.jsonl` on
  `run_smoke --full`: live rows win content-key collisions, and a frozen row
  whose source exists at the current pin is a hard error.
- To retire a row: delete it from the `.jsonl` and re-pin the manifest sha256/count
  in the same change. Do not edit rows in place.
