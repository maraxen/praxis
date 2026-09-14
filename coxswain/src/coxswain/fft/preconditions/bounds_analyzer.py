# --- PORT PROVENANCE ---------------------------------------------------------
# Copied from praxis/backend/core/simulation/bounds_analyzer.py (W0 recon record
# 260824_w0_simulation_reuse_verdict, verdict=partially_reusable; N4-C port
# choice). Entire module lifted per the W0 reusable_subset.
#
# ADAPTATION (the only change vs the source): the source's TYPE_CHECKING-only
# import of praxis.backend.utils.plr_static_analysis.models
# (OperationNode / ProtocolComputationGraph) is replaced by the local structural
# Protocols ``OperationNodeLike`` and ``ComputationGraphLike`` below. NFR-2 bans
# praxis.* imports anywhere under coxswain/src (AC-2 greps every Import node,
# including TYPE_CHECKING-guarded ones), and with `from __future__ import
# annotations` the swapped-in names are string annotations only -- runtime
# behavior of every function in this module is unchanged.
# -----------------------------------------------------------------------------
"""Loop bounds analyzer for protocol simulation.

This module analyzes loop iteration counts using resource dimensions
(items_x, items_y) to enable more precise simulation of loop-based protocols.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

class OperationNodeLike(Protocol):
  """Structural stand-in for plr_static_analysis.models.OperationNode.

  Carries exactly the attributes this module reads."""

  method_name: str
  arguments: dict[str, str]
  foreach_source: str | None

class ComputationGraphLike(Protocol):
  """Structural stand-in for plr_static_analysis.models.ProtocolComputationGraph."""

  resources: dict[str, Any]  # values expose .declared_type: str
  operations: list[OperationNodeLike]


@dataclass
class LoopBounds:
  """Computed bounds for a loop."""

  source_expression: str
  """Expression being iterated (e.g., 'plate.wells()')"""

  exact_count: int | None = None
  """Exact iteration count if known"""

  min_count: int = 1
  """Minimum possible iterations"""

  max_count: int | None = None
  """Maximum possible iterations (None = unbounded)"""

  is_bounded: bool = True
  """Whether we could determine bounds"""

  inferred_from: str | None = None
  """How bounds were inferred"""


@dataclass
class ItemizedResourceSpec:
  """Specification for an itemized resource (plate, tip rack, etc.)."""

  resource_name: str
  """Name of the resource"""

  resource_type: str
  """Type (Plate, TipRack, etc.)"""

  items_x: int = 12
  """Number of items in X dimension (columns)"""

  items_y: int = 8
  """Number of items in Y dimension (rows)"""

  @property
  def total_items(self) -> int:
    """Total number of items."""
    return self.items_x * self.items_y


# Default dimensions for common resource types
DEFAULT_DIMENSIONS: dict[str, tuple[int, int]] = {
  "Plate": (12, 8),  # 96-well standard
  "TipRack": (12, 8),  # 96-tip standard
  "Trough": (12, 1),  # 12-channel trough
  "Plate384": (24, 16),  # 384-well
  "TipRack384": (24, 16),  # 384-tip
  "Plate24": (6, 4),  # 24-well
  "Plate12": (4, 3),  # 12-well
  "Plate6": (3, 2),  # 6-well
}


class BoundsAnalyzer:
  """Analyzes loop bounds using resource dimensions.

  This analyzer uses knowledge of resource dimensions (items_x × items_y)
  to compute exact loop iteration counts for common patterns like:
  - `for well in plate.wells()`
  - `for tip in tips.tips()`
  - `for row in plate.rows()`

  Usage:
      analyzer = BoundsAnalyzer()
      bounds = analyzer.analyze_loop(
          loop_source="plate.wells()",
          resource_specs={"plate": ItemizedResourceSpec("plate", "Plate")},
      )
      print(f"Loop iterates {bounds.exact_count} times")

  """

  def __init__(
    self,
    resource_specs: dict[str, ItemizedResourceSpec] | None = None,
  ) -> None:
    """Initialize the analyzer.

    Args:
        resource_specs: Known resource specifications.

    """
    self._resource_specs = resource_specs or {}

  def add_resource_spec(self, spec: ItemizedResourceSpec) -> None:
    """Add a resource specification."""
    self._resource_specs[spec.resource_name] = spec

  def infer_spec_from_type(self, resource_name: str, resource_type: str) -> ItemizedResourceSpec:
    """Infer resource spec from type using defaults."""
    dims = DEFAULT_DIMENSIONS.get(resource_type, (12, 8))
    return ItemizedResourceSpec(
      resource_name=resource_name,
      resource_type=resource_type,
      items_x=dims[0],
      items_y=dims[1],
    )

  def analyze_loop(
    self,
    loop_source: str,
  ) -> LoopBounds:
    """Analyze loop bounds from a source expression.

    Args:
        loop_source: The collection being iterated (e.g., 'plate.wells()').

    Returns:
        LoopBounds with iteration count information.

    """
    # Parse the source expression
    # Common patterns:
    # - plate.wells() -> all wells
    # - plate.rows() -> rows (items_y iterations, each row has items_x)
    # - plate.columns() -> columns (items_x iterations)
    # - plate["A1:A12"] -> slice of wells
    # - tips.tips() -> all tip spots

    # Extract resource name from expression
    resource_name = self._extract_resource_name(loop_source)

    if not resource_name:
      return LoopBounds(
        source_expression=loop_source,
        is_bounded=False,
        inferred_from="could not parse expression",
      )

    # Get or infer resource spec
    spec = self._resource_specs.get(resource_name)

    if not spec:
      # Try to infer from the expression
      if ".wells()" in loop_source or ".tips()" in loop_source:
        # Assume standard 96-well/tip
        return LoopBounds(
          source_expression=loop_source,
          exact_count=96,
          min_count=96,
          max_count=96,
          is_bounded=True,
          inferred_from="default 96-item assumption",
        )
      return LoopBounds(
        source_expression=loop_source,
        is_bounded=False,
        inferred_from="resource spec not found",
      )

    # Determine iteration count based on method
    if ".wells()" in loop_source or ".tips()" in loop_source:
      count = spec.total_items
      return LoopBounds(
        source_expression=loop_source,
        exact_count=count,
        min_count=count,
        max_count=count,
        is_bounded=True,
        inferred_from=f"{spec.resource_type}({spec.items_x}x{spec.items_y})",
      )

    if ".rows()" in loop_source:
      count = spec.items_y
      return LoopBounds(
        source_expression=loop_source,
        exact_count=count,
        min_count=count,
        max_count=count,
        is_bounded=True,
        inferred_from=f"{spec.resource_type} has {spec.items_y} rows",
      )

    if ".columns()" in loop_source:
      count = spec.items_x
      return LoopBounds(
        source_expression=loop_source,
        exact_count=count,
        min_count=count,
        max_count=count,
        is_bounded=True,
        inferred_from=f"{spec.resource_type} has {spec.items_x} columns",
      )

    # Check for slice notation like plate["A1:A12"]
    slice_count = self._parse_slice_count(loop_source)
    if slice_count:
      return LoopBounds(
        source_expression=loop_source,
        exact_count=slice_count,
        min_count=slice_count,
        max_count=slice_count,
        is_bounded=True,
        inferred_from="slice notation",
      )

    # Unknown pattern
    return LoopBounds(
      source_expression=loop_source,
      is_bounded=False,
      inferred_from="unknown iteration pattern",
    )

  def analyze_graph_loops(
    self,
    graph: ComputationGraphLike,
  ) -> dict[str, LoopBounds]:
    """Analyze all loops in a computation graph.

    Args:
        graph: The computation graph to analyze.

    Returns:
        Mapping of loop source -> LoopBounds.

    """
    # First, build resource specs from graph
    for name, resource in graph.resources.items():
      if name not in self._resource_specs:
        spec = self.infer_spec_from_type(name, resource.declared_type)
        self._resource_specs[name] = spec

    # Find all foreach operations
    bounds_map: dict[str, LoopBounds] = {}

    for op in graph.operations:
      if op.foreach_source and op.foreach_source not in bounds_map:
        bounds = self.analyze_loop(op.foreach_source)
        bounds_map[op.foreach_source] = bounds

    return bounds_map

  def _extract_resource_name(self, expression: str) -> str | None:
    """Extract the resource name from an expression.

    Examples:
        'plate.wells()' -> 'plate'
        'tips.tips()' -> 'tips'
        'source["A1:A12"]' -> 'source'

    """
    # Handle method calls: plate.wells()
    if "." in expression:
      return expression.split(".")[0].strip()

    # Handle subscript: plate["A1:A12"]
    if "[" in expression:
      return expression.split("[")[0].strip()

    return None

  def _parse_slice_count(self, expression: str) -> int | None:
    """Parse slice notation to determine item count.

    Examples:
        'plate["A1:A12"]' -> 12 (A1 through A12)
        'plate["A1:H1"]' -> 8 (column 1)

    """
    import re

    # Match patterns like ["A1:A12"] or ['A1:H12']
    match = re.search(r'\[[\"\']([A-H])(\d+):([A-H])(\d+)[\"\']\]', expression)
    if not match:
      return None

    start_row, start_col, end_row, end_col = match.groups()

    # Convert to numbers
    start_row_num = ord(start_row) - ord("A") + 1
    end_row_num = ord(end_row) - ord("A") + 1
    start_col_num = int(start_col)
    end_col_num = int(end_col)

    # Same row = column slice
    if start_row == end_row:
      return abs(end_col_num - start_col_num) + 1

    # Same column = row slice
    if start_col_num == end_col_num:
      return abs(end_row_num - start_row_num) + 1

    # Rectangle
    rows = abs(end_row_num - start_row_num) + 1
    cols = abs(end_col_num - start_col_num) + 1
    return rows * cols


def compute_aggregate_effect(
  operation: OperationNodeLike,
  bounds: LoopBounds,
) -> dict[str, Any]:
  """Compute the aggregate effect of a loop operation.

  For operations inside loops, compute the total effect across
  all iterations.

  Args:
      operation: The operation inside the loop.
      bounds: The computed loop bounds.

  Returns:
      Dictionary describing aggregate effects.

  """
  if not bounds.exact_count:
    return {
      "is_bounded": False,
      "message": "Cannot compute aggregate - unknown iteration count",
    }

  effects: dict[str, Any] = {
    "is_bounded": True,
    "iteration_count": bounds.exact_count,
    "operation": operation.method_name,
  }

  # Compute aggregate based on operation type
  if operation.method_name in {"aspirate", "dispense"}:
    # Volume operations accumulate
    vol_arg = operation.arguments.get("vol") or operation.arguments.get("volume")
    if vol_arg:
      try:
        vol = float(vol_arg.strip("'\""))
        effects["total_volume"] = vol * bounds.exact_count
        effects["per_iteration_volume"] = vol
      except ValueError:
        effects["volume"] = f"{vol_arg} × {bounds.exact_count}"

  elif operation.method_name == "transfer":
    effects["total_transfers"] = bounds.exact_count

  return effects
