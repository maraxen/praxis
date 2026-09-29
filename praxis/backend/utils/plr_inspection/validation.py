# Standard Library Imports
import inspect
from typing import (
  Any,
)

from pylabrobot.legacy.machines.machine import Machine

# PyLabRobot Imports
from pylabrobot.resources import (
  Deck,
  Resource,
)


def is_resource_subclass(item_class: type[Any]) -> bool:
  """Check if a class is a non-abstract subclass of pylabrobot.resources.Resource."""
  return (
    inspect.isclass(item_class)
    and issubclass(item_class, Resource)
    and not inspect.isabstract(item_class)
    and item_class is not Resource
  )


def is_machine_subclass(item_class: type[Any]) -> bool:
  """Check if a class is a non-abstract subclass of Machine."""
  return (
    inspect.isclass(item_class)
    and issubclass(item_class, Machine)
    and not inspect.isabstract(item_class)
    and item_class is not Machine
  )


def is_deck_subclass(item_class: type[Any]) -> bool:
  """Check if a class is a non-abstract subclass of pylabrobot.resources.Deck."""
  return (
    inspect.isclass(item_class)
    and issubclass(item_class, Deck)
    and not inspect.isabstract(item_class)
    and item_class is not Deck  # Exclude the base Deck class itself
  )
