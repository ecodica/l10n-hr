from odoo import models, fields, api


class AccountTax(models.Model):
    _inherit = 'account.tax'

    l10n_hr_tax_category_id = fields.Many2one(
        comodel_name='l10n.hr.tax.category',
        string="Tax Category")
    l10n_hr_exemption_reason_mode = fields.Selection(
        related='l10n_hr_tax_category_id.exemption_reason_mode')
    l10n_hr_pass_through_reason_text = fields.Char(
        string="Exemption Reason Text",
        compute='_compute_l10n_hr_pass_through_reason_text', store=True, readonly=False, copy=True,
        help="Exemption reason of a pass-through charge, written to the eRačun exactly as it "
             "stands here. Proposed when the tax category is chosen as #<category code>#<default "
             "exemption reason of the category, or the tax name where the category has none>.")

    @api.depends('l10n_hr_tax_category_id')
    def _compute_l10n_hr_pass_through_reason_text(self):
        # the reason addresses the Croatian tax authority, so it is proposed in Croatian
        lang = self.env['res.lang']._get_code('hr_HR') or None
        for tax in self:
            tax_hr = tax.with_context(lang=lang)
            category_id = tax_hr.l10n_hr_tax_category_id
            if category_id.exemption_reason_mode == 'pass_through':
                tax.l10n_hr_pass_through_reason_text = '#{}#{}'.format(
                    category_id.code, category_id.pass_through_reason_text or tax_hr.name or '')
            else:
                tax.l10n_hr_pass_through_reason_text = False

    def write(self, vals):
        return super().write(vals)