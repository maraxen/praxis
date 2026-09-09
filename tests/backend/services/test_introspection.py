import pytest

from praxis.backend.services.introspection import inspect_machine_methods


def test_inspect_liquid_handler():
  fqn = "pylabrobot.liquid_handling.LiquidHandler"
  methods = inspect_machine_methods(fqn)

  assert len(methods) > 0

  # Check for some common methods
  method_names = [m.name for m in methods]
  assert "aspirate" in method_names
  assert "dispense" in method_names
  assert "pick_up_tips" in method_names
  assert "drop_tips" in method_names

  # Check aspirate details
  aspirate = next(m for m in methods if m.name == "aspirate")
  assert aspirate.doc is not None
  assert len(aspirate.args) > 0

  # Verify some arguments for aspirate
  arg_names = [a.name for a in aspirate.args]
  assert "resources" in arg_names
  assert "vols" in arg_names

  # Check pick_up_tips details
  pick_up_tips = next(m for m in methods if m.name == "pick_up_tips")
  arg_names = [a.name for a in pick_up_tips.args]
  assert "tip_spots" in arg_names


def test_inspect_security():
  with pytest.raises(ValueError, match="Access denied"):
    inspect_machine_methods("os.path")


def test_inspect_invalid_class():
  with pytest.raises(ValueError, match="Could not load class"):
    inspect_machine_methods("pylabrobot.non_existent.Class")
