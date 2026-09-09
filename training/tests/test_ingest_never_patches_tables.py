"""No-auto-patch guarantee tests (§5.6, C2, Task 6).

Three enforcement mechanisms, tested here in order of increasing strength:

  (a) `io.write_artifact` is the ONLY writer, and it raises `ProtectedPathError`
      for any of the 7 `PROTECTED_ROOTS` prefixes -- tested by
      `TestProtectedRootsRaise`.
  (b) An AST lint over every module under `training/ingest/` (other than
      `io.py` itself) -- a cheap, EXPLICITLY INCOMPLETE heuristic early
      warning, not the proof (§5.6(b), W7). Tested by `TestAstLint`.
  (c) A byte-level canary: hash four canonical-table files, run the full
      pipeline into a `tmp_path`, re-hash, assert equality. This observes the
      property directly and does not care how (or whether) a write was
      spelled -- the strongest evidence in this file, and the cheapest.
      Tested by `TestByteCanary`.
"""

import ast
import hashlib
from pathlib import Path

import pytest

from ingest import audit, cli, io, licenses, recipes

INGEST_DIR = Path(io.__file__).parent
REPO_ROOT = io.REPO_ROOT

MODULES_UNDER_LINT = sorted(
    p for p in INGEST_DIR.glob("*.py") if p.name != "io.py"
)


# ============================================================================
# (a) io.ProtectedPathError -- the runtime-checked single writer
# ============================================================================


class TestProtectedRootsRaise:
    """Every PROTECTED_ROOTS prefix raises ProtectedPathError via write_artifact."""

    @pytest.mark.parametrize(
        "target_rel",
        [
            "coxswain/src/coxswain/plr/tool_schema.py",
            "coxswain/src/coxswain/plr/param_namespace.py",
        ],
        ids=["coxswain-tool_schema", "coxswain-param_namespace"],
    )
    def test_coxswain_root_raises(self, target_rel):
        target = Path(target_rel)
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(REPO_ROOT / target.parent, target.name, "x")

    def test_floor_gen_data_root_raises(self):
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(
                REPO_ROOT / "training/floor_gen/data", "ambiguity_matrix.json", "x"
            )

    def test_overlay_gen_root_raises(self):
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(REPO_ROOT / "training/overlay_gen", "miner.py", "x")

    def test_assemble_out_root_raises(self):
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(
                REPO_ROOT / "training/assemble/out", "corpus_p25.jsonl", "x"
            )

    def test_golden_root_raises(self):
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(REPO_ROOT / "training/golden", "some_fixture.json", "x")

    def test_external_root_raises(self):
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(REPO_ROOT / "external/plr", "some_file.py", "x")

    @pytest.mark.parametrize(
        "name",
        [
            "sources.json",
            "license_rules.json",
            "experimental_partition.json",
            "audit_adjudications.json",
            "import_closure_allowlist.json",
            "receiver_aliases.json",
            "lineage_contract.json",
            "token_histogram.json",
            "eval_split.json",
            "canonical_tables_fingerprint.json",
            "blocking_census.json",
        ],
    )
    def test_ingest_data_root_raises_for_all_eleven_committed_files(self, name):
        """training/ingest/data/ is a single PROTECTED_ROOTS prefix; §5.6(d)
        confirms no command may write ANY of the eleven committed files in it,
        hand-authored or computed. One test per file, all routed through the
        same prefix match."""
        with pytest.raises(io.ProtectedPathError):
            io.write_artifact(REPO_ROOT / "training/ingest/data", name, "x")

    def test_tmp_path_outside_repo_root_is_always_legal(self, tmp_path):
        """A tmp_path target is legal even if its basename collides with a
        protected file's basename -- REPO_ROOT-relative-ness is what's
        checked, not the name."""
        written = io.write_artifact(tmp_path, "tool_schema.py", "not actually protected")
        assert written.read_text() == "not actually protected"

    def test_protected_path_error_is_an_ingest_error(self):
        """ProtectedPathError subclasses cli.IngestError, not bare RuntimeError
        (rev 7, C1) -- so an attempted write into a protected root surfaces as
        exit 1 via cli.run, not an uncaught traceback."""
        assert issubclass(io.ProtectedPathError, cli.IngestError)


# ============================================================================
# (b) AST lint -- heuristic, explicitly incomplete, but must actually run
# ============================================================================

_UNAMBIGUOUS_PATH_WRITE_METHODS = frozenset({
    "write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir",
    "symlink_to", "hardlink_to", "chmod",
})

# rename/replace collide with str.rename (doesn't exist) / str.replace (does).
# Path.rename(target) and Path.replace(target) each take exactly ONE
# positional-or-keyword argument; str.replace(old, new[, count]) takes two or
# three. Disambiguate on arg count rather than name alone.
_AMBIGUOUS_PATH_WRITE_METHODS_ONE_ARG = frozenset({"rename", "replace"})

_OS_MODULE_WRITE_CALLS = frozenset({
    "makedirs", "mkdir", "rmdir", "remove", "unlink", "rename", "replace",
    "truncate", "symlink", "link", "chmod",
})

_DUMP_STYLE_CALLS = frozenset({
    ("json", "dump"), ("pickle", "dump"), ("csv", "writer"), ("csv", "DictWriter"),
})

_WHOLE_MODULES_BANNED = frozenset({"shutil", "tempfile"})

_WRITE_CAPABLE_OS_OPEN_FLAGS = frozenset({
    "O_WRONLY", "O_RDWR", "O_APPEND", "O_CREAT", "O_EXCL", "O_TRUNC",
})


def _dotted_root_name(node: ast.AST) -> str | None:
    """Leftmost Name in an attribute chain: `os.path.join` -> 'os'."""
    while isinstance(node, ast.Attribute):
        node = node.value
    if isinstance(node, ast.Name):
        return node.id
    return None


def _mode_arg_looks_write_capable(mode_node: ast.AST) -> bool:
    """True for a string-literal mode containing w/a/x/+; conservatively True
    for a non-literal mode too, since a lint can't prove a variable is safe."""
    if isinstance(mode_node, ast.Constant) and isinstance(mode_node.value, str):
        return any(c in mode_node.value for c in "wax+")
    return True


def _flags_arg_looks_write_capable(flags_node: ast.AST) -> bool:
    for sub in ast.walk(flags_node):
        if isinstance(sub, ast.Attribute) and sub.attr in _WRITE_CAPABLE_OS_OPEN_FLAGS:
            return True
    return False


def _keyword_value(call: ast.Call, name: str) -> ast.AST | None:
    for kw in call.keywords:
        if kw.arg == name:
            return kw.value
    return None


def _scan_module_for_violations(path: Path) -> list[str]:
    """Heuristic AST scan for §5.6(b)'s banned-call list. Returns a list of
    human-readable violation descriptions (empty if clean). NOT claimed
    complete (W7) -- this is the lint, not the proof; see TestByteCanary."""
    tree = ast.parse(path.read_text(), filename=str(path))
    violations: list[str] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name in _WHOLE_MODULES_BANNED:
                    violations.append(f"{path.name}:{node.lineno}: `import {alias.name}` (banned module)")
            continue

        if isinstance(node, ast.ImportFrom):
            if node.module in _WHOLE_MODULES_BANNED:
                violations.append(f"{path.name}:{node.lineno}: `from {node.module} import ...` (banned module)")
            continue

        if not isinstance(node, ast.Call):
            continue

        func = node.func

        # Bare-name calls: open(...)
        if isinstance(func, ast.Name):
            if func.id == "open":
                mode_arg = node.args[1] if len(node.args) >= 2 else _keyword_value(node, "mode")
                if mode_arg is not None and _mode_arg_looks_write_capable(mode_arg):
                    violations.append(f"{path.name}:{node.lineno}: open(..., mode=...) write-capable")
            continue

        if not isinstance(func, ast.Attribute):
            continue

        attr = func.attr
        root = _dotted_root_name(func.value)

        if root == "os" and attr == "fdopen":
            mode_arg = node.args[1] if len(node.args) >= 2 else _keyword_value(node, "mode")
            if mode_arg is not None and _mode_arg_looks_write_capable(mode_arg):
                violations.append(f"{path.name}:{node.lineno}: os.fdopen(..., mode=...) write-capable")
            continue

        if root == "os" and attr == "open":
            flags_arg = node.args[1] if len(node.args) >= 2 else _keyword_value(node, "flags")
            if flags_arg is not None and _flags_arg_looks_write_capable(flags_arg):
                violations.append(f"{path.name}:{node.lineno}: os.open(..., flags=...) write-capable")
            continue

        if root == "io" and attr == "open":
            mode_arg = node.args[1] if len(node.args) >= 2 else _keyword_value(node, "mode")
            if mode_arg is not None and _mode_arg_looks_write_capable(mode_arg):
                violations.append(f"{path.name}:{node.lineno}: io.open(..., mode=...) write-capable")
            continue

        if root == "os" and attr in _OS_MODULE_WRITE_CALLS:
            violations.append(f"{path.name}:{node.lineno}: os.{attr}(...)")
            continue

        if root in _WHOLE_MODULES_BANNED:
            violations.append(f"{path.name}:{node.lineno}: {root}.{attr}(...) (banned module)")
            continue

        if root is not None and (root, attr) in _DUMP_STYLE_CALLS:
            violations.append(f"{path.name}:{node.lineno}: {root}.{attr}(...)")
            continue

        if attr == "open":
            # <obj>.open(mode=...) -- e.g. Path.open; mode is the first
            # positional-or-keyword argument for pathlib.Path.open.
            mode_arg = node.args[0] if len(node.args) >= 1 else _keyword_value(node, "mode")
            if mode_arg is not None and _mode_arg_looks_write_capable(mode_arg):
                violations.append(f"{path.name}:{node.lineno}: <obj>.open(mode=...) write-capable")
            continue

        if attr in _UNAMBIGUOUS_PATH_WRITE_METHODS:
            violations.append(f"{path.name}:{node.lineno}: .{attr}(...)")
            continue

        if attr in _AMBIGUOUS_PATH_WRITE_METHODS_ONE_ARG:
            n_args = len(node.args) + len(node.keywords)
            if n_args == 1:
                violations.append(f"{path.name}:{node.lineno}: .{attr}(<1 arg>) (Path-shaped)")
            continue

    return violations


class TestAstLint:
    def test_lint_scans_every_module_except_io(self):
        """Sanity on the lint's own scope: io.py is excluded, every other
        module in the package is included."""
        names = {p.name for p in MODULES_UNDER_LINT}
        assert "io.py" not in names
        assert "audit.py" in names
        assert "recipes.py" in names
        assert "licenses.py" in names
        assert "eval_split.py" in names
        assert "cli.py" in names
        assert "sources.py" in names

    @pytest.mark.parametrize(
        "module_path", MODULES_UNDER_LINT, ids=[p.name for p in MODULES_UNDER_LINT]
    )
    def test_module_has_no_banned_write_calls(self, module_path):
        """Real per-module assertion: each module other than io.py is clean.
        A failure here names the exact module and call -- if this ever fires
        against real code, that is a genuine bug in an earlier task, not a
        lint false positive to be shrugged off (per Task 6's own instruction)."""
        violations = _scan_module_for_violations(module_path)
        assert violations == [], f"banned write-shaped call(s) found: {violations}"

    def test_lint_detects_a_synthetic_violation(self, tmp_path):
        """The lint isn't a no-op: prove it actually fires on an obviously
        bad module before trusting that it found nothing in the real one."""
        bad_module = tmp_path / "definitely_not_io.py"
        bad_module.write_text(
            "from pathlib import Path\n"
            "def f():\n"
            "    Path('x').write_text('y')\n"
        )
        violations = _scan_module_for_violations(bad_module)
        assert violations != []

    def test_lint_does_not_false_positive_on_str_replace(self, tmp_path):
        """cli.py's `dest.replace('_', '-')` is str.replace (2 args), not
        Path.replace (1 arg) -- must not be flagged."""
        mod = tmp_path / "looks_like_cli.py"
        mod.write_text(
            "def f(dest):\n"
            "    return dest.replace('_', '-')\n"
        )
        assert _scan_module_for_violations(mod) == []

    def test_lint_does_not_false_positive_on_read_only_open(self, tmp_path):
        """A bare `open(path)` (default mode 'r') or `open(path, 'rb')` must
        not be flagged -- every read in this package is spelled this way."""
        mod = tmp_path / "looks_like_a_reader.py"
        mod.write_text(
            "def f(path):\n"
            "    with open(path) as fh:\n"
            "        pass\n"
            "    with open(path, 'rb') as fh:\n"
            "        pass\n"
        )
        assert _scan_module_for_violations(mod) == []


# ============================================================================
# (c) Byte-level canary -- the strongest evidence, observes C2 directly
# ============================================================================

_CANARY_RELPATHS: tuple[Path, ...] = (
    Path("coxswain/src/coxswain/plr/tool_schema.py"),
    Path("coxswain/src/coxswain/plr/param_namespace.py"),
    Path("training/floor_gen/data/ambiguity_matrix.json"),
    Path("training/overlay_gen/miner.py"),
)


def _hash_canary_files() -> dict[str, str]:
    return {
        str(rel): hashlib.sha256((REPO_ROOT / rel).read_bytes()).hexdigest()
        for rel in _CANARY_RELPATHS
    }


class TestByteCanary:
    def test_full_pipeline_leaves_canonical_tables_byte_identical(self, tmp_path):
        """Hash the four canonical-table files, run the pipeline
        (licenses --report, audit --report, audit --gate, gap --gate) into
        tmp_path, and re-hash. Any inequality fails."""
        before = _hash_canary_files()

        # licenses --report --out <tmp>  (equivalent in-process call: main()'s
        # --report branch is exactly verify_all() -> write_report() ->
        # write_sources_manifest())
        findings = licenses.verify_all()
        licenses.write_report(findings, tmp_path)
        licenses.write_sources_manifest(findings, tmp_path)

        # audit --report --out <tmp>
        report_code = cli.run(
            audit._dispatch_handler, audit._make_parser(),
            ["--report", "--out", str(tmp_path)],
        )
        assert report_code == cli.EXIT_OK

        # audit --gate  (no --out; writes nothing)
        gate_code = cli.run(audit._dispatch_handler, audit._make_parser(), ["--gate"])
        assert gate_code == cli.EXIT_OK

        # gap --gate --out <tmp>  (explicit --out so this test never writes
        # into the real training/ingest/out/ as a side effect)
        from ingest import gap  # noqa: PLC0415
        gap_code = cli.run(
            gap._dispatch_handler, gap._make_parser(),
            ["--gate", "--out", str(tmp_path)],
        )
        # Any of gap's OWN decision codes is fine here -- this test observes
        # canonical-table byte-identity, not the gate's verdict. 5 (clone
        # absent) is deliberately excluded: this test's whole premise is that
        # the pipeline can run, so an unexpected 5 is worth failing loudly on.
        assert gap_code in (
            cli.EXIT_OK, cli.EXIT_MEASUREMENT_ERROR,
            cli.EXIT_STOP_COVERAGE, cli.EXIT_CONTESTED,
        )

        after = _hash_canary_files()

        assert before == after, (
            "the full ingest pipeline changed the bytes of a canonical-table "
            "file -- this is exactly the property C2 exists to prevent"
        )

    def test_canary_files_actually_exist_and_are_nonempty(self):
        """Sanity on the fixture itself: the four paths are real files, so a
        pass above means 'compared', not 'both sides were missing'."""
        for rel in _CANARY_RELPATHS:
            p = REPO_ROOT / rel
            assert p.is_file(), f"canary fixture path does not exist: {p}"
            assert p.stat().st_size > 0
