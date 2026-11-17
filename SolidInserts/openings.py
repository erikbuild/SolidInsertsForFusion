# ABOUTME: Reads hole openings from Fusion geometry: checks that each selected rim is a hole
# ABOUTME: entrance and measures its centre, direction, bore depth and clearance in millimetres.
import adsk.core
import adsk.fusion

from .geometry import BoreEdge, Circle, Cylinder, PlanarFace, bore_end, is_hole_entrance
from .messages import SeatError, message
from .seats import SEAT_ATTRIBUTE_GROUP, SEAT_ATTRIBUTE_NAME, Opening

MM_PER_CM = 10
MM2_PER_CM2 = 100


class EntityKeys:
    """Short keys for API objects, matched with == because every API call returns a new
    Python object for the same entity."""

    def __init__(self, prefix):
        self.prefix = prefix
        self.known = []

    def key(self, entity):
        for index, known in enumerate(self.known):
            if known == entity:
                return '{}{}'.format(self.prefix, index)
        self.known.append(entity)
        return '{}{}'.format(self.prefix, len(self.known) - 1)


def read_openings(design, rims):
    """(openings, errors) for the selected rims: one Opening, or one message, per rim."""
    if design.designType != adsk.fusion.DesignTypes.ParametricDesignType:
        return [], [message('needs_history')]
    bodies = EntityKeys('body')
    planes = EntityKeys('face')
    seat_walls = seat_side_faces(design)
    openings = []
    errors = []
    for ordinal, rim in enumerate(rims, start=1):
        native_rim = native(rim)
        try:
            openings.append(read_opening(rim, native_rim, ordinal, bodies, planes, seat_walls))
        except SeatError as error:
            errors.append(message('hole_prefix', ordinal=ordinal, body=native_rim.body.name, reason=str(error)))
    return openings, errors


def read_opening(rim, native_rim, ordinal, bodies, planes, seat_walls):
    faces = entrance_faces(native_rim)
    circle = circle_of(native_rim)
    if faces is None or circle is None:
        raise SeatError(message('not_entrance'))
    plane, wall = faces
    outward = normal_at(plane, plane.pointOnFace)
    if not is_hole_entrance(circle, outward, cylinder_of(wall), mm_point(wall.pointOnFace),
                            normal_at(wall, wall.pointOnFace)):
        raise SeatError(message('not_entrance'))
    if in_linked_component(rim):
        raise SeatError(message('linked_component'))
    if any(wall == side for side in seat_walls):
        raise SeatError(message('existing_seat'))
    end = bore_end(circle, outward, bore_edges(wall))
    if end is None:
        raise SeatError(message('bore_depth_unknown'))
    return Opening(
        ordinal=ordinal,
        body_key=bodies.key(native_rim.body),
        body_name=native_rim.body.name,
        plane_key=planes.key(plane),
        center=circle.center,
        outward=outward,
        diameter=2 * circle.radius,
        bore_depth=end[0],
        can_deepen=end[1],
        clearance=clearance_mm(rim),
        rim_token=native_rim.entityToken,
    )


def native(entity):
    """The entity in its own component's space. A root-component entity is already native."""
    return entity.nativeObject or entity


def mm_point(point):
    return (point.x * MM_PER_CM, point.y * MM_PER_CM, point.z * MM_PER_CM)


def unit(vector):
    length = vector.length
    return (vector.x / length, vector.y / length, vector.z / length)


def normal_at(face, point):
    """The face normal at point, pointing out of the body."""
    _, normal = face.evaluator.getNormalAtPoint(point)
    return unit(normal)


def surface_type(face):
    return face.geometry.surfaceType


def entrance_faces(rim):
    """(flat face, cylindrical wall) meeting at rim, or None when the rim joins other faces."""
    flat = [face for face in rim.faces if surface_type(face) == adsk.core.SurfaceTypes.PlaneSurfaceType]
    walls = [face for face in rim.faces if surface_type(face) == adsk.core.SurfaceTypes.CylinderSurfaceType]
    if len(flat) == 1 and len(walls) == 1:
        return flat[0], walls[0]
    return None


def circle_of(edge):
    circle = adsk.core.Circle3D.cast(edge.geometry)
    if circle is None:
        return None
    return Circle(mm_point(circle.center), unit(circle.normal), circle.radius * MM_PER_CM)


def cylinder_of(face):
    cylinder = adsk.core.Cylinder.cast(face.geometry)
    return Cylinder(mm_point(cylinder.origin), unit(cylinder.axis), cylinder.radius * MM_PER_CM)


def in_linked_component(rim):
    occurrence = rim.assemblyContext
    while occurrence:
        if occurrence.isReferencedComponent:
            return True
        occurrence = occurrence.assemblyContext
    return False


def seat_side_faces(design):
    """Side faces of every cut SolidInserts made, found by the attribute on each feature."""
    faces = []
    for attribute in design.findAttributes(SEAT_ATTRIBUTE_GROUP, SEAT_ATTRIBUTE_NAME):
        feature = adsk.fusion.ExtrudeFeature.cast(attribute.parent)
        if feature:
            faces.extend(feature.sideFaces)
    return faces


def bore_edges(wall):
    """The circular edges of the hole wall, each with its flat neighbouring faces."""
    edges = []
    for edge in wall.edges:
        circle = circle_of(edge)
        if circle is None:
            continue
        flat = tuple(PlanarFace(normal_at(face, face.pointOnFace), face.area * MM2_PER_CM2)
                     for face in edge.faces
                     if surface_type(face) == adsk.core.SurfaceTypes.PlaneSurfaceType)
        edges.append(BoreEdge(circle, flat))
    return edges


def clearance_mm(rim):
    """Nearest distance from the rim centre to the other edges of the entrance face. It is
    measured on the selected rim itself, because Fusion cannot measure the native edges of a
    component that is not the root; a distance is the same in either space. Each edge is
    measured from the rim edge and the rim radius added, which is exact for edges of the face
    around the hole; Fusion measures a point against a straight edge as if the edge ran on
    past its ends."""
    plane, wall = entrance_faces(rim)
    radius_mm = adsk.core.Circle3D.cast(rim.geometry).radius * MM_PER_CM
    wall_edges = list(wall.edges)
    measure = adsk.core.Application.get().measureManager
    distances = []
    for edge in plane.edges:
        if any(edge == other for other in wall_edges):
            continue
        try:
            distances.append(measure.measureMinimumDistance(rim, edge).value * MM_PER_CM + radius_mm)
        except RuntimeError:
            raise SeatError(message('clearance_unknown'))
    if not distances:
        raise SeatError(message('clearance_unknown'))
    return min(distances)
