# ABOUTME: Fusion add-in entry point for SolidInserts: adds the Insert Seats button to the configured
# ABOUTME: toolbar panel when the add-in starts and removes it when the add-in stops.
import json
import os
import traceback

import adsk.core

from . import command
from .messages import message

WORKSPACE_ID = 'FusionSolidEnvironment'
TAB_ID = 'SolidTab'
PANEL_ID = 'SolidCreatePanel'
FALLBACK_PANEL_ID = 'SolidScriptsAddinsPanel'

_ui = None
_active_panel_id = None
_custom_panel_id = None


def load_config():
    config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'config.json')
    try:
        with open(config_path, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, ValueError):
        return {}


def get_or_create_custom_panel(panel_id, panel_name):
    """The custom panel on the Solid tab, created when missing. None when the tab is unavailable."""
    workspace = _ui.workspaces.itemById(WORKSPACE_ID)
    tab = workspace.toolbarTabs.itemById(TAB_ID) if workspace else None
    if not tab:
        return None
    return tab.toolbarPanels.itemById(panel_id) or tab.toolbarPanels.add(panel_id, panel_name)


def run(context):
    global _ui, _active_panel_id, _custom_panel_id
    try:
        _ui = adsk.core.Application.get().userInterface
        config = load_config()
        definition = command.create_definition(_ui)

        panel = None
        if config.get('use_custom_panel'):
            _custom_panel_id = config.get('panel_id', 'CustomPlugins_Panel')
            panel = get_or_create_custom_panel(_custom_panel_id, config.get('panel_name', 'ERIKBUILD'))
        if not panel:
            panel = _ui.allToolbarPanels.itemById(PANEL_ID)
        if not panel:
            panel = _ui.allToolbarPanels.itemById(FALLBACK_PANEL_ID)

        if panel:
            _active_panel_id = panel.id
            if not panel.controls.itemById(command.CMD_ID):
                control = panel.controls.addCommand(definition)
                control.isPromotedByDefault = True
                control.isPromoted = True
    except Exception:
        if _ui:
            _ui.messageBox(message('unexpected_error', details=traceback.format_exc()))


def stop(context):
    global _active_panel_id, _custom_panel_id
    try:
        if _active_panel_id:
            panel = _ui.allToolbarPanels.itemById(_active_panel_id)
            if panel:
                control = panel.controls.itemById(command.CMD_ID)
                if control:
                    control.deleteMe()
                # Remove the custom panel if no controls remain
                if _custom_panel_id and _active_panel_id == _custom_panel_id and panel.controls.count == 0:
                    panel.deleteMe()
            _active_panel_id = None
            _custom_panel_id = None
        command.delete_definition(_ui)
    except Exception:
        if _ui:
            _ui.messageBox(message('unexpected_error', details=traceback.format_exc()))
