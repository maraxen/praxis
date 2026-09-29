"""REPL Session management."""

import code
import io
import sys
import traceback
from typing import Any

from praxis.backend.utils.logging import get_logger

logger = get_logger(__name__)


class ReplSession:
  """A persistent interactive Python session."""

  def __init__(self, context: dict[str, Any] | None = None):
    """Initialize the session with an optional context."""
    self.context = context or {}
    self.console = code.InteractiveConsole(self.context)
    self.buffer = io.StringIO()
    self._bootstrap_imports()

  def _bootstrap_imports(self):
    """Auto-import useful classes into the context."""
    try:
      from pylabrobot import resources
      from pylabrobot.legacy.liquid_handling import LiquidHandler

      self.context["LiquidHandler"] = LiquidHandler
      self.context["resources"] = resources

      # Add other common resources if easy to discover or just wildcard import
      # We can't do 'from resources import *' easily into a dict context without iterating dir()
      for name in dir(resources):
        if not name.startswith("_"):
          self.context[name] = getattr(resources, name)

      logger.info("REPL auto-imports loaded")
    except ImportError:
      logger.warning("Could not auto-import PyLabRobot in REPL")

  def push(self, line: str) -> tuple[bool, str, str | None]:
    """Push a line of code to the interpreter.

    Args:
        line: The line of code to execute.

    Returns:
        A tuple containing:
        - more (bool): True if more input is required (incomplete statement).
        - output (str): Captured stdout/stderr.
        - error (str | None): Error message if an exception occurred, else None.

    """
    # Capture stdout and stderr
    stdout_capture = io.StringIO()
    stderr_capture = io.StringIO()

    original_stdout = sys.stdout
    original_stderr = sys.stderr

    sys.stdout = stdout_capture
    sys.stderr = stderr_capture

    more = False
    error = None

    try:
      # push return True if more input needed
      more = self.console.push(line)
    except Exception:
      # Get full traceback - this handles edge cases where push() throws
      # (normally InteractiveConsole catches exceptions and prints to stderr)
      error = traceback.format_exc()
    finally:
      sys.stdout = original_stdout
      sys.stderr = original_stderr

    output = stdout_capture.getvalue() + stderr_capture.getvalue()

    return more, output, error

  def get_completions(self, text: str) -> list[str]:
    """Get tab completions for the given text using rlcompleter."""
    try:
      import rlcompleter

      # Re-create completer to ensure it has latest context
      completer = rlcompleter.Completer(self.context)

      matches = []
      state = 0
      while True:
        match = completer.complete(text, state)
        if match is None:
          break
        matches.append(match)
        state += 1

      return matches
    except ImportError:
      return []
    except Exception as e:
      logger.error(f"Error getting completions: {e}")
      return []

  def get_variables(self) -> list[dict[str, str]]:
    """Get a list of interesting variables in the current context."""
    variables = []
    for name, value in self.context.items():
      if name.startswith("_"):
        continue

      # Filter out standard modules if not explicitly imported by user (hard to track)
      # For now, just show everything that isn't private
      type_name = type(value).__name__

      # Add some basic descriptions
      desc = str(value)
      if len(desc) > 50:
        desc = desc[:47] + "..."

      variables.append({"name": name, "type": type_name, "value": desc})

    # Sort by name
    variables.sort(key=lambda x: x["name"])
    return variables
