"""Praxis copilot training pipeline (P2.1, backlog 4476).

Layout (spec `.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md` rev2):

- ``praxis_training.golden_build``  authored golden pair set + generator (training/golden/).
- ``praxis_training.baseline_eval`` FunctionGemma baseline eval harness (training/eval/).

Boundary reminder (F2-rev2): this package MAY import coxswain.plr.* / praxis.backend.*;
nothing in coxswain/ may ever import THIS package.
"""
