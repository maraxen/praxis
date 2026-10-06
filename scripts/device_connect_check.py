#!/usr/bin/env python3
"""Real-browser check of the device-connect journey: ``await lh.setup()`` on a
Hamilton STAR, in the built REPL, must reach the browser's USB picker.

What it guards (2026-10-06): constructing ``STARBackend()`` worked, but
``lh.setup()`` waited forever with no picker, because nothing on the page answered
the kernel's ``device_connect`` request. The shim contract gate and the unit tests
stopped at construction; only someone with a robot found it. This drives the whole
path the user takes, on the real built page:

  kernel ``lh.setup()`` -> WebUSB shim -> web_bridge USER_INTERACTION ->
  shell/device/connect.js dialog -> click Connect -> ``navigator.usb.requestDevice``
  -> answer -> kernel continues.

The page's ``navigator.usb.requestDevice`` is replaced by a recorder (no hardware in
CI), so the picker "returns" a device the worker cannot see. The expected outcome
is therefore the shim's own "No matching USB device" error, reached AFTER the
picker was asked for exactly the STAR's vendor/product id. That proves the round
trip; a hang (the original bug) times out and fails.

``--block-handler`` is the negative control: it blocks ``shell/device/connect.js``
from loading, and the kernel must then fail fast with
``InteractionUnavailableError`` (no hang, no picker). A run of the check that cannot
tell these two apart is not a check.

Targets:
  * ``--dist DIR --base-path /praxis/``: serve a local build (CI, before publishing).
  * ``--url https://maraxen.github.io/praxis/``: the deployed site (after a Pages
    deploy). ``--expect-sha`` first waits until the live manifest carries that
    commit, so a CDN still serving the previous deploy is not mistaken for a pass.

Exit 0 only when the observed outcome is the expected one. Prints a JSON report.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import urllib.parse
import urllib.request
from contextlib import nullcontext
from pathlib import Path
from typing import Any

LOG = logging.getLogger("device_connect_check")
REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DIST = REPO_ROOT / "web-repl" / "dist"

STAR_VENDOR_ID = 0x08AF
STAR_PRODUCT_ID = 0x8000
CONNECT_SELECTOR = '[data-praxis-interaction="device_connect"] [data-action="connect"]'
DEVICE_MODULE_GLOB = "**/shell/device/connect.js"

# Split so the contiguous markers exist only in printed output, never in the echoed
# cell source (the repl/ entry echoes ?code= before running it).
_BEGIN = ("@@DEVICE_CHECK", "_BEGIN@@")
_END = ("@@DEVICE_CHECK", "_END@@")
BEGIN, END = "".join(_BEGIN), "".join(_END)

KERNEL_CODE = f"""
import json, time, traceback
_t0 = time.monotonic()
_out = {{}}
try:
    from pylabrobot.liquid_handling import LiquidHandler
    from pylabrobot.liquid_handling.backends.hamilton.STAR_backend import STARBackend
    from pylabrobot.resources.hamilton import STARLetDeck
    lh = LiquidHandler(backend=STARBackend(), deck=STARLetDeck())
    _out["io_class"] = type(lh.backend.io).__name__
    await lh.setup()
    _out["outcome"] = "setup-returned"
except Exception as e:
    _out["outcome"] = "raised"
    _out["error_type"] = type(e).__name__
    _out["error"] = str(e)
    _out["traceback"] = traceback.format_exc()[-2000:]
_out["seconds"] = round(time.monotonic() - _t0, 2)
print({_BEGIN[0]!r} + {_BEGIN[1]!r} + json.dumps(_out) + {_END[0]!r} + {_END[1]!r})
"""

# Runs on the PAGE (not the kernel's worker): record picker calls, return a device
# the worker cannot see. Defined even where headless Chromium lacks navigator.usb.
PICKER_RECORDER = """
(() => {
  window.__pickerCalls = [];
  const fake = (options) => {
    window.__pickerCalls.push(JSON.parse(JSON.stringify(options || {})));
    return Promise.resolve({ vendorId: 0x08af, productId: 0x8000, productName: "fake STAR", serialNumber: "CI" });
  };
  try {
    if (navigator.usb) {
      Object.defineProperty(navigator.usb, "requestDevice", { value: fake, configurable: true });
    } else {
      Object.defineProperty(navigator, "usb", {
        value: { requestDevice: fake, getDevices: () => Promise.resolve([]) },
        configurable: true,
      });
    }
  } catch (err) {
    window.__pickerRecorderError = String(err);
  }
})();
"""


def wait_for_live_sha(root_url: str, sha: str, timeout_s: float) -> str:
  """Poll the live manifest until it carries *sha* (Pages caches for ~10 min)."""
  deadline = time.monotonic() + timeout_s
  seen = None
  while True:
    url = f"{root_url}assets/wheels/manifest.json?cb={int(time.time())}"
    try:
      with urllib.request.urlopen(url, timeout=30) as resp:
        seen = json.load(resp).get("praxis_git_sha")
    except Exception as exc:  # keep polling: a transient fetch error is not a verdict
      LOG.warning("manifest fetch failed: %s", exc)
    if seen == sha:
      return seen
    if time.monotonic() > deadline:
      raise SystemExit(f"live manifest still at {seen!r}, expected {sha!r} after {timeout_s:g}s")
    LOG.info("live manifest at %r, waiting for %r", seen, sha)
    time.sleep(20)


def run(args: argparse.Namespace) -> dict[str, Any]:
  from playwright.sync_api import sync_playwright

  if args.url:
    root = args.url if args.url.endswith("/") else args.url + "/"
    if args.expect_sha:
      wait_for_live_sha(root, args.expect_sha, args.sha_wait)
    served = nullcontext(None)
  else:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    from repl_smoke import ServedDir, _normalize_base_path

    prefix = _normalize_base_path(args.base_path)
    served = ServedDir(Path(args.dist), prefix, coi=False)

  report: dict[str, Any] = {"block_handler": args.block_handler}
  with served as server:
    if server is not None:
      root = f"http://127.0.0.1:{server.port}{_normalize_base_path(args.base_path)}"
    report["root"] = root
    params = urllib.parse.urlencode(
      {"kernel": "python", "toolbar": "1", "execute": "1", "code": KERNEL_CODE}
    )
    url = f"{root}{args.entry}/index.html?{params}"

    with sync_playwright() as p:
      browser = p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
      try:
        context = browser.new_context()
        page = context.new_page()
        page.add_init_script(PICKER_RECORDER)
        console: list[str] = []
        page.on("console", lambda m: console.append(f"{m.type}: {m.text}"))
        if args.block_handler:
          page.route(DEVICE_MODULE_GLOB, lambda route: route.abort())

        page.goto(url, wait_until="load", timeout=args.timeout * 1000)
        deadline = time.monotonic() + args.timeout
        clicked = False
        body = ""
        while time.monotonic() < deadline:
          if not clicked and not args.block_handler:
            button = page.query_selector(CONNECT_SELECTOR)
            if button is not None:
              report["dialog_text"] = page.inner_text(
                '[data-praxis-interaction="device_connect"] p'
              )
              button.click()  # a real, trusted user gesture
              clicked = True
          body = page.evaluate("() => document.body.innerText")
          if END in body:
            break
          page.wait_for_timeout(500)
        report["clicked_connect"] = clicked
        report["picker_calls"] = page.evaluate("() => window.__pickerCalls || []")
        report["picker_recorder_error"] = page.evaluate(
          "() => window.__pickerRecorderError || null"
        )
        if END in body:
          report["kernel"] = json.loads(body[body.rindex(BEGIN) + len(BEGIN) : body.rindex(END)])
        else:
          report["kernel"] = None
          report["page_tail"] = body[-3000:]
          report["console_tail"] = console[-40:]
      finally:
        browser.close()
  return report


def verdict(report: dict[str, Any]) -> list[str]:
  """Problems with the observed outcome; empty means the check passed."""
  k = report.get("kernel")
  if k is None:
    return ["lh.setup() never finished within the timeout (the original hang)"]
  problems: list[str] = []
  if k.get("io_class") != "WebUSB":
    problems.append(f"STARBackend().io is {k.get('io_class')!r}, not the WebUSB shim")
  if report["block_handler"]:
    if k.get("error_type") != "InteractionUnavailableError":
      problems.append(f"expected InteractionUnavailableError with the handler blocked, got {k}")
    if report["picker_calls"]:
      problems.append("the picker opened although the handler was blocked")
    if k.get("seconds", 0) > 60:
      problems.append(f"failing took {k['seconds']}s; it must be fast")
    return problems
  expected = [{"filters": [{"vendorId": STAR_VENDOR_ID, "productId": STAR_PRODUCT_ID}]}]
  if not report["clicked_connect"]:
    problems.append("the device_connect dialog never appeared")
  if report["picker_calls"] != expected:
    problems.append(f"picker calls {report['picker_calls']!r}, expected {expected!r}")
  if k.get("outcome") != "raised" or "No matching USB device" not in (k.get("error") or ""):
    problems.append(
      "expected the shim's 'No matching USB device' error after authorization "
      f"(the fake device is invisible to the worker), got {k}"
    )
  return problems


def main(argv: list[str] | None = None) -> int:
  ap = argparse.ArgumentParser(
    description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
  )
  target = ap.add_mutually_exclusive_group()
  target.add_argument(
    "--dist", default=str(DEFAULT_DIST), help="local build to serve (default: web-repl/dist)"
  )
  target.add_argument("--url", help="deployed site root, e.g. https://maraxen.github.io/praxis/")
  ap.add_argument(
    "--base-path", default="/praxis/", help="path prefix the local build was built for"
  )
  ap.add_argument("--entry", default="repl", help="entry app to drive (default: repl)")
  ap.add_argument(
    "--block-handler", action="store_true", help="negative control: block shell/device/connect.js"
  )
  ap.add_argument(
    "--expect-sha", help="with --url: wait until the live manifest carries this commit"
  )
  ap.add_argument("--sha-wait", type=float, default=900, help="seconds to wait for --expect-sha")
  ap.add_argument("--timeout", type=float, default=240, help="seconds for boot + setup")
  args = ap.parse_args(argv)
  logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")

  report = run(args)
  problems = verdict(report)
  report["problems"] = problems
  report["passed"] = not problems
  print(json.dumps(report, indent=2))
  return 0 if not problems else 1


if __name__ == "__main__":
  sys.exit(main())
