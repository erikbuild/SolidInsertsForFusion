# ABOUTME: End-to-end Fusion test for the running SolidInserts add-in: preselects two hole rims, opens Insert
# ABOUTME: Seats, checks the preview through Type and chamfer changes, presses OK, and checks the seats and one Undo.
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
# The preview bodies each dialog step waits for, and the check it logs. A chamfered seat draws a cone
# and a cylinder.
STEP_PREVIEWS = {
    'preselected': (4, 'the preview draws both chamfered seats ({} bodies)'),
    'voron': (0, 'VORON clears the preview ({} bodies)'),
    'standard': (4, 'switching back to Standard draws both chamfered seats again ({} bodies)'),
    'no_chamfer': (2, 'unchecking Chamfer top edge draws the seats without cones ({} bodies)'),
    'chamfer': (4, 'checking Chamfer top edge draws the cones again ({} bodies)'),
}
EXPECTED_NAMES = ['Profile Insert M3 × 5.7', 'SolidInserts · Insert M3 × 5.7', 'SolidInserts · Chamfer Insert M3 × 5.7',
                  'Profile Insert M4 × 8.1', 'SolidInserts · Insert M4 × 8.1', 'SolidInserts · Chamfer Insert M4 × 8.1']
EXPECTED_REMOVED_MM3 = 157.263

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


def preview_bodies():
    groups = _state['design'].rootComponent.customGraphicsGroups
    return sum(groups.item(index).count for index in range(groups.count))


def dialog_input(input_id):
    return _state['command'].commandInputs.itemById(input_id)


def chamfer_inputs():
    return (adsk.core.BoolValueCommandInput.cast(dialog_input('chamfer')),
            adsk.core.FloatSpinnerCommandInput.cast(dialog_input('chamfer_size')))


def summary_text():
    return adsk.core.TextBoxCommandInput.cast(dialog_input('summary')).formattedText


def spinner_mm(input_id):
    """A length spinner's value, minimum and maximum in millimetres, and the expression it shows."""
    spinner = adsk.core.FloatSpinnerCommandInput.cast(dialog_input(input_id))
    if spinner is None:
        return None, None
    values = (spinner.value, spinner.minimumValue, spinner.maximumValue)
    return tuple(round(value * 10, 3) for value in values), spinner.expression


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
        bodies = preview_bodies()
        if bodies != expected and time.monotonic() < _state['deadline']:
            adsk.core.Application.get().fireCustomEvent(STEP_EVENT, step)
            return
        support.check(bodies == expected, label.format(bodies))
        chamfer, chamfer_size = chamfer_inputs()
        if step == 'preselected':
            holes = adsk.core.SelectionCommandInput.cast(dialog_input('holes'))
            support.check(holes is not None and holes.selectionCount == 2,
                          'both preselected rims are in Holes ({})'.format(holes.selectionCount if holes else '-'))
            support.check(chamfer is not None and chamfer.value, 'Chamfer top edge starts on')
            for input_id, expected in (('chamfer_size', (0.4, 0.1, 2.0)), ('compensation', (0.0, -1.0, 1.0))):
                actual, expression = spinner_mm(input_id)
                support.check(actual == expected, '{} value, minimum and maximum are {} mm, showing {!r} '
                                                  '(expected {} mm)'.format(input_id, actual, expression, expected))
            choose_series(VORON)
            start_step('voron')
        elif step == 'voron':
            choose_series(STANDARD)
            start_step('standard')
        elif step == 'standard':
            chamfer.value = False
            start_step('no_chamfer')
        elif step == 'no_chamfer':
            support.check(not chamfer_size.isEnabled, 'unchecking Chamfer top edge disables Chamfer size')
            support.check('chamfer' not in summary_text(),
                          'the summary has no chamfer when it is off: {}'.format(summary_text()))
            chamfer.value = True
            start_step('chamfer')
        else:
            support.check(chamfer_size.isEnabled, 'checking Chamfer top edge enables Chamfer size')
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
            support.check(names == EXPECTED_NAMES, 'timeline gains the two chamfered seats {}'.format(names))
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
