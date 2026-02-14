"""Custom exceptions and logging utility for Praxis backend."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
  from uuid import UUID


class PraxisError(Exception):
  """Base exception for all custom Praxis backend errors.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the PraxisError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class InvalidWellSetsError(PraxisError):
  """Raised when source and destination well sets are not linked by index."""


class OrchestratorError(Exception):
  """Exception raised for errors in the orchestrator service.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the OrchestratorError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class DataError(Exception):
  """Exception raised for errors during data operations (e.g., database interactions).

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the DataError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class ModelError(Exception):
  """Exception raised for data models errors (e.g., validation, serialization).

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the ModelError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class AssetAcquisitionError(RuntimeError):
  """Exception raised when there is an issue acquiring or assigning assets.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the AssetAcquisitionError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class AssetReleaseError(RuntimeError):
  """Exception raised when there is an issue releasing or returning assets.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the AssetReleaseError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class ProtocolCancelledError(Exception):
  """Exception raised when a protocol run is explicitly cancelled.

  Attributes:
    message (str): The cancellation message.

  """

  def __init__(self, message: str = "Protocol run was cancelled.") -> None:
    """Initialize a new instance of the ProtocolCancelledError.

    Args:
      message (str): The detailed cancellation message.
        Defaults to "Protocol run was cancelled.".

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class WorkcellRuntimeError(Exception):
  """Exception raised for errors specific to the WorkcellRuntime.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the WorkcellRuntimeError.

    Args:
      message (str): The detailed error message.

    """
    self.message = message
    super().__init__(self.message)

  def __str__(self) -> str:
    """Return the string representation of the error."""
    return f"{self.message}"


class PylabRobotError(PraxisError):
  """Base exception for PyLabRobot-related errors within Praxis."""

  def __init__(self, message: str, original_plr_exception: Exception | None = None) -> None:
    """Initialize a new instance of the PylabRobotError.

    Args:
      message (str): The detailed error message.
      original_plr_exception (Exception | None): The original PyLabRobot exception, if
      any.

    """
    super().__init__(message)
    self.original_plr_exception = original_plr_exception


class AccessionNotFoundError(PraxisError, ValueError):
  """Raised when an entity is not found during accession lookup."""

  def __init__(self, entity_type: str, accession: str | UUID) -> None:
    """Initialize the exception.

    Args:
        entity_type: The type of entity being looked up (e.g., "ProtocolRun")
        accession: The accession ID that was not found

    """
    self.entity_type = entity_type
    self.accession = accession
    super().__init__(f"{entity_type} with accession '{accession}' not found.")


class PyLabRobotVolumeError(PylabRobotError):
  """Specific error for PyLabRobot 'TooLittleLiquidError' scenarios."""

  def __init__(
    self,
    message="Too little liquid for transfer.",
    details=None,
    original_plr_exception: Exception | None = None,
  ) -> None:
    """Initialize a new instance of the PyLabRobotVolumeRelatedError.

    Args:
      message (str): The detailed error message.
      details (dict[str, Any] | None): Additional details about the error.
      original_plr_exception (Exception | None): The original PyLabRobot exception, if
        any.

    """
    super().__init__(message, original_plr_exception)
    self.details = details or {}


class PyLabRobotGenericError(PylabRobotError):
  """Generic placeholder for other PyLabRobot errors."""

  def __init__(
    self,
    message="A PyLabRobot operation failed.",
    original_plr_exception: Exception | None = None,
  ) -> None:
    """Initialize a new instance of the PyLabRobotGenericError."""
    super().__init__(message, original_plr_exception)


class PraxisAPIError(PraxisError):
  """Base exception for errors in the Praxis API.

  Attributes:
    message (str): The error message.

  """

  def __init__(self, message: str) -> None:
    """Initialize a new instance of the PraxisAPIError.

    Args:
      message (str): The detailed error message.

    """
    super().__init__(message)
