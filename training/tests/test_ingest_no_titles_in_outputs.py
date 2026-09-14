"""Tier-0 discipline: recipe titles never reach any output file (§3.1).

Recipe `title` is tier-2 EXPRESSION (a display name). Every artifact this
package emits is tier-0 (facts) or tier-1 (structure) -- titles must never
appear verbatim in any of them. This grep-checks the five artifact-producing
outputs against all 91 real recipe titles.
"""

from pathlib import Path
from types import SimpleNamespace

from ingest import audit, eval_split, gap, licenses, recipes


def _all_titles() -> tuple[str, ...]:
    recs = recipes.load_recipes()
    return tuple(r.title for r in recs)


class TestNoTitlesInOutputs:
    def test_no_recipe_title_appears_in_any_artifact(self, tmp_path):
        titles = _all_titles()
        assert len(titles) == 91, f"expected 91 recipe titles, got {len(titles)}"

        out = tmp_path / "out"

        # License report + manifest
        findings = licenses.verify_all()
        licenses.write_report(findings, out)
        licenses.write_sources_manifest(findings, out)

        # Audit report + findings
        audit._handle_report(SimpleNamespace(out=out))

        # Gap report
        gap.gate(out_dir=out)

        artifact_names = [
            "license_report.json",
            "SOURCES.md",
            "audit_report.json",
            "audit_findings.jsonl",
            "gap_report.json",
        ]

        contents = {}
        for name in artifact_names:
            path = out / name
            assert path.exists(), f"expected artifact {name} was not written"
            contents[name] = path.read_text()

        hits = []
        for name, text in contents.items():
            for title in titles:
                if title and title in text:
                    hits.append((name, title))

        assert not hits, (
            f"tier-2 recipe title(s) leaked into tier-0/1 output(s): {hits[:10]}"
            f"{'...' if len(hits) > 10 else ''}"
        )

    def test_titles_fixture_itself_is_non_trivial(self):
        """Sanity on the fixture: titles are non-empty, varied strings, so a
        vacuously-passing grep (e.g. an empty titles tuple) can't hide behind
        this test. Guards against a future load_recipes() regression that
        silently returns zero-length titles."""
        titles = _all_titles()
        assert all(isinstance(t, str) and t for t in titles)
        assert len(set(titles)) > 1
