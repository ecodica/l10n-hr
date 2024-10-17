from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    """ Extend to add configuration field. """
    _inherit = 'res.config.settings'

    l10n_hr_enable_tips_on_invoice = fields.Boolean(
        related='company_id.l10n_hr_enable_tips_on_invoice',
        readonly=False,
        help='If enabled, a field for manual tip entry is visible on the outgoing invoices form')
