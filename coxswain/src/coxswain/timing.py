"""§4.7 timing constants (H1) -- kernel side.

One module per side so these are changed in one place and are visible to
review; ``web-repl/shell/coxswain/timing.js`` mirrors these exactly and
``coxswain/tests/test_timing_parity.py`` asserts the two sides agree.

The two edit-path values are deliberately different: 300 ms is a typing pause,
2 s is a work budget. Collapsing them into one number is how a debounce
silently becomes a timeout. What is normative is that each constant has a
value and that expiry is always in the fail-closed direction (NFR-5).
"""

from __future__ import annotations

from typing import Final

#: FR-4 inline-edit re-grounding. Blur flushes immediately without waiting out
#: the interval.
EDIT_DEBOUNCE_MS: Final[int] = 300

#: Cue-2/cue-3 re-grounding after an inline edit. On expiry the field fails
#: closed to invalid, never to validated.
REGROUND_TIMEOUT_MS: Final[int] = 2000

#: NFR-5's kernel round-trip timeout and FR-9's audit-ack flush window. On
#: expiry the pass exits blocked:*, never continue.
KERNEL_RTT_TIMEOUT_MS: Final[int] = 5000
