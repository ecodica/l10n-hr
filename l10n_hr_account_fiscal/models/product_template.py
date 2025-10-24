from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    l10n_hr_pnp_categ_id = fields.Many2one(
        comodel_name='l10n_hr.pnp.category',
        string="PNP Category",
    )
