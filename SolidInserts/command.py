# ABOUTME: The Insert Seats command: a dialog that reads the selected hole rims, plans seats from the
# ABOUTME: chosen insert type, thread and compensation, previews the cuts and keeps them on OK.
import dataclasses
import os
import traceback

import adsk.core
import adsk.fusion

from .catalog import AUTOMATIC, THREAD_CHOICES, Series
from .cuts import cut_seats
from .geometry import round_mm
from .messages import SeatError, message
from .openings import MM_PER_CM, read_openings
from .seats import plan_seats, summary_html

CMD_ID = 'erikbuild_SolidInserts_insertSeats'
RESOURCES = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'resources')

_handlers = []
_command_handlers = []


class OpeningsCache:
    """The openings read for the last selection, so changing a setting does not read the model again."""

    def __init__(self):
        self.clear()

    def clear(self):
        self.rims = None
        self.result = None

    def read(self, design, rims):
        if not self.matches(rims):
            self.rims = rims
            self.result = read_openings(design, rims)
        return self.result

    def matches(self, rims):
        return (self.rims is not None and len(rims) == len(self.rims)
                and all(rim == cached for rim, cached in zip(rims, self.rims)))


_openings = OpeningsCache()


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
    definition = ui.commandDefinitions.itemById(CMD_ID)
    if definition:
        definition.deleteMe()
    _handlers.clear()
    _command_handlers.clear()
    _openings.clear()


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


class CommandCreatedHandler(adsk.core.CommandCreatedEventHandler):
    def notify(self, args):
        try:
            _openings.clear()
            command = args.command
            add_inputs(command.commandInputs)
            show_summary(command.commandInputs, current_plan(command.commandInputs))
            _command_handlers.clear()
            for event, handler in ((command.inputChanged, InputChangedHandler()),
                                   (command.validateInputs, ValidateInputsHandler()),
                                   (command.executePreview, ExecutePreviewHandler()),
                                   (command.execute, ExecuteHandler())):
                event.add(handler)
                _command_handlers.append(handler)
        except Exception:
            show_unexpected_error()


class InputChangedHandler(adsk.core.InputChangedEventHandler):
    def notify(self, args):
        try:
            if args.input.id != 'summary':
                show_summary(args.inputs, current_plan(args.inputs))
        except Exception:
            show_unexpected_error()


class ValidateInputsHandler(adsk.core.ValidateInputsEventHandler):
    def notify(self, args):
        try:
            args.areInputsValid = current_plan(args.inputs).can_apply
        except Exception:
            args.areInputsValid = False
            show_unexpected_error()


class ExecutePreviewHandler(adsk.core.CommandEventHandler):
    """Cuts the seats as the preview. A valid preview is kept as the result when OK is pressed."""

    def notify(self, args):
        try:
            inputs = args.command.commandInputs
            plan = current_plan(inputs)
            show_summary(inputs, plan)
            try:
                cut_seats(active_design(), plan)
                args.isValidResult = True
            except SeatError as error:
                show_summary(inputs, dataclasses.replace(plan, obstacles=plan.obstacles + (str(error),)))
        except Exception:
            show_unexpected_error()


class ExecuteHandler(adsk.core.CommandEventHandler):
    """Cuts the seats when there is no valid preview to keep. Fusion rolls back a failed execute."""

    def notify(self, args):
        try:
            cut_seats(active_design(), current_plan(args.command.commandInputs))
        except SeatError as error:
            args.executeFailed = True
            args.executeFailedMessage = str(error)
        except Exception:
            args.executeFailed = True
            show_unexpected_error()
