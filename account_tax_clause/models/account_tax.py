# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountTax(models.Model):
    _inherit = "account.tax"

    tax_clause = fields.Text(string='Tax Clause', translate=True)
