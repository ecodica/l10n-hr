# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountTax(models.Model):
    _inherit = "account.tax"

    @api.constrains('invoice_repartition_line_ids', 'refund_repartition_line_ids')
    def _validate_repartition_lines(self):
        if not (self.env.context.get('install_mode') and
                self.env.context.get('install_module') == 'l10n_hr_extension'):
            return super()._validate_repartition_lines()
