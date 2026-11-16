# ABOUTME: Shows planned seats in the viewport as see-through cylinders without changing the model,
# ABOUTME: so the selected hole rims stay valid while the Insert Seats dialog is open.
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
    """Draws a seat as a cylinder in its rim's component, so it shows in every occurrence."""
    component = resolve_rim(design, seat.opening.rim_token).body.parentComponent
    opening = seat.opening
    floor = tuple(center - outward * seat.depth for center, outward in zip(opening.center, opening.outward))
    radius_cm = seat.diameter / 2 / MM_PER_CM
    cylinder = adsk.fusion.TemporaryBRepManager.get().createCylinderOrCone(
        cm_point(opening.center), radius_cm, cm_point(floor), radius_cm)
    group = component.customGraphicsGroups.add()
    graphics = group.addBRepBody(cylinder)
    # A show-through colour keeps the seat visible inside the solid around it.
    graphics.color = adsk.fusion.CustomGraphicsShowThroughColorEffect.create(
        adsk.core.Color.create(*SEAT_COLOR, 255), SHOW_THROUGH_OPACITY)
    graphics.isSelectable = False
    return group


def cm_point(point_mm):
    return adsk.core.Point3D.create(*(value / MM_PER_CM for value in point_mm))
