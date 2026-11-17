# Clearance Measurement Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop "The seat reaches a nearby edge" from firing when a straight edge only comes near the hole if extended past its end.

**Architecture:** `openings.clearance_mm` measures from the rim centre point to each edge of the entrance face. Fusion measures a point against a straight edge as its unbounded line, so it uses the wrong distance. The fix measures from the rim edge itself to each edge, which is a bounded BRep-to-BRep measure, and adds the rim radius.

**Tech Stack:** Fusion add-in API (Python 3.14), in-Fusion test scripts that Erik runs, stdlib `unittest`.

**Spec:** Erik's bug report and approval in chat on 2026-11-17.

- **The report:** on `controlbox_lower` (in occurrence `Control Box:1`), a Ø3.2 hole with a VORON Ø4.6 seat was refused with "The Ø4.60 seat reaches a nearby edge at the opening". Its nearest real edge is 5.106 mm from the hole centre.
- **The probe:** Claude's probe found the pocket's left side edge, at x = 262.606 and running from y = −17.566 to 46.906. `measureMinimumDistance(centre point, edge)` gave 2.000 mm for it, the distance to the line extended past its end. The real distance is 5.500 mm.
- **The confirmed fix:** a second probe compared rim-edge-to-edge + rim radius with a distance Claude computed exactly from each edge's own geometry. They matched to 0.000000 mm on all 24 edges (lines, arcs, circles).
- **Approval:** Erik approved "measure from the rim edge to each face edge and add the rim radius", with a fixture part reproducing the case RED first.

## Why rim-to-edge + radius is exact

Every other edge of the flat entrance face lies in that plane, outside the hole's disc. For any point P there, the distance to the rim circle is |P − centre| − r. The minimum over an edge is therefore (minimum distance from the centre to the edge) − r.

## Global Constraints

- Fusion API lengths are centimetres; `MM_PER_CM` converts. Every code file starts with two `# ABOUTME: ` lines. Names and comments contain no time references. Keep existing comments unless they become false.
- Unit test command (repo root): `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`. Its output must be pristine.
- In-Fusion tests: `tests/fusion/SolidInsertsIntegrationTest` loads the add-in package from the repo. `tests/fusion/SolidInsertsCommandTest` drives the running add-in, so Erik reloads it first with Stop and Run. Both end with `==== N passed, M failed ====`.

## Ground Rules For The Executing Agent

1. **Commit at the commit step.** Erik granted standing approval for this plan ("Yes, plan and run it", inline execution with a Codex review). Record it in the ledger.
2. **Claude cannot run Fusion.** At each **[FUSION — Erik runs]** step, stop and wait for Erik to paste the Text Commands output.

## Review Focus

1. **A part in a component occurrence:** proxy edges, as in Erik's assembly. *(The fixture part is in a component.)*
2. **A neighbouring hole's rim (circle to circle):** h6 has clearance 2.0 to h7. *(Existing `h6 clearance` check.)*
3. **Straight face edges that run past the hole:** h5 has clearance 2.5 to the plate edge. *(Existing `h5 clearance` check.)*
4. **Reading speed:** the 36-rim grid must still read in under 5 s with edge-to-edge measures. *(Existing grid check.)*
5. **Arc edges:** Erik's probe covered pad arcs in the real part; the fixture has no arc edge. *(Covered by the probe, not by a test.)*

---

### Task 1: Measure clearance from the rim edge

**Files:**
- Modify: `SolidInserts/openings.py` (`clearance_mm`)
- Test: `tests/fusion/support.py`, `tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py`

**Interfaces:**
- `clearance_mm(rim)` keeps its signature and its millimetre result.
- New fixture helper `pocket(body, x0, y0, x1, y1, top_z, depth)` in `support.py`: cuts a rectangular blind pocket `depth` mm deep, straight down from `top_z`, the way `hole` cuts a circle.

- [ ] **Step 1: Build the reproduction**

In `support.py`, add `pocket` next to `hole`.

In `build_fixture`, after the bracket, add a component part:
- **The occurrence:** `pocket_part = root.occurrences.addNewComponent(place(130, 0, 0))`. Name its component `PocketPart`.
- **The body:** `box(component, 0, 0, 0, 40, 30, 10, 'PocketBlock')`.
- **The pocket:** `pocket(body, 15, 10, 35, 25, 10, 3)`.
- **The hole:** `hole(body, 13, 5, 10, 3, 7)`.
- **Fixture entries:** `fixture.bodies['PocketBlock'] = pocket_part.bRepBodies.item(0)` and `fixture.rims['pocket'] = rim(pocket_part.bRepBodies.item(0), (143, 5, 10), 3)`.
- **A comment** saying what it reproduces: the pocket's left side, extended, passes 2 mm from the hole, but the nearest real edge is the block's front edge, 5 mm away.

In `SolidInsertsIntegrationTest.py`:
- In `test_openings`, add `('pocket', 5.0)` to the clearance list.
- In `test_single_seats`, add the case `('pocket', 'PocketBlock', None, 36.835, 3.3)`. That's a Standard M3 seat, Ø4 × 6.7, in the Ø3 × 7 blind hole: the same volume as h1. Its floor is at z = 10 − 6.7.

- [ ] **Step 2: [FUSION — Erik runs] the integration test, RED**

Erik runs `SolidInsertsIntegrationTest`.
Expected: `==== 70 passed, 4 failed ====`. The four failures are all the pocket's:
- `pocket clearance 5.0 -> 2.0…`
- "seat plan can apply", listing `Hole 1 on PocketBlock. The Ø4.00 seat reaches a nearby edge at the opening.`
- `pocket removes 0.000 mm3`
- `pocket seat floor at z = 3.3 mm`

If the clearance reads 5.0 instead, the fixture does not reproduce the report. In that case, stop and investigate before changing code.

- [ ] **Step 3: Implement**

In `clearance_mm`:
- Replace `measure.measureMinimumDistance(center, edge)` with `measure.measureMinimumDistance(rim, edge)`, converted to mm, plus the rim radius in mm. The radius comes from the rim's `Circle3D`.
- Keep the wall-edge skip and the `clearance_unknown` errors.
- Extend the docstring: each edge is measured from the rim itself and the radius added, which is exact for edges of the face around the hole, because Fusion measures a point against a straight edge as if the edge ran on past its ends.
- Keep the existing sentence about native edges of non-root components.

- [ ] **Step 4: Run the unit tests**

Run: `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`
Expected: OK, 68 tests, with no other output.

- [ ] **Step 5: [FUSION — Erik runs] both Fusion tests, GREEN**

Erik reloads the add-in (Stop, then Run), then runs `SolidInsertsIntegrationTest` and `SolidInsertsCommandTest`.
Expected: integration `==== 74 passed, 0 failed ====`; command test `==== 18 passed, 0 failed ====`.

- [ ] **Step 6: Commit**

```bash
git add SolidInserts/openings.py tests/fusion/support.py tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py
git commit -m "Measure seat clearance from the rim edge so straight edges count only up to their ends"
```
