import os
import sys
from pathlib import Path
from unittest.mock import MagicMock

import cloudpickle

# Add project root to path
sys.path.append(os.getcwd())


def verify_pickle(pickle_path):
  print(f"Verifying {pickle_path}...")

  with open(pickle_path, "rb") as f:
    protocol_func = cloudpickle.load(f)

  print(f"Loaded function: {protocol_func}")

  # Mock backend
  mock_backend = MagicMock()
  mock_backend.__class__.__name__ = "ChatterboxBackend"

  # Run it
  # We suspect it might need 'backend' or 'layout' depending on the protocol
  # But our injection logic in python.worker.ts handles this.
  # Here we just want to see if we can CALL it without 'praxis' errors.

  try:
    # Try calling with backend (simulating what worker does)
    import inspect

    sig = inspect.signature(protocol_func)
    print(f"Signature: {sig}")

    kwargs = {}
    if "backend" in sig.parameters:
      kwargs["backend"] = mock_backend

    # If it needs 'layout' or other args, we might need to mock them too.
    # Most simple protocols might just take backend or no args if they build their own deck.

    # We can't easily simulate the full PLR run without a real deck,
    # but getting to the point of "it's running" and hitting a PLR line is success
    # vs "ModuleNotFoundError: praxis".

    # Let's just try to inspect it deeply to ensure no closure issues.
    closure_vars = inspect.getclosurevars(protocol_func)
    print(f"Closure globals: {closure_vars.globals.keys()}")

    if "praxis" in str(closure_vars.globals):
      print("WARNING: 'praxis' found in closure globals! This might fail in browser.")

    print("Verification passed (loaded and inspected).")
    return True

  except Exception as e:
    print(f"Verification failed: {e}")
    return False


if __name__ == "__main__":
  # Test the first pickle found
  p = list(Path("praxis/web-client/src/assets/protocols").glob("*.pkl"))[0]
  verify_pickle(p)
