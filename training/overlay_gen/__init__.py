"""P2.4 naturalness-overlay generator (spec rev2 §5 P2.4, backlog item 4479).

Mines liquid-handling calls from the vendored PLR LH user-guide notebooks and
the runnable ``@protocol_function`` corpus, normalizes them into the P2.0
namespace-table shapes, pairs each with teacher-paraphrased natural-language
instructions (titanix-vllm-primary), deduplicates normalized utterances
against the coverage floor (P2.3) and within the overlay, and emits
provenance-tagged candidate rows.

Layout note: this package lives at ``training/overlay_gen/`` next to the P2.1
worker's planned ``training/src/``; it is importable with ``training/`` on
``sys.path`` (the tests' conftest arranges that) rather than via the member
package discovery in ``training/pyproject.toml``, which belongs to P2.1.
"""

from overlay_gen.normalize import normalize_utterance

__all__ = ["normalize_utterance"]
