"""Regression tests for PLR type-hint matching in praxis.common.type_inspection.

`is_pylabrobot_resource` gates asset acquisition: protocol_discovery.py sets
`is_asset` from it, and parameter_processor.py calls it on a serialized (string)
type hint. Before 2026-09-14 its string branch was `any(t in type_str for t in
PLR_RESOURCE_TYPES)` -- raw substring containment against a set holding short
English nouns (Well, Plate, Deck, Lid, Tube, Machine, Resource). Every plausible
non-PLR name tested matched, so ordinary parameters were classified as lab
resources to acquire at runtime.

These tests pin both directions: real PLR resources are recognised, and names
that merely *contain* a PLR noun are not.
"""

from __future__ import annotations

import inspect

import pytest

from praxis.common.type_inspection import (
  PLR_RESOURCE_TYPES,
  extract_resource_types,
  is_pylabrobot_resource,
)

# Names that merely contain a PLR noun as a substring. Each of these returned
# True under the old containment check; the fragment it collided with is noted.
NON_PLR_NAMES = [
  "PlateauConfig",       # "Plate"
  "ResourceLimits",      # "Resource"
  "DeckingMaterial",     # "Deck"
  "WellnessScore",       # "Well"
  "MachineLearningModel",  # "Machine"
  "LidarScan",           # "Lid"
  "TubeMapEntry",        # "Tube"
  "SpotlightConfig",     # "Spot"
]

# Live PLR classes that the pre-fix set omitted outright.
PREVIOUSLY_MISSED_PLR_NAMES = [
  "Trash",
  "PetriDish",
  "PetriDishHolder",
  "TecanWashStation",
]

# The CarrierSite -> ResourceHolder/PlateHolder rename.
HOLDER_NAMES = ["ResourceHolder", "PlateHolder", "PlateAdapter"]


@pytest.mark.parametrize("name", NON_PLR_NAMES)
def test_substring_collisions_are_not_plr_resources(name: str) -> None:
  """A name containing a PLR noun is not itself a PLR resource."""
  assert is_pylabrobot_resource(name) is False


@pytest.mark.parametrize("name", PREVIOUSLY_MISSED_PLR_NAMES + HOLDER_NAMES)
def test_live_plr_resources_are_recognised(name: str) -> None:
  assert is_pylabrobot_resource(name) is True


@pytest.mark.parametrize(
  "hint",
  ["Plate", "list[Well]", "Optional[PlateHolder]", "tuple[Plate, TipRack]", "Sequence[TipSpot]"],
)
def test_generic_and_bare_hints_still_match(hint: str) -> None:
  assert is_pylabrobot_resource(hint) is True


@pytest.mark.parametrize("name", ["LiquidHandler", "PlateReader", "Centrifuge", "Thermocycler"])
def test_machines_are_still_assets(name: str) -> None:
  """Machines are acquirable assets too -- the docstring's stated contract."""
  assert is_pylabrobot_resource(name) is True


def test_user_defined_subclass_names_are_recognised_by_suffix() -> None:
  """Protocols outside this repo subclass PLR resources; suffix-match keeps them working.

  This is why the fix is not simply the existing word-boundary regex:
  ``\\bPlate\\b`` does not match "CorningCostar96Plate".
  """
  assert is_pylabrobot_resource("CorningCostar96Plate") is True
  assert is_pylabrobot_resource("MyCustomTipRack") is True


def test_carriersite_is_gone_from_the_type_set() -> None:
  """CarrierSite no longer exists in the pinned PLR; it must not linger here."""
  assert "CarrierSite" not in PLR_RESOURCE_TYPES


def test_extract_resource_types_is_unchanged() -> None:
  """The extractor already used word-boundary matching and must keep its behaviour."""
  assert extract_resource_types("list[Well]") == ["Well"]
  assert sorted(extract_resource_types("tuple[Plate, TipRack]")) == ["Plate", "TipRack"]


def test_every_live_plr_resource_class_is_recognised() -> None:
  """Drift guard: fail loudly when the PLR pin adds a resource this set cannot name.

  Enumerated from the submodule rather than hardcoded, so bumping the pin
  surfaces new classes here instead of silently misclassifying them.
  """
  import pylabrobot.resources as plr_resources
  from pylabrobot.resources import Resource

  live = {
    obj.__name__
    for attr in dir(plr_resources)
    for obj in [getattr(plr_resources, attr)]
    if inspect.isclass(obj) and issubclass(obj, Resource)
  }
  unrecognised = sorted(name for name in live if not is_pylabrobot_resource(name))
  assert unrecognised == [], f"PLR resource classes not recognised: {unrecognised}"
