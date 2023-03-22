from odoo import fields, models, api


class L10nHrJOPPDCodeRegisterPaymentMethod(models.Model):
    _inherit = "l10n.hr.joppd.code.register"
    _name = 'l10n.hr.joppd.code.register.payment.method'
    _description = "JOPPD Code Register Payment Method"

