"""W6 import boundary for ``coxswain/sim`` (spec amendment, lines ~1192-1197):
zero runtime imports of ``praxis.backend.*``, and no sqlalchemy/redis reachable
from ``coxswain.sim`` -- the two coupling mechanisms W0 identified (tracing
imports at pipeline.py:30-35; package-init chains core/__init__ -> ORM models
and utils/__init__ -> db.py + redis_lock.py) must stay cut.

Same AST-walking style as W2's test_import_boundary.py, plus one stronger
reachability check: importing the package in a clean interpreter must not pull
praxis/sqlalchemy/redis into sys.modules.
"""

import ast
import subprocess
import sys
from pathlib import Path

SIM_ROOT = Path(__file__).resolve().parents[1] / "src" / "coxswain" / "sim"

BANNED_TOP_LEVEL_MODULES = ("praxis", "sqlalchemy", "redis")


def _iter_imports(tree: ast.AST):
    """Yield (node, top_level_module) for every absolute import."""
    if isinstance(tree, ast.Import):
        for alias in tree.names:
            yield tree, alias.name.split(".")[0]
    elif isinstance(tree, ast.ImportFrom):
        if tree.level == 0 and tree.module:
            yield tree, tree.module.split(".")[0]


def test_no_banned_imports_under_sim() -> None:
    offenders: list[str] = []
    for path in sorted(SIM_ROOT.rglob("*.py")):
        tree = ast.parse(path.read_text(), filename=str(path))
        for node in ast.walk(tree):
            for import_node, top in _iter_imports(node):
                if top in BANNED_TOP_LEVEL_MODULES:
                    offenders.append(f"{path}: {ast.unparse(import_node)}")
    assert offenders == [], f"W6 boundary violated: {offenders}"


def test_importing_sim_is_dependency_clean() -> None:
    """Reachability proof: a fresh CPython importing coxswain.sim AND
    coxswain.sim.preview must not have praxis.*, sqlalchemy, or redis in
    sys.modules afterwards."""
    script = (
        "import sys\n"
        "import coxswain.sim\n"
        "import coxswain.sim.preview\n"
        "bad = sorted(m for m in sys.modules "
        "if m.split('.')[0] in ('praxis', 'sqlalchemy', 'redis'))\n"
        "assert not bad, f'reachable: {bad}'\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", script],
        capture_output=True,
        text=True,
    )
    assert proc.returncode == 0, f"stderr:\n{proc.stderr}"


def test_sim_package_exposes_exactly_the_amended_subset() -> None:
    """The amendment names exactly ten symbols from the three partial modules.
    coxswain.sim's __all__ must be exactly that set -- no more (scope creep),
    no less (missing subset member)."""
    import coxswain.sim as sim

    expected = {
        # pipeline.py
        "InferredRequirement",
        "HierarchicalSimulationResult",
        "StatefulSimulationResult",
        # failure_detector.py
        "FailureMode",
        "FailureDetectionResult",
        "BooleanStateConfig",
        "generate_boolean_states",
        # simulator.py
        "ProtocolSimulationResult",
        "SIMULATION_VERSION",
        "is_cache_valid",
    }
    assert set(sim.__all__) == expected


def test_sim_reexports_are_the_single_landed_definitions() -> None:
    """Anti-divergence guard (RISK-3): sim's symbols must BE the W2-landed
    fft.preconditions objects -- identity, not copies."""
    import coxswain.fft.preconditions as pre
    import coxswain.sim as sim

    assert sim.InferredRequirement is pre.InferredRequirement
    assert sim.HierarchicalSimulationResult is pre.HierarchicalSimulationResult
    assert sim.StatefulSimulationResult is pre.StatefulSimulationResult
    assert sim.FailureMode is pre.FailureMode
    assert sim.FailureDetectionResult is pre.FailureDetectionResult
    assert sim.BooleanStateConfig is pre.BooleanStateConfig
    assert sim.generate_boolean_states is pre.generate_boolean_states
    assert sim.ProtocolSimulationResult is pre.ProtocolSimulationResult
    assert sim.SIMULATION_VERSION is pre.SIMULATION_VERSION
    assert sim.is_cache_valid is pre.is_cache_valid
