# PR #27 — Fix Re-Verification Instructions (Claude computer use)

**Read this first, then follow `docs/PR27_COMPUTER_USE_TEST_PLAN.md` for the
detailed per-test steps.** This document is the *re-run* after the two release
blockers from the 2026-07-23 verification report were fixed. It (a) tells you
what changed, (b) **overrides some pass/fail criteria from the old plan** — most
importantly for opacity — so you do not re-report expected behavior as a defect,
and (c) gives the execution order.

The pure-Python suite passes (91 tests). Everything here needs a running Fusion
session with screenshots + a terminal, same conventions as the old plan.

---

## What was changed since the last report

1. **Critical opacity crash — fixed.** Every mutating operation used to call
   `occurrence.component.createForAssemblyContext(occurrence).opacity`. That
   method does not exist on `Component`, so it raised `AttributeError` and every
   Create Scene / Render / Apply / Restore / Load Scene died with
   `Error (INTERNAL_ERROR): Unexpected add-in error while handling the request.`
   Opacity is now read and written through the documented `Component.opacity`
   property (`occurrence.component.opacity`).

2. **Error surfacing — fixed.** Unexpected exceptions used to collapse into an
   opaque "Unexpected add-in error while handling the request." with no cause.
   The palette error line now names the exception, e.g.
   `Error (INTERNAL_ERROR): Unexpected add-in error: AttributeError: '...'`.

3. **Palette repaint — strengthened (UNVERIFIED).** The blank-on-open /
   stale-after-switch nudge previously flipped CSS opacity only, which the Qt
   WebEngine host ignored. It now also forces a real layout reflow. **This fix
   could not be verified outside Fusion — §1 is the highest-value part of this
   pass.**

---

## ⚠️ Corrected expectations — READ BEFORE §4 (opacity)

The old plan assumed opacity could be a **per-instance** override
(assumption **A-2**). That assumption was wrong and has been **retired**. In the
Fusion API opacity is a **component-level** override; there is no writable
`Occurrence.opacity`. The consequences you MUST account for:

- **CU-4.2 is redefined.** Two instances of the *same* component now **share one
  opacity value** by design. The old plan called shared opacity a FAIL — that is
  now the **EXPECTED PASS**. Do **not** report "both instances end at the same
  opacity" as a defect. Only a crash, or a failure to restore the shared value,
  is a defect here.
- **CU-4.1 caveat.** A single part's opacity round-trips **only if the value
  lives on the component**. If you set opacity as a per-instance override on one
  occurrence of a multi-instance component, `Component.opacity` will not capture
  it and it will not round-trip. That is the **documented limitation**, not a
  bug. Use the YAML check below to tell the two apart.
- Independent per-instance opacity is explicitly **out of scope** for this
  deliverable (see `docs/08_RISKS_AND_API_NOTES.md` §8.3 "Opacity").

Assumption **A-1** (transform batching) still stands and still needs live
confirmation in §3.

---

## Global rule — error surfacing (applies to every test)

Whenever any error appears in the palette, **record its full text.**

- An `INTERNAL_ERROR` whose message is now just
  `Unexpected add-in error while handling the request.` with **no exception
  named** = **FAIL of the error-surfacing fix** (report it).
- An `INTERNAL_ERROR` that **names the exception and message** (e.g.
  `... AttributeError: 'Component' object has no attribute ...`) is the fix
  working — but the underlying exception is still a real bug to report with its
  full text, since no mutating op should throw at all anymore.

---

## Setup

1. Update the installed add-in to the fixed code (branch
   `claude/pr-27-test-defects-14i41p`, or `main` once merged):
   ```bash
   cd <repo>
   git fetch origin
   git checkout claude/pr-27-test-defects-14i41p && git pull
   ```
   Then point Fusion's **Scripts and Add-Ins** at
   `addin/FusionManualSceneManager` (re-add if the old copy is elsewhere) and
   **Run** it. Confirm you are running the freshly pulled copy, not the old
   `Downloads/...` bundle from the last report.
2. Record the add-in version and the current git commit hash
   (`git rev-parse --short HEAD`) so results are attributable.
3. Reuse Fixtures A–E and the extra fixtures (`A-opacity`, `C-repeated`,
   `legacy-scene`, `B-nested`) from the old plan — they still apply.
4. Wait for **`Add-in connected.`** before each section.

---

## Execution order (do them in this order)

### Step 1 — Headline: the crash is gone (do this first)

This is the single most important result. Last time these both returned
`Error (INTERNAL_ERROR): Unexpected add-in error while handling the request.`

1. On a freshly-initialized project (Fixture C is fine), click **Create Scene
   from Current State**.
   - **PASS:** the scene is created; no `INTERNAL_ERROR`.
2. On a Fixture A scene, click **Render**.
   - **PASS:** it renders; no `INTERNAL_ERROR`.

If either still throws `INTERNAL_ERROR`, capture the **full** message (it now
names the exception) and stop — that is a blocking regression; the rest of the
plan depends on this working.

### Step 2 — Re-run everything the crash previously blocked

With the crash gone, these are now testable for the first time. Follow the old
plan's steps; apply the corrected opacity criteria above.

| Old-plan test | What it now confirms | Notes / criteria changes |
|---|---|---|
| **CU-2.1** Successful render | render round-trip | unchanged |
| **CU-2.2 / CU-2.3** Read-only folder → `RENDER_FAILED`, state restored | render gate + restore | unchanged; was BLOCKED before |
| **CU-3.1 / CU-3.2 / CU-3.3** Nested transforms (Fixture B) | **A-1** batch transform replay | unchanged criteria; was BLOCKED before — watch nested children stay at their parent-relative offset |
| **CU-4.1** Single-part opacity round-trip | component opacity round-trip | **use the YAML check below**; per-instance override caveat applies |
| **CU-4.2** Repeated component (Fixture C) | shared opacity round-trip | **REDEFINED — shared opacity is PASS.** Verify no crash and the shared value restores; do NOT expect independent opacities |
| **CU-4.3** Scene YAML stores opacity per occurrence | schema shape | unchanged — `occurrences[]` carry `opacity`, `components[]` do not |
| **CU-4.4** Legacy scene replays opacity | legacy fallback | unchanged; was BLOCKED before |
| **CU-5.1** Per-scene cameras distinct | camera regression | unchanged; was BLOCKED before |

**CU-4.1 YAML check (do this to avoid a false FAIL):**
1. Make a part visibly translucent, then **Create Scene from Current State**.
2. Terminal — read what capture actually recorded:
   ```bash
   python3 -c "import yaml,glob; d=yaml.safe_load(open(sorted(glob.glob('scenes/*.yaml'))[-1])); print('occ opacity:', [o.get('opacity') for o in d['assembly_state']['occurrences']])"
   ```
   - If some value is `< 1.0`: capture worked. Set the part solid, **Load/Apply**
     the scene, screenshot → the part should be translucent again = **PASS**.
   - If every value is `1.0` despite visible translucency: you set a per-instance
     override the component-level API cannot see. **Note it as the documented
     limitation, not a defect.** (Retest by setting opacity on the component /
     the part's body so it lands on `Component.opacity`.)

### Step 3 — Palette rendering (§1) — the UNVERIFIED fix

Re-run **CU-1.1, CU-1.2, CU-1.3, CU-1.4 exactly as written** in the old plan.
This is the fix that could not be verified in code, so it is the most important
signal from this pass.

- **Do NOT collapse/expand or minimize/maximize the panel** anywhere in §1 — the
  whole point is that the palette must paint without that nudge.
- CU-1.1: on Run, the palette must show full content (heading, connection line,
  Project section, buttons) with no nudge. The old failure was "only the title
  bar and a 'Fusion' fragment, blank for 7+ s."
- CU-1.3: after switching the active document, a **single Refresh** must update
  the `Document:` line (last time it took two clicks).
- Report exactly what you see, and whether any nudge was needed to make it paint.

### Step 4 — Remaining regression / robustness (§5–§6)

Run the ones not yet covered: **CU-5.2** (bad IDs / missing references still
block), **CU-5.3** (reorder touches only `manual.yaml`), **CU-6.1** (corrupted
`manual.yaml` shows a clear error), and if time permits **CU-6.2 / CU-6.3**.
These do not touch the changed code; treat only a crash or a silent/blank
failure as blocking.

---

## Release gate

PR is release-ready when **all of**:

1. **Step 1 passes** — no `INTERNAL_ERROR` on Create Scene or Render.
2. **§2, §3, §4 pass** under the corrected opacity criteria (shared opacity in
   CU-4.2 is a PASS; transforms keep nested children in place for A-1).
3. **§1 passes** — the palette paints on open and updates on a single Refresh
   **without** a manual resize nudge.
4. No §5 regression; §6 shows clear errors, no crash/blank.

Flag separately (non-blocking, expected): any per-instance opacity that does not
round-trip because it lives on the occurrence rather than the component.

---

## Sign-off

| Test | Result (Pass/Fail) | Evidence (screenshot / terminal) | Notes |
|---|---|---|---|
| Step 1 — Create Scene (no crash) | | | headline |
| Step 1 — Render (no crash) | | | headline |
| CU-1.1 blank-on-open | | | no nudge allowed |
| CU-1.2 stop/rerun | | | no nudge allowed |
| CU-1.3 doc switch, single Refresh | | | no nudge allowed |
| CU-1.4 "Checking stable IDs…" clears | | | |
| CU-2.1 render success | | | |
| CU-2.2 read-only → RENDER_FAILED | | | |
| CU-2.3 state restored after failure | | | |
| CU-3.1 nested apply (A-1) | | | |
| CU-3.2 nested restore | | | |
| CU-3.3 nested render | | | |
| CU-4.1 single opacity round-trip | | | YAML check; note caveat |
| CU-4.2 repeated component (shared = PASS) | | | criteria redefined |
| CU-4.3 opacity stored per occurrence | | | |
| CU-4.4 legacy scene replays | | | |
| CU-5.1 cameras distinct | | | |
| CU-5.2 bad IDs / refs blocked | | | |
| CU-5.3 reorder touches only manual.yaml | | | |
| CU-6.1 corrupted manual.yaml | | | |
| CU-6.2 project folder removed | | | optional |
| CU-6.3 stable-ID persistence | | | optional |
| Error surfacing (global) | | | any INTERNAL_ERROR names its cause? |
