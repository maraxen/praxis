"""Tool-declaration rendering tests (deliverable 6a)."""

from __future__ import annotations

import json

from coxswain.plr.param_namespace import (
    ParamKind,
    params_of,
    required_params,
)
from coxswain.plr.tool_schema import PHASE2_TOOL_NAMES

from floor_gen.declarations import render_declaration, render_declarations


def test_declarations_cover_exactly_the_phase2_surface():
    decls = render_declarations()
    assert [d["name"] for d in decls] == sorted(PHASE2_TOOL_NAMES)


def test_excluded_tools_render_loudly():
    import pytest

    for excluded in ("mix", "set_temperature", "dispense_to_waste"):
        with pytest.raises(KeyError):
            render_declaration(excluded)


def test_every_declaration_has_description_and_parameters():
    for decl in render_declarations():
        assert isinstance(decl["description"], str) and len(decl["description"]) > 20
        parameters = decl["parameters"]
        assert parameters["type"] == "object"
        assert set(parameters["required"]) == set(required_params(decl["name"]))
        assert set(parameters["required"]) <= set(parameters["properties"])
        # properties mirror the SCHEMA-side names of the namespace table
        assert set(parameters["properties"]) == {s.name for s in params_of(decl["name"])}


def test_type_mappings_follow_the_table():
    aspirate = render_declaration("aspirate")
    props = aspirate["parameters"]["properties"]
    assert props["source"] == {"type": "string"}
    assert props["volume_ul"] == {"type": "array", "items": {"type": "number"}}

    transfer = render_declaration("transfer")
    tprops = transfer["parameters"]["properties"]
    assert tprops["destination"] == {"type": "array", "items": {"type": "string"}}
    assert tprops["volume_ul"] == {"type": "array", "items": {"type": "number"}}
    assert transfer["parameters"]["required"] == ["source", "destination"]

    discard = render_declaration("discard_tips")
    dprops = discard["parameters"]["properties"]
    assert dprops["what"] == {"type": "string", "enum": ["tips"]}
    assert discard["parameters"]["required"] == []

    read = render_declaration("read_absorbance")
    rprops = read["parameters"]["properties"]
    assert rprops["wavelength_nm"] == {"type": "number"}
    assert rprops["at"] == {"type": "array", "items": {"type": "string"}}


def test_symbolic_params_are_string_typed():
    for name in PHASE2_TOOL_NAMES:
        for spec in params_of(name):
            if spec.kind is not ParamKind.SYMBOLIC_RESOURCE_REF:
                continue
            prop = render_declaration(name)["parameters"]["properties"][spec.name]
            expected = (
                {"type": "array", "items": {"type": "string"}}
                if spec.cardinality == "list"
                else {"type": "string"}
            )
            assert prop == expected, (name, spec.name)


def test_declarations_are_json_serializable_and_stable():
    a = json.dumps(render_declarations(), sort_keys=True)
    b = json.dumps(render_declarations(), sort_keys=True)
    assert a == b
