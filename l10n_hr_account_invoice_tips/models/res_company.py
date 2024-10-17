from odoo import fields, models


class Company(models.Model):
    """ Extend to add configuration field. """
    _inherit = "res.company"

    l10n_hr_enable_tips_on_invoice = fields.Boolean(
        string="Enable Tips", help="If enabled, a field for manual tip entry is visible on the outgoing invoices form"
    )
