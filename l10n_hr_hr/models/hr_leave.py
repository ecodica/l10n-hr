# -*- coding: utf-8 -*-
from odoo import api, fields, models
from datetime import datetime, date

class HolidaysType(models.Model):
    _inherit = "hr.leave"

    def _get_duration(self, check_leave_type=True, resource_calendar=None):
        """
        This method is factored out into a separate method from
        _compute_duration so it can be hooked and called without necessarily
        modifying the fields and triggering more computes of fields that
        depend on number_of_hours or number_of_days.
        """
        res = super()._get_duration()

        days_and_hours = self.get_holidays(res)

        return days_and_hours

    def get_holidays(self, days_and_hours):
        """
        Reduce days by number of holidays. Idea is that State Holidays won't be used and we will use Holidays instead.
        """
        days = days_and_hours[0]
        hours = days_and_hours[1]
        holidays = self.env['hr.holiday'].search([('date', '>=', self.date_from), ('date', '<=', self.date_to)])
        if not holidays:
            return days_and_hours
        for holiday in holidays:
            holiday_date = datetime.combine(holiday.date, datetime.min.time())
            is_weekend = holiday_date.weekday() > 4
            if is_weekend:
                continue
            days -= 1
            hours -= 8
        return (days, hours)
