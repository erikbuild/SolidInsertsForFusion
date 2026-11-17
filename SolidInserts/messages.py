# ABOUTME: All user-facing SolidInserts copy as named templates, plus the error that
# ABOUTME: carries a finished message to the dialog.

TEMPLATES = {
    'select_rims': 'Select the circular rim of each hole in the 3D view.',
    'needs_history': 'SolidInserts needs design history. Turn on Capture Design History and try again.',
    'not_entrance': 'Select a circular rim on a flat face, with a cylindrical wall and no chamfer.',
    'linked_component': 'This body is in a linked component. Open its design to add seats.',
    'existing_seat': 'SolidInserts already created this seat. Edit it in the timeline.',
    'bore_depth_unknown': 'Could not measure the cylindrical depth of the hole.',
    'clearance_unknown': 'Could not measure the edges around the opening.',
    'hole_prefix': 'Hole {ordinal} on {body}. {reason}',
    'choose_thread': 'Hole Ø{diameter:.2f} mm. Select the screw thread explicitly.',
    'thread_unavailable': '{thread} is not available in the CNC Kitchen {series} series.',
    'compensation_range': 'Diameter compensation must be between −1 and +1 mm.',
    'seat_not_wider': 'The Ø{seat:.2f} seat must be wider than the Ø{hole:.2f} mm hole.',
    'seat_reaches_edge': 'The Ø{seat:.2f} seat reaches a nearby edge at the opening.',
    'seat_too_deep': ('The seat needs {depth:.2f} mm of depth. The cylindrical wall ends at '
                      '{bore:.2f} mm; choose a shorter insert.'),
    'thin_wall': ('The opening has {wall:.2f} mm of material to the nearest edge. '
                  'The catalog specifies {catalog:.2f} mm.'),
    'seats_overlap': 'The seats for holes {first} and {second} overlap at the opening.',
    'chamfer_range': 'Chamfer size must be between {low:.2f} and {high:.2f} mm.',
    'chamfer_reaches_edge': 'The {chamfer:.2f} mm chamfer on the Ø{seat:.2f} seat reaches a nearby edge at the opening.',
    'chamfers_overlap': 'The chamfers of the seats for holes {first} and {second} overlap at the opening.',
    'opening_changed': 'The hole opening changed after an earlier edit.',
    'profile_unconstrained': 'The seat profile is not fully constrained.',
    'cut_other_bodies': 'The cut changed other bodies besides this one.',
    'cut_intersects': 'The seat intersects an edge, a cavity or another hole at the requested depth.',
    'cut_no_floor': 'The seat has no floor at the requested depth. Check the thickness or use a shorter insert.',
    'chamfer_failed': 'The chamfer could not be cut at the seat opening. Make it smaller or turn it off.',
    'chamfer_intersects': ('The chamfer meets an edge, a cavity or another hole at the seat opening. '
                           'Make it smaller or turn it off.'),
    'insert_name': 'Insert {product}',
    'profile_name': 'Profile {name}',
    'chamfer_name': 'Chamfer {name}',
    'seat_line': 'Hole {ordinal} · {thread} · Ø{diameter:.2f} × {depth:.2f} mm',
    'seat_chamfer': ' · {chamfer:.2f} mm chamfer',
    'note_line': 'Note: {note}',
    'command_name': 'Insert Seats',
    'command_tooltip': 'Cut seats for heat-set threaded inserts at the rims of existing holes.',
    'holes_label': 'Holes',
    'series_label': 'Type',
    'series_tooltip': 'Short Version for M3, M4, M5, M6 and M8. VORON M3 × 5 × 4 for M3.',
    'thread_label': 'Screw thread',
    'thread_tooltip': ('Automatic matches the nominal hole diameter within ±0.05 mm. '
                       'For clearance holes, choose the screw size.'),
    'compensation_label': 'Diameter compensation',
    'compensation_tooltip': 'Adjustment to the seat diameter. Use 0 for the catalog dimension.',
    'chamfer_label': 'Chamfer top edge',
    'chamfer_tooltip': 'Adds a 45° lead-in at the seat opening so the insert starts straight.',
    'chamfer_size_label': 'Chamfer size',
    'chamfer_size_tooltip': 'How far the chamfer cuts into the face and down the seat wall.',
    'summary_label': 'Seats',
    'unexpected_error': 'SolidInserts stopped because of an unexpected error:\n{details}',
}


class SeatError(Exception):
    """A reason, in finished user-facing copy, why a seat cannot be made."""


def message(key, **values):
    return TEMPLATES[key].format(**values)
