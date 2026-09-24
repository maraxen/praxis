"""Tests for core/decorators/protocol_decorator.py."""

from unittest.mock import Mock

import pytest

from praxis.backend.core.decorators import (
    ProtocolRuntimeInfo,
    _prepare_function_arguments,
    protocol_function,
)
from praxis.backend.core.run_context import PraxisRunContext
from praxis.backend.models.domain.protocol import (
    FunctionProtocolDefinitionCreate,
)
from praxis.backend.utils.uuid import uuid7


class TestPrepareFunctionArguments:

    """Tests for _prepare_function_arguments function."""

    @pytest.mark.asyncio
    async def test_prepare_function_arguments_basic(self) -> None:
        """Test preparing basic function arguments."""

        def test_func(volume: int):
            pass

        mock_context = Mock(spec=PraxisRunContext)
        mock_context.run_accession_id = uuid7()

        kwargs = {"volume": 100}

        result = await _prepare_function_arguments(
            test_func,
            kwargs,
            mock_context,
            None,
            "state",
        )

        assert result == {"volume": 100}

    @pytest.mark.asyncio
    async def test_prepare_function_arguments_with_praxis_run_context_param(self) -> None:
        """Test preparing arguments with __praxis_run_context__ parameter."""

        def test_func(__praxis_run_context__: PraxisRunContext, volume: int):
            pass

        mock_context = Mock(spec=PraxisRunContext)
        mock_context.run_accession_id = uuid7()

        kwargs = {"volume": 100}

        result = await _prepare_function_arguments(
            test_func,
            kwargs,
            mock_context,
            None,
            "state",
        )

        assert result["volume"] == 100
        assert result["__praxis_run_context__"] == mock_context

    @pytest.mark.asyncio
    async def test_prepare_function_arguments_with_state_param(self) -> None:
        """Test preparing arguments with state parameter."""

        def test_func(state: PraxisRunContext, volume: int):
            pass

        mock_context = Mock(spec=PraxisRunContext)
        mock_context.run_accession_id = uuid7()

        state_details = {
            "name": "state",
            "expects_praxis_state": True,
            "expects_dict": False,
        }

        kwargs = {"volume": 100}

        result = await _prepare_function_arguments(
            test_func,
            kwargs,
            mock_context,
            state_details,
            "state",
        )

        assert result["volume"] == 100
        assert result["state"] == mock_context


class TestProtocolFunctionDecorator:

    """Tests for protocol_function decorator."""

    def test_protocol_function_basic_decoration(self) -> None:
        """Test basic protocol function decoration."""

        @protocol_function(name="test_protocol", version="1.0")
        def my_protocol():
            pass

        assert hasattr(my_protocol, "_protocol_definition")
        assert hasattr(my_protocol, "_protocol_runtime_info")
        assert isinstance(my_protocol._protocol_definition, FunctionProtocolDefinitionCreate)
        assert my_protocol._protocol_definition.name == "test_protocol"
        assert my_protocol._protocol_definition.version == "1.0"

    def test_protocol_function_with_description(self) -> None:
        """Test protocol function with description."""

        @protocol_function(description="This is a test protocol")
        def my_protocol():
            pass

        assert my_protocol._protocol_definition.description == "This is a test protocol"

    def test_protocol_function_uses_function_name_if_not_provided(self) -> None:
        """Test that decorator uses function name if name not provided."""

        @protocol_function()
        def my_custom_protocol():
            pass

        assert my_custom_protocol._protocol_definition.name == "my_custom_protocol"

    def test_protocol_function_with_tags_and_category(self) -> None:
        """Test protocol function with tags and category."""

        @protocol_function(category="testing", tags=["unit", "test"])
        def my_protocol():
            pass

        assert my_protocol._protocol_definition.category == "testing"
        assert my_protocol._protocol_definition.tags == ["unit", "test"]

    def test_protocol_function_with_parameters(self) -> None:
        """Test protocol function with parameters."""

        @protocol_function(
            param_metadata={
                "volume": {"description": "Volume in microliters"},
            },
        )
        def my_protocol(volume: int):
            pass

        assert len(my_protocol._protocol_definition.parameters) == 1
        assert my_protocol._protocol_definition.parameters[0].name == "volume"
        assert my_protocol._protocol_definition.parameters[0].description == "Volume in microliters"

    def test_protocol_function_solo_execution(self) -> None:
        """Test protocol function with solo execution flag."""

        @protocol_function(solo=True)
        def my_protocol():
            pass

        assert my_protocol._protocol_definition.solo_execution is True


class TestProtocolFunctionDecoratorErrors:

    """Tests for protocol_function decorator error cases."""

    def test_protocol_function_top_level_without_state_raises_error(self) -> None:
        """Test that top-level protocol without state raises error."""
        with pytest.raises(TypeError, match="must define a 'state' parameter"):

            @protocol_function(is_top_level=True)
            def my_protocol():
                pass

    def test_protocol_function_invalid_top_level_name_raises_error(self) -> None:
        """Test that invalid top-level name raises error."""
        with pytest.raises(ValueError, match="does not match format"):

            @protocol_function(name="invalid name!", is_top_level=True)
            def my_protocol(state: dict):
                pass

    def test_protocol_function_preconfigure_deck_without_deck_param_raises_error(self) -> None:
        """Test that preconfigure_deck without deck param raises error."""
        with pytest.raises(TypeError, match="missing 'deck' param"):

            @protocol_function(preconfigure_deck=True)
            def my_protocol():
                pass


class TestDecoratorIntegration:

    """Integration tests for decorator functionality."""

    def test_decorated_function_retains_original_attributes(self) -> None:
        """Test that decorated function retains original attributes."""

        @protocol_function()
        def my_protocol():
            """My protocol docstring."""

        # Should retain name and docstring
        assert my_protocol.__name__ == "my_protocol"
        assert "My protocol docstring" in my_protocol.__doc__

    def test_decorated_function_has_runtime_info(self) -> None:
        """Test that decorated function has runtime info."""

        @protocol_function()
        def my_protocol():
            pass

        assert hasattr(my_protocol, "_protocol_runtime_info")
        runtime_info = my_protocol._protocol_runtime_info
        assert isinstance(runtime_info, ProtocolRuntimeInfo)
        assert runtime_info.function_ref == my_protocol.__wrapped__

    def test_multiple_decorations_work_independently(self) -> None:
        """Test that multiple functions can be decorated independently."""

        @protocol_function(name="protocol_one", version="1.0")
        def protocol_one():
            pass

        @protocol_function(name="protocol_two", version="2.0")
        def protocol_two():
            pass

        assert protocol_one._protocol_definition.name == "protocol_one"
        assert protocol_two._protocol_definition.name == "protocol_two"
        assert protocol_one._protocol_definition.version == "1.0"
        assert protocol_two._protocol_definition.version == "2.0"


class TestDecoratorsPackageStructure:

    """Tests for module structure and exports."""

    def test_module_exports_protocol_function(self) -> None:
        """Test that module exports protocol_function."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "protocol_function")

    def test_module_exports_create_protocol_definition_data(self) -> None:
        """Test that module exports CreateProtocolDefinitionData."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "CreateProtocolDefinitionData")

    def test_module_exports_protocol_runtime_info(self) -> None:
        """Test that module exports ProtocolRuntimeInfo."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "ProtocolRuntimeInfo")

    def test_module_has_logger(self) -> None:
        """Test that module defines logger."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "logger")

    def test_module_defines_constants(self) -> None:
        """Test that module defines expected constants."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "DEFAULT_DECK_PARAM_NAME")
        assert decorators.DEFAULT_DECK_PARAM_NAME == "deck"
        assert hasattr(decorators, "DEFAULT_STATE_PARAM_NAME")
        assert decorators.DEFAULT_STATE_PARAM_NAME == "state"
        assert hasattr(decorators, "TOP_LEVEL_NAME_REGEX")

    def test_module_exports_setup_instruction(self) -> None:
        """Test that module exports SetupInstruction."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "SetupInstruction")

    def test_module_exports_data_view_definition(self) -> None:
        """Test that module exports DataViewDefinition."""
        from praxis.backend.core import decorators

        assert hasattr(decorators, "DataViewDefinition")


class TestSetupInstructions:

    """Tests for setup_instructions parameter in protocol_function decorator."""

    def test_protocol_function_with_string_setup_instructions(self) -> None:
        """Test protocol function with string setup instructions."""

        @protocol_function(
            setup_instructions=[
                "Ensure source plate is at room temperature",
                "Verify tip rack is loaded in position 3",
            ],
        )
        def my_protocol():
            pass

        instructions = my_protocol._protocol_definition.setup_instructions_json
        assert instructions is not None
        assert len(instructions) == 2
        assert instructions[0]["message"] == "Ensure source plate is at room temperature"
        assert instructions[0]["severity"] == "required"
        assert instructions[0]["position"] is None
        assert instructions[0]["resource_type"] is None
        assert instructions[1]["message"] == "Verify tip rack is loaded in position 3"

    def test_protocol_function_with_dict_setup_instructions(self) -> None:
        """Test protocol function with dict setup instructions."""

        @protocol_function(
            setup_instructions=[
                {
                    "message": "Load 200µL tips",
                    "severity": "required",
                    "position": "3",
                    "resource_type": "TipRack",
                },
                {
                    "message": "Optional calibration",
                    "severity": "recommended",
                },
            ],
        )
        def my_protocol():
            pass

        instructions = my_protocol._protocol_definition.setup_instructions_json
        assert instructions is not None
        assert len(instructions) == 2
        assert instructions[0]["message"] == "Load 200µL tips"
        assert instructions[0]["severity"] == "required"
        assert instructions[0]["position"] == "3"
        assert instructions[0]["resource_type"] == "TipRack"
        assert instructions[1]["message"] == "Optional calibration"
        assert instructions[1]["severity"] == "recommended"

    def test_protocol_function_with_setup_instruction_dataclass(self) -> None:
        """Test protocol function with SetupInstruction dataclass instances."""
        from praxis.backend.core.decorators import SetupInstruction

        @protocol_function(
            setup_instructions=[
                SetupInstruction(
                    message="Critical step",
                    severity="required",
                    position="1",
                    resource_type="Plate",
                ),
                SetupInstruction(
                    message="Info only",
                    severity="info",
                ),
            ],
        )
        def my_protocol():
            pass

        instructions = my_protocol._protocol_definition.setup_instructions_json
        assert instructions is not None
        assert len(instructions) == 2
        assert instructions[0]["message"] == "Critical step"
        assert instructions[0]["severity"] == "required"
        assert instructions[0]["position"] == "1"
        assert instructions[0]["resource_type"] == "Plate"
        assert instructions[1]["message"] == "Info only"
        assert instructions[1]["severity"] == "info"
        assert instructions[1]["position"] is None

    def test_protocol_function_with_mixed_setup_instructions(self) -> None:
        """Test protocol function with mixed types of setup instructions."""
        from praxis.backend.core.decorators import SetupInstruction

        @protocol_function(
            setup_instructions=[
                "Simple string instruction",
                {"message": "Dict instruction", "severity": "recommended"},
                SetupInstruction(message="Dataclass instruction", severity="info"),
            ],
        )
        def my_protocol():
            pass

        instructions = my_protocol._protocol_definition.setup_instructions_json
        assert instructions is not None
        assert len(instructions) == 3
        assert instructions[0]["message"] == "Simple string instruction"
        assert instructions[0]["severity"] == "required"  # Default for strings
        assert instructions[1]["message"] == "Dict instruction"
        assert instructions[1]["severity"] == "recommended"
        assert instructions[2]["message"] == "Dataclass instruction"
        assert instructions[2]["severity"] == "info"

    def test_protocol_function_without_setup_instructions(self) -> None:
        """Test protocol function without setup instructions returns None."""

        @protocol_function()
        def my_protocol():
            pass

        assert my_protocol._protocol_definition.setup_instructions_json is None

    def test_protocol_function_with_empty_setup_instructions(self) -> None:
        """Test protocol function with empty setup instructions list."""

        @protocol_function(setup_instructions=[])
        def my_protocol():
            pass

        # Empty list should be converted to None
        assert my_protocol._protocol_definition.setup_instructions_json is None

