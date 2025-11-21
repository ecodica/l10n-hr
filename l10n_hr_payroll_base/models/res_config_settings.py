# -*- coding: utf-8 -*-

from odoo import fields, models, _
from odoo.tools.misc import formatLang
from decimal import Decimal, ROUND_HALF_UP


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    module_account_accountant = fields.Boolean(string='Account Accountant')
    module_l10n_fr_hr_payroll = fields.Boolean(string='French Payroll')
    module_l10n_be_hr_payroll = fields.Boolean(string='Belgium Payroll')
    module_l10n_in_hr_payroll = fields.Boolean(string='Indian Payroll')


## From hr_account> models > res_config_settings.py

    secondary_currency_enable = fields.Boolean(related='company_id.secondary_currency_enable', readonly=False)
    secondary_currency_id = fields.Many2one('res.currency', related='company_id.secondary_currency_id', readonly=False)
    secondary_currency_rate = fields.Float(related='company_id.secondary_currency_rate', readonly=False)
    secondary_currency_multiply_rate = fields.Boolean(related='company_id.secondary_currency_multiply_rate', readonly=False)
    secondary_currency_all_partners = fields.Boolean(related='company_id.secondary_currency_all_partners', readonly=False)
    secondary_currency_apply_date = fields.Date(related='company_id.secondary_currency_apply_date', readonly=False)
    external_report_invoice_layout_id = fields.Many2one(related="company_id.external_report_invoice_layout_id", readonly=False)
    invoice_posting_date_default = fields.Selection(related='company_id.invoice_posting_date_default', readonly=False)
    
    @property
    def _active_company(self):
        return self.env.user.company_id

    def _display_secondary_currency(self):
        return (
            self._active_company.secondary_currency_enable and
            self._active_company.secondary_currency_id and
            self._active_company.secondary_currency_rate or
            False
        )

    def _get_secondary_currency(self):
        return self._active_company.secondary_currency_id

    def _get_secondary_currency_rate(self):
        return self._active_company.secondary_currency_rate

    def _get_secondary_currency_multiply_rate(self):
        return self._active_company.secondary_currency_multiply_rate

    def _get_secondary_currency_all_partners(self):
        return self._active_company.secondary_currency_all_partners

    def _get_secondary_currency_apply_date(self):
        return self._active_company.secondary_currency_apply_date

    def _calculate_secondary_currency_amount(self, amount, precision, currency_rate, currency_multiply_rate):
        if not amount or not currency_rate:
            return 0.0
        if currency_multiply_rate:
            amount *= currency_rate
        else:
            amount /= currency_rate
        return float(Decimal(str(amount)).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP))

    def _convert_secondary_currency_amount(self, amount):
        currency = self._get_secondary_currency()
        currency_rate = self._get_secondary_currency_rate()
        currency_multiply_rate = self._get_secondary_currency_multiply_rate()
        return self._calculate_secondary_currency_amount(amount, currency.rounding, currency_rate, currency_multiply_rate)

    def _secondary_currency_rate_text(self):
        """Default text to use as label for fixed secondary currency conversion rate on reports"""
        currency_rate = self._get_secondary_currency_rate()
        formated_currency_rate = formatLang(self.env, currency_rate, digits=5)
        return _("Fixed currency rate: {}").format(formated_currency_rate)

    def _secondary_currency_amount_text(self):
        """ Default text to use as label for amount in secondary currency on reports"""
        currency = self._get_secondary_currency()
        if not currency:
            return ''
        return _('Informational amount in {}').format(currency.name)