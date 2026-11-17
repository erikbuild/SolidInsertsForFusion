# Seat Chamfer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an option, on by default, to chamfer each seat's top edge, with a configurable size that defaults to 0.4 mm.

**Architecture:** `seats.py` carries the chamfer on each planned `Seat` and adds its checks, with the mouth diameter used for the edge and overlap checks. `cuts.py` adds a Fusion chamfer feature on the seat mouth after each extrude cut. `preview.py` draws the chamfer as a cone on top of each cylinder. `command.py` adds the checkbox and the size spinner.

**Tech Stack:** Fusion add-in API (Python 3.14), stdlib `unittest`, and in-Fusion test scripts that Erik runs.

**Spec:** Erik approved this description in chat on 2026-11-17 ("Looks good"). It is repeated here because there is no separate spec file. Items marked *(Claude's call)* were proposed by Claude and approved along with the rest.

- **Dialog:**
  - A **Chamfer top edge** checkbox, on by default, and a **Chamfer size** spinner (mm, default 0.40 mm) below **Diameter compensation**.
  - The spinner is greyed out while the box is unchecked.
  - The spinner range is 0.1–2 mm in 0.05 mm steps *(Claude's call)*.
  - Neither setting is remembered between runs *(Claude's call)*.
- **Cut:**
  - After each seat's extrude cut, an equal-distance (45°) Fusion **Chamfer** feature goes on the seat mouth, where the seat wall meets the face *(Claude's call)*.
  - It is named `SolidInserts · Chamfer …` and can be edited in the timeline.
  - It is part of the same single Undo.
  - If Fusion cannot make it, OK fails with a message and the batch rolls back.
- **Checks when the box is on:**
  - The edge and overlap checks use the mouth diameter (seat diameter + 2 × chamfer).
  - When the plain seat already fails a check, only the existing message appears.
  - When only the chamfer fails, a separate message names the chamfer *(Claude's call)*.
  - The thin-wall note keeps using the seat diameter *(Claude's call)*.
  - Erik asked for this rule: "check for that too, if the option is selected".
- **Summary and preview:**
  - Each seat line gains ` · 0.40 mm chamfer`.
  - The orange preview draws the chamfer cone at the top of each cylinder.

## Decisions Made While Planning (Claude's calls; Erik to confirm)

1. **`plan_seats` takes `chamfer_mm` as a keyword after `rim_errors`.** Its value is `None` when the box is off. Every caller passes `rim_errors` by position, so adding the parameter at the end keeps an existing call from silently passing its errors as the chamfer.
2. **The chamfer range is checked in `plan_seats`**, the same way as compensation. The range constants live in `seats.py`, and the dialog spinner uses them too.
3. **There is no volume check on the chamfer.** The planner already keeps the mouth clear of face edges and other seats. Fusion's own failure becomes the `chamfer_failed` message. The integration test measures the volume the chamfer removes.
4. **Re-picking a chamfered seat's rim** gives the existing "no chamfer" refusal, not "already created". That rim now meets a cone rather than a cylinder.
5. **Tasks 2 and 3 share Fusion runs.** Erik runs the RED integration test and the RED end-to-end test once each, and the GREEN runs once each.

## Global Constraints

- Fusion API lengths are centimetres. The pure modules (`catalog`, `geometry`, `seats`, `messages`) work in millimetres, never import `adsk`, and import under plain CPython ≥ 3.12.
- Every code file starts with two `# ABOUTME: ` lines. Names and comments contain no time references.
- All user-facing copy lives in `messages.py`. Dimension expressions carry an explicit `mm`.
- Unit test command (repo root): `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`. Its output must be pristine.
- In-Fusion tests are `tests/fusion/SolidInsertsIntegrationTest` (it loads the add-in package from the repo) and `tests/fusion/SolidInsertsCommandTest` (it drives the running add-in, so Erik reloads the add-in first with Stop and Run). Both end with `==== N passed, M failed ====`.

## Ground Rules For The Executing Agent

1. **Commit only with Erik's OK.** At each commit step, stop, suggest a message, and wait. If Erik grants standing approval for this plan, record it in the ledger and commit at the steps.
2. **Claude cannot run Fusion.** At each **[FUSION — Erik runs]** step, stop and wait for Erik to paste the Text Commands output.

## Review Focus

1. **Bracket component in two occurrences:** the mouth edge is found in component space, and the chamfer shows in both instances. *(Task 2: `test_bracket` with a chamfer.)*
2. **Inch display units:** the chamfer is still 0.4 mm. *(Task 2: `test_inch_display_units`.)*
3. **A chamfer that reaches an edge the plain seat clears:** h5 has 2.5 mm clearance. A 0.5 mm chamfer on its Ø4 seat is blocked; a 0.4 mm chamfer is not. *(Task 2: `test_chamfer_clearance`; Task 1 unit tests.)*
4. **Unchecking the box:** the spinner is disabled, the preview loses its cones, and no chamfer feature is cut. *(Task 2: the end-to-end steps.)*
5. **A chamfer Fusion cannot make:** OK fails with `chamfer_failed`. *(Task 2: `test_chamfer_failure`.)*

---

### Task 1: Chamfer planning and copy

**Files:**
- Modify: `SolidInserts/messages.py`, `SolidInserts/seats.py`
- Test: `tests/unit/test_seats.py`, `tests/unit/test_messages.py`

**Interfaces:**
- Produces:
  - `seats.CHAMFER_MIN_MM = 0.1` and `seats.CHAMFER_MAX_MM = 2.0`.
  - `Seat.chamfer: float | None` (mm), the last field.
  - `Seat.mouth_diameter` property: `diameter + 2 * chamfer`, or `diameter` when there is no chamfer.
  - `plan_seats(openings, series, thread_label, compensation_mm, rim_errors=(), chamfer_mm=None)`.
- New message keys:
  - `chamfer_label`: `Chamfer top edge`
  - `chamfer_tooltip`: `Adds a 45° lead-in at the seat opening so the insert starts straight.`
  - `chamfer_size_label`: `Chamfer size`
  - `chamfer_size_tooltip`: `How far the chamfer cuts into the face and down the seat wall.`
  - `chamfer_range`: `Chamfer size must be between {low:.2f} and {high:.2f} mm.`
  - `chamfer_reaches_edge`: `The {chamfer:.2f} mm chamfer on the Ø{seat:.2f} seat reaches a nearby edge at the opening.`
  - `chamfers_overlap`: `The chamfers of the seats for holes {first} and {second} overlap at the opening.`
  - `seat_chamfer`: ` · {chamfer:.2f} mm chamfer`
  - `chamfer_name`: `Chamfer {name}`
  - `chamfer_failed`: `The chamfer could not be cut at the seat opening. Make it smaller or turn it off.`

- [ ] **Step 1: Write the failing tests.**
  - In `test_seats.py`, the `plan` helper gains `chamfer=None` and passes `chamfer_mm=chamfer`.
  - New `PlanSeatsTest` cases:
    - `test_chamfer_is_carried_on_each_seat`: `plan(M3, chamfer=0.4)` gives `(chamfer, mouth_diameter) == (0.4, 4.8)`, and `plan(M3)` gives `(None, 4.0)`.
    - `test_chamfer_reaching_an_edge`: `plan(opening(clearance=2.3), chamfer=0.4).obstacles == ('Hole 1 on Plate. The 0.40 mm chamfer on the Ø4.00 seat reaches a nearby edge at the opening.',)`, and the same opening without a chamfer has no obstacles.
    - `test_a_seat_reaching_an_edge_names_only_the_seat`: `plan(opening(clearance=2.0), chamfer=0.4).obstacles` equals the plain `seat_reaches_edge` message only.
    - `test_overlapping_chamfers`: openings at x = 40 and 44.5 give `('The chamfers of the seats for holes 1 and 2 overlap at the opening.',)` with `chamfer=0.4` and `()` without.
    - `test_overlapping_seats_name_only_the_seats`: openings at x = 40 and 43.5 with `chamfer=0.4` give only the `seats_overlap` message.
    - `test_chamfer_out_of_range`: 0.05 and 2.5 each give `'Chamfer size must be between 0.10 and 2.00 mm.'` in the obstacles and `can_apply` False. 0.1 and 2.0 give no obstacles.
    - `test_thin_wall_note_ignores_the_chamfer`: `plan(opening(clearance=2.5), chamfer=0.4)` has the same note as without the chamfer (0.50 mm) and no obstacles.
  - New `SummaryLinesTest` case: `test_lists_each_seat_with_its_chamfer` expects `summary_lines(plan(M3, chamfer=0.4)) == ['Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm · 0.40 mm chamfer']`.
  - In `test_messages.py`, `test_dialog_copy_names_the_command_and_its_inputs` gains the four `chamfer_label`, `chamfer_tooltip`, `chamfer_size_label` and `chamfer_size_tooltip` entries.

- [ ] **Step 2: Run the unit tests.**
  Expected: the new cases FAIL or error. They fail on the unknown keyword `chamfer_mm`, the missing `chamfer` and `mouth_diameter`, and the `KeyError` for the copy. The existing 51 pass.

- [ ] **Step 3: Implement the planning and the copy.**
  - Add the message keys to `messages.py`.
  - In `seats.py`:
    - Check the chamfer range right after the compensation check, with the same early-return shape.
    - Round the chamfer with `round_mm`.
    - Run the chamfer edge check as an `elif` after the seat edge check: `hole.clearance - seat.mouth_diameter / 2 <= TOLERANCE_MM`.
    - Run the overlap check as an `elif` on `(seat.mouth_diameter + other.mouth_diameter) / 2`.
    - `summary_lines` appends `seat_chamfer` to a seat line when the seat has a chamfer.

- [ ] **Step 4: Run the unit tests.**
  Expected: all pass, with pristine output.

- [ ] **Step 5: Commit.** Message: `Plan seat chamfers and check them against edges and other seats`.

### Task 2: Chamfer cut, preview and dialog

**Files:**
- Modify:
  - `SolidInserts/cuts.py`
  - `SolidInserts/preview.py`
  - `SolidInserts/command.py`
  - `docs/user-guide.md`
  - `README.md`
- Test:
  - `tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py`
  - `tests/fusion/SolidInsertsCommandTest/SolidInsertsCommandTest.py`

**Interfaces:**
- Consumes: everything Task 1 produces.
- Produces:
  - `cuts.cut_seat` adds the chamfer feature after `check_cut` when `seat.chamfer` is set. `cut_seats` still returns the extrude features.
  - The dialog has the inputs `chamfer` (`BoolValueCommandInput`) and `chamfer_size` (`FloatSpinnerCommandInput`).

- [ ] **Step 1: Write the failing integration cases.**
  - `cut_rims` gains `chamfer=None` and passes it as `chamfer_mm`.
  - `test_bracket` cuts with `chamfer=0.4`. Both occurrences then lose 37.907 mm³ (±0.02), and the timeline gains 3 items.
  - New `test_chamfered_seats`:
    - Cut h1 and h2 with `chamfer=0.4`. The Plate loses 157.263 mm³ (±0.02), which is the two seats plus π·c²·(r + c/3) per chamfer.
    - The root component's `chamferFeatures.itemByName` finds `SolidInserts · Chamfer Insert M3 × 5.7` and `… M4 × 8.1`.
    - Each has one edge set whose distance expression is `0.4 mm`.
  - `test_inch_display_units` cuts with `chamfer=0.4` and also checks that the chamfer distance value is 0.04 cm.
  - New `test_chamfer_clearance`:
    - Planning h5 with `chamfer_mm=0.5` gives `['Hole 1 on Plate. The 0.50 mm chamfer on the Ø4.00 seat reaches a nearby edge at the opening.']` as obstacles.
    - With `chamfer_mm=0.4` the plan can apply.
  - New `test_chamfer_failure`:
    - Plan h5 with `chamfer_mm=0.4`, then use `dataclasses.replace` to set the seat's chamfer to 1.0.
    - `cut_seats` raises `SeatError` with `'Hole 1 on Plate. The chamfer could not be cut at the seat opening. Make it smaller or turn it off.'`.
  - New `test_preview_chamfer`:
    - h1 with `chamfer=0.4` draws one root group of 2 unselectable bodies.
    - Boxes: a cone at (7.6, 12.4, 7.6, 12.4, 17.6, 18) and a cylinder at (8, 12, 8, 12, 11.3, 17.6), ±0.05.
  - Add the new cases to the `test_cuts` tuple.

- [ ] **Step 2: Write the failing end-to-end steps.**
  - `preview_bodies()` sums `group.count` over the root groups.
  - `STEP_PREVIEWS` counts bodies instead of groups: `preselected` 4, `voron` 0, `standard` 4, `no_chamfer` 2, `chamfer` 4.
  - At `preselected`, also check that `chamfer` is on and that `chamfer_size` is 0.04 cm.
  - After `standard`, set `chamfer.value = False` and go to `no_chamfer`. That step also checks `not chamfer_size.isEnabled` and that the summary has no `chamfer`.
  - Then set `chamfer.value = True` and go to `chamfer`. That step checks `chamfer_size.isEnabled` and then presses OK.
  - `EXPECTED_NAMES` gains `SolidInserts · Chamfer Insert M3 × 5.7` after the M3 seat and `SolidInserts · Chamfer Insert M4 × 8.1` after the M4 seat. `EXPECTED_REMOVED_MM3 = 157.263`.

- [ ] **Step 3: [FUSION — Erik runs] RED.** Erik runs the integration test, then reloads the add-in and runs the command test.
  Expected:
  - The integration test fails the new chamfer checks. `test_chamfer_failure` reports that nothing was raised. The other cases pass.
  - The command test fails at `preselected`, because there is no `chamfer` input and there are 2 bodies, not 4.

- [ ] **Step 4: Implement the chamfer cut in `cuts.py`.**
  - The mouth edge is the circular edge of `feature.sideFaces` whose centre is within `TOLERANCE_MM` of `opening.center`. Use `circle_of`. Both are in component space.
  - Make the chamfer with `chamferFeatures.createInput2()` and `addEqualDistanceChamferEdgeSet(edges, ValueInput.createByString(f'{seat.chamfer} mm'), False)`. Name it `SEAT_NAME_PREFIX + message('chamfer_name', name=seat.name)`.
  - Raise `SeatError(message('chamfer_failed'))` in three cases: no single mouth edge, `add` raising `RuntimeError`, or `add` returning `None`.
  - Add `'chamfer_mm': seat.chamfer` to the seat attribute JSON.

- [ ] **Step 5: Implement the chamfer preview in `preview.py`.**
  - When `seat.chamfer` is set, draw a cone first: radius `mouth_diameter / 2` at the opening down to `diameter / 2` at depth `chamfer`.
  - Then draw a cylinder from depth `chamfer` to the floor.
  - Both bodies go in the seat's one group, each with the show-through colour and `isSelectable = False`.

- [ ] **Step 6: Implement the dialog in `command.py`.**
  - `add_inputs` adds, below compensation:
    - `addBoolValueInput('chamfer', …, True, '', True)`
    - `addFloatSpinnerCommandInput('chamfer_size', …, 'mm', CHAMFER_MIN_MM / MM_PER_CM, CHAMFER_MAX_MM / MM_PER_CM, 0.05, 0.4 / MM_PER_CM)`
    - Both get tooltips. The 0.05 step and the 0.4 default are module constants `CHAMFER_STEP_MM` and `CHAMFER_DEFAULT_MM`.
  - `current_plan` passes `chamfer_mm=round_mm(size.value * MM_PER_CM)` when the box is checked, and `None` otherwise.
  - `InputChangedHandler` sets `chamfer_size.isEnabled` from the checkbox when the `chamfer` input changes, before `refresh_plan`.

- [ ] **Step 7: Update the docs.**
  - User guide:
    - A **Chamfer top edge** paragraph under the settings section.
    - Step 3 of "Cut the seats" names the chamfer settings.
    - "Check and undo" names the `SolidInserts · Chamfer …` feature and its editable distance.
    - Troubleshooting: the chamfer reaching an edge or another seat, and the chamfer that could not be cut.
  - README: the feature summary and settings lines mention the chamfer.

- [ ] **Step 8: Run the unit tests.** Expected: all pass. Task 2 changes no pure module, so this guards Task 1.

- [ ] **Step 9: [FUSION — Erik runs] GREEN.** Erik runs the integration test, then reloads the add-in and runs the command test.
  Expected: both report `0 failed`.

- [ ] **Step 10: Commit.** Message: `Chamfer each seat's top edge, with a dialog option on by default`.
