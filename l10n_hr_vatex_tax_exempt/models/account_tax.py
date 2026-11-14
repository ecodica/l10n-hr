from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_hr_vatex_tax_exempt_id = fields.Many2one(
        comodel_name='l10n.hr.vatex.tax.exempt',
        string="VATEX Tax Exempt")

    @api.constrains('l10n_hr_vatex_tax_exempt_id', 'l10n_hr_tax_category_id')
    def _check_l10n_hr_vatex_tax_exempt_id(self):
        """A VATEX reason is linked only where the tax category states one, see
        l10n.hr.tax.category.exemption_reason_mode. A tax without a category is not restricted."""
        for tax in self:
            if (tax.l10n_hr_vatex_tax_exempt_id
                    and tax.l10n_hr_exemption_reason_mode in ('none', 'pass_through')):
                raise ValidationError(_(
                    "Tax %(tax)s cannot have a VATEX exemption reason: its tax category "
                    "%(category)s does not state one.",
                    tax=tax.display_name, category=tax.l10n_hr_tax_category_id.code))

    @api.onchange('l10n_hr_tax_category_id')
    def _onchange_l10n_hr_tax_category_id_vatex(self):
        if self.l10n_hr_exemption_reason_mode in ('none', 'pass_through'):
            self.l10n_hr_vatex_tax_exempt_id = False
