# PR #27 — Round-3 Verification Results

Results of the live-Fusion pass described in `docs/PR27_ROUND3_FIX_REVERIFICATION.md`.

**Date:** 2026-07-26
**Scope:** §R1 (palette painting) and §R3 (stable-ID guard) only, by explicit
decision, following that document's own "if you run out of time, §R1 and §R3 are
what matter" guidance. §R2, §R4, §R5 and §R6 were not run.

---

## Sign-off

| ID | Test | Result | Notes |
|---|---|---|---|
| R1.1 | Blank on open | **PASS** | Blank at 0 s, fully painted by ~2 s, stable to 10 s. No nudge needed. |
| R1.2 | Stop/rerun | **PASS** | Same pattern as R1.1. |
| R1.3 | Full Fusion restart | **PASS** | Verified after a real Cmd+Q quit and relaunch. |
| R1.4 | Doc switch on one Refresh | **FAIL (partial)** | A *fresh* document updates on 1 click. Switching **back** to a previously-viewed document takes **2–3** clicks. See "Follow-up fix" below. |
| R1.5 | Resize diagnostic | **PASS** | `palette declined the startup repaint resize.` never appeared, so the resize was attempted — consistent with the successful paints. |
| R1.6 | Typing not disrupted | **PASS** | Confirmed in both "New scene title" and the Description/Instructions textareas. |
| R1.7 | User resize not fought | **INCONCLUSIVE** | Could not trigger a manual window resize through computer use; docked-edge and floating-corner drags both had no effect. Needs a human pass. |
| R1.8 | On-disk reorder on one Refresh | **FAIL (partial)** | Reorder did appear, but took 3 clicks. Confounded with the R1.4 lag rather than cleanly isolated. |
| R3.1 | Missing ID → actionable error | **PASS** | Exact expected string, naming the entity and the button. |
| R3.2 | Ensure IDs self-heals | **PASS** | Assigned exactly the one missing component ID; the healthy sibling's ID was untouched. Recapture then succeeded. |
| R3.3 | Duplicate IDs refused | **PASS** | Capture refused before writing; Repair reassigned exactly one of the pair. |
| R3.4 | Recapture guarded, non-destructive | **PASS** | Explicit confirmation dialog; scene count, title, filename and metadata all unchanged. |
| R3.5 | Healthy fixture unaffected | **PASS** | Fixture B's legitimate repeated component (shared `component_id`, distinct `occurrence_id`s) captured first time, with no false positive. |

### Release gate

No blocking item was hit. R1.1–R1.3 passed, R3.5 showed no false positive, and
nothing in §R1 or §R3 regressed. R2.1, R5.1 and R5.2 remain **unrun**, so the
gate is not fully cleared — it is only clear of everything this pass covered.

---

## §R3 — settled

All five sub-tests passed. Missing IDs and true duplicates are both caught with
actionable text naming the affected entities; the two repair actions fix exactly
what is broken and leave healthy IDs alone; recapture is gated behind an explicit
confirmation and alters neither scene count nor metadata nor filenames; and the
guard correctly distinguishes a legitimate repeated component from a duplicate-ID
fault. Nothing here needs another round.

---

## §R1 — fixed on open, and the residual lag is now fixed too

Blank-on-open is genuinely resolved: R1.1, R1.2 and R1.3 all paint unaided, which
is what round 2 could not do. R1.6 confirms the repaint does not eat typing, and
R1.5 confirms the resize was attempted rather than refused.

What remained was R1.4/R1.8: the palette paints on open but goes **stale later**,
needing two or three Refresh clicks to show a change. That is case 3 of the test
document's own diagnostic tree ("the palette paints on open but goes stale later
→ the bound of three startup nudges is too tight"), and it has now been diagnosed
and fixed.

### Root cause

The bound was only half of it. The real fault was **ordering**.

`PaletteController.nudge_native_surface()` ran at the end of
`_IncomingHtmlHandler.notify()` — that is, as a request was *answered*. On both
palette browsers that moment is strictly **before** the page has received the
response and updated its DOM. The resize therefore invalidated the surface while
the *old* DOM was still on it.

Startup masked this completely. Its three requests (`ping`, `project.status`,
`identity.status`) follow one another closely, so each nudge happened to reveal
the update the *previous* response had made, and by the end the palette looked
correct. That is why R1.1–R1.3 pass.

A lone request after startup has nothing following it. The Refresh behind a
document switch, or behind a scene list edited on disk, updated the DOM onto a
surface that nothing subsequently invalidated — so the change only appeared when
a later click's nudge pushed it forward. Hence 2–3 clicks, and hence "a fresh
document takes 1 click but switching back takes 2–3": the counts simply track how
many nudges happen to land after the update.

### The fix

Invert the order — let the page ask for the resize once its DOM has actually
changed.

- `ui/palette.html` sends a new no-op `system.repaint` action from `handleRaw`,
  *after* the response has been applied to the DOM. Its answer is what triggers
  the add-in's resize, so the resize now lands behind the update instead of in
  front of it.
- The request goes out **only when visible content changed** (compared by a
  content signature). An idle Refresh that changes nothing still moves no window,
  which is what keeps R1.7's property intact.
- A reserved request id keeps the repaint's answer from being mistaken for the
  user's in-flight request, and an in-flight guard keeps it from looping.
- `PaletteController.nudge_native_surface(requested=True)` is not drawn from the
  three-nudge startup budget: a requested nudge means the page has something new
  to show. The startup burst is unchanged, so R1.1–R1.3 cannot regress.
- A host that refuses `setSize` now logs once per kind instead of on every
  content change, so a docked palette cannot flood Text Commands. The startup
  line R1.5 looks for is unchanged; refused *requested* repaints log
  `palette declined the requested repaint resize.`

### Verification

- Unit suite: **107 passed** (101 before, 6 added).
- The palette script was additionally driven against a fake DOM and a fake
  add-in to check runtime behaviour rather than source patterns. With the
  document switched and **one** Refresh click, the repaint is requested and the
  DOM it would paint already reads the new document line; a response that
  changes nothing requests no repaint; the request loop terminates.

This still needs confirming in live Fusion — R1.4 and R1.8 should be re-run, and
R1.7 checked at the same time, since requested repaints now recur for the life of
the palette rather than stopping after startup.

---

## Still open

| Item | State |
|---|---|
| R1.4 / R1.8 | Fixed here; **needs live re-verification**. |
| R1.7 (user resize not fought) | Never verified. Computer use could not drag the palette. Needs a human, and now matters more than it did: repaints are no longer confined to startup. The nudge always measures from the palette's *current* size and restores it, and only fires on a real content change. |
| R1.8 clean measurement | The 3-click figure was conflated with the R1.4 lag. Re-isolate if a clean number is wanted. |
| R3.1 step 4 | The refused capture *appeared* to write nothing, but "no new file in `scenes/`, no new entry in `manual.yaml`" was not rigorously checked. Worth confirming. |
| §R2, §R4, §R5, §R6 | Not run this pass. §R2.1 and §R5.1/§R5.2 are release-gate items and still carry no direct verification. |

---

## Environment notes for the next session

- A real Fusion MCP (`mcp__Autodesk_Fusion__fusion_mcp_*`) is available and was
  used for direct reads/writes of component attributes (`FMSM.component_id`,
  `FMSM.occurrence_id`) via script execution. It is far faster and more reliable
  than the screenshot + click + Text-Commands workflow of the prior session. Use
  it first for anything touching document state, attributes, or file I/O; reserve
  computer use for the add-in's own Qt palette, which the Fusion API cannot reach.
- Palette scrolling is slow and inconsistent — roughly 100 scroll ticks sometimes
  moved a whole section and sometimes barely 30 px. Budget generously.
- The macOS Dock (always-visible in this environment) can visually clip the
  bottom of a docked palette, hiding **Ensure IDs** and **Repair Duplicate IDs**
  even at the panel's real scroll limit. Toggling Dock auto-hide (Cmd+Option+D)
  resolves it.
- Fixture A and Fixture E were left with unsaved changes (the add-in never
  auto-saves). Fixture B carries one captured scene from R3.5.
- Quitting Fusion from the File menu did **not** quit the application, only the
  document. R1.3 needs a real Cmd+Q.
