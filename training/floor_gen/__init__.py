"""P2.3 coverage-floor generator (backlog 4478, spec rev2 §7 AC-2.3.x).

Pipeline: committed verb x ambiguity matrix -> structured-call synthesizer
(corpus-B keyword style, namespace-table driven) -> teacher NL-ification
(titanix vLLM direct HTTP now; ox-alpha spawned-worker batches for fan-out)
behind a content-hash cache (R4/D9) -> provenance-tagged corpus rows with
FunctionGemma tool declarations rendered from the canonical namespace table.

Import boundary (F2-rev2): this package MAY import ``coxswain.plr.*``;
nothing in ``coxswain/`` or the browser bundle may ever import back.
"""

from __future__ import annotations

__all__ = ["cache", "corpus", "declarations", "matrix", "prompts", "synth", "teachers", "value_formats", "versions"]
