from odoo import fields, models


class ProductTemplate(models.Model):
    _inherit = "product.template"

    pnp_categ_id = fields.Many2one(        
        comodel_name='l10n.hr.pnp.category',
        string="PNP Category",
    )
