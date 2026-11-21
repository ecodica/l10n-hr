from odoo import api, fields, models, _
from odoo.exceptions import UserError


class L10nHrFiscalDevice(models.Model):
    _inherit = "l10n_hr.fiscal.device"

    fiscalization_active = fields.Boolean()
    enable_fiscalize_on_confirm = fields.Boolean(help="""
            If enabled, invoices on this fiscal device are automatically
            fiscalized when posted. If disabled, posting leaves the invoice
            unfiscalized: no ZKI is generated, nothing is sent to FINA and
            nothing is queued - fiscalization is started by hand, with the
            Fiscalize button or the batch fiscalization action.
            """)
    enable_cron_fiscalization = fields.Boolean(
        default=True,
        help="The automated job retries invoices whose fiscalization was "
             "already attempted (a ZKI without a JIR) once the delay below "
             "has passed. Invoices never fiscalized are not touched.")
    cron_fiscalization_delay_hours = fields.Integer(help="""
            Number of hours an invoice on this fiscal device can remain in unfiscalized state
            after its posting time before the automated job will check it and attempt to fiscalize it again.
            The automated job will select a record to process only if:
            - Posting Time + Delay < Current Time
            """, default=12)

    @api.onchange('cron_fiscalization_delay_hours')
    def _onchange_cron_fiscalization_delay_hours(self):
        if not isinstance(self.cron_fiscalization_delay_hours,
                          int) or not 1 <= self.cron_fiscalization_delay_hours <= 24:
            raise UserError(_("Fiscalization delay must be between 1 and 24 hours."))

    def button_l10n_hr_test_fiscal_echo(self):
        self.l10n_hr_business_premise_id.company_id.button_l10n_hr_test_fiscal_echo(self)
