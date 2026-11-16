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
