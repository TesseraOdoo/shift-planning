# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime

import pytz

from odoo import api, models

from odoo.addons.resource.models.utils import string_to_datetime


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    @api.model
    def _resource_shift_for_datetime_range(self, start_dt, end_dt, resources, tz=None):
        shifts = super()._resource_shift_for_datetime_range(
            start_dt, end_dt, resources, tz=tz
        )
        if self.env.context.get("shift_leave_request_unit") in ("day", "half_day"):
            # For leave duration computations a shift belongs to the day it
            # starts on: the tail of a night shift started before the leave
            # period is not covered by the leave.
            min_time = (
                datetime.combine(start_dt, start_dt.min.time(), tzinfo=tz or pytz.UTC)
                .astimezone(pytz.UTC)
                .replace(tzinfo=None)
            )
            shifts = shifts.filtered(lambda shift: shift.start_time >= min_time)
        return shifts

    def _attendance_intervals_batch(
        self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False
    ):
        res = super()._attendance_intervals_batch(
            start_dt, end_dt, resources, domain, tz, lunch
        )
        request_unit = self.env.context.get("shift_leave_request_unit")
        if resources and not lunch and request_unit in ("day", "half_day"):
            # A day based leave covers the whole shift starting on that day,
            # so restore the full shift span that hr_shift clamped to the
            # requested window (night shifts end past midnight). Half day
            # leaves cover half of the shift hours: only the duration matters
            # for the computation, so which half is not relevant.
            for resource in resources:
                items = []
                for start, stop, record in res[resource.id]._items:
                    if record._name == "hr.shift.planning.line" and len(record) == 1:
                        start = string_to_datetime(record.start_time).astimezone(
                            start.tzinfo
                        )
                        stop = string_to_datetime(record.end_time).astimezone(
                            stop.tzinfo
                        )
                        if request_unit == "half_day":
                            start = start + (stop - start) / 2
                    items.append((start, stop, record))
                res[resource.id]._items = items
        return res
