"""Workcell Protocol."""

from typing import Any, Protocol, runtime_checkable

from pylabrobot.legacy.machines.machine import Machine
from pylabrobot.resources.resource import Resource


@runtime_checkable
class IWorkcell(Protocol):
  """A protocol for a workcell."""

  name: str
  save_file: str
  backup_interval: int
  num_backups: int
  backup_num: int

  def add_asset(self, asset: Resource | Machine) -> None:
    """Add a single live asset object to the workcell container."""
    ...

  def serialize_all_state(self) -> dict[str, Any]:
    """Serialize the state of all resources within the workcell."""
    ...

  def load_all_state(self, state: dict[str, Any]) -> None:
    """Load the state for all resources from a dictionary."""
    ...

  def save_state_to_file(self, fn: str, indent: int | None = 4) -> None:
    """Save the current state of all workcell resources to a JSON file."""
    ...
