# ABOUTME: Cuts planned insert seats into Fusion bodies as editable sketches, extrusions and chamfers,
# ABOUTME: checking that each cut touched one body, removed the expected material and left a floor.
import json

import adsk.core
import adsk.fusion

from .geometry import (TOLERANCE_MM, cut_direction, cut_volume_matches, expected_cut_volume_mm3, is_floor,
                       norm, sub)
from .messages import SeatError, message
from .openings import MM_PER_CM, circle_of, entrance_faces, mm_point, normal_at
from .seats import SEAT_ATTRIBUTE_GROUP, SEAT_ATTRIBUTE_NAME, SEAT_NAME_PREFIX

MM3_PER_CM3 = 1000


def cut_seats(design, plan):
    """Cuts every seat in plan and returns the extrude features, in plan order."""
    features = []
    for seat in plan.seats:
        try:
            features.append(cut_seat(design, seat))
        except SeatError as error:
            raise SeatError(message('hole_prefix', ordinal=seat.opening.ordinal,
                                    body=seat.opening.body_name, reason=str(error))) from None
    return features


def cut_seat(design, seat):
    rim = resolve_rim(design, seat.opening.rim_token)
    body = rim.body
    component = body.parentComponent
    plane, _ = entrance_faces(rim)

    sketch = component.sketches.addWithoutEdges(plane)
    sketch.name = message('profile_name', name=seat.name)
    seat_circle(sketch, rim, seat.diameter)

    outward = seat.opening.outward
    inward = (-outward[0], -outward[1], -outward[2])
    direction = (adsk.fusion.ExtentDirections.PositiveExtentDirection
                 if cut_direction(vector(sketch.xDirection), vector(sketch.yDirection), inward) > 0
                 else adsk.fusion.ExtentDirections.NegativeExtentDirection)
    extrudes = component.features.extrudeFeatures
    cut = extrudes.createInput(sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation)
    cut.setOneSideExtent(adsk.fusion.DistanceExtentDefinition.create(
        adsk.core.ValueInput.createByString(f'{seat.depth} mm')), direction)
    cut.participantBodies = [body]
    volume_before = body.volume
    feature = extrudes.add(cut)
    feature.name = SEAT_NAME_PREFIX + seat.name
    feature.attributes.add(SEAT_ATTRIBUTE_GROUP, SEAT_ATTRIBUTE_NAME, json.dumps({
        'thread': seat.insert.thread,
        'insert': seat.insert.product_name,
        'diameter_mm': seat.diameter,
        'depth_mm': seat.depth,
        'chamfer_mm': seat.chamfer,
    }))
    check_cut(feature, body, volume_before, seat)
    if seat.chamfer:
        chamfer_mouth(component, feature, seat)
    return feature


def chamfer_mouth(component, feature, seat):
    """Chamfers the seat's mouth, the edge where the seat wall meets the face the hole opens onto."""
    mouths = [edge for face in feature.sideFaces for edge in face.edges
              if is_at(circle_of(edge), seat.opening.center)]
    if len(mouths) != 1:
        raise SeatError(message('chamfer_failed'))
    edges = adsk.core.ObjectCollection.create()
    edges.add(mouths[0])
    chamfers = component.features.chamferFeatures
    chamfer_input = chamfers.createInput2()
    chamfer_input.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
        edges, adsk.core.ValueInput.createByString(f'{seat.chamfer} mm'), False)
    try:
        chamfer = chamfers.add(chamfer_input)
    except RuntimeError:
        chamfer = None
    if chamfer is None:
        raise SeatError(message('chamfer_failed'))
    chamfer.name = SEAT_NAME_PREFIX + message('chamfer_name', name=seat.name)
    return chamfer


def is_at(circle, center_mm):
    return circle is not None and norm(sub(circle.center, center_mm)) <= TOLERANCE_MM


def resolve_rim(design, rim_token):
    found = design.findEntityByToken(rim_token)
    rim = adsk.fusion.BRepEdge.cast(found[0]) if len(found) == 1 else None
    if rim is None or entrance_faces(rim) is None:
        raise SeatError(message('opening_changed'))
    return rim


def seat_circle(sketch, rim, diameter_mm):
    """Draws the seat circle on the centre of the projected rim, sized by a diameter dimension."""
    projected = sketch.project2([rim], True)
    projection = adsk.fusion.SketchCircle.cast(projected[0]) if len(projected) == 1 else None
    if projection is None:
        raise SeatError(message('profile_unconstrained'))
    projection.isConstruction = True
    circle = sketch.sketchCurves.sketchCircles.addByCenterRadius(
        projection.centerSketchPoint, diameter_mm / MM_PER_CM / 2)
    center = circle.centerSketchPoint.geometry
    dimension = sketch.sketchDimensions.addDiameterDimension(
        circle, adsk.core.Point3D.create(center.x + circle.radius, center.y + circle.radius, 0))
    dimension.parameter.expression = f'{diameter_mm} mm'
    if not circle.isFullyConstrained:
        raise SeatError(message('profile_unconstrained'))
    return circle


def vector(direction):
    return (direction.x, direction.y, direction.z)


def check_cut(feature, body, volume_before_cm3, seat):
    opening = seat.opening
    if feature.bodies.count != 1 or not feature.bodies.item(0) == body:
        raise SeatError(message('cut_other_bodies'))
    removed_mm3 = (volume_before_cm3 - body.volume) * MM3_PER_CM3
    expected_mm3 = expected_cut_volume_mm3(seat.diameter, seat.depth, opening.diameter, opening.bore_depth)
    if not cut_volume_matches(removed_mm3, expected_mm3):
        raise SeatError(message('cut_intersects'))
    if not any(is_floor(mm_point(face.pointOnFace), normal_at(face, face.pointOnFace),
                        opening.center, opening.outward, seat.depth)
               for face in feature.endFaces):
        raise SeatError(message('cut_no_floor'))
