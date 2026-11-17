# ABOUTME: The Insert Seats command: a dialog that reads the selected hole rims, plans seats from the
# ABOUTME: chosen insert type, thread and compensation, previews the seats and cuts them on OK.
import os
import traceback

import adsk.core
import adsk.fusion

from .catalog import AUTOMATIC, THREAD_CHOICES, Series
from .cuts import cut_seats
from .geometry import round_mm
from .messages import SeatError, message
from .openings import MM_PER_CM, read_openings
from .openings_cache import OpeningsCache
from .preview import SeatPreview
from .seats import plan_seats, summary_html

CMD_ID = 'erikbuild_SolidInserts_insertSeats'
RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

_handlers = []
_command_handlers = []


_openings = OpeningsCache(read_openings)
_plan = None
_preview = SeatPreview()


def create_definition(ui):
    """Registers the Insert Seats button definition and its commandCreated handler."""
    definition = ui.commandDefinitions.itemById(CMD_ID)
    if definition:
        definition.deleteMe()
    definition = ui.commandDefinitions.addButtonDefinition(
        CMD_ID, message('command_name'), message('command_tooltip'), RESOURCES)
    created = CommandCreatedHandler()
    definition.commandCreated.add(created)
    _handlers.append(created)
    return definition


def delete_definition(ui):
    global _plan
    definition = ui.commandDefinitions.itemById(CMD_ID)
    if definition:
        definition.deleteMe()
    _handlers.clear()
    _command_handlers.clear()
    _openings.clear()
    _preview.clear()
    _plan = None


def active_design():
    return adsk.fusion.Design.cast(adsk.core.Application.get().activeProduct)


def show_unexpected_error():
    adsk.core.Application.get().userInterface.messageBox(
        message('unexpected_error', details=traceback.format_exc()))


def add_inputs(inputs):
    holes = inputs.addSelectionInput('holes', message('holes_label'), message('select_rims'))
    holes.addSelectionFilter('CircularEdges')
    holes.setSelectionLimits(1, 0)

    series = inputs.addDropDownCommandInput(
        'series', message('series_label'), adsk.core.DropDownStyles.TextListDropDownStyle)
    for choice in Series:
        series.listItems.add(choice.value, choice is Series.STANDARD)
    series.tooltip = message('series_tooltip')

    thread = inputs.addDropDownCommandInput(
        'thread', message('thread_label'), adsk.core.DropDownStyles.TextListDropDownStyle)
    for choice in THREAD_CHOICES:
        thread.listItems.add(choice, choice == AUTOMATIC)
    thread.tooltip = message('thread_tooltip')

    # Limits and the initial value are centimetres; the step is in the spinner's millimetres.
    compensation = inputs.addFloatSpinnerCommandInput(
        'compensation', message('compensation_label'), 'mm', -0.1, 0.1, 0.01, 0)
    compensation.tooltip = message('compensation_tooltip')

    inputs.addTextBoxCommandInput('summary', message('summary_label'), '', 6, True)


def current_plan(inputs):
    """Plans seats from the dialog: openings come from the cache, settings are read fresh."""
    holes = adsk.core.SelectionCommandInput.cast(inputs.itemById('holes'))
    rims = [holes.selection(index).entity for index in range(holes.selectionCount)]
    openings, rim_errors = _openings.read(active_design(), rims)
    series = Series(adsk.core.DropDownCommandInput.cast(inputs.itemById('series')).selectedItem.name)
    thread = adsk.core.DropDownCommandInput.cast(inputs.itemById('thread')).selectedItem.name
    compensation_cm = adsk.core.FloatSpinnerCommandInput.cast(inputs.itemById('compensation')).value
    return plan_seats(openings, series, thread, round_mm(compensation_cm * MM_PER_CM), rim_errors)


def show_summary(inputs, plan):
    adsk.core.TextBoxCommandInput.cast(inputs.itemById('summary')).formattedText = summary_html(plan)


def refresh_plan(inputs):
    """Plans seats for the dialog's inputs, lists them and clears the drawn seats until the next
    preview. The other command events use this plan, so only an input change reads the model."""
    global _plan
    _plan = current_plan(inputs)
    show_summary(inputs, _plan)
    _preview.clear()


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            _openings.clear()
            command = args.command
            add_inputs(command.commandInputs)
            refresh_plan(command.commandInputs)
            _command_handlers.clear()
            for event, handler in ((command.inputChanged, InputChangedHandler()),
                                   (command.validateInputs, ValidateInputsHandler()),
                                   (command.executePreview, ExecutePreviewHandler()),
                                   (command.execute, ExecuteHandler()),
                                   (command.destroy, DestroyHandler())):
                event.add(handler)
                _command_handlers.append(handler)
        except Exception:
            show_unexpected_error()


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            if args.input.id != 'summary':
                refresh_plan(args.inputs)
        except Exception:
            show_unexpected_error()


class ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            args.areInputsValid = _plan.can_apply
        except Exception:
            args.areInputsValid = False
            show_unexpected_error()


class ExecutePreviewHandler(adsk.core.CommandEventHandler):
    """Draws the planned seats without changing the model, so the selected rims stay valid."""

    def notify(self, args):
        try:
            if _plan.can_apply:
                _preview.show(active_design(), _plan)
        except Exception:
            show_unexpected_error()


class ExecuteHandler(adsk.core.CommandEventHandler):
    """Cuts the planned seats when OK is pressed. Fusion rolls back a failed execute."""

    def notify(self, args):
        try:
            _preview.clear()
            cut_seats(active_design(), _plan)
        except SeatError as error:
            args.executeFailed = True
            args.executeFailedMessage = str(error)
        except Exception:
            args.executeFailed = True
            show_unexpected_error()


class DestroyHandler(adsk.core.CommandEventHandler):
    """Removes the drawn seats when the dialog closes, whether by OK or Cancel."""

    def notify(self, args):
        try:
            _preview.clear()
        except Exception:
            show_unexpected_error()
