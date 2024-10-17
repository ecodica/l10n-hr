from collections import defaultdict
from odoo import models, api


class InvoiceTipsReport(models.AbstractModel):
    ''' Report for Invoice Tips. '''
    _name = 'report.l10n_hr_account_invoice_tips.report_l10n_hr_invoice_tips'
    _description = 'Invoice Tips Report'

    @api.model
    def _get_report_values(self, docids, data=None):
        invoices_with_tips = self.env['account.move'].search(data['domain'])

        return {
            "docs": [data['wizard_id']],
            'invoices_with_tips': invoices_with_tips,
            'sum_by_employee': self._get_sums_by_employee(invoices_with_tips),
            'totals': self._get_totals(invoices_with_tips),
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'company': self.env.company
        }

    def _get_totals(self, invoices):
        totals = {
            'total_invoice': 0.0,
            'total_tips': 0.0
        }

        for invoice in invoices:
            totals['total_invoice'] += invoice.amount_total
            totals['total_tips'] += invoice.l10n_hr_napojnica_iznos

        return totals

    def _get_sums_by_employee(self, invoices):
        sum_by_user = defaultdict(
            lambda: {'name': '', 'total_amount': 0.0, 'total_tip_amount': 0.0})

        user_field_name = self._get_invoice_user_field()

        for invoice in invoices:
            user_field = getattr(invoice, user_field_name)
            user_id = user_field.id
            user_name = user_field.name
            user_id = invoice.invoice_user_id.id
            sum_by_user[user_id]['name'] = user_name
            sum_by_user[user_id]['total_amount'] += invoice.amount_total
            sum_by_user[user_id]['total_tip_amount'] += invoice.l10n_hr_napojnica_iznos

        sum_by_employee = [
            {'name': values['name'],
             'total_amount': values['total_amount'],
             'total_tip_amount': values['total_tip_amount']
            } for values in sum_by_user.values()]

        return sum_by_employee

    def _get_invoice_user_field(self):
        """
        Return the name of the field to group by as a string.

        Override this method to return a different field name if needed.
        """
        return 'invoice_user_id'
