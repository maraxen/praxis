"""Coxswain Increment-1 corpus ingestion pipeline.

This package orchestrates the five-stage admission and measurement pipeline:
  1. Registry loading and invariant verification (sources.py)
  2. License scanning and descend-rule verification (licenses.py)
  3. Recipe extraction and token classification (recipes.py)
  4. Eval split commitment and leak verification (eval_split.py)
  5. Drift audit and canonical table verification (audit.py)
  6. Coverage-gap analysis (gap.py)

Entry points are module-per-command: python -m ingest.{licenses,recipes,eval_split,audit,gap}.
There is no central dispatcher; python -m ingest is a signpost only.
"""
