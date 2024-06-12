from odoo import fields, models


class L10nHrJOPPDCodeRegistryCityMunicipality(models.Model):
    _inherit = "l10n.hr.joppd.code.register"
    _name = "l10n.hr.joppd.code.register.city.municipality"
    _description = "JOPPD Code Register City/Municipality"

    regos_code = fields.Char('REGOS Code', size=4)
    joppd_code = fields.Char('JOPPD Code', size=5)
    local_tax_pct = fields.Float('Stopa prireza(%)')
    iban = fields.Char('IBAN')
