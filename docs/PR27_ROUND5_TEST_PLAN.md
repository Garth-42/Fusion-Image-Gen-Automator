# Round-5 Verification Plan (Claude computer use)

A live-Fusion plan covering (a) the round-4 fixes, and (b) the round-4 sections
that were never run.

**Read these first:**

1. `docs/PR27_ROUND4_RESULTS.md` — what round 4 settled, what it broke open, and
   what each fix was for.
2. `docs/PR27_ROUND4_TEST_PLAN.md` — its **corrected expectations still apply in
   full**, especially the opacity one (shared component-level opacity is a PASS,
   never a defect). Its §S5 and §S6 wording is reused below rather than restated.
3. `docs/PR27_COMPUTER_USE_TEST_PLAN.md` — fixtures and CU-numbered steps.

The pure-Python suite passes (128 tests). Everything here needs a running
Fusion session.

---

## Before you start

1. Install and run the add-in from the branch under test, and record the commit
   hash in the sign-off table. Round 4's sessions did not record it, which made
   it impossible to say afterwards exactly what had been tested.
2. Keep **Text Commands** visible all session. §T1 and §T5 both read it.
3. **Record docked or floating for every result.**
4. **Fixture A needs repair before it can be used for scene work.** Its
   `ChildA_Moved:1` was reassigned a new ID in round 4, so scenes captured
   against the old one now fail with `SCENE_REFERENCE_MISSING`. Either recapture
   the scenes you need or use another fixture and say which.
5. **Fixture C has two scenes titled "Opacity shared check C."** Identify scenes
   by `scene_id` or by the `output.image_file` in their YAML, not by position in
   the list. Round 4 rendered the wrong one this way.

---

## §T1 Render failure is detected and reported — the blocking item

This is the one round 4 blocked on, and the fix changed how every render writes
its files. Both halves matter: failures must be caught, and ordinary renders
must still work.

### T1.1 A normal render still works
1. Render any scene with a writable output folder.
- **PASS**: `Rendered assets/generated/<name>.png and assets/thumbnails/<name>.png.`,
  the files exist at 2400×1600 and 480×320, and no file matching
  `*fmsm-staging*` is left in either folder.
- Renders now write through a staging file and move it into place. A leftover
  staging file is a defect even when the render itself succeeded.

### T1.2 A blocked write on a scene that has never been rendered
1. Make `assets/generated` read-only (`chmod a-w`, or Finder → Get Info →
   Read only for your user).
2. Render a scene whose PNG does **not** already exist. Screenshot.
- **PASS**: `Error (RENDER_FAILED): …` naming the path.
- **FAIL**: any "Rendered …" text, or no message.

### T1.3 A blocked write on a scene that *has* already been rendered — the round-4 failure
1. Keep the folder read-only **and** make the existing target PNG unwritable
   (`chmod a-w <file>`, or tick Finder's **Locked** on it). Both steps are
   needed: a read-only folder alone does not stop an existing file being
   overwritten.
2. Note the target PNG's modification time.
3. Render that scene. Screenshot.
- **PASS**: `Error (RENDER_FAILED): …`, **and** the existing PNG is untouched —
  same modification time, same content.
- **FAIL**: a success message. This is the exact round-4 S2.4 failure; the
  previous render's file satisfying the "was anything written?" check is what
  the staging-file fix exists to stop.
- Restore permissions afterwards and confirm a render succeeds again.

### T1.4 State is restored after a genuine, visible failure (the old S3.2)
1. With T1.3's failure showing, check occurrence transforms and the camera
   against their pre-render values.
- **PASS**: both restored. S3.2 could not be judged in round 4 because no
  failure was ever visible to recover from; now it can.

---

## §T2 Feedback text (round-4 S1/S2 ancillary findings)

Judged only on what is legible in a screenshot of the `#project-feedback` line.

### T2.1 The busy text always clears
For **each** of Capture Current State, Apply Captured State, Restore Previous
State, and **Edit** on a scene:
1. Click it. Screenshot immediately, and again ~3 s later.
- **PASS**: the feedback line does **not** still read "Capturing current Fusion
  state…", "Applying captured state…", "Restoring previous Fusion state…" or
  "Loading scene metadata…" once the action has settled. Edit should read
  "Scene loaded into the editor below."
- The three state actions report their outcome in the **Scene State Preview**
  line, which should read correctly at the same time.

### T2.2 Apply reports what it applied
1. Capture a state, then Apply it.
- **PASS**: the Scene State Preview line reads `Applied captured state: N
  occurrence(s) and M component(s).`
- **FAIL**: `undefined` anywhere in it (the round-4 S1 finding).

### T2.3 Apply names what it hid
1. Capture a state. Add a new component to the design. Apply the captured state.
- **PASS**: the line additionally reads `N occurrence(s) added since the capture
  were hidden.`, and the new component is indeed hidden in the viewport.

### T2.4 S2.1–S2.3 regression
Re-run round-4 S2.1, S2.2 and S2.3 unchanged. They passed; the change to how
requests settle touches the same line, so confirm they still pass.

---

## §T3 Linked-component IDs are reported honestly (round-4 S4.2)

Use **Fixture A**, whose `FixtureA_Part1` is externally referenced. Nothing here
tests a fix to the persistence itself — there isn't one, and there cannot be
from inside the add-in. It tests that the add-in stops presenting an
unwinnable situation as a missing click.

### T3.1 The standing note
1. Open the **Stable IDs** panel.
- **PASS**: a line naming the linked components, saying their IDs live in other
  documents and that saving this assembly will not keep them.
- **FAIL**: the note is absent, or it names a component that is *not* linked.
  Cross-check with `occ.isReferencedComponent` in the Text Commands Python
  console.

### T3.2 The note at the moment of assignment
1. Click **Ensure IDs** with at least one linked component missing its ID.
- **PASS**: the feedback line reports the counts *and* says how many of those
  IDs live in linked documents and will not survive reopening.

### T3.3 A fixture with no linked components says nothing
1. Open the Stable IDs panel on a fixture built entirely from local components.
- **PASS**: no linked-component line at all. A note that appears everywhere is
  noise, not information.

---

## §T4 Summary preview (round-4 S5.5)

### T4.1 The preview does not outlive its document
1. On Fixture C, click **Preview Summary**. Confirm the images are Fixture C's.
2. Switch to Fixture B and click **Refresh**.
- **PASS**: the preview area reads "This preview describes an earlier state.
  Click Preview Summary to rebuild it."
- **FAIL**: Fixture C's image still showing under Fixture B's scenes — the
  round-4 finding.
3. Click **Preview Summary** again.
- **PASS**: Fixture B's own scenes and images.

### T4.2 The preview goes stale after a mutation
1. Open the preview, then render a scene, or reorder, or create one.
- **PASS**: the rebuild prompt replaces the stale content.
- Refresh alone must **not** trigger it — that would make the preview unusable.

### T4.3 A newly rendered scene shows its image
1. Pick a scene that has never been rendered. Render it, then click
   **Preview Summary**.
- **PASS**: its thumbnail appears in the preview.
- **FAIL**: a blank or grey placeholder box (the other half of round-4 S5.5).
  The preview now embeds the 480×320 thumbnail rather than the full 2400×1600
  render; if the box is still blank, say whether the thumbnail file itself
  exists on disk.

### T4.4 Image-only change is repainted
This is round-4 S5.5's original wording, now that the change signature covers
image sources.
1. With the preview open, re-render a scene so only its picture changes.
2. Rebuild the preview.
- **PASS**: the new image appears without extra clicks.

---

## §T5 Palette behaviour

### T5.1 Scroll position survives a click — the biggest tester complaint
1. Scroll to the bottom of the palette (the **Scene State Preview** buttons).
2. Click **Capture Current State**. Screenshot without scrolling.
- **PASS**: the panel is still where you left it and the buttons are still under
  the pointer.
- **FAIL**: it jumped back to the top. Two round-4 sessions reported this as the
  single biggest drag on manual testing.
3. Repeat for Refresh, Render, and Create Scene.

### T5.2 Scroll and typing together
1. Put the caret in the **Instructions (Markdown)** textarea, type, and click
   **Save Metadata** without clicking away first.
- **PASS**: no characters lost, caret retained, and the panel does not jump.
- The repaint skips its box-tree rebuild entirely while a field has focus, so
  the scroll restore does not apply on this path; both behaviours are being
  checked at once.

### T5.3 The scene editor closes with its document
1. Click **Edit** on a Fixture C scene.
2. Switch to Fixture B and click **Refresh**.
- **PASS**: the editor is gone.
- **FAIL**: the previous document's scene still open for editing.

### T5.4 Script errors are diagnosable
This one cannot be provoked reliably; check it opportunistically.
- If `Palette script error: …` ever appears, record the **full** text and check
  Text Commands for a matching `FMSM: page:` line. **PASS** if both are present
  and the palette text carries a source location or stack frame beyond the bare
  string `Script error.`

---

## §T6 Carried over from round 4, never run

Run these exactly as `docs/PR27_ROUND4_TEST_PLAN.md` specifies them.

| # | Round-4 test | Why it still matters |
|---|---|---|
| T6.1 | **S5.3** docked vs floating repaint diagnostic | The plan calls this "the make-or-break diagnostic"; it is the prerequisite for fixing S5.1 (see §T7) and it has never been run |
| T6.2 | **S5.1** document switch, one Refresh, **both** directions | Still failing on the back-switch |
| T6.3 | **S5.4** resize while a text field has focus | Highest-likelihood new bug from the round-3 repaint fix; covered here by T5.2, run the round-4 wording too |
| T6.4 | **S5.6** no visible twitch, no request storm | The repaint now fires on image changes as well as text; that is more requests than round 4 measured |
| T6.5 | **S5.7** the palette does not fight a user resize | Never performed in any round — see §T8 |
| T6.6 | **S5.8** blank-on-open regressions (R1.1, R1.2, R1.3, R1.6) | The repaint was modified; re-confirm |
| T6.7 | **S6.1** exactly one Stable IDs panel | Was in progress when round 4 ended |
| T6.8 | **S6.2** a refused capture wrote nothing | Never started; confirm with `git status` that no `scenes/` file and no `manual.yaml` entry appeared |

---

## §T7 If S5.1 still fails

Round 4 left the back-switch needing two Refresh clicks and **no fix was
attempted**, on purpose: S5.3's log line is what distinguishes "the host refused
the resize" from "the resize happened and was not enough", and without it any
change to the repaint path is a guess.

So run **T6.1 before T6.2**, and record:

1. Whether `palette declined the requested repaint resize.` appears in Text
   Commands at all, and in which dock state.
2. Whether the back-switch lag differs between docked and floating.
3. Whether the second click is needed for the `Document:` line only, or for the
   scene list and Stable IDs panel too.

Those three answers determine the fix. Without them, do not attempt one.

---

## §T8 The one that may need a human

**S5.7 / T6.5 — does the palette fight a manual window resize?** Round 3 could
not drive a manual resize through computer use (docked-edge and floating-corner
drags both had no effect) and round 4 did not reach it. It matters more than it
used to, because requested repaints now recur for the life of the palette rather
than stopping after startup, and they fire on image changes too.

If you cannot perform the resize, **say so plainly and leave it unrun.** Do not
mark it passed. Raise it with Garth directly — it is a thirty-second manual
check for a human and has now cost two rounds.

---

## Sign-off

Record the git commit hash, the OS, and docked/floating for each result.

| Test | Result | Docked/Floating | Evidence | Notes |
|---|---|---|---|---|
| T1.1 normal render | | | | |
| T1.2 blocked write, new file | | | | |
| T1.3 blocked write, existing file | | | | |
| T1.4 state restored after failure | | | | |
| T2.1 busy text clears (×4) | | | | |
| T2.2 apply reports counts | | | | |
| T2.3 apply names what it hid | | | | |
| T2.4 S2.1–S2.3 regression | | | | |
| T3.1 linked-component note | | | | |
| T3.2 note on Ensure IDs | | | | |
| T3.3 no note when all local | | | | |
| T4.1 preview vs document switch | | | | |
| T4.2 preview vs mutation | | | | |
| T4.3 newly rendered scene shows | | | | |
| T4.4 image-only repaint | | | | |
| T5.1 scroll survives a click | | | | |
| T5.2 scroll and typing | | | | |
| T5.3 editor closes with document | | | | |
| T5.4 script errors diagnosable | | | | |
| T6.1 S5.3 dock diagnostic | | | | |
| T6.2 S5.1 document switch | | | | |
| T6.3 S5.4 resize while typing | | | | |
| T6.4 S5.6 no twitch/storm | | | | |
| T6.5 S5.7 user resize | | | | |
| T6.6 S5.8 blank-on-open | | | | |
| T6.7 S6.1 one Stable IDs panel | | | | |
| T6.8 S6.2 refused capture | | | | |

### Release gate

- **Blocking**: any §T1 failure (a render failure that is not reported, or a
  normal render that broke); any §T2.1 failure; any regression in T2.4 or T6.6.
- **Report but not blocking**: §T3 (the underlying limitation is Fusion's, only
  the reporting is ours); §T4; §T5.1; S5.1/T6.2; anything that fails **only**
  while docked, recorded with its T6.1 log line as evidence.
- **Do not report as defects**: shared opacity between instances of one
  component; a linked component's ID failing to persist across a restart (that
  is the documented limitation — only a missing or wrong *report* of it is a
  defect).

### Scope note

§T1 is the blocking section and the only one that gates the release. If the
session can complete one section, complete that one.
