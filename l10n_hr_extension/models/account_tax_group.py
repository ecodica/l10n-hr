# -*- coding: utf-8 -*-

from odoo import api, fields, models, _


class AccountTaxGroup(models.Model):
    _inherit = "account.tax.group"

    @api.constrains('tax_payable_account_id', 'tax_receivable_account_id')
    def _check_accounts_configuration(self):
        if not (self.env.context.get('install_mode') and
                self.env.context.get('install_module') == 'l10n_hr_extension'):
            return super()._check_accounts_configuration()
