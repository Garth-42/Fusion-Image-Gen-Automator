# PR #27 — Round-3 Fix Re-Verification Instructions (Claude computer use)

**Read `docs/PR27_FIX_REVERIFICATION.md` first** — its corrected expectations,
especially that **opacity is a component-level, shared property**, still apply
in full and are not repeated here. Then follow
`docs/PR27_COMPUTER_USE_TEST_PLAN.md` for per-test steps.

This round answers the 2026-07-26 report, which passed every
functional/data-integrity test and failed only on palette painting. The
pure-Python suite passes (100 tests).

---

## What was changed since the 2026-07-26 report

### 1. Palette blank on open / on stop-rerun — CU-1.1, CU-1.2 (was FAIL)

The previous fix tried to force the repaint from inside the page. It could not
work, and the report's reproduction across a full Fusion restart is what made
that clear: **the workaround that works is a resize of the palette *window*, and
no JavaScript running inside the document can resize its own host window.** An
opacity flip, a reflow, and a scroll are all in-page changes the Qt WebEngine
host is free to coalesce away without ever invalidating the native surface.

The fix now lives on the add-in side, where the API to do it exists.
`PaletteController` resizes the palette one pixel taller and immediately back
after answering each of the page's first three requests
(`STARTUP_REPAINT_NUDGES`), reproducing the manual collapse/expand
programmatically at the three moments the page's DOM has just changed. It is
bounded to startup so nothing later moves a window the user has sized, it
happens after `returnData` is set so a resize that pumps the event loop cannot
re-enter the dispatcher mid-request, and a docked palette that refuses
`setSize` logs and carries on rather than failing the request.

The in-document nudge is kept and strengthened (it now also forces a box-tree
rebuild, skipped while a text field has focus so it cannot eat the caret), and
its startup burst now runs to 7.5s rather than 0.7s, because the report
measured the blank window lasting past seven seconds.

**This is the one change that cannot be verified outside Fusion — §1 is the
highest-value part of this pass.** Judge it strictly: the palette must paint its
full contents on open, and again after a stop/rerun, with no manual nudge.

### 2. Render feedback never appearing — Finding 2 (root cause confirmed)

The report's diagnosis was exactly right, and reproducing it in a stubbed DOM
confirmed it: `renderScene()` set `"Rendered X and Y."` and then called
`requestStatus()`, whose own success path assigned `feedback.textContent = ""`
microseconds later. The same bug hit five other messages — Render All, Scene
list updated, Scene metadata saved, Scene graphics updated, Scene order updated
— all of which refresh behind themselves.

Those messages are now handed to `requestStatus()`, which restores them after
the refresh (and after the identity check chained behind it) instead of racing
them. The next user action clears the line, so an outcome can never outlive what
it describes. Driving the real page against a stubbed host: pre-fix the line is
empty after a successful render, post-fix it reads
`Rendered assets/generated/one.png and assets/thumbnails/one.png.`

The report noted the *failure*-path half of this was intermittent rather than
consistent. That half is not separately explained; if error text still fails to
appear once §1 is confirmed working, it needs its own investigation.

### 3. Component missing `FMSM.component_id` — Finding 3

Reproduced: capture copies each entity's stored UUID straight into the scene
file, so a component with no attribute produced a scene the schema rejected with
`Error (COMPONENT_ID_INVALID): Component ID must be a UUID.` — naming neither
the part at fault nor the fix. Scene capture and recapture now check identity
first and fail with, e.g.

> `Error (IDENTITY_IDS_MISSING): 1 entity has no stable ID yet, so this scene could not be replayed: FixtureA_Part1. Click Ensure IDs, then capture again.`

Duplicates are refused at capture the same way, pointing at Repair Duplicate
IDs. IDs are deliberately **not** auto-assigned: that writes an attribute into
the user's document, and this add-in does not modify documents unprompted.

This makes the condition self-healing through the UI, which the report asked to
confirm — **re-run it on Fixture A**: the missing ID should now produce the
message above, and one click of **Ensure IDs** should clear it and let capture
succeed. That is the check that closes Finding 3.

### 4. Second Refresh needed for an on-disk change — Finding 4

Treated as §1, not as a separate defect: the first Refresh did update the DOM,
the host just did not present it. Confirm it is gone once §1 passes; if a single
Refresh still shows a stale scene list on a palette that is otherwise painting
correctly, that is a new bug and needs reporting as one.

### 5. Also fixed while in here

- A duplicated `<section id="identity-panel">` in `palette.html` rendered a
  second, dead "Stable IDs" panel whose controls were unreachable
  (`getElementById` returns the first match). Removed.
- CU-5.1's `getbbox()` recipe is replaced with a direct array comparison, per
  the report's recommendation. It reports magnitude and differing-pixel count
  instead of a bounding box that read as "identical" on renders that differed.

---

## Execution order

1. **§1 (CU-1.1, CU-1.2)** — the only outright failure from last round, and the
   only change here that no test outside Fusion can reach. Do it first, twice:
   fresh add-in load, then stop/rerun.
2. **Finding 3 re-check on Fixture A** — clear `FMSM.component_id` on one
   component, capture, confirm the new message, click Ensure IDs, capture again.
3. **CU-2.x render feedback** — with §1 working, confirm the success message is
   readable on screen, not just correct on disk.
4. **CU-3.2 / CU-3.3** — carried over; not directly verified in either of the
   last two rounds. CU-3.1 exercises the same batch-transform path, so the risk
   is low, but low is not verified.
5. **CU-6.2 / CU-6.3** — still optional, still unattempted.

Everything else in the 2026-07-26 report passed with evidence from the files and
Fusion API state, and is not scheduled for re-testing unless §1's fix changes
behavior around it.
