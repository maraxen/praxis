"""C2 / AC-30 / GATE X part 3: vendoring the pin's Visualizer3D ``static/`` tree.

Revision 10 (D11): only ``pylabrobot/visualizer3D/static/`` is vendored, from the
PLR checkout at the pin, into ``web-repl/overlay/assets/visualizer3d/``. No PLR
Python is copied. Every file except ``index.html`` is byte-identical to its
source; ``index.html`` is transformed in exactly three ways (placeholders
stripped, one classic ``socket.js`` tag before the first ``<script``, one module
``embed.js`` tag before ``</body>``). ``VENDOR_MANIFEST.json`` records the source
commit and every file's sha256, and ``--check`` compares BOTH bytes and commit.

Two groups of tests:

* Synthetic-source tests (no submodule, no network): a tiny static tree with the
  real anchors drives the script, each with a positive control and a paired
  negative control, so the instrument is shown to fire.
* Committed-tree tests: the tree that was actually vendored (from the pin) is
  checked for self-consistency against its manifest and for the AC-30 structural
  clauses. The one test that needs the submodule skips when it is not initialised.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

_SCRIPTS_DIR = Path(__file__).resolve().parents[1] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

import vendor_visualizer3d  # noqa: E402 -- path setup must precede this import

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "web-repl" / "scripts" / "vendor_visualizer3d.py"
ASSETS = REPO_ROOT / "web-repl" / "overlay" / "assets"
VENDORED = ASSETS / "visualizer3d"
SUBMODULE = REPO_ROOT / "external" / "pylabrobot"
STATIC_REL = Path("pylabrobot") / "visualizer3D" / "static"

# PLR 1.0.0b1, the repo's pin (spec OQ-7, AC-30).
PIN = "786ac2c4e4f7afe37885af2d98ff5b0afe274c67"

SOCKET_TAG = '<script src="../visualizer3d-augmentations/socket.js"></script>'
EMBED_TAG = '<script type="module" src="../visualizer3d-augmentations/embed.js"></script>'
GIF_TAG = '<script src="./vendor/gif.js"></script>'

# Mirrors the real index.html's anchors: two placeholders, the classic gif.js tag as the
# first <script, an importmap, an inline script carrying `{{ ws_port }}`, one </body>.
SYNTHETIC_INDEX = f"""<!DOCTYPE html>
<html>
<head><title>viz3d</title><link rel="stylesheet" href="./main.css"></head>
<body>
<span id="source-filename">{{{{ source_filename }}}}</span>
<div id="app"></div>

{GIF_TAG}
<script type="importmap">
{{ "imports": {{ "three": "./vendor/three.js" }} }}
</script>
<script>
  window.wsUrlFor = (p) => `ws://${{p.hostname}}:{{{{ ws_port }}}}/?token=x`;
</script>
<script type="module" src="./boot.js"></script>
</body>
</html>
"""

SYNTHETIC_FILES: dict[str, bytes] = {
    "boot.js": b"export const boot = 1;\n",
    "main.css": b"body { margin: 0 }\n",
    "vendor/three.js": b"// three stub\n",
    "vendor/draco/decoder.wasm": b"\x00asm\x01\x00\x00\x00\xff\xfe",
    "img/logo.png": bytes(range(256)),
}

COMMIT_A = "a" * 40
COMMIT_B = "b" * 40


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def write_static(root: Path, index: str = SYNTHETIC_INDEX, files: dict[str, bytes] | None = None) -> Path:
    """Write a synthetic ``static/`` dir at ``root``; return it."""
    root.mkdir(parents=True, exist_ok=True)
    (root / "index.html").write_text(index)
    for rel, data in (SYNTHETIC_FILES if files is None else files).items():
        p = root / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_bytes(data)
    return root


@pytest.fixture()
def src(tmp_path: Path) -> Path:
    return write_static(tmp_path / "src" / "static")


@pytest.fixture()
def out(tmp_path: Path) -> Path:
    return tmp_path / "assets" / "visualizer3d"


def run_main(*argv: str) -> int:
    return vendor_visualizer3d.main(list(argv))


def vendor(src: Path, out: Path, commit: str = COMMIT_A) -> int:
    return run_main("--src", str(src), "--out", str(out), "--commit", commit)


def check(src: Path, out: Path, commit: str = COMMIT_A) -> int:
    return run_main("--check", "--src", str(src), "--out", str(out), "--commit", commit)


def tree_bytes(root: Path) -> dict[str, bytes]:
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in sorted(root.rglob("*")) if p.is_file()}


def git(cwd: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.invalid", "-c", "commit.gpgsign=false", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


# --- vendoring a synthetic source ------------------------------------------------


class TestVendorSynthetic:
    def test_every_file_except_index_is_byte_identical_and_hashed(self, src, out):
        assert vendor(src, out) == 0
        vendored = tree_bytes(out)
        manifest = json.loads(vendored.pop("VENDOR_MANIFEST.json"))
        assert sorted(vendored) == sorted(["index.html", *SYNTHETIC_FILES])
        for rel, data in SYNTHETIC_FILES.items():
            assert vendored[rel] == data, rel
        entries = {e["path"]: e for e in manifest["files"]}
        assert sorted(entries) == sorted(vendored)
        for rel, data in vendored.items():
            assert entries[rel]["sha256"] == sha256(data), rel
            assert entries[rel]["bytes"] == len(data), rel

    def test_manifest_records_the_source_commit(self, src, out):
        assert vendor(src, out, COMMIT_A) == 0
        manifest = json.loads((out / "VENDOR_MANIFEST.json").read_text())
        assert manifest["source_sha"] == COMMIT_A
        assert manifest["generator"] == "vendor_visualizer3d.py"

    def test_manifest_records_the_untransformed_source_hash_of_index(self, src, out):
        assert vendor(src, out) == 0
        manifest = json.loads((out / "VENDOR_MANIFEST.json").read_text())
        index = next(e for e in manifest["files"] if e["path"] == "index.html")
        assert index["source_sha256"] == sha256(SYNTHETIC_INDEX.encode())
        assert index["sha256"] != index["source_sha256"]

    def test_running_twice_gives_identical_manifests(self, src, out):
        assert vendor(src, out) == 0
        first = (out / "VENDOR_MANIFEST.json").read_bytes()
        first_tree = tree_bytes(out)
        assert vendor(src, out) == 0
        assert (out / "VENDOR_MANIFEST.json").read_bytes() == first
        assert tree_bytes(out) == first_tree

    def test_no_python_and_no_glb_reach_the_output(self, tmp_path, out):
        files = dict(SYNTHETIC_FILES)
        files["server_stub.py"] = b"print('never vendored')\n"
        files["__pycache__/x.cpython-312.pyc"] = b"\x00\x01"
        src = write_static(tmp_path / "s" / "static", files=files)
        assert vendor(src, out) == 0
        names = sorted(tree_bytes(out))
        assert not [n for n in names if n.endswith((".py", ".pyc")) or "__pycache__" in n], names
        assert not [n for n in names if n.lower().endswith(".glb")], names

    def test_a_glb_in_the_source_fails_loud(self, tmp_path, out, caplog):
        files = dict(SYNTHETIC_FILES)
        files["models/plate.glb"] = b"glTF"
        src = write_static(tmp_path / "s" / "static", files=files)
        assert vendor(src, out) == 1
        assert "plate.glb" in caplog.text

    def test_a_previous_output_is_replaced_not_merged(self, src, out):
        out.mkdir(parents=True)
        (out / "stale.js").write_text("stale")
        assert vendor(src, out) == 0
        assert not (out / "stale.js").exists()

    def test_the_sibling_augmentations_directory_is_never_written(self, src, out):
        aug = out.parent / "visualizer3d-augmentations"
        aug.mkdir(parents=True)
        (aug / "socket.js").write_text("// hand-authored\n")
        before = tree_bytes(aug)
        assert vendor(src, out) == 0
        assert tree_bytes(aug) == before


# --- index.html transform ---------------------------------------------------------


class TestIndexTransform:
    @pytest.fixture()
    def html(self, src, out) -> str:
        assert vendor(src, out) == 0
        return (out / "index.html").read_text()

    def test_no_placeholders_remain(self, html):
        assert "{{" not in html

    def test_placeholders_are_stripped_by_pattern_not_by_name(self, tmp_path, out):
        index = SYNTHETIC_INDEX.replace("<div id=\"app\">", "<b>{{ liquid_color }}</b><div id=\"app\">")
        src = write_static(tmp_path / "s" / "static", index=index)
        assert vendor(src, out) == 0
        assert "{{" not in (out / "index.html").read_text()

    def test_exactly_one_socket_tag_and_it_is_the_first_script(self, html):
        assert html.count(SOCKET_TAG) == 1
        assert html.index("<script") == html.index(SOCKET_TAG)

    def test_socket_tag_is_immediately_followed_by_the_original_first_script(self, html):
        assert f"{SOCKET_TAG}\n{GIF_TAG}" in html
        assert html.count(GIF_TAG) == 1

    def test_exactly_one_embed_tag_before_body_close(self, html):
        assert html.count(EMBED_TAG) == 1
        assert html.count("</body>") == 1
        assert html.index(EMBED_TAG) < html.index("</body>")
        assert html.rindex("<script") == html.index(EMBED_TAG)

    def test_embed_tag_runs_after_the_pages_own_module(self, html):
        assert html.index('src="./boot.js"') < html.index(EMBED_TAG)

    def test_no_https_urls_in_index(self, html):
        assert "https://" not in html

    def test_nothing_else_in_index_changed(self, html):
        stripped = html.replace(f"{SOCKET_TAG}\n", "").replace(f"{EMBED_TAG}\n", "")
        expected = re.sub(r"\{\{[^}]*\}\}", "", SYNTHETIC_INDEX)
        assert stripped == expected

    @pytest.mark.parametrize(
        ("label", "mutate", "needle"),
        [
            ("gif tag missing", lambda h: h.replace(GIF_TAG, ""), "gif.js"),
            ("gif tag not first script", lambda h: h.replace("<body>", "<body>\n<script>1</script>"), "first"),
            ("gif tag twice", lambda h: h.replace("</body>", f"{GIF_TAG}\n</body>"), "gif.js"),
            ("no body close", lambda h: h.replace("</body>", ""), "</body>"),
            ("two body closes", lambda h: h.replace("</html>", "</body></html>"), "</body>"),
            ("an https url", lambda h: h.replace("<title>", '<link href="https://x.invalid/a.css"><title>'), "https://"),
        ],
    )
    def test_anchor_drift_fails_loud_with_context(self, tmp_path, out, caplog, label, mutate, needle):
        src = write_static(tmp_path / "s" / "static", index=mutate(SYNTHETIC_INDEX))
        assert vendor(src, out) == 1, label
        assert needle in caplog.text, (label, caplog.text)

    def test_anchor_failure_shows_line_numbered_context(self, tmp_path, out, caplog):
        src = write_static(tmp_path / "s" / "static", index=SYNTHETIC_INDEX.replace("</body>", ""))
        assert vendor(src, out) == 1
        assert re.search(r"^\s*\d+ \| ", caplog.text, re.M) or "no occurrence" in caplog.text

    def test_a_jsdelivr_reference_in_the_tree_fails_loud(self, tmp_path, out, caplog):
        files = dict(SYNTHETIC_FILES)
        files["vendor/three.js"] = b"import 'https://cdn.jsdelivr.net/npm/three'\n"
        src = write_static(tmp_path / "s" / "static", files=files)
        assert vendor(src, out) == 1
        assert "cdn.jsdelivr.net" in caplog.text


# --- --check: positive control and negative controls ------------------------------


class TestCheck:
    def test_positive_control_a_fresh_vendor_passes(self, src, out):
        assert vendor(src, out) == 0
        assert check(src, out) == 0

    def test_negative_control_source_byte_changed(self, src, out, caplog):
        assert vendor(src, out) == 0
        (src / "vendor" / "three.js").write_bytes(b"// three stuc\n")  # one byte
        assert check(src, out) == 1
        assert "vendor/three.js" in caplog.text

    def test_negative_control_committed_byte_changed(self, src, out, caplog):
        assert vendor(src, out) == 0
        target = out / "img" / "logo.png"
        data = bytearray(target.read_bytes())
        data[10] ^= 0x01
        target.write_bytes(bytes(data))
        assert check(src, out) == 1
        assert "img/logo.png" in caplog.text

    def test_negative_control_index_changed(self, src, out, caplog):
        assert vendor(src, out) == 0
        (src / "index.html").write_text(SYNTHETIC_INDEX.replace("viz3d", "viz3D"))
        assert check(src, out) == 1
        assert "index.html" in caplog.text

    def test_negative_control_committed_index_edited(self, src, out, caplog):
        assert vendor(src, out) == 0
        idx = out / "index.html"
        idx.write_text(idx.read_text().replace(SOCKET_TAG, ""))
        assert check(src, out) == 1
        assert "index.html" in caplog.text

    def test_negative_control_committed_file_missing(self, src, out, caplog):
        assert vendor(src, out) == 0
        (out / "main.css").unlink()
        assert check(src, out) == 1
        assert "main.css" in caplog.text

    def test_negative_control_committed_file_extra(self, src, out, caplog):
        assert vendor(src, out) == 0
        (out / "extra.js").write_text("// not in the source\n")
        assert check(src, out) == 1
        assert "extra.js" in caplog.text

    def test_negative_control_source_gains_a_file(self, src, out, caplog):
        assert vendor(src, out) == 0
        (src / "added.js").write_text("// new upstream file\n")
        assert check(src, out) == 1
        assert "added.js" in caplog.text

    def test_negative_control_recorded_commit_differs(self, src, out, caplog):
        assert vendor(src, out, COMMIT_A) == 0
        assert check(src, out, COMMIT_B) == 1
        assert COMMIT_A in caplog.text and COMMIT_B in caplog.text

    def test_a_commit_mismatch_fails_even_though_every_byte_matches(self, src, out):
        # A pin bump of any kind fails --check until the tree is re-vendored (D11).
        assert vendor(src, out, COMMIT_A) == 0
        assert check(src, out, COMMIT_A) == 0
        assert check(src, out, COMMIT_B) == 1

    def test_negative_control_manifest_hash_tampered(self, src, out, caplog):
        assert vendor(src, out) == 0
        mpath = out / "VENDOR_MANIFEST.json"
        manifest = json.loads(mpath.read_text())
        entry = next(e for e in manifest["files"] if e["path"] == "boot.js")
        entry["sha256"] = "0" * 64
        mpath.write_text(json.dumps(manifest, indent=2) + "\n")
        assert check(src, out) == 1
        assert "boot.js" in caplog.text

    def test_negative_control_manifest_missing(self, src, out):
        assert vendor(src, out) == 0
        (out / "VENDOR_MANIFEST.json").unlink()
        assert check(src, out) == 1

    def test_check_never_writes(self, src, out):
        assert vendor(src, out) == 0
        (out / "extra.js").write_text("x")
        before = tree_bytes(out)
        assert check(src, out) == 1
        assert tree_bytes(out) == before

    def test_check_exits_nonzero_from_the_command_line_naming_the_path(self, src, out):
        assert vendor(src, out) == 0
        (src / "boot.js").write_bytes(b"export const boot = 2;\n")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--check", "--src", str(src), "--out", str(out), "--commit", COMMIT_A],
            capture_output=True,
            text=True,
        )
        assert proc.returncode != 0
        assert "boot.js" in proc.stderr


# --- resolving the commit and the source from the checkout ------------------------


class TestSourceResolution:
    @pytest.fixture()
    def checkout(self, tmp_path: Path) -> Path:
        """A synthetic PLR checkout: a real git repo with ``static/`` at the real depth."""
        root = tmp_path / "plr"
        write_static(root / STATIC_REL)
        git(root, "init", "-q")
        git(root, "add", "-A")
        git(root, "commit", "-q", "-m", "pin")
        return root

    def test_commit_defaults_to_head_of_the_checkout(self, checkout, out):
        head = git(checkout, "rev-parse", "HEAD")
        assert run_main("--src", str(checkout), "--out", str(out)) == 0
        assert json.loads((out / "VENDOR_MANIFEST.json").read_text())["source_sha"] == head

    def test_src_may_be_the_static_dir_itself(self, checkout, out):
        head = git(checkout, "rev-parse", "HEAD")
        assert run_main("--src", str(checkout / STATIC_REL), "--out", str(out)) == 0
        assert json.loads((out / "VENDOR_MANIFEST.json").read_text())["source_sha"] == head

    def test_source_alias_flag(self, checkout, out):
        assert run_main("--source", str(checkout), "--out", str(out)) == 0

    def test_check_passes_at_head_and_fails_after_a_bytewise_no_op_commit(self, checkout, out, caplog):
        assert run_main("--src", str(checkout), "--out", str(out)) == 0
        assert run_main("--check", "--src", str(checkout), "--out", str(out)) == 0
        git(checkout, "commit", "-q", "--allow-empty", "-m", "bump")  # bytes untouched, HEAD moved
        assert run_main("--check", "--src", str(checkout), "--out", str(out)) == 1
        assert "commit" in caplog.text.lower()

    def test_check_fails_when_a_checkout_file_changes_at_head(self, checkout, out, caplog):
        assert run_main("--src", str(checkout), "--out", str(out)) == 0
        (checkout / STATIC_REL / "boot.js").write_bytes(b"export const boot = 3;\n")
        git(checkout, "commit", "-q", "-am", "edit")
        assert run_main("--check", "--src", str(checkout), "--out", str(out)) == 1
        assert "boot.js" in caplog.text

    def test_no_commit_and_no_checkout_fails_loud(self, src, out, caplog):
        # A bare static dir with no enclosing PLR checkout and no --commit must not invent one.
        assert run_main("--src", str(src), "--out", str(out)) == 1
        assert "--commit" in caplog.text
        assert not out.exists()

    def test_an_enclosing_unrelated_git_repo_is_not_mistaken_for_the_checkout(self, tmp_path, out, caplog):
        # An uninitialised submodule sits inside the parent repo; its HEAD is not the pin.
        outer = tmp_path / "outer"
        outer.mkdir()
        git(outer, "init", "-q")
        git(outer, "commit", "-q", "--allow-empty", "-m", "outer")
        static = write_static(outer / "vendored" / "static")
        assert run_main("--src", str(static), "--out", str(out)) == 1
        assert "--commit" in caplog.text

    def test_an_uninitialised_submodule_dir_fails_loud(self, tmp_path, out, caplog):
        empty = tmp_path / "external" / "pylabrobot"
        empty.mkdir(parents=True)
        assert run_main("--src", str(empty), "--out", str(out), "--commit", COMMIT_A) == 1
        assert "submodule" in caplog.text.lower()

    @pytest.mark.parametrize("bad", ["", "abc123", "Z" * 40, "a" * 41, "A" * 40])
    def test_a_malformed_commit_is_rejected(self, src, out, bad):
        assert run_main("--src", str(src), "--out", str(out), "--commit", bad) == 1

    def test_default_src_and_out_point_where_the_spec_says(self):
        assert vendor_visualizer3d.DEFAULT_SRC == SUBMODULE
        assert vendor_visualizer3d.DEFAULT_OUT == VENDORED


# --- the committed tree (vendored from the pin) -----------------------------------


@pytest.fixture(scope="module")
def committed_manifest() -> dict:
    path = VENDORED / "VENDOR_MANIFEST.json"
    assert path.is_file(), f"{path} missing: run web-repl/scripts/vendor_visualizer3d.py"
    return json.loads(path.read_text())


def committed_files() -> dict[str, Path]:
    return {
        p.relative_to(VENDORED).as_posix(): p
        for p in sorted(VENDORED.rglob("*"))
        if p.is_file() and p.name != "VENDOR_MANIFEST.json"
    }


class TestCommittedTree:
    def test_manifest_records_the_pin(self, committed_manifest):
        assert committed_manifest["source_sha"] == PIN
        assert committed_manifest["generator"] == "vendor_visualizer3d.py"

    def test_manifest_lists_exactly_the_files_on_disk_with_true_hashes(self, committed_manifest):
        entries = {e["path"]: e for e in committed_manifest["files"]}
        on_disk = committed_files()
        assert sorted(entries) == sorted(on_disk)
        for rel, path in on_disk.items():
            data = path.read_bytes()
            assert entries[rel]["sha256"] == sha256(data), rel
            assert entries[rel]["bytes"] == len(data), rel

    def test_only_index_html_is_marked_transformed(self, committed_manifest):
        transformed = [e["path"] for e in committed_manifest["files"] if "source_sha256" in e]
        assert transformed == ["index.html"]

    def test_the_assets_the_shell_needs_are_present(self):
        # C6 stages these by path (spec §4, build_repl.py row).
        for rel in ("index.html", "boot.js", "vendor/three.webgpu.min.js", "main.css"):
            assert (VENDORED / rel).is_file(), rel

    def test_no_python_and_no_glb_in_the_vendored_tree(self):
        names = sorted(committed_files())
        assert not [n for n in names if n.endswith((".py", ".pyc")) or "__pycache__" in n]
        assert not [n for n in names if n.lower().endswith(".glb")]

    def test_no_vendored_plr_python_package_exists_anywhere(self):
        # GATE X part 2 (AC-30): no PLR Python is vendored into the overlay.
        assert not (ASSETS / "python" / "plr_visualizer3d").exists()
        needle = "plr_" + "visualizer3d"
        offenders = []
        for root in (REPO_ROOT / "web-repl" / "overlay", REPO_ROOT / "web-repl" / "scripts"):
            for p in root.rglob("*"):
                if p.is_file() and needle.encode() in p.read_bytes():
                    offenders.append(p.relative_to(REPO_ROOT).as_posix())
        assert offenders == []

    def test_zero_cdn_jsdelivr_hits_in_the_whole_tree(self):
        offenders = [n for n, p in committed_files().items() if b"cdn.jsdelivr.net" in p.read_bytes()]
        assert offenders == []

    def test_index_html_clauses(self):
        html = (VENDORED / "index.html").read_text()
        assert "{{" not in html
        assert "https://" not in html
        assert html.count(SOCKET_TAG) == 1
        assert html.index("<script") == html.index(SOCKET_TAG)
        assert f"{SOCKET_TAG}\n{GIF_TAG}" in html  # followed by the original first <script (upstream :319)
        assert html.count(EMBED_TAG) == 1
        assert html.count("</body>") == 1
        assert html.index(EMBED_TAG) < html.index("</body>")

    def test_augmentation_tags_resolve_to_a_sibling_directory(self):
        # The relative src is load-bearing: it resolves only while visualizer3d/ and
        # visualizer3d-augmentations/ are siblings under overlay/assets/ (as in the 2D layout).
        html = (VENDORED / "index.html").read_text()
        srcs = re.findall(r'src="(\.\./[^"]+)"', html)
        assert sorted(srcs) == [
            "../visualizer3d-augmentations/embed.js",
            "../visualizer3d-augmentations/socket.js",
        ]
        for s in srcs:
            resolved = (VENDORED / s).resolve()
            assert resolved.parent == (ASSETS / "visualizer3d-augmentations").resolve()

    def test_vendored_tree_equals_the_submodule_at_the_pin(self):
        static = SUBMODULE / STATIC_REL
        if not static.is_dir():
            pytest.skip("external/pylabrobot submodule not initialised")
        proc = subprocess.run(
            [sys.executable, str(SCRIPT), "--check"],
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
        assert proc.returncode == 0, proc.stderr

    def test_rerunning_the_vendor_script_on_the_committed_tree_is_a_noop(self, tmp_path):
        # Idempotence at the scale of the real tree: vendoring a copy of the source the
        # manifest describes reproduces the committed manifest. Needs the submodule.
        static = SUBMODULE / STATIC_REL
        if not static.is_dir():
            pytest.skip("external/pylabrobot submodule not initialised")
        out = tmp_path / "again"
        assert run_main("--src", str(SUBMODULE), "--out", str(out)) == 0
        assert (out / "VENDOR_MANIFEST.json").read_bytes() == (VENDORED / "VENDOR_MANIFEST.json").read_bytes()
        shutil.rmtree(out)
