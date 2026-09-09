#!/usr/bin/env python3
"""Vendor the Coxswain serving runtime + fetch the FunctionGemma model files.

Coxswain P2.7a (spec ``.praxia/docs/specs/260825_coxswain-phase-2-functiongemma-copilot-p.md``
rev2, F3 + AC-2.7a.x). Two narrow jobs, both sha256-verified end to end:

**``--runtime``** -- vendor ``@huggingface/transformers`` (transformers.js) into
``web-repl/overlay/assets/coxswain/vendor/`` the same way ``vendor_visualizer.py``
vendors gif.js/konva: TRACKED vendored lib files + a generated
``VENDOR_MANIFEST.json`` (path/sha256/bytes per file). The npm tarball is
verified against the registry's published integrity digest BEFORE extraction,
and the extracted bundle's ONE jsDelivr default-URL literal is rewritten to the
sibling ``ort/`` directory (count asserted == 1 pre-patch, 0 post-patch) --
GATE G5 greps dist for ``cdn.jsdelivr.net`` and wants zero hits, and a dead
default inside a tracked bundle would still trip it. The ORT WebAssembly
backend binary (``ort-wasm-simd-threaded.asyncify.wasm``, ~23.6 MB) is a
COMPILED BINARY and is therefore NEVER committed (repo-wide
zero-tracked-binaries rule): it is fetched into the same tree but gitignored,
with its expected sha256 pinned in VENDOR_MANIFEST.json so the browser-side
first-use integrity check can vouch for it. Its ``.mjs`` loader sibling is a
text file and IS tracked.

**``--models``** -- download the pinned q4f16 export of
``onnx-community/functiongemma-270m-it-ONNX`` (~426 MB; D4's primary dtype)
into gitignored ``web-repl/vendor/models/`` -- the same discipline as
``fetch_pyodide.py``: never a tracked binary, always a fetch script writing
into ``vendor/``. Every file is verified against an UPSTREAM-published digest
before it is atomically renamed into place: LFS files against the Hub's
``lfs.oid`` sha256, plain files against their git blob sha1 (computed exactly
as git does: ``sha1(b"blob <size>\\x00" + data)``). The manifest half of this
contract (the wheels-shaped ``models`` array) lives in ``build_manifest.py``;
this script owns the FETCH half plus the pin table both halves read.

``--check`` verifies an already-vendored runtime + already-fetched models
against the pins offline (no network), loudly.

House rules: uv-run only, argparse + logging, narrow runs, fail loud.
"""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import logging
import os
import re
import shutil
import tarfile
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

logger = logging.getLogger("fetch_models")

_THIS_FILE = Path(__file__).resolve()
DEFAULT_WEB_REPL_ROOT = _THIS_FILE.parents[1]
DEFAULT_VENDOR_DIR = DEFAULT_WEB_REPL_ROOT / "vendor"
# Tracked output tree (JS + manifest); mirrors overlay/assets/visualizer/'s role.
DEFAULT_RUNTIME_VENDOR_DIR = DEFAULT_WEB_REPL_ROOT / "overlay" / "assets" / "coxswain" / "vendor"
DEFAULT_MODELS_DIR = DEFAULT_VENDOR_DIR / "models"

CHUNK_SIZE = 1 << 20  # 1 MiB streaming hash/read chunks

VENDOR_MANIFEST_NAME = "VENDOR_MANIFEST.json"
GENERATOR_VERSION = "1.0.0"

NPM_TRANSFORMERS_URL = (
    "https://registry.npmjs.org/@huggingface/transformers/-/transformers-{version}.tgz"
)
NPM_ORT_WEB_URL = (
    "https://registry.npmjs.org/onnxruntime-web/-/onnxruntime-web-{version}.tgz"
)

HF_RESOLVE_URL = "https://huggingface.co/{repo}/resolve/{revision}/{filename}"


class FetchError(RuntimeError):
    """Raised for any condition that must fail this fetch loudly."""


# --- runtime pins (exact versions; never "latest") ----------------------------
# Verified 260825 against registry.npmjs.org dist-tags: 4.2.0 is `latest`
# stable (4.x line; research §4: v4.2 added TextGenerationPipeline `tools`,
# #1655). The integrity digests are the registry's own published values.
TRANSFORMERS_VERSION = "4.2.0"
TRANSFORMERS_TARBALL_SHA512 = (  # registry dist.integrity for 4.2.0
    "sha512-8BRCoBMH0XsWaEIamuR0LrJGAfftgHAfb2Vrffy0VKlSAE/MnUJ5/h/zTfEP3fDIft"
    "+nk7TqB8xXEyABGitBjQ=="
)
ORT_WEB_VERSION = "1.26.0-dev.20260416-b7804b056c"  # transformers 4.2.0's exact dep
ORT_WEB_TARBALL_SHA512 = (
    "sha512-MD6Ss4GSpQBo6zqoJzyT9LRbKYs7x/JVN23FT24EcEvlqF4VuzPOeH6X38orZPKHQDbprn7K+SBpu0/"
    "mj2CQiw=="
)

#: Files taken from the two npm packages, <member-path-in-tarball> -> dest
#: path relative to the runtime vendor dir. ``transformers.min.js`` is the
#: FULLY SELF-CONTAINED browser ESM bundle (the file jsDelivr's default entry
#: serves): ORT is inlined and there are NO bare module specifiers. The
#: ``transformers.web(.min).js`` variants are NOT shippable origin-local:
#: they carry static `import ... from "onnxruntime-web/webgpu"` /
#: `"onnxruntime-common"` externals that only resolve under a bundler or an
#: import map (measured 260825: a page importing the .web variant fails at
#: link with 'Failed to resolve module specifier'). The asyncify ORT pair is
#: the non-Safari default in v4's env bootstrap AND its binary carries the
#: WebGPU EP for this ORT version. The Safari-named artifacts are deliberately
#: NOT shipped (Safari < 26 has no WebGPU per research §4; matrix follow-up).
RUNTIME_FILES: dict[str, str] = {
    "package/dist/transformers.min.js": "transformers.min.js",
    "package/dist/ort-wasm-simd-threaded.asyncify.mjs": "ort/ort-wasm-simd-threaded.asyncify.mjs",
    "package/dist/ort-wasm-simd-threaded.asyncify.wasm": "ort/ort-wasm-simd-threaded.asyncify.wasm",
}

#: The compiled binary above is fetched into place but NEVER tracked; its pin
#: lives in VENDOR_MANIFEST.json instead. Keep in lockstep with .gitignore
#: (web-repl/.gitignore: /overlay/assets/coxswain/vendor/ort/*.wasm).
RUNTIME_UNTRACKED_SUFFIXES = (".wasm",)

#: Anchored substitution for G5: transformers.js v4's env bootstrap defaults
#: wasmPaths to a jsDelivr prefix when none was set. The minifier renames the
#: module-local variable (`ONNX_ENV` -> e.g. `Ce`), so match the surrounding
#: shape rather than one exact byte string, assert EXACTLY ONE occurrence
#: (vendor_visualizer.py's anchor discipline), and rewrite it to the sibling
#: ort/ dir. model_integrity.js additionally sets wasmPaths explicitly at load
#: time -- this rewrite exists so even the dead default can never trip G5's
#: grep on dist.
_JSDELIVR_WASM_PREFIX_RE = re.compile(
    r"https://cdn\.jsdelivr\.net/npm/onnxruntime-web@\$\{[A-Za-z_$][A-Za-z0-9_$]*\.versions\.web\}/dist/"
)
_JSDELIVR_LOCAL_REPLACEMENT = "./ort/"

#: Hand-authored files in the vendor dir that fetch_models.py must NEVER
#: overwrite or delete -- recorded in VENDOR_MANIFEST.json (role marker) but
#: only ever written by humans, like visualizer-augmentations/.
HAND_AUTHORED_FILES = ("model_integrity.js",)


# --- model pins (P2.7a proves plumbing on the COMMUNITY checkpoint) ----------
# Repo state verified 260825 via
#   GET https://huggingface.co/api/models/<repo>/tree/<revision>?recursive=true
# LFS entries pin lfs.oid (sha256 of raw bytes); plain files pin their git blob
# sha1 -- BOTH are upstream-published expectations, neither is invented here.
MODEL_REPO_ID = "onnx-community/functiongemma-270m-it-ONNX"
MODEL_REVISION = "ba3c872ede162a5c4ab753f509b2260af5587143"
MODEL_NAME = "functiongemma-270m-it"
#: D4 (spec rev2): exactly ONE dtype ships globally; P2.7a's primary is q4f16.
MODEL_DTYPE = "q4f16"
#: Directory name under web-repl/vendor/models/ (mirrors the HF layout so
#: from_pretrained(<dir>) works unchanged in the P2.8 worker).
MODEL_DIR_NAME = f"{MODEL_NAME}-onnx-{MODEL_DTYPE}"

# filename (repo-relative) -> {"bytes": int, "sha256": hex | "git_blob_sha1": hex}
MODEL_FILE_PINS: dict[str, dict] = {
    "config.json": {
        "bytes": 1729,
        "git_blob_sha1": "9ca1f5a763ae9eccaad5ac168c1be82050756918",
    },
    "generation_config.json": {
        "bytes": 210,
        "git_blob_sha1": "14709ab7546f775c213038b64dbdc28243934a5d",
    },
    "tokenizer_config.json": {
        "bytes": 14945,
        "git_blob_sha1": "7ab5f9fdaf305c5e5b9353aa09bf23afb4b5dfcf",
    },
    "chat_template.jinja": {
        "bytes": 13792,
        "git_blob_sha1": "16294794d96bfe26bbf2da97af27ced085fd1683",
    },
    "tokenizer.json": {
        "bytes": 20316979,
        "sha256": "69fde4ada54844b6a7b94494e97f93c581c80cc6610c87e7b45d223077542169",
    },
    "onnx/model_q4f16.onnx": {
        "bytes": 518626,
        "sha256": "8dc9fb5e2b0aa34f527309f0ecaeb9b824b5ad9a9613350168753054c180e145",
    },
    "onnx/model_q4f16.onnx_data": {
        "bytes": 425724416,
        "sha256": "b30ca95e4b31014ec791d7589f8c6416b8056ffc4f39093aa7ceb3ad37f2a0c7",
    },
}

EXPECTED_MODEL_TOTAL_BYTES = sum(p["bytes"] for p in MODEL_FILE_PINS.values())


def model_manifest_entries() -> list[dict]:
    """The wheels-shaped ``models`` rows this pin table implies:
    ``{name, filename, source_sha, sha256, bytes}``. ``filename`` is relative
    to web-repl/vendor/models/; ``source_sha`` is the pinned Hub revision.
    Order is stable (sorted by filename). Consumed by build_manifest.py.
    """
    entries = []
    for repo_rel in sorted(MODEL_FILE_PINS):
        pin = MODEL_FILE_PINS[repo_rel]
        entries.append(
            {
                "name": f"{MODEL_NAME}-{MODEL_DTYPE}",
                "filename": f"{MODEL_DIR_NAME}/{repo_rel}",
                "source_sha": MODEL_REVISION,
                "sha256": pin.get("sha256"),
                "bytes": pin["bytes"],
            }
        )
    return entries


# --- hashing -------------------------------------------------------------------


def _sha256_stream(fileobj) -> str:
    h = hashlib.sha256()
    while True:
        chunk = fileobj.read(CHUNK_SIZE)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def _sha256_file(path: Path) -> str:
    with path.open("rb") as f:
        return _sha256_stream(f)


def git_blob_sha1(data: bytes) -> str:
    """Compute git's blob object id for *data* -- the digest the Hub API
    reports for non-LFS files, so plain-text pins verify against upstream too."""
    hasher = hashlib.sha1()  # noqa: S324 -- git's object format IS sha1
    hasher.update(b"blob %d\x00" % len(data))
    hasher.update(data)
    return hasher.hexdigest()


def _verify_digest(path: Path, pin: dict) -> None:
    """Fail loud unless *path* matches its pin (size first -- cheap -- then
    the upstream-published content digest)."""
    actual_bytes = path.stat().st_size
    if actual_bytes != pin["bytes"]:
        raise FetchError(
            f"{path}: size mismatch (expected {pin['bytes']}, got {actual_bytes})"
        )
    if "sha256" in pin:
        actual = _sha256_file(path)
        if actual != pin["sha256"]:
            raise FetchError(
                f"{path}: sha256 MISMATCH (expected {pin['sha256']}, got {actual})"
            )
    else:
        actual_blob = git_blob_sha1(path.read_bytes())
        if actual_blob != pin["git_blob_sha1"]:
            raise FetchError(
                f"{path}: git-blob-sha1 MISMATCH "
                f"(expected {pin['git_blob_sha1']}, got {actual_blob})"
            )


def _check_tarball_integrity(tarball: Path, integrity: str) -> None:
    """Verify an npm tarball against its registry ``dist.integrity`` value
    (``sha512-<base64>``) BEFORE anything is extracted from it."""
    scheme, _, expected_b64 = integrity.partition("-")
    if scheme != "sha512" or not expected_b64:
        raise FetchError(f"unsupported integrity digest shape: {integrity!r}")
    actual = hashlib.sha512(tarball.read_bytes()).digest()
    if base64.b64encode(actual).decode() != expected_b64:
        raise FetchError(f"{tarball.name}: registry sha512 integrity MISMATCH")
    logger.info("tarball integrity OK (%s)", integrity[:27] + "...")


# --- HTTP -----------------------------------------------------------------------


def _http_get(url: str, *, timeout: float = 60.0) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "praxis-fetch-models/1"})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310 -- fixed https hosts
            return resp.read()
    except urllib.error.HTTPError as exc:
        raise FetchError(f"GET {url} -> HTTP {exc.code}: {exc.reason}") from exc
    except urllib.error.URLError as exc:
        raise FetchError(f"GET {url} failed: {exc.reason}") from exc


def _download_verified(
    url: str, dest_dir: Path, *, tmp_prefix: str, verify, timeout: float = 600.0
) -> tuple[Path, int]:
    """Stream *url* into a temp file in *dest_dir*, verifying as bytes arrive
    via *verify(fileobj)->None* (raise = corrupt). Returns (temp_path, bytes).
    The caller owns the atomic os.replace into its final name, so a partial or
    corrupted download can never be mistaken for a verified one."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(prefix=tmp_prefix, suffix=".tmp", dir=str(dest_dir))
    tmp_path = Path(tmp_name)
    written = 0
    req = urllib.request.Request(url, headers={"User-Agent": "praxis-fetch-models/1"})
    try:
        with os.fdopen(fd, "wb") as out, urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            while True:
                chunk = resp.read(CHUNK_SIZE)
                if not chunk:
                    break
                out.write(chunk)
                written += len(chunk)
            out.flush()
            os.fsync(out.fileno())
        with tmp_path.open("rb") as f:
            verify(f)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    return tmp_path, written


# --- --runtime: vendor transformers.js + ORT backend ----------------------------


def _extract_members(tarball: Path, members: dict[str, str], dest_root: Path) -> None:
    """Extract exactly the named tarball members into *dest_root* (mapping
    member -> relative dest path). Refuses anything outside ./package/ or with
    parent traversal -- a tarball is untrusted input."""
    with tarfile.open(tarball, "r:gz") as tf:
        present = set(tf.getnames())
        missing = [m for m in members if m not in present]
        if missing:
            raise FetchError(f"tarball {tarball.name} lacks expected member(s): {missing}")
        for member_name, rel_dest in members.items():
            if member_name.startswith("/") or ".." in Path(member_name).parts:
                raise FetchError(f"refusing unsafe tar member {member_name!r}")
            data = tf.extractfile(member_name).read()
            dest = dest_root / rel_dest
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            logger.info("extracted %-52s -> %s (%d bytes)", member_name, rel_dest, len(data))


def patch_jsdelivr_default(bundle_text: str) -> str:
    """Rewrite transformers.js's jsDelivr wasmPaths default to the local
    sibling ort/ dir. Exactly-one-match assertion: zero matches means upstream
    changed shape (new default, new host) and G5 compliance must be re-derived,
    not assumed; multiple matches mean the same. Postcondition: no 'jsdelivr'
    substring survives anywhere in the patched text."""
    matches = _JSDELIVR_WASM_PREFIX_RE.findall(bundle_text)
    if len(matches) != 1:
        raise FetchError(
            f"expected exactly 1 jsDelivr wasmPaths default in the transformers "
            f"bundle (G5 anchor), found {len(matches)} -- upstream shape changed; "
            "re-derive the substitution before vendoring."
        )
    patched = _JSDELIVR_WASM_PREFIX_RE.sub(_JSDELIVR_LOCAL_REPLACEMENT, bundle_text)
    if "jsdelivr" in patched.lower():
        raise FetchError("patched bundle still mentions jsdelivr -- refusing to vendor")
    return patched


def _assert_no_jsdelivr_tree(runtime_dir: Path) -> None:
    """G5 hygiene over everything this tree will ship to dist.

    GATE G5 greps dist for the literal ``cdn.jsdelivr.net`` and wants zero
    files -- so that exact needle is banned from EVERY file here, comments
    included (a future reader paraphrasing the gate must not be able to trip
    it). Generated files are held to the stricter standard of mentioning NO
    CDN host at all; hand-authored files may discuss jsDelivr in prose as long
    as the literal never appears."""
    offenders_g5 = [
        str(p.relative_to(runtime_dir))
        for p in sorted(runtime_dir.rglob("*"))
        if p.is_file() and b"cdn.jsdelivr.net" in p.read_bytes()
    ]
    if offenders_g5:
        raise FetchError(
            f"G5 violation: file(s) carry the cdn.jsdelivr.net literal: {offenders_g5}"
        )
    offenders_generated = []
    for p in sorted(runtime_dir.rglob("*")):
        rel = p.relative_to(runtime_dir).as_posix()
        if not p.is_file() or rel in HAND_AUTHORED_FILES or rel == VENDOR_MANIFEST_NAME:
            continue
        if b"jsdelivr" in p.read_bytes().lower():
            offenders_generated.append(rel)
    if offenders_generated:
        raise FetchError(
            f"generated runtime file(s) mention jsdelivr at all: {offenders_generated}"
        )


def _write_vendor_manifest(runtime_dir: Path, pins: dict) -> None:
    """Write VENDOR_MANIFEST.json over the CURRENT contents of *runtime_dir*
    (generated set + hand-authored extras), recording path/sha256/bytes per
    file -- the visualizer's manifest treatment, extended with a ``tracked``
    flag because this tree deliberately contains one fetched binary."""

    def role(rel: str) -> str:
        if rel == VENDOR_MANIFEST_NAME:
            return "manifest"
        if rel in HAND_AUTHORED_FILES:
            return "hand-authored"
        if rel.endswith(RUNTIME_UNTRACKED_SUFFIXES):
            return "fetched-binary-untracked"
        return "vendored-lib"

    files = []
    for path in sorted(runtime_dir.rglob("*")):
        if not path.is_file() or path.name == VENDOR_MANIFEST_NAME:
            continue
        rel = path.relative_to(runtime_dir).as_posix()
        files.append(
            {
                "path": rel,
                "sha256": _sha256_file(path),
                "bytes": path.stat().st_size,
                "tracked": role(rel) != "fetched-binary-untracked",
                "role": role(rel),
            }
        )
    record = {
        "generator": "fetch_models.py --runtime",
        "generator_version": GENERATOR_VERSION,
        "generated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "pins": pins,
        "files": files,
    }
    fd, tmp_name = tempfile.mkstemp(
        prefix=".vendor-manifest-", suffix=".json.tmp", dir=str(runtime_dir)
    )
    tmp_path = Path(tmp_name)
    try:
        with os.fdopen(fd, "w") as f:
            json.dump(record, f, indent=2)
            f.write("\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp_path, 0o644)
        os.replace(tmp_path, runtime_dir / VENDOR_MANIFEST_NAME)
    except BaseException:
        tmp_path.unlink(missing_ok=True)
        raise
    total = sum(f["bytes"] for f in files)
    logger.info(
        "wrote %s (%d file(s), %.1f MB total)", VENDOR_MANIFEST_NAME, len(files), total / 1e6
    )


def vendor_runtime(
    *, runtime_dir: Path, scratch_dir: Path, force: bool
) -> Path:
    """Fetch, verify, patch, and publish the vendored runtime. Idempotent:
    re-runs rebuild the generated set from the pinned tarballs (cheap, ~28 MB);
    hand-authored files are never touched."""
    runtime_dir.mkdir(parents=True, exist_ok=True)
    for rel in HAND_AUTHORED_FILES:  # refuse to run into a broken contract
        if not (runtime_dir / rel).is_file():
            logger.warning(
                "%s not yet present under %s (hand-authored, ships separately)",
                rel,
                runtime_dir,
            )

    scratch_dir.mkdir(parents=True, exist_ok=True)
    pins = {
        "transformers.js": {
            "npm": "@huggingface/transformers",
            "version": TRANSFORMERS_VERSION,
            "tarball_sha512": TRANSFORMERS_TARBALL_SHA512,
        },
        "onnxruntime-web": {
            "npm": "onnxruntime-web",
            "version": ORT_WEB_VERSION,
            "tarball_sha512": ORT_WEB_TARBALL_SHA512,
        },
        "substitutions": [
            {
                "what": "wasmPaths jsDelivr default -> ./ort/",
                "why": "GATE G5 forbids the jsDelivr CDN host anywhere in dist",
                "matches_expected": 1,
            }
        ],
    }

    hf_tgz = scratch_dir / f"transformers-{TRANSFORMERS_VERSION}.tgz"
    ort_tgz = scratch_dir / f"onnxruntime-web-{ORT_WEB_VERSION}.tgz"

    def _fetch_tarball(url: str, dest: Path, integrity: str) -> None:
        if dest.is_file():
            try:
                _check_tarball_integrity(dest, integrity)
                logger.info("cached tarball OK: %s", dest.name)
                return
            except FetchError:
                if not force:
                    logger.warning("%s failed re-verification; refetching", dest)
                dest.unlink()
        tmp, _ = _download_verified(
            url,
            dest.parent,
            tmp_prefix=".tgz-",
            verify=lambda f: _check_tarball_integrity_hash(f, integrity),
        )
        os.replace(tmp, dest)

    _fetch_tarball(
        NPM_TRANSFORMERS_URL.format(version=TRANSFORMERS_VERSION), hf_tgz, TRANSFORMERS_TARBALL_SHA512
    )
    _fetch_tarball(NPM_ORT_WEB_URL.format(version=ORT_WEB_VERSION), ort_tgz, ORT_WEB_TARBALL_SHA512)

    extract_root = scratch_dir / "extract"
    if extract_root.exists():
        shutil.rmtree(extract_root)
    extract_root.mkdir(parents=True)
    hf_members = {m: d for m, d in RUNTIME_FILES.items() if m.startswith("package/dist/transformers")}
    ort_members = {m: d for m, d in RUNTIME_FILES.items() if m.startswith("package/dist/ort-")}
    _extract_members(hf_tgz, hf_members, extract_root)
    _extract_members(ort_tgz, ort_members, extract_root)

    # Patch the G5 anchor BEFORE publishing; publish atomically per file.
    staged_bundle = extract_root / RUNTIME_FILES["package/dist/transformers.min.js"]
    patched = patch_jsdelivr_default(staged_bundle.read_text(encoding="utf-8"))
    staged_bundle.write_text(patched, encoding="utf-8")

    for member, rel_dest in RUNTIME_FILES.items():
        src = extract_root / rel_dest
        dest = runtime_dir / rel_dest
        dest.parent.mkdir(parents=True, exist_ok=True)
        # scratch/ and runtime_dir may be different mounts -- never os.replace
        # across them; copy to a temp sibling of DEST and rename there.
        fd, tmp_name = tempfile.mkstemp(prefix=".publish-", dir=str(dest.parent))
        os.close(fd)
        tmp_dest = Path(tmp_name)
        try:
            shutil.copyfile(src, tmp_dest)
            os.chmod(tmp_dest, 0o644)
            os.replace(tmp_dest, dest)
        except BaseException:
            tmp_dest.unlink(missing_ok=True)
            raise
        logger.info("published %s (%d bytes)", rel_dest, dest.stat().st_size)

    _assert_no_jsdelivr_tree(runtime_dir)
    _write_vendor_manifest(runtime_dir, pins)
    return runtime_dir


def _check_tarball_integrity_hash(fileobj, integrity: str) -> None:
    """Like _check_tarball_integrity but over an open stream (download path)."""
    scheme, _, expected_b64 = integrity.partition("-")
    if scheme != "sha512":
        raise FetchError(f"unsupported integrity scheme: {scheme!r}")
    h = hashlib.sha512()
    while True:
        chunk = fileobj.read(CHUNK_SIZE)
        if not chunk:
            break
        h.update(chunk)
    if base64.b64encode(h.digest()).decode() != expected_b64:
        raise FetchError("registry sha512 integrity MISMATCH on streamed tarball")


# --- --models: fetch the pinned q4f16 export ------------------------------------


def model_dest_dir(models_dir: Path) -> Path:
    return models_dir / MODEL_DIR_NAME


def _model_url(repo_rel: str) -> str:
    return HF_RESOLVE_URL.format(repo=MODEL_REPO_ID, revision=MODEL_REVISION, filename=repo_rel)


def fetch_model_file(models_dir: Path, repo_rel: str, *, force: bool) -> Path:
    """Download one pinned file (unless a verified copy is already on disk)."""
    pin = MODEL_FILE_PINS[repo_rel]
    dest = model_dest_dir(models_dir) / repo_rel
    if dest.is_file() and not force:
        try:
            _verify_digest(dest, pin)
            logger.info("OK (cached, verified): %s", repo_rel)
            return dest
        except FetchError:
            logger.warning("%s exists but fails its pin -- refetching", dest)
    url = _model_url(repo_rel)

    def _verify_stream(fileobj) -> None:
        data = bytearray()
        while True:
            chunk = fileobj.read(CHUNK_SIZE)
            if not chunk:
                break
            data.extend(chunk)
        if len(data) != pin["bytes"]:
            raise FetchError(
                f"{repo_rel}: downloaded {len(data)} bytes, expected {pin['bytes']}"
            )
        if "sha256" in pin:
            actual = hashlib.sha256(data).hexdigest()
            if actual != pin["sha256"]:
                raise FetchError(
                    f"{repo_rel}: sha256 MISMATCH (expected {pin['sha256']}, got {actual})"
                )
        else:
            actual_blob = git_blob_sha1(bytes(data))
            if actual_blob != pin["git_blob_sha1"]:
                raise FetchError(
                    f"{repo_rel}: git-blob-sha1 MISMATCH "
                    f"(expected {pin['git_blob_sha1']}, got {actual_blob})"
                )

    tmp_path, written = _download_verified(url, dest.parent, tmp_prefix=f".{MODEL_DTYPE}-", verify=_verify_stream)
    os.replace(tmp_path, dest)
    logger.info("fetched + verified %-32s (%d bytes)", repo_rel, written)
    return dest


def check_models(models_dir: Path) -> bool:
    """Offline verification of fetched models against the pin table."""
    problems = []
    for repo_rel, pin in sorted(MODEL_FILE_PINS.items()):
        dest = model_dest_dir(models_dir) / repo_rel
        if not dest.is_file():
            problems.append(f"missing: {dest}")
            continue
        try:
            _verify_digest(dest, pin)
        except FetchError as exc:
            problems.append(str(exc))
    if problems:
        for p in problems:
            logger.error("MODEL PIN MISMATCH: %s", p)
        return False
    total = EXPECTED_MODEL_TOTAL_BYTES
    logger.info(
        "models OK: %d file(s), %.1f MB all match upstream pins (%s@%s)",
        len(MODEL_FILE_PINS),
        total / 1e6,
        MODEL_REPO_ID,
        MODEL_REVISION[:12],
    )
    return True


def check_runtime(runtime_dir: Path) -> bool:
    """Offline verification of the vendored runtime against VENDOR_MANIFEST.json."""
    manifest_path = runtime_dir / VENDOR_MANIFEST_NAME
    if not manifest_path.is_file():
        logger.error("%s missing -- run --runtime first", manifest_path)
        return False
    record = json.loads(manifest_path.read_text())
    problems = []
    for entry in record["files"]:
        path = runtime_dir / entry["path"]
        if not path.is_file():
            problems.append(f"missing: {entry['path']}")
            continue
        if path.stat().st_size != entry["bytes"]:
            problems.append(f"size drift: {entry['path']}")
            continue
        actual = _sha256_file(path)
        if actual != entry["sha256"]:
            problems.append(f"sha256 drift: {entry['path']}")
    if problems:
        for p in problems:
            logger.error("RUNTIME PIN MISMATCH: %s", p)
        return False
    logger.info("runtime OK: %d file(s) match VENDOR_MANIFEST.json", len(record["files"]))
    return True


# --- CLI -----------------------------------------------------------------------


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument(
        "--runtime",
        action="store_true",
        help="Vendor @huggingface/transformers + ORT wasm into "
        "overlay/assets/coxswain/vendor/ (tracked lib files + VENDOR_MANIFEST.json).",
    )
    parser.add_argument(
        "--models",
        action="store_true",
        help="Fetch the pinned q4f16 FunctionGemma ONNX export into "
        "gitignored vendor/models/.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Shorthand for --runtime --models.",
    )
    parser.add_argument("--force", action="store_true", help="Re-download even if verified copies exist.")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify already-present runtime + models against the pins offline. Exits 1 on any mismatch.",
    )
    parser.add_argument("--web-repl-root", type=Path, default=DEFAULT_WEB_REPL_ROOT, help="Override web-repl/ root (testing only).")
    parser.add_argument("--runtime-dir", type=Path, default=None, help="Override runtime vendor dir (testing only).")
    parser.add_argument("--models-dir", type=Path, default=None, help="Override models dir (default <root>/vendor/models).")
    parser.add_argument("--scratch-dir", type=Path, default=None, help="Override scratch dir for tarballs/extraction (default system temp).")
    parser.add_argument("-v", "--verbose", action="store_true", help="Debug-level logging.")
    args = parser.parse_args(argv)
    if not (args.runtime or args.models or args.all or args.check):
        parser.error("nothing to do: pass --runtime, --models, --all, or --check")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(levelname)s %(name)s: %(message)s",
    )
    web_repl_root = args.web_repl_root.resolve()
    runtime_dir = (args.runtime_dir or DEFAULT_RUNTIME_VENDOR_DIR).resolve()
    models_dir = (args.models_dir or (web_repl_root / "vendor" / "models")).resolve()

    do_runtime = args.runtime or args.all
    do_models = args.models or args.all

    try:
        if args.check:
            ok = True
            if runtime_dir.is_dir():
                ok &= check_runtime(runtime_dir)
            if models_dir.is_dir():
                ok &= check_models(models_dir)
            if not runtime_dir.is_dir() and not models_dir.is_dir():
                logger.error("nothing to check: neither %s nor %s exists", runtime_dir, models_dir)
                ok = False
            return 0 if ok else 1
        if do_runtime:
            scratch = (args.scratch_dir or Path(tempfile.gettempdir()) / "praxis-fetch-models").resolve()
            vendor_runtime(runtime_dir=runtime_dir, scratch_dir=scratch, force=args.force)
        if do_models:
            for repo_rel in sorted(MODEL_FILE_PINS):
                fetch_model_file(models_dir, repo_rel, force=args.force)
            if not check_models(models_dir):
                return 1
    except FetchError as exc:
        logger.error("%s", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
