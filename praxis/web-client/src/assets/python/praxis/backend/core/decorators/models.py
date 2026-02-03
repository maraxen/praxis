"""Browser-compatible stub for praxis.backend.core.decorators.models.

This module provides minimal implementations of the types that cloudpickle
needs when deserializing protocol functions in the Pyodide environment.
Only the types actually referenced in the pickle are stubbed.
"""

from dataclasses import dataclass
from typing import Any, Callable, Optional
import uuid


@dataclass
class DataViewDefinition:
    """Stub for DataViewDefinition."""
    name: str
    description: Optional[str] = None
    source_type: str = "function_output"
    source_filter: Optional[dict] = None
    schema: Optional[dict] = None
    required: bool = False
    default_value: Any = None


@dataclass
class SetupInstruction:
    """Stub for SetupInstruction."""
    message: str
    severity: str = "required"
    position: Optional[str] = None
    resource_type: Optional[str] = None


class ProtocolRuntimeInfo:
    """Stub for ProtocolRuntimeInfo.

    This is the key class that holds protocol metadata attached to decorated functions.
    In the browser, we only need it to exist so cloudpickle can reconstruct the object.
    """

    def __init__(
        self,
        pydantic_definition: Any,
        function_ref: Callable,
        found_state_param_details: Optional[dict] = None,
    ) -> None:
        self.pydantic_definition = pydantic_definition
        self.function_ref = function_ref
        self.callable_wrapper: Optional[Callable] = None
        self.db_accession_id: Optional[uuid.UUID] = None
        self.found_state_param_details = found_state_param_details


def get_callable_fqn(func: Callable) -> str:
    """Get the fully qualified name of a callable function."""
    return f"{func.__module__}.{func.__qualname__}"


# Exported names that cloudpickle may reference
__all__ = [
    "DataViewDefinition",
    "SetupInstruction",
    "ProtocolRuntimeInfo",
    "get_callable_fqn",
]
