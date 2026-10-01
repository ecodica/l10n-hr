from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_hr_tax_category_id = fields.Many2one(
        comodel_name='l10n.hr.tax.category',
        string="Tax Category")
    l10n_hr_pass_through_reason_text = fields.Char(
        string="Exemption Reason Text", translate=True,
        help="Names the charge in the exemption reason of a pass-through category, overriding "
             "the category default. Needed where one category carries unlike charges: HR:N is "
             "shared by every levy that is simply not turnover.")

    def write(self, vals):
        return super().write(vals)