from odoo import api, fields, models, _


class ResConfigSettings(models.TransientModel):
    _inherit = "res.config.settings"

    storno_advance_account_move_name_prefix = fields.Text(
        related='company_id.storno_advance_account_move_name_prefix', 
        readonly=False,
        default="storno avansa"
    )