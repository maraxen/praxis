"""Precondition resolver for protocol computation graphs.

This module provides a service that resolves protocol preconditions against
the current deck state and available assets, generating deck configuration
recommendations for unmet requirements.

The resolver handles:
- Resource placement preconditions (resource must be on deck)
- State preconditions (tips loaded, temperature stable, etc.)
- Idempotency (already-satisfied preconditions are skipped)
- Asset matching (finding suitable resources from inventory)
"""

from typing import Any

from pydantic import BaseModel, Field

from praxis.backend.core.deck_config import DeckLayoutConfig, ResourcePlacement
from praxis.backend.utils.plr_static_analysis.models import (
  PreconditionType,
  ProtocolComputationGraph,
  ResourceNode,
  StatePrecondition,
)
from praxis.backend.utils.plr_static_analysis.resource_hierarchy import (
  DeckLayoutType,
  get_parental_chain,
  get_registry,
)

# =============================================================================
# Result Models
# =============================================================================


class PreconditionStatus(BaseModel):
  """Status of a single precondition."""

  precondition_id: str
  precondition_type: PreconditionType
  resource_variable: str
  status: str = Field(
    description="Status: 'satisfied', 'auto_satisfiable', 'needs_user_input', 'unresolvable'"
  )
  satisfied_by: str | None = Field(
    default=None, description="What satisfies this (operation ID or existing state)"
  )
  suggested_action: str | None = Field(
    default=None, description="Suggested action for user"
  )
  candidate_assets: list[str] = Field(
    default_factory=list, description="Asset IDs that could satisfy this"
  )


class ResolutionResult(BaseModel):
  """Result of resolving preconditions against current state."""

  can_execute: bool = Field(
    description="Whether all preconditions can be satisfied (potentially with user action)"
  )
  requires_user_input: bool = Field(
    default=False, description="Whether user input is needed"
  )

  # Precondition breakdown
  satisfied: list[PreconditionStatus] = Field(
    default_factory=list, description="Already satisfied preconditions"
  )
  auto_satisfiable: list[PreconditionStatus] = Field(
    default_factory=list, description="System can auto-satisfy these"
  )
  needs_user_input: list[PreconditionStatus] = Field(
    default_factory=list, description="User must select/configure these"
  )
  unresolvable: list[PreconditionStatus] = Field(
    default_factory=list, description="Cannot be resolved"
  )

  # Generated configurations
  deck_config: DeckLayoutConfig | None = Field(
    default=None, description="Recommended deck configuration"
  )
  suggested_placements: list[ResourcePlacement] = Field(
    default_factory=list, description="Suggested resource placements"
  )

  # Summary
  total_preconditions: int = 0
  summary: str = ""


class AssetMatch(BaseModel):
  """A potential asset match for a resource requirement."""

  asset_id: str
  asset_name: str
  asset_type: str
  asset_fqn: str
  match_score: float = Field(
    default=1.0, description="How well this asset matches (1.0 = perfect)"
  )
  match_reasons: list[str] = Field(
    default_factory=list, description="Why this is a match"
  )


# =============================================================================
# Deck State Model
# =============================================================================


class DeckState(BaseModel):
  """Represents the current state of a deck for resolution."""

  deck_type: DeckLayoutType = DeckLayoutType.CARRIER_BASED
  deck_fqn: str | None = None

  # Resources currently on deck (name -> type)
  placed_resources: dict[str, str] = Field(default_factory=dict)

  # Active states (e.g., "tips_loaded")
  active_states: set[str] = Field(default_factory=set)

  # Resource positions (name -> slot/position)
  resource_positions: dict[str, str] = Field(default_factory=dict)


# =============================================================================
# Precondition Resolver
# =============================================================================


class PreconditionResolver:
  """Resolves protocol preconditions against current deck state.

  This service analyzes a protocol's computation graph and determines
  what actions are needed to satisfy all preconditions before execution.

  Usage:
      resolver = PreconditionResolver()

      # With current deck state
      result = resolver.resolve(
          graph=protocol_graph,
          deck_state=current_deck_state,
          available_assets=asset_list,
      )

      if result.can_execute:
          # Apply result.deck_config or result.suggested_placements
          pass
      else:
          # Show result.unresolvable to user
          pass

  """

  def __init__(self) -> None:
    """Initialize the resolver."""
    self._registry = get_registry()

  def resolve(
    self,
    graph: ProtocolComputationGraph,
    deck_state: DeckState | None = None,
    available_assets: list[dict[str, Any]] | None = None,
  ) -> ResolutionResult:
    """Resolve all preconditions in a computation graph.

    Args:
        graph: The protocol computation graph to resolve.
        deck_state: Current deck state (None = empty deck).
        available_assets: List of available assets (from inventory).

    Returns:
        ResolutionResult with resolution status and recommendations.

    """
    if deck_state is None:
      deck_state = DeckState()

    if available_assets is None:
      available_assets = []

    result = ResolutionResult(
      can_execute=True,
      total_preconditions=len(graph.preconditions),
    )

    # Process each precondition
    for precond in graph.preconditions:
      status = self._resolve_single_precondition(
        precond, graph, deck_state, available_assets
      )

      if status.status == "satisfied":
        result.satisfied.append(status)
      elif status.status == "auto_satisfiable":
        result.auto_satisfiable.append(status)
      elif status.status == "needs_user_input":
        result.needs_user_input.append(status)
        result.requires_user_input = True
      else:  # unresolvable
        result.unresolvable.append(status)
        result.can_execute = False

    # Generate deck configuration if needed
    if result.auto_satisfiable or result.needs_user_input:
      result.deck_config = self._generate_deck_config(
        graph, deck_state, result.auto_satisfiable + result.needs_user_input
      )
      result.suggested_placements = result.deck_config.placements if result.deck_config else []

    # Generate summary
    result.summary = self._generate_summary(result)

    return result

  def _resolve_single_precondition(
    self,
    precond: StatePrecondition,
    graph: ProtocolComputationGraph,
    deck_state: DeckState,
    available_assets: list[dict[str, Any]],
  ) -> PreconditionStatus:
    """Resolve a single precondition.

    Args:
        precond: The precondition to resolve.
        graph: The computation graph for context.
        deck_state: Current deck state.
        available_assets: Available assets.

    Returns:
        PreconditionStatus indicating resolution status.

    """
    status = PreconditionStatus(
      precondition_id=precond.id,
      precondition_type=precond.precondition_type,
      resource_variable=precond.resource_variable,
      status="unresolvable",
    )

    # Check based on precondition type
    if precond.precondition_type == PreconditionType.RESOURCE_ON_DECK:
      return self._resolve_resource_on_deck(
        precond, graph, deck_state, available_assets, status
      )

    if precond.precondition_type == PreconditionType.TIPS_LOADED:
      return self._resolve_tips_loaded(precond, graph, deck_state, status)

    if precond.precondition_type == PreconditionType.PLATE_ACCESSIBLE:
      return self._resolve_plate_accessible(precond, graph, deck_state, status)

    if precond.precondition_type == PreconditionType.MACHINE_READY:
      # Machine readiness is typically auto-satisfied by the system
      status.status = "auto_satisfiable"
      status.suggested_action = f"Initialize {precond.resource_variable}"
      return status

    # Default: can't resolve
    status.suggested_action = f"Unknown precondition type: {precond.precondition_type}"
    return status

  def _resolve_resource_on_deck(
    self,
    precond: StatePrecondition,
    graph: ProtocolComputationGraph,
    deck_state: DeckState,
    available_assets: list[dict[str, Any]],
    status: PreconditionStatus,
  ) -> PreconditionStatus:
    """Resolve a resource_on_deck precondition."""
    var_name = precond.resource_variable
    resource = graph.resources.get(var_name)

    if not resource:
      status.status = "unresolvable"
      status.suggested_action = f"Resource '{var_name}' not found in protocol"
      return status

    # Check if already on deck
    if var_name in deck_state.placed_resources:
      status.status = "satisfied"
      status.satisfied_by = "existing_placement"
      return status

    # Look for matching assets
    matches = self._find_matching_assets(resource, available_assets)

    if matches:
      status.status = "needs_user_input" if len(matches) > 1 else "auto_satisfiable"
      status.candidate_assets = [m.asset_id for m in matches]
      status.suggested_action = (
        f"Place {resource.declared_type} on deck"
        if len(matches) == 1
        else f"Select one of {len(matches)} available {resource.declared_type}(s)"
      )
      return status

    # No matches but could still be satisfiable if user provides
    status.status = "needs_user_input"
    status.suggested_action = f"Provide or select a {resource.declared_type} for '{var_name}'"
    return status

  def _resolve_tips_loaded(
    self,
    precond: StatePrecondition,
    graph: ProtocolComputationGraph,
    deck_state: DeckState,
    status: PreconditionStatus,
  ) -> PreconditionStatus:
    """Resolve a tips_loaded precondition."""
    # Check if tips are already loaded
    if "tips_loaded" in deck_state.active_states:
      status.status = "satisfied"
      status.satisfied_by = "existing_state"
      return status

    # Check if satisfied by a prior operation in the graph
    if precond.satisfied_by:
      status.status = "satisfied"
      status.satisfied_by = precond.satisfied_by
      return status

    # Tips must be loaded by pick_up_tips - this will happen during execution
    # if the protocol includes pick_up_tips before aspirate/dispense
    for op in graph.operations:
      if op.method_name in ("pick_up_tips", "pick_up_tips96"):
        status.status = "auto_satisfiable"
        status.satisfied_by = op.id
        status.suggested_action = "Tips will be loaded by pick_up_tips operation"
        return status

    # No pick_up_tips found - protocol may be malformed
    status.status = "unresolvable"
    status.suggested_action = "Protocol missing pick_up_tips - add tip pickup before liquid handling"
    return status

  def _resolve_plate_accessible(
    self,
    precond: StatePrecondition,
    graph: ProtocolComputationGraph,
    deck_state: DeckState,
    status: PreconditionStatus,
  ) -> PreconditionStatus:
    """Resolve a plate_accessible precondition."""
    var_name = precond.resource_variable
    resource = graph.resources.get(var_name)

    if not resource:
      status.status = "unresolvable"
      status.suggested_action = f"Resource '{var_name}' not found"
      return status

    # Check if the resource (plate) is accessible
    # This would typically involve checking if a lid is on it
    # For now, assume accessible if on deck
    if var_name in deck_state.placed_resources:
      status.status = "satisfied"
      status.satisfied_by = "existing_placement"
      return status

    # Not on deck yet, but will be accessible once placed
    status.status = "auto_satisfiable"
    status.suggested_action = f"Ensure {var_name} is accessible (no lid)"
    return status

  def _find_matching_assets(
    self,
    resource: ResourceNode,
    available_assets: list[dict[str, Any]],
  ) -> list[AssetMatch]:
    """Find assets that match a resource requirement.

    Args:
        resource: The resource requirement.
        available_assets: Available assets from inventory.

    Returns:
        List of matching assets sorted by score.

    """
    matches: list[AssetMatch] = []

    target_type = resource.declared_type
    # Handle container types (list[Well] -> Plate)
    if resource.is_container and resource.element_type:
      parent_chain = get_parental_chain(resource.element_type)
      if parent_chain.chain:
        target_type = parent_chain.chain[0]  # First parent (e.g., Plate)

    for asset in available_assets:
      asset_type = asset.get("type") or asset.get("resource_type", "")
      asset_fqn = asset.get("fqn", "")

      # Check for type match
      if target_type.lower() in asset_type.lower() or target_type.lower() in asset_fqn.lower():
        match = AssetMatch(
          asset_id=get_asset_identifier(asset),
          asset_name=asset.get("name", "Unknown"),
          asset_type=asset_type,
          asset_fqn=asset_fqn,
          match_score=1.0,
          match_reasons=[f"Type '{asset_type}' matches '{target_type}'"],
        )
        matches.append(match)

    # Sort by score
    matches.sort(key=lambda m: m.match_score, reverse=True)
    return matches

  def _generate_deck_config(
    self,
    graph: ProtocolComputationGraph,
    deck_state: DeckState,
    preconditions: list[PreconditionStatus],
  ) -> DeckLayoutConfig:
    """Generate a deck configuration for preconditions.

    Args:
        graph: The computation graph.
        deck_state: Current deck state.
        preconditions: Preconditions that need placements.

    Returns:
        DeckLayoutConfig with recommended placements.

    """
    placements: list[ResourcePlacement] = []
    seen_resources: set[str] = set()

    for precond_status in preconditions:
      if precond_status.precondition_type != PreconditionType.RESOURCE_ON_DECK:
        continue

      var_name = precond_status.resource_variable
      if var_name in seen_resources:
        continue

      resource = graph.resources.get(var_name)
      if not resource:
        continue

      seen_resources.add(var_name)

      # Create a placement entry
      # In production, this would include FQN lookup from asset catalog
      placement = ResourcePlacement(
        resource_fqn=f"pylabrobot.resources.{resource.declared_type}",  # Placeholder
        name=var_name,
        slot=None,  # To be filled by user or auto-layout
        position=None,
        rotation=None,
        parent_name=None,
      )
      placements.append(placement)

    return DeckLayoutConfig(
      deck_fqn=deck_state.deck_fqn or "pylabrobot.resources.Deck",
      deck_kwargs={},
      placements=placements,
      description=f"Generated deck config for {graph.protocol_name}",
    )

  def _generate_summary(self, result: ResolutionResult) -> str:
    """Generate a human-readable summary of the resolution."""
    parts = []

    if result.satisfied:
      parts.append(f"{len(result.satisfied)} precondition(s) already satisfied")

    if result.auto_satisfiable:
      parts.append(f"{len(result.auto_satisfiable)} precondition(s) auto-satisfiable")

    if result.needs_user_input:
      parts.append(f"{len(result.needs_user_input)} precondition(s) need user input")

    if result.unresolvable:
      parts.append(f"{len(result.unresolvable)} precondition(s) unresolvable")

    if not parts:
      return "No preconditions to resolve"

    summary = "; ".join(parts)

    if result.can_execute:
      if result.requires_user_input:
        summary += " - Ready to execute with user configuration"
      else:
        summary += " - Ready to execute"
    else:
      summary += " - Cannot execute (unresolvable preconditions)"

    return summary


# =============================================================================
# Convenience Functions
# =============================================================================


def get_asset_identifier(asset: dict[str, Any]) -> str:
  """Get a unique identifier for an asset.

  Args:
      asset: The asset dictionary.

  Returns:
      The asset identifier (from 'id' or 'accession_id').

  Raises:
      KeyError: If neither 'id' nor 'accession_id' is present.
  """
  if "id" in asset:
    return str(asset["id"])
  if "accession_id" in asset:
    return str(asset["accession_id"])

  raise KeyError("Asset missing both 'id' and 'accession_id'")


def resolve_protocol_preconditions(
  graph: ProtocolComputationGraph,
  deck_state: DeckState | None = None,
  available_assets: list[dict[str, Any]] | None = None,
) -> ResolutionResult:
  """Convenience function to resolve protocol preconditions.

  Args:
      graph: The protocol computation graph.
      deck_state: Current deck state (optional).
      available_assets: Available assets (optional).

  Returns:
      ResolutionResult with resolution status.

  """
  resolver = PreconditionResolver()
  return resolver.resolve(graph, deck_state, available_assets)
