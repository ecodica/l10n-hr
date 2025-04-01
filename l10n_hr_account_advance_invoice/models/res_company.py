from odoo import api, fields, models, _

class ResCompany(models.Model):
    _inherit = "res.company"

    storno_advance_account_move_name_prefix = fields.Text()