# ABOUTME: End-to-end Fusion test for the running SolidInserts add-in: preselects two hole rims, opens Insert
# ABOUTME: Seats, checks the preview through a Type change, presses OK, and checks the seats and one Undo.
import importlib
import os
import sys
import time
import traceback

import adsk
import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import support  # noqa: E402
importlib.reload(support)

TAG = 'SolidInsertsCommandTest'
CMD_ID = 'erikbuild_SolidInserts_insertSeats'
STEP_EVENT = 'SolidInsertsCommandTestStep'
STANDARD = 'Standard'
VORON = 'VORON M3 × 5 × 4'
PREVIEW_TIMEOUT_S = 3.0
# The preview graphics groups each dialog step waits for, and the check it logs.
STEP_PREVIEWS = {
    'preselected': (2, 'the preview draws both seats ({} groups)'),
    'voron': (0, 'VORON clears the preview ({} groups)'),
    'standard': (2, 'switching back to Standard draws both seats again ({} groups)'),
}
EXPECTED_NAMES = ['Profile Insert M3 × 5.7', 'SolidInserts · Insert M3 × 5.7',
                  'Profile Insert M4 × 8.1', 'SolidInserts · Insert M4 × 8.1']
EXPECTED_REMOVED_MM3 = 36.835 + 117.856

_handlers = []
_state = {'design': None, 'command': None, 'timeline': 0, 'volume': 0.0, 'undo_sent': False,
          'created': None, 'terminated': None, 'deadline': 0.0}


def app_ui():
    app = adsk.core.Application.get()
    return app, app.userInterface


def plate_volume():
    return _state['design'].rootComponent.bRepBodies.itemByName('Plate').volume


def preview_groups():
    return _state['design'].rootComponent.customGraphicsGroups.count


def choose_series(name):
    series = adsk.core.DropDownCommandInput.cast(_state['command'].commandInputs.itemById('series'))
    for index in range(series.listItems.count):
        if series.listItems.item(index).name == name:
            series.listItems.item(index).isSelected = True


def start_step(step):
    _state['deadline'] = time.monotonic() + PREVIEW_TIMEOUT_S
    adsk.core.Application.get().fireCustomEvent(STEP_EVENT, step)


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
        # OK cannot be pressed inside a command event, so custom events drive the dialog once Fusion is idle.
        start_step('preselected')


class StepHandler(adsk.core.CustomEventHandler):
    """Waits until the preview shows the groups the step expects, then changes the dialog for the next step."""

    @guarded
    def notify(self, args):
        step = args.additionalInfo
        expected, label = STEP_PREVIEWS[step]
        groups = preview_groups()
        if groups != expected and time.monotonic() < _state['deadline']:
            adsk.core.Application.get().fireCustomEvent(STEP_EVENT, step)
            return
        support.check(groups == expected, label.format(groups))
        if step == 'preselected':
            holes = adsk.core.SelectionCommandInput.cast(_state['command'].commandInputs.itemById('holes'))
            support.check(holes is not None and holes.selectionCount == 2,
                          'both preselected rims are in Holes ({})'.format(holes.selectionCount if holes else '-'))
            choose_series(VORON)
            start_step('voron')
        elif step == 'voron':
            choose_series(STANDARD)
            start_step('standard')
        else:
            pressed = _state['command'].doExecute(True)
            support.check(pressed, 'OK pressed from the script')
            if not pressed:
                finish()


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
            support.check(preview_groups() == 0, 'OK removes the preview ({} groups)'.format(preview_groups()))
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
        app.unregisterCustomEvent(STEP_EVENT)
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
        _state.update(design=design, timeline=design.timeline.count, undo_sent=False)
        _state['volume'] = plate_volume()

        created = CreatedHandler()
        definition.commandCreated.add(created)
        terminated = TerminatedHandler()
        ui.commandTerminated.add(terminated)
        step = StepHandler()
        app.registerCustomEvent(STEP_EVENT).add(step)
        _state.update(created=created, terminated=terminated)
        _handlers.extend([created, terminated, step])

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
