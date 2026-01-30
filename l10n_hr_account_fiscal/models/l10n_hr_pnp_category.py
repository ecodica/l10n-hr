from odoo import fields, models


class L10nHrPnpCategory(models.Model):
    _name = "l10n_hr.pnp.category"
    _description = "PNP Category"

    name = fields.Char(required=True)
    
    _unique_name = models.Constraint(
        'unique(name)',
        "The name must be unique!",
    )
