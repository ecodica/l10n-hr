

from odoo import fields, models, api, _


class Company(models.Model):
    _inherit = 'res.company'

    def _get_invoice_reference_types(self):
        res = super(Company, self)._get_invoice_reference_types()
        res.append(('per_journal', 'Defined on journal'))
        return res
