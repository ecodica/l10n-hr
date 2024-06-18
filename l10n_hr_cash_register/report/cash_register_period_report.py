from odoo import models, api


class ReportCashRegisterPeriod(models.AbstractModel):
    _name = 'report.l10n_hr_cash_register.cash_register_period_report'
    _description = 'Cash Register Report for defined period'

    @api.model
    def _get_report_values(self, docids, data=None):
        """It is necessary to overwrite this function because values from other models in the report
         i.e. other models have to be passed as the objects in the docargs dictionary
        """
        stmnts = data['period_stmnt_ids']
        stmnt_ids = self.env['account.bank.statement.line'].browse(stmnts)
        journal_id = self.env['account.journal'].browse(data['journal_id'])
        currency_id = self.env['res.currency'].browse(data['currency_id']) or stmnt_ids.mapped('currency_id')
        before_aml_ids = self.env['account.move.line'].browse(data['before_aml_ids'])
        sum_debit_before = sum(before_aml_ids and before_aml_ids.mapped('debit'))
        sum_credit_before = sum(before_aml_ids and before_aml_ids.mapped('credit'))

        return {
            'doc_ids': stmnts,
            'docs': stmnt_ids,
            'journal_id': journal_id,
            'currency_id': currency_id,
            'sum_debit_before': sum_debit_before,
            'sum_credit_before': sum_credit_before,
            'balance_before': sum_debit_before - sum_credit_before,
            'date_from': data['date_from'],
            'date_to': data['date_to'],
            'balance_before_date': data['balance_before_date'],
        }
