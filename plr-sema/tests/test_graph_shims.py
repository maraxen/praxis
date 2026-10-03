"""praxis re-export shims return the SAME objects as plr_sema.graph (spec 261002 §4).

Identity, not equality: isinstance checks across praxis consumers depend on it.
"""

from __future__ import annotations

import importlib

import pytest

pytest.importorskip("pydantic")

GRAPH_NAMES = (
    "GraphNodeType",
    "PreconditionType",
    "OperationNode",
    "ResourceNode",
    "StatePrecondition",
    "ProtocolComputationGraph",
)


def _assert_reexports_everything(old_name: str, new_name: str) -> None:
    old = importlib.import_module(old_name)
    new = importlib.import_module(new_name)
    public = [n for n in vars(new) if not n.startswith("_")]
    wrong = [n for n in public if getattr(old, n, None) is not getattr(new, n)]
    assert public, f"{new_name} exports nothing"
    assert wrong == [], f"{old_name} does not re-export {wrong} from {new_name}"


def test_graph_models_are_identical() -> None:
    old = importlib.import_module("praxis.backend.utils.plr_static_analysis.models")
    new = importlib.import_module("plr_sema.graph.models")
    for name in GRAPH_NAMES:
        assert getattr(old, name) is getattr(new, name), name


def test_resource_hierarchy_shim() -> None:
    _assert_reexports_everything(
        "praxis.backend.utils.plr_static_analysis.resource_hierarchy",
        "plr_sema.graph.resource_hierarchy",
    )


def test_type_inspection_shim() -> None:
    _assert_reexports_everything("praxis.common.type_inspection", "plr_sema.graph.type_inspection")


def test_backend_type_inspection_still_resolves() -> None:
    # praxis/backend/utils/type_inspection.py re-imports from praxis.common.type_inspection.
    backend = importlib.import_module("praxis.backend.utils.type_inspection")
    new = importlib.import_module("plr_sema.graph.type_inspection")
    assert backend.extract_resource_types is new.extract_resource_types


def test_extractor_shim() -> None:
    _assert_reexports_everything(
        "praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor",
        "plr_sema.extract.computation_graph_extractor",
    )
