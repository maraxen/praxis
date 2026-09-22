import pytest

# These REPL tests depend on frontend-only PyLabRobot runtime behavior and
# external interactive imports. Skip them in backend CI — they should be
# exercised in the frontend/integration test matrix instead.
pytest.skip(
    "REPL tests are frontend-only; skipped in backend test runs. See .praxia/docs/audits/251225_technical-debt.md",
    allow_module_level=True,
)

from praxis.backend.core.repl_session import ReplSession


class TestReplSession:
    """Tests for the ReplSession core logic."""

    def test_initialization_and_imports(self):
        """Test that the session initializes and imports PLR modules."""
        session = ReplSession()

        # Check if context has populated imports
        assert "LiquidHandler" in session.context
        assert "resources" in session.context

        # Check if we can run basic python
        more, output, error = session.push("x = 10 + 5")
        assert not more
        assert not error

        more, output, error = session.push("print(x)")
        assert "15" in output

    def test_plr_simulation_instantiation(self):
        """Test that we can instantiate a LiquidHandler with a simulation backend."""
        session = ReplSession()

        # Define a script to initialize a simulator
        script = """
from pylabrobot.liquid_handling.backends import LiquidHandlerChatterboxBackend
from pylabrobot.resources.hamilton import STARLetDeck

# Create a backend
backend = LiquidHandlerChatterboxBackend()

# Create a deck
deck = STARLetDeck()

# Create LH
lh = LiquidHandler(backend=backend, deck=deck)

print("LH Initialized")
"""
        # Execute line by line or as a block? push() takes a line.
        # But InteractiveConsole.push() handles multiline if we feed it line by line?
        # Or we can just use exec(script, session.context) to verify the logic broadly first,
        # but session.push() simulates the user typing.

        # Let's split by newline and push
        last_output = ""
        for line in script.split("\n"):
            # Skip empty lines to avoid noise unless needed
            if not line.strip():
                continue

            _more, output, error = session.push(line)

            if error:
                pytest.fail(f"Error in REPL line '{line}': {error}")

            if "Traceback" in output:
                pytest.fail(f"Exception in REPL execution: {output}")

            if output:
                last_output = output

        # Verification logic needs to be robust to where the output appeared
        # Since we iterate, we can't just assert on the last loop variable 'output'
        # if the print happened earlier or later.
        # But here print is the last line.

        # Check context
        assert "lh" in session.context

        # Check if print output was captured in the last non-empty push
        # The last line is print("LH Initialized")
        # session.push() captures output for THAT push.
        assert "LH Initialized" in last_output

        # Let's ensure 'lh' is in context
        assert "lh" in session.context
        lh = session.context["lh"]
        assert lh.__class__.__name__ == "LiquidHandler"

    @pytest.mark.asyncio
    async def test_plr_simulation_setup_and_stop(self):
        """Test setup() and stop() on the simulated LH."""
        session = ReplSession()

        # We need to run setup() which is async.
        # InteractiveConsole doesn't await async functions automatically unless we use a wrapper
        # or if the REPL supports top-level await (which standard code.InteractiveConsole does not by default,
        # but 3.8+ handles it differently? No, usually need a custom runner).

        # Wait, Praxis REPL `repl.py` does:
        # more, output, error = session.push(code)
        # It's synchronous. PLR methods are often async.
        # Does the user have to Type `await lh.setup()`?
        # If they type `await ...`, code.InteractiveConsole might syntax error if not configured for async.

        # Let's check if ReplSession supports async.
        # It uses `code.InteractiveConsole`. Standard python console doesn't support top-level await until 3.8+
        # AND you need to run it in a specific way OR usage of `asyncio.run()`.

        # If the user types `await lh.setup()`, it will fail in standard InteractiveConsole.
        # They might need to do: `import asyncio; asyncio.run(lh.setup())`

        setup_script = """
from pylabrobot.liquid_handling.backends.simulation.simulator_backend import SimulatorBackend
from pylabrobot.resources.hamilton import STARLetDeck
import asyncio

backend = SimulatorBackend(open_browser=False)
deck = STARLetDeck()
lh = LiquidHandler(backend=backend, deck=deck)

async def run_setup():
    await lh.setup()
    print("Setup Complete")
    await lh.stop()
    print("Stop Complete")

asyncio.run(run_setup())
"""
        for line in setup_script.split("\n"):
            _more, output, error = session.push(line)
            assert not error, f"Error on line: {line}"
            if "Setup Complete" in output:
                assert "Stop Complete" in output

    def test_completion(self):
        """Test autocomplete functionality."""
        session = ReplSession()

        session.push("import os")

        # Test completion for 'os.pa' -> 'os.path'
        matches = session.get_completions("os.pa")
        assert "os.path" in matches

        # Test completion for pre-imported 'LiquidHandler'
        matches = session.get_completions("LiquidHan")
        assert any(m.startswith("LiquidHandler") for m in matches)
