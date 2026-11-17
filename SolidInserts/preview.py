# ABOUTME: Shows planned seats in the viewport as see-through cylinders, with a cone for each chamfer,
# ABOUTME: without changing the model, so the selected hole rims stay valid while the dialog is open.
import adsk.core
import adsk.fusion

from .cuts import resolve_rim
from .openings import MM_PER_CM

SEAT_COLOR = (255, 140, 0)
SHOW_THROUGH_OPACITY = 0.6


class SeatPreview:
    """The seats of a plan drawn as custom graphics, one group per seat."""

    def __init__(self):
        self.groups = []

    def show(self, design, plan):
        self.clear()
        for seat in plan.seats:
            self.groups.append(draw_seat(design, seat))

    def clear(self):
        for group in self.groups:
            if group.isValid:
                group.deleteMe()
        self.groups = []


def draw_seat(design, seat):
    """Draws a seat as a cylinder, below a cone for its chamfer, in its rim's component, so it shows
    in every occurrence."""
    component = resolve_rim(design, seat.opening.rim_token).body.parentComponent
    opening = seat.opening
    radius = seat.diameter / 2
    top = opening.center
    shapes = []
    if seat.chamfer:
        shoulder = below(opening, seat.chamfer)
        shapes.append((top, seat.mouth_diameter / 2, shoulder, radius))
        top = shoulder
    shapes.append((top, radius, below(opening, seat.depth), radius))
    group = component.customGraphicsGroups.add()
    for start, start_radius, end, end_radius in shapes:
        shape = adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(
            cm_point(start), start_radius / MM_PER_CM, cm_point(end), end_radius / MM_PER_CM)
        graphics = group.addBRepBody(shape)
        # A show-through colour keeps the seat visible inside the solid around it.
        graphics.color = adsk.fusion.CustomGraphicsShowThroughColorEffect.create(
            adsk.core.Color.create(*SEAT_COLOR, 255), SHOW_THROUGH_OPACITY)
        graphics.isSelectable = False
    return group


def below(opening, depth_mm):
    """The point on the opening's axis depth_mm into the body."""
    return tuple(center - outward * depth_mm for center, outward in zip(opening.center, opening.outward))


def cm_point(point_mm):
    return adsk.core.Point3D.create(*(value / MM_PER_CM for value in point_mm))
