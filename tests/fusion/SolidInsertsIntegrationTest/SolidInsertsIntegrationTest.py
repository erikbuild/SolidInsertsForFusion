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
    except Exception:
        support.check(False, 'test run raised:\n{}'.format(traceback.format_exc()))
    support.report(app, TAG)
