from odoo import fields, models, api, _
from odoo.exceptions import ValidationError


class L10nHrBusinessPremise(models.Model):
    _inherit = "l10n_hr.business.premise"

    def button_l10n_hr_fiskal_echo(self):
        self.company_id.button_test_echo(self)


class L10nHrFiscalDevice(models.Model):
    _inherit = "l10n_hr.fiscal.device"

    fiskalisation_active = fields.Boolean()
    enable_fiskalise_on_confirm = fields.Boolean(help="""
        If enabled, account moves on this fiscal device will be
        automatically fiscalized in account moves posting process
        """
    )
    enable_cron_fiskalisation = fields.Boolean(default=True)
    cron_fiskalisation_delay_hours = fields.Integer(help="""
        Number of hours an invoice on this fiscal device can remain in unfiscalized state
        after its posting time before the automated job will check it and attempt to fiscalize it again.
        The automated job will select a record to process only if:
        - Posting Time + Delay < Current Time
        """,
        default=12
    )

    def button_l10n_hr_fiskal_echo(self):
        self.l10n_hr_business_premise_id.company_id.button_test_echo(self)

    @api.onchange('cron_fiskalisation_delay_hours')
    def _onchange_cron_fiskalisation_delay_hours(self):
        if not isinstance(self.cron_fiskalisation_delay_hours, int) or not 1 <= self.cron_fiskalisation_delay_hours <= 240:
            raise ValidationError(_("Fiscalization delay must be between 1 and 240 hours."))
