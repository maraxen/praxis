---
title: GATE G2 — spike battery verdict
description: Adjudication of the five G2 criteria from spikes S-A/S-B/S-C/S-D/S-E/S-F, with independent spot-check output; overall PARTIAL-GO.
category: research
task_id: 260817_praxis_repl_refocus
status: complete
date: 260817
---

# GATE G2 — spike battery verdict

**Overall: PARTIAL-GO.** Criteria 1–4 PASS. Criterion 5 is **UNMET** (not measured — no human, no device).

Two of the four passes carry a **named mandatory precondition** that must land before the dependent
work ships. Criterion 5 being UNMET hard-blocks Phase 5's `praxis-shell.js` work and leaves the
B-prime-vs-Design-A architecture choice open. It does not block Phases 2, 3, 4, or 6.

This record is an adjudication, not a relay. Every load-bearing claim below was **re-verified by the
adjudicator** against raw artifacts, the shipped bundle, or the submodule at read-only SHAs. Where a
spike's reasoning did not survive that check, it is corrected here rather than repeated.

---

## Verdict table

| # | Criterion | Spike | Verdict | Gating consequence |
|---|---|---|---|---|
| 1 | websockets in Pyodide | S-A | **PASS** *(requires a one-line bootstrap fix)* | Visualizer constructible at 0.2.2 |
| 2 | WebLoop shim viability | S-A | **PASS** | T2.2 fallback **not** needed |
| 3 | PLR 0.2.2 boots in Pyodide | S-B | **PASS** | **Phase 4 may happen** |
| 4 | `contentsStorageName` overrides | S-C | **PASS** *(with a 3-key amendment)* | T08 migration viable as designed + amendment |
| 5 | S0 gesture chain | S-E | **UNMET** | **Phase 5 blocked**; architecture undecided |

Supporting spikes S-D (viz handoff) and S-F (blast radius) are not G2 criteria but changed two
downstream recommendations; both are recorded in §6.

---

## Criterion 1 — websockets in Pyodide → **PASS**, conditional on a named fix

**Bare, as currently deployed: FAIL.** No install, no websockets.

```
websockets_import = {"error": "ModuleNotFoundError: No module named 'websockets'", "ok": false}
websockets_asyncio_server_import = {"error": "ModuleNotFoundError: No module named 'websockets'", "ok": false}
plr_HAS_WEBSOCKETS = false
pylabrobot_visualizer_import = {"ok": true}
```
<sub>`sa_result.json` — adjudicator-read.</sub>

**Per the transport-shim spec's own T0.1 method (`micropip.install("websockets")` first): full PASS.**

```
micropip_install_websockets = {"ok": true}
websockets_import = {"file": "/lib/python3.14/site-packages/websockets/__init__.py", "ok": true, "version": "17.0.1"}
websockets_asyncio_server_import = {"ok": true}
websockets_legacy_server_import = {"ok": true}
plr_HAS_WEBSOCKETS = true
plr_websockets_import_error_attr = "None"
pylabrobot_visualizer_import = {"ok": true}
pageerrors = []
```
<sub>`sa_result3.json` — adjudicator-read. websockets is pure-Python and micropip-installable; it was never a native-code blocker, it was simply never requested.</sub>

**Why the install is mandatory, not optional — adjudicator-verified.** At 0.2.2 the guard is inside
`__init__`, so the viz spec's `setup()` override does **not** rescue a False flag:

```
$ git -C external/pylabrobot show dd79c4c8…:pylabrobot/visualizer/visualizer.py | grep -n 'HAS_WEBSOCKETS\|^class \|  def '
20:  HAS_WEBSOCKETS = True
22:  HAS_WEBSOCKETS = False
99:class Visualizer:
113:  def __init__(
144:    if not HAS_WEBSOCKETS:
218:  def websocket(
```
`:144` sits between `__init__` (`:113`) and the next member (`:218`) — the raise is in the constructor,
exactly as the criterion stated.

**Consequence.** Neither documented fallback is required. A stub `websockets` is **not** needed, and
holding the visualizer at the old pin is **not** needed. The fix is one line added to
`praxis_bootstrap.py`'s install step, mirroring the existing `pylibftdi` wheel precedent:

```python
await micropip.install("websockets")
```

**This fix has not been made.** No repo file was touched by any spike. Criterion 1's PASS is a pass of
the *mechanism*; it becomes a pass of the *product* only when that line lands.

**SUPERSEDED 260818 — the one-line fix above is NOT what shipped, and should not ship.** This
section's own §9 already named the exact failure mode: *"Criterion 1 → FAIL if
`micropip.install("websockets")` proves unavailable in the offline/vendored configuration (all
evidence here is CDN/PyPI-reachable)."* GATE G5 (execution plan, PHASE 5) mandates exactly that
configuration — chromium `--host-resolver-rules` blackholing `cdn.jsdelivr.net`, `pypi.org`, and
`files.pythonhosted.org` — so a boot-time `await micropip.install("websockets")` against live PyPI
would pass this criterion while setting up a G5 failure. Decided and implemented instead: **vendor
`websockets-17.0.1-py3-none-any.whl`** into `web-repl/overlay/assets/wheels/` (sha256
`c6be9cba65c65cc76dfa3d4619e359ff02a4476c74e179b215236c11a0b32345`, verified against PyPI's own
published digest) and let the *existing* D2 manifest-driven wheel pipeline install it —
`build_manifest.py`'s `collect_wheels()` already globs every `*.whl` in that directory with no
allowlist, and `praxis_bootstrap.py`'s wheel-install loop already `micropip.install()`s every
`manifest["wheels"]` entry with `deps=False`. Zero code changes were needed in either file. Full
reasoning, the three-way option comparison (boot-time PyPI fetch / stub / vendored wheel), and literal
verification output live in
`.praxia/docs/specs/260817_spec-visualizer-transport-shim.md` under "Decision: the `websockets` hard
dependency is met by a VENDORED WHEEL". Criterion 1's verdict (**PASS**) is unaffected — only the
*mechanism* satisfying it changed, from a boot-time fetch to a vendored, D2-covered artifact.

---

## Criterion 2 — WebLoop shim viability → **PASS**

```
loop_module = "pyodide.webloop"   loop_type = "WebLoop"
call_soon                = {"present": true, "callable": true, "call_result": "ok"}
call_soon_threadsafe     = {"present": true, "callable": true, "call_result": "ok"}
create_future            = {"present": true, "callable": true, "call_result": "ok", "returned_type": "PyodideFuture"}
create_task              = {"present": true, "callable": true, "call_result": "ok", "task_done_after_yield": true}
run_until_complete       = {"present": true, "callable": true, "call_result": "ok"}
run_coroutine_threadsafe_MODULE_LEVEL = {"present_as_module_function": true,
   "present_as_loop_method": false, "callable": true, "call_result": "ok",
   "returned_type": "Future", "resolved_value": 1}
add_reader = {"present": true, "callable": true, "call_result": "raised",
   "call_error": "NotImplementedError: add_reader() is not available in browser environments…"}
```
<sub>`sa_result3.json` — adjudicator-read.</sub>

**S-A's probe-design correction is accepted and independently checked.** `run_coroutine_threadsafe` is a
module-level `asyncio` function on *any* CPython loop, never a bound loop method; testing
`getattr(loop, …)` would have produced a false "absent" attributable to nothing. PLR calls the
module-level form, and that form works natively — `resolved_value: 1` shows the coroutine's real return
value crossed the future.

**`add_reader` is not load-bearing — adjudicator-verified at both SHAs:**

```
$ git -C external/pylabrobot show HEAD:pylabrobot/visualizer/visualizer.py | grep -c add_reader
0
$ git -C external/pylabrobot show dd79c4c8…:pylabrobot/visualizer/visualizer.py | grep -c add_reader
0
```

**Consequence.** All four members the inherited callbacks touch work unshimmed. **Viz task T2.2 does
NOT take the documented +30-line callback-override fallback.**

---

## Criterion 3 — PLR 0.2.2 boots in Pyodide → **PASS**

```
praxis_ready = true
pylabrobot_version = "0.2.2+gdd79c4c8"
pylabrobot_file = "/lib/python3.14/site-packages/pylabrobot/__init__.py"
storage_Incubator_resolves = true
storage_Incubator_repr = "<class 'pylabrobot.storage.incubator.Incubator'>"
legacy_pylabrobot_incubator_resolves = false
legacy_pylabrobot_incubator_error = "ModuleNotFoundError: No module named 'pylabrobot.incubator'"
contract_all_resolve = false      contract_failures = ["pylabrobot.visualizer"]
contract ok count = 27            fail = ['pylabrobot.visualizer']
bare_import_websockets = {"error": "ModuleNotFoundError: No module named 'websockets'", "ok": false}
```
<sub>`S-B/result_sb_rerun.json` — adjudicator-read. `result_sb.json` and `result_sb_rerun.json` were confirmed to **differ** (`cmp` → "differ: byte 320, line 11"), so the rerun is a genuine second execution, not a restated artifact.</sub>

**The single contract "failure" is a namespace artifact, and the adjudicator found independent
corroboration S-B did not cite.** The same result file records `visualizer_HAS_WEBSOCKETS = false` — a
value that cannot be read off a module that failed to import. So `pylabrobot.visualizer.visualizer`
imported successfully; only the parent-package `hasattr` binding was absent. Not an import failure.

**The `+local` version survives micropip end-to-end**, with the `+` unescaped in the URL:

```
http://127.0.0.1:46287/assets/wheels_022/pylabrobot-0.2.2+gdd79c4c8-py3-none-any.whl
```

**`deps=False` prevents the websockets fetch.** Adjudicator filtered all 315 request-log entries; exactly
3 touch PyPI hosts and none is websockets or pylabrobot:

```
https://pypi.org/simple/comm/
https://files.pythonhosted.org/packages/…/comm-0.2.3-py3-none-any.whl.metadata
https://files.pythonhosted.org/packages/…/comm-0.2.3-py3-none-any.whl
```
The literal "zero PyPI requests" assertion is therefore **unmet**, for a pre-existing `comm`/ipykernel
reason unrelated to the version bump. The *risk* the assertion existed to catch — a live websockets
fetch — is confirmed absent.

**Caveats are pre-existing, not 0.2.2 regressions — adjudicator cross-checked against Phase 1:**

```
result_sb_rerun (0.2.2+gdd79c4c8): flags={"HAS_PYLIBFTDI":true,"HAS_SERIAL":true,"USE_HID":false,"USE_USB":false}
                                   io_id={"ftdi":true,"hid":true,"serial":false,"usb":false}
baseline-prechange (0.1.6):        flags={…identical…}  io_id={…identical…}
g1-final           (0.1.6):        flags={…identical…}  io_id={…identical…}
```
The serial/usb two-class-object defect and the two False capability flags reproduce **exactly**. 0.2.2
neither causes nor fixes them.

**S-B's "pyodide version deviation" surprise is retired — it is not a deviation.** The adjudicator
checked the shipped tree: there is no `pyodideUrl` override in `jupyter-lite.json`, and the vendored
kernel extension's own schema hardcodes the default:

```
…/pyodide-kernel-extension/static/schema/kernel.v0.schema.json:11:
  "default": "https://cdn.jsdelivr.net/pyodide/v314.0.1/full/pyodide.mjs"
```
So **v314.0.1 / CPython 3.14.2 is what production serves today**; the "v0.29.0 / 3.13.2" figure in the
brief and prior docs is stale. This *removes* a would-be caveat: S-A and S-B ran on the production
runtime, not a scratch-only one. The residual risk is that the runtime is pinned by a vendored bundle
rather than by our config — worth an explicit pin, but not a G2 blocker.

**Consequence. Phase 4 (the pin bump) is NOT blocked.** The pipeline is not forced to ship at 0.1.6 on
the evidence of criterion 3.

---

## Criterion 4 — `contentsStorageName` actually overrides → **PASS, with a 3-key amendment**

**Proven BY CONTENT, in both runs** — the spike1d trap (same visible name, still-isolated stores) is
disproven, not merely avoided:

```
mount_a_write = {"ok": true, "saved_path": "shared.txt", "immediate_readback": "FROM_MOUNT_A"}
mount_b_read  = {"ok": true, "found": true, "path": "shared.txt", "content": "FROM_MOUNT_A"}
content_crossed_mounts = true
```
<sub>Present and identical in **both** `spike_c_result.json` and `spike_c2_result.json` — adjudicator-read. Two mounts (`/mount-a/`, `/mount-b/`) on one origin, one persistent profile.</sub>

**S-C's amendment is real and the adjudicator confirmed it in the *shipped repo build*, not the scratch
copy.** All three storage keys are read with the same `getOption(...)||default` shape:

```
$ grep -roh '.\{160\}getOption("contentsStorageName").\{0,40\}' build/8262.7bb3dc3.js
…let r=n.PageConfig.getOption("baseUrl"),i=`JupyterLite Storage - ${r}`,
  s=n.PageConfig.getOption("contentsStorageName")||i,…

$ grep -roh '.\{200\}getOption("workspacesStorageName").\{0,40\}' build/8262.7bb3dc3.js
…workspace manager plugin.",…activate:(e,t)=>{let r=n.PageConfig.getOption("baseUrl"),
  i=`JupyterLite Storage - ${r}`,a=n.PageConfig.getOption("workspacesStorageName")||i,…
```
When set, the literal is used with **no baseUrl suffix** — the override is genuinely load-bearing.
But `workspacesStorageName` is a **third** key that the criterion's stated method (contents + settings
only) omits. With two keys, orphaned per-baseUrl databases remain:

```
run 1 (2 keys):  all_indexeddb_database_names_observed =
   ["JupyterLite Storage - /mount-a/", "JupyterLite Storage - /mount-b/", "praxis-repl-contents"]
   legacy_pattern_database_names = [2 entries]   store_enumeration_clean = false   VERDICT "FAIL"

run 2 (3 keys):  all_indexeddb_database_names_observed = ["praxis-repl-contents"]
   legacy_pattern_database_names = []            store_enumeration_clean = true    VERDICT "PASS"
```

**Adjudication.** S-C returned PARTIAL because its literally-instructed 2-key method failed its own
enumeration bar. As a G2 criterion the question is whether `contentsStorageName` *actually overrides* —
it does, proven by content, and the enumeration bar is fully met once the third key is pinned. The gap
is in the criterion's config recipe, not in the mechanism. **Criterion 4 = PASS**, with the amendment
binding.

**Consequence for the ADR.** §5.5 says the path move is not authorised "until `contentsStorageName` is
explicitly pinned in `jupyter-lite.json` and the migration lands in the same commit as the path move."
That precondition's *evidence* half is now satisfied — the pin demonstrably works. **§5.5 and T08 must be
amended to name all three keys:**

```
contentsStorageName, settingsStorageName, workspacesStorageName
```

Pinning only `contentsStorageName` will migrate content correctly and still strand workspace databases.
The "migration lands in the same commit" half of §5.5 remains an execution requirement, unchanged.

---

## Criterion 5 — S0 gesture chain → **UNMET**

**Not measured.** S-E authored a runnable driver and a human protocol; the spike itself requires a human
and a physical device and was not run.

```
{"api": "serial", "topologies": {"toplevel":
  {"api": "serial", "pageerrors": [], "pause_only": true, "reached_pause_point": false, "topology": "toplevel"}}}
```
<sub>`S-E/xvfb_selfcheck_result.json` — adjudicator-read. Even the headless self-check did not reach the human pause point across 4 attempts (Pyodide boot was clean, `pageerrors: []`, but the kernel never posted the `device_connect` interaction in budget).</sub>

**Recorded as UNMET, not FAIL and not BLOCKED.** UNMET means not yet measured. Per the plan, criterion 5
is **not** inferred from headless API presence, no code reading is substituted for it, and the
underlying open question is **not** closed.

Deliverables ready for the real run: `/tmp/claude-1000/praxis-spikes/S-E/gesture_spike.py`,
`/tmp/claude-1000/praxis-spikes/S-E/PROTOCOL.md`, `/tmp/claude-1000/praxis-spikes/S-E/overlay/host_iframe.html`.

**Consequence. Phase 5's `praxis-shell.js` work is BLOCKED.** Design B-prime is not authorised, and the
revert-to-Design-A decision cannot be taken either — both require this measurement.

---

## 6. Supporting spikes that changed a downstream recommendation

### 6.1 S-D — viz handoff PASSES, and found a real defect that conflicts with S-F's advice

All three required operations delivered end-to-end through a real Pyodide kernel → `praxis_viz`
BroadcastChannel → real vendored renderer, with `success: true` acks and zero page errors:

```
transport_final_stats = {"sent": 8}
transport_replay_events = ["set_root_resource","set_state"×5,"resource_assigned","resource_unassigned"]
pick_up_tips_ok=true (Δ4)   assign_child_resource_ok=true (Δ1)   unassign_ok=true (Δ1)
viz_courier_log_count = 8   pageerrors_repl = []   pageerrors_viz = []
```

But the **initial full-state push failed to parse**:

```
{"bytes": 65516, "error": "parse_error",
 "detail": "SyntaxError: Unexpected token 'I', ...\"_volume\": Infinity},\"... is not valid JSON"}
```

**Adjudicator-verified root cause and, crucially, its fix status across all three trees:**

```
current pin d9651e2 :  60:def _sanitize_floats(obj)   263: return json.dumps(_sanitize_floats(command_data)), id_
0.2.2 dd79c4c8      :  81:def _sanitize_floats(obj)   305: return json.dumps(_sanitize_floats(command_data)), id_
DEPLOYED 0.1.6 wheel:  (no _sanitize_floats)          186: return json.dumps(command_data), id_
```

`trash`/`trash_core96` carry `max_volume = float('inf')`; bare `json.dumps` emits a literal `Infinity`
token that browser `JSON.parse` rejects. **The deployed 0.1.6 wheel is the only one of the three
without the fix.**

**This contradicts S-F's "build the pipeline first at 0.1.6 (Option B)" recommendation.** Shipping the
visualizer against the deployed 0.1.6 wheel ships a silently incomplete first deck paint. Either take
the pin bump before/with the viz work, or wrap the transport's `send()` with equivalent float
sanitization as an explicit stopgap. This is a decision for the plan owner, surfaced here rather than
left to be rediscovered.

Two methodological findings worth carrying: BroadcastChannel is **origin-scoped** and silently delivered
nothing across two dev-server ports (no error either side) — same-origin is load-bearing for the future
host-page/iframe app. And `performance.now()` is **not** valid across the kernel-Worker and Document
realms (uniform ~800ms size-invariant offset); `Date.now()` gave the real 1–3ms hop cost for ≤115KB.

### 6.2 S-F — conclusion upheld, but on the adjudicator's evidence, not S-F's

S-F's method does not support its stated strength. 59 of 61 modules failed at `praxis.ini` **before
reaching their pylabrobot imports**, so "identical failure signature across versions" proves nothing
about PLR compatibility for those 59 — the claim that it "rules out ALL PLR-specific import changes in a
single test run" is overstated. Only 2 modules actually exercised PLR.

The adjudicator ran the test S-F should have run: AST-extract every `pylabrobot` symbol referenced by the
61 modules and resolve each against both versions, isolated from `praxis.ini`.

```
pairs checked: 55
resolve@0.2.2: 53   resolve@0.1.6: 53
=== DIVERGENT between 0.1.6 and 0.2.2 ===  count: 0
=== unresolved at 0.2.2 ===
    pylabrobot::resources        -> False
    pylabrobot.resources::CarrierSite -> False
```

**Zero divergence.** S-F's conclusion — no new import breakage at 0.2.2 — **stands**, now properly
evidenced. The two non-resolutions:

- `pylabrobot::resources` is the same parent-namespace `hasattr` artifact as criterion 3's
  `pylabrobot.visualizer`, not an import failure.
- **`CarrierSite` is already broken at the currently installed pin** — a pre-existing bug, unrelated to
  0.2.2, that S-F's method masked:

```
$ uv run python3 -c "import pylabrobot, pylabrobot.resources as r; print(pylabrobot.__version__); print(hasattr(r,'CarrierSite'), hasattr(r,'PlateHolder'))"
0.1.6   (external/pylabrobot/pylabrobot/__init__.py)
False True
$ grep -rn CarrierSite praxis/ --include=*.py | grep -v web-client
praxis/backend/commons/plate_staging.py:9:from pylabrobot.resources import CarrierSite, Coordinate, Plate, TipRack, Well
```
`praxis/backend/commons/plate_staging.py` cannot import today. Upstream renamed it to `PlateHolder`.
File as a separate pre-existing defect; it neither blocks nor is fixed by Phase 4.

Also adjudicator-verified: the one known 0.2.2 rename has **zero** backend blast radius —
`grep -rn "pylabrobot\.incubator" praxis/ --include=*.py | grep -v web-client` returns nothing. It hits
only `web_bridge.py:412`, exactly as the wheel spec assumed.

---

## 7. What this verdict permits and forbids

**Permitted to start now:**

- **Phase 2 / viz transport work (T2.x).** Criteria 1 and 2 both PASS. T2.2 takes the **normal** path —
  the +30-line callback-override fallback is not needed. Subject to §8-a landing.
- **Phase 4, the PLR pin bump.** Criterion 3 PASS; 0.2.2 boots, the contract surface resolves, the
  `+local` version survives micropip, and the backend blast radius is zero-divergence.
- **Phase 3 wheel-pipeline work**, unchanged — but see §6.1: the "ship the pipeline at 0.1.6 first"
  rationale is weakened for anything on the visualizer path.
- **T08 design work**, with the three-key amendment folded in.

**Forbidden until a named precondition lands:**

- **No served-path change** until all three `*StorageName` keys are pinned in `jupyter-lite.json` **and**
  the migration lands in the same commit — ADR §5.5, now amended from one key to three.
- **No visualizer construction at 0.2.2** until `await micropip.install("websockets")` is in
  `praxis_bootstrap.py`. Without it the constructor raises at `visualizer.py:144`.
- **No Phase 5 `praxis-shell.js` work.** Criterion 5 UNMET. Design B-prime is unauthorised, and the
  revert to Design A is equally unauthorised — neither may be chosen on present evidence.

**Explicitly still open:** criterion 5 / the S0 gesture open question is **not closed**.

---

## 8. Required actions before dependent work ships

- **(a)** ~~Add `await micropip.install("websockets")` to `praxis_bootstrap.py`'s install step.~~
  **SUPERSEDED 260818** (see the note under "Criterion 1" above) — `micropip.install` against live
  PyPI at boot conflicts with GATE G5's offline requirement. DONE instead: vendor
  `websockets-17.0.1-py3-none-any.whl` into `overlay/assets/wheels/` and regenerate
  `manifest.json` — no `praxis_bootstrap.py` edit needed, the existing wheel-install loop already
  covers it. Gates criterion 1's mechanism-pass becoming a product-pass; this action is now complete
  at the wheel/manifest layer (T0.1's in-kernel Pyodide probe is separately still open).
- **(b)** Amend ADR §5.5 and spec T08 to name `contentsStorageName`, `settingsStorageName`, **and**
  `workspacesStorageName`.
- **(c)** Decide the §6.1 conflict: bump the pin before/with the viz work, or add explicit float
  sanitization to the transport's `send()`. Do not ship the initial deck paint against the unpatched
  0.1.6 wheel.
- **(d)** Run S-E with a human and a device. Until then criterion 5 stays UNMET.
- **(e)** File `CarrierSite` → `PlateHolder` in `plate_staging.py:9` as a pre-existing defect.
- **(f)** Consider pinning `pyodideUrl` explicitly rather than inheriting v314.0.1 from a vendored
  bundle, and correct the stale "v0.29.0 / 3.13.2" figure in the brief and prior docs.

---

## 9. What would change this verdict

- **Criterion 1 → FAIL** if `micropip.install("websockets")` proves unavailable in the *offline/vendored*
  configuration (all evidence here is CDN/PyPI-reachable). Then the stub-`websockets` fallback becomes
  live — and it remains viable, because `BrowserVisualizer` overrides `setup`/`stop`/`has_connection`/
  `send_command` and never calls the real `serve(...)`; a shim need only satisfy the import and flip
  `HAS_WEBSOCKETS`. Holding the visualizer at the old pin stays the second fallback.
- **Criterion 2 → FAIL** if a real `BrowserVisualizer` (not the probe's direct member calls) exercises a
  loop path not covered by the six members tested. Note `run_until_complete` succeeded reentrantly inside
  an already-running WebLoop, which stock CPython forbids — observed, unexplained, and a place a real
  implementation could still diverge.
- **Criterion 3 → FAIL** if the service-worker / GH-Pages caching half of OQ-2 rejects the `+local` wheel
  filename. Only the micropip-acceptance half was tested; OQ-12/OQ-13 (COI and `/praxis/` base-path
  variants) were **not** re-run and remain open.
- **Criterion 4 → FAIL** if a fourth `*StorageName`-style key exists that neither the bundle grep nor the
  live enumeration surfaced, or if the override behaves differently across *separate origins* rather than
  the two same-origin mounts tested.
- **Criterion 5** resolves only by running S-E on real hardware. A PASS authorises Phase 5 / B-prime; a
  FAIL or materially-worse-than-iframe result reverts the architecture to Design A.
- **The whole battery** weakens if the deployed runtime moves off pyodide v314.0.1 / CPython 3.14.2,
  since criteria 1–3 were all measured there. Nothing in our config pins it (§6f).

---

## 10. Provenance

Adjudicated by spot-check, not relay. Independently re-verified by the adjudicator: the 0.2.2
`__init__`-vs-`setup()` raise site; `add_reader` absence at both SHAs; `_sanitize_floats` presence across
all three trees; the three `*StorageName` read sites in the shipped bundle; the pyodide default-URL
source; S-B's rerun distinctness (`cmp`); the PyPI request filter over all 315 log entries; the
0.1.6-baseline flag/identity cross-check; the 55-symbol two-version blast-radius test; the `CarrierSite`
breakage at the installed pin; and the zero-reference check for `pylabrobot.incubator`.

**Zero repo mutation** by any spike or by this adjudication, except this file. Submodule
`external/pylabrobot` confirmed still at `d9651e2098cd269fc47e6aff80c9242a82d1b587` with only its 6
pre-existing dirty entries; PLR 0.2.2 was obtained solely via `git archive`/`git show` at
`dd79c4c89bc008629a1c598ea614be5e6067d1f9`, never by checkout.

**Artifacts** (all under `/tmp/claude-1000/praxis-spikes/`, none in the repo):
`sa_result.json`, `sa_result3.json`, `S-B/result_sb_rerun.json`, `spike_c_result.json`,
`spike_c2_result.json`, `S-D/sd_result2.json`, `S-E/xvfb_selfcheck_result.json`,
plus adjudicator-generated `plr_syms.json`, `sym_022.json`, `sym_016.json`.
