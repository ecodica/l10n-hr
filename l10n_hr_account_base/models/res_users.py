from odoo import fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # res.users has no company_registry of its own in Odoo 19; expose the
    # partner's (core, computed) field for the user preferences form.
    company_registry = fields.Char(related='partner_id.company_registry')
