from odoo import models, fields


class Department(models.Model):
    _inherit = "hr.department"

    code = fields.Char(size=32)
