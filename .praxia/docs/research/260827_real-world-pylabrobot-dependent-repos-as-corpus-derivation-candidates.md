---
title: Real-world PyLabRobot-dependent repos as corpus-derivation candidates
description: Survey of GitHub's dependency graph, plain code search, and filename-scoped dependency-file search (pyproject.toml/requirements.txt/lockfiles -- the highest-precision method found) for public repos using pylabrobot, to find real task/protocol corpora beyond the plr-cookbook for Coxswain out-of-surface and task-type coverage.
status: draft
task_id: 260825_copilot_pipeline_spec
date: '260827'
confidence: ''
sources: ''
---
# Real-world PyLabRobot-dependent repos as corpus-derivation candidates

User-directed (260827): "is there a way to see what repos depend on PLR
given it's a pypi package or look up on github? it would be good to get a
strong corpus to first derive tasks from." Extends the same coverage
question as the decision doc's §5 (`260827_teacher-backend-gemini-3-7-flash-...md`)
-- the cookbook (`chory-lab/plr-cookbook`) is one real task source; this
looks for others in actual downstream consumers.

## 0. Better method (260827 follow-up): filename-scoped dependency-file search

User follow-up: "is ther ea better way to mine for pylabrobot dependents?
is there a way to search specifically for pyproject or requirements.txt
declaration of dependencies?" **Yes, and it's a real improvement, not a
marginal one.** `gh search code "pylabrobot" --filename <name> --match file`
scopes the search to files with that exact name and requires the match be
in file CONTENT (not path), which is a MUCH higher-precision filter than
the plain `"import pylabrobot"` search in §1-3 below: it eliminates almost
all the AI-skill-documentation noise (§3) at the source, because those hits
were `.md`/`SKILL.md` files, never `pyproject.toml`/`requirements.txt`, and
it directly answers "who declares this as a dependency" rather than "who
mentions it anywhere."

Ran across `pyproject.toml`, `requirements.txt`, `uv.lock`, `poetry.lock`,
`setup.py`, `environment.yml`, `Pipfile` (60-item limit per query, the `gh`
CLI's default page cap). Consolidated, deduplicated, excluding
`PyLabRobot/pylabrobot` itself, this repo (`maraxen/praxis`), and the
`chory-lab/plr-cookbook`/`bme590-fall-2025` pair (already covered in §2's
narrative):

| Repo | Stars | Last push | Declared in | What it is |
|---|---|---|---|---|
| [`Cheshire-Labs/cheshire-drivers`](https://github.com/Cheshire-Labs/cheshire-drivers) | 0 | 2026-07-02 | pyproject.toml | "Driver interfaces + PyLabRobot wrappers and simulation drivers for the Orca lab-automation stack (AGPL)" -- a THIRD repo in the Cheshire-Labs/orca ecosystem (alongside `orca` and `swarm-client` from §2), confirming that's a real multi-repo platform, not a one-off. |
| [`vanallenlab/agentic-ai-codebase`](https://github.com/vanallenlab/agentic-ai-codebase) | 2 | 2026-06-04 | requirements.txt | "M3A agent code" -- Van Allen Lab (Dana-Farber/Broad, computational oncology). Small, but thematically the closest find to Coxswain itself: an agentic-AI codebase that depends on PLR, i.e. someone else building an LLM-agent-to-lab-automation bridge. Worth a direct look regardless of star count. |
| [`Koeng101/pylabrobot-protobuf`](https://github.com/Koeng101/pylabrobot-protobuf) | 0 | 2026-03-11 | pyproject.toml | No description, but the name says it: a protobuf schema for PLR. Potentially a useful STRUCTURAL reference (a typed call/contract representation) rather than a task-corpus source -- different value than the others in this table. |
| [`qte77/so101-biolab-automation`](https://github.com/qte77/so101-biolab-automation) | 3 | 2026-08-26 | pyproject.toml, uv.lock | Same repo as §2 -- now confirmed via an actual lockfile (`uv.lock`), the highest-confidence signal available (a resolved, installed dependency, not just declared). |
| [`SLKS99/PyFluent`](https://github.com/SLKS99/PyFluent) | 12 | 2026-04-02 | requirements.txt, setup.py | Same repo as §2, now confirmed twice over via two independent dependency files. |
| [`Tetsuwan-Scientific/plr-sandbox`](https://github.com/Tetsuwan-Scientific/plr-sandbox) | 0 | 2026-04-07 | pyproject.toml | No description. A company name ("Tetsuwan Scientific") suggests real commercial lab-automation use, not a hobby project -- worth a look despite no stars/description. |
| [`jt05610/python-graphmix`](https://github.com/jt05610/python-graphmix) | 2 | 2024-06-13 | pyproject.toml, requirements.txt | "Intelligent experiment planning and optimization powered by graph algorithms" -- stale (mid-2024) but a distinct task style (planning/optimization, not direct pipetting calls). |
| [`norle/plr-gui`](https://github.com/norle/plr-gui) | 0 | 2026-05-16 | pyproject.toml | No description -- a GUI layer over PLR, by name. |
| [`rickwierenga/plr-game-of-life`](https://github.com/rickwierenga/plr-game-of-life) | 1 | 2023-06-25 | setup.py | "Conway's Game of Life on a microplate" -- a novelty/demo project, low corpus value but a real, working PLR consumer. |
| [`rickwierenga/lwdb`](https://github.com/rickwierenga/lwdb) | 0 | 2022-11-09 | setup.py | "A centralized database of labware definitions" -- resource/labware metadata, not task/call data; possibly useful for a DIFFERENT purpose (labware coverage) than task-type coverage. |
| [`LuHesketh/GSOC-2023-LabOP`](https://github.com/LuHesketh/GSOC-2023-LabOP) | 0 | 2023-10-05 | setup.py | Google Summer of Code 2023 project: "a converter that allows specialization of Laboratory protocols for Biotechnology" -- protocol-specification-format work, possibly relevant to the assembly/scaffold side of this project rather than task NL-ification. |
| [`OrthoDim/Cereal-Delusion`](https://github.com/OrthoDim/Cereal-Delusion) | 0 | -- | environment.yml | Name gives no signal; not investigated further. |
| [`evnkm/basic_viz`](https://github.com/evnkm/basic_viz) | 0 | 2025-01-06 | requirements.txt | No description; likely a small visualization script, not a task-corpus source. |

**Libraries.io** (a public dependents-tracking site) was also tried as a
third cross-check but its `/pypi/PyLabRobot/dependent_repositories` page
returned no repo listing when fetched without an authenticated session --
dead end, not pursued further.

**Revised top picks**, combining §2 and this section: `deepmodeling/Uni-Lab-OS`
still leads on activity/popularity/structural relevance; the
**Cheshire-Labs cluster** (`orca` + `swarm-client` + `cheshire-drivers`, now
confirmed as 3 repos not 1) is the most substantial *platform*-style find;
`Pioneer-Research-Labs/ngs_library_prep` remains the best single *real
protocol* to mine calls from; and `vanallenlab/agentic-ai-codebase` is the
one worth reading first out of curiosity even at 2 stars, given how close
its stated purpose is to this project's own.

## 1. Method (and its limits)

No PyPI reverse-dependency API exists (checked: PyPI's own JSON API has no
"used by" field). Two GitHub-side methods, each incomplete on its own:

- **GitHub's dependency graph "Used by" page**
  (`github.com/PyLabRobot/pylabrobot/network/dependents?dependent_type=REPOSITORY`):
  scraped directly (logged out, no session -- `gh api` doesn't cover this
  HTML view). Returned only **9 distinct repos**. This is a KNOWN-INCOMPLETE,
  GitHub-curated sample, not an exhaustive list -- there is no visible total
  count or working pagination without a browser session, and GitHub is
  documented elsewhere to cap what this view shows.
- **GitHub code search** (`gh search code "import pylabrobot"` /
  `"from pylabrobot"`, authenticated via `gh`, ~50 results each): broader
  and surfaced several real consumers the dependents graph missed (e.g.
  `deepmodeling/Uni-Lab-OS`, `Pioneer-Research-Labs/ngs_library_prep`,
  `SLKS99/PyFluent`), but is itself capped (~50/query here) and mixes in a
  lot of noise -- see §3.

Neither method is authoritative or complete; both are directionally useful
and were cross-checked against each other rather than trusted alone.

## 2. Real candidates, prioritized by activity + relevance

| Repo | Stars | Last push | What it is |
|---|---|---|---|
| [`deepmodeling/Uni-Lab-OS`](https://github.com/deepmodeling/Uni-Lab-OS) | 175 | 2026-08-26 (yesterday) | "A Platform for Laboratory Automation" -- a full lab-automation OS/registry with its own resource + liquid-handling abstractions built on PLR (`unilabos/registry/registry.py`, `unilabos/devices/liquid_handling/liquid_handler_abstract.py`). Highest-signal find: active, popular, broad task registry. |
| [`Cheshire-Labs/orca`](https://github.com/Cheshire-Labs/orca) | 24 | 2026-04-23 | "Lab Automation Scheduling Software" -- workflow/scheduling layer over PLR-controlled hardware. Paired with `Cheshire-Labs/swarm-client` (0 stars, "Lab client for connecting to swarm integration layer") -- same org, orchestration-focused. |
| [`Pioneer-Research-Labs/ngs_library_prep`](https://github.com/Pioneer-Research-Labs/ngs_library_prep) | 12 | 2026-04-02 | "Code for running Illumina Library Prep on Hamilton STARlet with PyLabRobot" -- a REAL wet-lab protocol repo (in-house use at an actual lab), not a demo. Directly relevant task-type material (NGS library prep is outside the copilot's current 13-tool surface -- more out-of-surface seed material). |
| [`SLKS99/PyFluent`](https://github.com/SLKS99/PyFluent) | 12 | 2026-04-02 | No description, but real content: `worklist_converter.py`, `backends/fluent_visionx.py` -- a Tecan Fluent-adjacent PLR project. Worklist-driven task style, distinct from the copilot's per-call style. |
| [`qte77/so101-biolab-automation`](https://github.com/qte77/so101-biolab-automation) | 3 | 2026-08-26 (yesterday) | "Dual SO-101 robotic arm bio-lab automation: 96-well pipetting, tool changing, remote oversight." Active, robotic-arm-based (not a liquid handler in the STAR/OT sense) -- a different hardware paradigm than anything in the current surface. |
| [`ivoryos-ai/IvoryOS-PyLabRobot-Integration`](https://github.com/ivoryos-ai/IvoryOS-PyLabRobot-Integration) | 0 | 2026-07-03 | "A lightweight IvoryOS wrapper for PyLabRobot, enabling visual workflow design, execution, and reuse." Another orchestration-layer integration, low activity. |
| [`aicell-lab/hamilton-control`](https://github.com/aicell-lab/hamilton-control) | 0 | 2025-02-25 | "Python for Hamilton liquid handling robots" -- uses `pylabrobot/serializer.py` directly. Stale (6+ months). |
| [`GreenTilden/oolitic-plr`](https://github.com/GreenTilden/oolitic-plr) | 0 | 2026-08-08 | "a framework for getting PLR methods to generate locally on a >=16GB gpu locally" -- sounds like an LLM-for-PLR-codegen project, i.e. potentially adjacent/competing work to this project's own goal, not necessarily a task-corpus source. Worth a closer look before mining, not before noting the resemblance. |

**Top pick if starting with one:** `deepmodeling/Uni-Lab-OS` -- by far the most active (pushed yesterday), most popular (175 stars, an order of magnitude above everything else found), and structurally closest to what would matter here (its own task/resource registry sitting on top of PLR primitives, comparable in spirit to `coxswain.plr.param_namespace`/`tool_schema`).

## 3. Noise excluded

Several code-search hits were AI-agent **skill-definition** repos (Claude
Code / agent "skills" documenting how to call PyLabRobot for an LLM
audience, not real automation code): `K-Dense-AI/scientific-agent-skills`,
`davila7/claude-code-templates`, `FreedomIntelligence/OpenClaw-Medical-Skills`,
`synthetic-sciences/openscience`, `wu-yc/LabClaw`,
`majiayu000/claude-skill-registry`, `boisenoise/skills-collections`. These
are meta-documentation ABOUT pylabrobot usage, not task corpora -- excluded
from the candidate list, though `K-Dense-AI/scientific-agent-skills`'s
`skills/pylabrobot/scripts/inspect_backends.py` and similar could be a
tertiary source of *how people describe PLR tasks to an LLM*, which is a
different and possibly interesting question from "what tasks do real
protocols perform," not pursued further here. Also excluded: `PyLabRobot/pylabrobot`
itself (source, not a consumer), this repo (`maraxen/praxis`), and
`Lyn4ever29/pipy_server` / `alphavector/all` (unclear relevance, not
investigated further).

## 4. Recommendation (not implemented -- research only, per the user's ask)

If pursuing this as a corpus-derivation source (parallel to the
`plr-cookbook` recipe-mining idea in the decision doc's §5), start with
`deepmodeling/Uni-Lab-OS`'s registry and `Pioneer-Research-Labs/ngs_library_prep`'s
real protocol code -- the former for task-type/registry-shape ideas, the
latter for an actual wet-lab task sequence to mine call patterns from, the
same way `overlay_gen/miner.py` already mines PLR's own notebooks/protocols.
Neither has been cloned or mined yet; this doc is the survey, not the
extraction.
