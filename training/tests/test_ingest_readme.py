"""README.md's exit-code vocabulary matches cli.py's EXIT_* constants exactly.

The exit-code table drifted across five sections and two tasks during this
spec's own review (§7.1's rev-7 hierarchy table exists for the identical
reason); this test applies the same discipline README.md's own list. The
comparison is over all NINE constants (eight decisions + EXIT_USAGE=64), in
both directions, so adding a constant to cli.py without documenting it fails
just as loudly as documenting a code that doesn't exist.
"""

import re
from pathlib import Path

from ingest import cli

README_PATH = Path(cli.__file__).parent / "README.md"

_HEADING_RE = re.compile(r"^### (\d+)\b", re.MULTILINE)


def _documented_exit_codes() -> set[int]:
    text = README_PATH.read_text()
    return {int(m.group(1)) for m in _HEADING_RE.finditer(text)}


def _actual_exit_codes() -> set[int]:
    return {
        getattr(cli, name)
        for name in dir(cli)
        if name.startswith("EXIT_")
    }


class TestReadmeExitCodesMatchCli:
    def test_readme_documents_all_nine_and_no_extras(self):
        documented = _documented_exit_codes()
        actual = _actual_exit_codes()

        assert len(actual) == 9, f"expected 9 EXIT_* constants in cli.py, found {len(actual)}: {sorted(actual)}"

        missing_from_readme = actual - documented
        extra_in_readme = documented - actual

        assert not missing_from_readme, (
            f"cli.py defines exit code(s) {sorted(missing_from_readme)} that "
            f"README.md does not document under a `### <code>` heading"
        )
        assert not extra_in_readme, (
            f"README.md documents exit code(s) {sorted(extra_in_readme)} that "
            f"do not correspond to any EXIT_* constant in cli.py"
        )
        assert documented == actual

    def test_readme_documents_64_separately_from_0_through_7(self):
        """64 must be under its own heading, not folded into the 0-7 decision
        range, so a reader cannot mistake it for a ninth decision."""
        text = README_PATH.read_text()
        assert "### 64" in text
        # The 0-7 decisions and 64 are visually separated by a heading-level
        # `---` rule in this file; assert 64's heading comes after it.
        idx_64 = text.index("### 64")
        idx_rule = text.index("\n---\n")
        assert idx_rule < idx_64, "the 64 heading must follow the decisions/non-decision separator"

    def test_readme_states_module_per_command_invocation_form(self):
        text = README_PATH.read_text()
        assert "python -m ingest.<module> <flags>" in text
        assert "python -m ingest <subcommand>" in text  # named as the NON-supported form
