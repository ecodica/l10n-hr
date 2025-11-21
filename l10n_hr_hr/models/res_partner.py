from odoo import models, fields


class Partner(models.Model):
    _inherit = "res.partner"

    addr_type = fields.Many2one("hr.address.type", string="Addr. Type")
