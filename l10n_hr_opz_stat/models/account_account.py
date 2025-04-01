from odoo import models, fields, api, _


class AccountAccount(models.Model):
    _inherit = "account.account"

    exclude_from_opz_stat = fields.Boolean("Exclude from OPZ-STAT", default=False)
