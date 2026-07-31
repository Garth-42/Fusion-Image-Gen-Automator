# PR #27 — Round-4 Verification Results

Consolidated results of the live-Fusion pass described in
`docs/PR27_ROUND4_TEST_PLAN.md`, run across five sessions between 2026-07-26 and
2026-07-31 against `main`. Each session was scoped to one section by explicit
instruction; the per-session reports are the primary record and this document is
the sign-off across all of them.

Verification was done with computer use for every palette action, and with
direct Fusion API script execution (`fusion_mcp_execute`) or Fusion's own Text
Commands Python console for state that a screenshot cannot settle — transforms,
camera values, opacity, file sizes, PNG headers, SHA-256 hashes. Where a result
below says "exact", it is backed by compared values, not a visual match.

---

## Sign-off

| Test | Result | Palette | Notes |
|---|---|---|---|
| S1.1 nested apply | **PASS** | floating | Bit-exact return to the reference pose, including the child moved independently of its parent |
| S1.2 nested restore | **PASS** | floating | Bit-exact return to the modified pose |
| S1.3 nested render | **PASS** | floating | Correct 2400×1600 PNG; camera restored to full float precision |
| S2.1 render message visible | **PASS** | docked | Exact expected text, still legible at 3 s |
| S2.2 other five messages | **PASS** | docked | All five verbatim, all still present at 3 s |
| S2.3 later action clears | **PASS** | docked | Feedback line fully empty after one Refresh |
| S2.4 render failure visible | **FAIL** | docked | Blocked write reported the normal success text; nothing logged anywhere |
| S3.1 render dimensions | **PASS** | floating | 2400×1600 and 480×320 confirmed by PNG header parse |
| S3.2 restore after failed render | **INCONCLUSIVE** | floating | Same defect as S2.4 — with no visible failure there is nothing to test recovery from |
| S3.3 opacity round-trip | **PASS** | floating | Shared component-level opacity restored exactly on all three instances |
| S3.4 legacy scene translucency | **PASS** | floating | Hand-authored pre-PR schema shape loaded and applied correctly |
| S3.5 broken reference blocks render | **PASS** | floating | Exact `SCENE_REFERENCE_MISSING`; no mutation from either Render or Load Scene |
| S3.6 reorder touches only the manifest | **PASS** | floating | All scene files byte-identical by SHA-256; no asset touched |
| S3.7 corrupted manifest | **PASS** | floating | Immediate `YAML_PARSE_FAILED` naming file, line and column |
| S3.8 healthy fixture captures first time | **PASS** | floating | No false positive from the §R3 identity guard |
| S4.1 project folder removed | **PASS** | docked | Exact `PROJECT_ROOT_UNRESOLVED`; clean recovery on one Refresh |
| S4.2 stable-ID persistence | **SPLIT: PASS native / FAIL linked** | docked | Native IDs survive a restart; IDs on externally-referenced components are silently discarded |
| S5.1 document switch, one Refresh | **SPLIT: PASS forward / FAIL back** | floating | Back-switch still needs 2 clicks (was 2–3) |
| S5.2 on-disk reorder, isolated | **PASS** | floating | New order shown after one Refresh |
| S5.5 preview image repaint | **FAIL** | floating | A first render showed a blank placeholder; after a document switch the preview kept the previous document's image |
| S5.9 perceived speed | **no perceptible slowdown** | floating | Refresh on a 207-scene manifest still felt instant |
| S5.3, S5.4, S5.6, S5.7, S5.8 | **not run** | — | Session ended on a usage-limit checkpoint |
| S6.1 one Stable IDs panel | **not run** | — | In progress when the session ended; no second heading seen, but not confirmed |
| S6.2 refused capture wrote nothing | **not run** | — | Not started |

### Release gate

Against the plan's gate:

- **§S1 — the point of the pass — passed completely.** `556a04f`'s nested
  transform batching is confirmed against real Fusion for apply, restore and
  render. Assumption **A-1** is settled. This was the oldest unverified item in
  the project.
- **S2.1 passed**, so the blocking feedback-visibility item is clear.
- **No §S3 regression** in seven of eight checks; S3.2 is not a regression but a
  re-observation of S2.4 from another angle.
- **The stable-ID guard produced no false positive** (S3.8, and S1.3's capture).
- **S2.4 blocked.** The plan expected an intermittent legibility problem and
  said so ("report but not blocking… if it remains intermittent"). What was
  found is categorically worse: a blocked render wrote nothing, reported the
  ordinary success message character-for-character, and logged nothing. That is
  a detection failure, not a display one, and it is fixed rather than deferred.

Everything the gate calls blocking is clear once S2.4's fix is verified live.
§S5 and §S6 are only partly run, so the gate is clear of what this pass covered
and no more.

---

## What was fixed in response

Each item names the section that found it. The pure-Python suite covers all of
them; none is confirmed against live Fusion yet, which is what round 5 is for.

### 1. Render failures were undetectable when the target already existed (S2.4, S3.2)

The blocking one. `RenderService` already refused to report success unless the
image was on disk — that check was added after round 2 — but it asked whether
the *destination* existed, and in both S2.4 and S3.2 the destination existed
already, left by an earlier successful render. A blocked write therefore found
the previous render's file, called it proof, and produced the normal message.
The file's own mtime showed nothing had been written.

Rendering now exports to a staging file in the output folder and moves it onto
the destination (`atomic_write.staging_path`/`commit`, used by
`RenderService._export_png`). A path that cannot pre-exist is the only thing
that can answer whether *this* export wrote anything. A read-only folder now
fails at the staging write, an unwritable target fails at the move, and both
raise `RENDER_FAILED` naming the path. A failed render also no longer truncates
the previous good image, and the destination is never left half-written.

This also un-blocks S3.2, whose own premise needs a visible failure to recover
from.

### 2. Feedback text stuck on its busy message (S1 ancillary 1, S2 deviation 3)

Capture, Apply, Restore and Edit all left the feedback line reading
"Capturing current Fusion state…", "Applying captured state…", "Restoring
previous Fusion state…" or "Loading scene metadata…" indefinitely. Each of those
handlers reports into a line of its own and so never touched the shared one.
Every finished request now clears the busy text as it settles, before its
handler runs, so a handler with something to say still overwrites it and a
handler with nothing to say cannot leave a stale present participle on screen.
Edit additionally says the editor has loaded, because on a long scene list it
opens below the fold.

### 3. "Captured state contains undefined occurrence(s)" after Apply (S1 ancillary 2)

`state.apply_captured` returned only the guard's warnings while the page read it
as a capture summary. It now answers in the capture's shape, and the page
describes each of the three state actions separately. Apply also reports how
many occurrences it hid — it hides anything the capture did not list, which
changes the viewport and was previously the one part of the outcome never
mentioned.

### 4. Stable IDs on linked components (S4.2)

S4.2 established, twice, through three different save procedures, that Fusion
stores an externally-referenced component's attributes in that component's own
document — which saving the parent assembly does not save. The ID disappears at
the next launch while Fusion reports the assembly as fully saved. Nothing in the
add-in can persist it; the documented "Ensure IDs, then save the document"
workflow is genuinely insufficient for these components, and this is the whole
explanation for Fixture A's `component_id` that has been "still missing, never
fixed" for four rounds.

The add-in cannot fix it, so it now says so instead of letting the ID silently
come back missing every session: `identity_records` reports whether each
component is externally referenced, the Stable IDs panel carries a standing note
naming the affected components, and Ensure IDs says at the moment of assignment
which of the IDs it just wrote will not survive reopening. See
`docs/KNOWN_LIMITATIONS.md`.

### 5. Summary preview outliving what it describes (S5.5)

The more serious half of S5.5 — a preview showing Fixture B's rendered image
beneath Fixture C's scene entries — was not a repaint problem at all. The panel
holds a point-in-time snapshot of YAML and PNGs and nothing ever invalidated it,
so it survived document switches and re-renders intact. It is now replaced with
a rebuild prompt when the document or project changes, and after any mutation
that alters the files it was built from.

The palette preview also embedded the full 2400×1600 render as base64 in
`innerHTML` — megabytes per scene — which is the likeliest cause of the blank
placeholder in the other half of S5.5. It now embeds the 480×320 thumbnail,
falling back to the full render when no thumbnail exists; the exportable
document still carries full-resolution images.

Separately, the page's "did anything change?" test compared text only, exactly
as the plan predicted, so an image-only change never asked for a repaint. Image
sources are now fingerprinted into that signature — the fix the plan itself
prescribed.

### 6. Scroll position reset on every click (S1 ancillary 5, S4 ancillary 4)

Reported by two sessions as the single biggest drag on manual testing, and
severe enough on Fixture A that a session had to resort to the **End** key to
reach the Stable IDs panel. The cause is in the repaint: hiding the body to
force a box-tree rebuild throws the scroll offset away, and that repaint runs
after every response. The offset is now saved and restored inside the same
synchronous block, so no frame can be presented at the wrong position.

### 7. Scene editor surviving a document switch (S5 ancillary 3)

The editor holds a scene id, not a scene, and nothing checked that the id still
belonged to what was on screen — so it stayed open across a switch to a
different fixture, with Save Metadata pointed at a manifest that no longer
contained the scene. It now closes when its scene is not in the current list.

### 8. "Palette script error: Script error." (S4 ancillary 1)

The message named no exception and Text Commands held nothing, which the plan's
global error-surfacing rule calls a failure in itself. Hosts mask the message on
a script they treat as cross-origin, but the source location and the error
object usually survive that masking, so both are now reported. The page also
forwards the text to the add-in through a new `system.log` action, so a script
error lands in Fusion's log where a tester can find it after the fact.

---

## Still open

### S5.1 — the back-switch still takes two Refresh clicks

Improved from 2–3 clicks to exactly 2, and only in one direction: switching to a
fresh document updates on one click, switching back to a previously-viewed one
does not. **No fix is attempted here**, deliberately. The plan names S5.3
(reading Text Commands for `palette declined the requested repaint resize.`) as
"the make-or-break diagnostic" and "the first thing to check if S5.1 or S5.2
fail" — and S5.3 was not run. Guessing at a second repaint mechanism without
that line would be changing window-resize behaviour blind. Round 5 runs S5.3
first.

### Fixture A is largely unusable for scene tests

`ChildA_Moved:1`'s ID was reassigned during S4.2's contrast test, so scenes
captured against the old ID now fail with `SCENE_REFERENCE_MISSING`. That is the
stable-ID guard working correctly, but it means much of Fixture A's 207-scene
manifest cannot be rendered until an Ensure IDs and recapture pass is done. The
207-scene count is itself unexplained and unattributed to any session.

### Not run

§S5.3, S5.4, S5.6, S5.7, S5.8 and all of §S6. S5.7 (does the palette fight a
manual resize) has never been performed in any round — computer use could not
drive a manual window resize in round 3 or round 4, and the plan flags it as
possibly needing a human. It should be raised directly rather than attempted a
third time.

---

## Fixture state carried forward

- **Fixture A:** `FixtureA_Part1`'s `component_id` still missing, and now known
  to be unfixable by saving (see item 4). `ChildA_Moved:1` carries a new,
  successfully persisted ID that several captured scenes do not match. 207
  scenes, order restored after S5.2's test swap. Document saved.
- **Fixture B:** 2 scenes ("R3.5 healthy fixture regression check", "S1.3 nested
  reference pose render check"), both rendered. Geometry at the captured
  reference pose. Unsaved changes.
- **Fixture C:** 5 scenes, two of them added in round 4; two scenes share the
  title "Opacity shared check C", which misled one session into rendering the
  wrong one. Live opacity at 0.4. Unsaved changes.
- **Fixture D:** 1 scene, still referencing the removed `WillBeRemoved:1` (this
  is deliberate — it is the S3.5 fixture). `manual.yaml` corruption reverted
  byte-for-byte; document unmodified throughout.
- **Fixture E:** 3 scenes, left in the order S3.6 swapped them into. Unsaved
  changes.
