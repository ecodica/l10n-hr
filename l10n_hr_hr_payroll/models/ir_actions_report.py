from odoo import models, api, fields, _

_PAYROLL_CUSTOM_REPORTS = [
    'joppd_form_a',
    'report_additional_income',
    'report_fees_earnings',
    'report_hr_payslip_confirmation',
    'report_hr_payslip_run_recap',
    'report_work_statistics',
    'report_hr_payslip_run_suspensions',
    'report_ip_form',
]

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'

    @api.model
    def render_qweb_html(self, docids, data=None):
        """This method generates and returns html version of a report.
        """
        if self.report_name in _PAYROLL_CUSTOM_REPORTS:
            report_name = "l10n_hr_hr_payroll." + self.report_name
            if not data:
                data = {}
            data.setdefault('report_type', 'html')
            data = self._get_rendering_context(docids, data)
            return self.render_template(report_name, data), 'html'

        return super(IrActionsReport, self).render_qweb_html(docids, data)