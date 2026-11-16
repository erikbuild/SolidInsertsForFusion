# ABOUTME: One-shot Fusion script that checks the geometry API behaviours the SolidInserts
# ABOUTME: port relies on, logging one FINDING line per behaviour to the Text Commands palette.
import importlib
import math
import os
import sys
import traceback

import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import support  # noqa: E402
importlib.reload(support)

TAG = 'SolidInsertsSpike'


def log(app, message):
    app.log('[{}] {}'.format(TAG, message))


def finding(app, number, action):
    try:
        action()
    except Exception:
        log(app, 'FINDING {} RAISED: {}'.format(number, traceback.format_exc()))


def planar_face_at(body, z_mm, area_below_mm2=None):
    for face in body.faces:
        if face.geometry.surfaceType != adsk.core.SurfaceTypes.PlaneSurfaceType:
            continue
        if abs(face.pointOnFace.z - support.cm(z_mm)) > support.EPSILON_CM:
            continue
        if area_below_mm2 is None or face.area * 100 < area_below_mm2:
            return face
    raise LookupError('No planar face at z={}'.format(z_mm))


def straight_edge(body, y_cm, z_cm):
    for edge in body.edges:
        line = adsk.core.Line3D.cast(edge.geometry)
        if line and all(abs(p.y - y_cm) < support.EPSILON_CM and abs(p.z - z_cm) < support.EPSILON_CM
                        for p in (line.startPoint, line.endPoint)):
            return edge
    raise LookupError('No straight edge at y={} z={}'.format(y_cm, z_cm))


def probe_moved_component_cuts(app, root):
    """Cuts Ø3 holes into a component placed away from the origin three ways and logs which
    ones create a hole, to show which space Fusion evaluates component cuts in."""
    occurrence = root.occurrences.addNewComponent(support.place(0, 80, 0))
    probe = occurrence.component
    probe.name = 'Probe'
    block = support.box(probe, 0, 0, 0, 20, 10, 10, 'Probe')
    box_min = block.boundingBox.minPoint
    log(app, 'FINDING 0a: native probe body bounding box min = ({:.3f}, {:.3f}, {:.3f}) cm, '
             'assemblyContext is None: {}'.format(box_min.x, box_min.y, box_min.z, block.assemblyContext is None))
    attempts = [
        (4, 'native body, through all', [block], None),
        (10, 'occurrence proxy body, through all', [block.createForAssemblyContext(occurrence)], None),
        (16, 'native body, 15 mm distance', [block], support.cm(15)),
    ]
    for x, label, bodies, distance_cm in attempts:
        sketch = probe.sketches.add(support.plane_at(probe, 10))
        origin = sketch.sketchToModelSpace(adsk.core.Point3D.create(0, 0, 0))
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(support.cm(x), support.cm(5), 0), support.cm(3) / 2)
        try:
            support.extrude(probe, sketch.profiles.item(0), adsk.fusion.FeatureOperations.CutFeatureOperation,
                            distance_cm, adsk.fusion.ExtentDirections.NegativeExtentDirection, bodies)
            try:
                support.rim(block, (x, 5, 10), 3)
                outcome = 'hole created'
            except LookupError:
                outcome = 'feature added but NO hole in the native body'
        except Exception as error:
            outcome = 'raised: {}'.format(str(error).splitlines()[0])
        log(app, 'FINDING 0b ({}): sketch origin in model space = ({:.3f}, {:.3f}, {:.3f}) cm -> {}'.format(
            label, origin.x, origin.y, origin.z, outcome))


def probe_occurrence_move(app, design):
    """Moves an occurrence with transform2 after building its body, then adds a feature
    elsewhere, logging whether the move survives that recompute."""
    root = design.rootComponent
    occurrence = root.occurrences.addNewComponent(support.place(0, 0, 0))
    occurrence.component.name = 'MovedProbe'
    support.box(occurrence.component, 200, 0, 0, 210, 10, 10, 'MovedProbe')
    occurrence.transform2 = support.place(0, 30, 0)
    log(app, 'FINDING 0c: after transform2 translation y = {:.3f} cm, hasPendingSnapshot = {}'.format(
        occurrence.transform2.translation.y, design.snapshots.hasPendingSnapshot))
    support.box(root, 220, 0, 0, 230, 10, 10, 'AfterMove')
    log(app, 'FINDING 0c: after a root feature translation y = {:.3f} cm, hasPendingSnapshot = {}'.format(
        occurrence.transform2.translation.y, design.snapshots.hasPendingSnapshot))


def run(context):
    app = adsk.core.Application.get()
    try:
        design = support.new_design(app)
        root = design.rootComponent

        plate = support.box(root, 0, 0, 0, 42, 30, 18, 'Plate')
        support.hole(plate, 8, 8, 18, 3, 7)
        support.hole(plate, 20, 8, 18, 3, 7)
        support.hole(plate, 35, 20, 18, 3)

        finding(app, 0, lambda: probe_moved_component_cuts(app, root))
        finding(app, 0, lambda: probe_occurrence_move(app, design))

        # A through-all cut finds no body in a component placed away from the origin, so the
        # through hole is a distance cut deeper than the 10 mm block.
        bracket_a = root.occurrences.addNewComponent(support.place(0, 50, 0))
        bracket = bracket_a.component
        bracket.name = 'Bracket'
        block = support.box(bracket, 0, 0, 0, 20, 10, 10, 'Block')
        support.hole(block, 10, 5, 10, 3, 15)
        bracket_b = root.occurrences.addExistingComponent(bracket, support.place(30, 50, 0))

        rim_a = support.rim(plate, (8, 8, 18), 3)
        rim_b = support.rim(plate, (20, 8, 18), 3)
        token_b = rim_b.entityToken
        plate_before = plate.volume
        feature, sketch, facts = support.cut_circle_seat(
            rim_a, 4, 6.7, 'SolidInserts · Insert M3 × 5.7')
        removed_mm3 = (plate_before - plate.volume) * 1000
        expected_mm3 = math.pi / 4 * (4 ** 2 - 3 ** 2) * 6.7

        def f1():
            log(app, 'FINDING 1 (sketch): {}'.format(facts))

        def f2():
            log(app, 'FINDING 2 (direction): sketch normal · outward = {:.6f}; plate volume dropped by {:.6f} mm3 '
                     '(plate.isValid={})'.format(facts['sketch_normal_dot_outward'], removed_mm3, plate.isValid))

        def f3():
            floor = planar_face_at(plate, 11, area_below_mm2=10)
            log(app, 'FINDING 3 (precision): removed - analytic = {:.9f} mm3; floor area - pi r^2 = {:.9f} mm2'.format(
                removed_mm3 - expected_mm3, floor.area * 100 - math.pi * 1.5 ** 2))

        def f4():
            found = design.findEntityByToken(token_b)
            log(app, 'FINDING 4 (tokens): old rim B isValid={}; findEntityByToken -> {} entities: {}'.format(
                rim_b.isValid, len(found),
                ['{} r={:.4f}cm'.format(e.objectType, adsk.core.Circle3D.cast(e.geometry).radius)
                 if adsk.fusion.BRepEdge.cast(e) else e.objectType for e in found]))

        def f5():
            sketch.name = 'Profile Insert M3 × 5.7'
            log(app, 'FINDING 5 (names): feature={!r} same={} sketch={!r} same={}'.format(
                feature.name, feature.name == 'SolidInserts · Insert M3 × 5.7',
                sketch.name, sketch.name == 'Profile Insert M3 × 5.7'))

        def f6():
            proxy_body = bracket_a.bRepBodies.item(0)
            proxy_body_b = bracket_b.bRepBodies.item(0)
            native_body = proxy_body.nativeObject
            log(app, 'FINDING 6 (placement): occurrence A translation y = {:.3f} cm; proxy body min y = {:.3f} cm; '
                     'native body min y = {:.3f} cm'.format(
                         bracket_a.transform2.translation.y, proxy_body.boundingBox.minPoint.y,
                         native_body.boundingBox.minPoint.y))
            outer_native = straight_edge(native_body, 0.0, 1.0)
            outer_proxy = straight_edge(proxy_body, 5.0, 1.0)
            measure = app.measureManager

            def distance(label, point, edge):
                try:
                    return '{} = {:.6f} cm'.format(label, measure.measureMinimumDistance(point, edge).value)
                except RuntimeError as error:
                    return '{} raised: {}'.format(label, str(error).splitlines()[0])

            log(app, 'FINDING 6a (measure): {}; {}'.format(
                distance('native point(1,0.5,1)->native edge', adsk.core.Point3D.create(1.0, 0.5, 1.0), outer_native),
                distance('world point(1,5.5,1)->proxy edge', adsk.core.Point3D.create(1.0, 5.5, 1.0), outer_proxy)))
            before_a, before_b = proxy_body.volume, proxy_body_b.volume
            timeline_before = design.timeline.count
            proxy_rim = support.rim(proxy_body, (10, 55, 10), 3)
            bracket_feature, _, bracket_facts = support.cut_circle_seat(
                proxy_rim, 4, 6.7, 'SolidInserts · Insert M3 × 5.7')
            log(app, 'FINDING 6b (component cut): facts={} feature parent={} timeline +{}; '
                     'occurrence A dropped {:.6f} mm3, occurrence B dropped {:.6f} mm3 (expected {:.6f})'.format(
                         bracket_facts, bracket_feature.parentComponent.name, design.timeline.count - timeline_before,
                         (before_a - bracket_a.bRepBodies.item(0).volume) * 1000,
                         (before_b - bracket_b.bRepBodies.item(0).volume) * 1000, expected_mm3))

        def f7():
            end_faces = feature.endFaces
            ends = []
            for face in (end_faces or []):
                _, normal = face.evaluator.getNormalAtPoint(face.pointOnFace)
                ends.append('{} depth={:.6f}mm normal=({:.3f},{:.3f},{:.3f})'.format(
                    face.geometry.surfaceType, 18 - face.pointOnFace.z * 10, normal.x, normal.y, normal.z))
            log(app, 'FINDING 7a (result): bodies.count={} first==plate:{}; endFaces={}'.format(
                feature.bodies.count, feature.bodies.item(0) == plate if feature.bodies.count else None,
                ends if end_faces is not None else None))
            through_rim = support.rim(plate, (35, 20, 18), 3)
            through_feature, _, _ = support.cut_circle_seat(through_rim, 4, 20, 'Break-through')
            through_ends = through_feature.endFaces
            log(app, 'FINDING 7b (break-through): endFaces is None={} count={} bodies.count={}'.format(
                through_ends is None, through_ends.count if through_ends is not None else '-',
                through_feature.bodies.count))

        def f8():
            feature.attributes.add('SolidInserts', 'seat', '{}')
            found = design.findAttributes('SolidInserts', 'seat')
            seat_rim = support.rim(plate, (8, 8, 18), 4)
            wall = next(f for f in seat_rim.faces
                        if f.geometry.surfaceType == adsk.core.SurfaceTypes.CylinderSurfaceType)
            log(app, 'FINDING 8 (attributes): found={} parent type={} parent==feature:{}; '
                     'sideFaces contains seat wall: {}'.format(
                         len(found), found[0].parent.objectType if found else '-',
                         found[0].parent == feature if found else '-',
                         any(side == wall for side in feature.sideFaces)))

        for number, action in enumerate([f1, f2, f3, f4, f5, f6, f7, f8], start=1):
            finding(app, number, action)
        log(app, '==== spike done ====')
    except Exception:
        log(app, 'SPIKE FAILED: {}'.format(traceback.format_exc()))
