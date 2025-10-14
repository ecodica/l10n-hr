from odoo import fields, models

class l10n_hr_account_payment_type(models.Model):
    _name = 'l10n_hr.account.payment.type'
    _description = "Croatian Payment Means"

    name = fields.Char(string="Name", required=True, translate=True)
    code = fields.Char(string="Code", required=True)
    active = fields.Boolean()
