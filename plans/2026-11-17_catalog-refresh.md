# Catalogue Refresh And Clearance-Hole Matching Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Bring the insert catalogue up to CNC Kitchen's current sheet, using Voron's Downdraft Ø4.6 seat for the VORON series. Make **Automatic** recognise ISO 273 clearance holes as well as nominal-diameter holes.

**Architecture:** Both changes are data and rules in the pure `catalog.py`, plus copy in `messages.py` and the two docs. `Thread` gains its ISO 273 clearance sizes. `choose` tries every thread's nominal diameter first, then every thread's clearance sizes. Nothing in the Fusion-facing modules changes.

**Tech Stack:** Fusion add-in API (Python 3.14), stdlib `unittest`, and in-Fusion test scripts that Erik runs.

**Spec:** Erik approved this in chat on 2026-11-17. It is repeated here because there is no separate spec file. Items marked *(Claude's call)* were proposed by Claude and are listed under Decisions for Erik to confirm.

- **Catalogue** ("Full catalogue update"):
  - Add CNC Kitchen's current-sheet inserts. Columns are L, D2 and W in mm.
    - Standard M1.6 × 2.5: 2.5, 2.2, 1.3.
    - Short M6 × 6.8: 6.8, 8.1, 3.3.
    - Short M8 × 6.8: 6.8, 9.7, 4.5.
  - Add the thread M1.6 × 0.35.
  - Every other row already matches the current sheet.
- **VORON seat** ("Let's do 4.6, and cite Downdraft in the readme as the reason"):
  - The VORON M3 × 5 × 4 seat becomes Ø4.6 mm (L 4.0, W 1.6 unchanged).
  - In Voron Design's Downdraft toolhead STEP, every modelled insert sits in a Ø4.6 hole: 328 insert-to-hole pairings across 40 printed parts.
  - CNC Kitchen's current sheet gives Ø4.45. Trident R2 parts mostly use Ø4.7, which Erik has found too loose.
- **Automatic matching** ("ISO 273 clearance sizes work"):
  - Automatic also accepts each thread's ISO 273 fine, medium and coarse clearance diameters, within the existing ±0.05 mm.
  - Where a nominal size and a clearance size coincide (Ø2.0, Ø10.0), the nominal thread wins.

| Thread | Nominal | Fine | Medium | Coarse |
|---|---|---|---|---|
| M1.6 | 1.6 | 1.7 | 1.8 | 2.0 |
| M2 | 2.0 | 2.2 | 2.4 | 2.6 |
| M2.5 | 2.5 | 2.7 | 2.9 | 3.1 |
| M3 | 3.0 | 3.2 | 3.4 | 3.6 |
| M4 | 4.0 | 4.3 | 4.5 | 4.8 |
| M5 | 5.0 | 5.3 | 5.5 | 5.8 |
| M6 | 6.0 | 6.4 | 6.6 | 7.0 |
| M8 | 8.0 | 8.4 | 9.0 | 10.0 |
| M10 | 10.0 | 10.5 | 11.0 | 12.0 |

## Decisions Made While Planning (Claude's calls; Erik to confirm)

1. **The Automatic label becomes `Automatic (from hole Ø)`.** "Automatic (nominal Ø)" stops being true once clearance holes match.
2. **Nominal beats clearance by trying every nominal diameter first, then every clearance size.** The alternative, nearest-size-wins, gives the same answer for every size in the table, so the simpler rule is used.
3. **Tap-drill holes stay manual.** A Ø2.5 M3 tap-drill hole still matches M2.5 nominal. The docs and tooltip keep telling people to choose the thread for tap-drill holes.
4. **The repo vendors CNC Kitchen's current sheet, and the README links that copy.** Erik: "You may vendor in that image then."
   - **Where it lives:** `assets/cnc-kitchen/dimensions-and-design-guidelines.png`, an unchanged copy of `https://cdn.shopify.com/s/files/1/0654/4821/4767/files/Dimensions_and_Guidlines.png` (SHA-1 `6eeb8c4af9e09f40e6a85befb5ed6745fe88059f`, 1600 × 1600). CNC Kitchen's filename really does say "Guidlines".
   - **Why a copy:** CNC Kitchen publishes the current sheet only as that image, in the galleries of its cnckitchen.store insert product pages. Every PDF still on its sites is the old sheet: cnckitchen.com's, the store's "poster" PDF (byte-identical to it), and the blog posts' copies.
   - **Checked:** Claude checked the image: every value in the Spec is there, with "min. L+1mm" for blind holes.
   - **Credit:** the README credits CNC Kitchen and links the source image and the [Standard set product page](https://cnckitchen.store/products/gewindeeinsatz-threaded-insert-set-standard-200-stk-pcs) where it appears. `NOTICE.md` records the copy alongside the other assets.
5. **The thin-wall note and every other check stay as they are.** For example, an M8 coarse hole (Ø10) resolves to M10 nominal. An M10 coarse hole (Ø12) with a Standard Ø12 seat gets the existing "seat must be wider than the hole" refusal.

## Global Constraints

- The pure modules (`catalog`, `geometry`, `seats`, `messages`) work in millimetres, never import `adsk`, and import under plain CPython ≥ 3.12.
- Every code file starts with two `# ABOUTME: ` lines. Names and comments contain no time references.
- All user-facing copy lives in `messages.py`.
- Unit test command (repo root): `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`. Its output must be pristine.
- In-Fusion tests are `tests/fusion/SolidInsertsIntegrationTest` (loads the add-in package from the repo) and `tests/fusion/SolidInsertsCommandTest` (drives the running add-in; Erik reloads the add-in first with Stop and Run). Both end with `==== N passed, M failed ====`.

## Ground Rules For The Executing Agent

1. **Commit only with Erik's OK.** At each commit step, stop, suggest a message, and wait. If Erik grants standing approval for this plan, record it in the ledger and commit at the steps.
2. **Claude cannot run Fusion.** At each **[FUSION — Erik runs]** step, stop and wait for Erik to paste the Text Commands output.

## Review Focus

1. **Ø2.0 and Ø10.0 holes:** each is a nominal size and a coarse clearance size. They resolve to M2 and M10. *(Task 2: `test_nominal_wins_over_clearance`.)*
2. **A hole between clearance sizes (Ø3.3):** still refused with "Select the screw thread explicitly". *(Task 2: `test_automatic_refuses_unrecognised_holes`.)*
3. **A clearance hole wider than the seat (M10 coarse Ø12 with a Standard Ø12 seat):** the existing "seat must be wider" refusal. *(Task 2: `test_coarse_clearance_wider_than_the_seat`.)*
4. **A VORON seat on an M3 clearance hole:** Ø4.6 × 5 mm. *(Task 2: `test_automatic_clearance_hole`.)*
5. **The catalogue has exactly the sheet's rows:** no extra or missing (series, thread) pairs. *(Task 1: `test_catalog_has_exactly_these_rows`.)*

---

### Task 1: Catalogue refresh

**Files:**
- Create: `assets/cnc-kitchen/dimensions-and-design-guidelines.png` (Decision 4)
- Modify: `SolidInserts/catalog.py`, `SolidInserts/messages.py`, `README.md`, `docs/user-guide.md`, `NOTICE.md`
- Test: `tests/unit/test_catalog.py`, `tests/unit/test_messages.py`

**Interfaces:**
- Produces:
  - `THREADS` begins with `Thread('M1.6 × 0.35', 1.6)`.
  - `SEAT_DIMENSIONS` gains `(Series.STANDARD, 1.6): (2.5, 2.2, 1.3)`, `(Series.SHORT, 6.0): (6.8, 8.1, 3.3)` and `(Series.SHORT, 8.0): (6.8, 9.7, 4.5)`. `(Series.VORON, 3.0)` becomes `(4.0, 4.6, 1.6)`.
  - `series_tooltip`: `Short Version for M3, M4, M5, M6 and M8. VORON M3 × 5 × 4 for M3.`

- [ ] **Step 1: Write the failing tests**

In `tests/unit/test_catalog.py`:
- In `CATALOG`, add `(Series.STANDARD, 'M1.6 × 0.35'): (2.5, 2.2, 1.3)`, `(Series.SHORT, 'M6 × 1.00'): (6.8, 8.1, 3.3)` and `(Series.SHORT, 'M8 × 1.25'): (6.8, 9.7, 4.5)`.
- Set the VORON row to `(4.0, 4.6, 1.6)`.
- Make the comment above `CATALOG` read: `# CNC Kitchen, Dimensions & Design Guidelines, except the VORON seat diameter, which is the Ø4.6 mm insert hole in Voron Design's Downdraft toolhead CAD: (series, thread) -> (L, D2, W) in mm.` Wrap it to the file's line length.
- In `test_hole_selects_the_thread_but_series_sets_the_seat`, the VORON tuple becomes `(Series.VORON, 4.6, 5.0)`.
- `test_catalog_has_exactly_these_rows`: for every `Series` and every label in `THREAD_CHOICES[1:]`, `choose(series, label, 0.0)` succeeds exactly when `(series, label)` is in `CATALOG`, and raises `SeatError` otherwise.
- `test_product_names` also asserts `choose(Series.STANDARD, 'M1.6 × 0.35', 1.6).product_name == 'M1.6 × 2.5'` and `choose(Series.SHORT, 'M6 × 1.00', 6.0).product_name == 'M6 × 6.8 (Short Version)'`.
- `test_automatic_finds_m1_6`: `choose(Series.STANDARD, AUTOMATIC, 1.6).thread == 'M1.6 × 0.35'`.
- `test_thread_choices_start_with_automatic` expects `'M1.6 × 0.35'` between `'Automatic (nominal Ø)'` and `'M2 × 0.40'`.

In `tests/unit/test_messages.py`, set the expected `series_tooltip` to the Interfaces value.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`
Expected: FAIL. Failures in `test_every_catalog_row`, `test_hole_selects_the_thread_but_series_sets_the_seat`, `test_catalog_has_exactly_these_rows`, `test_product_names`, `test_automatic_finds_m1_6`, `test_thread_choices_start_with_automatic` and the messages test. All other tests pass.

- [ ] **Step 3: Implement the catalogue rows, the thread and the tooltip**

Use the values in the Interfaces block. Make the comment above `SEAT_DIMENSIONS` say the same as the test comment: values are CNC Kitchen's L, D2 and W, except the VORON D2, which is the Downdraft Ø4.6 hole.

- [ ] **Step 4: Run the tests to verify they pass**

Run: `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`
Expected: OK, with no other output.

- [ ] **Step 5: Update the docs**

- **`README.md` series table:**
  - The Standard row lists `M1.6, M2, M2.5, M3, M4, M5, M6, M8, M10`.
  - The Short Version row lists `M3, M4, M5, M6, M8`.
  - The VORON row's example is `Ø4.6 × 5 mm`.
- **`README.md` text:**
  - In the sentence about CNC Kitchen's sheet, add "except the VORON seat diameter".
  - Below the table, add: `The VORON seat is Ø4.6 mm, the insert hole Voron Design uses for M3 × 5 × 4 inserts throughout its [Downdraft toolhead](https://github.com/VoronDesign/voron-downdraft) CAD. CNC Kitchen's sheet gives Ø4.45 mm; set **Diameter compensation** to −0.15 mm for that size.`
  - Copy the image into the repo, as described in Decision 4, and check that its SHA-1 matches.
  - Point the sheet link at the vendored copy: `[CNC Kitchen dimensions and design guidelines](assets/cnc-kitchen/dimensions-and-design-guidelines.png) (CNC Kitchen's [current sheet](https://cdn.shopify.com/s/files/1/0654/4821/4767/files/Dimensions_and_Guidlines.png), shown on its [insert product pages](https://cnckitchen.store/products/gewindeeinsatz-threaded-insert-set-standard-200-stk-pcs))`.
- **`docs/user-guide.md`:** make the same three changes to its series table, and add the same Downdraft sentence below it.
- **`NOTICE.md`:**
  - The CNC Kitchen line also names the VORON exception.
  - Add a line: `assets/cnc-kitchen/dimensions-and-design-guidelines.png` is CNC Kitchen's Dimensions & Design Guidelines sheet, copied unchanged from its store.

- [ ] **Step 6: Commit**

```bash
git add assets/cnc-kitchen/dimensions-and-design-guidelines.png NOTICE.md SolidInserts/catalog.py SolidInserts/messages.py README.md docs/user-guide.md tests/unit/test_catalog.py tests/unit/test_messages.py
git commit -m "Refresh the insert catalogue from CNC Kitchen's current sheet and seat VORON inserts at Ø4.6"
```

---

### Task 2: Automatic recognises ISO 273 clearance holes

**Files:**
- Modify: `SolidInserts/catalog.py`, `SolidInserts/messages.py`, `README.md`, `docs/user-guide.md`
- Test: `tests/unit/test_catalog.py`, `tests/unit/test_seats.py`, `tests/unit/test_messages.py`, `tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py`

**Interfaces:**
- Consumes: Task 1's `THREADS` (nine threads, M1.6 first).
- Produces:
  - `Thread.clearance_mm: tuple`: the (fine, medium, coarse) ISO 273 diameters from the Spec table, as the last field.
  - `AUTOMATIC = 'Automatic (from hole Ø)'`.
  - `choose(series, thread_label, hole_diameter_mm)` keeps its signature. Under Automatic it returns the first thread whose nominal diameter matches within `AUTO_TOLERANCE_MM + 1e-8`; failing that, the first thread with a matching clearance size; failing that, it raises `choose_thread` as now.
  - `thread_tooltip`: `('Automatic matches the hole to a screw’s nominal or ISO 273 clearance diameter within ±0.05 mm. ' 'For tap-drill holes, choose the screw size.')`

- [ ] **Step 1: Write the failing unit tests**

In `tests/unit/test_catalog.py`:
- `test_automatic_rejects_clearance_holes` is replaced by `test_automatic_matches_iso_273_clearance_holes`. It checks that `choose(Series.STANDARD, AUTOMATIC, d).thread` is the expected thread for every pair below.
  - **M1.6 × 0.35:** 1.7 and 1.8.
  - **M2 × 0.40:** 2.2, 2.4 and 2.6.
  - **M2.5 × 0.45:** 2.7, 2.9 and 3.1.
  - **M3 × 0.50:** 3.2, 3.4 and 3.6.
  - **M4 × 0.70:** 4.3, 4.5 and 4.8.
  - **M5 × 0.80:** 5.3, 5.5 and 5.8.
  - **M6 × 1.00:** 6.4, 6.6 and 7.0.
  - **M8 × 1.25:** 8.4 and 9.0.
  - **M10 × 1.50:** 10.5, 11.0 and 12.0.
- `test_clearance_tolerance_edge`: 3.25 gives `'M3 × 0.50'`.
- `test_nominal_wins_over_clearance`: 2.0 gives `'M2 × 0.40'`, and 10.0 gives `'M10 × 1.50'`.
- `test_automatic_refuses_unrecognised_holes`: 3.3 raises `SeatError` with `'Hole Ø3.30 mm. Select the screw thread explicitly.'`.
- `test_automatic_clearance_hole_with_voron`: `choose(Series.VORON, AUTOMATIC, 3.2)` has `bore_mm == 4.6` and `depth_mm` within 1e-9 of 5.0.
- `test_thread_choices_start_with_automatic` expects `'Automatic (from hole Ø)'` first.

In `tests/unit/test_seats.py`:
- `test_automatic_needs_a_nominal_hole` becomes `test_automatic_needs_a_recognised_hole`. It uses `opening(diameter=3.3)` and expects the obstacle `'Hole 1 on Plate. Hole Ø3.30 mm. Select the screw thread explicitly.'`. With `thread='M3 × 0.50'`, it expects a seat diameter of 4.0.
- `test_automatic_clearance_hole_plans_a_seat`: `plan(opening(diameter=3.2)).seats[0]` has thread `'M3 × 0.50'`, diameter 4.0 and no obstacles.
- `test_coarse_clearance_wider_than_the_seat`: `plan(opening(diameter=12.0))` has the obstacle `'Hole 1 on Plate. The Ø12.00 seat must be wider than the Ø12.00 mm hole.'`. Check the `opening` helper's clearance default; if it is too small for a Ø12 seat, pass a larger `clearance` so that this is the only obstacle.

In `tests/unit/test_messages.py`, set the expected `thread_tooltip` to the Interfaces value.

- [ ] **Step 2: Run the unit tests to verify they fail**

Run: `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`
Expected: FAIL in the new and changed tests above, with the clearance diameters raising `SeatError` and the label and tooltip differing. Every other test passes.

- [ ] **Step 3: Add the Fusion integration case**

In `test_single_seats`, add the case `('h3', 'Plate', None, 30.310, 11.3)`. h3 is the fixture's Ø3.2 through hole in the 18 mm plate, and the M3 seat is Ø4 × 6.7: π/4 · (4.0² − 3.2²) · 6.7 = 30.310 mm³.

- [ ] **Step 4: [FUSION — Erik runs] the integration test, RED**

Erik runs `SolidInsertsIntegrationTest`.
Expected: `==== 67 passed, 3 failed ====`. The three failures are all h3's:
- "seat plan can apply" lists `Hole 1 on Plate. Hole Ø3.20 mm. Select the screw thread explicitly.`
- The removed volume is 0.000 mm³.
- There is no seat floor at z = 11.3 mm, because `cut_seats` gets a plan with no seats.

- [ ] **Step 5: Implement clearance matching, the label and the tooltip**

Use the Interfaces block and the Spec table. Update the `choose` docstring to describe both passes. Keep `AUTO_TOLERANCE_MM`.

- [ ] **Step 6: Run the unit tests to verify they pass**

Run: `uv run --python 3.14 --no-project python -m unittest discover -s tests/unit`
Expected: OK, with no other output.

- [ ] **Step 7: Update the docs**

- **`README.md`:** the Automatic sentences become: `Automatic sizing recognises a hole drawn at a thread's nominal diameter or at one of its ISO 273 clearance sizes (fine, medium or coarse; Ø3.2, Ø3.4 or Ø3.6 mm for M3), within ±0.05 mm. Where the two coincide, the nominal thread wins: a Ø10 mm hole is M10, not an M8 coarse clearance hole. For tap-drill holes, choose the screw size manually.` Keep the two sentences about series and batches.
- **`docs/user-guide.md`:**
  - The label becomes **Automatic (from hole Ø)** everywhere.
  - The Automatic paragraph says the same as the README.
  - The troubleshooting row's remedy becomes: `Select the screw thread explicitly for a tap-drill hole or a hole that is neither a nominal nor an ISO 273 clearance size. If the intended size is unavailable in the chosen series, use a compatible series and matching insert.`

- [ ] **Step 8: [FUSION — Erik runs] both Fusion tests, GREEN**

Erik reloads the add-in (Stop, then Run), then runs `SolidInsertsIntegrationTest` and `SolidInsertsCommandTest`.
Expected: integration `==== 70 passed, 0 failed ====` (the h3 case adds three checks: can apply, volume, floor); command test `==== 18 passed, 0 failed ====`.

- [ ] **Step 9: Commit**

```bash
git add SolidInserts/catalog.py SolidInserts/messages.py README.md docs/user-guide.md tests/unit/test_catalog.py tests/unit/test_seats.py tests/unit/test_messages.py tests/fusion/SolidInsertsIntegrationTest/SolidInsertsIntegrationTest.py
git commit -m "Let Automatic recognise ISO 273 clearance holes"
```
