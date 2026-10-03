"""plr_sema.analysis: the one analysis seam every surface calls (spec 261002 §5).

``analyze(source, function_name)`` extracts the protocol function's graph and
checks it against the contract table. It never raises for a bad protocol: it
returns ``Analyzed`` or a typed ``NotAnalyzed``. A ``NotAnalyzed`` is never a
SAFE verdict, on any surface.

Importable on a base install: libcst, pydantic and the extractor are imported
inside ``analyze``, so without the ``extract`` extra it returns
``NotAnalyzed(EXTRACTOR_UNAVAILABLE)`` instead of raising ``ImportError``.
"""

from __future__ import annotations

import enum
import functools
import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Union

from plr_sema.check import check_graph
from plr_sema.contracts import Contracts, ContractsError, contracts_source, load_contracts
from plr_sema.verdict import SCHEMA_VERSION, AnalysisReport


class NotAnalyzedReason(str, enum.Enum):
    SYNTAX_ERROR = "syntax_error"
    FUNCTION_NOT_FOUND = "function_not_found"
    AMBIGUOUS_FUNCTION = "ambiguous_function"
    EXTRACT_FAILED = "extract_failed"
    CHECK_FAILED = "check_failed"
    EXTRACTOR_UNAVAILABLE = "extractor_unavailable"
    CONTRACTS_UNAVAILABLE = "contracts_unavailable"


@dataclass(frozen=True)
class VerdictKey:
    source_sha256: str  # the analyzed function, without its leading blank lines/comments
    contracts_sha256: str  # Contracts.sha256 (same for .json and .json.gz)
    analyzer_sha256: str  # every plr_sema/**/*.py in the installed package
    schema_version: int  # plr_sema.verdict.SCHEMA_VERSION

    def as_str(self) -> str:
        return f"v{self.schema_version}:{self.source_sha256}:{self.contracts_sha256}:{self.analyzer_sha256}"


@dataclass(frozen=True)
class Analyzed:
    report: AnalysisReport
    key: VerdictKey
    function_name: str
    op_lines: dict[str, int]  # OperationNode.id -> line in `source`


@dataclass(frozen=True)
class NotAnalyzed:
    reason: NotAnalyzedReason
    detail: str
    function_name: str | None = None


AnalysisOutcome = Union[Analyzed, NotAnalyzed]


@functools.lru_cache(maxsize=1)
def analyzer_sha256() -> str:
    root = Path(__file__).resolve().parent
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        digest.update(path.relative_to(root).as_posix().encode("utf-8") + b"\0")
        digest.update(path.read_bytes() + b"\0")
    return digest.hexdigest()


def analyze(
    source: str,
    function_name: str | None = None,
    *,
    contracts: Contracts | None = None,
    deck_layout_type=None,
    module_name: str = "protocol",
) -> AnalysisOutcome:
    R = NotAnalyzedReason
    try:
        import libcst as cst
        from libcst.metadata import MetadataWrapper

        from plr_sema.extract import computation_graph_extractor as extractor
        from plr_sema.graph.resource_hierarchy import DeckLayoutType
    except ImportError as exc:
        return NotAnalyzed(R.EXTRACTOR_UNAVAILABLE, f"install plr-sema[extract]: {exc}", function_name)

    try:
        module = cst.parse_module(source)
    except cst.ParserSyntaxError as exc:
        return NotAnalyzed(R.SYNTAX_ERROR, str(exc), function_name)
    wrapper = MetadataWrapper(module)
    defs = [s for s in wrapper.module.body if isinstance(s, cst.FunctionDef)]
    names = [d.name.value for d in defs]

    if function_name is None:
        if not defs:
            return NotAnalyzed(R.FUNCTION_NOT_FOUND, "no top-level function in source")
        if len(defs) > 1:
            return NotAnalyzed(R.AMBIGUOUS_FUNCTION, f"several top-level functions {names}; pass function_name")
        target = defs[0]
    else:
        matches = [d for d in defs if d.name.value == function_name]
        if not matches:
            return NotAnalyzed(R.FUNCTION_NOT_FOUND, f"no top-level function {function_name!r} (found {names})", function_name)
        if len(matches) > 1:
            return NotAnalyzed(R.AMBIGUOUS_FUNCTION, f"{function_name!r} is defined {len(matches)} times", function_name)
        target = matches[0]
    name = target.name.value

    if contracts is None:
        where = contracts_source()
        if where.path is None:
            return NotAnalyzed(R.CONTRACTS_UNAVAILABLE, f"no contract table configured (layer: {where.layer})", name)
        try:
            contracts = load_contracts(where.path)
        except ContractsError as exc:
            return NotAnalyzed(R.CONTRACTS_UNAVAILABLE, str(exc), name)

    try:
        graph = extractor.extract_graph_from_function(
            target,
            module_name,
            deck_layout_type=deck_layout_type or DeckLayoutType.CARRIER_BASED,
            _wrapper=wrapper,
        )
    except Exception as exc:  # noqa: BLE001 -- an extractor crash is a typed outcome, never a traceback
        return NotAnalyzed(R.EXTRACT_FAILED, f"{type(exc).__name__}: {exc}", name)

    try:
        report = check_graph(json.dumps(graph.model_dump(mode="json")), contracts.json_text)
    except Exception as exc:  # noqa: BLE001 -- same rule for the checker
        return NotAnalyzed(R.CHECK_FAILED, f"{type(exc).__name__}: {exc}", name)

    function_source = wrapper.module.code_for_node(target.with_changes(leading_lines=()))
    key = VerdictKey(
        source_sha256=hashlib.sha256(function_source.encode("utf-8")).hexdigest(),
        contracts_sha256=contracts.sha256,
        analyzer_sha256=analyzer_sha256(),
        schema_version=SCHEMA_VERSION,
    )
    return Analyzed(
        report=report,
        key=key,
        function_name=name,
        op_lines={op.id: op.line_number for op in graph.operations},
    )
