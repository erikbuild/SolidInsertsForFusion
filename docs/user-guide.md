# SolidInserts for Fusion user guide

SolidInserts enlarges the opening of an existing hole to make a seat for a heat-set threaded insert. It cuts inward from the rim you select and adds an editable sketch and extrude cut for each seat to the Fusion timeline.

## Install

Follow the [README](../README.md#install). After installation, **Insert Seats** appears in **Solid › Create**.

## Prepare the model

Use a design that captures design history. Use a cylindrical hole that opens directly onto a flat face, with no chamfer or countersink. For a through hole, select the rim on the side where the insert will enter. The wider part of the cut starts at that rim and leaves part of the original through bore below it.

## Choose the series, thread, compensation and chamfer

**Type** selects the CNC Kitchen insert series. The table gives example seat dimensions at zero compensation.

| Series | Supported screw threads | M3 seat (diameter × depth) |
| --- | --- | --- |
| Standard | M1.6, M2, M2.5, M3, M4, M5, M6, M8, M10 | Ø4 × 6.7 mm |
| Short Version | M3, M4, M5, M6, M8 | Ø4 × 4 mm |
| VORON M3 × 5 × 4 | M3 | Ø4.6 × 5 mm |

The VORON seat is Ø4.6 mm, the insert hole Voron Design uses for M3 × 5 × 4 inserts throughout its [Downdraft toolhead](https://github.com/VoronDesign/voron-downdraft) CAD. CNC Kitchen's sheet gives Ø4.45 mm; set **Diameter compensation** to −0.15 mm for that size.

**Screw thread** sets the screw thread. **Automatic (from hole Ø)** recognises each selected hole drawn at a thread's nominal diameter or at one of its ISO 273 clearance sizes (fine, medium or coarse), within ±0.05 mm. A Ø3 mm or Ø3.2 mm hole gives M3, and a Ø4 mm or Ø4.5 mm hole gives M4. Where the two coincide, the nominal thread wins: a Ø10 mm hole is M10, not an M8 coarse clearance hole. For tap-drill holes, choose the intended screw thread explicitly. For example, choose **M3 × 0.50** for a Ø2.5 mm M3 tap-drill hole, which Automatic reads as M2.5.

One run uses the same series and compensation for every selected hole. Automatic mode can resolve different thread sizes in that batch if the series supports all of them. A manual thread choice applies to the whole batch. Use separate runs for different series, different compensation values, or different manually assigned threads.

**Diameter compensation** adds a correction to the catalog seat diameter, from −1 to +1 mm in 0.01 mm steps. Start at **0 mm** for the catalog size. For a Standard M3 insert, **+0.10 mm** gives a Ø4.10 mm seat. Depth stays at 6.7 mm because it is set by the insert length plus 1 mm. To tune the fit, print a small test piece in the same material and orientation as the final part.

**Chamfer top edge** adds a 45° chamfer where each seat meets the face, so the insert starts straight under the soldering iron. It is on by default. **Chamfer size** sets how far the chamfer cuts into the face and down the seat wall, from 0.1 to 2 mm in 0.05 mm steps, and starts at **0.4 mm**. A 0.4 mm chamfer on a Ø4 mm seat makes the opening Ø4.8 mm. Clear the check box for a plain seat; **Chamfer size** is then unavailable.

## Cut the seats

1. Open **Solid › Create › Insert Seats**. Rims you selected before opening the command are already in **Holes**.
2. Click the circular rim of each hole, where the cylindrical wall meets the flat face. Click a selected rim again to remove it.
3. Set **Type**, **Screw thread**, **Diameter compensation**, **Chamfer top edge** and **Chamfer size**. The viewport shows each planned seat as a see-through orange cylinder, with a cone at the top for its chamfer, and updates it as you change the selection or settings.
4. Read the **Seats** box. It lists each hole with its thread, seat diameter, depth and chamfer, then anything that blocks the batch and any notes. **OK** stays disabled while something blocks the batch.
5. Click **OK** to apply the cuts, or **Cancel** to leave the design unchanged.

## Check and undo the cuts

After a run, inspect the `Profile Insert …` sketches, `SolidInserts · Insert …` cuts and `SolidInserts · Chamfer Insert …` chamfers in the timeline. Edit the sketch dimension to change the seat diameter, the extrusion distance to change its depth, or the chamfer distance to change the chamfer. One **Undo** immediately after the run removes the whole batch.

For example, on a plate with a Ø3 mm blind hole 7 mm deep and a Ø4 mm through hole, select both top rims and run **Standard** with **Automatic (from hole Ø)** and **0 mm** compensation. The result is an M3 seat of **Ø4 × 6.7 mm** and an M4 seat of **Ø5.7 × 9.1 mm**, each with the default **0.4 mm** chamfer.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| **Insert Seats** is missing | In **Utilities › Add-Ins**, check that **SolidInserts** is running. The folder must be named `SolidInserts` and contain `SolidInserts.py` and `SolidInserts.manifest`. |
| **SolidInserts needs design history** | The design is in direct modeling mode. Right-click the top of the browser and choose **Capture Design History**. |
| A rim is refused | Click the circular edge where the cylindrical wall meets the flat face, on the side where the insert goes. Chamfered or countersunk openings and rims on curved faces are not supported. |
| **OK** is disabled | Read the **Seats** box. It lists every problem that blocks the batch. |
| Automatic sizing fails, or a thread is unavailable | Select the screw thread explicitly for a tap-drill hole or a hole that is neither a nominal nor an ISO 273 clearance size. If the intended size is unavailable in the chosen series, use a compatible series and matching insert. |
| The seat is narrower than the hole or reaches an edge or another seat | Check the original hole size and compensation. If the selected insert needs more space, revise the hole spacing or surrounding material. |
| The chamfer reaches an edge, or the chamfers of two seats overlap | The plain seats fit, but their chamfered openings do not. Reduce **Chamfer size** or clear **Chamfer top edge**. |
| There is too little depth | Check the body thickness and any internal cavities. Use a shorter compatible insert or revise the part to leave enough material under the seat. |
| The cut fails after **OK** | The seat met an edge, a cavity or another hole, or broke through the part. Check the material around and below the hole. |
| **The chamfer could not be cut**, or **meets an edge, a cavity or another hole**, after **OK** | The chamfer did not fit at the seat opening, or broke into material hidden just below the face. Reduce **Chamfer size** or clear **Chamfer top edge**. |
| The hole already has a SolidInserts seat | Edit the existing sketch and cut in the timeline. |
| The hole is in a linked component | Open the linked design and add the seat there. |
