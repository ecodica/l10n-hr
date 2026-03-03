# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_hr_fiskal_type = fields.Selection(
        selection=[
            ("Pdv", "PDV"),
            ("Pnp", "Porez na potrosnju"),
            ("OstaliPor", "Ostali porezi"),
            ("oslobodenje", "Oslobodjenje"),
            ("marza", "Oporezivanje marze"),
            ("ne_podlijeze", "Ne podlijeze oporezivanju"),
            ("Naknade", "Naknade (npr. ambalaza)"),
        ],
        string="Fiskal tax type",
    )

    @api.model
    def _get_tax_totals_summary(self, base_lines, currency, company, cash_rounding=None):
        """Extend to send information if company is in tax system or not."""
        result = super()._get_tax_totals_summary(base_lines, currency, company, cash_rounding=cash_rounding)
        result.update({'l10n_hr_fiskal_taxative': self.env.company.l10n_hr_fiskal_taxative})
        return result
