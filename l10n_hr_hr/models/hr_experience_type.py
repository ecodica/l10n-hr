from odoo import fields, models


class ExperienceType(models.Model):
    _name = "hr.experience.type"
    _description = "Experience type"
    _order = "code"

    code = fields.Char(required=True)
    name = fields.Char(size=256, required=True)
    description = fields.Char(size=512)
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
