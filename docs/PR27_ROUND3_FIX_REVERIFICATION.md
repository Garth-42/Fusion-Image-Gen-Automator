# PR #27 — Round-3 Verification Instructions (Claude computer use)

A live-Fusion plan for an agent driving the machine through **computer use**
(screenshots + mouse/keyboard, plus a terminal and scripted Fusion access for
what a screenshot cannot prove). It covers **(a)** the fixes made in response to
the 2026-07-26 report and **(b)** the tests that have now gone two rounds
without direct verification.

**Read these first, in this order:**

1. `docs/PR27_FIX_REVERIFICATION.md` — its **corrected expectations still apply
   in full**, above all that **opacity is component-level and shared between
   instances of the same component**. Shared opacity is the expected PASS, never
   a defect. Its global error-surfacing rule also still applies: record the full
   text of every error, and an `INTERNAL_ERROR` that names no exception is
   itself a failure.
2. `docs/PR27_COMPUTER_USE_TEST_PLAN.md` — fixtures, terminal recipes, and the
   CU-numbered steps referenced below. Do not re-derive them here.

The pure-Python suite passes (100 tests). Everything in this document needs a
running Fusion session.

---

## What changed, and what each change needs from you

| # | Change | Layer | Round-2 result | Verified by |
|---|---|---|---|---|
| 1 | Palette repaint moved to the **add-in side** (window resize) | `fusion/palette_controller.py` | **FAIL** | §R1 |
| 2 | In-document repaint strengthened; burst extended to 7.5 s | `ui/palette.html` | **FAIL** | §R1 |
| 3 | Mutation outcome messages survive the refresh behind them | `ui/palette.html` | Finding 2 | §R2 |
| 4 | Scene capture checks stable IDs first, with an actionable message | `application/identity_service.py`, `application/scene_service.py` | Finding 3 | §R3 |
| 5 | Duplicated dead "Stable IDs" panel removed | `ui/palette.html` | not reported | §R4.1 |
| 6 | Pixel-diff recipe replaced with an array comparison | `docs/…TEST_PLAN.md` | CU-5.1 note | §R4.2 |

**§R1 is the point of this pass.** It is the only outright failure from round 2,
and the only change here that no test outside Fusion can reach. If you run out
of time, §R1 and §R3 are what matter.

### Why §R1 is expected to behave differently this time

The previous attempt tried to force the repaint from inside the page, which
cannot work: the workaround that works is a resize of the palette **window**,
and no JavaScript running inside a document can resize its own host window. The
resize now happens in `PaletteController.nudge_native_surface()`, which grows the
palette one pixel and puts it straight back after answering each of the page's
first three requests (`STARTUP_REPAINT_NUDGES = 3`).

Two consequences to watch for, both new-risk rather than old-bug:

- The nudge is **bounded to startup**. A palette that paints on open but goes
  stale later is a different symptom from round 2's, and worth reporting as its
  own finding.
- `setSize` can be refused by a **docked** palette. That path logs and carries
  on rather than failing the request — see §R1.5.

---

## Setup

1. Install and run the fixed add-in:
   ```bash
   cd <repo>
   git fetch origin
   git checkout claude/pr-27-revert-results-csk4c1 && git pull
   git rev-parse --short HEAD     # record this in the sign-off table
   ```
   Point Fusion's **Scripts and Add-Ins** at `addin/FusionManualSceneManager`
   and **Run** it. Confirm you are running the freshly pulled copy, not a stale
   bundle from an earlier report.
2. Open Fusion's **Text Commands** window and keep it visible for the whole
   session. It carries FMSM diagnostics you will need in §R1.5.
3. Reuse Fixtures A–E and the extras (`A-opacity`, `C-repeated`,
   `legacy-scene`, `B-nested`) from the old plan.
4. **Fixture B needs one repair before §R5.** Round 2 could not use
   `Assembly1:1/Widget:1/Widget:2` for CU-3.1 because they were grounded.
   Un-ground them (right-click the occurrence → untick **Ground**) so §R5.1 and
   §R5.2 can exercise the intended nested pair. If you cannot, use
   `Assembly2:1/VisibleChild:1` as round 2 did and say so in the notes.

### Extra conventions for this pass

- **Never collapse/expand, minimize/maximize, or manually resize the palette
  anywhere in §R1.** That gesture is the bug's workaround; using it destroys the
  result. If you need to prove a blank palette *has* content behind it, take the
  screenshot first, then nudge, and report both.
- **Time your §R1 screenshots.** Capture at roughly 0 s, 2 s, 5 s, and 10 s
  after the palette appears. Round 2 measured the blank lasting 5–7.5 s and then
  indefinitely; the shape of the delay is evidence, not just its endpoint.
- **Do not judge §R2 by the filesystem.** §R2 is entirely about whether text is
  *visible to a user*. The underlying operations already passed round 2. If a
  message is absent, the test fails even though the render succeeded.

### Scripted-Fusion snippets used below

Run these through the Fusion scripting/MCP path, not the terminal. `FMSM` is the
attribute group; `occurrence_id` and `component_id` are the attribute names.

```python
# List every component's stable ID (blank = missing)
import adsk.core
root = adsk.core.Application.get().activeProduct.rootComponent
for occurrence in root.allOccurrences:
    component = occurrence.component
    attribute = component.attributes.itemByName("FMSM", "component_id")
    print(occurrence.name, "|", component.name, "|", attribute.value if attribute else "<MISSING>")

# Remove one component's stable ID, to stage §R3.1
target = "FixtureA_Part1"          # component name
for occurrence in root.allOccurrences:
    if occurrence.component.name == target:
        attribute = occurrence.component.attributes.itemByName("FMSM", "component_id")
        if attribute:
            attribute.deleteMe()
            print("cleared", target)
        break
```

---

## §R1 Palette painting — the headline (was CU-1.1 / CU-1.2 FAIL)

### R1.1 Blank on open — paints with no nudge
1. Stop the add-in and close the palette. Confirm both.
2. Run the add-in from Scripts and Add-Ins.
3. Screenshot at ~0 s, 2 s, 5 s, 10 s. **Touch nothing.**
- **PASS**: full content — heading, `Add-in connected.`, Project section,
  buttons — painted without any manual nudge. Note which screenshot it first
  appeared in.
- **FAIL**: only the title bar and a fragment (round 2 saw the word "Fusion")
  persisting past 10 s. Record all four screenshots and continue to R1.5, which
  will tell you *why*.

### R1.2 Stop/rerun — paints with no nudge
1. Stop the add-in. Run it again. Screenshot at ~0 s, 2 s, 5 s.
- **PASS/FAIL**: as R1.1. Round 2 failed this exactly as it failed R1.1.

### R1.3 Full Fusion restart — paints with no nudge
1. Quit Fusion entirely. Relaunch, open Fixture A, run the add-in.
2. Screenshot at ~0 s, 2 s, 5 s.
- **PASS/FAIL**: as R1.1. Round 2 reproduced the blank here too, so a pass at
  R1.1 that fails here is still a failure of the fix.

### R1.4 Document switch updates on a **single** Refresh
1. With the add-in running on Fixture A, note the `Document:` line.
2. Make a different document active (Fixture E).
3. Click **Refresh exactly once**. Screenshot.
- **PASS**: the `Document:` line names the new document after one click.
- **FAIL**: it takes a second click, or a nudge. Note that this happens **after**
  the add-in's three startup nudges are spent, so it exercises the in-document
  repaint alone — report a failure here separately from R1.1.

### R1.5 Did the window resize actually happen? (diagnostic, always run)
1. Read the **Text Commands** window for FMSM lines emitted during startup.
- `palette declined the startup repaint resize.` means `setSize` was refused —
  almost certainly because the palette is **docked**. If you see this **and**
  R1.1 failed, that is the diagnosis: **re-run R1.1 with the palette floating**
  (drag it out of its dock first, then stop/rerun the add-in) and report both
  results. A fix that works floating but not docked is a real, reportable
  limitation, not a total failure.
- No such line means the resize was attempted. If R1.1 still failed, the resize
  is not sufficient on this host — say so plainly; that is the finding.
2. Record whether the palette was docked or floating for **every** §R1 result.
   Round 2 did not record this and it may explain the whole section.

### R1.6 The repaint does not eat typing
1. With the palette painted, click into **New scene title** and type a dozen
   characters slowly (~5 s of typing).
2. Screenshot mid-typing and after.
- **PASS**: every character lands, the caret stays in the field, nothing is
  reordered or dropped.
- **FAIL**: focus is lost, characters are missing, or the caret jumps. The
  repaint hides and re-shows the page body, which is suppressed while a text
  field has focus — a failure here means that suppression is not working.
- Repeat once in the **Instructions (Markdown)** textarea in the scene editor.

### R1.7 The palette does not fight a user resize
1. Resize the palette window manually to something clearly non-default.
2. Click **Refresh** three or four times, and render a scene.
3. Screenshot after each.
- **PASS**: the window stays exactly where you put it. The nudge is bounded to
  the first three requests, so nothing later should move it.
- **FAIL**: the window twitches, grows, or snaps back at any point after
  startup. Report with the count of how many actions triggered it.

### R1.8 Scene list edited on disk refreshes on one click (round-2 Finding 4)
1. Terminal: reorder two scenes in `manual.yaml` by hand (or run **Move Down**
   and then edit the file back).
2. Click **Refresh exactly once**. Screenshot the scene list.
- **PASS**: the list shows the on-disk order after one click.
- **FAIL**: a second Refresh is needed. Round 2 saw exactly this and it was
  attributed to the same stale-surface cause as R1.1 — if R1.1 passes and this
  still fails, that attribution was wrong and this is a separate bug. Say so.

---

## §R2 Feedback text is actually visible (round-2 Finding 2)

Every test here is judged **only** on what is legible in a screenshot of the
`#project-feedback` line. Do not substitute filesystem evidence.

### R2.1 Render success message is readable
1. Select a Fixture A scene. Click **Render**.
2. Screenshot as soon as the operation settles, and again ~3 s later.
- **PASS**: the line reads `Rendered assets/generated/<name>.png and
  assets/thumbnails/<name>.png.` and **stays** readable.
- **FAIL**: the line is empty, or the message flashes and is replaced by an
  empty line. Round 2's root cause was the status refresh blanking it; that
  refresh now restores it instead.

### R2.2 The other five refresh-behind-themselves messages
Run each and screenshot the feedback line:

| Action | Expected message |
|---|---|
| **Render All Scenes** | `Rendered N scene(s).` |
| **Create Scene from Current State** | `Scene list updated.` |
| **Save Metadata** (scene editor) | `Scene metadata saved.` |
| **Update Graphics from Current State** | `Scene graphics updated from current Fusion state.` |
| **Move Up** / **Move Down** | `Scene order updated.` |

- **PASS**: each message appears and stays. These shared the single root cause,
  so they should now pass or fail together — a split result is informative,
  report it.

### R2.3 A later action clears the previous message
1. After R2.1, click **Refresh**.
- **PASS**: the line goes empty. A stale outcome must not outlive the action it
  describes.
- **FAIL**: the old "Rendered …" text persists next to unrelated new state.

### R2.4 Render failure message is readable (the intermittent half)
1. Terminal: `chmod -R a-w assets/generated`.
2. Click **Render**. Screenshot the feedback line. Restore with
   `chmod -R u+w assets/generated`.
- **PASS**: `Error (RENDER_FAILED): …` is legible.
- **FAIL**: no visible message. Round 2 found this half **intermittent** and it
  was **not** separately diagnosed. If R1 passes and this still fails, it is an
  undiagnosed bug in its own right — capture the exact sequence, whether the
  palette was docked, and how many attempts out of how many showed the text.

---

## §R3 Stable-ID guard on capture (round-2 Finding 3)

Round 2 hit `Error (COMPONENT_ID_INVALID): Component ID must be a UUID.` because
`FixtureA_Part1` had no `FMSM.component_id` attribute, and asked whether the
add-in can self-heal that condition. **§R3.2 is the answer to that question and
is the most valuable test in this section.**

### R3.1 A missing ID gives an actionable message, not a schema error
1. Open Fixture A. Run the **list** snippet above; confirm every component has an
   ID (if `FixtureA_Part1` is still missing one from round 2's manual repair,
   even better — skip to step 3).
2. Run the **remove** snippet on one component to clear its ID.
3. Click **Create Scene from Current State**. Screenshot the feedback line.
- **PASS**: an error naming the part **and** the button. The exact string, taken
  from the code rather than paraphrased:
  > `Error (IDENTITY_IDS_MISSING): 1 entity without a stable ID, so this scene could not be replayed: FixtureA_Part1. Click Ensure IDs, then capture again.`

  A missing **component** ID reports the component's name (`FixtureA_Part1`); a
  missing **occurrence** ID reports the occurrence's name (`FixtureA_Part1:1`).
  Use that suffix to tell which of the two you actually cleared.
- **FAIL**: the old `Error (COMPONENT_ID_INVALID): Component ID must be a UUID.`,
  or any message that names neither the part nor the fix.
4. Terminal: confirm the refused capture left nothing behind — no new file in
   `scenes/`, and no new entry in `manual.yaml`.

### R3.2 **Ensure IDs self-heals it** (the round-2 open question)
1. Directly after R3.1, click **Ensure IDs**. Screenshot.
2. Click **Create Scene from Current State** again. Screenshot.
- **PASS**: Ensure IDs reports assigning at least one component ID, the Stable
  IDs panel goes clean, and the capture now succeeds — **with no scripted
  intervention**. This is what round 2 had to fix by hand.
- **FAIL**: Ensure IDs reports 0 assigned, or capture still refuses. That would
  mean the add-in genuinely cannot self-heal this condition, which is a real gap
  in ID-assignment coverage and should be reported as such.
3. Run the **list** snippet again to confirm the component now has a real UUID.
4. Repeat R3.1 + R3.2 once for an **occurrence** ID (`occurrence_id` instead of
   `component_id`) — the guard covers both and only components were exercised in
   round 2.

### R3.3 Duplicate IDs are refused at capture, pointing at Repair
1. On Fixture E, re-create the duplicate `occurrence_id` condition from CU-5.2.
2. Click **Create Scene from Current State**. Screenshot.
- **PASS**: capture is refused **before** a bad scene is written, where
  previously only render was gated. Exact shape:
  > `Error (DUPLICATE_OCCURRENCE_ID): 2 entities sharing a stable ID cannot be told apart when the scene replays: Widget:1, Widget:2. Click Repair Duplicate IDs, then capture again.`
3. Click **Repair Duplicate IDs**, then capture again.
- **PASS**: capture succeeds.

### R3.4 Recapture is guarded the same way, and is non-destructive
1. On a scene that already exists, clear one component's ID (snippet above).
2. Select the scene, click **Update Graphics from Current State**. Screenshot.
- **PASS**: the same `IDENTITY_IDS_MISSING` error, **and** — check with
  `git diff` — the existing scene YAML on disk is completely unchanged. A
  refused recapture must not partially overwrite the scene it was editing.
3. Click **Ensure IDs**, retry, confirm it succeeds.

### R3.5 A healthy fixture is unaffected (regression watch)
1. On a fixture where every entity has a valid ID, capture a scene normally.
- **PASS**: capture works exactly as before, with no new error and no perceptible
  delay. The guard runs an identity scan on every capture; on Fixture A's large
  manifest, note whether capture feels slower than round 2.
- **FAIL**: a healthy design is refused. That would be a false positive in the
  guard and is blocking — report immediately with the full message.

---

## §R4 Small fixes

### R4.1 Exactly one "Stable IDs" panel
1. With a document open and the palette fully painted, scroll the whole palette.
   Screenshot top to bottom.
- **PASS**: exactly **one** "Stable IDs" section. A duplicate `<section>` used to
  render a second, dead copy whose buttons did nothing.
- **FAIL**: two. Also confirm the **Ensure IDs** and **Repair Duplicate IDs**
  buttons you click actually respond (round 2 could have been clicking the dead
  pair without knowing).

### R4.2 Updated pixel-diff recipe works
1. Re-run CU-5.1's comparison using the **array-diff recipe** now in the plan,
   against the three `camera-test-*` renders.
- **PASS**: it reports non-zero differing-pixel counts for all three pairs,
  matching round 2's numpy findings (636K–959K of 3.84M pixels).
- This is a check on the *plan's recipe*, not on the product. If it disagrees
  with round 2's numbers, say so — the recipe is what future rounds will trust.

---

## §R5 Carried over — never directly verified in round 1 or 2

These are not new, and none of this round's changes touch them. They are here
because two consecutive reports have deferred them, and "low risk" is not
"verified".

### R5.1 CU-3.2 — Restore Previous State with nested occurrences
Follow `PR27_COMPUTER_USE_TEST_PLAN.md` §CU-3.2 exactly, on the un-grounded
Fixture B pair from Setup step 4. Round 2 deferred this after losing state to a
mid-session restart; do it **early in a fresh session** so a restart cannot
strand it again.
- **PASS**: the assembly returns to the *modified* pose, nested children at their
  correct relative offsets.
- Use the **Inspect → Measure** parent-vertex-to-child-vertex check from CU-3.1
  for quantitative evidence rather than eyeballing the screenshot.

### R5.2 CU-3.3 — Render a Fixture B scene round-trips transforms
Follow §CU-3.3. Compare the output PNG against the reference-pose screenshot
with the array-diff recipe where possible.
- **PASS**: nested parts correctly assembled in the PNG; viewport restored after.

### R5.3 CU-6.2 — Project folder removed mid-session
Follow §CU-6.2. Round 2 skipped this as optional.
- **PASS**: a clear `PROJECT_ROOT_UNRESOLVED`-style error, no crash, no blank
  panel. Restore the folder afterward and confirm the palette recovers.

### R5.4 CU-6.3 — Stable-ID persistence across a Fusion restart
Follow §CU-6.3, both halves (saved and unsaved). This one now interacts directly
with §R3: if IDs do not persist across a save/restart, §R3's guard will start
refusing captures that used to work.
- **PASS**: saved → IDs persist and capture works with no Ensure IDs click;
  unsaved → Ensure IDs is required again, and §R3.1's message is what tells the
  user so.

---

## §R6 Fast regression sweep

The capture path changed, so re-confirm these round-2 passes. One run each, no
deep investigation unless something fails.

| Check | Source | Expected |
|---|---|---|
| Render produces 2400×1600 + 480×320 | CU-2.1 | unchanged |
| State restored after a failed render | CU-2.3 | unchanged |
| Opacity round-trips (shared, component-level) | CU-4.1 | unchanged |
| Legacy scene replays real translucency | CU-4.4 | unchanged |
| Broken reference blocks render | CU-5.2 | unchanged |
| Reorder touches only `manual.yaml` | CU-5.3 | unchanged |
| Corrupted `manual.yaml` shows a clear error | CU-6.1 | unchanged — and now check it appears **without** the repaint nudge round 2 needed |

---

## Sign-off

Record the git commit hash, the OS, and **whether the palette was docked or
floating**, then fill in:

| Test | Result | Docked/Floating | Evidence | Notes |
|---|---|---|---|---|
| R1.1 blank on open | | | | |
| R1.2 stop/rerun | | | | |
| R1.3 full Fusion restart | | | | |
| R1.4 doc switch, one Refresh | | | | |
| R1.5 resize diagnostic | | | | |
| R1.6 typing not disrupted | | | | |
| R1.7 user resize not fought | | | | |
| R1.8 scene list, one Refresh | | | | |
| R2.1 render success visible | | | | |
| R2.2 other five messages | | | | |
| R2.3 later action clears | | | | |
| R2.4 render failure visible | | | | |
| R3.1 missing ID actionable | | | | |
| R3.2 Ensure IDs self-heals | | | | |
| R3.3 duplicates refused | | | | |
| R3.4 recapture guarded | | | | |
| R3.5 healthy fixture unaffected | | | | |
| R4.1 one Stable IDs panel | | | | |
| R4.2 pixel-diff recipe | | | | |
| R5.1 CU-3.2 nested restore | | | | |
| R5.2 CU-3.3 nested render | | | | |
| R5.3 CU-6.2 folder removed | | | | |
| R5.4 CU-6.3 ID persistence | | | | |
| R6 sweep (7 rows) | | | | |

### Release gate

- **Blocking**: any R1.1–R1.3 failure with the palette **floating**; any R3.5
  false positive; any R2.1 failure; any R5.1/R5.2 nested-transform corruption.
- **Report but not blocking**: R1 failures that occur **only** while docked
  (record it as a limitation with the R1.5 log line as evidence); R2.4 if it
  remains intermittent; R5.3/R5.4.
- **Do not report as defects**: shared opacity between instances of one
  component, and any behavior the round-2 corrected-expectations section already
  reclassified.

### If §R1 fails again

Two rounds of repaint fixes have now failed. Before a third attempt is designed,
this pass needs to establish which of these is true, so include whichever
applies in the report:

1. The resize is **not being attempted** — R1.5 shows the "declined" log line.
   → The docking state is the cause; a docked palette needs a different lever.
2. The resize **is attempted and insufficient** — no log line, still blank.
   → Resizing is not what invalidates this host's surface, and the whole
   approach needs rethinking rather than another increment.
3. The palette paints on open but **goes stale later** (R1.4/R1.8 fail while
   R1.1 passes) → the bound of three startup nudges is too tight.

Distinguishing these three is more useful than any amount of additional
screenshots of a blank window.
