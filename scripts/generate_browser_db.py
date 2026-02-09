#!/usr/bin/env python3
"""Generate a prebuilt SQLite database for browser mode with PLR definitions.

This script creates a complete SQLite database file that can be loaded directly
by the browser-mode SqliteService, containing:
1. Schema from SQLAlchemy ORM models
2. All PLR machine definitions (from LibCST static analysis)
3. All PLR resource definitions (from LibCST static analysis)
4. All PLR deck definitions (from LibCST static analysis)

Uses PLRSourceParser (LibCST-based) for static analysis without runtime imports,
avoiding deprecation warnings and side effects.

Usage:
    uv run scripts/generate_browser_db.py

Output:
    praxis/web-client/src/assets/db/praxis.db
"""

from __future__ import annotations

from praxis.backend.utils.protocol_serialization import serialize_protocol_function
import cloudpickle
import hashlib
import json
import sqlite3
from datetime import datetime
from pathlib import Path
from uuid import uuid4
import importlib
import sys

# Project paths
PROJECT_ROOT = Path(__file__).resolve().parent.parent
WEB_CLIENT_ROOT = PROJECT_ROOT / "praxis" / "web-client"
ASSETS_DB_DIR = WEB_CLIENT_ROOT / "src" / "assets" / "db"
SCHEMA_SQL_PATH = ASSETS_DB_DIR / "schema.sql"
OUTPUT_DB_PATH = ASSETS_DB_DIR / "praxis.db"


def generate_uuid_from_fqn(fqn: str) -> str:
  """Generate a deterministic UUID from a fully qualified name."""
  hash_bytes = hashlib.md5(fqn.encode()).digest()
  hex_str = hash_bytes.hex()
  return f"{hex_str[:8]}-{hex_str[8:12]}-{hex_str[12:16]}-{hex_str[16:20]}-{hex_str[20:32]}"


def safe_json_dumps(obj: object) -> str:
  """Safely serialize an object to JSON."""
  try:
    return json.dumps(obj)
  except (TypeError, ValueError):
    return "{}"


def discover_resources_static(conn: sqlite3.Connection) -> int:
  """Discover and insert all PLR resource definitions using static analysis."""
  from praxis.backend.utils.plr_static_analysis import (
    PLRSourceParser,
    find_plr_source_root,
  )

  parser = PLRSourceParser(find_plr_source_root())

  # Get class-based resources
  class_resources = parser.discover_resource_classes()

  # Get factory function-based resources
  factory_resources = parser.discover_resource_factories()

  # Combine and deduplicate by FQN
  all_resources = {r.fqn: r for r in class_resources}
  for r in factory_resources:
    if r.fqn not in all_resources:
      all_resources[r.fqn] = r

  now = datetime.now().isoformat()
  count = 0

  for res in all_resources.values():
    # Skip items that look like methods or private members
    if (
      res.name.startswith("get_")
      or res.name.startswith("set_")
      or res.name.startswith("_")
      or not any(c.isupper() for c in res.name)
    ):
      continue

    try:
      accession_id = generate_uuid_from_fqn(res.fqn)

      # Determine category
      category = res.category or res.class_type.value
      category = category.title() if category else "Resource"

      # Extract capabilities as properties
      props = {}
      if res.capabilities:
        if res.capabilities.channels:
          props["channels"] = res.capabilities.channels
        if res.capabilities.modules:
          props["modules"] = res.capabilities.modules

      # Determine consumable/reusable based on category
      is_consumable = category in ["TipRack", "Trough", "Reservoir"]
      is_reusable = category in ["Plate", "Carrier", "Deck"]

      conn.execute(
        """
                INSERT OR REPLACE INTO resource_definitions (
                    accession_id, fqn, name, description, plr_category,
                    is_consumable, is_reusable, vendor, manufacturer,
                    properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          res.fqn,
          res.name,
          res.docstring or "",
          category,
          1 if is_consumable else 0,
          1 if is_reusable else 0,
          res.vendor,
          res.manufacturer,
          safe_json_dumps(props),
          now,
          now,
        ),
      )
      count += 1
    except Exception as e:
      print(f"  [WARN] Failed to insert resource {res.name}: {e}")

  conn.commit()
  print(f"[generate_browser_db] Inserted {count} resource definitions")
  return count


def discover_machines_static(conn: sqlite3.Connection) -> int:
  """Discover and insert all PLR machine definitions using static analysis."""
  from praxis.backend.utils.plr_static_analysis import (
    MACHINE_FRONTEND_TYPES,
    PLRClassType,
    PLRSourceParser,
    find_plr_source_root,
  )

  parser = PLRSourceParser(find_plr_source_root())
  machines = parser.discover_machine_classes()

  now = datetime.now().isoformat()
  count = 0

  # Filter to frontend types only (exclude backends for the definition catalog)
  frontend_machines = [m for m in machines if m.class_type in MACHINE_FRONTEND_TYPES]

  for machine in frontend_machines:
    try:
      from praxis.backend.models.pydantic_internals.maintenance import MAINTENANCE_DEFAULTS

      accession_id = generate_uuid_from_fqn(f"machine:{machine.fqn}")

      # Determine machine category from class type
      category_map = {
        PLRClassType.LIQUID_HANDLER: "LiquidHandler",
        PLRClassType.PLATE_READER: "PlateReader",
        PLRClassType.HEATER_SHAKER: "HeaterShaker",
        PLRClassType.SHAKER: "Shaker",
        PLRClassType.TEMPERATURE_CONTROLLER: "TemperatureController",
        PLRClassType.CENTRIFUGE: "Centrifuge",
        PLRClassType.THERMOCYCLER: "Thermocycler",
        PLRClassType.PUMP: "Pump",
        PLRClassType.PUMP_ARRAY: "PumpArray",
        PLRClassType.FAN: "Fan",
        PLRClassType.SEALER: "Sealer",
        PLRClassType.PEELER: "Peeler",
        PLRClassType.POWDER_DISPENSER: "PowderDispenser",
        PLRClassType.INCUBATOR: "Incubator",
        PLRClassType.SCARA: "Arm",
      }
      category = category_map.get(machine.class_type, "Unknown")

      # Get default maintenance schedule
      maintenance_schedule = MAINTENANCE_DEFAULTS.get(
        category, MAINTENANCE_DEFAULTS["DEFAULT"]
      ).model_dump()

      # Check if has deck (liquid handlers typically have decks)
      has_deck = machine.class_type == PLRClassType.LIQUID_HANDLER

      # Get capabilities dict
      caps_dict = machine.to_capabilities_dict() if hasattr(machine, "to_capabilities_dict") else {}

      conn.execute(
        """
                INSERT OR REPLACE INTO machine_definitions (
                    accession_id, fqn, name, description, plr_category,
                    machine_category, has_deck, manufacturer,
                    capabilities, compatible_backends, available_simulation_backends, properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          machine.fqn,
          machine.name,
          machine.docstring or "",
          "Machine",
          category,
          1 if has_deck else 0,
          machine.manufacturer,
          safe_json_dumps(caps_dict),
          safe_json_dumps(machine.compatible_backends),
          safe_json_dumps(getattr(machine, "available_simulation_backends", [])),
          safe_json_dumps({}),
          now,
          now,
        ),
      )

      # Also insert into machine_frontend_definitions for new architecture
      conn.execute(
        """
                INSERT OR REPLACE INTO machine_frontend_definitions (
                    accession_id, fqn, name, description, plr_category,
                    machine_category, has_deck, manufacturer,
                    capabilities, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          machine.fqn,
          machine.name,
          machine.docstring or "",
          "Machine",
          category,
          1 if has_deck else 0,
          machine.manufacturer,
          safe_json_dumps(caps_dict),
          now,
          now,
        ),
      )

      # NOTE: We intentionally do NOT seed machine instances.
      # Users should instantiate machines from definitions via the UI.
      # This keeps the inventory clean and follows the catalog model.

      count += 1
    except Exception as e:
      print(f"  [WARN] Failed to insert machine {machine.name}: {e}")

  conn.commit()
  print(f"[generate_browser_db] Inserted {count} machine definitions")
  return count


# Define critical decks that must always be included
CRITICAL_DECKS = [
  {
    "name": "STARDeck",
    "fqn": "pylabrobot.liquid_handling.backends.hamilton.STAR.STARDeck",
    "category": "Deck",
    "vendor": "Hamilton",
    "manufacturer": "Hamilton",
    "docstring": "Hamilton STAR Deck definition",
  },
  {
    "name": "STARLetDeck",
    "fqn": "pylabrobot.liquid_handling.backends.hamilton.STARlet.STARLetDeck",
    "category": "Deck",
    "vendor": "Hamilton",
    "manufacturer": "Hamilton",
    "docstring": "Hamilton STARLet Deck definition",
  },
  {
    "name": "VantageDeck",
    "fqn": "pylabrobot.liquid_handling.backends.hamilton.Vantage.VantageDeck",
    "category": "Deck",
    "vendor": "Hamilton",
    "manufacturer": "Hamilton",
    "docstring": "Hamilton Vantage Deck definition",
  },
  {
    "name": "OT2Deck",
    "fqn": "pylabrobot.liquid_handling.backends.opentrons.deck.OT2Deck",
    "category": "Deck",
    "vendor": "Opentrons",
    "manufacturer": "Opentrons",
    "docstring": "Opentrons OT-2 Deck definition",
  },
]


def create_discovered_class_from_dict(d: dict) -> DiscoveredClass:
  """Create a DiscoveredClass object from a dictionary (fallback)."""
  from praxis.backend.utils.plr_static_analysis.models import (
    DiscoveredCapabilities,
    DiscoveredClass,
    PLRClassType,
  )

  return DiscoveredClass(
    fqn=d["fqn"],
    name=d["name"],
    module_path=d["fqn"].rsplit(".", 1)[0],
    file_path="manual_fallback",
    class_type=PLRClassType.DECK,
    category=d.get("category", "Deck"),
    vendor=d.get("vendor"),
    manufacturer=d.get("manufacturer"),
    docstring=d.get("docstring"),
    capabilities=DiscoveredCapabilities(),
  )


def discover_decks_static(conn: sqlite3.Connection) -> int:
  """Discover and insert all PLR deck definitions using static analysis + fallback."""
  from praxis.backend.utils.plr_static_analysis import (
    DiscoveredClass,
    PLRClassType,
    PLRSourceParser,
    find_plr_source_root,
  )

  parser = PLRSourceParser(find_plr_source_root())

  # Get class-based resources
  discovered_classes = parser.discover_resource_classes()

  # Get factory function-based resources
  discovered_factories = parser.discover_resource_factories()

  # Filter for decks and combine
  deck_classes = [r for r in discovered_classes if r.class_type == PLRClassType.DECK]
  deck_factories = [r for r in discovered_factories if r.class_type == PLRClassType.DECK]

  # Combine and deduplicate by FQN
  all_decks: dict[str, DiscoveredClass] = {d.fqn: d for d in deck_classes + deck_factories}

  # Add critical decks if missing (fallback)
  for critical in CRITICAL_DECKS:
    if critical["fqn"] not in all_decks:
      print(f"  [INFO] Static analysis missed {critical['name']}, adding from manual registry")
      all_decks[critical["fqn"]] = create_discovered_class_from_dict(critical)

  now = datetime.now().isoformat()
  count = 0

  for deck in all_decks.values():
    try:
      accession_id = generate_uuid_from_fqn(f"deck:{deck.fqn}")

      conn.execute(
        """
                INSERT OR REPLACE INTO deck_definition_catalog (
                    accession_id, fqn, name, description, plr_category,
                    additional_properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          deck.fqn,
          deck.name,
          deck.docstring or "",
          "Deck",
          safe_json_dumps({"manufacturer": deck.manufacturer, "vendor": deck.vendor}),
          now,
          now,
        ),
      )
      count += 1
    except Exception as e:
      print(f"  [WARN] Failed to insert deck {deck.name}: {e}")

  conn.commit()
  print(f"[generate_browser_db] Inserted {count} deck definitions")
  return count


def discover_protocols_static(conn: sqlite3.Connection) -> int:
  """Discover and insert all protocol definitions using static analysis."""
  from praxis.backend.utils.plr_static_analysis.visitors.protocol_discovery import (
    ProtocolFunctionVisitor,
  )
  from praxis.backend.core.simulation.simulator import ProtocolSimulator
  import libcst as cst

  protocols_dir = PROJECT_ROOT / "praxis" / "protocol" / "protocols"
  now = datetime.now().isoformat()
  count = 0

  simulator = ProtocolSimulator()

  if not protocols_dir.exists():
    return 0

  # Define protocols asset directory
  PROTOCOLS_ASSET_DIR = WEB_CLIENT_ROOT / "src" / "assets" / "protocols"
  PROTOCOLS_ASSET_DIR.mkdir(parents=True, exist_ok=True)

  for protocol_file in protocols_dir.glob("*.py"):
    if protocol_file.name.startswith("__"):
      continue

    try:
      module_name = f"praxis.protocol.protocols.{protocol_file.stem}"
      source_code = protocol_file.read_text()

      # Parse with LibCST
      tree = cst.parse_module(source_code)
      visitor = ProtocolFunctionVisitor(module_name, str(protocol_file))
      tree.visit(visitor)

      for definition in visitor.definitions:
        accession_id = generate_uuid_from_fqn(definition.fqn)

        # Default category based on keywords
        category = "General"
        name_lower = definition.name.lower()
        if "plate" in name_lower or "prep" in name_lower:
          category = "Assay Prep"
        elif "transfer" in name_lower:
          category = "Liquid Handling"
        elif "kinetic" in name_lower or "reader" in name_lower:
          category = "Plate Reading"

        # Run real simulation analysis
        print(f"  [simulation] Analyzing {definition.fqn}...")
        try:
          # Import the protocol module
          # Ensure path is in sys.path
          if str(PROJECT_ROOT) not in sys.path:
            sys.path.append(str(PROJECT_ROOT))

          module = importlib.import_module(module_name)
          func = getattr(module, definition.name)

          # Serialize protocol function for offline use
          try:
            serialized_data = serialize_protocol_function(func)
            path = WEB_CLIENT_ROOT / "src" / "assets" / "protocols" / f"{accession_id}.pkl"
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(serialized_data)
            print(f"  [pickle] Generated {path}")
          except Exception as ser_e:
            print(f"  [pickle] ERROR: Failed to serialize {definition.fqn}: {ser_e}")

          parameter_types = {p.name: p.type_hint for p in definition.parameters}

          # Run analysis
          sim_result = simulator.analyze_protocol_sync(
            protocol_func=func, parameter_types=parameter_types
          )

          simulation_result_json = safe_json_dumps(sim_result.to_cache_dict())
          inferred_requirements_json = safe_json_dumps(sim_result.inferred_requirements)
          failure_modes_json = safe_json_dumps(sim_result.failure_modes)
        except Exception as e:
          print(f"  [simulation] ERROR: Protocol analysis failed for {definition.fqn}: {e}")
          # Fallback to a marked-as-failed or minimal result if needed?
          # For now, we'll keep the mock structure but with an error state if it fails
          simulation_result_json = safe_json_dumps(
            {
              "passed": False,
              "level_completed": "none",
              "violations": [{"type": "error", "message": str(e)}],
              "simulated_at": now,
            }
          )
          inferred_requirements_json = safe_json_dumps([])
          failure_modes_json = safe_json_dumps([])

        conn.execute(
          """
                    INSERT OR REPLACE INTO function_protocol_definitions (
                        accession_id, name, fqn, module_name, function_name,
                        source_file_path, description, category, tags,
                        hardware_requirements_json,
                        inferred_requirements_json, failure_modes_json, simulation_result_json,
                        computation_graph_json, source_hash, requires_deck,
                        requires_linked_indices,
                        is_top_level, created_at, updated_at, version,
                        solo_execution, preconfigure_deck, deprecated
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
          (
            accession_id,
            definition.name.replace("_", " ").title(),
            definition.fqn,
            definition.module_name,
            definition.name,
            str(protocol_file.relative_to(PROJECT_ROOT)),
            definition.docstring,
            category,
            safe_json_dumps(["demo", category.lower().replace(" ", "-")]),
            safe_json_dumps(definition.hardware_requirements or {}),
            inferred_requirements_json,
            failure_modes_json,
            simulation_result_json,
            safe_json_dumps(definition.computation_graph),
            definition.source_hash,
            1 if definition.requires_deck else 0,
            1 if getattr(definition, "requires_linked_indices", False) else 0,
            1,  # is_top_level default
            now,
            now,
            "0.1.0",  # default version
            0,  # solo_execution default
            0,  # preconfigure_deck default
            0,  # deprecated default
          ),
        )

        # Insert parameters into parameter_definitions table (excluding assets)
        for param in definition.parameters:
          # Skip assets - they go to protocol_asset_requirements
          if param.is_asset:
            continue

          param_id = generate_uuid_from_fqn(f"param:{definition.fqn}:{param.name}")
          conn.execute(
            """
                        INSERT OR REPLACE INTO parameter_definitions (
                            accession_id, protocol_definition_accession_id, name, type_hint, fqn,
                            is_deck_param, optional, default_value_repr, description,
                            constraints_json, field_type, is_itemized, itemized_spec_json, linked_to, ui_hint_json,
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
            (
              param_id,
              accession_id,
              param.name,
              param.type_hint,
              f"{definition.fqn}.{param.name}",
              0,  # is_deck_param (simplified)
              param.is_optional,
              str(param.default_value) if param.default_value is not None else None,
              "",  # description
              safe_json_dumps(param.constraints_json if hasattr(param, "constraints_json") else {}),
              param.field_type,
              1 if param.is_itemized else 0,
              safe_json_dumps(param.itemized_spec),
              param.linked_to,
              safe_json_dumps(param.ui_hint_json if hasattr(param, "ui_hint_json") else {}),
              now,
              now,
            ),
          )

        # Insert asset requirements into protocol_asset_requirements table
        for asset in definition.raw_assets:
          asset_id = generate_uuid_from_fqn(f"asset:{definition.fqn}:{asset['name']}")
          conn.execute(
            """
                        INSERT OR REPLACE INTO protocol_asset_requirements (
                            accession_id, protocol_definition_accession_id, name, type_hint_str,
                            actual_type_str, fqn, optional, default_value_repr, description,
                            required_plr_category, constraints_json, location_constraints_json, 
                            created_at, updated_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
            (
              asset_id,
              accession_id,
              asset["name"],
              asset["type_hint_str"],
              asset["actual_type_str"],
              asset["fqn"],
              asset.get("optional", False),
              asset.get("default_value_repr"),
              asset.get("description", ""),
              asset.get("required_plr_category"),
              safe_json_dumps({}),  # constraints (empty for now)
              safe_json_dumps({}),  # location_constraints (empty for now)
              now,
              now,
            ),
          )

        count += 1

    except Exception as e:
      print(f"  [WARN] Failed to process {protocol_file.name}: {e}")

  conn.commit()
  print(f"[generate_browser_db] Inserted {count} protocol definitions")
  return count


def discover_backends_static(conn: sqlite3.Connection) -> int:
  """Discover and insert all PLR backend definitions using static analysis."""
  from praxis.backend.utils.plr_static_analysis import (
    MACHINE_BACKEND_TYPES,
    PLRClassType,
    PLRSourceParser,
    find_plr_source_root,
  )

  parser = PLRSourceParser(find_plr_source_root())
  machines = parser.discover_machine_classes()

  # Filter to backend types only
  backends = [m for m in machines if m.class_type in MACHINE_BACKEND_TYPES]

  now = datetime.now().isoformat()
  count = 0

  # Map backend types to frontend category names
  backend_category_map = {
    PLRClassType.LH_BACKEND: "LiquidHandlerBackend",
    PLRClassType.PR_BACKEND: "PlateReaderBackend",
    PLRClassType.HS_BACKEND: "HeaterShakerBackend",
    PLRClassType.SHAKER_BACKEND: "ShakerBackend",
    PLRClassType.TEMP_BACKEND: "TemperatureControllerBackend",
    PLRClassType.CENTRIFUGE_BACKEND: "CentrifugeBackend",
    PLRClassType.THERMOCYCLER_BACKEND: "ThermocyclerBackend",
    PLRClassType.PUMP_BACKEND: "PumpBackend",
    PLRClassType.PUMP_ARRAY_BACKEND: "PumpArrayBackend",
    PLRClassType.FAN_BACKEND: "FanBackend",
    PLRClassType.SEALER_BACKEND: "SealerBackend",
    PLRClassType.PEELER_BACKEND: "PeelerBackend",
    PLRClassType.POWDER_DISPENSER_BACKEND: "PowderDispenserBackend",
    PLRClassType.INCUBATOR_BACKEND: "IncubatorBackend",
    PLRClassType.SCARA_BACKEND: "ScaraBackend",
  }

  # Map backend types to frontend FQNs
  backend_frontend_fqn_map = {
    PLRClassType.LH_BACKEND: "pylabrobot.liquid_handling.LiquidHandler",
    PLRClassType.PR_BACKEND: "pylabrobot.plate_reading.PlateReader",
    PLRClassType.HS_BACKEND: "pylabrobot.heating_shaking.HeaterShaker",
    PLRClassType.SHAKER_BACKEND: "pylabrobot.shaking.Shaker",
    PLRClassType.TEMP_BACKEND: "pylabrobot.temperature_controlling.TemperatureController",
    PLRClassType.CENTRIFUGE_BACKEND: "pylabrobot.centrifuging.Centrifuge",
    PLRClassType.THERMOCYCLER_BACKEND: "pylabrobot.thermocycling.Thermocycler",
    PLRClassType.PUMP_BACKEND: "pylabrobot.pumping.Pump",
    PLRClassType.PUMP_ARRAY_BACKEND: "pylabrobot.pumping.PumpArray",
    PLRClassType.FAN_BACKEND: "pylabrobot.fans.Fan",
    PLRClassType.SEALER_BACKEND: "pylabrobot.plate_sealing.Sealer",
    PLRClassType.PEELER_BACKEND: "pylabrobot.plate_peeling.Peeler",
    PLRClassType.POWDER_DISPENSER_BACKEND: "pylabrobot.powder_dispensing.PowderDispenser",
    PLRClassType.INCUBATOR_BACKEND: "pylabrobot.incubating.Incubator",
    PLRClassType.SCARA_BACKEND: "pylabrobot.scara.SCARA",
  }

  # First, seed machine_frontend_definitions to satisfy foreign key constraints
  for backend_type, frontend_fqn in backend_frontend_fqn_map.items():
    frontend_id = generate_uuid_from_fqn(f"machine:{frontend_fqn}")
    frontend_category = backend_category_map.get(backend_type, "Unknown").replace("Backend", "")
    
    conn.execute(
      """
            INSERT OR REPLACE INTO machine_frontend_definitions (
                accession_id, fqn, name, description, plr_category,
                machine_category, has_deck, manufacturer,
                capabilities, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
      (
        frontend_id,
        frontend_fqn,
        frontend_category,
        f"Generic {frontend_category} frontend",
        "Machine",
        frontend_category,
        1 if "LiquidHandler" in frontend_category else 0,
        "PyLabRobot",
        safe_json_dumps({}),
        now,
        now,
      ),
    )

  for backend in backends:
    try:
      accession_id = generate_uuid_from_fqn(f"backend:{backend.fqn}")
      category = backend_category_map.get(backend.class_type, "UnknownBackend")
      frontend_fqn = backend_frontend_fqn_map.get(backend.class_type)

      # Get capabilities dict
      caps_dict = backend.to_capabilities_dict() if hasattr(backend, "to_capabilities_dict") else {}

      # Determine backend type
      backend_type = "simulator" if "Chatterbox" in backend.fqn or "simulated" in backend.fqn else "hardware"

      conn.execute(
        """
                INSERT OR REPLACE INTO machine_backend_definitions (
                    accession_id, fqn, name, description, 
                    manufacturer, model, is_deprecated, backend_type, 
                    frontend_definition_accession_id, connection_config,
                    properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          backend.fqn,
          backend.name,
          backend.docstring or "",
          backend.manufacturer,
          backend.name,
          0, # is_deprecated
          backend_type,
          generate_uuid_from_fqn(f"machine:{frontend_fqn}"),
          safe_json_dumps({}), # connection_config
          safe_json_dumps(caps_dict), # properties_json (using capabilities for now)
          now,
          now,
        ),
      )

      # NOTE: We intentionally do NOT seed machine instances from backends.
      # Users should instantiate machines from definitions via the UI.

      count += 1
    except Exception as e:
      print(f"  [WARN] Failed to insert backend {backend.name}: {e}")

  conn.commit()
  print(f"[generate_browser_db] Inserted {count} backend definitions")
  return count


def ensure_minimal_backends(conn: sqlite3.Connection) -> None:
  """Ensure every frontend type has at least one simulator backend definition.
  
  Chatterbox backends are PLR's official simulation backends with realistic behavior.
  Simulated backends are synthetic fallbacks created here as safety nets.
  
  We only create a Simulated fallback if NO Chatterbox/simulator backend exists
  for the frontend type. This avoids cluttering the UI with redundant options.
  """
  now = datetime.now().isoformat()

  # All known frontend types
  frontend_types = [
    ("LiquidHandler", "pylabrobot.liquid_handling.LiquidHandler"),
    ("PlateReader", "pylabrobot.plate_reading.PlateReader"),
    ("HeaterShaker", "pylabrobot.heating_shaking.HeaterShaker"),
    ("Shaker", "pylabrobot.shaking.Shaker"),
    ("TemperatureController", "pylabrobot.temperature_controlling.TemperatureController"),
    ("Centrifuge", "pylabrobot.centrifuging.Centrifuge"),
    ("Thermocycler", "pylabrobot.thermocycling.Thermocycler"),
    ("Pump", "pylabrobot.pumping.Pump"),
    ("PumpArray", "pylabrobot.pumping.PumpArray"),
    ("Fan", "pylabrobot.fans.Fan"),
    ("Sealer", "pylabrobot.plate_sealing.Sealer"),
    ("Peeler", "pylabrobot.plate_peeling.Peeler"),
    ("PowderDispenser", "pylabrobot.powder_dispensing.PowderDispenser"),
    ("Incubator", "pylabrobot.incubating.Incubator"),
    ("Arm", "pylabrobot.scara.SCARA"),
  ]

  for short_name, frontend_fqn in frontend_types:
    # Check if any SIMULATOR backend exists for this frontend
    # (Chatterbox or other simulators - not hardware backends)
    cursor = conn.execute(
      """SELECT count(*) FROM machine_backend_definitions 
         WHERE frontend_definition_accession_id = ? 
         AND backend_type = 'simulator'""",
      (generate_uuid_from_fqn(f"machine:{frontend_fqn}"),)
    )
    simulator_count = cursor.fetchone()[0]

    if simulator_count == 0:
      # No Chatterbox or simulator exists - create a synthetic fallback
      fqn = f"pylabrobot.backends.simulated.{short_name}Backend"
      accession_id = generate_uuid_from_fqn(f"backend:{fqn}")
      
      print(f"  [backends] Creating Simulated fallback for {short_name} (no Chatterbox found)")

      conn.execute(
        """
                INSERT OR REPLACE INTO machine_backend_definitions (
                    accession_id, fqn, name, description, 
                    manufacturer, model, is_deprecated, backend_type, 
                    frontend_definition_accession_id, connection_config,
                    properties_json, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
        (
          accession_id,
          fqn,
          f"Simulated {short_name}",
          f"Generic simulated backend for {short_name} (fallback - no Chatterbox available)",
          "PyLabRobot",
          f"Simulated {short_name}",
          0,
          "simulator",
          generate_uuid_from_fqn(f"machine:{frontend_fqn}"),
          safe_json_dumps({}),
          safe_json_dumps({}),
          now,
          now,
        ),
      )
    else:
      print(f"  [backends] {short_name}: {simulator_count} Chatterbox/simulator backend(s) found, skipping Simulated fallback")

  # NOTE: We intentionally do NOT seed machine instances.
  # Users should instantiate machines from definitions via the UI.


def insert_metadata(conn: sqlite3.Connection) -> None:
  """Insert metadata about the database generation."""
  now = datetime.now().isoformat()

  conn.execute(
    "INSERT OR REPLACE INTO _schema_metadata (key, value) VALUES (?, ?)",
    ("generated_at", now),
  )
  conn.execute(
    "INSERT OR REPLACE INTO _schema_metadata (key, value) VALUES (?, ?)",
    ("schema_version", "1.0.0"),
  )
  conn.execute(
    "INSERT OR REPLACE INTO _schema_metadata (key, value) VALUES (?, ?)",
    ("generator", "generate_browser_db.py (LibCST static analysis)"),
  )
  conn.commit()


def add_sample_workcell(conn: sqlite3.Connection) -> None:
  """Add a sample workcell for demo purposes."""
  now = datetime.now().isoformat()
  workcell_id = str(uuid4())

  conn.execute(
    """
        INSERT OR REPLACE INTO workcells (
            accession_id, name, description, physical_location, status,
            created_at, updated_at, properties_json
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
    (
      workcell_id,
      "Demo Workcell",
      "A sample workcell for browser-mode demonstration",
      "Virtual Lab 1",
      "available",
      now,
      now,
      "{}",
    ),
  )
  conn.commit()


def enrich_resource_definitions(conn: sqlite3.Connection) -> int:
  """Second pass: instantiate each resource and call .serialize().

  Populates plr_definition_details_json with the full serialized
  representation and backfills indexed columns (size, num_items, etc.)
  from the serialized data.
  """
  import inspect

  # Abstract/base classes that can't be meaningfully instantiated.
  SKIP_NAMES = {
    "TecanPlate", "TecanResource", "TecanTipRack", "TecanTrash",
    "TecanPlateCarrier", "TecanTipCarrier", "TecanWashStation",
  }

  cursor = conn.execute("SELECT accession_id, fqn, name FROM resource_definitions")
  rows = cursor.fetchall()

  # TODO: Open PLR issue — many carrier factories omit pedestal_size_z but
  # PlateHolder.__init__ now requires it. Default to 4.74 (from PLT_CAR_L5AC_A00).
  _patched = False
  try:
    from pylabrobot.resources.carrier import PlateHolder
    _orig_init = PlateHolder.__init__

    def _patched_init(self, *a, pedestal_size_z=4.74, **kw):
      _orig_init(self, *a, pedestal_size_z=pedestal_size_z, **kw)

    PlateHolder.__init__ = _patched_init
    _patched = True
  except Exception:
    pass

  enriched = 0
  errors = 0

  for accession_id, fqn, name in rows:
    # Skip abstract base classes
    _, attr_name = fqn.rsplit(".", 1)
    if attr_name in SKIP_NAMES:
      continue

    try:
      module_path = fqn.rsplit(".", 1)[0]
      module = importlib.import_module(module_path)
      obj = getattr(module, attr_name)

      # Instantiate — factory function or class
      instance = None
      if inspect.isfunction(obj):
        try:
          instance = obj(name=f"_enrich_{attr_name}")
        except Exception:
          pass
      elif isinstance(obj, type):
        try:
          instance = obj(name=f"_enrich_{attr_name}")
        except TypeError:
          try:
            instance = obj(name=f"_enrich_{attr_name}", size_x=0, size_y=0, size_z=0)
          except Exception:
            pass

      if instance is None:
        continue

      # Serialize the full resource
      if not hasattr(instance, "serialize"):
        continue

      serialized = instance.serialize()

      # Extract indexed columns from serialized dict
      size_x = serialized.get("size_x")
      size_y = serialized.get("size_y")
      size_z = serialized.get("size_z")

      if not size_x:  # skip zero-dimension fallback instances
        continue

      num_items = None
      if hasattr(instance, "num_items"):
        try:
          num_items = instance.num_items
        except Exception:
          pass

      plate_type = serialized.get("plate_type") or getattr(instance, "plate_type", None)

      conn.execute(
        """UPDATE resource_definitions SET
            size_x_mm = ?, size_y_mm = ?, size_z_mm = ?,
            num_items = COALESCE(?, num_items),
            plate_type = COALESCE(?, plate_type),
            plr_definition_details_json = ?
           WHERE accession_id = ?""",
        (
          size_x, size_y, size_z,
          num_items,
          plate_type,
          safe_json_dumps(serialized),
          accession_id,
        ),
      )
      enriched += 1
    except Exception as e:
      errors += 1
      if errors <= 5:
        print(f"  [WARN] Could not enrich {name} ({fqn}): {e}")

  # Restore original PlateHolder init
  if _patched:
    PlateHolder.__init__ = _orig_init

  conn.commit()
  print(f"[generate_browser_db] Enriched {enriched}/{len(rows)} resource definitions ({errors} errors)")
  return enriched


def main() -> None:
  """Main entry point for database generation."""
  # Ensure output directory exists
  ASSETS_DB_DIR.mkdir(parents=True, exist_ok=True)

  # Check for schema file
  if not SCHEMA_SQL_PATH.exists():
    return

  # Remove existing database
  if OUTPUT_DB_PATH.exists():
    OUTPUT_DB_PATH.unlink()

  # Create new database
  conn = sqlite3.connect(OUTPUT_DB_PATH)

  try:
    # Load and execute schema
    schema = SCHEMA_SQL_PATH.read_text()
    conn.executescript(schema)

    # Discover and insert PLR definitions using static analysis
    discover_resources_static(conn)

    # Enrich with runtime-extracted properties via .serialize()
    enrich_resource_definitions(conn)

    discover_machines_static(conn)

    discover_decks_static(conn)

    discover_protocols_static(conn)

    discover_backends_static(conn)

    # Ensure simulated definitions for all types (fixes SCARA etc)
    ensure_minimal_backends(conn)

    # Add sample workcell
    add_sample_workcell(conn)

    # Update metadata
    insert_metadata(conn)

    # Get database size
    conn.commit()
    OUTPUT_DB_PATH.stat().st_size

    # Show table statistics
    cursor = conn.execute(
      """
            SELECT name FROM sqlite_master
            WHERE type='table' AND name NOT LIKE 'sqlite_%' AND name NOT LIKE '_%'
            ORDER BY name
            """
    )
    for (table_name,) in cursor.fetchall():
      count_cursor = conn.execute(f"SELECT COUNT(*) FROM {table_name}")
      count = count_cursor.fetchone()[0]
      print(f"  {table_name:30}: {count}")

  except Exception:
    raise
  finally:
    conn.close()


if __name__ == "__main__":
  main()
