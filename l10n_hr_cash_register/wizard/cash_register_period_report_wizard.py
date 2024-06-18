from dateutil.relativedelta import relativedelta
from odoo import fields, models, api


class CashRegisterPeriodReport(models.TransientModel):
    _name = 'cash.register.period.report'
    _description = 'Cash Register Report for defined period of time'

    journal_id = fields.Many2one(
        'account.journal',
        domain=[('type', '=', 'cash')],
        required=True,
        string='Journal'
    )
    date_from = fields.Date(
        string='Date From',
        required=True
    )
    date_to = fields.Date(
        string='Date To',
        required=True
    )

    def print_period_report(self):
        """Redirects to the report with the values obtained from the wizard
        """
        period_statement_ids = self.env['account.bank.statement.line'].search(
            domain=[('journal_id', '=', self.journal_id.id),
                    ('date', '>=', self.date_from),
                    ('date', '<=', self.date_to)]
        )

        before_aml_ids = self.env['account.move.line'].search(
            domain=[('journal_id', '=', self.journal_id.id),
                    ('account_id', '=', self.journal_id.default_account_id.id),
                    ('date', '<', self.date_from),
                    ('parent_state', '=', 'posted'),
                    ]
        )
        data = {
            'period_stmnt_ids': period_statement_ids.ids,
            'before_aml_ids': before_aml_ids.ids,
            'date_from': self.date_from.strftime('%d.%m.%Y.'),
            'date_to': self.date_to.strftime('%d.%m.%Y.'),
            'balance_before_date': (self.date_from - relativedelta(days=1)).strftime('%d.%m.%Y.'),
            'currency_id': self.journal_id.currency_id.id,
            'journal_id': self.journal_id.id,
        }

        return self.env.ref('l10n_hr_cash_register.action_period_cash_register_report').report_action(
            self,
            data=data
        )
