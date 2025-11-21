from odoo import models, fields


class TransportationType(models.Model):
    _name = "hr.transportation.type"
    _description = 'Transportation type'

    code = fields.Char(size=10)
    name = fields.Char(size=50, required=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
