# SolidInserts for Fusion user guide

SolidInserts enlarges the opening of an existing hole to make a seat for a heat-set threaded insert. It cuts inward from the rim you select and adds an editable sketch and extrude cut for each seat to the Fusion timeline.

## Install

Follow the [README](../README.md#install). After installation, **Insert Seats** appears in **Solid › Create**.

## Prepare the model

Use a design that captures design history. Use a cylindrical hole that opens directly onto a flat face, with no chamfer or countersink. For a through hole, select the rim on the side where the insert will enter. The wider part of the cut starts at that rim and leaves part of the original through bore below it.

## Choose the series, thread and compensation

**Type** selects the CNC Kitchen insert series. The table gives example seat dimensions at zero compensation.

| Series | Supported screw threads | M3 seat (diameter × depth) |
| --- | --- | --- |
| Standard | M2, M2.5, M3, M4, M5, M6, M8, M10 | Ø4 × 6.7 mm |
| Short Version | M3, M4, M5 | Ø4 × 4 mm |
| VORON M3 × 5 × 4 | M3 | Ø4.4 × 5 mm |

**Screw thread** sets the screw thread. **Automatic (nominal Ø)** compares each selected hole diameter with the nominal thread diameter within ±0.05 mm. A Ø3 mm hole gives M3, and a Ø4 mm hole gives M4. For clearance and tap-drill holes, choose the intended screw thread explicitly. For example, choose **M3 × 0.50** for a Ø3.2 mm M3 clearance hole.

One run uses the same series and compensation for every selected hole. Automatic mode can resolve different thread sizes in that batch if the series supports all of them. A manual thread choice applies to the whole batch. Use separate runs for different series, different compensation values, or different manually assigned threads.

**Diameter compensation** adds a correction to the catalog seat diameter, from −1 to +1 mm in 0.01 mm steps. Start at **0 mm** for the catalog size. For a Standard M3 insert, **+0.10 mm** gives a Ø4.10 mm seat. Depth stays at 6.7 mm because it is set by the insert length plus 1 mm. To tune the fit, print a small test piece in the same material and orientation as the final part.

## Cut the seats

1. Open **Solid › Create › Insert Seats**. Rims you selected before opening the command are already in **Holes**.
2. Click the circular rim of each hole, where the cylindrical wall meets the flat face. Click a selected rim again to remove it.
3. Set **Type**, **Screw thread** and **Diameter compensation**. The viewport shows each planned seat as a see-through orange cylinder and updates it as you change the selection or settings.
4. Read the **Seats** box. It lists each hole with its thread, seat diameter and depth, then anything that blocks the batch and any notes. **OK** stays disabled while something blocks the batch.
5. Click **OK** to apply the cuts, or **Cancel** to leave the design unchanged.

## Check and undo the cuts

After a run, inspect the `Profile Insert …` sketches and `SolidInserts · Insert …` cuts in the timeline. Edit the sketch dimension to change the seat diameter or the extrusion distance to change its depth. One **Undo** immediately after the run removes the whole batch.

For example, on a plate with a Ø3 mm blind hole 7 mm deep and a Ø4 mm through hole, select both top rims and run **Standard** with **Automatic (nominal Ø)** and **0 mm** compensation. The result is an M3 seat of **Ø4 × 6.7 mm** and an M4 seat of **Ø5.7 × 9.1 mm**.

## Troubleshooting

| Symptom | What to check |
| --- | --- |
| **Insert Seats** is missing | In **Utilities › Add-Ins**, check that **SolidInserts** is running. The folder must be named `SolidInserts` and contain `SolidInserts.py` and `SolidInserts.manifest`. |
| **SolidInserts needs design history** | The design is in direct modeling mode. Right-click the top of the browser and choose **Capture Design History**. |
| A rim is refused | Click the circular edge where the cylindrical wall meets the flat face, on the side where the insert goes. Chamfered or countersunk openings and rims on curved faces are not supported. |
| **OK** is disabled | Read the **Seats** box. It lists every problem that blocks the batch. |
| Automatic sizing fails, or a thread is unavailable | Select the screw thread explicitly for a clearance or tap-drill hole. If the intended size is unavailable in the chosen series, use a compatible series and matching insert. |
| The seat is narrower than the hole or reaches an edge or another seat | Check the original hole size and compensation. If the selected insert needs more space, revise the hole spacing or surrounding material. |
| There is too little depth | Check the body thickness and any internal cavities. Use a shorter compatible insert or revise the part to leave enough material under the seat. |
| The cut fails after **OK** | The seat met an edge, a cavity or another hole, or broke through the part. Check the material around and below the hole. |
| The hole already has a SolidInserts seat | Edit the existing sketch and cut in the timeline. |
| The hole is in a linked component | Open the linked design and add the seat there. |
