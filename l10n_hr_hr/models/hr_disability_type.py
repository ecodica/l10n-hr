from odoo import fields, models


class DisabilityType(models.Model):
    _name = "hr.disability.type"
    _description = "Disability type"
    _order = "code"

    code = fields.Char(size=7)
    name = fields.Char(size=256, required=True)
    description = fields.Char(size=512)
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
