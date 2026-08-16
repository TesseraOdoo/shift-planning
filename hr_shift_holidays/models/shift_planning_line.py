# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo import models


class ShiftPlanningLine(models.Model):
    _inherit = "hr.shift.planning.line"

    def _get_is_on_leave_domain(self, start_time, end_time):
        # Half day and hour based leaves don't cover the whole shift, so the
        # employee is still expected to work part of it and the line must not
        # be flagged as on leave
        return super()._get_is_on_leave_domain(start_time, end_time) + [
            ("holiday_id.request_unit_half", "=", False),
            ("holiday_id.request_unit_hours", "=", False),
        ]
