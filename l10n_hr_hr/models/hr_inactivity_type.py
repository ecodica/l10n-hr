from odoo import models, fields


class InactivityType(models.Model):
    _name = "hr.inactivity.type"
    _description = "Inactivity type"

    code = fields.Char(size=10)
    name = fields.Char(size=200, required=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
