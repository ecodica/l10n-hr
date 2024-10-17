from odoo import api, models, fields, _
from odoo.exceptions import ValidationError


class TipsReportWizard(models.TransientModel):
    ''' Wizard for generating Invoice Tips Report. '''
    _name = 'l10n.hr.invoice.tips.report.wizard'
    _description = 'Wizard to Generate Tips Report'

    date_from = fields.Date(default=fields.Date.today, required=True)
    date_to = fields.Date(default=fields.Date.today, required=True)
    employee_id = fields.Many2one(comodel_name='res.users')

    @api.onchange('date_from', 'date_to')
    def _onchange_date_from_to(self):
        if self.date_from > self.date_to:
            raise ValidationError(_("Date From cannot be greater than Date To."))

    def print_report(self):
        """Print tips report."""
        data = self._prepare_report_invoice_tips()
        return self.env.ref(
            'l10n_hr_account_invoice_tips.action_report_l10n_hr_invoice_tips').report_action(self, data=data)

    def _prepare_report_invoice_tips(self):
        domain = self._get_invoices_with_tips_domain()
        return {
            'wizard_id': self.id,
            'date_from': self.date_from,
            'date_to': self.date_to,
            'domain': domain,
        }

    def _get_invoices_with_tips_domain(self):
        self.ensure_one()
        domain = [
            ('invoice_date', '>=', self.date_from),
            ('invoice_date', '<=', self.date_to),
            ('move_type', 'in', ('out_invoice', 'out_refund')),
            ('l10n_hr_napojnica_iznos', '>', 0)
        ]
        if self.employee_id:
            domain.append(('invoice_user_id', '=', self.employee_id.id))
        return domain
