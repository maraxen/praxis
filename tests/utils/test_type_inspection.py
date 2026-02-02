"""Tests for type inspection utilities in utils/type_inspection.py."""

import inspect
from collections.abc import Sequence
from typing import Any, Optional, Union

from pylabrobot.resources import Carrier, Plate, Resource, TipRack

from praxis.backend.utils.type_inspection import (
    PLR_RESOURCE_TYPES,
    extract_resource_types,
    fqn_from_hint,
    get_element_type,
    is_container_type,
    is_pylabrobot_resource,
    serialize_type_hint,
)


class TestIsPylabrobotResource:

    """Tests for is_pylabrobot_resource function."""

    def test_returns_true_for_resource_class(self) -> None:
        """Test that Resource class is identified as PyLabRobot resource."""
        assert is_pylabrobot_resource(Resource)

    def test_returns_true_for_resource_subclass(self) -> None:
        """Test that Resource subclasses are identified as PyLabRobot resources."""
        from pylabrobot.resources import Carrier

        assert is_pylabrobot_resource(Plate)
        assert is_pylabrobot_resource(Carrier)

    def test_returns_false_for_non_resource_types(self) -> None:
        """Test that non-Resource types return False."""
        assert not is_pylabrobot_resource(int)
        assert not is_pylabrobot_resource(str)
        assert not is_pylabrobot_resource(dict)
        assert not is_pylabrobot_resource(list)

    def test_returns_false_for_parameter_empty(self) -> None:
        """Test that inspect.Parameter.empty returns False."""
        assert not is_pylabrobot_resource(inspect.Parameter.empty)

    def test_handles_union_with_resource(self) -> None:
        """Test that Union with Resource type returns True."""
        union_type = Union[Plate, str]
        assert is_pylabrobot_resource(union_type)

    def test_handles_optional_resource(self) -> None:
        """Test that Optional[Resource] returns True."""
        optional_type = Optional[Plate]
        assert is_pylabrobot_resource(optional_type)

    def test_handles_union_without_resource(self) -> None:
        """Test that Union without Resource returns False."""
        union_type = Union[int, str]
        assert not is_pylabrobot_resource(union_type)

    def test_handles_optional_non_resource(self) -> None:
        """Test that Optional of non-Resource returns False."""
        optional_type = Optional[int]
        assert not is_pylabrobot_resource(optional_type)

    def test_handles_union_with_none(self) -> None:
        """Test that Union with only None returns False."""
        union_type = Union[str, None]
        # Should return False because str is not a Resource
        assert not is_pylabrobot_resource(union_type)

    def test_handles_union_multiple_resources(self) -> None:
        """Test that Union with multiple Resource types returns True."""
        union_type = Union[Plate, Carrier]
        assert is_pylabrobot_resource(union_type)


class TestIsPylabrobotAsset:
    """Tests for machine types that should also be detected as assets.

    These tests currently FAIL because is_pylabrobot_resource() only checks
    for Plate, TipRack, Container, Resource strings. After the fix, machine
    types should be detected as assets.
    """

    def test_returns_true_for_liquid_handler_string(self) -> None:
        """Test that LiquidHandler string is identified as asset."""
        assert is_pylabrobot_resource("LiquidHandler")

    def test_returns_true_for_plate_reader_string(self) -> None:
        """Test that PlateReader string is identified as asset."""
        assert is_pylabrobot_resource("PlateReader")

    def test_returns_true_for_shaker_string(self) -> None:
        """Test that Shaker string is identified as asset."""
        assert is_pylabrobot_resource("Shaker")

    def test_returns_true_for_heater_shaker_string(self) -> None:
        """Test that HeaterShaker string is identified as asset."""
        assert is_pylabrobot_resource("HeaterShaker")

    def test_returns_true_for_trough_string(self) -> None:
        """Test that Trough string is identified as asset."""
        assert is_pylabrobot_resource("Trough")

    def test_returns_true_for_centrifuge_string(self) -> None:
        """Test that Centrifuge string is identified as asset."""
        assert is_pylabrobot_resource("Centrifuge")

    def test_returns_true_for_thermocycler_string(self) -> None:
        """Test that Thermocycler string is identified as asset."""
        assert is_pylabrobot_resource("Thermocycler")

    def test_returns_true_for_pump_string(self) -> None:
        """Test that Pump string is identified as asset."""
        assert is_pylabrobot_resource("Pump")

    def test_returns_true_for_incubator_string(self) -> None:
        """Test that Incubator string is identified as asset."""
        assert is_pylabrobot_resource("Incubator")

    def test_returns_true_for_optional_liquid_handler_string(self) -> None:
        """Test that Optional[LiquidHandler] string is identified as asset."""
        assert is_pylabrobot_resource("Optional[LiquidHandler]")

    def test_returns_true_for_runtime_liquid_handler(self) -> None:
        """Test that LiquidHandler class is identified as asset at runtime."""
        from pylabrobot.liquid_handling import LiquidHandler

        assert is_pylabrobot_resource(LiquidHandler)

    def test_returns_true_for_runtime_plate_reader(self) -> None:
        """Test that PlateReader class is identified as asset at runtime."""
        from pylabrobot.plate_reading import PlateReader

        assert is_pylabrobot_resource(PlateReader)

    def test_returns_true_for_runtime_shaker(self) -> None:
        """Test that Shaker class is identified as asset at runtime."""
        from pylabrobot.shaking import Shaker

        assert is_pylabrobot_resource(Shaker)


class TestFqnFromHint:


    """Tests for fqn_from_hint function."""

    def test_returns_any_for_parameter_empty(self) -> None:
        """Test that inspect.Parameter.empty returns 'Any'."""
        assert fqn_from_hint(inspect.Parameter.empty) == "Any"

    def test_returns_name_for_builtin_types(self) -> None:
        """Test that built-in types return just their name."""
        assert fqn_from_hint(int) == "int"
        assert fqn_from_hint(str) == "str"
        assert fqn_from_hint(float) == "float"
        assert fqn_from_hint(bool) == "bool"
        assert fqn_from_hint(dict) == "dict"
        assert fqn_from_hint(list) == "list"

    def test_returns_fqn_for_pylabrobot_types(self) -> None:
        """Test that PyLabRobot types return fully qualified names."""
        result = fqn_from_hint(Resource)
        assert result.startswith("pylabrobot.")
        assert "Resource" in result

        result = fqn_from_hint(Plate)
        assert result.startswith("pylabrobot.")
        assert "Plate" in result

    def test_handles_optional_type(self) -> None:
        """Test that Optional[T] returns FQN of T."""
        result = fqn_from_hint(Optional[int])
        assert result == "int"

        result = fqn_from_hint(Optional[Plate])
        assert "Plate" in result

    def test_handles_union_with_none(self) -> None:
        """Test that Union[T, None] returns FQN of T."""
        result = fqn_from_hint(Union[str, None])
        assert result == "str"

    def test_handles_union_without_none(self) -> None:
        """Test that Union without None returns string representation."""
        result = fqn_from_hint(Union[int, str])
        # Union types without None are not specifically handled
        # and return their string representation
        assert isinstance(result, str)

    def test_prioritizes_resource_in_optional_union(self) -> None:
        """Test that Resource types are prioritized in Optional Union."""
        result = fqn_from_hint(Union[str, Plate, None])
        # Should prioritize the Resource type (Plate) when None is present
        assert "Plate" in result

    def test_handles_optional_union_with_resource_first(self) -> None:
        """Test Optional Union when Resource is first."""
        result = fqn_from_hint(Union[Plate, str, None])
        # When resource is first in an optional union, it should be prioritized
        assert "Plate" in result

    def test_handles_union_with_only_none(self) -> None:
        """Test that Union with only None returns 'None'."""
        # This is a contrived case, but the code handles it
        result = fqn_from_hint(type(None))
        # The function would return "NoneType" or similar
        assert result is not None

    def test_returns_str_representation_for_unknown_types(self) -> None:
        """Test that unknown types return string representation."""
        # Create a type without __name__ attribute
        class CustomType:
            pass

        result = fqn_from_hint(CustomType)
        assert "CustomType" in result


class TestSerializeTypeHint:

    """Tests for serialize_type_hint function."""

    def test_returns_any_for_parameter_empty(self) -> None:
        """Test that inspect.Parameter.empty returns 'Any'."""
        assert serialize_type_hint(inspect.Parameter.empty) == "Any"

    def test_returns_string_representation_for_int(self) -> None:
        """Test that int type is serialized to string."""
        result = serialize_type_hint(int)
        assert isinstance(result, str)
        assert "int" in result

    def test_returns_string_representation_for_str(self) -> None:
        """Test that str type is serialized to string."""
        result = serialize_type_hint(str)
        assert isinstance(result, str)
        assert "str" in result

    def test_serializes_optional_type(self) -> None:
        """Test that Optional types are serialized."""
        result = serialize_type_hint(Optional[int])
        assert isinstance(result, str)
        assert "int" in result or "Optional" in result or "Union" in result

    def test_serializes_union_type(self) -> None:
        """Test that Union types are serialized."""
        result = serialize_type_hint(Union[int, str])
        assert isinstance(result, str)
        # Should contain both types or Union
        assert "int" in result or "str" in result or "Union" in result

    def test_serializes_resource_type(self) -> None:
        """Test that PyLabRobot Resource types are serialized."""
        result = serialize_type_hint(Plate)
        assert isinstance(result, str)
        assert "Plate" in result

    def test_serializes_list_type(self) -> None:
        """Test that generic list type is serialized."""
        result = serialize_type_hint(list[int])
        assert isinstance(result, str)
        # Should contain indication of list and int
        assert isinstance(result, str)

    def test_always_returns_string(self) -> None:
        """Test that serialize_type_hint always returns a string."""
        test_types = [
            int,
            str,
            float,
            bool,
            Optional[int],
            Union[int, str],
            Plate,
            Resource,
        ]

        for type_hint in test_types:
            result = serialize_type_hint(type_hint)
            assert isinstance(result, str), f"Failed for type: {type_hint}"


class TestTypeInspectionEdgeCases:

    """Tests for edge cases in type inspection utilities."""

    def test_is_pylabrobot_resource_with_string(self) -> None:
        """Test is_pylabrobot_resource handles string input gracefully."""
        # Shouldn't crash, should return False
        assert not is_pylabrobot_resource("not a type")

    def test_fqn_from_hint_with_any(self) -> None:
        """Test fqn_from_hint with Any type."""
        result = fqn_from_hint(Any)
        assert isinstance(result, str)

    def test_serialize_with_complex_nested_types(self) -> None:
        """Test serialize_type_hint with complex nested generics."""
        complex_type = dict[str, list[int | None]]
        result = serialize_type_hint(complex_type)
        assert isinstance(result, str)
        assert len(result) > 0


# =============================================================================
# Tests for extract_resource_types
# =============================================================================


class TestExtractResourceTypes:
    """Tests for extract_resource_types function."""

    # --- String Type Hints ---

    def test_extract_list_well_string(self) -> None:
        """Test extracting Well from list[Well] string."""
        result = extract_resource_types("list[Well]")
        assert result == ["Well"]

    def test_extract_sequence_tipspot_string(self) -> None:
        """Test extracting TipSpot from Sequence[TipSpot] string."""
        result = extract_resource_types("Sequence[TipSpot]")
        assert result == ["TipSpot"]

    def test_extract_tuple_mixed_string(self) -> None:
        """Test extracting multiple types from tuple[Plate, TipRack] string."""
        result = extract_resource_types("tuple[Plate, TipRack]")
        assert "Plate" in result
        assert "TipRack" in result

    def test_extract_optional_plate_string(self) -> None:
        """Test extracting Plate from Union[Plate, None] string."""
        result = extract_resource_types("Union[Plate, None]")
        assert result == ["Plate"]

    def test_extract_dict_values_string(self) -> None:
        """Test extracting Well from dict[str, list[Well]] string."""
        result = extract_resource_types("dict[str, list[Well]]")
        assert "Well" in result

    def test_extract_nested_list_string(self) -> None:
        """Test extracting from nested containers."""
        result = extract_resource_types("list[list[Well]]")
        assert result == ["Well"]

    def test_extract_simple_resource_string(self) -> None:
        """Test extracting Plate from simple type hint."""
        result = extract_resource_types("Plate")
        assert result == ["Plate"]

    def test_extract_no_resources_string(self) -> None:
        """Test that non-resource types return empty list."""
        result = extract_resource_types("list[int]")
        assert result == []

    def test_extract_carrier_types_string(self) -> None:
        """Test extracting carrier types."""
        result = extract_resource_types("PlateCarrier")
        assert result == ["PlateCarrier"]

        result = extract_resource_types("list[TipCarrier]")
        assert result == ["TipCarrier"]

    def test_extract_preserves_order_string(self) -> None:
        """Test that extraction preserves order and removes duplicates."""
        result = extract_resource_types("tuple[Plate, Well, Plate]")
        # Should have Plate first (order preserved), but no duplicates
        assert result == ["Plate", "Well"]

    # --- Runtime Type Hints ---

    def test_extract_list_runtime(self) -> None:
        """Test extracting from runtime list type."""
        result = extract_resource_types(list[Plate])
        assert result == ["Plate"]

    def test_extract_optional_runtime(self) -> None:
        """Test extracting from Optional runtime type."""
        result = extract_resource_types(Optional[Plate])
        assert result == ["Plate"]

    def test_extract_union_runtime(self) -> None:
        """Test extracting from Union runtime type."""
        result = extract_resource_types(Union[Plate, TipRack])
        assert "Plate" in result
        assert "TipRack" in result

    def test_extract_sequence_runtime(self) -> None:
        """Test extracting from Sequence runtime type."""
        result = extract_resource_types(Sequence[Plate])
        assert result == ["Plate"]

    def test_extract_tuple_runtime(self) -> None:
        """Test extracting from tuple runtime type."""
        result = extract_resource_types(tuple[Plate, TipRack])
        assert "Plate" in result
        assert "TipRack" in result

    def test_extract_plain_type_runtime(self) -> None:
        """Test extracting from plain resource type."""
        result = extract_resource_types(Plate)
        assert result == ["Plate"]

    def test_extract_non_resource_runtime(self) -> None:
        """Test that non-resource types return empty list."""
        result = extract_resource_types(list[int])
        assert result == []


class TestGetElementType:
    """Tests for get_element_type function."""

    # --- String Type Hints ---

    def test_get_element_list_well_string(self) -> None:
        """Test getting Well from list[Well] string."""
        result = get_element_type("list[Well]")
        assert result == "Well"

    def test_get_element_sequence_tipspot_string(self) -> None:
        """Test getting TipSpot from Sequence[TipSpot] string."""
        result = get_element_type("Sequence[TipSpot]")
        assert result == "TipSpot"

    def test_get_element_non_container_string(self) -> None:
        """Test that non-container returns None."""
        result = get_element_type("Plate")
        assert result is None

    def test_get_element_non_resource_container_string(self) -> None:
        """Test that container of non-resources returns None."""
        result = get_element_type("list[int]")
        assert result is None

    # --- Runtime Type Hints ---

    def test_get_element_list_runtime(self) -> None:
        """Test getting element type from runtime list type."""
        result = get_element_type(list[Plate])
        assert result == "Plate"

    def test_get_element_tuple_runtime(self) -> None:
        """Test getting element type from runtime tuple type."""
        result = get_element_type(tuple[Plate, TipRack])
        # Should return first PLR type
        assert result == "Plate"

    def test_get_element_non_container_runtime(self) -> None:
        """Test that non-container returns None."""
        result = get_element_type(Plate)
        assert result is None


class TestIsContainerType:
    """Tests for is_container_type function."""

    # --- String Type Hints ---

    def test_is_container_list_string(self) -> None:
        """Test list[X] is recognized as container."""
        assert is_container_type("list[Well]") is True

    def test_is_container_sequence_string(self) -> None:
        """Test Sequence[X] is recognized as container."""
        assert is_container_type("Sequence[TipSpot]") is True

    def test_is_container_tuple_string(self) -> None:
        """Test tuple[X] is recognized as container."""
        assert is_container_type("tuple[Plate, TipRack]") is True

    def test_is_not_container_string(self) -> None:
        """Test simple types are not containers."""
        assert is_container_type("Plate") is False
        assert is_container_type("int") is False

    # --- Runtime Type Hints ---

    def test_is_container_list_runtime(self) -> None:
        """Test list[X] is recognized as container at runtime."""
        assert is_container_type(list[Plate]) is True

    def test_is_container_sequence_runtime(self) -> None:
        """Test Sequence[X] is recognized as container at runtime."""
        assert is_container_type(Sequence[Plate]) is True

    def test_is_not_container_runtime(self) -> None:
        """Test plain types are not containers."""
        assert is_container_type(Plate) is False
        assert is_container_type(int) is False


class TestPLRResourceTypes:
    """Tests for PLR_RESOURCE_TYPES constant."""

    def test_contains_core_resources(self) -> None:
        """Test that core resource types are included."""
        assert "Plate" in PLR_RESOURCE_TYPES
        assert "TipRack" in PLR_RESOURCE_TYPES
        assert "Well" in PLR_RESOURCE_TYPES
        assert "TipSpot" in PLR_RESOURCE_TYPES
        assert "Carrier" in PLR_RESOURCE_TYPES
        assert "Deck" in PLR_RESOURCE_TYPES

    def test_contains_carrier_types(self) -> None:
        """Test that carrier types are included."""
        assert "PlateCarrier" in PLR_RESOURCE_TYPES
        assert "TipCarrier" in PLR_RESOURCE_TYPES
        assert "TroughCarrier" in PLR_RESOURCE_TYPES

    def test_contains_container_elements(self) -> None:
        """Test that container element types are included."""
        assert "Well" in PLR_RESOURCE_TYPES
        assert "TipSpot" in PLR_RESOURCE_TYPES
        assert "Spot" in PLR_RESOURCE_TYPES
        assert "Tube" in PLR_RESOURCE_TYPES

    def test_is_frozenset(self) -> None:
        """Test that PLR_RESOURCE_TYPES is immutable."""
        assert isinstance(PLR_RESOURCE_TYPES, frozenset)
