# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class HrLeave(models.Model):
    _inherit = "hr.leave"

    def _get_durations(self, check_leave_type=True, resource_calendar=None):
        """Flag the leave request unit in the context so the shift based
        attendance intervals can be adapted accordingly (see resource_calendar)"""
        result = {}
        half_leaves = self.filtered("request_unit_half")
        hour_leaves = (self - half_leaves).filtered("request_unit_hours")
        day_leaves = self - half_leaves - hour_leaves
        if day_leaves:
            result.update(
                super(
                    HrLeave, day_leaves.with_context(shift_leave_request_unit="day")
                )._get_durations(check_leave_type, resource_calendar)
            )
        if half_leaves:
            result.update(
                super(
                    HrLeave,
                    half_leaves.with_context(shift_leave_request_unit="half_day"),
                )._get_durations(check_leave_type, resource_calendar)
            )
        if hour_leaves:
            result.update(
                super(HrLeave, hour_leaves)._get_durations(
                    check_leave_type, resource_calendar
                )
            )
        return result
