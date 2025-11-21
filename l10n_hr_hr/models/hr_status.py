from odoo import fields, models


class Status(models.Model):
    _name = "hr.status"
    _description = "Status"

    name = fields.Char(size=128, required=True, translate=True)
