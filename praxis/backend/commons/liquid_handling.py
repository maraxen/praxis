import warnings
from typing import Literal

from praxis.utils import (
  check_list_length,
  coerce_to_list,
  liquid_handler_setup_check,
  tip_mapping,
  type_check,
)
from pylabrobot.legacy.liquid_handling import LiquidHandler
from pylabrobot.resources import (
  Container,
  ItemizedResource,
  Plate,
  Resource,
  TipRack,
  TipSpot,
  Well,
)


async def split_along_columns(resources: list[Container]) -> list[list[Resource]]:
  """Splits a list of resources into sublists based on their column indices.

  Args:
    resources (list[Resource]): The resources to split.

  Returns:
    list[list[Resource]]: The resources split into sublists based on their column indices.

  """
  if not all(isinstance(resources, Resource) for resource in resources):
    msg = "Invalid well type."
    raise ValueError(msg)
  if all(isinstance(resource, Plate) for resource in resources):
    return [list(resource) for resource in resources]
  if all(isinstance(resource, Well) for resource in resources):
    columns = [(await parse_well_name(well))[0] for well in wells]
  return [
    [well for column, well in zip(columns, wells, strict=False) if column == i]
    for i in range(max(columns) + 1)
  ]


async def inspect_mix_parameters(
  mix_proportion: float | None, mix_volumes: float | list[float] | None,
) -> tuple[float | None, list[float] | None]:
  """ """
  if mix_volumes is None and mix_proportion is None:
    mix_proportion = 0.5
  elif mix_volumes is not None and mix_proportion is not None:
    msg = "Use either mix proportion or mix volumes, not both."
    raise ValueError(msg)
  mix_volumes = (
    [mix_volumes]
    if mix_volumes is not None and not isinstance(mix_volumes, list)
    else None
  )
  return mix_proportion, mix_volumes


async def generate_mix_volumes(
  volumes: list[float],
  mix_proportion: float | None,
  mix_volumes: list[float] | None = None,
) -> list[float]:
  """ """
  if mix_volumes is None and mix_proportion is None:
    msg = "Either mix_proportion or mix_volumes must be provided."
    raise ValueError(msg)
  if mix_volumes is not None and mix_proportion is not None:
    warnings.warn("Mix proportion and mix volumes are both set, using mix volumes.", stacklevel=2)
  if mix_volumes is not None:
    return mix_volumes
  assert mix_proportion is not None, "Mix proportion must be provided."
  return [v * mix_proportion * 10 for v in volumes]  # * 10 for hamilton


@liquid_handler_setup_check
async def transfer_with_mixing(
  liquid_handler: LiquidHandler,
  sources: Container | list[Container],
  targets: Container | list[Container],
  volumes: float | list[float],
  transfer_tips: TipSpot | TipRack | list[TipSpot] | list[TipRack],
  mix_cycles: int | list[int] = 10,
  return_tips: bool = True,
  mix_proportion: float | None = None,
  mix_volumes: float | list[float] | None = None,
  map_tips: Literal["source", "target"] | None = None,
) -> None:
  """Transfers liquid from source containers to target containers with mixing.

  Args:
    liquid_handler (LiquidHandler): The liquid handler object used for the transfer.
    sources (Container | list[Container]): The source container(s) from which to aspirate liquid.
    targets (Container | list[Container]): The target container(s) to which to dispense liquid.
    volumes (float | list[float]): The volume(s) of liquid to transfer.
    transfer_tips (TipSpot | TipRack | list[TipSpot] | list[TipRack]): The tip(s) to use for the
    transfer.
    mix_cycles (int | list[int], optional): The number of mixing cycles to perform. Defaults to 10.
    return_tips (bool, optional): Whether to return the tips after the transfer. Defaults to True.
    mix_proportion (Optional[float | list[float]], optional): The proportion of mixing volume to
    total volume.
      If not provided, defaults to 0.5. Defaults to None.
    mix_volumes (Optional[float | list[float]], optional): The volume(s) of mixing liquid to use.
      If not provided, it is calculated as mix_proportion * volumes. Defaults to None.
    map_tips (Optional[Literal["source", "target"]], optional): The mapping of tips to sources or
    targets.
      If not provided, the tips are mapped to source well indices. Defaults to None.

  Raises:
    ValueError: If mix_proportion is provided with mix_volumes.
    ValueError: If sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes are not lists.
    ValueError: If the length of sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes
    does not match.
    ValueError: If sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes are not of the
    correct types.

  """
  mix_proportion, mix_volumes = await inspect_mix_parameters(
    mix_proportion, mix_volumes,
  )
  await coerce_to_list(items=[sources, targets, volumes, transfer_tips, mix_cycles])
  assert (
    isinstance(transfer_tips, list)
    and isinstance(sources, list)
    and isinstance(targets, list)
    and isinstance(volumes, list)
    and isinstance(mix_cycles, list)
  ), "All arguments must be lists or coercible to lists."
  mix_volumes = await generate_mix_volumes(
    volumes=volumes, mix_proportion=mix_proportion, mix_volumes=mix_volumes,
  )
  transfer_tips = await tip_mapping(
    tips=transfer_tips, sources=sources, targets=targets, map_tips=map_tips,
  )
  (
    sources,
    targets,
    volumes,
    transfer_tips,
    mix_cycles,
    mix_volumes,
  ) = await check_list_length(
    items=[sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes],
    coerce_length=True,
    target_length=len(transfer_tips),
  )
  await type_check(
    items=[sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes],
    types=[Container, Container, float, TipSpot, int, float, float],
    in_list=True,
  )
  await liquid_handler.pick_up_tips(tip_spots=transfer_tips)
  await liquid_handler.aspirate(
    resources=sources, vols=volumes, mix_cycles=mix_cycles, mix_volumes=mix_volumes,
  )
  await liquid_handler.dispense(
    resources=targets, vols=volumes, mix_cycles=mix_cycles, mix_volumes=mix_volumes,
  )
  if return_tips:
    await liquid_handler.drop_tips(tip_spots=transfer_tips)


@liquid_handler_setup_check
async def transfer_with_mixing96(
  liquid_handler: LiquidHandler,
  source: Plate,  # ItemizedResource[Container], TODO: change to ItemizedResource once implemented with PLR
  target: Plate,  # ItemizedResource[Container], TODO: change to ItemizedResource once implemented with PLR
  volume: float,
  transfer_tips: TipRack,
  mix_cycles: int = 10,
  return_tips: bool = True,
  mix_proportion: float | None = None,
  mix_volume: float | None = None,
) -> None:
  """Transfers liquid from source containers to target containers with mixing.

  Args:
    liquid_handler (LiquidHandler): The liquid handler object used for the transfer.
    sources (Container | list[Container]): The source container(s) from which to aspirate liquid.
    targets (Container | list[Container]): The target container(s) to which to dispense liquid.
    volumes (float | list[float]): The volume(s) of liquid to transfer.
    transfer_tips (TipSpot | TipRack | list[TipSpot] | list[TipRack]): The tip(s) to use for the
    transfer.
    mix_cycles (int | list[int], optional): The number of mixing cycles to perform. Defaults to 10.
    return_tips (bool, optional): Whether to return the tips after the transfer. Defaults to True.
    mix_proportion (Optional[float | list[float]], optional): The proportion of mixing volume to
    total volume.
      If not provided, defaults to 0.5. Defaults to None.
    mix_volumes (Optional[float | list[float]], optional): The volume(s) of mixing liquid to use.
      If not provided, it is calculated as mix_proportion * volumes. Defaults to None.
    map_tips (Optional[Literal["source", "target"]], optional): The mapping of tips to sources or
    targets.
      If not provided, the tips are mapped to source well indices. Defaults to None.

  Raises:
    ValueError: If mix_proportion is provided with mix_volumes.
    ValueError: If sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes are not lists.
    ValueError: If the length of sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes
    does not match.
    ValueError: If sources, targets, volumes, transfer_tips, mix_cycles, mix_volumes are not of the
    correct types.

  """
  if mix_proportion is not None and mix_volume is not None:
    warnings.warn(
      "Mix proportion and volume are not currently supported for 96 head transfers.       Ignoring.", stacklevel=2,
    )
  # mix_proportion, mix_volume = await inspect_mix_parameters(mix_proportion, mix_volume)
  if any(isinstance(i, list) for i in [volume, transfer_tips, mix_cycles, mix_volume]):
    msg = "All arguments must be single values for 96 head use, not lists."
    raise ValueError(msg)
  if not isinstance(source, ItemizedResource) or not isinstance(
    target, ItemizedResource,
  ):
    msg = "Sources and targets must be ItemizedResource objects."
    raise ValueError(msg)
  if not isinstance(transfer_tips, TipRack):
    msg = "Transfer tips must be a TipRack object."
    raise ValueError(msg)
  # mix_volume = mix_proportion * volume if mix_volume is None else mix_volume
  await type_check(
    items=[source, target, volume, transfer_tips],  # , mix_cycles, mix_volumes],
    types=[ItemizedResource, ItemizedResource, float, TipRack],  # , int, float],
    in_list=False,
  )
  await liquid_handler.pick_up_tips96(tip_rack=transfer_tips)
  await liquid_handler.aspirate96(
    resource=source, volume=volume,
  )  # TODO: add mix_cycles to aspirate96 and dispense96 and allow for resource to be any container of appropriate size
  await liquid_handler.dispense(resource=target, volume=volume)
  if return_tips:
    await liquid_handler.drop_tips(tip_spots=transfer_tips)


async def fast_optimal_transfer():
  pass
