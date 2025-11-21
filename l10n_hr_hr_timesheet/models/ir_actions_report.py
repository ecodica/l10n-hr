from odoo import models, api, fields, _

class IrActionsReport(models.Model):
    _inherit = 'ir.actions.report'


    @api.model
    def render_qweb_html(self, docids, data=None):
        """This method generates and returns html version of a report.
        """

        if self.report_name in ('report_info3_timesheet', 'report_info3_timesheet_sum', 'report_info3_timesheet_absence'):
            report_name = "l10n_hr_hr_timesheet." + self.report_name
            if not data:
                data = {}
            data.setdefault('report_type', 'html')
            data = self._get_rendering_context(docids, data)
            return self.render_template(report_name, data), 'html'

        return super().render_qweb_html(docids, data)
