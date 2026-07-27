# Round-4 Verification Plan (Claude computer use)

A live-Fusion plan for an agent driving the machine through **computer use**
(screenshots + mouse/keyboard, plus scripted Fusion access for what a screenshot
cannot prove).

**Read these first, in this order:**

1. `docs/PR27_FIX_REVERIFICATION.md` — its **corrected expectations still apply
   in full**. See the opacity correction restated below; do not skip it.
2. `docs/PR27_COMPUTER_USE_TEST_PLAN.md` — fixtures, terminal recipes, and the
   CU-numbered steps referenced throughout. Do not re-derive them here.
3. `docs/PR27_ROUND3_RESULTS.md` — what round 3 established, and what it did not.

The pure-Python suite passes (107 tests). Everything in this document needs a
running Fusion session.

---

## Why this pass is ordered the way it is

Rounds 1, 2 and 3 all spent their time on the palette. That was defensible — a
palette showing stale content makes every other test unreliable to read — but it
has had three passes and now paints correctly on open. Meanwhile:

> **PR #27's headline commit (`556a04f`, "Fix nested-occurrence transform
> replay") has never been verified against real Fusion.** Its tests are CU-3.2
> and CU-3.3, and all three rounds deferred them.

That fix is covered by unit tests, but only against a hand-written stub whose
`transformOccurrences` returns `True`. This project has already been burned by
exactly that gap: round 2's blocker was
`occurrence.component.createForAssemblyContext(occurrence).opacity`, which passed
its mocked tests and **did not exist on the real API**. `transformOccurrences(...,
ignoreJoints=True)` carries the same risk, and assumption **A-1** (transform
batching) is still marked as needing live confirmation.

So this pass runs **functional core first, palette last**. If you run out of
time, §S1 and §S2 are what matter. §S5 is genuinely the lowest priority here,
which reverses the previous three rounds.

---

## ⚠️ Corrected expectations — read before §S3

**Opacity is component-level and shared between instances of the same
component.** Shared opacity is the expected **PASS**, never a defect.

This overrides `PR27_COMPUTER_USE_TEST_PLAN.md` **CU-4.2**, which was written
when a per-instance override was thought to exist. It does not: `Occurrence` has
no writable `opacity`, and `Component.createForAssemblyContext` does not exist.
The code reads and writes `Component.opacity`. Two instances of one component
ending at the same opacity is correct behaviour — **do not report it**. Only a
crash, or a failure to restore the shared value, is a defect.

Note that `556a04f`'s own commit message describes per-occurrence opacity
proxies. That half of the commit was **superseded** by `bfa7bc0`. The transform
half of `556a04f` still stands and is what §S1 tests.

**Global error-surfacing rule:** record the full text of every error. An
`INTERNAL_ERROR` that names no exception is itself a failure.

---

## Setup

1. Install and run the add-in from `main` (it now carries the round-3 fixes plus
   the repaint-ordering fix):
   ```bash
   cd <repo>
   git fetch origin && git checkout main && git pull
   git rev-parse --short HEAD     # record this in the sign-off table
   ```
   Point Fusion's **Scripts and Add-Ins** at `addin/FusionManualSceneManager`
   and **Run** it. Confirm you are running the freshly pulled copy.
2. Open Fusion's **Text Commands** window and keep it visible all session. It
   carries the FMSM diagnostics §S5.3 needs.
3. Reuse Fixtures A–E and the extras (`A-opacity`, `C-repeated`, `legacy-scene`,
   `B-nested`).
4. **Fixture B needs one repair before §S1.** Round 2 could not use
   `Assembly1:1/Widget:1/Widget:2` because they were grounded. Un-ground them
   (right-click the occurrence → untick **Ground**). If you cannot, use
   `Assembly2:1/VisibleChild:1` as round 2 did and **say so** — a substitute pair
   makes the result weaker evidence, and that needs to be on the record.
5. **Record whether the palette is docked or floating for every result.**
6. Do §S1 **early, in a fresh session.** Round 2 lost it to a mid-session
   restart. Do not let that happen a fourth time.

---

## §S1 Nested-occurrence transforms — the point of this pass

Verifies `556a04f` and assumption **A-1**. Never directly verified in any round.
Use **B-nested**.

### S1.1 Apply Captured State keeps nested children in place (CU-3.1)
1. Open **B-nested**. Frame a clear view; screenshot the viewport — this is the
   **reference pose**.
2. Before capturing, use **Inspect → Measure** to record the distance between a
   parent vertex and a nested-child vertex. Write the number down.
3. Click **Capture Current State**.
4. Move the parent occurrence, then move a nested child, then change the camera.
5. Click **Apply Captured State**. Screenshot, and re-measure the same two
   vertices.
- **PASS**: the assembly matches the reference pose and the measured distance
  matches what you recorded. Every nested child sits at its original offset.
- **FAIL**: the parent returns correctly but nested children are displaced,
  roughly by the parent's move. *(That is the exact Fixture B corruption
  `556a04f` claims to fix.)*
- The measurement is the evidence. A screenshot comparison alone cannot settle a
  small offset, and this is the test the whole PR rests on.

### S1.2 Restore Previous State (CU-3.2)
1. Directly after S1.1, click **Restore Previous State**. Screenshot and measure.
- **PASS**: the assembly returns to the *modified* pose from S1.1 step 4, nested
  children intact. Restore uses the same batch-transform path, so a pass at S1.1
  with a failure here means the two paths have diverged — report that precisely.

### S1.3 Render a Fixture B scene round-trips transforms (CU-3.3)
1. Create a scene from B-nested's reference pose. **Render** it.
2. Open the output PNG and compare against the S1.1 reference screenshot, using
   the array-diff recipe where possible.
- **PASS**: nested parts correctly assembled in the PNG, and the viewport is
  restored afterwards.
- **FAIL**: nested parts displaced in the PNG. Note that render replays state
  into the viewport and back, so this can fail even if S1.1 and S1.2 pass.

### S1.4 If §S1 fails
Capture, for each failing step: the full error text if any, the measured
distances, and whether the failure is a **uniform** offset (suggesting the batch
applied in the wrong coordinate context) or a **per-child** one (suggesting the
batch did not happen at all and per-occurrence `transform2` writes are still
fighting each other). That distinction is what determines the next fix, and it
is worth more than extra screenshots.

---

## §S2 Feedback text is actually visible (round-2 Finding 2, never verified)

Round 2 found outcome messages were being blanked by the status refresh behind
them. That was fixed in code and has never been confirmed. **R2.1 is a release
gate item.**

Every test here is judged **only** on what is legible in a screenshot of the
`#project-feedback` line. **Do not substitute filesystem evidence** — the
underlying operations already passed round 2. If a message is absent, the test
fails even though the operation succeeded.

### S2.1 Render success message is readable
1. Select a Fixture A scene. Click **Render**.
2. Screenshot as soon as the operation settles, and again ~3 s later.
- **PASS**: the line reads `Rendered assets/generated/<name>.png and
  assets/thumbnails/<name>.png.` and **stays** readable.
- **FAIL**: empty, or the message flashes and is replaced by an empty line.

### S2.2 The other five refresh-behind-themselves messages
| Action | Expected message |
|---|---|
| **Render All Scenes** | `Rendered N scene(s).` |
| **Create Scene from Current State** | `Scene list updated.` |
| **Save Metadata** (scene editor) | `Scene metadata saved.` |
| **Update Graphics from Current State** | `Scene graphics updated from current Fusion state.` |
| **Move Up** / **Move Down** | `Scene order updated.` |

- **PASS**: each appears and stays. These shared one root cause, so they should
  pass or fail together — a split result is informative, report it.

### S2.3 A later action clears the previous message
1. After S2.1, click **Refresh**.
- **PASS**: the line goes empty. A stale outcome must not outlive its action.

### S2.4 Render failure message is readable
1. Terminal: `chmod -R a-w assets/generated`.
2. Click **Render**. Screenshot. Restore with `chmod -R u+w assets/generated`.
- **PASS**: `Error (RENDER_FAILED): …` is legible.
- Round 2 found this half **intermittent** and never diagnosed it. If it fails,
  record how many attempts out of how many showed the text, and whether the
  palette was docked.

---

## §S3 Regression sweep against the changed capture path

These passed in round 2, but the capture path has changed since (the §R3 stable-ID
guard now runs an identity scan on every capture). One run each, no deep
investigation unless something fails.

| # | Check | Source | Expected |
|---|---|---|---|
| S3.1 | Render produces 2400×1600 + 480×320 | CU-2.1 | unchanged |
| S3.2 | State restored after a failed render | CU-2.3 | unchanged |
| S3.3 | Opacity round-trips (**shared, component-level**) | CU-4.1 | unchanged |
| S3.4 | Legacy scene replays real translucency | CU-4.4 | unchanged |
| S3.5 | Broken reference blocks render | CU-5.2 | unchanged |
| S3.6 | Reorder touches only `manual.yaml` | CU-5.3 | unchanged |
| S3.7 | Corrupted `manual.yaml` shows a clear error | CU-6.1 | unchanged |
| S3.8 | Healthy fixture still captures first time | R3.5 | unchanged |

S3.3: re-read the opacity correction above before judging this one.

---

## §S4 Troubleshooting states — carried over, never verified

### S4.1 Project folder removed mid-session (CU-6.2)
1. With a project open, terminal-move the project folder aside.
2. Press **Refresh**, then attempt a scene operation. Screenshot.
- **PASS**: `PROJECT_ROOT_UNRESOLVED` or a clear "open the project folder"
  message; no crash, no blank panel. Restore the folder and confirm recovery.

### S4.2 Stable-ID persistence across a Fusion restart (CU-6.3)
1. On a fresh Fixture A: **Ensure IDs**, **save the document**, restart Fusion,
   reopen, run the add-in.
2. Repeat **without** saving before the restart.
- **PASS**: saved → IDs persist and capture works with no Ensure IDs click;
  unsaved → Ensure IDs is required again, and the §R3.1 message is what says so.
- This interacts with the stable-ID guard: if IDs do not persist across a
  save/restart, the guard will start refusing captures that used to work.

---

## §S5 Palette repaint — verifying the round-3 follow-up fix

**Lowest priority in this pass.** Run it only once §S1–§S3 are done.

Round 3 fixed blank-on-open but left the palette going stale later: a Refresh
after switching documents, or behind a scene list edited on disk, needed 2–3
clicks. The cause was ordering — the window resize ran as a request was
*answered*, which is before the page had applied the response to its DOM. The
page now asks for the resize *after* it redraws, and only when visible content
changed. §S5 checks that, and the new risks it introduces.

### S5.1 Document switch updates on a single Refresh, both directions
1. With the add-in running on Fixture A, note the `Document:` line.
2. Make a **fresh** document active. Click **Refresh exactly once**. Screenshot.
3. Now switch **back** to a previously-viewed document. Click **Refresh exactly
   once**. Screenshot.
- **PASS**: the `Document:` line names the new document after **one** click in
  **both** directions. The back-switch is the case that took 2–3 clicks; it is
  the one that matters.

### S5.2 Scene list edited on disk refreshes on one click — isolated
1. **Without** switching documents first, reorder two scenes in `manual.yaml` by
   hand.
2. Click **Refresh exactly once**. Screenshot the scene list.
- **PASS**: the list shows the on-disk order after one click.
- Round 3's 3-click figure here was conflated with the document-switch lag. Keep
  this one isolated so the number means something.

### S5.3 Docked vs floating — the make-or-break diagnostic
Run S5.1 with the palette **docked**, then again **floating**.
1. Read **Text Commands** for FMSM lines.
- `palette declined the requested repaint resize.` means the host refused
  `setSize`, so the fix **cannot work in that dock state**. That is a real,
  reportable limitation, not a mystery — and it is the first thing to check if
  S5.1 or S5.2 fail.
- `palette declined the startup repaint resize.` is the startup-burst equivalent.
- Each line is logged **once per kind** by design; do not read a single
  occurrence as a single refusal.

### S5.4 A window resize while a text field has focus
The highest-likelihood **new** bug in this fix.
1. Put the caret in the scene editor's **Instructions (Markdown)** textarea.
2. Without clicking away, click **Save Metadata**. A response arrives, content
   changes, and the window resizes.
- **PASS**: the caret stays put, no characters are lost, focus is retained.
- The in-document repaint skips itself while a field has focus. The **native
  window resize has no such guard** and cannot have one — the add-in cannot see
  focus. If this fails, that is the gap.

### S5.5 Preview images may not trigger a repaint
A known limitation by construction, worth confirming rather than discovering.
The "did content change?" check compares **text**, so a change that is purely an
image may not request a repaint.
1. Click **Preview Summary**. Screenshot.
2. Re-render a scene whose surrounding text does not change, and look at the
   embedded thumbnail.
- **PASS**: the image appears/updates without extra clicks.
- **FAIL** here is plausible and expected-ish. Report it; the fix is to extend
  the change signature to cover image sources.

### S5.6 No visible twitch, no request storm
1. Click **Refresh** several times, render a scene, and move a scene up and down.
   Watch the window edge.
- **PASS**: no perceptible flicker, growth, or snap-back, and Text Commands shows
  no runaway repeated activity.

### S5.7 The palette does not fight a user resize
Never verified in any round, and it now matters more: repaints recur for the life
of the palette rather than stopping after startup.
1. Resize the palette manually to something clearly non-default.
2. Click **Refresh** three or four times, and render a scene.
- **PASS**: the window stays exactly where you put it.
- **FAIL**: it twitches, grows, or snaps back. Report with the count of actions
  that triggered it.
- Round 3 could not drive a manual resize through computer use (docked-edge and
  floating-corner drags both had no effect). **This one may need a human.** If
  you cannot perform the resize, say so plainly rather than marking it passed.

### S5.8 Regressions — blank on open still fixed
Re-confirm R1.1 (blank on open), R1.2 (stop/rerun), R1.3 (full Fusion restart —
note that File → Quit does **not** quit the app, only the document; use Cmd+Q),
and R1.6 (plain typing, no mutation). Screenshot at ~0 s, 2 s, 5 s, 10 s and
**touch nothing**. The startup burst is unchanged, so these should be unchanged.

### S5.9 Perceived speed
Every content-changing response now costs one extra round trip plus two `setSize`
calls. On Fixture A's large manifest, does **Refresh** or **Render All Scenes**
feel slower than round 3? A subjective note is fine; a stopwatch is better.

---

## §S6 Small fixes

### S6.1 Exactly one "Stable IDs" panel
Scroll the whole palette, top to bottom.
- **PASS**: exactly **one** "Stable IDs" section, and the **Ensure IDs** /
  **Repair Duplicate IDs** buttons you click actually respond.

### S6.2 R3.1 step 4 — the refused capture really wrote nothing
Round 3 checked this loosely. Clear one component's ID, attempt **Create Scene
from Current State**, and confirm with `git status` that **no** new file appeared
in `scenes/` and **no** new entry appeared in `manual.yaml`.

---

## Sign-off

Record the git commit hash, the OS, and **whether the palette was docked or
floating** for each result.

| Test | Result | Docked/Floating | Evidence | Notes |
|---|---|---|---|---|
| S1.1 nested apply | | | | |
| S1.2 nested restore | | | | |
| S1.3 nested render | | | | |
| S2.1 render message visible | | | | |
| S2.2 other five messages | | | | |
| S2.3 later action clears | | | | |
| S2.4 render failure visible | | | | |
| S3.1–S3.8 sweep | | | | |
| S4.1 folder removed | | | | |
| S4.2 ID persistence | | | | |
| S5.1 doc switch, one Refresh | | | | |
| S5.2 on-disk reorder, isolated | | | | |
| S5.3 docked vs floating | | | | |
| S5.4 resize during typing | | | | |
| S5.5 preview image repaint | | | | |
| S5.6 no twitch / no storm | | | | |
| S5.7 user resize not fought | | | | |
| S5.8 blank-on-open regressions | | | | |
| S5.9 perceived speed | | | | |
| S6.1 one Stable IDs panel | | | | |
| S6.2 refused capture wrote nothing | | | | |

### Release gate

- **Blocking**: any §S1 failure (nested transform corruption); any S2.1 failure;
  any S3 regression; a false positive from the stable-ID guard.
- **Report but not blocking**: S5 failures that occur **only** while docked
  (record with the S5.3 log line as evidence); S2.4 if it remains intermittent;
  S4.1/S4.2; S5.5; S5.9.
- **Do not report as defects**: shared opacity between instances of one
  component, and anything the corrected-expectations section above reclassifies.

### Scope note

§S1 is the oldest unverified item in the project and the one the PR is named
after. If the session can only complete one section, complete that one.
