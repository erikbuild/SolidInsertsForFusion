# SolidInserts for Fusion

<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/branding/solidinserts-logo-inverse.svg">
  <img src="assets/branding/solidinserts-logo.svg" width="390" alt="SolidInserts">
</picture>

[User guide](docs/user-guide.md)

Cut seats for heat-set threaded inserts at the rims of existing holes in Autodesk Fusion.

Select the circular rim of each hole on the side where the insert goes. Choose a CNC Kitchen insert series and a screw thread, check the preview and click **OK**. Each seat becomes an editable sketch and extrude cut in the timeline, with a chamfer on its top edge unless you turn it off. One undo removes the whole batch.

SolidInserts for Fusion is a port of [SolidInserts](https://github.com/NoOneExceptEnderk/SolidInserts) for SolidCraft by NoOneExceptEnderk.

## Install

1. Download or clone this repository.
2. Copy the `SolidInserts` folder into the Fusion add-ins folder for your system, or link it from **Utilities › Add-Ins › Scripts and Add-Ins** with the **+** button. Keep `SolidInserts.py` and `SolidInserts.manifest` together in that folder.

   | OS | Add-ins folder |
   | --- | --- |
   | macOS | `~/Library/Application Support/Autodesk/Autodesk Fusion 360/API/AddIns/` |
   | Windows | `%AppData%\Autodesk\Autodesk Fusion 360\API\AddIns\` |

3. In **Utilities › Add-Ins**, select **SolidInserts** and click **Run**. The add-in starts with Fusion from then on. **Insert Seats** appears in **Solid › Create**.

To put the button in its own toolbar panel, set `use_custom_panel` to `true` in `SolidInserts/config.json` and restart the add-in.

## Use

1. Open **Solid › Create › Insert Seats**.
2. Click the circular rim of each hole on the side where the insert goes. Click a selected rim again to remove it.
3. Choose **Type**, **Screw thread**, **Diameter compensation** and the top-edge chamfer. The viewport shows each planned seat as a see-through cylinder with a cone for its chamfer, and **Seats** lists the diameter, depth and chamfer of each seat and anything that blocks the batch.
4. Click **OK**.

## Supported inserts

SolidInserts is an independent add-in with no affiliation with CNC Kitchen. The seat dimensions for the listed inserts are based on the dimension sheet published by CNC Kitchen, except the VORON seat diameter.

| CNC Kitchen series | Screw sizes | M3 seat example (diameter × depth) |
| --- | --- | --- |
| Standard | M1.6, M2, M2.5, M3, M4, M5, M6, M8, M10 | Ø4 × 6.7 mm |
| Short Version | M3, M4, M5, M6, M8 | Ø4 × 4 mm |
| VORON M3 × 5 × 4 | M3 | Ø4.6 × 5 mm |

The VORON seat is Ø4.6 mm, the insert hole Voron Design uses for M3 × 5 × 4 inserts throughout its [Downdraft toolhead](https://github.com/VoronDesign/voron-downdraft) CAD. CNC Kitchen's sheet gives Ø4.45 mm; set **Diameter compensation** to −0.15 mm for that size.

Automatic sizing matches the hole diameter to a nominal thread diameter within ±0.05 mm. For clearance holes or tap drills, choose the screw size manually. For example, choose M3 for a Ø3.2 mm M3 clearance hole. One insert series applies to the batch. Automatic sizing can choose a different thread size for each hole.

Seat depth equals insert length plus 1 mm. The diameter compensation defaults to zero and changes only the diameter. **Chamfer top edge** is on by default and adds a 0.4 mm 45° lead-in at each seat opening; set **Chamfer size** from 0.1 to 2 mm. Print a test piece to fine-tune the fit. [CNC Kitchen dimensions and design guidelines](assets/cnc-kitchen/dimensions-and-design-guidelines.png) (CNC Kitchen's [current sheet](https://cdn.shopify.com/s/files/1/0654/4821/4767/files/Dimensions_and_Guidlines.png), shown on its [insert product pages](https://cnckitchen.store/products/gewindeeinsatz-threaded-insert-set-standard-200-stk-pcs)).

## What SolidInserts checks

SolidInserts accepts cylindrical holes with a circular, unchamfered entrance on a flat face. The design must capture design history, so the cuts stay editable.

- The seat must be wider than the hole and must not reach a nearby edge at the opening. The **Seats** box adds a note when the material at the opening is thinner than the catalog recommends.
- A through hole keeps a section of the original bore below the seat. A blind hole with a flat floor can be deepened to fit the insert.
- Seats in one batch must not overlap.
- With **Chamfer top edge** on, the chamfered opening must also clear nearby edges and the other seats.
- After each cut and chamfer, SolidInserts compares the removed volume with the expected volume and checks the seat floor, so a cut or chamfer that meets an edge, a cavity or another hole is refused.
- A hole inside a component gets its seat in the component, so every instance of that component shows it. Holes in linked components are edited in their own design.
- A hole that already has a SolidInserts seat is refused. Edit that seat in the timeline instead.

## Test

The unit tests cover the catalog, the geometry rules and seat planning. They need Python 3.12 or later:

```sh
python3 -m unittest discover -s tests/unit -v
```

The Fusion tests run inside Fusion. Link each folder in **Utilities › Add-Ins › Scripts and Add-Ins** with **+**, run it and read the PASS/FAIL lines in the Text Commands palette:

- `tests/fusion/SolidInsertsIntegrationTest` builds fixture geometry, then reads hole openings and cuts seats with the add-in code.
- `tests/fusion/SolidInsertsCommandTest` drives the running add-in's **Insert Seats** command end to end.

## License and credits

SolidInserts for Fusion is distributed under the [MIT License](LICENSE). [Third-party credits](NOTICE.md).
