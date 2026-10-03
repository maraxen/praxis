"""Resource hierarchy registry for PLR resource parent-child relationships.

This module provides a static registry that maps PyLabRobot resource types
to their parent types, enabling automatic inference of deck layout requirements
from protocol parameter types.

Two deck layout strategies are supported:
- Carrier-based (Hamilton STAR): Resources sit on carriers, carriers sit on deck
- Slot-based (Opentrons): Resources sit directly on deck slots
"""

from enum import Enum

from pydantic import BaseModel, Field

# =============================================================================
# Enums and Constants
# =============================================================================


class DeckLayoutType(str, Enum):
  """Type of deck layout strategy."""

  SLOT_BASED = "slot_based"  # OT-2: resources go directly on slots
  CARRIER_BASED = "carrier_based"  # Hamilton: resources need carriers


class ResourceCategory(str, Enum):
  """Category of PLR resource for hierarchy purposes."""

  # Sub-resource elements (children of containers)
  WELL = "well"  # Child of Plate/Trough
  TIP_SPOT = "tip_spot"  # Child of TipRack
  TUBE = "tube"  # Child of TubeRack
  CARRIER_SITE = "carrier_site"  # Child of Carrier

  # Containers (hold sub-resources)
  PLATE = "plate"
  TIP_RACK = "tip_rack"
  TROUGH = "trough"
  TUBE_RACK = "tube_rack"
  CONTAINER = "container"  # Generic container
  LID = "lid"

  # Carriers (hold containers on carrier-based decks)
  PLATE_CARRIER = "plate_carrier"
  TIP_CARRIER = "tip_carrier"
  TROUGH_CARRIER = "trough_carrier"
  CARRIER = "carrier"  # Generic carrier

  # Infrastructure
  SLOT = "slot"  # Slot on slot-based deck
  DECK = "deck"
  RESOURCE = "resource"  # Generic/unknown


# =============================================================================
# Hierarchy Mappings
# =============================================================================

# Map resource type names to their categories
TYPE_TO_CATEGORY: dict[str, ResourceCategory] = {
  # Sub-resources
  "Well": ResourceCategory.WELL,
  "TipSpot": ResourceCategory.TIP_SPOT,
  "Spot": ResourceCategory.CARRIER_SITE,
  "Tube": ResourceCategory.TUBE,
  "CarrierSite": ResourceCategory.CARRIER_SITE,
  # Containers
  "Plate": ResourceCategory.PLATE,
  "TipRack": ResourceCategory.TIP_RACK,
  "Trough": ResourceCategory.TROUGH,
  "TubeRack": ResourceCategory.TUBE_RACK,
  "Container": ResourceCategory.CONTAINER,
  "Lid": ResourceCategory.LID,
  # Carriers
  "PlateCarrier": ResourceCategory.PLATE_CARRIER,
  "TipCarrier": ResourceCategory.TIP_CARRIER,
  "TroughCarrier": ResourceCategory.TROUGH_CARRIER,
  "Carrier": ResourceCategory.CARRIER,
  # Infrastructure
  "Slot": ResourceCategory.SLOT,
  "Deck": ResourceCategory.DECK,
  "Resource": ResourceCategory.RESOURCE,
}

# Direct parent relationships (child category -> parent category)
DIRECT_PARENT: dict[ResourceCategory, ResourceCategory] = {
  ResourceCategory.WELL: ResourceCategory.PLATE,
  ResourceCategory.TIP_SPOT: ResourceCategory.TIP_RACK,
  ResourceCategory.TUBE: ResourceCategory.TUBE_RACK,
  ResourceCategory.CARRIER_SITE: ResourceCategory.CARRIER,
}

# Carrier mappings for carrier-based decks (container -> carrier type)
CARRIER_FOR_CONTAINER: dict[ResourceCategory, ResourceCategory] = {
  ResourceCategory.PLATE: ResourceCategory.PLATE_CARRIER,
  ResourceCategory.TIP_RACK: ResourceCategory.TIP_CARRIER,
  ResourceCategory.TROUGH: ResourceCategory.TROUGH_CARRIER,
  ResourceCategory.TUBE_RACK: ResourceCategory.CARRIER,  # Usually generic carrier
  ResourceCategory.CONTAINER: ResourceCategory.CARRIER,
  ResourceCategory.LID: ResourceCategory.PLATE_CARRIER,  # Lids typically on plates/plate carriers
}

# Containers that can go directly on slots (slot-based decks)
SLOT_COMPATIBLE: frozenset[ResourceCategory] = frozenset({
  ResourceCategory.PLATE,
  ResourceCategory.TIP_RACK,
  ResourceCategory.TROUGH,
  ResourceCategory.TUBE_RACK,
  ResourceCategory.CONTAINER,
  ResourceCategory.LID,
})

# All carrier types
CARRIER_TYPES: frozenset[ResourceCategory] = frozenset({
  ResourceCategory.PLATE_CARRIER,
  ResourceCategory.TIP_CARRIER,
  ResourceCategory.TROUGH_CARRIER,
  ResourceCategory.CARRIER,
})

# Deck type detection patterns (class name patterns)
SLOT_BASED_DECK_PATTERNS: frozenset[str] = frozenset({
  "otdeck",
  "opentrons",
  "ot-2",
  "ot2",
  "flex",  # Opentrons Flex
})

CARRIER_BASED_DECK_PATTERNS: frozenset[str] = frozenset({
  "hamilton",
  "star",
  "nimbus",
  "vantage",
  "tecan",
  "beckman",
})


# =============================================================================
# Pydantic Models
# =============================================================================


class ParentalChain(BaseModel):
  """A parental chain from a resource type up to the deck."""

  resource_type: str = Field(description="Starting resource type name")
  chain: list[str] = Field(
    default_factory=list,
    description="Parent types from resource to deck (not including the resource itself)",
  )
  deck_layout_type: DeckLayoutType = Field(
    default=DeckLayoutType.CARRIER_BASED,
    description="Deck layout type used for this chain",
  )

  @property
  def requires_carrier(self) -> bool:
    """Check if this chain requires a carrier."""
    return any(
      cat.value in self.chain
      for cat in CARRIER_TYPES
      if hasattr(cat, "value") and cat.value in [c.lower() for c in self.chain]
    ) or any("Carrier" in p for p in self.chain)

  @property
  def immediate_parent(self) -> str | None:
    """Get the immediate parent type."""
    return self.chain[0] if self.chain else None


class ResourceRequirement(BaseModel):
  """A resource requirement inferred from a protocol parameter."""

  variable_name: str = Field(description="Parameter/variable name in protocol")
  resource_type: str = Field(description="Declared resource type")
  element_type: str | None = Field(
    default=None,
    description="For containers like list[Well], the element type",
  )
  is_container: bool = Field(
    default=False,
    description="Whether this is a container type (list, Sequence, etc.)",
  )
  parental_chain: ParentalChain | None = Field(
    default=None,
    description="Full parental chain to deck",
  )
  required_on_deck: bool = Field(
    default=True,
    description="Whether this resource must be on deck before execution",
  )


# =============================================================================
# Registry Class
# =============================================================================


class ResourceHierarchyRegistry:
  """Registry of PLR resource parent-child relationships.

  This registry provides methods to:
  1. Get the parental chain for any resource type
  2. Determine deck layout requirements
  3. Map resource types to their categories

  Example usage:
      registry = ResourceHierarchyRegistry()

      # Get parental chain for a Well on Hamilton deck
      chain = registry.get_parental_chain("Well", DeckLayoutType.CARRIER_BASED)
      # Returns: ["Plate", "PlateCarrier", "Deck"]

      # Get parental chain for a Plate on OT-2
      chain = registry.get_parental_chain("Plate", DeckLayoutType.SLOT_BASED)
      # Returns: ["Slot", "Deck"]

  """

  def __init__(self) -> None:
    """Initialize the registry."""
    self._type_to_category = TYPE_TO_CATEGORY.copy()

  def get_category(self, resource_type: str) -> ResourceCategory:
    """Get the category for a resource type.

    Args:
        resource_type: The resource type name (e.g., "Well", "Plate").

    Returns:
        The ResourceCategory for this type.

    """
    return self._type_to_category.get(resource_type, ResourceCategory.RESOURCE)

  def get_parental_chain(
    self,
    resource_type: str,
    deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
  ) -> ParentalChain:
    """Get the full parental chain from a resource type to the deck.

    Args:
        resource_type: The starting resource type name.
        deck_layout_type: The type of deck layout (slot or carrier based).

    Returns:
        ParentalChain with the full hierarchy.

    Example:
        For "Well" on carrier-based deck:
            Well -> Plate -> PlateCarrier -> Deck
            Returns chain: ["Plate", "PlateCarrier", "Deck"]

        For "Well" on slot-based deck:
            Well -> Plate -> Slot -> Deck
            Returns chain: ["Plate", "Slot", "Deck"]

    """
    chain: list[str] = []
    current_type = resource_type
    current_category = self.get_category(current_type)

    # Step 1: Handle sub-resource to container (Well -> Plate)
    if current_category in DIRECT_PARENT:
      parent_category = DIRECT_PARENT[current_category]
      parent_type = self._category_to_type_name(parent_category)
      chain.append(parent_type)
      current_category = parent_category

    # Step 2: Handle container to carrier/slot
    if current_category in SLOT_COMPATIBLE:
      if deck_layout_type == DeckLayoutType.CARRIER_BASED:
        # Container -> Carrier -> Deck
        if current_category in CARRIER_FOR_CONTAINER:
          carrier_category = CARRIER_FOR_CONTAINER[current_category]
          carrier_type = self._category_to_type_name(carrier_category)
          chain.append(carrier_type)
        chain.append("Deck")
      else:
        # Container -> Slot -> Deck (slot-based)
        chain.append("Slot")
        chain.append("Deck")
    elif current_category in CARRIER_TYPES:
      # Carrier -> Deck
      chain.append("Deck")
    elif current_category == ResourceCategory.SLOT:
      # Slot -> Deck
      chain.append("Deck")

    return ParentalChain(
      resource_type=resource_type,
      chain=chain,
      deck_layout_type=deck_layout_type,
    )

  def get_immediate_parent_type(
    self,
    resource_type: str,
    deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
  ) -> str | None:
    """Get the immediate parent type for a resource.

    Args:
        resource_type: The resource type name.
        deck_layout_type: The deck layout type.

    Returns:
        The immediate parent type name, or None if this is a top-level type.

    """
    chain = self.get_parental_chain(resource_type, deck_layout_type)
    return chain.immediate_parent

  def infer_deck_type(self, deck_class_name: str) -> DeckLayoutType:
    """Infer deck layout type from a deck class name.

    Args:
        deck_class_name: The class name of the deck.

    Returns:
        The inferred DeckLayoutType.

    """
    lower_name = deck_class_name.lower()

    # Check for slot-based patterns
    for pattern in SLOT_BASED_DECK_PATTERNS:
      if pattern in lower_name:
        return DeckLayoutType.SLOT_BASED

    # Check for carrier-based patterns
    for pattern in CARRIER_BASED_DECK_PATTERNS:
      if pattern in lower_name:
        return DeckLayoutType.CARRIER_BASED

    # Default to carrier-based (more common in lab automation)
    return DeckLayoutType.CARRIER_BASED

  def is_sub_resource(self, resource_type: str) -> bool:
    """Check if a resource type is a sub-resource (Well, TipSpot, etc.).

    Args:
        resource_type: The resource type name.

    Returns:
        True if this is a sub-resource type.

    """
    category = self.get_category(resource_type)
    return category in DIRECT_PARENT

  def is_carrier(self, resource_type: str) -> bool:
    """Check if a resource type is a carrier.

    Args:
        resource_type: The resource type name.

    Returns:
        True if this is a carrier type.

    """
    category = self.get_category(resource_type)
    return category in CARRIER_TYPES

  def is_container(self, resource_type: str) -> bool:
    """Check if a resource type is a container (Plate, TipRack, etc.).

    Args:
        resource_type: The resource type name.

    Returns:
        True if this is a container type.

    """
    category = self.get_category(resource_type)
    return category in SLOT_COMPATIBLE

  def get_child_element_type(self, container_type: str) -> str | None:
    """Get the expected child element type for a container.

    Args:
        container_type: The container type name.

    Returns:
        The child element type name, or None if not a container.

    """
    category = self.get_category(container_type)

    # Reverse lookup in DIRECT_PARENT
    for child_cat, parent_cat in DIRECT_PARENT.items():
      if parent_cat == category:
        return self._category_to_type_name(child_cat)

    return None

  def register_type(self, type_name: str, category: ResourceCategory) -> None:
    """Register a custom resource type.

    Args:
        type_name: The type name to register.
        category: The category for this type.

    """
    self._type_to_category[type_name] = category

  def _category_to_type_name(self, category: ResourceCategory) -> str:
    """Convert a category to its canonical type name.

    Args:
        category: The resource category.

    Returns:
        The canonical type name for this category.

    """
    # Map categories back to their canonical type names
    category_to_name: dict[ResourceCategory, str] = {
      ResourceCategory.WELL: "Well",
      ResourceCategory.TIP_SPOT: "TipSpot",
      ResourceCategory.TUBE: "Tube",
      ResourceCategory.CARRIER_SITE: "CarrierSite",
      ResourceCategory.PLATE: "Plate",
      ResourceCategory.TIP_RACK: "TipRack",
      ResourceCategory.TROUGH: "Trough",
      ResourceCategory.TUBE_RACK: "TubeRack",
      ResourceCategory.CONTAINER: "Container",
      ResourceCategory.LID: "Lid",
      ResourceCategory.PLATE_CARRIER: "PlateCarrier",
      ResourceCategory.TIP_CARRIER: "TipCarrier",
      ResourceCategory.TROUGH_CARRIER: "TroughCarrier",
      ResourceCategory.CARRIER: "Carrier",
      ResourceCategory.SLOT: "Slot",
      ResourceCategory.DECK: "Deck",
      ResourceCategory.RESOURCE: "Resource",
    }
    return category_to_name.get(category, "Resource")


# =============================================================================
# Module-level singleton
# =============================================================================

_registry: ResourceHierarchyRegistry | None = None


def get_registry() -> ResourceHierarchyRegistry:
  """Get the global resource hierarchy registry singleton.

  Returns:
      The global ResourceHierarchyRegistry instance.

  """
  global _registry
  if _registry is None:
    _registry = ResourceHierarchyRegistry()
  return _registry


def get_parental_chain(
  resource_type: str,
  deck_layout_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED,
) -> ParentalChain:
  """Convenience function to get parental chain using global registry.

  Args:
      resource_type: The resource type name.
      deck_layout_type: The deck layout type.

  Returns:
      The parental chain for this resource type.

  """
  return get_registry().get_parental_chain(resource_type, deck_layout_type)


def infer_deck_type(deck_class_name: str) -> DeckLayoutType:
  """Convenience function to infer deck type using global registry.

  Args:
      deck_class_name: The deck class name.

  Returns:
      The inferred deck layout type.

  """
  return get_registry().infer_deck_type(deck_class_name)
