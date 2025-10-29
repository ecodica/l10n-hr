from odoo import fields, models


class L10nHrFiscalDevice(models.Model):
    _inherit = "l10n_hr.fiscal.device"

    fiscalization_active = fields.Boolean()

    def button_l10n_hr_fiscal_echo(self):
        self.l10n_hr_business_premise.company_id.button_test_echo(self)
