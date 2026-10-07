# Copyright 2026 Tesseratech - Abraham Anes
# License AGPL-3.0 or later (https://www.gnu.org/licenses/agpl.html).
from .common import TestHrShiftBase


class TestHrShiftAddNewEmployees(TestHrShiftBase):
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

    def test_hr_shift_add_new_employees(self):
        """New employees are added to generated plannings without touching the
        shifts already assigned"""
        self.planning.generate_shifts()
        shift_a = self.planning.shift_ids.filtered(
            lambda x: x.employee_id == self.employee_a
        )
        shift_a.template_id = self.template_morning
        shift_a.line_ids.filtered(lambda x: x.day_number == "4").template_id = False
        self.planning.state = "planned"
        other_planning = self.env["hr.shift.planning"].create(
            {"year": 2025, "week_number": 4}
        )
        other_planning.generate_shifts()
        shifts_count = len(self.planning.shift_ids)
        self.employee_c.shift_planning = True
        (self.planning | other_planning).action_add_new_employees()
        for planning in self.planning | other_planning:
            self.assertIn(self.employee_c, planning.shift_ids.employee_id)
            self.assertEqual(len(planning.shift_ids), shifts_count + 1)
        self.assertEqual(self.planning.state, "planned")
        self.assertEqual(other_planning.state, "assignment")
        self.assertTrue(shift_a.exists())
        self.assertEqual(shift_a.template_id, self.template_morning)
        self.assertEqual(
            shift_a.line_ids.filtered(lambda x: x.day_number == "4").state,
            "unassigned",
        )
        # Plannings not generated yet are left alone
        new_planning = self.env["hr.shift.planning"].create(
            {"year": 2025, "week_number": 5}
        )
        new_planning.action_add_new_employees()
        self.assertFalse(new_planning.shift_ids)
        self.assertEqual(new_planning.state, "new")
