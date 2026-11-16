# ABOUTME: Pure millimetre geometry rules for insert seats: whether a rim is a hole entrance,
# ABOUTME: where the bore ends, and whether a finished cut has the right direction, volume and floor.
import math
from dataclasses import dataclass

TOLERANCE_MM = 0.01
PARALLEL = 0.99999
FLOOR_AREA_TOLERANCE_MM2 = 0.001


def sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def norm(v):
    return math.sqrt(dot(v, v))


def cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def radial_part(v, axis):
    """The component of v perpendicular to the unit vector axis."""
    along = dot(v, axis)
    return (v[0] - axis[0] * along, v[1] - axis[1] * along, v[2] - axis[2] * along)


def radial_distance(v, axis):
    return norm(radial_part(v, axis))


def round_mm(value):
    return round(value, 3)


@dataclass(frozen=True)
class Circle:
    center: tuple
    axis: tuple
    radius: float


@dataclass(frozen=True)
class Cylinder:
    origin: tuple
    axis: tuple
    radius: float


@dataclass(frozen=True)
class PlanarFace:
    normal: tuple
    area_mm2: float


@dataclass(frozen=True)
class BoreEdge:
    circle: Circle
    planar_neighbours: tuple


def is_hole_entrance(rim, outward, wall, wall_point, wall_normal):
    """True when rim is where a cylindrical hole wall meets a flat face whose outward
    normal is outward: coaxial, same radius, the wall running inward and concave."""
    from_rim = sub(wall_point, rim.center)
    return (abs(dot(outward, wall.axis)) >= PARALLEL
            and abs(rim.radius - wall.radius) <= TOLERANCE_MM
            and radial_distance(sub(rim.center, wall.origin), wall.axis) <= TOLERANCE_MM
            and dot(from_rim, outward) < -1e-5
            and dot(wall_normal, radial_part(from_rim, outward)) < 0)


def bore_end(rim, outward, edges):
    """(depth, can_deepen) of the nearest coaxial edge of the same radius below the rim.
    can_deepen means the bore ends in a flat full-disc floor facing the opening."""
    end = None
    for edge in edges:
        circle = edge.circle
        if (abs(circle.radius - rim.radius) > TOLERANCE_MM
                or abs(dot(circle.axis, outward)) < PARALLEL
                or radial_distance(sub(circle.center, rim.center), outward) > TOLERANCE_MM):
            continue
        depth = dot(sub(rim.center, circle.center), outward)
        if depth <= TOLERANCE_MM or (end is not None and depth >= end[0] - TOLERANCE_MM):
            continue
        full_disc = math.pi * rim.radius ** 2
        flat_floor = any(dot(face.normal, outward) > PARALLEL
                         and abs(face.area_mm2 - full_disc) < FLOOR_AREA_TOLERANCE_MM2
                         for face in edge.planar_neighbours)
        end = (depth, flat_floor)
    return end


def expected_cut_volume_mm3(seat_diameter, seat_depth, hole_diameter, bore_depth):
    """Material a seat cut removes: the seat cylinder minus the part of the bore it overlaps."""
    return math.pi / 4 * (seat_diameter ** 2 * seat_depth
                          - hole_diameter ** 2 * min(seat_depth, bore_depth))


def cut_volume_matches(removed_mm3, expected_mm3):
    return abs(removed_mm3 - expected_mm3) <= max(0.005, expected_mm3 * 0.0005)


def cut_direction(sketch_x, sketch_y, inward):
    """+1 when the sketch normal points into the body, else -1."""
    return 1 if dot(cross(sketch_x, sketch_y), inward) > 0 else -1


def is_floor(point, normal, center, outward, depth):
    """True for a flat face facing the opening at depth below center."""
    below = -dot(sub(point, center), outward)
    return dot(normal, outward) > PARALLEL and abs(below - depth) <= TOLERANCE_MM
