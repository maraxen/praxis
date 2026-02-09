"""Chatterbox Protocol Runner.

Executes protocols against real PLR Chatterbox backends to verify
they complete without runtime errors. This is a separate validation
step in the ProtocolSimulator facade — NOT a level in the
HierarchicalSimulator (which uses traced proxy objects).

Architecture (v2 — Feb 2026):
- CHATTERBOX_REGISTRY: maps machine types → available Chatterbox backends
- DeckFactory: creates deck + resources for carrier-based OR slot-based layouts
- resolve_resource(): generic resource resolution from type hints
  (mirrors web_bridge.resolve_parameters pattern)
- ChatterboxProtocolRunner: orchestrates execution and result collection
"""

from __future__ import annotations

import time
import traceback
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from pylabrobot.liquid_handling import LiquidHandler
from pylabrobot.liquid_handling.backends.chatterbox import (
    LiquidHandlerChatterboxBackend,
)
from pylabrobot.liquid_handling.backends.hamilton.STAR_chatterbox import (
    STARChatterboxBackend,
)
from pylabrobot.plate_reading import PlateReader
from pylabrobot.plate_reading.chatterbox import PlateReaderChatterboxBackend
from pylabrobot.resources import (
    PLT_CAR_L5AC_A00,
    TIP_CAR_480_A00,
    Coordinate,
    Cor_96_wellplate_360ul_Fb,
    Resource,
    hamilton_96_tiprack_1000uL_filter,
)
from pylabrobot.resources.hamilton import STARLetDeck
from pylabrobot.resources.hamilton.troughs import hamilton_1_trough_200ml_Vb
from pylabrobot.resources.opentrons.deck import OTDeck

# Centralized type utilities — single source of truth for PLR type names.
# NOTE: We do NOT import from praxis.backend.core.tracing.executor because
# that triggers the SQLAlchemy import chain via backend.core.__init__.py.
# Instead, MACHINE_TYPE_PATTERNS is inlined below.
from praxis.common.type_inspection import PLR_RESOURCE_TYPES, extract_resource_types

if TYPE_CHECKING:
    from collections.abc import Callable

# =============================================================================
# Machine Type Detection (inlined from executor.py)
#
# Inlined to break the import chain:
#   chatterbox_runner → executor → backend.core.__init__ → db → sqlalchemy
# The executor.py infer_machine_type() function is just a dict lookup.
# =============================================================================

_MACHINE_TYPE_PATTERNS: dict[str, str] = {
    "LiquidHandler": "liquid_handler",
    "PlateReader": "plate_reader",
    "HeaterShaker": "heater_shaker",
    "Shaker": "shaker",
    "Centrifuge": "centrifuge",
    "Thermocycler": "thermocycler",
    "TemperatureController": "temperature_controller",
    "Incubator": "incubator",
    "Pump": "pump",
    "PumpArray": "pump_array",
    "Fan": "fan",
    "Sealer": "sealer",
    "Peeler": "peeler",
    "PowderDispenser": "powder_dispenser",
}


def _infer_machine_type(type_hint: str) -> str | None:
    """Infer machine type from a type hint string.

    Equivalent to executor.infer_machine_type but inlined to avoid
    the SQLAlchemy import chain.
    """
    for pattern, machine_type in _MACHINE_TYPE_PATTERNS.items():
        if pattern in type_hint:
            return machine_type
    return None


# =============================================================================
# Result Models
# =============================================================================


@dataclass
class BackendResult:
    """Result of running a protocol against a single Chatterbox backend."""

    backend_name: str
    passed: bool
    error: str | None = None
    traceback: str | None = None
    execution_time_ms: float = 0.0


@dataclass
class ChatterboxExecutionResult:
    """Aggregate result of running a protocol across all compatible backends."""

    protocol_name: str
    results_by_backend: dict[str, BackendResult] = field(default_factory=dict)

    @property
    def all_passed(self) -> bool:
        if not self.results_by_backend:
            return False
        return all(r.passed for r in self.results_by_backend.values())


# =============================================================================
# Backend Registry
#
# Discovered via ast-grep: sg --pattern 'class $NAME($BASE)' in external/pylabrobot/
# 16 total Chatterbox backends across 12 machine types.
# =============================================================================


def _lazy_import(module_path: str, class_name: str) -> type:
    """Lazy import to avoid loading all PLR backends at module import time."""
    import importlib

    mod = importlib.import_module(module_path)
    return getattr(mod, class_name)


# Maps PLR machine type names → list of (backend_name, backend_class_or_path, kwargs)
# Active entries use direct class references; scaffolded entries use lazy imports.
CHATTERBOX_REGISTRY: dict[str, list[tuple[str, type, dict[str, Any]]]] = {
    # ── Active: used by current protocols ──────────────────────────────
    "LiquidHandler": [
        (
            "LiquidHandlerChatterboxBackend",
            LiquidHandlerChatterboxBackend,
            {"num_channels": 8},
        ),
        (
            "STARChatterboxBackend",
            STARChatterboxBackend,
            {"num_channels": 8, "core96_head_installed": True},
        ),
    ],
    "PlateReader": [
        (
            "PlateReaderChatterboxBackend",
            PlateReaderChatterboxBackend,
            {},
        ),
    ],
}

# Scaffolded machine types — registered at module load time
_SCAFFOLDED_BACKENDS: list[tuple[str, str, str, dict[str, Any]]] = [
    ("HeaterShaker", "HeaterShakerChatterboxBackend",
     "pylabrobot.heating_shaking.chatterbox", {}),
    ("Thermocycler", "ThermocyclerChatterboxBackend",
     "pylabrobot.thermocycling.chatterbox", {}),
    ("TemperatureController", "TemperatureControllerChatterboxBackend",
     "pylabrobot.temperature_controlling.chatterbox", {}),
    ("Shaker", "ShakerChatterboxBackend",
     "pylabrobot.shaking.chatterbox", {}),
    ("PowderDispenser", "PowderDispenserChatterboxBackend",
     "pylabrobot.powder_dispensing.chatterbox", {}),
    ("Incubator", "IncubatorChatterboxBackend",
     "pylabrobot.storage.chatterbox", {}),
    ("Scale", "ScaleChatterboxBackend",
     "pylabrobot.scales.chatterbox", {}),
    ("Tilter", "TilterChatterboxBackend",
     "pylabrobot.tilting.chatterbox", {}),
    ("Tilter", "HamiltonTiltModuleChatterboxBackend",
     "pylabrobot.tilting.hamilton_backend", {}),
    ("Pump", "PumpChatterboxBackend",
     "pylabrobot.pumps.chatterbox", {}),
    ("PumpArray", "PumpArrayChatterboxBackend",
     "pylabrobot.pumps.chatterbox", {}),
    ("Centrifuge", "CentrifugeChatterboxBackend",
     "pylabrobot.centrifuge.chatterbox", {}),
    ("Centrifuge", "LoaderChatterboxBackend",
     "pylabrobot.centrifuge.chatterbox", {}),
    ("Fan", "FanChatterboxBackend",
     "pylabrobot.only_fans.chatterbox", {}),
]

for _mt, _cls_name, _mod_path, _kwargs in _SCAFFOLDED_BACKENDS:
    if _mt not in CHATTERBOX_REGISTRY:
        CHATTERBOX_REGISTRY[_mt] = []
    try:
        _cls = _lazy_import(_mod_path, _cls_name)
        CHATTERBOX_REGISTRY[_mt].append((_cls_name, _cls, _kwargs))
    except (ImportError, AttributeError):
        pass


# =============================================================================
# Type Helpers
# =============================================================================

# Scalar/state parameter types to skip when resolving machine/resource params.
_SCALAR_TYPE_PREFIXES: frozenset[str] = frozenset({
    "dict", "str", "int", "float", "bool", "list", "tuple",
    "None", "Any", "Optional",
})


def _is_scalar_type(type_str: str) -> bool:
    """Check if a type string represents a scalar (non-PLR) parameter."""
    if any(t in type_str for t in PLR_RESOURCE_TYPES):
        return False
    base = type_str.split("[")[0].strip()
    return base in _SCALAR_TYPE_PREFIXES


# =============================================================================
# Deck Layout Types
# =============================================================================


class DeckLayoutType(str, Enum):
    """Deck layout strategy.

    Intentionally duplicated from resource_hierarchy.py to avoid importing
    from the static analysis package (which is a separate concern).
    """

    SLOT_BASED = "slot_based"     # OT-2: resources go directly on slots
    CARRIER_BASED = "carrier_based"  # Hamilton: resources need carriers


# Backend → deck layout mapping
_BACKEND_DECK_TYPE: dict[str, DeckLayoutType] = {
    "LiquidHandlerChatterboxBackend": DeckLayoutType.CARRIER_BASED,
    "STARChatterboxBackend": DeckLayoutType.CARRIER_BASED,
    "PlateReaderChatterboxBackend": DeckLayoutType.SLOT_BASED,
}


# =============================================================================
# Generic Resource Resolution
#
# Mirrors the pattern from web_bridge.resolve_parameters():
#   type_hint → PLR resource class → instantiation with standard dims
# =============================================================================

# Resource type → factory callable
_RESOURCE_FACTORIES: dict[str, Any] = {
    "Plate": lambda name: Cor_96_wellplate_360ul_Fb(name=name),
    "TipRack": lambda name: hamilton_96_tiprack_1000uL_filter(name=name),
    "Trough": lambda name: hamilton_1_trough_200ml_Vb(name=name),
    "TubeRack": lambda name: Resource(name=name, size_x=127, size_y=85, size_z=100),
    "Container": lambda name: Resource(name=name, size_x=127, size_y=85, size_z=14),
    "Well": None,       # Sub-resource, not instantiated standalone
    "TipSpot": None,    # Sub-resource, not instantiated standalone
}

# Resource types we can place on a deck
_DECK_PLACEABLE_TYPES: frozenset[str] = frozenset({
    "Plate", "TipRack", "Trough", "TubeRack", "Container",
})


def resolve_resource(param_name: str, type_str: str) -> Any | None:
    """Resolve a parameter to a PLR resource instance from its type hint.

    Mirrors web_bridge.resolve_parameters() logic:
    1. Extract resource type from type hint (via extract_resource_types)
    2. Instantiate appropriate PLR object with standard dimensions

    Args:
        param_name: Parameter name (used as resource name).
        type_str: Type hint string (e.g. "Plate", "TipRack").

    Returns:
        A PLR resource instance, or None if not resolvable.
    """
    resource_types = extract_resource_types(type_str)
    if not resource_types:
        return None
    primary = resource_types[0]
    factory = _RESOURCE_FACTORIES.get(primary)
    if factory is None:
        return None
    return factory(param_name)


# =============================================================================
# Deck Factory
#
# Mirrors wizard-state.service.ts serializeToPython():
# - Carrier-based (Hamilton): carrier → deck at rails, labware → carrier[slot]
# - Slot-based (OT-2): labware → deck.assign_child_at_slot(N)
# =============================================================================


class DeckFactory:
    """Creates deck layouts with resources for Chatterbox execution.

    Two strategies mirroring wizard-state.service.ts serializeToPython():
    - CARRIER_BASED: resources go into carriers assigned to deck rails (Hamilton)
    - SLOT_BASED: resources assigned directly to deck slots (OT-2)
    """

    def create_setup(
        self,
        backend_name: str,
        resource_needs: dict[str, str],
    ) -> dict[str, Any]:
        """Create a complete machine + deck setup for the given backend.

        Args:
            backend_name: Name of the Chatterbox backend.
            resource_needs: Map of param_name → resource_type_str.

        Returns:
            Dict with keys: machine, deck, and each param_name → resource.
        """
        if backend_name == "PlateReaderChatterboxBackend":
            return self._create_plate_reader_setup()

        layout_type = _BACKEND_DECK_TYPE.get(
            backend_name, DeckLayoutType.CARRIER_BASED
        )

        if layout_type == DeckLayoutType.SLOT_BASED:
            return self._create_slot_based_setup(backend_name, resource_needs)
        return self._create_carrier_based_setup(backend_name, resource_needs)

    def _create_plate_reader_setup(self) -> dict[str, Any]:
        """Create a standalone PlateReader setup (no deck needed)."""
        backend = PlateReaderChatterboxBackend()
        plate = Cor_96_wellplate_360ul_Fb(name="plate")
        pr = PlateReader(
            name="plate_reader",
            backend=backend,
            size_x=0,
            size_y=0,
            size_z=0,
        )
        return {"machine": pr, "plate": plate}

    def _create_carrier_based_setup(
        self,
        backend_name: str,
        resource_needs: dict[str, str],
    ) -> dict[str, Any]:
        """Hamilton-style: resources in carriers on deck rails.

        Mirrors serializeToPython() CASE 1 (carrier-placement):
          carrier = PLT_CAR_L5AC_A00(name="plate_carrier")
          deck.assign_child_resource(carrier, rails=N)
          carrier[slot] = labware
        """
        deck = STARLetDeck()

        # Select backend class + kwargs from registry
        if backend_name == "STARChatterboxBackend":
            backend = STARChatterboxBackend(
                num_channels=8, core96_head_installed=True
            )
        else:
            backend = LiquidHandlerChatterboxBackend(num_channels=8)

        lh = LiquidHandler(backend, deck=deck)

        result: dict[str, Any] = {"machine": lh, "deck": deck}

        # -- Tip rack (always needed for LH protocols) ---------------------
        tip_car = TIP_CAR_480_A00(name="tip_carrier")
        tip_rack = hamilton_96_tiprack_1000uL_filter(name="tip_rack")
        tip_car[0] = tip_rack
        deck.assign_child_resource(tip_car, rails=1)
        result["tip_rack"] = tip_rack

        # -- Plate carrier for plate/trough resources ----------------------
        plt_car = PLT_CAR_L5AC_A00(name="plate_carrier")
        deck.assign_child_resource(plt_car, rails=9)
        carrier_slot = 0

        for param_name, res_type in resource_needs.items():
            if res_type not in _DECK_PLACEABLE_TYPES:
                continue
            resource = resolve_resource(param_name, res_type)
            if resource is None:
                continue

            if res_type == "TipRack":
                # Already handled above; alias to the default tip rack
                result[param_name] = tip_rack
            elif res_type == "Trough":
                # Troughs don't go in plate carriers — assign directly to deck rails
                deck.assign_child_resource(resource, rails=21)
                result[param_name] = resource
            elif carrier_slot < 5:
                # Place in plate carrier (5 slots available on PLT_CAR_L5AC_A00)
                plt_car[carrier_slot] = resource
                result[param_name] = resource
                carrier_slot += 1
            else:
                # Overflow: assign directly at rails
                deck.assign_child_resource(resource, rails=25)
                result[param_name] = resource

        return result

    def _create_slot_based_setup(
        self,
        backend_name: str,
        resource_needs: dict[str, str],
    ) -> dict[str, Any]:
        """OT-2 style: resources directly on deck slots.

        Mirrors serializeToPython() OTDeck path:
          deck.assign_child_at_slot(labware, slot_number)
        """
        deck = OTDeck()
        backend = LiquidHandlerChatterboxBackend(num_channels=8)
        lh = LiquidHandler(backend, deck=deck)

        result: dict[str, Any] = {"machine": lh, "deck": deck}

        # OT-2 has 11 usable slots (1-11)
        slot_number = 1
        for param_name, res_type in resource_needs.items():
            if res_type not in _DECK_PLACEABLE_TYPES:
                continue
            resource = resolve_resource(param_name, res_type)
            if resource is None:
                continue

            if slot_number <= 11:
                deck.assign_child_at_slot(resource, slot=slot_number)
                result[param_name] = resource
                slot_number += 1

        return result


# =============================================================================
# Protocol Runner
# =============================================================================


class ChatterboxProtocolRunner:
    """Executes protocols against real Chatterbox backends.

    Usage:
        runner = ChatterboxProtocolRunner()

        # Run against ALL compatible backends
        result = await runner.run_protocol_function(func, param_types)

        # Run against a SINGLE backend
        backend_result = await runner.run_single(func, param_types, "STARChatterboxBackend")
    """

    def __init__(self) -> None:
        self.factory = DeckFactory()

    def detect_machine_types(self, parameter_types: dict[str, str]) -> set[str]:
        """Inspect parameter types to determine which machine types a protocol needs.

        Uses the inlined _MACHINE_TYPE_PATTERNS dict — equivalent to
        executor.infer_machine_type() but without the import chain.
        """
        machine_types = set()
        for param_name, type_str in parameter_types.items():
            if param_name == "state" or _is_scalar_type(type_str):
                continue
            mt = _infer_machine_type(type_str)
            if mt and any(
                pattern in type_str
                for pattern in _MACHINE_TYPE_PATTERNS
                if _MACHINE_TYPE_PATTERNS[pattern] == mt
                and pattern in CHATTERBOX_REGISTRY
            ):
                # Map back to the class name used as registry key
                for pattern, mapped_mt in _MACHINE_TYPE_PATTERNS.items():
                    if mapped_mt == mt and pattern in CHATTERBOX_REGISTRY:
                        machine_types.add(pattern)
                        break
        return machine_types

    def detect_resource_needs(self, parameter_types: dict[str, str]) -> dict[str, str]:
        """Determine which resource types are needed, mapped by parameter name.

        Uses extract_resource_types() from praxis.common.type_inspection —
        the same function used by pipeline.py and failure_detector.py.
        """
        resources = {}
        for param_name, type_str in parameter_types.items():
            if param_name == "state" or _is_scalar_type(type_str):
                continue
            if _infer_machine_type(type_str):
                continue
            extracted = extract_resource_types(type_str)
            if extracted:
                primary = extracted[0]
                if primary in _DECK_PLACEABLE_TYPES:
                    resources[param_name] = primary
        return resources

    def resolve_backends(self, machine_types: set[str]) -> list[str]:
        """Given machine types, return all compatible backend names."""
        backend_names = set()
        for mt in machine_types:
            if mt in CHATTERBOX_REGISTRY:
                for name, _, _ in CHATTERBOX_REGISTRY[mt]:
                    backend_names.add(name)
        return sorted(backend_names)

    async def run_protocol_function(
        self,
        protocol_func: Callable,
        parameter_types: dict[str, str],
    ) -> ChatterboxExecutionResult:
        """Run a protocol function against all compatible backends."""
        machine_types = self.detect_machine_types(parameter_types)
        backend_names = self.resolve_backends(machine_types)

        protocol_name = getattr(protocol_func, "__name__", str(protocol_func))
        result = ChatterboxExecutionResult(protocol_name=protocol_name)

        for backend_name in backend_names:
            br = await self.run_single(protocol_func, parameter_types, backend_name)
            result.results_by_backend[backend_name] = br

        return result

    async def run_single(
        self,
        protocol_func: Callable,
        parameter_types: dict[str, str],
        backend_name: str,
    ) -> BackendResult:
        """Run a protocol function against a single named backend."""
        start = time.monotonic()
        machine = None
        is_lh = backend_name != "PlateReaderChatterboxBackend"

        try:
            resource_needs = self.detect_resource_needs(parameter_types)
            setup = self.factory.create_setup(backend_name, resource_needs)

            machine = setup["machine"]
            if is_lh:
                await machine.setup()

            kwargs = self._build_protocol_kwargs(
                parameter_types, setup, backend_name
            )

            # Bypass decorators (like @protocol_function) to avoid DB checks
            # and context requirements during simulation/verification.
            func_to_run = getattr(protocol_func, "__wrapped__", protocol_func)
            await func_to_run(**kwargs)

            elapsed_ms = (time.monotonic() - start) * 1000
            return BackendResult(
                backend_name=backend_name,
                passed=True,
                execution_time_ms=elapsed_ms,
            )

        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            return BackendResult(
                backend_name=backend_name,
                passed=False,
                error=f"{type(e).__name__}: {e}",
                traceback=traceback.format_exc(),
                execution_time_ms=elapsed_ms,
            )
        finally:
            if machine is not None and is_lh:
                try:
                    await machine.stop()
                except Exception:
                    pass

    def _build_protocol_kwargs(
        self,
        parameter_types: dict[str, str],
        setup: dict[str, Any],
        backend_name: str,
    ) -> dict[str, Any]:
        """Map protocol parameters to actual objects from the setup.

        Mirrors web_bridge.resolve_parameters() pattern:
        - Machine types → setup["machine"]
        - Resource types → setup[param_name] (created by DeckFactory)
        - Scalar types → skipped (use function defaults)
        - "state" → empty dict
        """
        kwargs: dict[str, Any] = {}
        is_plate_reader = backend_name == "PlateReaderChatterboxBackend"

        for param_name, type_str in parameter_types.items():
            # State dict
            if param_name == "state":
                kwargs["state"] = {}
                continue

            # Skip scalar types — use defaults
            if _is_scalar_type(type_str):
                continue

            # Machine types
            mt = _infer_machine_type(type_str)
            if mt:
                kwargs[param_name] = setup["machine"]
                continue

            # Resource types — resolved by DeckFactory and stored in setup
            if param_name in setup:
                kwargs[param_name] = setup[param_name]
                continue

            # Fallback: try name aliases (e.g. "source_plate" → "plate")
            resource = self._resolve_alias(param_name, type_str, setup)
            if resource is not None:
                kwargs[param_name] = resource

        return kwargs

    def _resolve_alias(
        self,
        param_name: str,
        type_str: str,
        setup: dict[str, Any],
    ) -> Any | None:
        """Resolve a parameter by name aliases when exact match isn't in setup.

        Handles common protocol naming conventions:
        - source_plate, dest_plate → any Plate in setup
        - diluent_trough, reagent_trough → any Trough in setup
        """
        extracted = extract_resource_types(type_str)
        if not extracted:
            return None
        primary = extracted[0]

        # Find all resources of the same type in setup
        candidates = [
            (k, v) for k, v in setup.items()
            if k not in ("machine", "deck") and hasattr(v, "name")
        ]

        if primary == "Plate":
            for key, val in candidates:
                if isinstance(val, type(Cor_96_wellplate_360ul_Fb(name="_check"))):
                    return val
        elif primary in ("Trough", "TipRack"):
            for key, val in candidates:
                return val  # Return first available resource

        return None
