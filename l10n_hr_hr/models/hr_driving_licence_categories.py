from odoo import models, fields


class DrivingLicenceCategory(models.Model):
    _name = "hr.driving_licence.category"
    _description = "Categories for driving licence"

    name = fields.Char(string="Category name", size=50, required=True)
    code = fields.Char(size=10)
    description = fields.Text()
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
