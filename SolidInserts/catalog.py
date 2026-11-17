# ABOUTME: CNC Kitchen heat-set insert catalog: screw threads, insert series and the
# ABOUTME: seat dimensions each insert needs, chosen from a series, a thread and a hole size.
from dataclasses import dataclass
from enum import Enum

from .messages import SeatError, message

AUTOMATIC = 'Automatic (nominal Ø)'
AUTO_TOLERANCE_MM = 0.05


class Series(Enum):
    STANDARD = 'Standard'
    SHORT = 'Short Version'
    VORON = 'VORON M3 × 5 × 4'


@dataclass(frozen=True)
class Thread:
    label: str
    nominal_mm: float


THREADS = (
    Thread('M1.6 × 0.35', 1.6),
    Thread('M2 × 0.40', 2.0),
    Thread('M2.5 × 0.45', 2.5),
    Thread('M3 × 0.50', 3.0),
    Thread('M4 × 0.70', 4.0),
    Thread('M5 × 0.80', 5.0),
    Thread('M6 × 1.00', 6.0),
    Thread('M8 × 1.25', 8.0),
    Thread('M10 × 1.50', 10.0),
)

THREAD_CHOICES = (AUTOMATIC, *(thread.label for thread in THREADS))

# CNC Kitchen, Dimensions & Design Guidelines. Values are L, D2 and W in mm, except the VORON D2,
# which is the Ø4.6 mm insert hole in Voron Design's Downdraft toolhead CAD (CNC Kitchen gives 4.45).
SEAT_DIMENSIONS = {
    (Series.STANDARD, 1.6): (2.5, 2.2, 1.3),
    (Series.STANDARD, 2.0): (3.0, 3.2, 1.3),
    (Series.STANDARD, 2.5): (4.0, 4.0, 1.6),
    (Series.STANDARD, 3.0): (5.7, 4.0, 1.6),
    (Series.STANDARD, 4.0): (8.1, 5.7, 2.1),
    (Series.STANDARD, 5.0): (9.5, 6.5, 2.6),
    (Series.STANDARD, 6.0): (12.7, 8.1, 3.3),
    (Series.STANDARD, 8.0): (12.7, 9.7, 4.5),
    (Series.STANDARD, 10.0): (12.7, 12.0, 6.0),
    (Series.SHORT, 3.0): (3.0, 4.0, 1.6),
    (Series.SHORT, 4.0): (4.0, 5.7, 2.1),
    (Series.SHORT, 5.0): (5.8, 6.5, 2.6),
    (Series.SHORT, 6.0): (6.8, 8.1, 3.3),
    (Series.SHORT, 8.0): (6.8, 9.7, 4.5),
    (Series.VORON, 3.0): (4.0, 4.6, 1.6),
}


@dataclass(frozen=True)
class Insert:
    thread: str
    product_name: str
    length_mm: float
    bore_mm: float
    wall_mm: float

    @property
    def depth_mm(self):
        """Seat depth: the insert length plus 1 mm."""
        return self.length_mm + 1.0


def choose(series, thread_label, hole_diameter_mm):
    """The insert for a series and thread. Automatic picks the thread whose nominal
    diameter matches the hole within AUTO_TOLERANCE_MM."""
    if thread_label == AUTOMATIC:
        thread = next((t for t in THREADS
                       if abs(t.nominal_mm - hole_diameter_mm) <= AUTO_TOLERANCE_MM + 1e-8), None)
    else:
        thread = next((t for t in THREADS if t.label == thread_label), None)
    if thread is None:
        raise SeatError(message('choose_thread', diameter=hole_diameter_mm))

    dimensions = SEAT_DIMENSIONS.get((series, thread.nominal_mm))
    if dimensions is None:
        raise SeatError(message('thread_unavailable', thread=thread.label, series=series.value))
    length_mm, bore_mm, wall_mm = dimensions

    size = thread.label.split(' × ')[0]
    if series is Series.STANDARD:
        product_name = '{} × {:g}'.format(size, length_mm)
    elif series is Series.SHORT:
        product_name = '{} × {:g} (Short Version)'.format(size, length_mm)
    else:
        product_name = series.value
    return Insert(thread.label, product_name, length_mm, bore_mm, wall_mm)
