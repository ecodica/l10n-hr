# -*- coding: utf-8 -*-
from odoo import models, fields, api

class DateRange(models.Model):
    _inherit = "date.range"

    fiscal_year = fields.Many2one(
        'account.fiscal.year',
        string="Fiscal year",
        domain="[('company_id', '=', company_id)]"
    )
    
    can_user_close = fields.Boolean(compute='_compute_can_user_close_period')


    def _compute_can_user_close_period(self):
        has_group = self.env.user.has_group('hr_account.group_can_close_period')
        for rec in self:
            rec.can_user_close = has_group