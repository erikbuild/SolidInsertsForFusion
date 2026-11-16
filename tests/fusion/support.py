# ABOUTME: Shared helpers for SolidInserts in-Fusion scripts: PASS/FAIL logging,
# ABOUTME: millimetre geometry builders, and a fresh loader for the add-in code under test.
import importlib
import importlib.machinery
import importlib.util
import os
import sys

import adsk.core
import adsk.fusion

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ADDIN_DIR = os.path.join(REPO_ROOT, 'SolidInserts')
EPSILON_CM = 1e-4

_results = []


def check(condition, label):
    _results.append((bool(condition), label))


def report(app, tag):
    failures = [label for ok, label in _results if not ok]
    for ok, label in _results:
        app.log('[{}] {} {}'.format(tag, 'PASS' if ok else 'FAIL', label))
    app.log('[{}] ==== {} passed, {} failed ===='.format(
        tag, len(_results) - len(failures), len(failures)))
    _results.clear()


def cm(mm):
    return mm / 10.0


def new_design(app):
    """Opens a new design document with design history turned on."""
    app.documents.add(adsk.core.DocumentTypes.FusionDesignDocumentType)
    design = adsk.fusion.Design.cast(app.activeProduct)
    design.designType = adsk.fusion.DesignTypes.ParametricDesignType
    return design


def plane_at(component, z_mm):
    """The component's XY plane, offset to height z_mm."""
    if abs(z_mm) < 1e-9:
        return component.xYConstructionPlane
    planes = component.constructionPlanes
    plane_input = planes.createInput()
    plane_input.setByOffset(component.xYConstructionPlane,
                            adsk.core.ValueInput.createByReal(cm(z_mm)))
    return planes.add(plane_input)


def extrude(component, profile, operation, distance_cm, direction, bodies=None):
    extrudes = component.features.extrudeFeatures
    extrude_input = extrudes.createInput(profile, operation)
    if distance_cm is None:
        extent = adsk.fusion.ThroughAllExtentDefinition.create()
    else:
        extent = adsk.fusion.DistanceExtentDefinition.create(
            adsk.core.ValueInput.createByReal(distance_cm))
    extrude_input.setOneSideExtent(extent, direction)
    if bodies is not None:
        extrude_input.participantBodies = bodies
    return extrudes.add(extrude_input)


def box(component, x0, y0, z0, x1, y1, z1, name):
    """Creates a new body spanning the given millimetre corners."""
    sketch = component.sketches.add(plane_at(component, z0))
    sketch.sketchCurves.sketchLines.addTwoPointRectangle(
        adsk.core.Point3D.create(cm(x0), cm(y0), 0),
        adsk.core.Point3D.create(cm(x1), cm(y1), 0))
    feature = extrude(component, sketch.profiles.item(0),
                      adsk.fusion.FeatureOperations.NewBodyFeatureOperation,
                      cm(z1 - z0), adsk.fusion.ExtentDirections.PositiveExtentDirection)
    body = feature.bodies.item(0)
    body.name = name
    return body


def hole(body, x, y, top_z, diameter, depth=None):
    """Cuts a flat-bottomed blind hole, or a through hole when depth is None,
    straight down from top_z."""
    component = body.parentComponent
    sketch = component.sketches.add(plane_at(component, top_z))
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(x), cm(y), 0), cm(diameter) / 2)
    extrude(component, sketch.profiles.item(0),
            adsk.fusion.FeatureOperations.CutFeatureOperation,
            None if depth is None else cm(depth),
            adsk.fusion.ExtentDirections.NegativeExtentDirection, [body])


def rim(body, center_mm, diameter_mm):
    """The circular edge of body with this centre and diameter (proxy-aware)."""
    target = adsk.core.Point3D.create(*(cm(value) for value in center_mm))
    for edge in body.edges:
        circle = adsk.core.Circle3D.cast(edge.geometry)
        if circle and circle.center.distanceTo(target) < EPSILON_CM \
                and abs(circle.radius - cm(diameter_mm) / 2) < EPSILON_CM:
            return edge
    raise LookupError('No Ø{} rim at {} on {}'.format(diameter_mm, center_mm, body.name))


def boss(body, x, y, base_z, diameter, height):
    """Joins a cylinder standing on base_z to body."""
    component = body.parentComponent
    sketch = component.sketches.add(plane_at(component, base_z))
    sketch.sketchCurves.sketchCircles.addByCenterRadius(
        adsk.core.Point3D.create(cm(x), cm(y), 0), cm(diameter) / 2)
    extrude(component, sketch.profiles.item(0), adsk.fusion.FeatureOperations.JoinFeatureOperation,
            cm(height), adsk.fusion.ExtentDirections.PositiveExtentDirection, [body])


def chamfer(edge, distance_mm):
    chamfers = edge.body.parentComponent.features.chamferFeatures
    chamfer_input = chamfers.createInput2()
    edges = adsk.core.ObjectCollection.create()
    edges.add(edge)
    chamfer_input.chamferEdgeSets.addEqualDistanceChamferEdgeSet(
        edges, adsk.core.ValueInput.createByReal(cm(distance_mm)), False)
    chamfers.add(chamfer_input)


def side_bore(body, x, z, diameter):
    """Cuts a bore along Y through the whole body, centred at (x, z)."""
    component = body.parentComponent
    sketch = component.sketches.add(component.xZConstructionPlane)
    center = sketch.modelToSketchSpace(adsk.core.Point3D.create(cm(x), 0, cm(z)))
    sketch.sketchCurves.sketchCircles.addByCenterRadius(center, cm(diameter) / 2)
    extrudes = component.features.extrudeFeatures
    bore_input = extrudes.createInput(sketch.profiles.item(0),
                                      adsk.fusion.FeatureOperations.CutFeatureOperation)
    bore_input.setSymmetricExtent(adsk.core.ValueInput.createByReal(100.0), True)
    bore_input.participantBodies = [body]
    extrudes.add(bore_input)


def holes_through(body, top_z, diameter, centers):
    """Cuts many through holes from one sketch."""
    component = body.parentComponent
    sketch = component.sketches.add(plane_at(component, top_z))
    for x, y in centers:
        sketch.sketchCurves.sketchCircles.addByCenterRadius(
            adsk.core.Point3D.create(cm(x), cm(y), 0), cm(diameter) / 2)
    profiles = adsk.core.ObjectCollection.create()
    for profile in sketch.profiles:
        profiles.add(profile)
    extrude(component, profiles, adsk.fusion.FeatureOperations.CutFeatureOperation, None,
            adsk.fusion.ExtentDirections.NegativeExtentDirection, [body])


def straight_edge(body, y_mm, z_mm):
    """A straight edge of body lying along X at height z_mm and depth y_mm."""
    for edge in body.edges:
        line = adsk.core.Line3D.cast(edge.geometry)
        if line and all(abs(p.y - cm(y_mm)) < EPSILON_CM and abs(p.z - cm(z_mm)) < EPSILON_CM
                        for p in (line.startPoint, line.endPoint)):
            return edge
    raise LookupError('No straight edge at y={} z={} on {}'.format(y_mm, z_mm, body.name))


class Fixture:
    """Named rims, bodies and occurrences of the integration fixture."""

    def __init__(self):
        self.rims = {}
        self.bodies = {}
        self.occurrences = {}


def place(x_mm, y_mm, z_mm):
    matrix = adsk.core.Matrix3D.create()
    matrix.translation = adsk.core.Vector3D.create(cm(x_mm), cm(y_mm), cm(z_mm))
    return matrix


def build_fixture(design):
    """Builds every body the integration tests use. Positions are millimetres."""
    root = design.rootComponent
    fixture = Fixture()

    plate = box(root, 0, 0, 0, 60, 40, 18, 'Plate')
    hole(plate, 10, 10, 18, 3, 7)
    hole(plate, 30, 10, 18, 4)
    hole(plate, 10, 30, 18, 3.2)
    hole(plate, 25, 30, 18, 3)
    hole(plate, 2.5, 20, 18, 3)
    hole(plate, 40, 20, 18, 3)
    hole(plate, 43.5, 20, 18, 3)
    hole(plate, 50, 10, 18, 3, 4)
    boss(plate, 50, 30, 18, 3, 3)
    chamfer(rim(plate, (25, 30, 18), 3), 0.5)
    fixture.bodies['Plate'] = plate
    fixture.rims.update({
        'h1': rim(plate, (10, 10, 18), 3),
        'h2': rim(plate, (30, 10, 18), 4),
        'h2_bottom': rim(plate, (30, 10, 0), 4),
        'h3': rim(plate, (10, 30, 18), 3.2),
        'h4': rim(plate, (25, 30, 18), 4),
        'h5': rim(plate, (2.5, 20, 18), 3),
        'h6': rim(plate, (40, 20, 18), 3),
        'h7': rim(plate, (43.5, 20, 18), 3),
        'h8': rim(plate, (50, 10, 18), 3),
        'boss': rim(plate, (50, 30, 21), 3),
        'straight': straight_edge(plate, 0, 18),
    })

    thin = box(root, 70, 0, 0, 90, 20, 5, 'ThinPlate')
    hole(thin, 80, 10, 5, 3)
    fixture.bodies['ThinPlate'] = thin
    fixture.rims['thin'] = rim(thin, (80, 10, 5), 3)

    cavity = box(root, 100, 0, 0, 120, 20, 18, 'CavityBlock')
    hole(cavity, 110, 10, 18, 3, 12)
    side_bore(cavity, 112.8, 14, 2)
    fixture.bodies['CavityBlock'] = cavity
    fixture.rims['cavity'] = rim(cavity, (110, 10, 18), 3)

    # A through-all cut finds no body in a component placed away from the origin, so the
    # through hole is a distance cut deeper than the 10 mm block.
    bracket_a = root.occurrences.addNewComponent(place(0, 60, 0))
    bracket = bracket_a.component
    bracket.name = 'Bracket'
    bracket_body = box(bracket, 0, 0, 0, 20, 10, 10, 'Bracket')
    hole(bracket_body, 10, 5, 10, 3, 15)
    bracket_b = root.occurrences.addExistingComponent(bracket, place(30, 60, 0))
    fixture.occurrences.update({'bracket_a': bracket_a, 'bracket_b': bracket_b})
    fixture.rims['bracket_a'] = rim(bracket_a.bRepBodies.item(0), (10, 65, 10), 3)
    fixture.rims['bracket_b'] = rim(bracket_b.bRepBodies.item(0), (40, 65, 10), 3)

    perforated = box(root, 0, 100, 0, 100, 200, 10, 'Perforated')
    grid = [(12.5 + 15 * i, 112.5 + 15 * j) for j in range(6) for i in range(6)]
    holes_through(perforated, 10, 3, grid)
    fixture.bodies['Perforated'] = perforated
    fixture.rims['grid'] = [rim(perforated, (x, y, 10), 3) for x, y in grid]
    return fixture


def cut_circle_seat(rim_edge, diameter_mm, depth_mm, name):
    """Sketches a circle centred on the linked projection of the rim and cuts it
    into the rim's body. Returns (feature, sketch, facts) for spike logging."""
    native = rim_edge.nativeObject or rim_edge
    body = native.body
    component = body.parentComponent
    face = next(f for f in native.faces
                if f.geometry.surfaceType == adsk.core.SurfaceTypes.PlaneSurfaceType)
    sketch = component.sketches.addWithoutEdges(face)
    projected = sketch.project2([native], True)
    projection = adsk.fusion.SketchCircle.cast(projected[0])
    projection.isConstruction = True
    seat = sketch.sketchCurves.sketchCircles.addByCenterRadius(
        projection.centerSketchPoint, cm(diameter_mm) / 2)
    center = seat.centerSketchPoint.geometry
    dimension = sketch.sketchDimensions.addDiameterDimension(
        seat, adsk.core.Point3D.create(center.x + 0.5, center.y + 0.5, 0))
    dimension.parameter.expression = '{} mm'.format(diameter_mm)
    _, outward = face.evaluator.getNormalAtPoint(face.pointOnFace)
    alignment = sketch.xDirection.crossProduct(sketch.yDirection).dotProduct(outward)
    direction = (adsk.fusion.ExtentDirections.NegativeExtentDirection if alignment > 0
                 else adsk.fusion.ExtentDirections.PositiveExtentDirection)
    facts = {
        'projected_count': len(projected),
        'projected_type': projected[0].objectType,
        'projection_is_construction': projection.isConstruction,
        'seat_fully_constrained': seat.isFullyConstrained,
        'profile_count': sketch.profiles.count,
        'sketch_normal_dot_outward': alignment,
    }
    feature = extrude(component, sketch.profiles.item(0),
                      adsk.fusion.FeatureOperations.CutFeatureOperation,
                      cm(depth_mm), direction, [body])
    feature.name = name
    return feature, sketch, facts


def load_addin_package(name='solidinserts_under_test'):
    """Imports SolidInserts/ fresh under its own package name, so a running copy
    of the add-in never shadows the code under test."""
    for key in [k for k in sys.modules if k == name or k.startswith(name + '.')]:
        del sys.modules[key]
    spec = importlib.machinery.ModuleSpec(name, None, is_package=True)
    spec.submodule_search_locations = [ADDIN_DIR]
    package = importlib.util.module_from_spec(spec)
    sys.modules[name] = package
    return package


def addin_module(module_name, package_name='solidinserts_under_test'):
    return importlib.import_module('{}.{}'.format(package_name, module_name))
