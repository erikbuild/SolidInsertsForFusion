# ABOUTME: Fusion script that registers a throwaway command to check the dialog lifecycle the
# ABOUTME: Insert Seats command relies on: preselection, preview text, failed execute, scripted OK, undo.
import importlib
import os
import sys
import traceback

import adsk.core
import adsk.fusion

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import support  # noqa: E402
importlib.reload(support)

TAG = 'SolidInsertsCommandSpike'
CMD_ID = 'SolidInsertsSpikeCmd'
PANEL_ID = 'SolidScriptsAddinsPanel'
SEAT_NAME = 'SolidInserts · Spike seat'
DRIVE_EVENT = 'SolidInsertsSpikeDrive'

_handlers = []
_state = {'drive': False, 'fail': False, 'previews': 0, 'undo_sent': False, 'terminated': None,
          'command': None, 'plate': None}


def app_ui():
    app = adsk.core.Application.get()
    return app, app.userInterface


def log(message):
    app, _ = app_ui()
    app.log('[{}] {}'.format(TAG, message))


def timeline_count():
    app, _ = app_ui()
    return adsk.fusion.Design.cast(app.activeProduct).timeline.count


def cut_seat(rim_edge):
    feature, _, _ = support.cut_circle_seat(rim_edge, 4, 3, SEAT_NAME)
    feature.attributes.add('SolidInserts', 'seat', '{}')
    return feature


def guarded(name):
    def wrap(notify):
        def run_notify(self, args):
            try:
                notify(self, args)
            except Exception:
                log('{} RAISED: {}'.format(name, traceback.format_exc()))
        return run_notify
    return wrap


def start_command(rim_center):
    """Preselects the Ø3 rim at rim_center (mm) and starts the spike command."""
    _, ui = app_ui()
    _state['previews'] = 0
    ui.activeSelections.clear()
    ui.activeSelections.add(support.rim(_state['plate'], rim_center, 3))
    log('starting command (drive={}, fail={}) on rim {}; timeline = {}'.format(
        _state['drive'], _state['fail'], rim_center, timeline_count()))
    ui.commandDefinitions.itemById(CMD_ID).execute()


class ActivateHandler(adsk.core.CommandEventHandler):
    @guarded('activate')
    def notify(self, args):
        inputs = args.command.commandInputs
        log('FINDING 1a: activate, selection count = {}'.format(inputs.itemById('rims').selectionCount))
        if _state['drive']:
            _state['command'] = args.command
            app, _ = app_ui()
            app.fireCustomEvent(DRIVE_EVENT, 'ok')


class DriveHandler(adsk.core.CustomEventHandler):
    """Clicks OK on the running command, or starts the next driven run, outside any command event."""
    @guarded('drive')
    def notify(self, args):
        if args.additionalInfo == 'restart':
            start_command((20, 8, 18))
            return
        command = _state['command']
        log('FINDING 5a: custom event calls doExecute(True); selection count = {}'.format(
            command.commandInputs.itemById('rims').selectionCount))
        log('FINDING 5b: doExecute returned {}'.format(command.doExecute(True)))


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    @guarded('inputChanged')
    def notify(self, args):
        selection = args.inputs.itemById('rims')
        log('FINDING 1b: inputChanged id={} selection count = {}'.format(
            args.input.id, selection.selectionCount if selection else '-'))


class PreviewHandler(adsk.core.CommandEventHandler):
    @guarded('executePreview')
    def notify(self, args):
        _state['previews'] += 1
        inputs = args.command.commandInputs
        selection = inputs.itemById('rims')
        log('FINDING 1c: executePreview #{} selection count = {}'.format(_state['previews'], selection.selectionCount))
        if selection.selectionCount:
            cut_seat(selection.selection(0).entity)
        summary = adsk.core.TextBoxCommandInput.cast(inputs.itemById('summary'))
        summary.formattedText = 'preview ran {}'.format(_state['previews'])
        log('FINDING 2: summary text set in executePreview, reads back {!r}'.format(summary.formattedText))
        args.isValidResult = not inputs.itemById('fail').value


class ExecuteHandler(adsk.core.CommandEventHandler):
    @guarded('execute')
    def notify(self, args):
        inputs = args.command.commandInputs
        selection = inputs.itemById('rims')
        log('FINDING 5c: execute ran; selection count = {}; timeline before cut = {}'.format(
            selection.selectionCount, timeline_count()))
        if selection.selectionCount:
            cut_seat(selection.selection(0).entity)
        if inputs.itemById('fail').value:
            args.executeFailed = True
            args.executeFailedMessage = 'Spike failure after one cut.'
            log('FINDING 4a: execute set executeFailed after cutting; timeline now {}'.format(timeline_count()))


class CreatedHandler(adsk.core.CommandCreatedEventHandler):
    @guarded('commandCreated')
    def notify(self, args):
        command = args.command
        inputs = command.commandInputs
        selection = inputs.addSelectionInput('rims', 'Rims', 'Pick a hole rim.')
        selection.addSelectionFilter('CircularEdges')
        selection.setSelectionLimits(1, 0)
        inputs.addTextBoxCommandInput('summary', 'Summary', 'created', 3, True)
        inputs.addBoolValueInput('fail', 'Fail in execute', True, '', _state['fail'])
        for event, handler in [(command.activate, ActivateHandler()),
                               (command.inputChanged, InputChangedHandler()),
                               (command.executePreview, PreviewHandler()),
                               (command.execute, ExecuteHandler())]:
            event.add(handler)
            _handlers.append(handler)
        log('commandCreated; timeline = {}'.format(timeline_count()))


class TerminatedHandler(adsk.core.ApplicationCommandEventHandler):
    @guarded('commandTerminated')
    def notify(self, args):
        if args.commandId == CMD_ID:
            app, ui = app_ui()
            design = adsk.fusion.Design.cast(app.activeProduct)
            names = [design.timeline.item(i).name for i in range(design.timeline.count)]
            log('FINDING 3/4b: command terminated (fail={}, reason {}); timeline = {} {}; seat attributes = {}'.format(
                _state['fail'], args.terminationReason, design.timeline.count, names,
                len(design.findAttributes('SolidInserts', 'seat'))))
            if _state['drive'] and _state['fail']:
                _state['fail'] = False
                app.fireCustomEvent(DRIVE_EVENT, 'restart')
            elif _state['drive'] and not _state['undo_sent']:
                _state['undo_sent'] = True
                log('FINDING 6a: sending one Undo; timeline before = {}'.format(design.timeline.count))
                ui.commandDefinitions.itemById('UndoCommand').execute()
        elif args.commandId == 'UndoCommand' and _state['undo_sent']:
            log('FINDING 6b: after one Undo timeline = {}'.format(timeline_count()))
            log('==== spike done ====')


def remove_command(ui):
    app, _ = app_ui()
    try:
        app.unregisterCustomEvent(DRIVE_EVENT)
    except RuntimeError:
        pass  # Nothing is registered on a first run.
    if _state['terminated']:
        ui.commandTerminated.remove(_state['terminated'])
        _state['terminated'] = None
    panel = ui.allToolbarPanels.itemById(PANEL_ID)
    control = panel.controls.itemById(CMD_ID) if panel else None
    if control:
        control.deleteMe()
    definition = ui.commandDefinitions.itemById(CMD_ID)
    if definition:
        definition.deleteMe()


def run(context):
    app, ui = app_ui()
    try:
        adsk.autoTerminate(False)
        remove_command(ui)
        answer = ui.messageBox('Drive the command automatically (findings 4 to 6)?\n'
                               'Choose No for the interactive run (findings 1 to 3).',
                               'SolidInserts command spike', adsk.core.MessageBoxButtonTypes.YesNoButtonType)
        _state['drive'] = answer == adsk.core.DialogResults.DialogYes
        _state['fail'] = _state['drive']
        design = support.new_design(app)
        plate = support.box(design.rootComponent, 0, 0, 0, 42, 30, 18, 'Plate')
        support.hole(plate, 8, 8, 18, 3, 7)
        support.hole(plate, 20, 8, 18, 3, 7)
        _state['plate'] = plate

        definition = ui.commandDefinitions.addButtonDefinition(CMD_ID, 'SolidInserts Spike', 'Command lifecycle spike')
        created = CreatedHandler()
        definition.commandCreated.add(created)
        terminated = TerminatedHandler()
        ui.commandTerminated.add(terminated)
        _state['terminated'] = terminated
        drive = DriveHandler()
        app.registerCustomEvent(DRIVE_EVENT).add(drive)
        _handlers.extend([created, terminated, drive])
        panel = ui.allToolbarPanels.itemById(PANEL_ID)
        panel.controls.addCommand(definition)

        start_command((8, 8, 18))
    except Exception:
        log('SPIKE FAILED: {}'.format(traceback.format_exc()))


def stop(context):
    _, ui = app_ui()
    try:
        remove_command(ui)
        _handlers.clear()
    except Exception:
        log('stop RAISED: {}'.format(traceback.format_exc()))
