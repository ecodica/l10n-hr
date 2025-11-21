from odoo import fields, models


class Job(models.Model):
    _inherit = "hr.job"

    coefficient = fields.Float(digits=(1, 4))
    code = fields.Char(string="Šifra")
    # translate flag should be True -> it was set to False here before, we keep the flag so it changes on module update
    name = fields.Char(string='Job Position', required=True, index=True, translate=True)
