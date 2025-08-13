from odoo import fields, models

class l10n_hr_account_payment_type(models.Model):
    _name = 'l10n_hr.account.payment.type'
    _description = "Croatian Payment Means"

    name = fields.Char()
    code = fields.Char()
    active = fields.Boolean()
