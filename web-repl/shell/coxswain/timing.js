// §4.7 timing constants (H1) -- browser side.
//
// One module per side so these are changed in one place and are visible to
// review; `coxswain/src/coxswain/timing.py` mirrors these exactly and
// `coxswain/tests/test_timing_parity.py` asserts the two sides agree.
//
// The two edit-path values are deliberately different: 300 ms is a typing
// pause, 2 s is a work budget. Collapsing them into one number is how a
// debounce silently becomes a timeout. Expiry is always fail-closed (NFR-5).

// FR-4 inline-edit re-grounding. Blur flushes immediately without waiting out
// the interval.
export const EDIT_DEBOUNCE_MS = 300;

// Cue-2/cue-3 re-grounding after an inline edit. On expiry the field fails
// closed to invalid, never to validated.
export const REGROUND_TIMEOUT_MS = 2000;

// NFR-5's kernel round-trip timeout and FR-9's audit-ack flush window. On
// expiry the pass exits blocked:*, never continue.
export const KERNEL_RTT_TIMEOUT_MS = 5000;
