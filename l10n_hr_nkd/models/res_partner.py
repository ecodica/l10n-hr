from odoo import fields, models


class Partner(models.Model):
    _inherit = "res.partner"

    nace_id = fields.Many2one(
        help="Main occupation classified according to EU NACE 2.0 / NKD-2007",
    )
