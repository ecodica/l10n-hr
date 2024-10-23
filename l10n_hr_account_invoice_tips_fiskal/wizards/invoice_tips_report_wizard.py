from odoo import models, fields


class TipsReportWizard(models.TransientModel):
    ''' Extend Wizard for generating Invoice Tips Report. '''
    _inherit = 'l10n.hr.invoice.tips.report.wizard'

    employee_fiscal_id = fields.Many2one(
        comodel_name='res.partner', domain=lambda self: self._get_l10n_hr_fiskal_user_id_domain())
    only_fiscalized_tips = fields.Boolean()
    only_fiscalized_invoices = fields.Boolean(default=True)

    def _get_l10n_hr_fiskal_user_id_domain(self):
        ''' Retrieve domain from mixin '''
        fiscal_mixin = self.env['l10n.hr.fiskal.mixin']
        return fiscal_mixin._get_l10n_hr_fiskal_user_id_domain()

    def _get_invoices_with_tips_domain(self):
        domain = super()._get_invoices_with_tips_domain()
        domain.append(('l10n_hr_napojnica_refund_fiscalized', '=', False))
        if self.employee_fiscal_id:
            domain.append(('l10n_hr_fiskal_user_id', '=', self.employee_fiscal_id.id))
        if self.only_fiscalized_tips:
            domain.append(('l10n_hr_napojnica_is_fiscalized', '=', True))
        if self.only_fiscalized_invoices:
            domain.append(('l10n_hr_zki', '!=', False))
        return domain
