# ABOUTME: End-to-end Fusion test for the running SolidInserts add-in: preselects two hole rims, opens
# ABOUTME: Insert Seats, presses OK from the script, and checks the seats, the timeline and one Undo.
import importlib
import os
import sys
import traceback

import adsk
import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import support  # noqa: E402
importlib.reload(support)

TAG = 'SolidInsertsCommandTest'
CMD_ID = 'erikbuild_SolidInserts_insertSeats'
PRESS_OK_EVENT = 'SolidInsertsCommandTestPressOK'
EXPECTED_NAMES = ['Profile Insert M3 × 5.7', 'SolidInserts · Insert M3 × 5.7',
                  'Profile Insert M4 × 8.1', 'SolidInserts · Insert M4 × 8.1']
EXPECTED_REMOVED_MM3 = 36.835 + 117.856

_handlers = []
_state = {'design': None, 'command': None, 'timeline': 0, 'volume': 0.0, 'undo_sent': False,
          'created': None, 'terminated': None}


def app_ui():
    app = adsk.core.Application.get()
    return app, app.userInterface


def plate_volume():
    return _state['design'].rootComponent.bRepBodies.itemByName('Plate').volume


def new_timeline_names():
    timeline = _state['design'].timeline
    return [timeline.item(i).name for i in range(_state['timeline'], timeline.count)]


def guarded(notify):
    """Records an exception in a handler as a failure and ends the test."""
    def run_notify(self, args):
        try:
            notify(self, args)
        except Exception:
            support.check(False, '{} raised:\n{}'.format(type(self).__name__, traceback.format_exc()))
            finish()
    return run_notify


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    @guarded
    def notify(self, args):
        _state['command'] = args.command
        activate = ActivateHandler()
        args.command.activate.add(activate)
        _handlers.append(activate)


class ActivateHandler(adsk.core.CommandEventHandler):
    @guarded
    def notify(self, args):
        # OK cannot be pressed inside a command event, so a custom event presses it once Fusion is idle.
        app, _ = app_ui()
        app.fireCustomEvent(PRESS_OK_EVENT)


class PressOkHandler(adsk.core.CustomEventHandler):
    @guarded
    def notify(self, args):
        holes = adsk.core.SelectionCommandInput.cast(_state['command'].commandInputs.itemById('holes'))
        support.check(holes is not None and holes.selectionCount == 2,
                      'both preselected rims are in Holes ({})'.format(holes.selectionCount if holes else '-'))
        support.check(_state['command'].doExecute(True), 'OK pressed from the script')


class TerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    @guarded
    def notify(self, args):
        _, ui = app_ui()
        if args.commandId == CMD_ID:
            names = new_timeline_names()
            support.check(names == EXPECTED_NAMES, 'timeline gains the two seats {}'.format(names))
            removed = (_state['volume'] - plate_volume()) * 1000
            support.check(abs(removed - EXPECTED_REMOVED_MM3) <= 0.02,
                          'Plate loses {:.3f} mm3 (expected {:.3f})'.format(removed, EXPECTED_REMOVED_MM3))
            _state['undo_sent'] = True
            ui.commandDefinitions.itemById('UndoCommand').execute()
        elif args.commandId == 'UndoCommand' and _state['undo_sent']:
            timeline_count = _state['design'].timeline.count
            support.check(timeline_count == _state['timeline'],
                          'one Undo restores the timeline ({} -> {})'.format(timeline_count, _state['timeline']))
            restored = abs(plate_volume() - _state['volume']) * 1000
            support.check(restored <= 1e-6, 'one Undo restores the Plate volume (off by {:.6f} mm3)'.format(restored))
            finish()


def remove_handlers():
    app, ui = app_ui()
    definition = ui.commandDefinitions.itemById(CMD_ID)
    if definition and _state['created']:
        definition.commandCreated.remove(_state['created'])
    if _state['terminated']:
        ui.commandTerminated.remove(_state['terminated'])
    _state['created'] = _state['terminated'] = None
    try:
        app.unregisterCustomEvent(PRESS_OK_EVENT)
    except RuntimeError:
        pass  # Nothing is registered when the test stopped before registering it.
    _handlers.clear()


def finish():
    app, _ = app_ui()
    support.report(app, TAG)
    adsk.terminate()


def run(context):
    app, ui = app_ui()
    try:
        remove_handlers()
        definition = ui.commandDefinitions.itemById(CMD_ID)
        if definition is None:
            support.check(False, 'command definition {} not found: is the SolidInserts add-in running?'.format(CMD_ID))
            support.report(app, TAG)
            return
        design = support.new_design(app)
        fixture = support.build_fixture(design)
        _state.update(design=design, timeline=design.timeline.count, volume=plate_volume(), undo_sent=False)

        created = CreatedHandler()
        definition.commandCreated.add(created)
        terminated = TerminatedHandler()
        ui.commandTerminated.add(terminated)
        press_ok = PressOkHandler()
        app.registerCustomEvent(PRESS_OK_EVENT).add(press_ok)
        _state.update(created=created, terminated=terminated)
        _handlers.extend([created, terminated, press_ok])

        ui.activeSelections.clear()
        ui.activeSelections.add(fixture.rims['h1'])
        ui.activeSelections.add(fixture.rims['h2'])
        adsk.autoTerminate(False)
        definition.execute()
    except Exception:
        support.check(False, 'test run raised:\n{}'.format(traceback.format_exc()))
        remove_handlers()
        support.report(app, TAG)
        adsk.autoTerminate(True)


def stop(context):
    try:
        remove_handlers()
    except Exception:
        app, _ = app_ui()
        app.log('[{}] stop raised:\n{}'.format(TAG, traceback.format_exc()))
