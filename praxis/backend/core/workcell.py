"""Live Workcell management.

This module defines the `Workcell` class, which serves as a dynamic, in-memory container
for live PyLabRobot objects such as machines and resources. It is designed to be
populated by the `WorkcellRuntime` with live asset instances acquired by the
`AssetManager`. The `Workcell` class manages the serialization and deserialization
of the runtime state of these assets for backups and recovery.

It also provides a `WorkcellView` class, which acts as a secure proxy for protocols,
allowing them to access only the assets they have explicitly declared as required.
"""

import json
from typing import TYPE_CHECKING, Any, cast

import inflection  # pyright: ignore[reportMissingImports]
from pylabrobot.legacy.machines.machine import Machine
from pylabrobot.resources import Deck, Resource

from praxis.backend.models import AssetRequirementModel, MachineCategoryEnum, ResourceCategoryEnum
from praxis.backend.utils.logging import get_logger

from .protocols.filesystem import IFileSystem
from .protocols.workcell import IWorkcell

if TYPE_CHECKING:
  from pylabrobot.legacy.liquid_handling.liquid_handler import LiquidHandler


logger = get_logger(__name__)


class Workcell(IWorkcell):
  """A dynamic, in-memory container for live PyLabRobot objects.

  This class is the runtime representation of a workcell. It is populated by the
  WorkcellRuntime with live asset instances (machines and resources) that have been
  acquired by the AssetManager. Its primary responsibilities are to hold these
  live objects and manage the serialization/deserialization of their runtime state
  for backups and recovery.

  It is configured dynamically based on the MachineCategoryEnum and ResourceCategoryEnum
  from the application's data models.
  """

  def __init__(
    self,
    name: str,
    save_file: str,
    file_system: IFileSystem,
    backup_interval: int = 60,
    num_backups: int = 3,
  ) -> None:
    """Initialize the live Workcell container.

    Args:
        name: The name of the workcell, corresponding to a Workcell entry.
        save_file: Path to the JSON file for saving runtime state.
        file_system: A file system object for file operations.
        backup_interval: Interval in seconds for continuous state backup.
        num_backups: Number of rolling backup files to maintain.

    Raises:
        ValueError: If save_file does not end with .json.

    """
    if not save_file.endswith(".json"):
      msg = "save_file must be a JSON file ending in .json"
      raise ValueError(msg)

    self.name = name
    self.save_file = save_file
    self.backup_interval = backup_interval
    self.num_backups = num_backups
    self.backup_num: int = 0
    self.fs: IFileSystem = file_system

    self.refs: dict[str, dict[str, Resource | Machine]] = {}
    self.children: list[Resource | Machine] = []

    for member in MachineCategoryEnum:
      attr_name = inflection.pluralize(member.name.lower())
      self.refs[attr_name] = {}
      setattr(self, attr_name, self.refs[attr_name])

    for member in ResourceCategoryEnum:
      attr_name = inflection.pluralize(member.name.lower())
      if attr_name not in self.refs:
        self.refs[attr_name] = {}
        setattr(self, attr_name, self.refs[attr_name])

    if "other_machines" not in self.refs:
      self.refs["other_machines"] = {}
      self.other_machines = self.refs["other_machines"]

  @property
  def all_machines(self) -> dict[str, Machine]:
    """Returns a dictionary of all live machine objects in the workcell."""
    all_machines_dict: dict[str, Machine] = {}
    for member in MachineCategoryEnum:
      attr_name = inflection.pluralize(member.name.lower())
      all_machines_dict.update(
        cast("dict[str, Machine]", self.refs.get(attr_name, {})),
      )
    all_machines_dict.update(
      cast("dict[str, Machine]", self.refs.get("other_machines", {})),
    )
    return all_machines_dict

  @property
  def asset_keys(self) -> list[str]:
    """Returns a list of all asset names (machines and resources)."""
    return [getattr(child, "name", str(child.__hash__())) for child in self.children]

  def add_asset(self, asset: Resource | Machine) -> None:
    """Add a single live asset object to the workcell container.

    This should be called by WorkcellRuntime when an asset is initialized.

    Args:
        asset: The live asset object to add. Must be a subclass of Resource or Machine.

    Raises:
        ValueError: If the asset is not a valid Resource or Machine subclass.
        Warning: If the asset has an unknown or unhandled category.

    """
    self.children.append(asset)
    category_str = getattr(asset, "category", None)

    if category_str:
      attr_name = inflection.pluralize(category_str.lower())
      if attr_name in self.refs:
        self.refs[attr_name][getattr(asset, "name", str(asset.__hash__()))] = asset
        return
    else:
      logger.warning(
        "Live Workcell: Asset '%s' has unknown or unhandled category '%s'",
        getattr(asset, "name", str(asset.__hash__())),
        category_str,
      )

  def get_all_children(self) -> list[Resource | Machine]:
    """Recursively get all children of this asset container."""
    children = self.children.copy()
    for child in self.children:
      if isinstance(child, Resource):
        children.extend(child.get_all_children())
    return children

  def specify_deck(self, liquid_handler_accession_id: str, deck: Deck) -> None:
    """Assign a deck resource to a specific liquid handler."""
    if (
      "liquid_handlers" in self.refs and liquid_handler_accession_id in self.refs["liquid_handlers"]
    ):
      liquid_handler = cast(
        "LiquidHandler",
        self.refs["liquid_handlers"][liquid_handler_accession_id],
      )
      liquid_handler.deck = deck
    else:
      msg = f"Liquid handler '{liquid_handler_accession_id}' not found."
      raise KeyError(msg)

  def serialize_all_state(self) -> dict[str, Any]:
    """Serialize the state of all resources within the workcell."""
    state: dict[str, Any] = {}
    for child in self.get_all_children():
      if isinstance(child, Resource):
        state[child.name] = child.serialize_state()
    return state

  def load_all_state(self, state: dict[str, Any]) -> None:
    """Load the state for all resources from a dictionary."""
    for child in self.get_all_children():
      if isinstance(child, Resource) and child.name in state:
        child.load_state(state[child.name])

  def save_state_to_file(self, fn: str, indent: int | None = 4) -> None:
    """Save the current state of all workcell resources to a JSON file."""
    with self.fs.open(fn, "w", encoding="utf-8") as f:
      json.dump(self.serialize_all_state(), f, indent=indent)

  def load_state_from_file(self, fn: str) -> None:
    """Load the state of all workcell resources from a JSON file."""
    with self.fs.open(fn, encoding="utf-8") as f:
      content = json.load(f)
    self.load_all_state(content)

  def __contains__(self, item: str) -> bool:
    """Check if an asset with the given name exists in the workcell."""
    return item in self.asset_keys

  def __getitem__(self, key: str) -> dict[str, Resource | Machine]:
    """Get the asset category by name."""
    if key in self.refs:
      return self.refs[key]
    msg = f"'{key}' is not a valid asset category."
    raise KeyError(msg)


class WorkcellView:
  """A protocol's sandboxed view into a shared workcell.

  This class acts as a secure proxy, providing access ONLY to the assets that
  were explicitly acquired for a given protocol run. It prevents a protocol
  from accidentally accessing or modifying other active assets.
  """

  def __init__(
    self,
    parent_workcell: "Workcell",
    protocol_name: str,
    required_assets: list[AssetRequirementModel],
  ) -> None:
    """Initialize the protocol view with required assets."""
    self.parent = parent_workcell
    self.protocol_name = protocol_name
    self._required_asset_names: set[str] = {asset.name for asset in required_assets}

  def __contains__(self, asset_name: str) -> bool:
    """Check if an asset was declared as required by the protocol."""
    return asset_name in self._required_asset_names

  def __getattr__(self, name: str) -> "Resource | Machine":
    """Delegate attribute access to the parent workcell for required assets."""
    if name.startswith("_"):
      # Allow access to private attributes of the view itself
      return self.__dict__[name]

    # Enforce that protocols can only access assets they have declared.
    if name not in self._required_asset_names:
      msg = (
        f"Protocol '{self.protocol_name}' attempted to access asset '{name}' "
        "but did not declare it as a requirement."
      )
      raise AttributeError(
        msg,
      )

    # Safely delegate the attribute access to the parent Workcell
    return getattr(self.parent, name)
