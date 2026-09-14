"""Tests for the protocol tracing infrastructure.

This module tests:
- Tracer classes (TracedResource, TracedMachine, TracedWellCollection)
- OperationRecorder functionality
- ProtocolTracingExecutor integration
"""

import pytest

from praxis.backend.core.tracing.executor import (
  trace_protocol_sync,
)
from praxis.backend.core.tracing.recorder import OperationRecorder
from praxis.backend.core.tracing.tracers import (
  TracedMachine,
  TracedResource,
  TracedWell,
  TracedWellCollection,
)

# =============================================================================
# Test TracedResource
# =============================================================================


class TestTracedResource:
  """Tests for TracedResource class."""

  @pytest.fixture
  def recorder(self) -> OperationRecorder:
    """Create a recorder for testing."""
    return OperationRecorder(protocol_fqn="test.protocol", protocol_name="protocol")

  def test_init(self, recorder: OperationRecorder) -> None:
    """Test TracedResource initialization."""
    resource = TracedResource(
      name="plate",
      recorder=recorder,
      declared_type="Plate",
      resource_type="Plate",
    )
    assert resource.name == "plate"
    assert resource.resource_type == "Plate"

  def test_getitem_single_well(self, recorder: OperationRecorder) -> None:
    """Test subscript access for single well."""
    resource = TracedResource(
      name="plate",
      recorder=recorder,
      declared_type="Plate",
      resource_type="Plate",
    )
    well = resource["A1"]
    assert isinstance(well, TracedWell)
    assert well.name == "plate['A1']"
    assert well.element_type == "Well"

  def test_getitem_well_range(self, recorder: OperationRecorder) -> None:
    """Test subscript access for well range."""
    resource = TracedResource(
      name="plate",
      recorder=recorder,
      declared_type="Plate",
      resource_type="Plate",
    )
    wells = resource["A1:A8"]
    assert isinstance(wells, TracedWellCollection)
    assert wells.name == "plate['A1:A8']"
    assert wells.element_type == "Well"

  def test_getitem_tiprack(self, recorder: OperationRecorder) -> None:
    """Test subscript access for TipRack returns TipSpot."""
    resource = TracedResource(
      name="tips",
      recorder=recorder,
      declared_type="TipRack",
      resource_type="TipRack",
    )
    tip = resource["A1"]
    assert isinstance(tip, TracedWell)
    assert tip.element_type == "TipSpot"

  def test_wells_method(self, recorder: OperationRecorder) -> None:
    """Test wells() method returns TracedWellCollection."""
    resource = TracedResource(
      name="plate",
      recorder=recorder,
      declared_type="Plate",
      resource_type="Plate",
    )
    wells = resource.wells()
    assert isinstance(wells, TracedWellCollection)
    assert wells.name == "plate.wells()"
    assert wells.element_type == "Well"

  def test_tips_method(self, recorder: OperationRecorder) -> None:
    """Test tips() method for TipRack."""
    resource = TracedResource(
      name="tips",
      recorder=recorder,
      declared_type="TipRack",
      resource_type="TipRack",
    )
    tip_spots = resource.tips()
    assert isinstance(tip_spots, TracedWellCollection)
    assert tip_spots.element_type == "TipSpot"


# =============================================================================
# Test TracedWellCollection
# =============================================================================


class TestTracedWellCollection:
  """Tests for TracedWellCollection class."""

  @pytest.fixture
  def recorder(self) -> OperationRecorder:
    """Create a recorder for testing."""
    return OperationRecorder(protocol_fqn="test.protocol", protocol_name="protocol")

  def test_iter_yields_traced_well(self, recorder: OperationRecorder) -> None:
    """Test iteration yields a TracedWell."""
    collection = TracedWellCollection(
      name="plate.wells()",
      recorder=recorder,
      declared_type="list[Well]",
      element_type="Well",
      source_resource="plate",
    )
    wells = list(collection)
    assert len(wells) == 1
    assert isinstance(wells[0], TracedWell)
    assert "each_" in wells[0].name

  def test_iter_records_loop(self, recorder: OperationRecorder) -> None:
    """Test iteration records loop in recorder."""
    collection = TracedWellCollection(
      name="plate.wells()",
      recorder=recorder,
      declared_type="list[Well]",
      element_type="Well",
    )
    list(collection)  # Iterate
    graph = recorder.build_graph()
    assert graph.has_loops is True

  def test_getitem_int(self, recorder: OperationRecorder) -> None:
    """Test integer indexing returns TracedWell."""
    collection = TracedWellCollection(
      name="wells",
      recorder=recorder,
      declared_type="list[Well]",
      element_type="Well",
    )
    well = collection[0]
    assert isinstance(well, TracedWell)
    assert well.name == "wells[0]"

  def test_getitem_slice(self, recorder: OperationRecorder) -> None:
    """Test slice indexing returns TracedWellCollection."""
    collection = TracedWellCollection(
      name="wells",
      recorder=recorder,
      declared_type="list[Well]",
      element_type="Well",
    )
    sub = collection[0:8]
    assert isinstance(sub, TracedWellCollection)


# =============================================================================
# Test TracedMachine
# =============================================================================


class TestTracedMachine:
  """Tests for TracedMachine class."""

  @pytest.fixture
  def recorder(self) -> OperationRecorder:
    """Create a recorder for testing."""
    return OperationRecorder(protocol_fqn="test.protocol", protocol_name="protocol")

  def test_method_call_records_operation(self, recorder: OperationRecorder) -> None:
    """Test that method calls are recorded."""
    lh = TracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
    )
    lh.pick_up_tips("tips")
    graph = recorder.build_graph()

    assert len(graph.operations) == 1
    assert graph.operations[0].method_name == "pick_up_tips"
    assert graph.operations[0].receiver_variable == "lh"

  def test_method_call_with_traced_arg(self, recorder: OperationRecorder) -> None:
    """Test method calls with TracedValue arguments."""
    lh = TracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
    )
    plate = TracedResource(
      name="plate",
      recorder=recorder,
      declared_type="Plate",
      resource_type="Plate",
    )
    well = plate["A1"]
    lh.aspirate(well, 100)

    graph = recorder.build_graph()
    assert len(graph.operations) == 1
    assert "plate['A1']" in graph.operations[0].arguments.get("resource", "")

  def test_multiple_operations(self, recorder: OperationRecorder) -> None:
    """Test recording multiple operations."""
    lh = TracedMachine(
      name="lh",
      recorder=recorder,
      declared_type="LiquidHandler",
      machine_type="liquid_handler",
    )
    lh.pick_up_tips("tips")
    lh.aspirate("well", 100)
    lh.dispense("dest", 100)
    lh.drop_tips("tips")

    graph = recorder.build_graph()
    assert len(graph.operations) == 4
    methods = [op.method_name for op in graph.operations]
    assert methods == ["pick_up_tips", "aspirate", "dispense", "drop_tips"]


# =============================================================================
# Test OperationRecorder
# =============================================================================


class TestOperationRecorder:
  """Tests for OperationRecorder class."""

  def test_init(self) -> None:
    """Test recorder initialization."""
    recorder = OperationRecorder(
      protocol_fqn="my_module.my_protocol",
      protocol_name="my_protocol",
    )
    assert recorder._protocol_fqn == "my_module.my_protocol"
    assert recorder._protocol_name == "my_protocol"

  def test_record_operation(self) -> None:
    """Test recording an operation."""
    recorder = OperationRecorder(protocol_fqn="test.protocol")
    op_id = recorder.record_operation(
      receiver="lh",
      receiver_type="liquid_handler",
      method="aspirate",
      args=["well", "100"],
      kwargs={},
    )
    assert op_id.startswith("traced_op_")
    assert len(recorder._operations) == 1

  def test_build_graph(self) -> None:
    """Test building the computation graph."""
    recorder = OperationRecorder(protocol_fqn="test.protocol")
    recorder.record_operation(
      receiver="lh",
      receiver_type="liquid_handler",
      method="aspirate",
      args=["well", "100"],
      kwargs={},
    )
    graph = recorder.build_graph()

    assert graph.protocol_fqn == "test.protocol"
    assert len(graph.operations) == 1
    assert "liquid_handler" in graph.machine_types

  def test_register_resource(self) -> None:
    """Test registering a resource."""
    recorder = OperationRecorder(protocol_fqn="test.protocol")
    recorder.register_resource(
      name="plate",
      declared_type="Plate",
      resource_type="Plate",
      is_parameter=True,
    )
    graph = recorder.build_graph()

    assert "plate" in graph.resources
    assert "Plate" in graph.resource_types

  def test_tips_loaded_precondition(self) -> None:
    """Test tips_loaded precondition is created for aspirate."""
    recorder = OperationRecorder(protocol_fqn="test.protocol")
    # aspirate without prior pick_up_tips
    recorder.record_operation(
      receiver="lh",
      receiver_type="liquid_handler",
      method="aspirate",
      args=["well", "100"],
      kwargs={},
    )
    graph = recorder.build_graph()

    # Should have a tips_loaded precondition
    tips_preconds = [
      p for p in graph.preconditions if p.precondition_type.value == "tips_loaded"
    ]
    assert len(tips_preconds) == 1

  def test_pick_up_tips_satisfies_precondition(self) -> None:
    """Test pick_up_tips satisfies tips_loaded precondition."""
    recorder = OperationRecorder(protocol_fqn="test.protocol")
    # Create precondition first by calling aspirate
    recorder.record_operation(
      receiver="lh",
      receiver_type="liquid_handler",
      method="aspirate",
      args=["well", "100"],
      kwargs={},
    )
    # Then pick_up_tips should satisfy it
    recorder.record_operation(
      receiver="lh",
      receiver_type="liquid_handler",
      method="pick_up_tips",
      args=["tips"],
      kwargs={},
    )
    graph = recorder.build_graph()

    # Precondition should be satisfied
    tips_preconds = [
      p for p in graph.preconditions if p.precondition_type.value == "tips_loaded"
    ]
    # The first precondition is from aspirate, pick_up_tips satisfies future ones
    assert len(tips_preconds) == 1


# =============================================================================
# Test ProtocolTracingExecutor
# =============================================================================


class TestProtocolTracingExecutor:
  """Tests for ProtocolTracingExecutor class."""

  def test_trace_simple_protocol(self) -> None:
    """Test tracing a simple protocol."""

    async def simple_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 100)
      await lh.dispense(plate["B1"], 100)
      await lh.drop_tips(tips)

    graph = trace_protocol_sync(
      simple_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    assert graph.protocol_name == "simple_protocol"
    assert len(graph.operations) == 4
    assert "liquid_handler" in graph.machine_types

  def test_trace_with_loop(self) -> None:
    """Test tracing a protocol with a loop."""

    async def loop_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      for well in plate.wells():
        await lh.aspirate(well, 50)
      await lh.drop_tips(tips)

    graph = trace_protocol_sync(
      loop_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    assert graph.has_loops is True
    # Should have: pick_up_tips, aspirate (in loop), drop_tips
    assert len(graph.operations) == 3

  def test_trace_multi_machine(self) -> None:
    """Test tracing with multiple machine types."""

    async def multi_machine_protocol(lh, pr, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 100)
      await lh.dispense(plate["B1"], 100)
      await lh.drop_tips(tips)
      await pr.read_absorbance(plate, wavelength=450)

    graph = trace_protocol_sync(
      multi_machine_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "pr": "PlateReader",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    assert "liquid_handler" in graph.machine_types
    assert "plate_reader" in graph.machine_types
    assert len(graph.operations) == 5

  def test_executor_creates_resources(self) -> None:
    """Test that executor registers resources."""

    async def resource_protocol(lh, plate):
      await lh.aspirate(plate["A1"], 100)

    graph = trace_protocol_sync(
      resource_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
      },
    )

    assert "plate" in graph.resources
    assert graph.resources["plate"].is_parameter is True


# =============================================================================
# Integration Tests with Fixture Protocols
# =============================================================================


class TestProtocolTracing:
  """Integration tests with realistic protocols."""

  def test_simple_linear_pattern(self) -> None:
    """Test simple linear protocol (no loops/conditionals)."""

    async def simple_transfer(lh, source, dest, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(source["A1"], 100)
      await lh.dispense(dest["A1"], 100)
      await lh.drop_tips(tips)

    graph = trace_protocol_sync(
      simple_transfer,
      parameter_types={
        "lh": "LiquidHandler",
        "source": "Plate",
        "dest": "Plate",
        "tips": "TipRack",
      },
    )

    assert graph.has_loops is False
    assert graph.has_conditionals is False
    assert len(graph.operations) == 4
    assert len(graph.resources) >= 3  # source, dest, tips

  def test_loop_based_pattern(self) -> None:
    """Test loop-based protocol."""

    async def multi_well_transfer(lh, source, dest, tips, volume=50.0):
      await lh.pick_up_tips(tips)
      for well in source.wells():
        await lh.aspirate(well, volume)
      await lh.drop_tips(tips)

    graph = trace_protocol_sync(
      multi_well_transfer,
      parameter_types={
        "lh": "LiquidHandler",
        "source": "Plate",
        "dest": "Plate",
        "tips": "TipRack",
        "volume": "float",
      },
    )

    assert graph.has_loops is True
    # Foreach node type for operations inside loop
    loop_ops = [op for op in graph.operations if op.foreach_source]
    assert len(loop_ops) > 0

  def test_resources_have_deck_preconditions(self) -> None:
    """Test that resource parameters generate on-deck preconditions."""

    async def deck_protocol(lh, plate, tips):
      await lh.pick_up_tips(tips)
      await lh.aspirate(plate["A1"], 100)
      await lh.drop_tips(tips)

    graph = trace_protocol_sync(
      deck_protocol,
      parameter_types={
        "lh": "LiquidHandler",
        "plate": "Plate",
        "tips": "TipRack",
      },
    )

    # Should have resource_on_deck preconditions for plate and tips
    deck_preconds = [
      p for p in graph.preconditions if p.precondition_type.value == "resource_on_deck"
    ]
    assert len(deck_preconds) >= 2
