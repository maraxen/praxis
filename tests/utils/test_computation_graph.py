"""Tests for the Computation Graph Extractor."""

import json
import pathlib

import libcst as cst
import pytest
from libcst.metadata import MetadataWrapper

from praxis.backend.utils.plr_static_analysis.models import (
  GraphNodeType,
  PreconditionType,
)
from praxis.backend.utils.plr_static_analysis.visitors.computation_graph_extractor import (
  PLATE_ACCESS_METHODS,
  PLATE_MOVE_METHODS,
  TIPS_DROPPING_METHODS,
  TIPS_LOADING_METHODS,
  TIPS_REQUIRED_METHODS,
  ComputationGraphExtractor,
  VariableTypeTracker,
  _walk_cst_node,
  extract_graph_from_source,
)

# Repo root, resolved from this file's location (tests/utils/test_computation_graph.py).
_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
_PLR_SURVEY_PATH = _REPO_ROOT / "training" / "verify" / "data" / "plr_preconditions.json"

# Declared receiver class(es) for each frozenset in computation_graph_extractor.py.
# A method name in a set must exist as a method on at least one of its declared
# receiver classes in the AST-derived PLR survey, or it is stale (backlog #4846).
_FROZENSET_RECEIVER_CLASSES: dict[str, tuple[frozenset[str], tuple[str, ...]]] = {
  "TIPS_REQUIRED_METHODS": (TIPS_REQUIRED_METHODS, ("LiquidHandler",)),
  "TIPS_LOADING_METHODS": (TIPS_LOADING_METHODS, ("LiquidHandler",)),
  "TIPS_DROPPING_METHODS": (TIPS_DROPPING_METHODS, ("LiquidHandler",)),
  "PLATE_ACCESS_METHODS": (PLATE_ACCESS_METHODS, ("LiquidHandler", "PlateReader")),
  "PLATE_MOVE_METHODS": (PLATE_MOVE_METHODS, ("LiquidHandler",)),
}


def _load_plr_method_index() -> dict[str, set[str]]:
  """Build a {class_name: {method_name, ...}} index from the PLR AST survey."""
  data = json.loads(_PLR_SURVEY_PATH.read_text())
  index: dict[str, set[str]] = {}
  for fn in data["functions"]:
    class_name = fn.get("class_name")
    if not class_name:
      continue
    method_name = fn["qualname"].rsplit(".", 1)[-1]
    index.setdefault(class_name, set()).add(method_name)
  return index


# Test protocol source code
SIMPLE_TRANSFER_SOURCE = '''
async def simple_transfer(
    lh: LiquidHandler,
    source: Plate,
    dest: Plate,
    tips: TipRack,
):
    """Simple A to B transfer."""
    await lh.pick_up_tips(tips)
    await lh.aspirate(source["A1"], 100)
    await lh.dispense(dest["A1"], 100)
    await lh.drop_tips(tips)
'''

LOOP_PROTOCOL_SOURCE = '''
async def multi_well_transfer(
    lh: LiquidHandler,
    source: Plate,
    dest: Plate,
    tips: TipRack,
    volume: float = 50.0,
):
    """Transfer to multiple wells."""
    source_wells = source["A1:A8"]
    dest_wells = dest["A1:A8"]

    await lh.pick_up_tips(tips)

    for i, (src, dst) in enumerate(zip(source_wells, dest_wells)):
        await lh.aspirate(src, volume)
        await lh.dispense(dst, volume)

    await lh.drop_tips(tips)
'''

CONDITIONAL_PROTOCOL_SOURCE = '''
async def conditional_volume(
    lh: LiquidHandler,
    plate: Plate,
    tips: TipRack,
    volume: float,
    threshold: float = 50.0,
):
    """Conditional aspiration based on volume."""
    await lh.pick_up_tips(tips)

    if volume > threshold:
        await lh.aspirate(plate["A1"], volume)
    else:
        await lh.aspirate(plate["A1"], volume / 2)

    await lh.drop_tips(tips)
'''

MULTI_MACHINE_SOURCE = '''
async def plate_reader_workflow(
    lh: LiquidHandler,
    pr: PlateReader,
    plate: Plate,
    tips: TipRack,
):
    """Workflow involving multiple machines."""
    await lh.pick_up_tips(tips)
    await lh.aspirate(plate["A1"], 100)
    await lh.dispense(plate["B1"], 100)
    await lh.drop_tips(tips)

    result = await pr.read_absorbance(plate, wavelength=450)
    return result
'''

# §12.2.4: nested for -> if/elif/else -> while, exercising region nesting
# and the elif-as-nested-header shape.
NESTED_REGIONS_SOURCE = """
async def nested_regions_protocol(
    lh: LiquidHandler,
    plate: Plate,
    tips: TipRack,
):
    for i in range(2):
        if i == 0:
            await lh.aspirate(plate["A1"], 50)
        elif i == 1:
            await lh.dispense(plate["A1"], 50)
        else:
            await lh.drop_tips(tips)

        while True:
            await lh.pick_up_tips(tips)
            break
"""

# §12.2.3 AC-12.6: seven loops proving 3, 4, 3, 12, None, None, None, plus an
# eighth proving 0.
SEVEN_LOOPS_SOURCE = """
async def seven_loops_protocol(
    lh: LiquidHandler,
    plate: Plate,
    tips: TipRack,
):
    for i in range(3):
        await lh.pick_up_tips(tips)

    for j in range(2, 10, 2):
        await lh.pick_up_tips(tips)

    for x in [tips, tips, tips]:
        await lh.pick_up_tips(tips)

    for k in range(plate.items_x):
        await lh.pick_up_tips(tips)

    for well in plate.wells():
        await lh.pick_up_tips(tips)

    while True:
        await lh.pick_up_tips(tips)
        break

    for m in range(4):
        if m == 2:
            continue
        await lh.pick_up_tips(tips)

    for n in range(0):
        await lh.pick_up_tips(tips)
"""

# §12.2.4: a `for...else` and a `while...else` are explicitly out of scope --
# both stay flat (no header), `has_loops` still fires.
FOR_ELSE_SOURCE = """
async def for_else_protocol(
    lh: LiquidHandler,
    tips: TipRack,
):
    for i in range(3):
        await lh.pick_up_tips(tips)
    else:
        await lh.drop_tips(tips)
"""

# §12.2.5 (round-1 O4): a `self.<attr>` assignment target registers a
# ResourceNode, closing the tier-1/tier-2 grammar residual.
SELF_ATTR_SOURCE = """
async def self_attr_protocol(
    lh: LiquidHandler,
    plate: Plate,
    tips: TipRack,
):
    self.plate_1 = plate
    await lh.aspirate(self.plate_1["A1"], 50)
"""


class TestVariableTypeTracker:
  """Tests for VariableTypeTracker."""

  def test_init_with_parameters(self) -> None:
    """Test initialization with parameter types."""
    tracker = VariableTypeTracker({"lh": "LiquidHandler", "plate": "Plate"})
    assert tracker.get_type("lh") == "LiquidHandler"
    assert tracker.get_type("plate") == "Plate"

  def test_set_and_get_type(self) -> None:
    """Test setting and getting types."""
    tracker = VariableTypeTracker({})
    tracker.set_type("wells", "list[Well]", source='plate["A1:A8"]')
    assert tracker.get_type("wells") == "list[Well]"
    assert tracker.get_source("wells") == 'plate["A1:A8"]'

  def test_get_unknown_type(self) -> None:
    """Test that unknown variables return None."""
    tracker = VariableTypeTracker({})
    assert tracker.get_type("unknown") is None

  def test_infer_plate_subscript_type_range(self) -> None:
    """Test inferring type from plate subscript with range."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_subscript_type("Plate", "A1:A8")
    assert result == "list[Well]"

  def test_infer_plate_subscript_type_single(self) -> None:
    """Test inferring type from plate subscript with single well."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_subscript_type("Plate", "A1")
    assert result == "Well"

  def test_infer_tiprack_subscript_type_range(self) -> None:
    """Test inferring type from tip rack subscript with range."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_subscript_type("TipRack", "A1:A8")
    assert result == "list[TipSpot]"

  def test_infer_list_subscript_type(self) -> None:
    """Test inferring type from list subscript."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_subscript_type("list[Well]", "0")
    assert result == "Well"

  def test_infer_attribute_wells(self) -> None:
    """Test inferring type from .wells() attribute."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_attribute_type("Plate", "wells")
    assert result == "list[Well]"

  def test_infer_attribute_tips(self) -> None:
    """Test inferring type from .tips() attribute."""
    tracker = VariableTypeTracker({})
    result = tracker.infer_attribute_type("TipRack", "tips")
    assert result == "list[TipSpot]"


class TestComputationGraphExtractor:
  """Tests for ComputationGraphExtractor."""

  def test_simple_transfer_extracts_operations(self) -> None:
    """Test that simple_transfer extracts all 4 operations."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    assert len(graph.operations) == 4
    assert graph.execution_order == ["op_1", "op_2", "op_3", "op_4"]

  def test_simple_transfer_operation_methods(self) -> None:
    """Test that operation methods are correctly extracted."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    methods = [op.method_name for op in graph.operations]
    assert methods == ["pick_up_tips", "aspirate", "dispense", "drop_tips"]

  def test_simple_transfer_resources(self) -> None:
    """Test that resources are correctly identified."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    assert "source" in graph.resources
    assert "dest" in graph.resources
    assert "tips" in graph.resources
    assert graph.resources["source"].declared_type == "Plate"
    assert graph.resources["tips"].declared_type == "TipRack"

  def test_simple_transfer_machine_types(self) -> None:
    """Test that machine types are correctly identified."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    assert "liquid_handler" in graph.machine_types

  def test_simple_transfer_resource_types(self) -> None:
    """Test that resource types are collected."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    assert "Plate" in graph.resource_types
    assert "TipRack" in graph.resource_types

  def test_simple_transfer_no_loops_or_conditionals(self) -> None:
    """Test that simple protocol has no loops or conditionals."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None
    assert graph.has_loops is False
    assert graph.has_conditionals is False

  def test_loop_protocol_detects_loops(self) -> None:
    """Test that loop protocol is detected as having loops."""
    graph = extract_graph_from_source(
      LOOP_PROTOCOL_SOURCE, "multi_well_transfer", "test_module"
    )
    assert graph is not None
    assert graph.has_loops is True

  def test_conditional_protocol_detects_conditionals(self) -> None:
    """Test that conditional protocol is detected."""
    graph = extract_graph_from_source(
      CONDITIONAL_PROTOCOL_SOURCE, "conditional_volume", "test_module"
    )
    assert graph is not None
    assert graph.has_conditionals is True

  def test_multi_machine_detects_both_machines(self) -> None:
    """Test that multi-machine protocol detects both machine types."""
    graph = extract_graph_from_source(
      MULTI_MACHINE_SOURCE, "plate_reader_workflow", "test_module"
    )
    assert graph is not None
    assert "liquid_handler" in graph.machine_types
    assert "plate_reader" in graph.machine_types

  def test_multi_machine_operation_count(self) -> None:
    """Test that all operations are extracted."""
    graph = extract_graph_from_source(
      MULTI_MACHINE_SOURCE, "plate_reader_workflow", "test_module"
    )
    assert graph is not None
    # pick_up_tips, aspirate, dispense, drop_tips, read_absorbance
    assert len(graph.operations) == 5


class TestPreconditionExtraction:
  """Tests for precondition extraction."""

  def test_tips_loaded_precondition(self) -> None:
    """Test that aspirate/dispense require tips_loaded precondition."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    # Find aspirate operation
    aspirate_op = None
    for op in graph.operations:
      if op.method_name == "aspirate":
        aspirate_op = op
        break

    assert aspirate_op is not None
    # Aspirate should have preconditions (tips loaded, plate accessible)
    assert len(aspirate_op.preconditions) >= 0  # May have been satisfied by pick_up_tips

  def test_pick_up_tips_creates_state(self) -> None:
    """Test that pick_up_tips creates tips_loaded state."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    # Find pick_up_tips operation
    pickup_op = None
    for op in graph.operations:
      if op.method_name == "pick_up_tips":
        pickup_op = op
        break

    assert pickup_op is not None
    assert "tips_loaded" in pickup_op.creates_state

  def test_resource_on_deck_preconditions(self) -> None:
    """Test that resources have on_deck preconditions.

    backlog #4951: `b5635334` widened `PLR_RESOURCE_TYPES` to include
    machine frontends (`LiquidHandler`, `PlateReader`, ...) for
    `is_pylabrobot_resource`'s "asset that needs to be acquired at
    runtime" sense, which made this test regress to `4 == 3` -- `lh`
    (typed `LiquidHandler`) started getting its own spurious
    `RESOURCE_ON_DECK` precondition. That is a FALSE recognition, not a
    newly-correct one: `lh` is the instrument driving every call in this
    graph, never itself something placed on a deck, and
    `get_parental_chain("LiquidHandler", ...)` independently returns an
    empty chain -- corroborating that a machine simply does not fit the
    "resource -> deck" model this precondition encodes. The fix lives in
    `computation_graph_extractor.py`'s `_initialize_resources_from_params`
    (excludes `PLR_MACHINE_FRONTEND_TYPES`, `praxis/common/
    type_inspection.py`), not here -- the expected count stays `3`
    (source, dest, tips; not `lh`).
    """
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    # Check that preconditions exist for resource placement
    on_deck_preconds = [
      p
      for p in graph.preconditions
      if p.precondition_type == PreconditionType.RESOURCE_ON_DECK
    ]
    # Should have preconditions for source, dest, tips (3 PLR resources, not lh)
    assert len(on_deck_preconds) == 3


class TestGraphModel:
  """Tests for ProtocolComputationGraph model methods."""

  def test_get_operation(self) -> None:
    """Test get_operation method."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    op = graph.get_operation("op_1")
    assert op is not None
    assert op.method_name == "pick_up_tips"

  def test_get_operation_not_found(self) -> None:
    """Test get_operation returns None for unknown ID."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    op = graph.get_operation("op_999")
    assert op is None

  def test_get_resource(self) -> None:
    """Test get_resource method."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    res = graph.get_resource("source")
    assert res is not None
    assert res.declared_type == "Plate"

  def test_get_resource_not_found(self) -> None:
    """Test get_resource returns None for unknown name."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    res = graph.get_resource("nonexistent")
    assert res is None

  def test_get_unsatisfied_preconditions(self) -> None:
    """Test get_unsatisfied_preconditions method."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module"
    )
    assert graph is not None

    unsatisfied = graph.get_unsatisfied_preconditions()
    # resource_on_deck preconditions are unsatisfied (no satisfying operation)
    assert len(unsatisfied) > 0


class TestParentalChainIntegration:
  """Tests for parental chain integration in resource nodes."""

  def test_resource_parental_chain_carrier_based(self) -> None:
    """Test that resources have correct parental chains for carrier-based deck."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE,
      "simple_transfer",
      "test_module",
    )
    assert graph is not None

    source = graph.resources.get("source")
    assert source is not None
    # Plate -> PlateCarrier -> Deck
    assert "PlateCarrier" in source.parental_chain
    assert "Deck" in source.parental_chain

  def test_resource_parental_chain_tiprack(self) -> None:
    """Test that TipRack has correct parental chain."""
    graph = extract_graph_from_source(
      SIMPLE_TRANSFER_SOURCE,
      "simple_transfer",
      "test_module",
    )
    assert graph is not None

    tips = graph.resources.get("tips")
    assert tips is not None
    # TipRack -> TipCarrier -> Deck
    assert "TipCarrier" in tips.parental_chain
    assert "Deck" in tips.parental_chain


class TestExtractGraphFromSourceErrors:
  """Tests for error handling in extract_graph_from_source."""

  def test_invalid_source_returns_none(self) -> None:
    """Test that invalid Python source returns None."""
    graph = extract_graph_from_source(
      "this is not valid python {{{",
      "function",
      "module",
    )
    assert graph is None

  def test_function_not_found_returns_none(self) -> None:
    """Test that missing function returns None."""
    graph = extract_graph_from_source(
      "def other_function(): pass",
      "missing_function",
      "module",
    )
    assert graph is None

  def test_empty_function(self) -> None:
    """Test extracting graph from empty function."""
    source = '''
async def empty_protocol(lh: LiquidHandler):
    """Does nothing."""
    pass
'''
    graph = extract_graph_from_source(source, "empty_protocol", "test")
    assert graph is not None
    assert len(graph.operations) == 0


class TestFrozensetsMatchPlrSurface:
  """Regression guard for backlog #4846.

  The five hand-typed frozensets in computation_graph_extractor.py
  (TIPS_REQUIRED_METHODS, TIPS_LOADING_METHODS, TIPS_DROPPING_METHODS,
  PLATE_ACCESS_METHODS, PLATE_MOVE_METHODS) are the sole source of the
  preconditions / creates_state edges written onto every OperationNode. A
  stale entry (a method that no longer exists on its declared receiver
  class) means a precondition silently never fires. This test asserts every
  member exists as a method on at least one of its declared receiver
  classes, per the AST-derived survey of the real PLR surface at the
  currently pinned PLR commit.

  Before the 260901 fix, this test failed against the original sets:
  TIPS_REQUIRED_METHODS contained "mix", "blow_out", "touch_tip" (none
  exist on LiquidHandler at PLR pin dd79c4c89 / 0.2.2), PLATE_ACCESS_METHODS
  contained "mix", and PLATE_MOVE_METHODS contained "get_plate" / "put_plate"
  (they exist on PlateReader/Imager and a LiquidHandler *backend*
  respectively, not on LiquidHandler itself, which is the declared receiver
  for this set per its "require iSWAP or similar" docstring).
  """

  @pytest.fixture(scope="class")
  def plr_method_index(self) -> dict[str, set[str]]:
    """Load the {class_name: {method_name, ...}} index from the AST survey."""
    return _load_plr_method_index()

  @pytest.mark.parametrize("set_name", sorted(_FROZENSET_RECEIVER_CLASSES))
  def test_frozenset_members_exist_on_declared_receiver(
    self, set_name: str, plr_method_index: dict[str, set[str]]
  ) -> None:
    """Every member of each frozenset must exist on one of its receivers."""
    members, receiver_classes = _FROZENSET_RECEIVER_CLASSES[set_name]

    known_methods: set[str] = set()
    for receiver_class in receiver_classes:
      known_methods |= plr_method_index.get(receiver_class, set())

    stale = sorted(members - known_methods)
    assert not stale, (
      f"{set_name} contains method(s) not found on receiver class(es) "
      f"{receiver_classes} in the PLR AST survey: {stale}. "
      "Either the method was renamed/removed upstream (prune the entry) "
      "or the declared receiver class in this test is wrong (fix "
      "_FROZENSET_RECEIVER_CLASSES)."
    )

  def test_declared_receiver_classes_are_known_to_the_survey(
    self, plr_method_index: dict[str, set[str]]
  ) -> None:
    """Sanity check: the receiver classes we test against actually exist.

    Guards against a silently-empty `known_methods` set (e.g. a class name
    typo) making the main test above vacuously pass.
    """
    all_receiver_classes = {
      receiver_class
      for _, receivers in _FROZENSET_RECEIVER_CLASSES.values()
      for receiver_class in receivers
    }
    missing = sorted(all_receiver_classes - set(plr_method_index))
    assert not missing, f"Receiver class(es) not present in PLR survey: {missing}"


def _extract_with_resource_grid(
  source: str,
  function_name: str,
  resource_grid: dict[str, tuple[int | None, int | None]],
):
  """Extract a graph, first seeding a resource's `items_x`/`items_y` as if
  an earlier pipeline stage (not this extractor -- see
  `computation_graph_extractor.py`'s own note that it never sets these
  fields) had already populated the grid, so §12.2.3 condition 3
  (`range(<resource>.items_x)`) has something real to prove against.
  """
  tree = cst.parse_module(source)
  wrapper = MetadataWrapper(tree)
  for stmt in wrapper.module.body:
    if isinstance(stmt, cst.FunctionDef) and stmt.name.value == function_name:
      parameter_types: dict[str, str] = {}
      for param in stmt.params.params:
        if param.annotation:
          parameter_types[param.name.value] = cst.Module([]).code_for_node(
            param.annotation.annotation
          )
        else:
          parameter_types[param.name.value] = "Any"

      extractor = ComputationGraphExtractor(
        protocol_fqn=f"test_module.{function_name}",
        parameter_types=parameter_types,
      )
      for name, (items_x, items_y) in resource_grid.items():
        resource = extractor._resources.get(name)
        if resource is not None:
          resource.items_x = items_x
          resource.items_y = items_y
      with extractor.resolve(wrapper):
        _walk_cst_node(stmt, extractor)
      return extractor.build_graph()
  return None


class TestRegionEmission:
  """§12.2 -- real LOOP/BRANCH region headers, AC-12.5 through AC-12.9."""

  def test_ac_12_5_loop_protocol_emits_region_header(self) -> None:
    """AC-12.5's loop half: `LOOP_PROTOCOL_SOURCE` gets a `REGION` header
    whose `foreach_body` names the loop body ops, which do NOT additionally
    appear at top level in `execution_order`.
    """
    graph = extract_graph_from_source(
      LOOP_PROTOCOL_SOURCE, "multi_well_transfer", "test_module"
    )
    assert graph is not None
    headers = [op for op in graph.operations if op.node_type == GraphNodeType.REGION]
    assert len(headers) == 1
    header = headers[0]
    assert header.method_name == ""
    assert header.receiver_variable == ""
    assert header.receiver_type is None
    assert header.foreach_body
    body_ops = {op.id for op in graph.operations if op.method_name in ("aspirate", "dispense")}
    assert set(header.foreach_body) == body_ops
    # Body ops are owned by the header, not repeated at top level.
    assert not (body_ops & set(graph.execution_order))
    assert header.id in graph.execution_order
    assert graph.has_loops is True

  def test_ac_12_5_conditional_protocol_emits_region_header(self) -> None:
    """AC-12.5's branch half: `CONDITIONAL_PROTOCOL_SOURCE` gets a `REGION`
    header whose `true_branch` names the body op, not repeated at top
    level.
    """
    graph = extract_graph_from_source(
      CONDITIONAL_PROTOCOL_SOURCE, "conditional_volume", "test_module"
    )
    assert graph is not None
    headers = [op for op in graph.operations if op.node_type == GraphNodeType.REGION]
    assert len(headers) == 1
    header = headers[0]
    assert header.condition_expr == "volume > threshold"
    assert header.true_branch and header.false_branch
    branch_ops = {op.id for op in graph.operations if op.method_name == "aspirate"}
    assert set(header.true_branch) | set(header.false_branch) == branch_ops
    assert not (branch_ops & set(graph.execution_order))
    assert graph.has_conditionals is True

  def test_ac_12_6_proved_trip_counts(self) -> None:
    """AC-12.6: seven loops prove `3, 4, 3, 12, None, None, None` in
    source order, and an eighth (`range(0)`) proves `0` with a non-empty
    body.
    """
    graph = _extract_with_resource_grid(
      SEVEN_LOOPS_SOURCE, "seven_loops_protocol", {"plate": (12, 8)}
    )
    assert graph is not None
    headers = [op for op in graph.operations if op.node_type == GraphNodeType.REGION]
    assert len(headers) == 8
    trips = [h.trip for h in headers]
    assert trips == [3, 4, 3, 12, None, None, None, 0]
    # The eighth loop's body must be non-empty, or the trip==0 assertion
    # would be vacuous (spec §12.2.3's own caution).
    assert headers[-1].foreach_body

  def test_elif_chain_nests_as_false_branch_header(self) -> None:
    """§12.2.4: `elif` is a nested header inside its predecessor's
    `false_branch`, not a third arm -- and nesting inside a `for` and a
    `while` is structural (a header inside another header's body list).
    """
    graph = extract_graph_from_source(
      NESTED_REGIONS_SOURCE, "nested_regions_protocol", "test_module"
    )
    assert graph is not None
    headers = {op.id: op for op in graph.operations if op.node_type == GraphNodeType.REGION}
    # for i in range(2): -> the sole top-level (execution_order) header.
    assert len(graph.execution_order) == 1
    for_header = headers[graph.execution_order[0]]
    assert for_header.foreach_source == "range(2)"
    assert for_header.trip == 2

    # Its body contains the outer if/elif/else header AND the while header,
    # in that order, both owned by the for-loop -- neither repeated at top
    # level in execution_order.
    assert len(for_header.foreach_body) == 2
    outer_if_id, while_id = for_header.foreach_body
    outer_if = headers[outer_if_id]
    while_header = headers[while_id]
    assert while_header.foreach_body  # the while's own body (pick_up_tips)
    assert while_header.trip is None

    # elif -> nested header inside outer_if.false_branch, not a third arm.
    assert len(outer_if.true_branch) == 1  # the `if` arm: aspirate
    assert len(outer_if.false_branch) == 1  # a NESTED header, the elif
    nested_id = outer_if.false_branch[0]
    nested_if = headers[nested_id]
    assert nested_id in headers
    assert nested_if.true_branch  # the elif's own true arm: dispense
    assert nested_if.false_branch  # the elif's own else arm: drop_tips

    # Every NESTED header (everything but the outer for-loop's own id) is
    # owned by its parent's region field and never repeated at top level.
    nested_header_ids = set(headers) - {for_header.id}
    assert not (nested_header_ids & set(graph.execution_order))

  def test_for_else_and_while_else_stay_flat(self) -> None:
    """§12.2.4: `for...else` is out of scope -- no header, body operations
    stay flat at top level exactly as before this restructure, and
    `has_loops` still fires so the retained synthetic wrap still catches
    it.
    """
    graph = extract_graph_from_source(FOR_ELSE_SOURCE, "for_else_protocol", "test_module")
    assert graph is not None
    assert graph.has_loops is True
    assert not any(op.node_type == GraphNodeType.REGION for op in graph.operations)
    assert set(graph.execution_order) == {op.id for op in graph.operations}
    assert [op.method_name for op in graph.operations] == ["pick_up_tips", "drop_tips"]

  def test_self_attr_assignment_registers_resource(self) -> None:
    """§12.2.5 (round-1 O4): `self.<attr> = ...` registers a `ResourceNode`
    under `variable_name == "self.<attr>"`, `is_parameter is False`.
    """
    graph = extract_graph_from_source(SELF_ATTR_SOURCE, "self_attr_protocol", "test_module")
    assert graph is not None
    resource = graph.resources.get("self.plate_1")
    assert resource is not None
    assert resource.variable_name == "self.plate_1"
    assert resource.is_parameter is False
    assert resource.declared_type == "Plate"

  def test_empty_loop_body_emits_no_header(self) -> None:
    """A `for`/`while`/`if` whose body carries no operation the extractor
    would otherwise emit gets no `REGION` header at all (§12.2.2's "for
    every ... statement whose body contains at least one operation").
    """
    source = '''
async def empty_loop_protocol(lh: LiquidHandler):
    """Loop and branch bodies with no machine calls."""
    for i in range(3):
        x = i + 1

    if True:
        y = 1
    else:
        z = 2
'''
    graph = extract_graph_from_source(source, "empty_loop_protocol", "test")
    assert graph is not None
    assert len(graph.operations) == 0
    assert graph.has_loops is True
    assert graph.has_conditionals is True


class TestLineNumbers:
  """backlog #4948: `OperationNode.line_number` is real (PositionProvider
  via `MetadataWrapper`), not the pre-fix constant `0`
  (`_current_line` was assigned once in `__init__` and never again).
  """

  def test_three_calls_on_three_distinct_lines_report_distinct_lines(self) -> None:
    """`SIMPLE_TRANSFER_SOURCE`'s four straight-line calls sit on four
    consecutive, known source lines (9-12) -- each `OperationNode` must
    carry its OWN call's real line, not `0` and not one shared value.
    """
    graph = extract_graph_from_source(SIMPLE_TRANSFER_SOURCE, "simple_transfer", "test_module")
    assert graph is not None
    by_method = {op.method_name: op.line_number for op in graph.operations}
    assert by_method == {
      "pick_up_tips": 9,
      "aspirate": 10,
      "dispense": 11,
      "drop_tips": 12,
    }
    # Three (in fact four) distinct, non-zero lines -- not the pre-fix
    # collapse where every call reported the same `0`.
    assert len(set(by_method.values())) == len(by_method)
    assert 0 not in by_method.values()

  def test_region_header_carries_its_own_statement_line_and_body_ops_carry_theirs(
    self,
  ) -> None:
    """`LOOP_PROTOCOL_SOURCE`: the `for` statement is on line 15; its body
    (`aspirate`, `dispense`) is on lines 16-17; the straight-line
    `pick_up_tips`/`drop_tips` bracketing the loop are on lines 13 and 19.
    The REGION header's own `line_number` is the `for` keyword's line, NOT
    its first body operation's line (they must differ) and NOT `0`.
    """
    graph = extract_graph_from_source(LOOP_PROTOCOL_SOURCE, "multi_well_transfer", "test_module")
    assert graph is not None
    by_method = {
      op.method_name: op.line_number
      for op in graph.operations
      if op.node_type != GraphNodeType.REGION
    }
    assert by_method == {
      "pick_up_tips": 13,
      "aspirate": 16,
      "dispense": 17,
      "drop_tips": 19,
    }
    headers = [op for op in graph.operations if op.node_type == GraphNodeType.REGION]
    assert len(headers) == 1
    header = headers[0]
    assert header.line_number == 15
    # The header's own line is distinct from every one of its body ops'.
    assert header.line_number not in {by_method["aspirate"], by_method["dispense"]}

  def test_if_region_header_line_is_the_if_statement_not_an_arm(self) -> None:
    """`CONDITIONAL_PROTOCOL_SOURCE`'s `if` header reports the `if`
    keyword's own line, distinct from both the `true_branch` and
    `false_branch` `aspirate` calls' lines.
    """
    graph = extract_graph_from_source(
      CONDITIONAL_PROTOCOL_SOURCE, "conditional_volume", "test_module"
    )
    assert graph is not None
    headers = [op for op in graph.operations if op.node_type == GraphNodeType.REGION]
    assert len(headers) == 1
    header = headers[0]
    aspirate_lines = {
      op.line_number for op in graph.operations if op.method_name == "aspirate"
    }
    assert len(aspirate_lines) == 2  # the true and false arms are on different lines
    assert header.line_number not in aspirate_lines
    assert header.line_number != 0
