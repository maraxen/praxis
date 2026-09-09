# Source from SLURM scripts: source scripts/slurm/_bth_env.sh
# Sets BTH_PROJECT_SLUG, BTH_PROJECT_ROOT, BTH_WORKSPACE_ROOT, and BTH_CATALOG_DIR so bth runs transparently in batch jobs.
set -euo pipefail
export BTH_PROJECT_SLUG="praxis"
export BTH_PROJECT_ROOT="/home/maarxaru/projects/praxis"
# Deterministic workspace filesystem root: in a SLURM spool dir, `git rev-parse
# --show-toplevel` may resolve to an unrelated repo (or fail), so pin it to the
# absolute project root for worktree-aware resolution (spec 260611).
export BTH_WORKSPACE_ROOT="/home/maarxaru/projects/praxis"
export BTH_CATALOG_DIR="/home/maarxaru/projects/praxis/.bth/catalog"
