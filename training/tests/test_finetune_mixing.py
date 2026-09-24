"""P2.6 mixing: dedup + arm selection pinned against the COMMITTED P2.5 corpus.

Numbers below are drift alarms (like the assembly manifest tests): if the
assembled corpus or the recipe changes, these fail on purpose and the new
values must be re-derived and re-pinned in the same commit.
"""

from collections import Counter
from pathlib import Path

import pytest

from praxis_training.finetune import mixing
from praxis_training.finetune.versions import ARMS, CORPUS_REL, NEGATIVE_CLASSES, POSITIVE_CLASS, SIDECAR_REL

ROOT = Path(__file__).resolve().parents[2]
CORPUS = ROOT / CORPUS_REL
SIDECAR = ROOT / SIDECAR_REL

# Pinned 260903 against assembly_version 0.1.6 (1523 rows; eval 228 PINNED,
# train 1295 = 1199 + 96 near-surface out-of-surface rows of the six matrix-v3
# cells; 24 more of those rows form the near-surface probe, never train).
# History: 0.1.5 (1427 rows; train 1199; dedup 1108/91; A 382/265/216/245,
# B 382/139/114/129, C 382/70/57/64) -- the P2.6c arm A3 was trained on that set;
# 0.1.4 (1301 rows; train 1073; dedup 984/89; A 382/265/216/121,
# B 382/168/137/77, C 382/84/69/38) -- the P2.6b arm A2 was trained on that set;
# 0.1.2/0.1.3 (812 rows; train 584; dedup 515/69; A 226/102/66/121,
# B 226/80/51/95, C 226/40/26/47) -- the P2.6 arms were trained on that set.
EXPECT_ROWS = 1523
EXPECT_EVAL = 228
EXPECT_TRAIN = 1295
EXPECT_DEDUP_KEPT = 1200
EXPECT_DEDUP_DROPPED = 95
EXPECT_KEPT_BY_CLASS = {"clean_parse": 382, "missing_slot": 265, "ambiguous_referent": 216, "out_of_surface": 337}
EXPECT_ARMS = {
    "A": {"clean_parse": 382, "missing_slot": 265, "ambiguous_referent": 216, "out_of_surface": 337},
    "B": {"clean_parse": 382, "missing_slot": 124, "ambiguous_referent": 101, "out_of_surface": 157},
    "C": {"clean_parse": 382, "missing_slot": 62, "ambiguous_referent": 50, "out_of_surface": 79},
}


@pytest.fixture(scope="module")
def corpus():
    return mixing.load_corpus(CORPUS, SIDECAR)


@pytest.fixture(scope="module")
def deduped(corpus):
    train = mixing.train_rows(corpus)
    kept, dropped = mixing.dedup_rows(train)
    return train, kept, dropped


def test_corpus_loads_line_aligned(corpus):
    assert len(corpus) == EXPECT_ROWS
    assert all(r.split in ("train", "eval") for r in corpus)
    assert len({r.record_id for r in corpus}) == EXPECT_ROWS


def test_eval_split_is_the_pinned_228(corpus):
    import json

    from assemble.pin import PIN_REL

    pin = json.loads((ROOT / PIN_REL).read_text(encoding="utf-8"))
    eval_ids = {r.record_id for r in corpus if r.split == "eval"}
    assert len(eval_ids) == EXPECT_EVAL and eval_ids == set(pin["rows"])


def test_train_split_and_dedup_pins(deduped):
    train, kept, dropped = deduped
    assert len(train) == EXPECT_TRAIN
    assert len(kept) == EXPECT_DEDUP_KEPT
    assert len(dropped) == EXPECT_DEDUP_DROPPED
    assert dict(Counter(r.ambiguity_class for r in kept)) == EXPECT_KEPT_BY_CLASS


def test_dedup_keeps_lowest_record_id_and_never_touches_eval(corpus, deduped):
    train, kept, dropped = deduped
    assert all(r.split == "train" for r in kept + dropped)
    from overlay_gen.normalize import normalize_utterance

    kept_keys = {normalize_utterance(r.utterance): r.record_id for r in kept}
    for d in dropped:
        assert kept_keys[normalize_utterance(d.utterance)] < d.record_id
    eval_ids = {r.record_id for r in corpus if r.split == "eval"}
    assert eval_ids.isdisjoint({r.record_id for r in kept + dropped})


@pytest.mark.parametrize("arm", sorted(ARMS))
def test_arm_counts_pinned(deduped, arm):
    _, kept, dropped = deduped
    selected = mixing.select_arm(kept, arm, 0)
    assert dict(Counter(r.ambiguity_class for r in selected)) == EXPECT_ARMS[arm]
    summary = mixing.arm_summary(selected, dedup_dropped=dropped, train_total=EXPECT_TRAIN, arm=arm, seed=0)
    assert summary["selected_total"] == sum(EXPECT_ARMS[arm].values())
    assert summary["dedup_dropped"] == EXPECT_DEDUP_DROPPED
    assert summary["selected_record_ids"] == sorted(summary["selected_record_ids"])


def test_arm_ratio_invariants(deduped):
    _, kept, _ = deduped
    n_pos = sum(1 for r in kept if r.is_positive)
    for arm, ratio in ARMS.items():
        selected = mixing.select_arm(kept, arm, 0)
        pos = sum(1 for r in selected if r.is_positive)
        neg = len(selected) - pos
        assert pos == n_pos, "positives are never subsampled"
        if ratio is None:
            assert neg == len(kept) - n_pos
        else:
            assert neg == round(ratio * n_pos)
        # Class quotas are proportional to the post-dedup class counts (+-1).
        if ratio is not None:
            pool = Counter(r.ambiguity_class for r in kept if not r.is_positive)
            got = Counter(r.ambiguity_class for r in selected if not r.is_positive)
            for cls in NEGATIVE_CLASSES:
                expected = neg * pool[cls] / sum(pool.values())
                assert abs(got[cls] - expected) <= 1.0


def test_arm_selection_is_deterministic_and_seed_sensitive(deduped):
    _, kept, _ = deduped
    a = [r.record_id for r in mixing.select_arm(kept, "B", 0)]
    b = [r.record_id for r in mixing.select_arm(kept, "B", 0)]
    c = [r.record_id for r in mixing.select_arm(kept, "B", 1)]
    assert a == b
    assert a != c
    assert set(a) <= {r.record_id for r in kept}


def test_unknown_arm_rejected(deduped):
    _, kept, _ = deduped
    with pytest.raises(mixing.MixingError):
        mixing.select_arm(kept, "Z", 0)


def test_positive_class_constant_matches_corpus(corpus):
    classes = {r.ambiguity_class for r in corpus}
    assert classes == {POSITIVE_CLASS, *NEGATIVE_CLASSES}
