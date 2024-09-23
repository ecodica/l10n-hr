from odoo import fields, models


class PnpCategory(models.Model):
    _name = "l10n.hr.pnp.category"
    _description = "PNP Category"

    name = fields.Char(required=True)
    
    _sql_constraints = [
        ('unique_name', 'unique(name)', 'The name must be unique!')
    ]
