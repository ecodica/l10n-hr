# -*- coding: utf-8 -*-
from odoo import api, fields, models


class HolidaysType(models.Model):
    _inherit = "hr.leave.type"

    i3_leave_type = fields.Selection([
        ('annual_leave', 'Annual leave'),
        ('sick_leave', 'Sick leave'),
        ('sick_leave_fund', 'Sick leave paid by fund'),
        ('maternity_leave', 'Maternity leave'),
        ('parental_leave', 'Parental leave'),
        ('paid_leave', 'Paid leave'),
        ('unpaid_leave', 'Unpaid leave'),
        ('free_days', 'Free days')
        ], 'Leave type')
