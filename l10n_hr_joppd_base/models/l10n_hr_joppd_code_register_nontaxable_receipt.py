from odoo import fields, models, api


class L10nHrJOPPDCodeRegisterNonTaxableReceipt(models.Model):
    _inherit = "l10n.hr.joppd.code.register"
    _name = 'l10n.hr.joppd.code.register.nontaxable.receipt'
    _description = "JOPPD Code Register - Non-taxable Receipt"

