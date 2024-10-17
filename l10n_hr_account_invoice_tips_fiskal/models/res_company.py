from odoo import fields, models


class Company(models.Model):
    """Extend to add tip fiskalization fields."""
    _inherit = "res.company"

    l10n_hr_fiskal_tip_on_confirm = fields.Boolean(
        string="Fiscalize Invoice Tip On Confirmation", default=True, tracking=1,
        help="""Invoice tip will be fiskalized on confirmation"""
    )
