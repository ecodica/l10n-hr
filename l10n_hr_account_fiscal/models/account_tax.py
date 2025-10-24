# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).

from odoo import api, fields, models


class AccountTax(models.Model):
    _inherit = "account.tax"

    l10n_hr_fiscal_type = fields.Selection(
        selection=[
            ("Pdv", "PDV"),
            ("Pnp", "Porez na potrosnju"),
            ("OstaliPor", "Ostali porezi"),
            ("oslobodenje", "Oslobodjenje"),
            ("marza", "Oporezivanje marze"),
            ("ne_podlijeze", "Ne podlijeze oporezivanju"),
            ("Naknade", "Naknade (npr. ambalaza)"),
        ],
        string="Fiscal type",
    )
