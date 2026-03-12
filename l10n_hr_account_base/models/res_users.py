from odoo import api, models, fields


class ResUsers(models.Model):
    _inherit = 'res.users'

    company_registry = fields.Char(related='partner_id.company_registry', readonly=False)
