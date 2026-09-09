#!/usr/bin/env bash
# Run a command on a compute node with the bathos catalog wired to the
# project mirror ({remote_root}/.bth/catalog) instead of the job user's HOME
# catalog. Use it as the FIRST word of any `myxcel submit-job --command` /
# `bth submit -- ...` that contains `bth run`:
#
#     myxcel submit-job engaging praxis --preset gpu \
#         --command "scripts/slurm/bth_run.sh env HF_HUB_OFFLINE=1 bth run ... -- ..."
#
# Why: `scripts/slurm/_bth_env.sh` (written by `bth remote add`, checked by
# `bth submit`) exports BTH_CATALOG_DIR, but nothing sourced it for the P2.6
# jobs, so their fragments landed in ~/.bth/catalog on the cluster and
# `bth sync engaging --pull` had nothing to pull (lesson 469). Do not edit
# _bth_env.sh itself; bathos regenerates it. It sets `set -euo pipefail`, which
# this wrapper deliberately keeps for the exec'd command's argument expansion.
#
# Optional provenance: exports PRAXIS_GIT_SHA / PRAXIS_GIT_BRANCH if the
# submitter passed them (the rsync mirror has no .git, so the trainer's
# manifest would otherwise record an empty git block).
set -euo pipefail
_HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=_bth_env.sh
source "${_HERE}/_bth_env.sh"
export PRAXIS_GIT_SHA="${PRAXIS_GIT_SHA:-}"
export PRAXIS_GIT_BRANCH="${PRAXIS_GIT_BRANCH:-}"
if [[ $# -eq 0 ]]; then
    echo "bth_run.sh: no command given" >&2
    exit 64
fi
exec "$@"
