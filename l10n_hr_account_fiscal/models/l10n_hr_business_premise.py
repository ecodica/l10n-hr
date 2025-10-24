from odoo import fields, models


class L10nHrBusinessPremise(models.Model):
    _inherit = "l10n_hr.business.premise"

    l10n_hr_fiscal_log_ids = fields.One2many(
        comodel_name="l10n_hr.fiscal.log",
        inverse_name="business_premise_id",
        string="Fiscal message logs",
        help="Log of all messages sent and received for FINA",
    )

    def l10n_hr_fiscal_echo(self):
        self.company_id.button_test_echo(self)

