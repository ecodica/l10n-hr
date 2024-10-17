from odoo import models


class InvoiceTipsReport(models.AbstractModel):
    ''' Report for Invoice Tips. '''
    _inherit = 'report.l10n_hr_account_invoice_tips.report_l10n_hr_invoice_tips'


    def _get_invoice_user_field(self):
        """
        Return the name of the field to group by as a string.

        Override this method to return a different field name if needed.
        """
        return 'l10n_hr_fiskal_user_id'
