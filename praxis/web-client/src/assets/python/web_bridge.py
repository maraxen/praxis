"""WebBridge - PyLabRobot IO shim for browser-based hardware control.

This module provides:
1. WebBridgeIO: A transport layer that routes raw bytes through WebWorker messages
   to Angular's WebSerialService, enabling PLR machines to communicate with
   physical hardware connected to the browser.
2. WebBridgeBackend: A high-level backend that sends PLR commands to the browser
   (legacy approach, kept for compatibility).
3. patch_io_for_browser: Helper to patch any PLR machine's IO layer for browser mode.
4. materialize_context: Materializes the execution context from a Typed Execution Manifest.
"""
import json
import js
import sys
import importlib

def materialize_context(manifest):
  """
  Materializes the execution context from a Typed Execution Manifest.
  
  Args:
      manifest: Dictionary or JsProxy conforming to ExecutionManifest interface.
      
  Returns:
      A dictionary of resolved kwargs for protocol execution.
  """
  if hasattr(manifest, "to_py"):
    manifest = manifest.to_py()
  
  print(f"[Browser] Materializing context for protocol: {manifest['protocol']['fqn']}")
  
  protocol_info = manifest.get("protocol", {})
  requires_deck = protocol_info.get("requires_deck", True)
  
  # 1. Instantiate Deck
  deck = None
  if requires_deck:
    deck_manifest = None
    # Find deck manifest in machines (LiquidHandler)
    for m in manifest.get("machines", []):
      if m.get("machine_type") == "LiquidHandler" and "deck" in m:
        deck_manifest = m["deck"]
        break
    
    if deck_manifest:
      fqn = deck_manifest["fqn"]
      print(f"[Browser] Instantiating deck: {fqn}")
      try:
        module_path, class_name = fqn.rsplit(".", 1)
        module = importlib.import_module(module_path)
        DeckClass = getattr(module, class_name)
        # NOTE: STARLetDeck() etc don't take 'name' argument in newer PLR
        deck = DeckClass()
      except Exception as e:
        print(f"Error instantiating deck {fqn}: {e}. Falling back to generic Deck.")
        try:
          from pylabrobot.resources import Deck
          deck = Deck()
        except ImportError:
          print("Could not import pylabrobot.resources.Deck, deck will be None")
      
      # Populate Layout (Carriers and Resources)
      layout = deck_manifest.get("layout", [])
      layout_type = deck_manifest.get("layout_type", "rail-based")
      
      for entry in layout:
        try:
          if layout_type == "rail-based":
            _materialize_rail_entry(deck, entry)
          else:
            _materialize_slot_entry(deck, entry)
        except Exception as e:
          print(f"Error materializing layout entry {entry.get('name', '?')}: {e}")

  # 2. Instantiate Machines
  machines = {}
  for m_entry in manifest.get("machines", []):
    machine_name = m_entry["param_name"]
    m_type = m_entry.get("machine_type", "LiquidHandler")
    print(f"[Browser] Instantiating machine: {machine_name} (type={m_type}, backend={m_entry['backend_fqn']})")
    
    backend = create_configured_backend(m_entry)
    
    try:
      machine = _instantiate_machine(m_type, backend, deck, manifest)
      machines[machine_name] = machine
    except Exception as e:
      print(f"Error instantiating machine {machine_name}: {e}")

  # 3. Resolve Parameters
  kwargs = {}
  kwargs.update(machines)
  
  for p in manifest.get("parameters", []):
    p_name = p["name"]
    if p_name in kwargs:
      continue  # Already provided as a machine
    
    if p.get("is_deck_resource") and deck:
      try:
        resource = deck.get_resource(p["name"])
        if resource:
          kwargs[p_name] = resource
        else:
          print(f"Warning: Resource '{p['name']}' not found on deck. Skipping.")
      except Exception as e:
        print(f"Warning: Could not resolve deck resource '{p['name']}': {e}")
    else:
      kwargs[p_name] = p.get("value")
      
  return kwargs


def _import_class(fqn):
  """Import a class by its fully qualified name."""
  module_path, class_name = fqn.rsplit(".", 1)
  module = importlib.import_module(module_path)
  return getattr(module, class_name)


def instantiate_resource(fqn, name):
  """Public API: Instantiate a PLR resource class by FQN.
  
  Called from materialize_context (deck layout) and
  PlaygroundComponent.generateResourceCode (JupyterLite notebook injection).
  
  PLR resource subclasses (Plate, TipRack, etc.) define their own sizes
  in their __init__ or class body. We only pass `name` to avoid overriding
  class-defined dimensions. Falls back to base Resource with zero sizes.
  """
  try:
    ResourceClass = _import_class(fqn)
    # Try name-only first (works for most PLR resource subclasses)
    try:
      return ResourceClass(name=name)
    except TypeError:
      # Some base classes require size args
      return ResourceClass(name=name, size_x=0, size_y=0, size_z=0)
  except Exception as e:
    print(f"Could not instantiate resource {fqn}: {e}")
    from pylabrobot.resources import Resource
    return Resource(name=name, size_x=0, size_y=0, size_z=0)


def _materialize_rail_entry(deck, entry):
  """Materialize a carrier + children onto a rail-based deck."""
  # TODO: Open PLR issue — many carrier factories omit pedestal_size_z but
  # PlateHolder.__init__ now requires it. Default to 4.74 (from PLT_CAR_L5AC_A00).
  try:
    from pylabrobot.resources.carrier import PlateHolder
    _orig = PlateHolder.__init__
    def _patched(self, *a, pedestal_size_z=4.74, **kw):
      _orig(self, *a, pedestal_size_z=pedestal_size_z, **kw)
    PlateHolder.__init__ = _patched
  except Exception:
    _orig = None

  carrier_fqn = entry["carrier_fqn"]
  CarrierClass = _import_class(carrier_fqn)
  carrier = CarrierClass(name=entry["name"])
  deck.assign_child_resource(carrier, rails=entry["rails"])
  
  for child in entry.get("children", []):
    resource = instantiate_resource(child["resource_fqn"], child["name"])
    # PLR Carrier uses __setitem__ which delegates to assign_resource_to_site
    carrier[child["slot"]] = resource

  # Restore original
  if _orig is not None:
    PlateHolder.__init__ = _orig


def _materialize_slot_entry(deck, entry):
  """Materialize a resource onto a slot-based deck (e.g. OTDeck)."""
  resource = instantiate_resource(entry["resource_fqn"], entry["name"])
  # OTDeck uses assign_child_at_slot(resource, slot_number), not assign_child_resource
  deck.assign_child_at_slot(resource, entry["slot"])


# Machine type → (module_path, class_name) mapping for supported PLR machine types
_MACHINE_CLASS_MAP = {
  "LiquidHandler": ("pylabrobot.liquid_handling", "LiquidHandler"),
  "PlateReader": ("pylabrobot.plate_reading", "PlateReader"),
  "HeaterShaker": ("pylabrobot.heating_shaking", "HeaterShaker"),
  "Shaker": ("pylabrobot.shaking", "Shaker"),
  "Centrifuge": ("pylabrobot.centrifuge", "Centrifuge"),
  "Incubator": ("pylabrobot.incubator", "Incubator"),
}

def create_machine_frontend(category, backend, name=None, deck=None):
  """Public API: Instantiate a PLR machine frontend by category string.
  
  Called from:
    - materialize_context (protocol execution manifest)
    - DirectControlKernelService.ensureMachineInstantiated (generated Python)
    - PlaygroundComponent.generateMachineCode (JupyterLite notebook injection)
  
  Args:
      category: Machine category string (e.g., 'LiquidHandler', 'PlateReader')
      backend: A PLR backend instance (from create_configured_backend)
      name: Optional name for the machine (required by some types like PlateReader)
      deck: Optional deck instance (used by LiquidHandler)
      
  Returns:
      A PLR machine frontend instance, or the raw backend as fallback.
  """
  import inspect
  
  mapping = _MACHINE_CLASS_MAP.get(category)
  if not mapping:
    print(f"Warning: Unknown machine category '{category}', returning raw backend")
    return backend
  
  try:
    mod_path, cls_name = mapping
    mod = importlib.import_module(mod_path)
    MachineClass = getattr(mod, cls_name)
    
    # Introspect the constructor to pass only accepted kwargs
    sig = inspect.signature(MachineClass.__init__)
    params = sig.parameters
    
    kwargs = {}
    if "backend" in params:
      kwargs["backend"] = backend
    if "deck" in params and deck is not None:
      kwargs["deck"] = deck
    if "name" in params and name is not None:
      kwargs["name"] = name
    # PlateReader and similar require size; provide defaults if accepted but not given
    for dim in ("size_x", "size_y", "size_z"):
      if dim in params and params[dim].default is inspect.Parameter.empty:
        kwargs[dim] = 0.0
    
    machine = MachineClass(**kwargs)
    print(f"[web_bridge] Created {cls_name}({', '.join(f'{k}=...' for k in kwargs)})")
    return machine
    
  except Exception as e:
    print(f"Warning: Could not instantiate {category} ({e}), returning raw backend")
    return backend


def _instantiate_machine(machine_type, backend, deck, manifest):
  """Internal: Instantiate machine and apply execution patches.
  
  Wraps create_machine_frontend with protocol-specific patches
  (state emission, function call logging) used only during EXECUTE_BLOB.
  """
  machine = create_machine_frontend(machine_type, backend, deck=deck)
  
  if machine_type == "LiquidHandler" and machine is not backend:
    try:
      patch_state_emission(machine)
      run_id = manifest.get("run_id") if manifest else None
      if run_id:
        patch_function_call_logging(machine, run_id)
    except Exception as e:
      print(f"Warning: Could not apply execution patches: {e}")
  
  return machine

import asyncio
import builtins
import json
import os
import sys
import uuid
import json
from typing import Any

try:
  import js
except ImportError:
  js = None

# Check if we're running in browser/Pyodide mode
IS_BROWSER_MODE = "pyodide" in sys.modules


def resolve_parameters(params, metadata, asset_reqs, asset_specs=None):
  """
  Resolves protocol parameters by instantiating PLR objects for resources.

  Args:
      params: Dictionary of parameter values (JSON-serialized)
      metadata: Dictionary of parameter metadata (name -> type_hint)
      asset_reqs: Dictionary of asset requirements (accession_id -> type_hint)
      asset_specs: Dictionary of asset specifications (uuid -> {num_items, name, type})

  Returns:
      Dictionary of resolved parameters
  """
  try:
    import pylabrobot.resources as res
  except ImportError:
    # If PLR is not available, just return the raw params
    return params

  if asset_specs is None:
    asset_specs = {}

  resolved = {}
  for name, value in params.items():
    type_hint = metadata.get(name, "").lower()
    asset_type = asset_reqs.get(name, "").lower()

    # Check if this parameter is a resource (Plate, TipRack, etc.)
    effective_type = type_hint or asset_type
    is_resource = any(t in effective_type for t in ["plate", "tiprack", "resource", "container"])
    
    # Heuristic for JS resource objects even if metadata is missing
    if not is_resource and isinstance(value, dict) and ("fqn" in value or "asset_type" in value):
      is_resource = True

    if is_resource:
      # If value is a dict, it's likely a Resource object from the frontend
      # (Legacy/direct passing support)
      if isinstance(value, dict):
        resource_fqn = value.get("fqn", "")
        resource_name = value.get("name", name)

        # 1. Try to dynamically import and instantiate from FQN
        if resource_fqn:
          try:
            parts = resource_fqn.split('.')
            module_path = ".".join(parts[:-1])
            class_name = parts[-1]
            # Use __import__ to load the module
            module = __import__(module_path, fromlist=[class_name])
            ResourceClass = getattr(module, class_name)
            # Instantiate with name
            resolved[name] = ResourceClass(name=resource_name)
            continue # Success!
          except Exception as e:
            pass # Fallback to heuristics

        # 2. Simple heuristic fallback
        if "plate" in resource_fqn.lower() or "plate" in effective_type:
          resolved[name] = res.Plate(name=resource_name, size_x=127.7, size_y=85.4, size_z=14.5, num_items_x=12, num_items_y=8)
        elif "tiprack" in resource_fqn.lower() or "tiprack" in effective_type:
          resolved[name] = res.TipRack(name=resource_name, size_x=127.7, size_y=85.4, size_z=14.5, num_items_x=12, num_items_y=8)
        elif "trough" in resource_fqn.lower() or "reservoir" in resource_fqn.lower() or "trough" in effective_type:
          resolved[name] = res.Plate(name=resource_name, size_x=127.7, size_y=85.4, size_z=14.5, num_items_x=1, num_items_y=1) # Simple fallback
        else:
          resolved[name] = res.Resource(name=resource_name, size_x=0, size_y=0, size_z=0)

      else:
        # Value is a string (UUID)
        spec = asset_specs.get(value)

        if spec:
          # Use specs from backend/DB
          num_items = spec.get("num_items", 96)
          r_name = spec.get("name", name)

          # Geometry heuristics
          if num_items == 384:
            sx, sy = 24, 16
          elif num_items == 24:
            sx, sy = 6, 4
          elif num_items == 96:
            sx, sy = 12, 8
          else:
            sx, sy = 12, 8  # Default fallback

          if "plate" in effective_type:
            resolved[name] = res.Plate(name=r_name, size_x=sx, size_y=sy, size_z=10)
          elif "tiprack" in effective_type:
            resolved[name] = res.TipRack(name=r_name, size_x=sx, size_y=sy)
          else:
            # Generic Container/Resource
            resolved[name] = res.Container(name=r_name, size_x=sx * 9, size_y=sy * 9, size_z=10)

        else:
          # Fallback if no spec found
          if "plate" in effective_type:
            resolved[name] = res.Plate(name=name, size_x=127.7, size_y=85.4, size_z=14.5, num_items_x=12, num_items_y=8)
          elif "tiprack" in effective_type:
            resolved[name] = res.TipRack(name=name, size_x=127.7, size_y=85.4, size_z=14.5, num_items_x=12, num_items_y=8)
          else:
            resolved[name] = value
    else:
      resolved[name] = value

  return resolved


def emit_well_state(lh: Any):
  """
  Serializes the current state of a LiquidHandler's deck and emits it
  to the browser's main thread via postMessage.
  """
  if not IS_BROWSER_MODE:
    return

  try:
    from pylabrobot.resources import Plate, TipRack
  except ImportError:
    return

  state_update = {}

  # Traverse deck to find plates and tip racks
  # For each resource, we extract liquid levels and tip presence
  for resource in lh.deck.get_all_resources():
    res_name = resource.name

    if isinstance(resource, Plate):
      # Extract liquid mask and volumes
      # Well state update format:
      # { "resource_name": { "liquid_mask": "hex", "volumes": [...] } }
      num_wells = resource.num_items
      liquid_bits = 0
      volumes = []

      for i in range(num_wells):
        well = resource.get_item(i)
        volume = well.tracker.get_liquids_total()
        if volume > 0:
          liquid_bits |= 1 << i
          volumes.append(volume)
        else:
          volumes.append(0)

      if liquid_bits > 0:
        state_update[res_name] = {"liquid_mask": hex(liquid_bits), "volumes": volumes}

    elif isinstance(resource, TipRack):
      # Extract tip mask
      num_tips = resource.num_items
      tip_bits = 0

      for i in range(num_tips):
        if resource.get_item(i).has_tip:
          tip_bits |= 1 << i

      state_update[res_name] = {"tip_mask": hex(tip_bits)}

  if state_update:
    postMessage(json.dumps({"type": "WELL_STATE_UPDATE", "payload": state_update}))


def patch_state_emission(lh: Any):
  """
  Patches a LiquidHandler to automatically emit state updates after
  any liquid handling operation.
  """
  if not IS_BROWSER_MODE:
    return lh

  original_methods = {}
  methods_to_patch = [
    "aspirate",
    "dispense",
    "pick_up_tips",
    "drop_tips",
    "aspirate96",
    "dispense96",
    "pick_up_tips96",
    "drop_tips96",
  ]

  for method_name in methods_to_patch:
    if hasattr(lh, method_name):
      original_methods[method_name] = getattr(lh, method_name)

      def create_patched_method(m_name, original):
        async def patched(*args, **kwargs):
          result = await original(*args, **kwargs)
          emit_well_state(lh)
          return result

        return patched

      setattr(lh, method_name, create_patched_method(method_name, original_methods[method_name]))

  # Initial emission
  emit_well_state(lh)

  return lh


if IS_BROWSER_MODE:
  from js import postMessage
else:
  # Mock for local testing
  def postMessage(msg):
    pass


import time


# =============================================================================
# Function Call Logging - Time Travel Debugging
# =============================================================================

# Global sequence counter for ordering
_function_call_sequence = 0


def patch_function_call_logging(lh: Any, run_id: str):
  """
  Patches a LiquidHandler to emit function call logs with state before/after.

  Unlike patch_state_emission() which only emits well state updates,
  this captures full serialized state for time-travel debugging.
  """
  global _function_call_sequence
  _function_call_sequence = 0  # Reset for new run

  if not IS_BROWSER_MODE:
    return lh

  methods_to_log = [
    "aspirate",
    "dispense",
    "pick_up_tips",
    "drop_tips",
    "aspirate96",
    "dispense96",
    "pick_up_tips96",
    "drop_tips96",
    "move_plate",
    "move_lid",
  ]

  original_methods = {}

  for method_name in methods_to_log:
    if hasattr(lh, method_name):
      original_methods[method_name] = getattr(lh, method_name)

      def create_logged_method(m_name, original):
        async def logged_method(*args, **kwargs):
          global _function_call_sequence

          # Capture state before
          state_before = None
          try:
            state_before = lh.deck.serialize_all_state()
          except Exception as e:
            print(f"[web_bridge] State capture failed: {e}")

          call_id = str(uuid.uuid4())
          start_time = time.time()
          error_message = None

          # Log start
          _emit_function_call_log(
            call_id=call_id,
            run_id=run_id,
            sequence=_function_call_sequence,
            method_name=m_name,
            args=_serialize_args(args, kwargs),
            state_before=state_before,
            state_after=None,
            status="running",
            start_time=start_time,
          )

          try:
            # Execute actual method
            result = await original(*args, **kwargs)
            status = "completed"
          except Exception as e:
            error_message = str(e)
            status = "failed"
            raise
          finally:
            # Capture state after
            state_after = None
            try:
              state_after = lh.deck.serialize_all_state()
            except Exception:
              pass

            end_time = time.time()
            duration_ms = (end_time - start_time) * 1000

            # Log completion
            _emit_function_call_log(
              call_id=call_id,
              run_id=run_id,
              sequence=_function_call_sequence,
              method_name=m_name,
              args=_serialize_args(args, kwargs),
              state_before=state_before,
              state_after=state_after,
              status=status,
              start_time=start_time,
              end_time=end_time,
              duration_ms=duration_ms,
              error_message=error_message,
            )

            _function_call_sequence += 1

          return result

        return logged_method

      setattr(lh, method_name, create_logged_method(method_name, original_methods[method_name]))

  return lh


def _emit_function_call_log(
  call_id: str,
  run_id: str,
  sequence: int,
  method_name: str,
  args: dict,
  state_before: dict | None,
  state_after: dict | None,
  status: str,
  start_time: float,
  end_time: float | None = None,
  duration_ms: float | None = None,
  error_message: str | None = None,
):
  """Emit a function call log message to the browser."""
  payload = {
    "call_id": call_id,
    "run_id": run_id,
    "sequence": sequence,
    "method_name": method_name,
    "args": args,
    "state_before": state_before,
    "state_after": state_after,
    "status": status,
    "start_time": start_time,
    "end_time": end_time,
    "duration_ms": duration_ms,
    "error_message": error_message,
  }
  postMessage(json.dumps({"type": "FUNCTION_CALL_LOG", "payload": payload}))


def _serialize_args(args: tuple, kwargs: dict) -> dict:
  """Serialize function arguments for logging."""
  result = {}

  # Positional args
  for i, arg in enumerate(args):
    try:
      if hasattr(arg, "name"):
        result[f"arg_{i}"] = f"<{type(arg).__name__}: {arg.name}>"
      elif hasattr(arg, "__dict__"):
        result[f"arg_{i}"] = f"<{type(arg).__name__}>"
      else:
        result[f"arg_{i}"] = repr(arg)[:100]
    except Exception:
      result[f"arg_{i}"] = "<unserializable>"

  # Keyword args
  for key, value in kwargs.items():
    try:
      if hasattr(value, "name"):
        result[key] = f"<{type(value).__name__}: {value.name}>"
      elif hasattr(value, "__dict__"):
        result[key] = f"<{type(value).__name__}>"
      else:
        result[key] = repr(value)[:100]
    except Exception:
      result[key] = "<unserializable>"

  return result


# =============================================================================
# WebBridgeIO - Generic IO Transport for Browser Mode
# =============================================================================

# Global registry for pending read requests (used by worker to route responses)
_pending_reads: dict[str, asyncio.Future] = {}

# Global registry for pending user interactions
_pending_interactions: dict[str, asyncio.Future] = {}

# BroadcastChannel for Playground mode (registered by bootstrap code)
_broadcast_channel = None


def register_broadcast_channel(channel):
  """Register the BroadcastChannel for user interaction messages.

  Called by the bootstrap code after creating the channel.
  """
  global _broadcast_channel
  _broadcast_channel = channel


class WebBridgeIO:
  """A PLR-compatible IO transport that routes raw bytes through the WebWorker
  message interface to Angular's WebSerialService.

  This class implements the same interface as pylabrobot.io.serial.Serial and
  pylabrobot.io.usb.USB, allowing it to be used as a drop-in replacement for
  the `self.io` attribute on any PLR machine backend.

  Example:
      backend = STAR()
      backend.io = WebBridgeIO(port_id='serial-port-1')
      await backend.setup()  # Now uses WebSerial!

  """

  def __init__(
    self,
    port_id: str,
    baudrate: int = 9600,
    read_timeout: float = 30.0,
    write_timeout: float = 30.0,
  ):
    """Initialize WebBridgeIO.

    Args:
        port_id: Identifier for the WebSerial port (from hardware discovery)
        baudrate: Baud rate for serial communication
        read_timeout: Default timeout for read operations (seconds)
        write_timeout: Default timeout for write operations (seconds)

    """
    self.port_id = port_id
    self.baudrate = baudrate
    self.read_timeout = read_timeout
    self.write_timeout = write_timeout
    self._is_open = False

  async def setup(self) -> None:
    """Initialize the connection. Opens the WebSerial port."""
    await self._send_io_command("OPEN", {"baudRate": self.baudrate})
    self._is_open = True

  async def stop(self) -> None:
    """Close the connection."""
    if self._is_open:
      await self._send_io_command("CLOSE", {})
      self._is_open = False

  async def write(self, data: bytes, timeout: float | None = None) -> int:
    """Write raw bytes to the device via WebSerial.

    Args:
        data: Bytes to write
        timeout: Write timeout in seconds (unused, for interface compatibility)

    Returns:
        Number of bytes written

    """
    await self._send_io_command(
      "WRITE",
      {
        "data": list(data)  # Convert bytes to list for JSON serialization
      },
    )
    return len(data)

  async def read(self, num_bytes: int = 1, timeout: float | None = None) -> bytes:
    """Read bytes from the device. Waits for data from WebSerial via JS bridge.

    Args:
        num_bytes: Number of bytes to read
        timeout: Read timeout in seconds

    Returns:
        Bytes read from device

    Raises:
        TimeoutError: If read times out

    """
    if timeout is None:
      timeout = self.read_timeout

    request_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _pending_reads[request_id] = future

    await self._send_io_command(
      "READ", {"size": num_bytes, "timeout": timeout, "request_id": request_id}
    )

    try:
      result = await asyncio.wait_for(future, timeout=timeout + 1)
      return bytes(result)
    except asyncio.TimeoutError:
      msg = f"Read timeout after {timeout}s on port {self.port_id}"
      raise TimeoutError(msg)
    finally:
      _pending_reads.pop(request_id, None)

  async def readline(self) -> bytes:
    """Read a line from the device (until newline character).

    Returns:
        Bytes including the newline character

    """
    request_id = str(uuid.uuid4())
    loop = asyncio.get_event_loop()
    future = loop.create_future()
    _pending_reads[request_id] = future

    await self._send_io_command(
      "READLINE", {"timeout": self.read_timeout, "request_id": request_id}
    )

    try:
      result = await asyncio.wait_for(future, timeout=self.read_timeout + 1)
      return bytes(result)
    except asyncio.TimeoutError:
      msg = f"Readline timeout on port {self.port_id}"
      raise TimeoutError(msg)
    finally:
      _pending_reads.pop(request_id, None)

  async def _send_io_command(self, command: str, data: dict) -> None:
    """Send an IO command to the JavaScript layer."""
    message = {"type": "RAW_IO", "payload": {"command": command, "port_id": self.port_id, **data}}
    postMessage(json.dumps(message))

  def serialize(self) -> dict:
    """Serialize the IO configuration."""
    return {
      "type": "WebBridgeIO",
      "port_id": self.port_id,
      "baudrate": self.baudrate,
      "read_timeout": self.read_timeout,
      "write_timeout": self.write_timeout,
    }


def handle_io_response(request_id: str, data: list) -> None:
  """Called by the worker when JS sends data back from WebSerial.

  This function is invoked from python.worker.ts when a RAW_IO_RESPONSE
  message is received from the Angular main thread.

  Args:
      request_id: The request ID that was sent with the READ command
      data: List of byte values received from the device

  """
  future = _pending_reads.get(request_id)
  if future and not future.done():
    future.set_result(data)
  elif request_id not in _pending_reads:
    pass


async def request_user_interaction(interaction_type: str, payload: dict) -> Any:
  """Requests user interaction from the browser (pause, confirm, input)."""
  if not IS_BROWSER_MODE:
    print(f"[web_bridge] Mock interaction: {interaction_type} {payload}")
    return None

  request_id = str(uuid.uuid4())
  loop = asyncio.get_event_loop()
  future = loop.create_future()
  _pending_interactions[request_id] = future

  message_dict = {
    "type": "USER_INTERACTION",
    "payload": {"id": request_id, "interaction_type": interaction_type, "payload": payload},
  }

  # Try using registered BroadcastChannel if available (Playground mode)
  if _broadcast_channel is not None:
    try:
      import js
      from pyodide.ffi import to_js

      js_msg = to_js(message_dict, dict_converter=js.Object.fromEntries)
      _broadcast_channel.postMessage(js_msg)
    except Exception:
      postMessage(json.dumps(message_dict))
  else:
    postMessage(json.dumps(message_dict))

  try:
    # Interactions can take a long time (user waiting), so we don't set a short timeout here.
    # The frontend is responsible for providing a way to cancel if needed.
    return await future
  finally:
    _pending_interactions.pop(request_id, None)


def handle_interaction_response(request_id: str, value: Any) -> None:
  """Called by the worker when JS sends back the user's interaction response."""
  future = _pending_interactions.get(request_id)
  if future and not future.done():
    future.set_result(value)


# =============================================================================
# Machine Patcher - Patch any PLR machine for browser mode
# =============================================================================


def patch_io_for_browser(machine: Any, port_id: str, baudrate: int = 9600) -> Any:
  """Patch a PLR machine's transport layer to use WebBridgeIO.

  This function replaces the `self.io` attribute on a machine's backend
  with a WebBridgeIO instance, allowing the machine to communicate with
  hardware connected to the browser via WebSerial.

  Args:
      machine: Any PLR Machine instance (LiquidHandler, HeaterShaker, etc.)
      port_id: The WebSerial port identifier from hardware discovery
      baudrate: Baud rate for serial communication (default: 9600)

  Returns:
      The patched machine instance

  Example:
      lh = LiquidHandler(backend=STAR())
      patch_io_for_browser(lh, 'serial-port-1')
      await lh.setup()  # Now uses WebSerial!

  """
  if not IS_BROWSER_MODE:
    return machine

  backend = getattr(machine, "backend", None)
  if backend is None:
    return machine

  web_io = WebBridgeIO(port_id=port_id, baudrate=baudrate)

  # Try known IO attribute names
  io_attrs = ["io", "_io", "connection", "_connection", "ser", "_ser"]
  patched = False
  for attr in io_attrs:
    if hasattr(backend, attr):
      setattr(backend, attr, web_io)
      patched = True
      break

  if not patched:
    pass

  return machine


def create_browser_backend():
  """Returns an instance of WebBridgeBackend for browser-based simulation/execution."""
  return WebBridgeBackend()


def create_browser_deck():
  """Returns a default Deck for browser-based execution."""
  try:
    from pylabrobot.resources import Deck

    return Deck()
  except ImportError:
    return None


def create_browser_machine(
  machine_class, backend_class, port_id: str, baudrate: int = 9600, **kwargs
):
  """Factory function to create a PLR machine pre-configured for browser mode.

  Args:
      machine_class: The machine class (e.g., LiquidHandler)
      backend_class: The backend class (e.g., STAR)
      port_id: WebSerial port identifier
      baudrate: Baud rate for serial communication
      **kwargs: Additional arguments passed to backend constructor

  Returns:
      A machine instance with WebBridgeIO patched

  Example:
      lh = create_browser_machine(LiquidHandler, STAR, 'serial-port-1')
      await lh.setup()

  """
  backend = backend_class(**kwargs)
  machine = machine_class(backend=backend)
  return patch_io_for_browser(machine, port_id, baudrate)


def create_configured_backend(config):
  """
  Creates a PLR backend instance based on configuration.
  Supports dynamic loading of backends and patching them for WebBridgeIO.

  Args:
      config: Dictionary with keys:
          - backend_fqn: Fully qualified name of the backend class
          - port_id: WebSerial port ID (optional)
          - baudrate: Baud rate for serial (default: 9600)
          - is_simulated: Whether to use simulation (default: False)

  Returns:
      A PLR backend instance
  """
  if config is None:
    return WebBridgeBackend()

  # config might be a JsProxy if coming directly from JS, so we convert if needed
  if hasattr(config, "to_py"):
    config = config.to_py()

  if config is None: # In case to_py() returned None
    return WebBridgeBackend()

  if not isinstance(config, dict):
    # If it's not a dict, it might be a JsProxy that didn't convert well, or just some other value
    # Try to treat it as a dict if it has a .get method, otherwise fallback
    if not hasattr(config, "get"):
      return WebBridgeBackend()

  fqn = config.get("backend_fqn", "pylabrobot.liquid_handling.backends.LiquidHandlerBackend")

  # Dynamic Import
  try:
    module_path, class_name = fqn.rsplit(".", 1)
    module = __import__(module_path, fromlist=[class_name])
    BackendClass = getattr(module, class_name)
  except (ImportError, ValueError, AttributeError) as e:
    print(f"Error importing backend {fqn}: {e}")
    # Fallback to simulation
    return WebBridgeBackend()

  # Instantiate
  # Note: Some backends might take args. For now assume default constructor.
  try:
    backend = BackendClass()
  except Exception as e:
    print(f"Error instantiating backend {fqn}: {e}")
    # Fallback to default constructor attempt or WebBridgeBackend
    try:
      backend = BackendClass()
    except Exception:
      return WebBridgeBackend()

  # Patch IO if needed
  if not config.get("is_simulated", False):
    port_id = config.get("port_id")
    baudrate = config.get("baudrate", 9600)
    if port_id:
      # Create a WebBridgeIO
      web_io = WebBridgeIO(port_id=port_id, baudrate=baudrate)

      # Inject it - try known IO attribute names
      io_attrs = ["io", "_io", "connection", "_connection", "ser", "_ser"]
      for attr in io_attrs:
        if hasattr(backend, attr):
          setattr(backend, attr, web_io)
          break

  return backend


# =============================================================================
# Legacy WebBridgeBackend (kept for compatibility)
# =============================================================================

# Try to import LiquidHandlerBackend - may not be available in browser mode
try:
  from pylabrobot.liquid_handling.backends import LiquidHandlerBackend

  _HAS_PLR = True
except ImportError:
  _HAS_PLR = False
  LiquidHandlerBackend = object  # Fallback base class


class WebBridgeBackend(LiquidHandlerBackend if _HAS_PLR else object):
  """A PyLabRobot backend that routes commands to the browser's main thread via WebWorker messages.
  This allows the Python code running in WASM to control hardware connected to the browser (WebSerial).
  """

  def __init__(self, num_channels: int = 8):
    super().__init__()
    self._num_channels = num_channels

  async def setup(self):
    self.send_command("setup", {})

  async def stop(self):
    self.send_command("stop", {})

  def send_command(self, command: str, data: dict):
    """Sends a command to the JavaScript main thread."""
    message = {"type": "PLR_COMMAND", "payload": {"command": command, "data": data}}
    # In Pyodide worker, postMessage is available globally or via js module
    # We use a synchronous conversion to dict/json for safety across the boundary
    postMessage(json.dumps(message))

  # -------------------------------------------------------------------------
  # LiquidHandlerBackend Implementation
  # -------------------------------------------------------------------------

  async def assigned_resource_callback(self, resource):
    self.send_command(
      "resource_assigned",
      {"resource_name": resource.name, "resource_type": resource.__class__.__name__},
    )

  async def pick_up_tips(self, ops):
    self.send_command("pick_up_tips", {"ops": [op.serialize() for op in ops]})

  async def drop_tips(self, ops):
    self.send_command("drop_tips", {"ops": [op.serialize() for op in ops]})

  async def aspirate(self, ops):
    self.send_command("aspirate", {"ops": [op.serialize() for op in ops]})

  async def dispense(self, ops):
    self.send_command("dispense", {"ops": [op.serialize() for op in ops]})

  async def pick_up_tips96(self, pickup):
    self.send_command("pick_up_tips96", {"resource_name": pickup.resource.name})

  async def drop_tips96(self, drop):
    self.send_command("drop_tips96", {"resource_name": drop.resource.name})

  async def aspirate96(self, aspiration):
    self.send_command("aspirate96", {"volume": aspiration.volume})

  async def dispense96(self, dispense):
    self.send_command("dispense96", {"volume": dispense.volume})

  @property
  def num_channels(self) -> int:
    return self._num_channels


import io
import sys

from js import postMessage


class StdoutRedirector(io.TextIOBase):
  def __init__(self, stream_type="STDOUT"):
    self.stream_type = stream_type

  def write(self, s):
    if s:
      if js and hasattr(js, "handlePythonOutput"):
        js.handlePythonOutput(self.stream_type, s)
      else:
        # Fallback for environments without the handler (e.g. raw Pyodide without our worker)
        js.postMessage(json.dumps({"type": self.stream_type, "payload": s}))
    return len(s)


def bootstrap_playground(namespace=None):
  """Sets up the environment for the web playground:
  1. Redirects stdout/stderr to the browser.
  2. Imports common PyLabRobot classes.

  Args:
      namespace: Optional dictionary to inject variables into (e.g. console.globals).
                 If None, temporarily injects into __main__ (legacy behavior).

  """
  sys.stdout = StdoutRedirector("STDOUT")
  sys.stderr = StdoutRedirector("STDERR")
  
  target = namespace if namespace is not None else {}

  try:
    import pylabrobot.liquid_handling
    import pylabrobot.liquid_handling.backends
    import pylabrobot.resources

    # Core classes
    target["LiquidHandler"] = pylabrobot.liquid_handling.LiquidHandler

    # Resources
    target["Plate"] = pylabrobot.resources.Plate
    target["TipRack"] = pylabrobot.resources.TipRack
    target["Resource"] = pylabrobot.resources.Resource
    target["Container"] = pylabrobot.resources.Container
    target["Deck"] = pylabrobot.resources.Deck

    # Backends
    target["LiquidHandlerBackend"] = pylabrobot.liquid_handling.backends.LiquidHandlerBackend
    # Import specific backends if available
    for name, cls in pylabrobot.liquid_handling.backends.__dict__.items():
      if isinstance(cls, type) and name.endswith("Backend"):
        target[name] = cls

    # Standard PLR Layouts/Machines if available
    try:
      from pylabrobot.liquid_handling.backends.hamilton import STAR

      target["STAR"] = STAR
    except ImportError:
      pass

    # If using __main__ fallback
    if namespace is None:
      import __main__

      for k, v in target.items():
        setattr(__main__, k, v)

  except ImportError:
    pass

  # Inject WebSerial & WebUSB from shims if available
  try:
    # Ensure importability from root/current dir
    if "." not in sys.path:
      sys.path.append(".")
    if "/" not in sys.path:
      sys.path.append("/")

    print(f"DEBUG: CWD={os.getcwd()}", file=sys.stderr)

    # 1. Inject WebSerial
    try:
      from web_serial_shim import WebSerial

      if namespace is not None:
        namespace["WebSerial"] = WebSerial
      builtins.WebSerial = WebSerial
      print("SUCCESS: WebSerial injected into builtins", file=sys.stderr)
    except ImportError:
      print("WARNING: web_serial_shim not found", file=sys.stderr)

    # 2. Inject WebUSB
    try:
      from web_usb_shim import WebUSB

      if namespace is not None:
        namespace["WebUSB"] = WebUSB
      builtins.WebUSB = WebUSB
      print("SUCCESS: WebUSB injected into builtins", file=sys.stderr)
    except ImportError:
      print("WARNING: web_usb_shim not found", file=sys.stderr)

  except Exception as e:
    import traceback

    print(f"ERROR: Failed during shim injection: {e}", file=sys.stderr)
    traceback.print_exc(file=sys.stderr)


# =============================================================================
# Signature Help (still uses Jedi if available)
# =============================================================================

_jedi_available = False
_jedi_install_attempted = False


def _ensure_jedi():
  """Ensure Jedi is installed and available.
  Returns True if Jedi is ready, False otherwise.
  """
  global _jedi_available, _jedi_install_attempted

  if _jedi_available:
    return True

  if _jedi_install_attempted:
    return False

  _jedi_install_attempted = True

  try:
    import jedi

    _jedi_available = True
    return True
  except ImportError:
    # Try to install jedi via micropip
    if IS_BROWSER_MODE:
      try:
        import asyncio

        import micropip

        async def install_jedi():
          await micropip.install("jedi")

        # Run in event loop
        loop = asyncio.get_event_loop()
        loop.run_until_complete(install_jedi())

        _jedi_available = True
        return True
      except Exception:
        # Jedi is optional for signature help
        return False
    else:
      return False


def get_signatures(source: str, line: int = 1, column: int | None = None) -> list:
  """Get function signatures for the code at cursor position.
  Used for showing parameter hints when typing function calls.

  Args:
      source: Full source code up to cursor
      line: Line number (1-indexed)
      column: Column position (0-indexed)

  Returns:
      List of signature dicts with name, params, docstring

  """
  if not _ensure_jedi():
    return []

  try:
    import jedi

    import __main__

    if column is None:
      lines = source.split("\n")
      column = len(lines[-1]) if lines else 0

    script = jedi.Interpreter(source, namespaces=[__main__.__dict__])

    signatures = script.get_signatures(line, column)

    return [
      {
        "name": sig.name,
        "params": [p.description for p in sig.params],
        "index": sig.index,  # Current parameter index
        "docstring": sig.docstring(fast=True),
      }
      for sig in signatures
    ]
  except Exception:
    return []
