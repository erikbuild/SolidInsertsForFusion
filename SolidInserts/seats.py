# ABOUTME: Plans a batch of insert seats from hole openings: sizes each seat from the catalog,
# ABOUTME: collects what blocks or warns about it, and phrases the dialog summary.
from dataclasses import dataclass, field

from .catalog import Insert, choose
from .geometry import PARALLEL, TOLERANCE_MM, dot, norm, round_mm, sub
from .messages import SeatError, message

SEAT_ATTRIBUTE_GROUP = 'SolidInserts'
SEAT_ATTRIBUTE_NAME = 'seat'
SEAT_NAME_PREFIX = 'SolidInserts · '


@dataclass(frozen=True)
class Opening:
    """A hole entrance, measured in millimetres in its body's component space."""
    ordinal: int
    body_key: str
    body_name: str
    plane_key: str
    center: tuple
    outward: tuple
    diameter: float
    bore_depth: float
    can_deepen: bool
    clearance: float
    rim_token: str = field(default='', compare=False)


@dataclass(frozen=True)
class Seat:
    opening: Opening
    insert: Insert
    diameter: float
    depth: float
    wall: float
    name: str


@dataclass(frozen=True)
class SeatPlan:
    seats: tuple
    obstacles: tuple
    notes: tuple

    @property
    def can_apply(self):
        return bool(self.seats) and not self.obstacles


def same_opening(a, b):
    return (a.body_key == b.body_key and a.plane_key == b.plane_key
            and norm(sub(a.center, b.center)) <= TOLERANCE_MM)


def coplanar_distance(a, b):
    """Distance between two openings on the same flat face of one body, else None."""
    delta = sub(a.center, b.center)
    if (a.body_key == b.body_key and dot(a.outward, b.outward) > PARALLEL
            and abs(dot(delta, a.outward)) <= TOLERANCE_MM):
        return norm(delta)
    return None


def plan_seats(openings, series, thread_label, compensation_mm, rim_errors=()):
    obstacles = list(rim_errors)
    if not -1.0 <= compensation_mm <= 1.0:
        return SeatPlan((), tuple(obstacles + [message('compensation_range')]), ())
    if not openings and not obstacles:
        return SeatPlan((), (message('select_rims'),), ())

    unique = []
    for candidate in openings:
        if not any(same_opening(candidate, kept) for kept in unique):
            unique.append(candidate)

    seats = []
    notes = []
    for hole in unique:
        def about_hole(reason):
            return message('hole_prefix', ordinal=hole.ordinal, body=hole.body_name, reason=reason)

        try:
            insert = choose(series, thread_label, hole.diameter)
        except SeatError as error:
            obstacles.append(about_hole(str(error)))
            continue
        diameter = round_mm(insert.bore_mm + compensation_mm)
        depth = round_mm(insert.depth_mm)
        wall = round_mm(hole.clearance - diameter / 2)
        if diameter <= hole.diameter + TOLERANCE_MM:
            obstacles.append(about_hole(message('seat_not_wider', seat=diameter, hole=hole.diameter)))
        if wall <= TOLERANCE_MM:
            obstacles.append(about_hole(message('seat_reaches_edge', seat=diameter)))
        if not hole.can_deepen and depth + TOLERANCE_MM >= hole.bore_depth:
            obstacles.append(about_hole(message('seat_too_deep', depth=depth, bore=hole.bore_depth)))
        if TOLERANCE_MM < wall and wall + TOLERANCE_MM < insert.wall_mm:
            notes.append(about_hole(message('thin_wall', wall=wall, catalog=insert.wall_mm)))
        seats.append(Seat(hole, insert, diameter, depth, wall,
                          message('insert_name', product=insert.product_name)))

    for index, seat in enumerate(seats):
        for other in seats[:index]:
            distance = coplanar_distance(seat.opening, other.opening)
            if distance is not None and distance <= (seat.diameter + other.diameter) / 2 + TOLERANCE_MM:
                obstacles.append(message('seats_overlap', first=other.opening.ordinal,
                                         second=seat.opening.ordinal))
    return SeatPlan(tuple(seats), tuple(obstacles), tuple(notes))


def summary_lines(plan):
    lines = [message('seat_line', ordinal=seat.opening.ordinal, thread=seat.insert.thread,
                     diameter=seat.diameter, depth=seat.depth) for seat in plan.seats]
    lines.extend(plan.obstacles)
    lines.extend(message('note_line', note=note) for note in plan.notes)
    return lines
