# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from odoo.tests import Form

from .common import TestHrShiftBase


class TestHrShiftCopyDetails(TestHrShiftBase):
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

    def test_hr_shift_copy_shift_details_days_off(self):
        """Copying the details keeps the days off of each employee, e.g. a week
        that starts on Sunday night and ends on Thursday"""
        self.company.shift_end_day = "6"
        self.template_morning.write({"day_of_week_start": "0", "day_of_week_end": "6"})
        self.env["resource.calendar.leaves"].create(
            {
                "calendar_id": self.employee_a.resource_calendar_id.id,
                "resource_id": self.employee_a.resource_id.id,
                "date_from": "2025-01-15 08:00:00",
                "date_to": "2025-01-15 17:00:00",
            }
        )
        self.planning.generate_shifts()
        shift_a = self.planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        shift_a.template_id = self.template_morning
        self.assertEqual(len(shift_a.line_ids), 7)
        days = {line.day_number: line for line in shift_a.line_ids}
        self.assertEqual(days["2"].state, "on_leave")
        days["4"].template_id = False
        days["5"].template_id = False
        days["6"].template_id = self.template_afternoon
        wizard_form = Form(self.env["shift.planning.wizard"])
        wizard_form.copy_shift_details = True
        res = wizard_form.save().generate()
        new_planning = self.env[res["res_model"]].browse(res["res_id"])
        new_shift_a = new_planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        self.assertEqual(new_shift_a.template_id, self.template_morning)
        new_days = {line.day_number: line for line in new_shift_a.line_ids}
        for day in ("0", "1", "3"):
            self.assertEqual(new_days[day].template_id, self.template_morning)
        # The leave of the source week says nothing about the usual shift
        self.assertEqual(new_days["2"].template_id, self.template_morning)
        # Days off stay off and the Sunday keeps its own shift
        self.assertEqual(new_days["4"].state, "unassigned")
        self.assertEqual(new_days["5"].state, "unassigned")
        self.assertEqual(new_days["6"].template_id, self.template_afternoon)
        # Without details, the whole week gets the shift template
        wizard_form = Form(self.env["shift.planning.wizard"])
        res = wizard_form.save().generate()
        new_planning = self.env[res["res_model"]].browse(res["res_id"])
        new_shift_a = new_planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        self.assertEqual(
            set(new_shift_a.line_ids.mapped("template_id")), {self.template_morning}
        )

    def test_hr_shift_copy_shift_details_extra_days(self):
        """Days worked out of the days of the shift template are copied too,
        e.g. a night shift week that starts on Sunday"""
        self.company.shift_end_day = "6"
        self.planning.generate_shifts()
        shift_a = self.planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        # The template covers from Monday to Friday
        shift_a.template_id = self.template_morning
        self.assertEqual(len(shift_a.line_ids), 5)
        self.env["hr.shift.planning.line"].create(
            {
                "shift_id": shift_a.id,
                "day_number": "6",
                "template_id": self.template_afternoon.id,
            }
        )
        shift_a.line_ids.filtered(lambda x: x.day_number == "0").template_id = False
        wizard_form = Form(self.env["shift.planning.wizard"])
        wizard_form.copy_shift_details = True
        res = wizard_form.save().generate()
        new_planning = self.env[res["res_model"]].browse(res["res_id"])
        new_shift_a = new_planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        new_days = {line.day_number: line for line in new_shift_a.line_ids}
        self.assertEqual(sorted(new_days), ["0", "1", "2", "3", "4", "6"])
        self.assertEqual(new_days["0"].state, "unassigned")
        self.assertEqual(new_days["1"].template_id, self.template_morning)
        self.assertEqual(new_days["6"].template_id, self.template_afternoon)
