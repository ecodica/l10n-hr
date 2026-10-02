from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_hr_vatex_tax_exempt_id = fields.Many2one(
        comodel_name='l10n.hr.vatex.tax.exempt',
        string="VATEX Tax Exempt",
        help="VATEX code stating why this tax carries no VAT. The codebook covers only supplies "
             "that are genuinely exempt from VAT or zero rated, so leave it empty for a charge "
             "that is merely collected on behalf of a third party and stays outside the VAT base "
             "(čl. 33. st. 3) - no VATEX code describes such a charge.")
