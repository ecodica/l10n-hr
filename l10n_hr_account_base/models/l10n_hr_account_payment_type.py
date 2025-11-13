from odoo import fields, models

class L10nHrAccountPaymentType(models.Model):
    _name = 'l10n_hr.account.payment.type'
    _description = "Croatian Payment Means"

    name = fields.Char(required=True, translate=True, readonly=True)
    code = fields.Char(required=True, readonly=True)
    active = fields.Boolean()
