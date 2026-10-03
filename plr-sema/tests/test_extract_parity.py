"""Extractor parity goldens (spec 261002 Slice 1, T1): the moved extractor must
produce byte-identical graphs to the praxis extractor it replaced."""

from __future__ import annotations

import json

import pytest

pytest.importorskip("libcst")
pytest.importorskip("pydantic")

from _extract_corpus import GOLDENS, corpus, dump  # noqa: E402
from plr_sema.extract.computation_graph_extractor import extract_graph_from_source  # noqa: E402

CORPUS = corpus()


def _goldens() -> dict:
    return json.loads(GOLDENS.read_text(encoding="utf-8"))


def test_corpus_is_the_expected_size() -> None:
    assert len(CORPUS) >= 26, [k for k, _, _ in CORPUS]


def test_goldens_cover_exactly_the_corpus() -> None:
    assert sorted(_goldens()) == [k for k, _, _ in CORPUS]


@pytest.mark.parametrize("key,source,fn", CORPUS, ids=[k for k, _, _ in CORPUS])
def test_extractor_matches_golden(key: str, source: str, fn: str) -> None:
    assert dump(extract_graph_from_source(source, fn)) == _goldens()[key]
