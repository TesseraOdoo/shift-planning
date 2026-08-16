# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl).
from odoo.addons.hr_shift.tests.common import TestHrShiftBase


class TestHrShiftHolidays(TestHrShiftBase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.planning = cls.env["hr.shift.planning"].create(
            {
                "year": 2025,
                "week_number": 3,
                "start_date": "2025-01-13",
                "end_date": "2025-01-19",
            }
        )
        cls.leave_type = cls.env["hr.leave.type"].create(
            {
                "name": "Test leave",
                "requires_allocation": "no",
                "leave_validation_type": "no_validation",
                "request_unit": "half_day",
            }
        )
        cls.planning.generate_shifts()
        cls.shift_a = cls.planning.shift_ids.filtered(
            lambda x: x.employee_id == cls.employee_a
        )
        cls.line_0 = cls.shift_a.line_ids.filtered(lambda x: x.day_number == "0")

    def _create_leave(self, **extra_vals):
        vals = {
            "employee_id": self.employee_a.id,
            "holiday_status_id": self.leave_type.id,
            "request_date_from": "2025-01-13",
            "request_date_to": "2025-01-13",
        }
        vals.update(extra_vals)
        return self.env["hr.leave"].create(vals)

    def test_full_day_leave_on_shift(self):
        self.line_0.template_id = self.template_morning  # 6 hours long
        leave = self._create_leave()
        self.assertEqual(leave.number_of_hours, 6.0)

    def test_half_day_leave_on_shift(self):
        self.line_0.template_id = self.template_morning
        leave = self._create_leave(
            request_unit_half=True, request_date_from_period="am"
        )
        self.assertEqual(leave.number_of_hours, 3.0)
        # The shift line is still a (partially) working shift
        self.assertFalse(self.line_0._is_on_leave())

    def test_full_day_leave_on_night_shift(self):
        template_night = self.env["hr.shift.template"].create(
            {
                "name": "Night shift",
                "start_time": 22.0,
                "end_time": 6.0,
                "tz": "UTC",
            }
        )
        self.line_0.template_id = template_night
        # The whole night shift is covered even if it ends on the next day
        leave = self._create_leave()
        self.assertEqual(leave.number_of_hours, 8.0)

    def test_leave_next_day_not_covering_previous_night_shift(self):
        # A full day leave on Tuesday must not count the hours of a night
        # shift started on Monday, even if it ends on Tuesday morning
        template_night = self.env["hr.shift.template"].create(
            {
                "name": "Night shift",
                "start_time": 22.0,
                "end_time": 6.0,
                "tz": "UTC",
            }
        )
        self.line_0.template_id = template_night
        leave = self._create_leave(
            request_date_from="2025-01-14", request_date_to="2025-01-14"
        )
        # Tuesday has no shift assigned, so the calendar hours apply (8h) and
        # Monday's night shift hours are not added on top
        self.assertEqual(leave.number_of_hours, 8.0)
        # And Monday's shift is still a working shift
        self.assertEqual(self.line_0.state, "assigned")
