# Copyright 2024 Tecnativa - David Vidal
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from datetime import datetime, timedelta

import pytz

from odoo import api, models
from odoo.tools import groupby

from odoo.addons.resource.models.utils import string_to_datetime


class ResourceCalendar(models.Model):
    _inherit = "resource.calendar"

    @api.model
    def _resource_shift_for_datetime_range(self, start_dt, end_dt, resources, tz=None):
        min_time = datetime.combine(
            start_dt, start_dt.min.time(), tzinfo=tz or pytz.UTC
        )
        max_time = datetime.combine(end_dt, end_dt.max.time(), tzinfo=tz or pytz.UTC)
        # Overlap: night shifts end on the next day
        shifts = self.env["hr.shift.planning.line"].search(
            [
                ("resource_id", "in", resources.ids),
                ("state", "=", "assigned"),
                ("start_time", "<=", max_time),
                ("end_time", ">=", min_time),
            ]
        )
        return shifts

    def _attendance_intervals_batch(
        self, start_dt, end_dt, resources=None, domain=None, tz=None, lunch=False
    ):
        # Override calendar intervals when a shift is found and substitute those
        # intervals with the ones on the shift
        # TODO: deal with TZ!
        res = super()._attendance_intervals_batch(
            start_dt, end_dt, resources, domain, tz, lunch
        )
        if resources and not lunch:
            shift_ids = self._resource_shift_for_datetime_range(
                start_dt, end_dt, resources, tz=tz
            )
            # Day-expanded window bounds (local days of the range): a night shift
            # belongs whole to the day it starts on, to avoid leaking hours of
            # other days into the result.
            local_start = start_dt.astimezone(tz or pytz.UTC)
            # end_dt is exclusive. start_dt == end_dt keeps the start day, as
            # existing tests request a single day this way.
            local_end = max(
                local_start,
                (end_dt - timedelta(microseconds=1)).astimezone(tz or pytz.UTC),
            )
            window_start = (tz or pytz.UTC).localize(
                datetime.combine(local_start, local_start.min.time())
            )
            window_end = (tz or pytz.UTC).localize(
                datetime.combine(local_end, local_end.max.time())
            )
            for resource, shifts in groupby(shift_ids, lambda x: x.resource_id):
                intervals_to_add = []
                intervals_to_remove = []
                resource_intervals = res[resource.id]._items
                for shift in shifts:
                    start_time = string_to_datetime(shift.start_time).astimezone(tz)
                    end_time = string_to_datetime(shift.end_time).astimezone(tz)
                    # Remove any other interval that belongs to any of the dates of the
                    # shift (no matter the hours, as if the shift is around midnight,
                    # there will be a mix of 2 dates). Local dates on both sides.
                    intervals_to_remove += [
                        (start, end, resource_item)
                        for start, end, resource_item in resource_intervals
                        if (
                            start_time.date() == start.date()
                            or end_time.date() == end.date()
                        )
                    ]
                    # Only shifts starting within the window are added, whole
                    # and unclamped (tails of previous day shifts are skipped)
                    if not window_start <= start_time <= window_end:
                        continue
                    intervals_to_add.append((start_time, end_time, shift))
                res[resource.id]._items = [
                    x for x in resource_intervals if x not in intervals_to_remove
                ] + intervals_to_add
        return res
