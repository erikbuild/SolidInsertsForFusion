# SolidInserts for Fusion Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Port the SolidInserts SolidCraft plugin (Rust/WASM, in this repo) to a Python Autodesk Fusion add-in that cuts CNC Kitchen heat-set insert seats at selected hole rims, with a live preview in Fusion's command dialog.

**Architecture:** Pure-Python modules (`catalog`, `geometry`, `seats`, `messages`) hold every decision and are unit-tested with `unittest`, without Fusion. Two adapter modules read hole openings from the model (`openings`) and cut seats (`cuts`). They are verified by in-Fusion scripts that build real fixture geometry. A command module wires the dialog (selection, dropdowns, spinner, summary, preview) to the adapters.

**Tech Stack:** Fusion add-in API (Python 3.14, `adsk.core`/`adsk.fusion`), stdlib `unittest`, in-Fusion test scripts run by Erik.

**Spec:** No separate spec. Erik asked to skip design questions ("Just do it"), so the decisions below are Claude's calls for Erik to check while reviewing. The behaviour reference is the Rust source in `src/` (`lib.rs`, `catalog.rs`, `geometry.rs`) and `docs/user-guide.md`.

## Decisions (Claude's calls; Erik to confirm)

1. **Layout:** The add-in lives in the `SolidInserts/` subfolder (`SolidInserts/SolidInserts.py` + `SolidInserts/SolidInserts.manifest`). You install it by copying or linking that folder. Tests, docs and plans stay outside it.
2. **Placement:** One button, **Insert Seats**, in **Solid › Create**. `config.json` keeps Erik's usual `use_custom_panel` / `panel_id` / `panel_name` switch, shipped with `false`.
3. **Behaviour parity with 1.1.0:** The catalog values, Automatic sizing (±0.05 mm), depth (insert length + 1 mm), compensation (−1 to +1 mm in 0.01 mm steps), and all of these checks carry over: seat wider than hole, wall at opening, bore depth, overlap, removed volume, floor, existing seat.
4. **Dropped SolidCraft workarounds:** No 24-rim cap (it came from the 256-call budget) and no timeline-marker restriction. Only circular **edges** can be picked; cylindrical faces cannot. Preview, the single undo and the dialog come from Fusion itself, so the desktop patch is gone.
5. **Design history is required.** A direct-modeling design gets a message. The sketches and cuts must stay editable in the timeline.
6. **Components:** A rim picked in an occurrence is cut into its component, so every instance gets the seat. Linked (external) components are refused.
7. **Existing-seat detection** uses an attribute (`SolidInserts`/`seat`) on each cut feature rather than its name, so renaming the feature does not break it.
8. **English only** for the UI and docs, with decimal points in labels (`M2.5 × 0.45`, `Ø4.00`). All copy lives in `messages.py` so translations can be added later. The eight translated READMEs and the Italian guide describe SolidCraft. They are removed in Task 9, which **needs Erik's explicit OK**.
9. **Version 1.0.0**, manifest author "Erik Reynolds (erikbuild)". `LICENSE` stays unchanged. `NOTICE.md` credits the original SolidInserts (NoOneExceptEnderk, MIT) and CNC Kitchen's dimension sheet.
10. **Not built (YAGNI):** insert illustrations in the dialog, a ZIP packaging script, translations, remembering the last-used settings, and timeline grouping.

## Global Constraints

- Internal Fusion lengths are **centimetres**. Every pure module works in **millimetres**, and conversion happens only inside `openings.py` / `cuts.py` (`mm = cm * 10`, `mm³ = cm³ * 1000`, `mm² = cm² * 100`).
- Pure modules (`catalog`, `geometry`, `seats`, `messages`) must **never import `adsk`**. They must import under plain CPython ≥ 3.12 and use relative imports (`from .catalog import …`).
- Every new code file starts with two `# ABOUTME: ` lines.
- `TOLERANCE_MM = 0.01`, `AUTO_TOLERANCE_MM = 0.05`, parallel test `abs(dot) >= 0.99999`, and volume tolerance `max(0.005, expected * 0.0005)` mm³ are copied from `geometry.rs`.
- Command id `erikbuild_SolidInserts_insertSeats`. Attribute group `SolidInserts`, attribute name `seat`. Feature name `SolidInserts · Insert <product>`, sketch name `Profile Insert <product>`.
- Unit test command (repo root): `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit -v`. The output must be pristine, with no warnings.
- In-Fusion scripts live in `tests/fusion/<Name>/<Name>.py` + `<Name>.manifest` (`"type": "script"`). They log with `app.log('[SolidInserts…] PASS|FAIL label')` and finish with a `==== N passed, M failed ====` line.

## Ground Rules For The Executing Agent

1. **Never run `git commit`.** Each "Checkpoint" step means: stop, summarise, suggest a commit message, and wait for Erik.
2. **You cannot run Fusion.** Steps marked **[FUSION — Erik runs]** need Erik to run the script from **Utilities › Add-Ins › Scripts** (link the folder with **+**) and paste the Text Commands output back. Stop and wait at each one.
3. **Spike findings gate Tasks 5–7.** If a finding in Task 1 contradicts an assumption below, STOP and revise with Erik. Do not improvise around it.
4. The Rust code stays in the repo as reference until Task 9.

## Review Focus

1. **Same component in two occurrences, rim picked in both:** one seat, and both instances show it. *(Task 5 + Task 6 integration: Bracket fixture.)*
2. **Design display units set to inches:** the seat is still Ø4.00 × 6.70 mm, because dimension expressions carry explicit `mm`. *(Task 6 integration.)*
3. **A straight edge, chamfered rim, or boss rim picked:** a per-hole message in the summary, with no exception and no OK button. *(Task 5 integration.)*
4. **A second run on an already-seated hole:** the "already created" message. *(Task 5 integration.)*
5. **Many rims (36) on one face:** reading them stays under 5 s. *(Task 5 integration timing. The Task 7 selection cache keeps settings changes from re-reading them; Erik's hand check in Task 7 Step 5 covers how responsive that feels.)*

---

### Task 1: Scaffolding and Fusion API spike

**Files:**
- Modify: `.gitignore` (add `.DS_Store`)
- Create: `tests/fusion/support.py`
- Create: `tests/fusion/SolidInsertsSpike/SolidInsertsSpike.py`, `.manifest`
- Create: `tests/fusion/SolidInsertsCommandSpike/SolidInsertsCommandSpike.py`, `.manifest`
- Modify: this plan (record findings)

**Interfaces:**
- Produces, in `tests/fusion/support.py`:
  - `check(condition, label) -> None` and `report(app, tag) -> None`, the same shape as FusionDocumentationToolkit's `ExplodeIntegrationTest.py`.
  - `new_design(app) -> adsk.fusion.Design`, which makes a new parametric design document.
  - `box(component, x0, y0, z0, x1, y1, z1, name) -> BRepBody` (mm in, cm to API).
  - `hole(body, x, y, top_z, diameter, depth=None) -> None`, which cuts a flat-bottomed blind hole (or a through hole when `depth` is None) straight down from `top_z`.
  - `rim(body, center_mm, diameter_mm) -> BRepEdge`, which finds the circular edge with that centre and diameter.
  - `load_addin_package() -> module`, which imports `SolidInserts/` fresh under the package name `solidinserts_under_test`. This keeps the running add-in's modules from shadowing the code under test:

```python
def load_addin_package(name="solidinserts_under_test"):
    for key in [k for k in sys.modules if k == name or k.startswith(name + ".")]:
        del sys.modules[key]
    spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
    spec.submodule_search_locations = [ADDIN_DIR]
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    return package  # then importlib.import_module(name + ".openings")
```

Each script inserts `tests/fusion` on `sys.path` and calls `importlib.reload(support)`, because Fusion keeps one interpreter alive between script runs.

- [ ] **Step 1: Write `SolidInsertsSpike.py`.** It builds a 42 × 30 × 18 mm plate with Ø3 holes A at (8, 8) and B at (20, 8), each 7 mm blind. It also builds a Bracket component (20 × 10 × 10, Ø3 through hole at (10, 5)) placed twice, at (0, 50, 0) and (30, 50, 0). It logs one `FINDING n` line per check:
  1. `sketches.addWithoutEdges(topFace)` + `project2([rimA], True)` returns exactly one `SketchCircle`. Setting `isConstruction = True` works. `sketchCircles.addByCenterRadius(projected.centerSketchPoint, 0.2)` plus `sketchDimensions.addDiameterDimension(...)` with `parameter.expression = '4 mm'` gives `circle.isFullyConstrained == True`, and `sketch.profiles.count == 1`.
  2. Log `dot(sketch.xDirection × sketch.yDirection, outward)`, where `outward` is `topFace.evaluator.getNormalAtPoint(topFace.pointOnFace)`. Then cut 6.7 mm with `setOneSideExtent(DistanceExtentDefinition, NegativeExtentDirection)` when the dot is positive (Positive otherwise) and `participantBodies = [plate]`, and log the volume change.
  3. Log the removed volume minus π/4·(4²−3²)·6.7 = 36.835 mm³. Also log the floor area of hole B minus π·1.5² mm². Both should be < 0.001.
  4. Take hole B's rim `entityToken` before cutting A. After the cut, log the old edge's `isValid`, the length of `findEntityByToken` and the entity type.
  5. `feature.name = 'SolidInserts · Insert M3 × 5.7'` and `sketch.name = 'Profile Insert M3 × 5.7'`. Log whether both read back unchanged.
  6. Bracket: `proxyEdge.nativeObject` gives a native rim. Sketch with `nativeComponent.sketches.addWithoutEdges(nativeFace)` and cut with `nativeComponent.features.extrudeFeatures`. Log success, the volume change of **both** occurrence bodies, and `measureMinimumDistance(Point3D(1.0, 0.5, 1.0), nativeOuterEdge).value` (component-space centre; expect 0.5 cm).
  7. Log `feature.bodies.count` and `feature.bodies.item(0) == plate`. Log `feature.endFaces` (count, planar, depth from the rim plane). Log `endFaces` for a deliberate 20 mm break-through cut on the Bracket (None or 0?).
  8. Add an attribute with `feature.attributes.add('SolidInserts', 'seat', '{}')`. Log whether `design.findAttributes('SolidInserts', 'seat')[0].parent == feature`, and whether `feature.sideFaces` contains the face adjacent to the new Ø4 rim (`==` comparison).
- [ ] **Step 2: Write `SolidInsertsCommandSpike.py`.** It is a script that sets `adsk.autoTerminate(False)` and registers a throwaway command `SolidInsertsSpikeCmd`. The command has a `CircularEdges` selection input, a read-only text box, and a checkbox called "Fail in execute". `executePreview` cuts one Ø4 × 3 mm seat on the first selected rim, writes `preview ran <n>` into the text box, and sets `isValidResult = not failCheckbox`. `execute` cuts the same seat, then sets `executeFailed = True` when the checkbox is on. The script logs:
  1. After preselecting rim A with `ui.activeSelections.add(edge)` and calling `cmdDef.execute()`: the selection input count in `activate`, whether `inputChanged` fired for the preselection, and whether `executePreview` fired.
  2. **Erik observes:** does the text box show `preview ran 1`?
  3. After OK with the checkbox off: the feature name and attribute exist (logged from a `commandTerminated` handler).
  4. With the checkbox on: the timeline count before and after OK. Does a failed execute roll back the partial cut?
  5. A second `commandCreated` handler added by the script that calls `args.command.doExecute(True)` from the command's `activate` event when the flag `DRIVE = True` is set: does execute run, and does the dialog close?
  6. After one driven run, `ui.commandDefinitions.itemById('UndoCommand').execute()`: does one call remove the sketch and the cut together? Log the timeline counts.
  It removes its command definition on `stop` and logs `==== spike done ====`.
- [ ] **Step 3: [FUSION — Erik runs]** both spikes and pastes the output.
- [ ] **Step 4: Record the findings** under a `## Spike Findings` heading at the end of this plan. If any finding contradicts Tasks 5–7, stop and revise with Erik.
- [ ] **Step 5: Checkpoint.** Ask Erik to commit. Suggested message: `Add Fusion API spikes for the SolidInserts port`.

---

### Task 2: Insert catalog and user-facing copy

**Files:**
- Create: `SolidInserts/messages.py`, `SolidInserts/catalog.py`
- Test: `tests/unit/test_catalog.py`, `tests/unit/test_messages.py`

**Interfaces:**
- Produces in `messages.py`: `class SeatError(Exception)`, raised with finished copy, and `message(key: str, **values) -> str`. It raises `KeyError` for an unknown key. Templates use `str.format` with exactly this copy:

| key | template |
| --- | --- |
| `select_rims` | `Select the circular rim of each hole in the 3D view.` |
| `needs_history` | `SolidInserts needs design history. Turn on Capture Design History and try again.` |
| `not_entrance` | `Select a circular rim on a flat face, with a cylindrical wall and no chamfer.` |
| `linked_component` | `This body is in a linked component. Open its design to add seats.` |
| `existing_seat` | `SolidInserts already created this seat. Edit it in the timeline.` |
| `bore_depth_unknown` | `Could not measure the cylindrical depth of the hole.` |
| `clearance_unknown` | `Could not measure the edges around the opening.` |
| `hole_prefix` | `Hole {ordinal} on {body}. {reason}` |
| `choose_thread` | `Hole Ø{diameter:.2f} mm. Select the screw thread explicitly.` |
| `thread_unavailable` | `{thread} is not available in the CNC Kitchen {series} series.` |
| `compensation_range` | `Diameter compensation must be between −1 and +1 mm.` |
| `seat_not_wider` | `The Ø{seat:.2f} seat must be wider than the Ø{hole:.2f} mm hole.` |
| `seat_reaches_edge` | `The Ø{seat:.2f} seat reaches a nearby edge at the opening.` |
| `seat_too_deep` | `The seat needs {depth:.2f} mm of depth. The cylindrical wall ends at {bore:.2f} mm; choose a shorter insert.` |
| `thin_wall` | `The opening has {wall:.2f} mm of material to the nearest edge. The catalog specifies {catalog:.2f} mm.` |
| `seats_overlap` | `The seats for holes {first} and {second} overlap at the opening.` |
| `opening_changed` | `The hole opening changed after an earlier edit.` |
| `profile_unconstrained` | `The seat profile is not fully constrained.` |
| `cut_other_bodies` | `The cut changed other bodies besides this one.` |
| `cut_intersects` | `The seat intersects an edge, a cavity or another hole at the requested depth.` |
| `cut_no_floor` | `The seat has no floor at the requested depth. Check the thickness or use a shorter insert.` |
| `insert_name` | `Insert {product}` |
| `profile_name` | `Profile {name}` |
| `seat_line` | `Hole {ordinal} · {thread} · Ø{diameter:.2f} × {depth:.2f} mm` |
| `note_line` | `Note: {note}` |

- Produces in `catalog.py`:
  - `class Series(Enum)`: `STANDARD = "Standard"`, `SHORT = "Short Version"`, `VORON = "VORON M3 × 5 × 4"`, in that order.
  - `AUTOMATIC = "Automatic (nominal Ø)"`.
  - `@dataclass(frozen=True) class Thread: label: str; nominal_mm: float`.
  - `THREADS: tuple[Thread, ...]`, eight labels: `M2 × 0.40`, `M2.5 × 0.45`, `M3 × 0.50`, `M4 × 0.70`, `M5 × 0.80`, `M6 × 1.00`, `M8 × 1.25`, `M10 × 1.50`.
  - `THREAD_CHOICES: tuple[str, ...]` = `(AUTOMATIC, *labels)`.
  - `@dataclass(frozen=True) class Insert: thread: str; product_name: str; length_mm: float; bore_mm: float; wall_mm: float`, with property `depth_mm = length_mm + 1`.
  - `choose(series: Series, thread_label: str, hole_diameter_mm: float) -> Insert`, which raises `SeatError`.
  - The (L, D2, W) table is copied from `src/catalog.rs:112-124`. Product names: Standard `"M3 × 5.7"`, Short `"M3 × 3 (Short Version)"` (length formatted `:g`), Voron `"VORON M3 × 5 × 4"`.

- [ ] **Step 1: Write the failing tests.** In `test_messages.py`: `message('seat_line', ordinal=1, thread='M3 × 0.50', diameter=4, depth=6.7) == 'Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm'`, `message('hole_prefix', ordinal=2, body='Plate', reason='X.') == 'Hole 2 on Plate. X.'`, and `message('nope')` raises `KeyError`. In `test_catalog.py`, port `pilot_selects_the_thread_but_series_sets_the_seat`:
  - `choose(s, AUTOMATIC, 3.0 - 1e-12)` gives thread `'M3 × 0.50'` and `(bore, depth)` ≈ `(4.0, 6.7)` / `(4.0, 4.0)` / `(4.4, 5.0)` for STANDARD / SHORT / VORON.
  - `choose(STANDARD, AUTOMATIC, 2.55).thread == 'M2.5 × 0.45'`.
  - `choose(STANDARD, AUTOMATIC, 3.2)` raises `SeatError('Hole Ø3.20 mm. Select the screw thread explicitly.')`, and 4.5 also raises.
  - `choose(VORON, 'M4 × 0.70', 4.0)` raises with `'M4 × 0.70 is not available in the CNC Kitchen VORON M3 × 5 × 4 series.'`.
  - A table test over all 12 catalog rows.
  - Product names `'M3 × 5.7'`, `'M3 × 3 (Short Version)'`, `'VORON M3 × 5 × 4'`, `'M10 × 12.7'`.
  - `THREAD_CHOICES` equals the nine strings above in order.
- [ ] **Step 2: Run the tests.** Expected: errors with `ModuleNotFoundError: No module named 'SolidInserts.catalog'`.
- [ ] **Step 3: Implement** `messages.py` and `catalog.py`. The Automatic match is `abs(nominal - d) <= AUTO_TOLERANCE_MM + 1e-8`.
- [ ] **Step 4: Run the tests.** Expected: all pass, no warnings.
- [ ] **Step 5: Checkpoint.** Suggested message: `Port the CNC Kitchen insert catalog to Python`.

---

### Task 3: Hole geometry rules

**Files:**
- Create: `SolidInserts/geometry.py`
- Test: `tests/unit/test_geometry.py`

**Interfaces:**
- Produces:
  - `Vec3 = tuple[float, float, float]`; `TOLERANCE_MM = 0.01`.
  - `sub`, `dot`, `norm`, `cross`, `radial_distance(v, axis) -> float`; `round_mm(value) -> float` (3 decimals).
  - `@dataclass(frozen=True) class Circle: center: Vec3; axis: Vec3; radius: float`.
  - `@dataclass(frozen=True) class Cylinder: origin: Vec3; axis: Vec3; radius: float`.
  - `@dataclass(frozen=True) class PlanarFace: normal: Vec3; area_mm2: float`.
  - `@dataclass(frozen=True) class BoreEdge: circle: Circle; planar_neighbours: tuple[PlanarFace, ...]`.
  - `is_hole_entrance(rim: Circle, outward: Vec3, wall: Cylinder, wall_point: Vec3, wall_normal: Vec3) -> bool` is true when all of these hold: the wall axis is parallel to outward; the rim radius matches the wall radius within tolerance; the rim centre is on the wall axis within tolerance; the wall goes inward (`dot(wall_point − rim.center, outward) < −1e-5`); and the wall is concave (its normal points toward the axis).
  - `bore_end(rim: Circle, outward: Vec3, edges: Iterable[BoreEdge]) -> tuple[float, bool] | None` returns `(depth, can_deepen)` for the nearest edge that is coaxial, the same radius and deeper than `TOLERANCE_MM`. `can_deepen` means the edge has a planar neighbour facing outward (`dot > 0.99999`) whose area is within 0.001 mm² of π r².
  - `expected_cut_volume_mm3(seat_diameter, seat_depth, hole_diameter, bore_depth) -> float` (formula in `geometry.rs:638-640`).
  - `cut_volume_matches(removed_mm3, expected_mm3) -> bool`.
  - `cut_direction(sketch_x: Vec3, sketch_y: Vec3, inward: Vec3) -> int` (+1 or −1).
  - `is_floor(point, normal, center, outward, depth) -> bool` (normal parallel to outward, and depth within `TOLERANCE_MM`).

- [ ] **Step 1: Write the failing tests** with these exact cases:
  - `is_hole_entrance`:
    - True for a top rim `Circle((8,8,18),(0,0,1),1.5)` with outward `(0,0,1)`, wall `Cylinder((8,8,0),(0,0,1),1.5)`, point `(9.5,8,15)` and normal `(-1,0,0)`.
    - True for a bottom rim at `(23,9,0)` (radius 2, outward `(0,0,-1)`, wall point `(25,9,5)`, normal `(-1,0,0)`).
    - False for the boss rim (same as the top rim but normal `(1,0,0)`).
    - False for a blind-hole floor rim at `(8,8,11)` with the wall point above it.
    - False for a wall radius of 2.0, an axis of `(0,1,0)`, or a rim centre 0.1 off the axis.
  - `bore_end`:
    - Rim `(8,8,18)` r 1.5 with one edge at `(8,8,11)` and floor `PlanarFace((0,0,1), π·2.25)` gives `(7.0, True)`.
    - Through hole: rim `(23,9,18)` r 2 with an edge at `(23,9,0)`, axis `(0,0,-1)`, neighbour `PlanarFace((0,0,-1), 1200.0)` gives `(18.0, False)`.
    - An annular floor of area 5.0 gives `can_deepen` False.
    - With candidates at depths 12 and 7, the result is 7.
    - A different radius, an off-axis edge, or depth 0 gives `None`.
  - Volumes: `expected_cut_volume_mm3(4.0, 6.7, 3.0, 7.0) ≈ 36.835`, `(5.7, 9.1, 4.0, 18.0) ≈ 117.856`, `(4.0, 6.7, 3.0, 4.0) ≈ 55.920` (`places=3`).
  - `cut_volume_matches(36.853, 36.835)` is True and `(36.816, 36.835)` is False.
  - `cut_direction((1,0,0),(0,1,0),(0,0,-1)) == -1` and `… (0,0,1)) == 1`.
  - `is_floor((8,8,11.3),(0,0,1),(8,8,18),(0,0,1),6.7)` is True. It is False at depth 6.0 and with normal `(0,0,-1)`.
- [ ] **Step 2: Run the tests.** Expected: `ModuleNotFoundError`.
- [ ] **Step 3: Implement `geometry.py`.**
- [ ] **Step 4: Run the tests.** Expected: all pass.
- [ ] **Step 5: Checkpoint.** Suggested message: `Port the hole entrance, bore and cut checks`.

---

### Task 4: Seat planning

**Files:**
- Create: `SolidInserts/seats.py`
- Test: `tests/unit/test_seats.py`

**Interfaces:**
- Consumes: `catalog.choose`, `Series`, `geometry.*`, `messages.message` / `SeatError`.
- Produces:
  - `SEAT_ATTRIBUTE_GROUP = "SolidInserts"`, `SEAT_ATTRIBUTE_NAME = "seat"`, `SEAT_NAME_PREFIX = "SolidInserts · "`.
  - `@dataclass(frozen=True) class Opening:` with fields `ordinal: int` (1-based selection position), `body_key: str`, `body_name: str`, `plane_key: str`, `center: Vec3`, `outward: Vec3`, `diameter: float`, `bore_depth: float`, `can_deepen: bool`, `clearance: float`, and `rim_token: str = field(default="", compare=False)`.
  - `same_opening(a, b) -> bool`, which needs the same body, the same plane and centres within tolerance.
  - `coplanar_distance(a, b) -> float | None` (`geometry.rs:153-159`).
  - `@dataclass(frozen=True) class Seat: opening: Opening; insert: Insert; diameter: float; depth: float; wall: float; name: str`, where `name = message('insert_name', product=…)`.
  - `@dataclass(frozen=True) class SeatPlan: seats: tuple[Seat, ...]; obstacles: tuple[str, ...]; notes: tuple[str, ...]`, with property `can_apply = bool(seats) and not obstacles`.
  - `plan_seats(openings: Sequence[Opening], series: Series, thread_label: str, compensation_mm: float, rim_errors: Sequence[str] = ()) -> SeatPlan`. `rim_errors` come first in `obstacles`. Duplicates are dropped and the first ordinal is kept. A catalog `SeatError` becomes a `hole_prefix` obstacle. Seat issues and notes follow `lib.rs:142-231`, with `hole_prefix` on every per-hole message. Overlap uses `seats_overlap` without a prefix. With no openings and no errors, the only obstacle is `select_rims`.
  - `summary_lines(plan: SeatPlan) -> list[str]` returns the `seat_line` entries, then the obstacles, then a `note_line` for each note.

- [ ] **Step 1: Write the failing tests.** Use a helper `opening(ordinal=1, body='Plate', plane='top', center=(10,10,18), outward=(0,0,1), diameter=3.0, bore_depth=7.0, can_deepen=True, clearance=10.0)`:
  - M3 (Ø3, bore 7, clearance 10) and M4 (Ø4 at `(30,10,18)`, bore 18, `can_deepen=False`) with Standard, Automatic and 0 give seats `[('M3 × 0.50', 4.0, 6.7, 'Insert M3 × 5.7', wall 8.0), ('M4 × 0.70', 5.7, 9.1, 'Insert M4 × 8.1', wall 7.15)]`, no obstacles or notes, and `can_apply` is True.
  - Compensation 0.1 gives diameter 4.1 and depth 6.7. Compensation 1.5 gives the obstacle `'Diameter compensation must be between −1 and +1 mm.'`.
  - The same opening twice gives one seat.
  - Ø3.2 with Automatic gives `'Hole 1 on Plate. Hole Ø3.20 mm. Select the screw thread explicitly.'`. With `'M3 × 0.50'` it gives a Ø4.0 seat.
  - Ø4.0 with manual M3 gives `'Hole 1 on Plate. The Ø4.00 seat must be wider than the Ø4.00 mm hole.'`.
  - Clearance 2.0 gives `'Hole 1 on Plate. The Ø4.00 seat reaches a nearby edge at the opening.'`.
  - Clearance 2.5 gives the note `'Hole 1 on Plate. The opening has 0.50 mm of material to the nearest edge. The catalog specifies 1.60 mm.'`, and `can_apply` stays True.
  - Bore 5 with `can_deepen=False` gives `'Hole 1 on Plate. The seat needs 6.70 mm of depth. The cylindrical wall ends at 5.00 mm; choose a shorter insert.'`. The Short series gives no obstacle. Bore 4 with `can_deepen=True` gives no obstacle.
  - Centres `(40,20,18)` and `(43.5,20,18)` on the same body and plane give `'The seats for holes 1 and 2 overlap at the opening.'`. Different bodies, or outward `(0,0,-1)` on the second, give no overlap.
  - `rim_errors=('Hole 3 on Plate. X',)` comes first in the obstacles. An empty input gives the `select_rims` obstacle.
  - `summary_lines` for the first case gives `['Hole 1 · M3 × 0.50 · Ø4.00 × 6.70 mm', 'Hole 2 · M4 × 0.70 · Ø5.70 × 9.10 mm']`.
- [ ] **Step 2: Run the tests.** Expected: `ModuleNotFoundError`.
- [ ] **Step 3: Implement `seats.py`.**
- [ ] **Step 4: Run the tests.** Expected: all pass.
- [ ] **Step 5: Checkpoint.** Suggested message: `Port seat planning and batch checks`.

---

### Task 5: Reading hole openings from the model

**Files:**
- Create: `SolidInserts/openings.py`
- Modify: `tests/fusion/support.py` (add `build_fixture`)
- Create: `tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py`, `.manifest`

**Interfaces:**
- Consumes: `geometry.*`, `seats.Opening`, `seats.SEAT_ATTRIBUTE_*`, `messages.*`.
- Produces: `read_openings(design: adsk.fusion.Design, rims: Sequence[adsk.fusion.BRepEdge]) -> tuple[list[Opening], list[str]]`. Each rim gives either an `Opening` or one `hole_prefix`-formatted error string. It never raises for bad geometry. It works on `edge.nativeObject` when the edge is a proxy. `body_key` and `plane_key` are `"body<i>"` / `"face<i>"`, assigned by comparing API objects with `==`; entity tokens are never compared. `rim_token` is the native rim's `entityToken`. A non-parametric design returns `([], [message('needs_history')])`. A rim whose occurrence path contains a referenced (linked) component gives `linked_component`. Missing bore-end or clearance measurements give `bore_depth_unknown` / `clearance_unknown`. Checks run in this order: entrance (`geometry.is_hole_entrance`), linked component, existing seat, bore end, clearance. Clearance is the minimum `measureMinimumDistance(centerPoint, edge)` over the entrance face's edges, excluding edges of the wall face. The existing-seat check matches the wall face (`==`) against `sideFaces` of features found with `design.findAttributes(SEAT_ATTRIBUTE_GROUP, SEAT_ATTRIBUTE_NAME)`.
- Produces in `support.py`: `build_fixture(design) -> dict[str, BRepEdge]`, which builds these bodies (mm) and returns named rims.
  - **Plate** (0..60, 0..40, 0..18), every hole cut from the top:
    - `h1` Ø3 × 7 blind at (10, 10).
    - `h2` Ø4 through at (30, 10), plus `h2_bottom`.
    - `h3` Ø3.2 through at (10, 30).
    - `h4` Ø3 through at (25, 30) with a 0.5 mm top chamfer. The rim is the chamfer's outer Ø4 edge.
    - `h5` Ø3 through at (2.5, 20).
    - `h6` and `h7`, Ø3 through at (40, 20) and (43.5, 20).
    - `h8` Ø3 × 4 blind at (50, 10).
    - `boss`, a Ø3 × 3 boss joined at (50, 30); the rim is its top edge.
    - `straight`, the plate's top edge along y = 0.
  - **ThinPlate** (70..90, 0..20, 0..5): `thin`, Ø3 through at (80, 10).
  - **CavityBlock** (100..120, 0..20, 0..18): `cavity`, Ø3 × 12 blind at (110, 10), plus a Ø2 bore along y at x = 112.8, z = 14.
  - **Bracket** component (0..20, 0..10, 0..10) with a Ø3 through hole at (10, 5), placed at (0, 60, 0) and (30, 60, 0): rims `bracket_a` and `bracket_b`, as proxies.
  - **Perforated** (0..100, 100..200, 0..10): a 6 × 6 grid of Ø3 through holes at 15 mm pitch, starting at (12.5, 112.5). Returns `grid` as a list of rims.
  - Add `support.py` builders as the fixture needs them (boss, chamfer, side bore, component placement).

- [ ] **Step 1: Write the integration test (openings section).** Call `read_openings` and check:
  - `h1`: centre (10, 10, 18), outward (0, 0, 1), Ø3.0, bore 7.0, `can_deepen` True, clearance 10.0, all to 1e-6.
  - `h2`: bore 18.0 and `can_deepen` False.
  - `h2_bottom`: centre z = 0 and outward (0, 0, −1).
  - `h5`: clearance 2.5.
  - `h6`: clearance 2.0.
  - `h8`: bore 4.0 and `can_deepen` True.
  - `thin`: bore 5.0.
  - `bracket_a` and `bracket_b` give two `Opening`s with equal `body_key`, centres (10, 5, 10), clearance 5.0, and `same_opening` True.
  - `h4`, `boss` and `straight` each give exactly the error `'Hole n on Plate. Select a circular rim on a flat face, with a cylindrical wall and no chamfer.'`.
  - `grid` gives 36 openings in under 5.0 s; log the elapsed time.
  - After a temporary `design.designType = DirectDesignType` on a separate new document, the result is `([], ['SolidInserts needs design history. …'])`.
- [ ] **Step 2: [FUSION — Erik runs].** Expected: FAIL at import (`No module named 'solidinserts_under_test.openings'`).
- [ ] **Step 3: Implement `openings.py`.** It uses the spike findings for normals (`evaluator.getNormalAtPoint`), proxies and measurement space.
- [ ] **Step 4: [FUSION — Erik runs].** Expected: `==== N passed, 0 failed ====`.
- [ ] **Step 5: Checkpoint.** Suggested message: `Read hole openings from Fusion geometry`.

---

### Task 6: Cutting seats

**Files:**
- Create: `SolidInserts/cuts.py`
- Modify: `tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py` (add a cuts section)

**Interfaces:**
- Consumes: `seats.SeatPlan`/`Seat`/`SEAT_*`, `geometry.cut_direction`, `expected_cut_volume_mm3`, `cut_volume_matches`, `is_floor`, `messages.*`.
- Produces: `cut_seats(design: adsk.fusion.Design, plan: SeatPlan) -> list[adsk.fusion.ExtrudeFeature]`, which raises `SeatError` with `hole_prefix` copy. For each seat it:
  1. Re-resolves the rim with `design.findEntityByToken(seat.opening.rim_token)`. Anything other than exactly one `BRepEdge` raises `opening_changed`.
  2. Creates `addWithoutEdges(entranceFace)` in the body's parent component, named `profile_name`.
  3. Projects the rim (linked) as construction and adds the seat circle on its centre point. It adds a diameter dimension with `expression = f"{seat.diameter} mm"`, and raises `profile_unconstrained` unless the circle is fully constrained.
  4. Cuts one side, `f"{seat.depth} mm"`, with direction from `cut_direction`, `participantBodies = [body]`, and name `SEAT_NAME_PREFIX + seat.name`.
  5. Adds attribute `SolidInserts`/`seat` with JSON `{"thread", "insert", "diameter_mm", "depth_mm"}`.
  6. Checks the result in this order: the feature touched only this body (`cut_other_bodies`), the removed volume matches (`cut_intersects`), and some end face `is_floor` (`cut_no_floor`).

- [ ] **Step 1: Add the cuts section to the integration test.** Each case uses a fresh `build_fixture` document:
  - `h1` + `h2` with Standard, Automatic and 0 make 2 features named `SolidInserts · Insert M3 × 5.7` and `SolidInserts · Insert M4 × 8.1`. The Plate volume drops by 36.835 + 117.856 mm³ (±0.02). Both sketches are fully constrained and named `Profile Insert …`. Each feature has the `seat` attribute.
  - Re-reading the `h1` seat's new Ø4 top rim gives `'Hole 1 on Plate. SolidInserts already created this seat. Edit it in the timeline.'`.
  - `h8` gives a 55.920 mm³ drop and a floor at depth 6.7.
  - `h2_bottom` cuts upward from z = 0 and drops 117.856 mm³.
  - `cavity` raises `'Hole 1 on CavityBlock. The seat intersects an edge, a cavity or another hole at the requested depth.'`.
  - `thin` with the Short series drops 21.991 mm³.
  - `bracket_a` drops 36.835 mm³ in **both** Bracket occurrence bodies, and the timeline grows by 2.
  - With `design.fusionUnitsManager.distanceDisplayUnits = InchDistanceUnits` set first, the `h1` seat's diameter dimension `parameter.value` is 0.4 (cm) and its depth is 0.67.
- [ ] **Step 2: [FUSION — Erik runs].** Expected: the cuts section FAILS at import of `cuts`, and the openings section still passes.
- [ ] **Step 3: Implement `cuts.py`.**
- [ ] **Step 4: [FUSION — Erik runs].** Expected: all pass.
- [ ] **Step 5: Checkpoint.** Suggested message: `Cut insert seats as editable sketches and extrusions`.

---

### Task 7: Insert Seats command and add-in entry

**Files:**
- Create: `SolidInserts/SolidInserts.py`, `SolidInserts/SolidInserts.manifest`, `SolidInserts/config.json`, `SolidInserts/command.py`
- Create: `SolidInserts/resources/16x16.png`, `32x32.png`, `64x64.png` (made with `sips -z N N assets/branding/solidinserts-icon.png --out …`)
- Create: `tests/fusion/SolidInsertsCommandTest/SolidInsertsCommandTest.py`, `.manifest`

**Interfaces:**
- Consumes: `openings.read_openings`, `seats.plan_seats`/`summary_lines`, `cuts.cut_seats`, `catalog.Series`/`THREAD_CHOICES`/`AUTOMATIC`.
- Produces:
  - In `command.py`: `CMD_ID = "erikbuild_SolidInserts_insertSeats"`, `create_definition(ui) -> adsk.core.CommandDefinition` (name `Insert Seats`, tooltip `Cut seats for heat-set threaded inserts at the rims of existing holes.`, icons from `resources/`), and `delete_definition(ui) -> None`, which deletes the definition, drops the handler references and clears the openings cache.
  - Dialog inputs (id, label, setup):
    - `holes`, `Holes`: `CircularEdges` filter, limits (1, 0).
    - `series`, `Type`: dropdown of `Series` values, Standard selected; tooltip `Short Version for M3, M4 and M5. VORON M3 × 5 × 4 for M3.`
    - `thread`, `Screw thread`: dropdown of `THREAD_CHOICES`, Automatic selected; tooltip `Automatic matches the nominal hole diameter within ±0.05 mm. For clearance holes, choose the screw size.`
    - `compensation`, `Diameter compensation`: float spinner `'mm'` with min −0.1, max 0.1 (cm), step 0.01 (mm) and initial 0; tooltip `Adjustment to the seat diameter. Use 0 for the catalog dimension.`
    - `summary`, `Seats`: read-only text box, 6 rows, showing the HTML-escaped `summary_lines` joined by `<br>`.
  - Openings are cached against the current selection list, compared element by element with `==`. Only a selection change calls `read_openings` again. Settings changes re-run `plan_seats` only.
  - Handlers: `inputChanged` (and `executePreview`, per spike finding 1/2) refreshes the summary. `validateInputs` sets `areInputsValid = plan.can_apply`. `executePreview` calls `cut_seats` and sets `isValidResult = True`; on a `SeatError` it shows the message in the summary. `execute` calls `cut_seats`; on a `SeatError` it sets `executeFailed`/`executeFailedMessage`, with cleanup per spike finding 4. Unexpected exceptions show `traceback.format_exc()` in a message box.
  - `SolidInserts.py`: `run(context)` / `stop(context)` place and remove the button. It follows FusionTidy's `get_or_create_custom_panel` logic, with default panel `SolidCreatePanel`, fallback `SolidScriptsAddinsPanel` and `isPromoted = True`.
  - Manifest: `{"autodeskProduct": "Fusion", "type": "addin", "id": "SolidInserts", "author": "Erik Reynolds (erikbuild)", "description": {"": "Cut seats for heat-set threaded inserts at the rims of existing holes."}, "version": "1.0.0", "runOnStartup": true, "supportedOS": "windows|mac"}`.
  - `config.json`: `{"use_custom_panel": false, "panel_id": "CustomPlugins_Panel", "panel_name": "ERIKBUILD"}`.

- [ ] **Step 1: Write the end-to-end test.** It needs the add-in to be running. It builds the fixture, preselects the `h1` and `h2` top rims, and drives the real command by `CMD_ID`, using the mechanism spike finding 5 proved. It asserts:
  - The timeline grows by 4, with names `Profile Insert M3 × 5.7`, `SolidInserts · Insert M3 × 5.7`, `Profile Insert M4 × 8.1`, `SolidInserts · Insert M4 × 8.1`.
  - The Plate volume drops by 154.691 mm³.
  - One Undo restores both the volume and the timeline count.
  **If finding 5 showed the command cannot be driven from a script, STOP.** Ask Erik for explicit authorisation to replace this automated test with the Step 5 manual checklist.
- [ ] **Step 2: [FUSION — Erik runs]** with the add-in installed but `command.py` missing. Expected: FAIL (command definition not found).
- [ ] **Step 3: Implement** `command.py`, `SolidInserts.py`, the manifest, `config.json` and the icons.
- [ ] **Step 4: [FUSION — Erik runs]** the end-to-end test. Expected: all pass.
- [ ] **Step 5: [FUSION — Erik checks by hand]**:
  - The button appears in Solid › Create.
  - With `h1` + `h2` selected, the preview shows both cuts and the summary lists both seats.
  - Changing Type to VORON shows the M4 obstacle, OK is disabled and the preview clears.
  - Cancel leaves the timeline unchanged.
  - Selecting `h6` + `h7` shows both the overlap and the edge messages.
  - If Erik has a design with a linked component, a rim picked in it shows `This body is in a linked component…`. This is not automated, because the fixture would need a saved external design.
- [ ] **Step 6: Run the unit tests again.** Expected: all pass.
- [ ] **Step 7: Checkpoint.** Suggested message: `Add the Insert Seats command to Fusion`.

---

### Task 8: Documentation and CI

**Files:**
- Modify: `README.md`, `docs/user-guide.md`, `NOTICE.md`, `.github/workflows/ci.yml`, `.github/ISSUE_TEMPLATE/bug_report.md`

- [ ] **Step 1: Rewrite `README.md`** for Fusion:
  - What it does.
  - Install: copy or link `SolidInserts/` into `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` or `%AppData%\Autodesk\Autodesk Fusion 360\API\AddIns\`, or use **Utilities › Add-Ins › +**.
  - Use, with the existing supported-inserts table converted to decimal points.
  - Checks and limits from Decisions 3–6.
  - Run the tests: the unit command plus the three in-Fusion scripts.
  - Licence and credits: keep the CNC Kitchen non-affiliation sentence and the PDF link. Credit the original SolidInserts for SolidCraft.
  - Remove the language bar, the SolidCraft preview section and the SolidCraft screenshot.
- [ ] **Step 2: Rewrite `docs/user-guide.md`** for Fusion, using the same sections as today: prepare the model; choose series, thread and compensation; run; check and undo; troubleshooting. Remove the Italian link and the patched-desktop sections. The worked example becomes the `h1`/`h2` plate: M3 Ø4 × 6.7 and M4 Ø5.7 × 9.1.
- [ ] **Step 3: Rewrite `NOTICE.md`** with the port's credits (Decision 9). Read `bug_report.md` and change its environment fields to the Fusion version and OS.
- [ ] **Step 4: Replace the `ci.yml` job.** Keep the pinned `actions/checkout` SHA and `persist-credentials: false`, and run `python3 -m unittest discover -s tests/unit -v` (ubuntu-24.04 ships Python 3.12, so no new actions are needed).
- [ ] **Step 5: Checkpoint.** Suggested message: `Document SolidInserts for Fusion`.

---

### Task 9: Remove the SolidCraft build (needs Erik's explicit OK)

**Files:**
- Delete: `Cargo.toml`, `Cargo.lock`, `src/`, `wit/`, `build.sh`, `package-preview-kit.sh`, `try-hole-selection.sh`, `solidcraft-v0.41.0-select-holes.patch`, `solidcraft-v0.42.0-select-holes.patch`, `plugin.json`, `tests/solidcraft.py`, `examples/`, `docs/desktop-preview.md`, `docs/user-guide.it.md`, `README.it.md`, `docs/readme/`, `assets/screenshots/insert-seat-preview.png`
- Modify: `.gitignore` (drop `/target/`, `/dist/`, `/.codex-attachments/`)
- Ask: `.github/FUNDING.yml` points to the original author's Ko-fi. Keep it, change it, or delete it, as Erik decides.

- [ ] **Step 1: Ask Erik** to approve the deletion list and decide on `FUNDING.yml`. Do nothing until he answers.
- [ ] **Step 2: Delete** the approved files with `git rm`. Grep for leftover links with `grep -rn "SolidCraft\|\.sc\b\|README.it\|docs/readme" --include=*.md .`; only the credit lines should remain.
- [ ] **Step 3: Run the unit tests.** Expected: all pass.
- [ ] **Step 4: Checkpoint.** Suggested message: `Remove the SolidCraft plugin build`.

## Spike Findings

Geometry spike (`SolidInsertsSpike`):

- **0a/0b.** A through-all cut into a component placed away from the origin raises "body not found to extrude through". This happens with the native body and with the occurrence proxy as participant. A 15 mm distance cut with the native body as participant creates the hole. Seats are distance cuts, so the add-in is unaffected. Test helpers cut component through holes with a distance deeper than the block.
- **0c.** Pending. Does an occurrence moved with `transform2` after its body is built stay moved after the next recompute? The first fixture moved Bracket A this way, and its proxy rim was then not found at the moved position.
- **1.** `addWithoutEdges` + `project2([rim], True)` returns one `SketchCircle`. Construction works, the seat circle with a diameter dimension is fully constrained, `profiles.count == 1`, and on a top face the sketch normal · outward = 1.0.
- **2.** The cut removed 36.835174 mm³, the analytic π/4·(4²−3²)·6.7.
- **3.** Removed − analytic = 0.000000000 mm³; floor area − πr² = 0.000000000 mm². Volume tolerances in Global Constraints are generous.
- **4.** After cutting rim A, rim B's old edge is still valid, and `findEntityByToken(token_b)` returns exactly one `BRepEdge` (r = 0.15 cm).
- **5.** Names containing `·` and `×` read back unchanged.
- **6.** Pending. Where proxy geometry lives, and whether a component cut changes both occurrences.
- **7a.** `feature.bodies.count == 1` and is the plate. `endFaces` holds one planar face at depth 6.700 mm with normal (0, 0, 1), pointing out of the material toward the opening.
- **7b.** A break-through cut gives an empty `endFaces` collection (count 0), not None.
- **8.** `findAttributes('SolidInserts', 'seat')` finds one attribute whose `parent == feature`. `feature.sideFaces` contains the seat wall.

Command spike (`SolidInsertsCommandSpike`):

- **1.** With a rim preselected, `activate` sees 0 selections. An `inputChanged` for the selection input follows with 1 selection, then `executePreview` with 1.
- **2.** Text set on the read-only text box in `executePreview` reads back unchanged (`preview ran 1`).
- **3.** In every run `execute` never fired, termination reason was 4 (`PreEmptedTerminationReason`), and the timeline kept the preview's sketch and seat (8 → 10).
- **4.** Pending. Driven failing run.
- **5.** `doExecute(True)` inside `activate` raises "can not terminate command during a command event". Retried from a custom event fired by `activate`.
- **6.** One `UndoCommand` took the timeline 10 → 8: the sketch and the seat are undone together.
