from odoo import models
from odoo.addons.account.models.chart_template import template


class AccountChartTemplate(models.AbstractModel):
    _inherit = 'account.chart.template'

    @template('hr', 'account.tax')
    def _get_hr_vatex_tax_exempt_account_tax(self):
        data = self._parse_csv('hr', 'account.tax', module='l10n_hr_vatex_tax_exempt')
        return data
