import importlib
import inspect
import pkgutil
from typing import TypeVar

from pylabrobot.legacy.machines import Machine

T = TypeVar("T")


def get_class_members(library_name: str, subpackage, base_class_name: str):
  """Gets all members of a class, including those in subclasses,
  from a specified library.

  Args:
      library_name (str): The name of the library to import.
      subpackage (str): The subpackage to search for the base class in.
      base_class_name (str): The name of the base class to search for.

  Returns:
      dict: A dictionary where keys are class names and values are
            lists of their members.

  """

  def get_members(cls):
    return [name for name, _ in inspect.getmembers(cls)]

  all_members = {}
  base_class = getattr(
    importlib.import_module(name=library_name + "." + subpackage), base_class_name,
  )

  for _, module_name, _ in pkgutil.walk_packages(
    importlib.import_module(library_name).__path__, prefix=f"{library_name}.",
  ):
    module = importlib.import_module(module_name)
    for name, obj in inspect.getmembers(module):
      if inspect.isclass(obj) and issubclass(obj, base_class):
        all_members[name] = obj

  return all_members


def new_init(self, *args, **kwargs):
  if isinstance(self, Machine):  # TODO: Change this to a more general check
    if args:
      msg = "All arguments must be keyword arguments when using praxis."
      raise ValueError(msg)
    if "name" in kwargs:
      self.name = kwargs["name"]
      kwargs.pop("name")
    else:
      self.name = None
    self.backend = kwargs["backend"]
    self._setup_finished = False
  else:
    super(type(self), self).__init__(*args, **kwargs)


def new_serialize(self):
  return {
    **super(type(self), self).serialize(),
    "name": self.name,
  }


def patch_subclasses() -> dict[str, type[Machine]]:
  """Adds new __init__ and serialize methods to all subclasses of a base class. Specifically, it adds
  a name attribute to all subclasses of the Machine class.

  Args:
    base_class (T): The base class to add the new methods to.

  Returns:
    dict: A dictionary where keys are the names of the subclasses and values are the subclasses
          with the new methods.

  """
  new_objs = {}
  for obj in get_class_members(
    library_name="pylabrobot", subpackage="legacy.machines", base_class_name=Machine.__name__,
  ).values():
    if inspect.isclass(obj) and issubclass(obj, Machine):
      obj.__init__ = new_init  # type: ignore
      obj.serialize = new_serialize  # type: ignore
      new_objs[obj.__name__] = obj
  return new_objs
