#!/usr/bin/env python3
"""Generate comprehensive PLR definitions for demo mode.

This script introspects PyLabRobot to extract all resource and machine definitions,
then outputs them as JSON files for use in the frontend demo mode.

Usage:
    uv run python scripts/generate_plr_definitions.py

Output:
    praxis/web-client/src/assets/demo-data/plr-resource-definitions.json
    praxis/web-client/src/assets/demo-data/plr-machine-definitions.json
"""

import inspect
import json
import re
from pathlib import Path
from typing import Any

# PLR imports
from pylabrobot.legacy.machines.machine import Machine
from pylabrobot.resources import (
    Carrier,
    Deck,
    Plate,
    TipRack,
    Trough,
)

from praxis.backend.utils.plr_inspection import (
    get_all_carrier_classes,
    get_constructor_params_with_defaults,
    get_deck_classes,
    get_machine_classes,
    get_resource_classes,
)


def extract_category(fqn: str, klass: type) -> str:
    """Determine the PLR category from class hierarchy."""
    if issubclass(klass, TipRack):
        return "TipRack"
    if issubclass(klass, Plate):
        return "Plate"
    if issubclass(klass, Trough):
        return "Reservoir"
    if issubclass(klass, Carrier):
        return "Carrier"
    if issubclass(klass, Deck):
        return "Deck"
    if issubclass(klass, Machine):
        return "Machine"
    return "Resource"


def extract_vendor(fqn: str) -> str | None:
    """Extract vendor name from FQN."""
    # Pattern: pylabrobot.resources.{vendor}.{class}
    match = re.search(r"pylabrobot\.resources\.(\w+)\.", fqn)
    if match:
        vendor = match.group(1)
        # Skip generic module names
        if vendor not in {"carrier", "plate", "tip_rack", "trough", "resource", "deck"}:
            return vendor.replace("_", " ").title()
    return None


def is_json_serializable(val: Any) -> bool:
    """Check if a value is JSON serializable."""
    if val is None or isinstance(val, (str, int, float, bool)):
        return True
    if isinstance(val, (list, tuple)):
        return all(is_json_serializable(v) for v in val)
    if isinstance(val, dict):
        return all(isinstance(k, str) and is_json_serializable(v) for k, v in val.items())
    return False


def extract_properties(klass: type) -> dict[str, Any]:
    """Extract key properties from class definition."""
    props = {}

    # Try to get class-level attributes (skip properties, methods, etc.)
    for attr in ["num_items", "size_x", "size_y", "size_z", "well_volume"]:
        try:
            # Check if it's a property first (don't call it)
            class_attr = getattr(type(klass), attr, None) if hasattr(type(klass), attr) else getattr(klass.__class__, attr, None)
            if isinstance(class_attr, property):
                continue

            val = getattr(klass, attr, None)
            if val is not None and not callable(val) and is_json_serializable(val):
                props[attr] = val
        except Exception:
            continue

    # Get constructor defaults - only simple types
    try:
        ctor_params = get_constructor_params_with_defaults(klass)
        for name, default in ctor_params.items():
            if default is not inspect.Parameter.empty and default is not None:
                if is_json_serializable(default):
                    props[name] = default
    except Exception:
        pass

    return props


def generate_resource_definitions() -> list[dict]:
    """Generate all resource definitions."""
    definitions = []

    # Get all resource classes
    resources = get_resource_classes(concrete_only=True)
    carriers = get_all_carrier_classes(concrete_only=True)
    decks = get_deck_classes(concrete_only=True)

    all_classes = {**resources, **carriers, **decks}

    for fqn, klass in all_classes.items():
        try:
            category = extract_category(fqn, klass)
            vendor = extract_vendor(fqn)
            props = extract_properties(klass)

            definition = {
                "accession_id": f"plr-{hash(fqn) & 0xFFFFFFFF:08x}",
                "name": klass.__name__,
                "fqn": fqn,
                "plr_category": category,
                "description": inspect.getdoc(klass) or "",
                "vendor": vendor,
                "is_consumable": category in ["TipRack", "Plate"],
                "is_reusable": category not in ["TipRack"],
                "properties_json": props,
            }
            definitions.append(definition)
        except Exception:
            pass

    return definitions


def generate_machine_definitions() -> list[dict]:
    """Generate all machine definitions."""
    definitions = []

    machines = get_machine_classes(concrete_only=True)

    for fqn, klass in machines.items():
        try:
            props = extract_properties(klass)

            definition = {
                "accession_id": f"plr-machine-{hash(fqn) & 0xFFFFFFFF:08x}",
                "name": klass.__name__,
                "fqn": fqn,
                "description": inspect.getdoc(klass) or "",
                "has_deck": hasattr(klass, "deck") or "deck" in str(inspect.signature(klass.__init__)),
                "properties_json": props,
            }
            definitions.append(definition)
        except Exception:
            pass

    return definitions


def main():
    """Generate and write PLR definitions."""
    output_dir = Path(__file__).parent.parent / "praxis" / "web-client" / "src" / "assets" / "demo-data"
    output_dir.mkdir(parents=True, exist_ok=True)

    resources = generate_resource_definitions()

    machines = generate_machine_definitions()

    # Write resource definitions
    resource_file = output_dir / "plr-resource-definitions.json"
    with open(resource_file, "w") as f:
        json.dump(resources, f, indent=2)

    # Write machine definitions
    machine_file = output_dir / "plr-machine-definitions.json"
    with open(machine_file, "w") as f:
        json.dump(machines, f, indent=2)

    # Print summary by category
    categories = {}
    for r in resources:
        cat = r["plr_category"]
        categories[cat] = categories.get(cat, 0) + 1
    for cat, _count in sorted(categories.items()):
        pass



if __name__ == "__main__":
    main()
