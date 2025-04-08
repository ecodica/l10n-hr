from odoo import fields, models


class ResCompany(models.Model):
    """Extend to add configuration"""
    _inherit = 'res.company'

    l10n_hr_fiscal_number_as_move_name = fields.Boolean(
        string="Use Fiscal Number As Move Name",
        help="Documents that have a Fiscal Number set will use it as name on account move."
    )
