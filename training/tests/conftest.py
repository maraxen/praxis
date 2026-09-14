"""Pytest path setup for training/tests.

Puts ``training/`` itself on sys.path so ``import overlay_gen`` resolves to
``training/overlay_gen/``, and the repo root second so ``coxswain.plr.*``
resolves even without the workspace editable install. This file is
packaging-independent BY DESIGN: three parallel workers share
``training/pyproject.toml``, so the tests never rely on its contents.
"""

import sys
from pathlib import Path

TRAINING_DIR = Path(__file__).resolve().parents[1]
REPO_ROOT = TRAINING_DIR.parent

for candidate in (str(TRAINING_DIR), str(REPO_ROOT)):
    if candidate not in sys.path:
        sys.path.insert(0, candidate)
