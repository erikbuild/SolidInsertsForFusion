# ABOUTME: In-Fusion integration test for SolidInserts: builds real fixture geometry, reads hole
# ABOUTME: openings and cuts seats with the add-in code, and logs PASS/FAIL lines.
import importlib
import os
import sys
import time
import traceback

import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import support  # noqa: E402
importlib.reload(support)

TAG = 'SolidInsertsTest'
NOT_ENTRANCE = 'Select a circular rim on a flat face, with a cylindrical wall and no chamfer.'


def close(actual, expected, tolerance=1e-6):
    if isinstance(expected, tuple):
        return len(actual) == len(expected) and all(abs(a - e) <= tolerance for a, e in zip(actual, expected))
    return abs(actual - expected) <= tolerance


def read_one(openings, design, rim):
    found, errors = openings.read_openings(design, [rim])
    return (found[0] if len(found) == 1 else None), errors


def test_openings(design, fixture, openings, seats):
    check = support.check
    rims = fixture.rims

    h1, errors = read_one(openings, design, rims['h1'])
    check(h1 is not None and errors == [], 'h1 reads as one opening without errors {}'.format(errors))
    if h1:
        check(close(h1.center, (10.0, 10.0, 18.0)), 'h1 centre {}'.format(h1.center))
        check(close(h1.outward, (0.0, 0.0, 1.0)), 'h1 outward {}'.format(h1.outward))
        check(close(h1.diameter, 3.0), 'h1 diameter {}'.format(h1.diameter))
        check(close(h1.bore_depth, 7.0), 'h1 bore depth {}'.format(h1.bore_depth))
        check(h1.can_deepen is True, 'h1 flat floor can be deepened')
        check(close(h1.clearance, 10.0), 'h1 clearance {}'.format(h1.clearance))
        check(h1.body_name == 'Plate' and h1.ordinal == 1, 'h1 body and ordinal')

    h2, _ = read_one(openings, design, rims['h2'])
    check(h2 is not None and close(h2.bore_depth, 18.0) and h2.can_deepen is False,
          'h2 through bore 18 mm, cannot deepen {}'.format(h2))

    bottom, _ = read_one(openings, design, rims['h2_bottom'])
    check(bottom is not None and close(bottom.center[2], 0.0) and close(bottom.outward, (0.0, 0.0, -1.0)),
          'h2 bottom rim faces down {}'.format(bottom))

    for name, clearance in [('h5', 2.5), ('h6', 2.0)]:
        found, _ = read_one(openings, design, rims[name])
        check(found is not None and close(found.clearance, clearance),
              '{} clearance {} -> {}'.format(name, clearance, found and found.clearance))

    h8, _ = read_one(openings, design, rims['h8'])
    check(h8 is not None and close(h8.bore_depth, 4.0) and h8.can_deepen is True,
          'h8 shallow flat blind hole can deepen {}'.format(h8))

    thin, _ = read_one(openings, design, rims['thin'])
    check(thin is not None and close(thin.bore_depth, 5.0), 'thin plate bore 5 mm {}'.format(thin))

    brackets, errors = openings.read_openings(design, [rims['bracket_a'], rims['bracket_b']])
    check(len(brackets) == 2 and errors == [], 'both bracket rims read {}'.format(errors))
    if len(brackets) == 2:
        a, b = brackets
        check(a.body_key == b.body_key, 'bracket instances share one body key')
        check(close(a.center, (10.0, 5.0, 10.0)) and close(b.center, (10.0, 5.0, 10.0)),
              'bracket centres in component space {} {}'.format(a.center, b.center))
        check(close(a.clearance, 5.0), 'bracket clearance {}'.format(a.clearance))
        check(seats.same_opening(a, b), 'bracket instances are the same opening')

    found, errors = openings.read_openings(design, [rims['h4'], rims['boss'], rims['straight']])
    check(found == [] and errors == ['Hole {} on Plate. {}'.format(n, NOT_ENTRANCE) for n in (1, 2, 3)],
          'chamfered, boss and straight rims are refused {}'.format(errors))

    started = time.perf_counter()
    grid, errors = openings.read_openings(design, rims['grid'])
    elapsed = time.perf_counter() - started
    check(len(grid) == 36 and errors == [] and elapsed < 5.0,
          '36 grid rims read in {:.2f} s {}'.format(elapsed, errors[:2]))


def test_direct_design(app, openings):
    design = support.new_design(app)
    design.designType = adsk.fusion.DesignTypes.DirectDesignType
    support.check(openings.read_openings(design, []) == (
        [], ['SolidInserts needs design history. Turn on Capture Design History and try again.']),
        'direct design asks for history')


class AddIn:
    """The add-in modules a cuts case drives, loaded fresh by load_addin_package."""

    def __init__(self):
        self.catalog = support.addin_module('catalog')
        self.messages = support.addin_module('messages')
        self.openings = support.addin_module('openings')
        self.seats = support.addin_module('seats')
        self.cuts = support.addin_module('cuts')


def fresh_fixture(app):
    design = support.new_design(app)
    return design, support.build_fixture(design)


def cut_rims(addin, design, rims, series=None):
    """Plans seats on rims with Automatic sizing and no compensation, then cuts them."""
    found, errors = addin.openings.read_openings(design, rims)
    plan = addin.seats.plan_seats(found, series or addin.catalog.Series.STANDARD,
                                  addin.catalog.AUTOMATIC, 0.0, errors)
    support.check(plan.can_apply, 'seat plan can apply {}'.format(plan.obstacles))
    return addin.cuts.cut_seats(design, plan)


def dropped_mm3(volume_before_cm3, body):
    return (volume_before_cm3 - body.volume) * 1000


def profile_sketch(feature):
    return adsk.fusion.Profile.cast(feature.profile).parentSketch


def has_floor_at(feature, z_mm):
    return any(abs(face.pointOnFace.z * 10 - z_mm) <= 1e-4 for face in feature.endFaces)


def test_two_seats(app, addin):
    check = support.check
    design, fixture = fresh_fixture(app)
    plate = fixture.bodies['Plate']
    before = plate.volume
    features = cut_rims(addin, design, [fixture.rims['h1'], fixture.rims['h2']])
    names = [feature.name for feature in features]
    check(names == ['SolidInserts · Insert M3 × 5.7', 'SolidInserts · Insert M4 × 8.1'],
          'h1 and h2 feature names {}'.format(names))
    check(close(dropped_mm3(before, plate), 36.835 + 117.856, 0.02),
          'h1 and h2 remove {:.3f} mm3'.format(dropped_mm3(before, plate)))
    sketches = [profile_sketch(feature) for feature in features]
    check([sketch.name for sketch in sketches] == ['Profile Insert M3 × 5.7', 'Profile Insert M4 × 8.1'],
          'profile sketch names {}'.format([sketch.name for sketch in sketches]))
    check(all(sketch.isFullyConstrained for sketch in sketches), 'profile sketches are fully constrained')
    check(all(feature.attributes.itemByName('SolidInserts', 'seat') for feature in features),
          'each feature carries the seat attribute')

    _, errors = addin.openings.read_openings(design, [support.rim(plate, (10, 10, 18), 4)])
    check(errors == ['Hole 1 on Plate. SolidInserts already created this seat. Edit it in the timeline.'],
          'a seated rim is refused {}'.format(errors))


def test_single_seats(app, addin):
    check = support.check
    cases = [
        ('h8', 'Plate', None, 55.920, 11.3),
        ('h2_bottom', 'Plate', None, 117.856, 9.1),
        ('thin', 'ThinPlate', addin.catalog.Series.SHORT, 21.991, 1.0),
    ]
    for rim_name, body_name, series, removed_mm3, floor_z_mm in cases:
        design, fixture = fresh_fixture(app)
        body = fixture.bodies[body_name]
        before = body.volume
        features = cut_rims(addin, design, [fixture.rims[rim_name]], series)
        check(close(dropped_mm3(before, body), removed_mm3, 0.02),
              '{} removes {:.3f} mm3 (expected {})'.format(rim_name, dropped_mm3(before, body), removed_mm3))
        check(len(features) == 1 and has_floor_at(features[0], floor_z_mm),
              '{} seat floor at z = {} mm'.format(rim_name, floor_z_mm))


def test_cavity(app, addin):
    design, fixture = fresh_fixture(app)
    try:
        cut_rims(addin, design, [fixture.rims['cavity']])
        raised = None
    except addin.messages.SeatError as error:
        raised = str(error)
    support.check(raised == 'Hole 1 on CavityBlock. The seat intersects an edge, a cavity or another hole '
                            'at the requested depth.', 'cavity seat is refused {!r}'.format(raised))


def test_bracket(app, addin):
    design, fixture = fresh_fixture(app)
    occurrences = [fixture.occurrences['bracket_a'], fixture.occurrences['bracket_b']]
    before = [occurrence.bRepBodies.item(0).volume for occurrence in occurrences]
    timeline_before = design.timeline.count
    cut_rims(addin, design, [fixture.rims['bracket_a']])
    drops = [dropped_mm3(volume, occurrence.bRepBodies.item(0)) for volume, occurrence in zip(before, occurrences)]
    support.check(all(close(drop, 36.835, 0.02) for drop in drops),
                  'both bracket occurrences lose {}'.format(['{:.3f}'.format(drop) for drop in drops]))
    support.check(design.timeline.count - timeline_before == 2,
                  'bracket seat adds 2 timeline items (+{})'.format(design.timeline.count - timeline_before))


def test_inch_display_units(app, addin):
    design, fixture = fresh_fixture(app)
    design.fusionUnitsManager.distanceDisplayUnits = adsk.fusion.DistanceUnits.InchDistanceUnits
    feature = cut_rims(addin, design, [fixture.rims['h1']])[0]
    diameters = [adsk.fusion.SketchDiameterDimension.cast(dimension)
                 for dimension in profile_sketch(feature).sketchDimensions]
    diameter_cm = [dimension.parameter.value for dimension in diameters if dimension]
    depth = adsk.fusion.DistanceExtentDefinition.cast(feature.extentOne).distance
    # A cut against the sketch normal stores a negative distance; its size is the seat depth.
    support.check(len(diameter_cm) == 1 and close(diameter_cm[0], 0.4) and close(abs(depth.value), 0.67),
                  'inch display units keep Ø4 × 6.7 mm: {} cm, {} cm ({!r})'.format(
                      diameter_cm, depth.value, depth.expression))


def test_cuts(app):
    addin = AddIn()
    for case in (test_two_seats, test_single_seats, test_cavity, test_bracket, test_inch_display_units):
        try:
            case(app, addin)
        except Exception:
            support.check(False, '{} raised:\n{}'.format(case.__name__, traceback.format_exc()))


def run(context):
    app = adsk.core.Application.get()
    try:
        design = support.new_design(app)
        fixture = support.build_fixture(design)
        app.log('[{}] fixture built'.format(TAG))
        support.load_addin_package()
        openings = support.addin_module('openings')
        seats = support.addin_module('seats')
        test_openings(design, fixture, openings, seats)
        test_direct_design(app, openings)
        test_cuts(app)
    except Exception:
        support.check(False, 'test run raised:\n{}'.format(traceback.format_exc()))
    support.report(app, TAG)
