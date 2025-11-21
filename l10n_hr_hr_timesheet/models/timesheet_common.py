# -*- coding: utf-8 -*-
from odoo import _

_TIMESHEET_CATEGORIES = {
    # timesheet fields included in user work hours - on timesheet report and work time control wizard
    # keep in sync with work hours on payslip
    'work_hours': (
        'total','overtime','holiday','annual_leave_hours','fieldwork','fieldwork_abroad',
        'sick_leave','maternity_leave','paternity_leave','parental_leave','paid_leave','business_trip','unpaid_leave',
        'work_absence','unpaid_personal_care','sunday_work_hours'
    ),
    # work hours from info3.timesheet wizard which are deduced from total hours (regular hours - RR) when entered
    # night_work is not included because in general it is an addition - check overrides
    # overtime is not included because we expect the (start_time, end_time) input to include it
    # e.g. for 8 regular + 2 overtime hours the expected is (7, 17) or (8, 18)
    'timesheet_wizard_hours': (
        'non_working_sunday','non_working_holiday','annual_leave_hours','overtime','holiday',
        'sick_leave','sick_leave_fund','paid_leave','fieldwork','fieldwork_abroad',
        'maternity_leave','paternity_leave','parental_leave','sunday_work_hours'
    )
}

#function returns uom fields and uom qty field relations
def get_categories():
    return _TIMESHEET_CATEGORIES
