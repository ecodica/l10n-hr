from odoo import models, fields


class AddressType(models.Model):
    _name = 'hr.address.type'
    _description = "Address Type"

    name = fields.Char(required=True, translate=True)
