"""The ``l10n_hr.working.hours.schedule`` master model answers a single question:
what are the working hours on a given date for a given business premise?

It stores nothing of its own - it resolves the working hours living on each premise
(regulars by day of week + validity window, exceptions overriding a single date)
into one materialized line per premise/date/shift. These tests drive the resolver
(``premise.get_working_hours_for_date``) and the schedule materialization.
"""
from datetime import date

from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestWorkingHoursSchedule(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Schedule premise",
            "l10n_hr_fiscal_code": "SCHED",
            "company_id": cls.company.id,
        })
        cls.WorkingHours = cls.env["l10n_hr.business.working.hours"]
        cls.Schedule = cls.env["l10n_hr.working.hours.schedule"]

    def _hours(self, **vals):
        return self.WorkingHours.create(dict({
            "business_premise_id": self.premise.id,
            "type": "regular",
            "dow": "1",
            "valid_from": "2026-01-01",
            "time_from": "08:00",
            "time_to": "16:00",
        }, **vals))

    def test_regular_hours_resolved_by_day_of_week(self):
        self._hours(dow="1", time_from="08:00", time_to="16:00")  # Monday
        self._hours(dow="3", time_from="09:00", time_to="17:00")  # Wednesday
        monday = date(2026, 1, 5)
        tuesday = date(2026, 1, 6)
        wednesday = date(2026, 1, 7)

        self.assertEqual(self.premise.get_working_hours_for_date(monday).time_from, "08:00")
        self.assertEqual(self.premise.get_working_hours_for_date(wednesday).time_to, "17:00")
        self.assertFalse(self.premise.get_working_hours_for_date(tuesday), "closed - no Tuesday hours")

    def test_latest_valid_from_wins(self):
        self._hours(dow="1", valid_from="2026-01-01", time_from="08:00", time_to="16:00")
        self._hours(dow="1", valid_from="2026-06-01", time_from="10:00", time_to="18:00")
        # before the new validity window
        self.assertEqual(self.premise.get_working_hours_for_date(date(2026, 3, 2)).time_from, "08:00")
        # after it - only the most recent shift applies
        latest = self.premise.get_working_hours_for_date(date(2026, 9, 7))
        self.assertEqual(latest.time_from, "10:00")
        self.assertEqual(len(latest), 1)

    def test_exception_overrides_regular(self):
        self._hours(dow="4", time_from="08:00", time_to="16:00")  # Thursday regular
        self._hours(type="exception", valid_from=False, valid_on="2026-01-01", dow="4",
                    time_from="00:00", time_to="00:00")  # New Year - closed-ish special
        exceptional = self.premise.get_working_hours_for_date(date(2026, 1, 1))
        self.assertEqual(exceptional.type, "exception")
        self.assertEqual(exceptional.time_to, "00:00")
        # a normal Thursday still uses the regular hours
        self.assertEqual(self.premise.get_working_hours_for_date(date(2026, 1, 8)).time_from, "08:00")

    def test_schedule_materializes_lines_per_date_and_marks_closed(self):
        self._hours(dow="1", time_from="08:00", time_to="16:00")  # Monday only
        schedule = self.Schedule.create({
            "date_from": "2026-01-05",  # Monday
            "date_to": "2026-01-07",  # Wednesday
            "business_premise_ids": [(6, 0, self.premise.ids)],
        })
        schedule.action_compute()

        lines = schedule.line_ids.sorted("date")
        self.assertEqual(len(lines), 3, "one line per day in the range")
        monday, tuesday, wednesday = lines
        self.assertFalse(monday.closed)
        self.assertEqual(monday.time_from, "08:00")
        self.assertEqual(monday.dow, "1")
        self.assertTrue(tuesday.closed)
        self.assertFalse(tuesday.time_from)
        self.assertTrue(wednesday.closed)

    def test_schedule_defaults_to_company_premises(self):
        self._hours(dow="2", time_from="08:00", time_to="16:00")
        schedule = self.Schedule.create({"date_from": "2026-01-06", "date_to": "2026-01-06"})
        schedule.action_compute()
        self.assertIn(self.premise, schedule.line_ids.business_premise_id)
