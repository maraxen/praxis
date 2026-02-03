"""Browser-compatible stub for praxis.backend.models.domain.protocol.

This module provides minimal implementations of the Pydantic models that
cloudpickle needs when deserializing protocol functions in Pyodide.
The actual SQLModel/SQLAlchemy functionality is not needed - just the
data structures that get attached to protocol functions.
"""

from dataclasses import dataclass, field
from typing import Any, Optional, List
import uuid
from datetime import datetime


# Stub for the enum used in protocol definitions
class FunctionCallStatusEnum:
    """Stub for FunctionCallStatusEnum."""
    UNKNOWN = "UNKNOWN"
    SUCCESS = "SUCCESS"
    ERROR = "ERROR"
    RUNNING = "RUNNING"


class ProtocolRunStatusEnum:
    """Stub for ProtocolRunStatusEnum."""
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"
    PAUSED = "PAUSED"
    PAUSING = "PAUSING"
    RESUMING = "RESUMING"
    INTERVENING = "INTERVENING"
    CANCELING = "CANCELING"


@dataclass
class AssetConstraintsModel:
    """Stub for AssetConstraintsModel."""
    min_volume_ul: Optional[float] = None
    max_volume_ul: Optional[float] = None
    dead_volume_ul: Optional[float] = None
    min_quantity: Optional[int] = None
    max_quantity: Optional[int] = None
    allow_partial: Optional[bool] = None


@dataclass
class LocationConstraintsModel:
    """Stub for LocationConstraintsModel."""
    allowed_decks: Optional[List[str]] = None
    allowed_slots: Optional[List[str]] = None
    required_capabilities: Optional[dict] = None


@dataclass
class ParameterConstraintsModel:
    """Stub for ParameterConstraintsModel."""
    min_value: Optional[float] = None
    max_value: Optional[float] = None
    allowed_values: Optional[List[Any]] = None
    regex: Optional[str] = None


class ParameterMetadataModel:
    """Stub for ParameterMetadataModel."""
    name: str
    type_hint: str = ""
    fqn: Optional[str] = None
    description: Optional[str] = None
    optional: bool = False
    default_value_repr: Any = None
    default_value: Any = None
    constraints: Any = None
    ui_hint: Optional[dict] = None
    linked_to: Optional[str] = None
    is_deck_param: bool = False


@dataclass
class DataViewMetadataModel:
    """Stub for DataViewMetadataModel."""
    name: str
    description: Optional[str] = None
    source_type: str = "function_output"
    source_filter_json: Optional[dict] = None
    data_schema_json: Optional[dict] = None
    required: bool = False
    default_value_json: Any = None


@dataclass
class AssetRequirementCreate:
    """Stub for AssetRequirementCreate."""
    name: str = ""
    type_hint_str: str = ""
    fqn: Optional[str] = ""
    actual_type_str: Optional[str] = ""
    optional: bool = False
    default_value_repr: Optional[str] = None
    description: Optional[str] = None
    required_plr_category: Optional[str] = None
    protocol_definition_accession_id: Optional[uuid.UUID] = None


@dataclass
class FunctionProtocolDefinitionCreate:
    """Stub for FunctionProtocolDefinitionCreate.

    This is the main Pydantic model attached to protocol functions by the decorator.
    """
    fqn: str = ""
    name: str = ""
    version: str = "0.1.0"
    description: Optional[str] = None
    source_file_path: str = ""
    module_name: str = ""
    function_name: str = ""
    is_top_level: bool = False
    solo_execution: bool = False
    preconfigure_deck: bool = False
    requires_deck: bool = True
    deck_param_name: Optional[str] = None
    deck_construction_function_fqn: Optional[str] = None
    deck_layout_path: Optional[str] = None
    state_param_name: Optional[str] = None
    requires_linked_indices: bool = False
    category: Optional[str] = None
    deprecated: bool = False
    source_hash: Optional[str] = None
    graph_cached_at: Optional[datetime] = None
    simulation_version: Optional[str] = None
    simulation_cached_at: Optional[datetime] = None
    bytecode_python_version: Optional[str] = None
    bytecode_cache_version: Optional[str] = None
    bytecode_cached_at: Optional[datetime] = None
    commit_hash: Optional[str] = None
    accession_id: Optional[uuid.UUID] = None
    tags: Any = None
    parameters: Optional[List[ParameterMetadataModel]] = None
    assets: Optional[List[AssetRequirementCreate]] = None
    data_views: Optional[List[DataViewMetadataModel]] = None
    setup_instructions_json: Optional[List[dict]] = None
    source_repository_name: Optional[str] = None
    file_system_source_name: Optional[str] = None


# Exported names
__all__ = [
    "FunctionCallStatusEnum",
    "ProtocolRunStatusEnum",
    "AssetConstraintsModel",
    "LocationConstraintsModel",
    "ParameterConstraintsModel",
    "ParameterMetadataModel",
    "DataViewMetadataModel",
    "AssetRequirementCreate",
    "FunctionProtocolDefinitionCreate",
]

