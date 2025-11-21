# -*- encoding: utf-8 -*-
from odoo import fields, models, api
from datetime import datetime, date, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta
from ..models import payroll_common as paycom

class UnusedAnnualLeaveAverageGrossWageWizard(models.TransientModel):
    _name = 'unused.annual.leave.average.gross.wage.wizard'
    _description = 'Unused annual leave average gross wage wizard'
 
    def _get_datefrom_default(self):
        """
        Get last n paid payslips for current employee (with work hours), only count each month once (in case of 'IR').
        Set date_from to first day of month in which first payslip was paid.
        """
        number_of_months = self.env.user.company_id.i3_config_annual_leave_wage_number_of_months
        now =fields.Date.context_today(self)
        first_day = date(day = 1, month = now.month, year = now.year)
        lastMonth = first_day - relativedelta(months = number_of_months)
        date_from = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return date_from

    def _get_dateto_default(self):
        """
        End of current month.
        """
        now = datetime.now()
        first_day = date(day=1, month=now.month, year=now.year)
        lastMonth = first_day - timedelta(days=1)
        date_to = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return date_to


    date_from = fields.Date('Od datuma', required=True, default=_get_datefrom_default)
    date_to = fields.Date('Do datuma', required=True, default=_get_dateto_default)
    average_gross_wage = fields.Float('Prosječna bruto satnica', digits=(16,8))
    average_salary_line_ids = fields.One2many('unused.annual.leave.average.gross.wage.wizard.line', 'wizard_id', 'Salaries', help='Plaće za određeni period.', readonly=False)


    @api.onchange('date_from', 'date_to')
    def onchange_date(self):
        """
        On date change calculate average salary .
        Removes current written slip lines and shows new ones.
        Doesn't count work hours of bolovanje_fond (get from payroll_common).
        Doesn't include salary_in_kind, profit_payment and add_only_inputs.
        Doesn't include IR - absence by fault (key: NETO is None).
        """
        self.average_salary_line_ids = [(5, 0, 0)]
        if not self.date_from or not self.date_to:
            self.average_gross_wage = 0
            self.average_salary_line_ids = [(5, 0, 0)]
            return

        emp_id = self.env.context.get('active_id')
        date_from = self.date_from
        date_to = self.date_to
        data = self.get_payslip_data(emp_id, date_from, date_to, run_id=False)
        excluded_keys = ['gon_gross', 'gonpr_gross']
        self.average_gross_wage = data['gross_avg']
        self.average_salary_line_ids = [
            (0,0, {key: value for key, value in line.items() if key not in excluded_keys})
            for line in data['slips_without_izostanak']
            if isinstance(line,dict)
        ]

    def get_payslip_cond(self, run_id, date_from, date_to):
        """
        On pay_payslip_run() we want to count the slip(s) on that payslip run so we have the last n salaries for the next payslip run.
        This is why we use run_id - it is False when using the wizard because in that case we only want slips that have been paid.
        """
        if not run_id:
            slip_cond = """
                slip.state in ('paid','posted') AND paid_date >= '{0}' AND paid_date <= '{1}'
            """.format(date_from, date_to)
        else:
            slip_cond = """
                ((slip.state in ('paid','posted') AND paid_date >= '{0}' AND paid_date <= '{1}')
                OR
                (slip.payslip_run_id = {2} AND run.pay_date  >= '{0}' AND run.pay_date <= '{1}'))
            """.format(date_from, date_to, run_id)
        return slip_cond
    
    def get_payslip_data(self, emp_id, date_from, date_to, run_id=False):
        bolovanje_fond = list(self.env['hr.payroll.salary.rule.configuration'].get_rules('bolovanje_fond'))
        bolovanje_fond.extend(['GON', 'GONPR'])
        slip_cond = self.get_payslip_cond(run_id, date_from, date_to)
        params = {
            'emp_id': emp_id,
            'bolovanje_fond': tuple(bolovanje_fond),
        }
        query = """
            SELECT slip.paid_date, slip.month_work_hours,
                (SELECT id
                FROM hr_payslip_run
                WHERE id = slip.payslip_run_id) as payslip_run_id,

                (SELECT amount
                FROM hr_payslip_line
                WHERE code = 'BASIC' AND slip_id = slip.id) as salary_gross,

                (SELECT amount
                FROM hr_payslip_line
                WHERE code = 'GON' AND slip_id = slip.id) as gon_gross,

                (SELECT amount
                FROM hr_payslip_line
                WHERE code = 'GONPR' AND slip_id = slip.id) as gonpr_gross,

                (SELECT amount
                FROM hr_payslip_line
                WHERE code = 'NETO' AND slip_id = slip.id) as salary_payout,

                (SELECT
                SUM (number_of_hours)
                FROM hr_payslip_worked_days as wd 
                LEFT JOIN hr_payslip_line as pl ON(wd.payslip_id = pl.slip_id) 
                WHERE wd.code = pl.code AND (pl.amount <> 0 or wd.number_of_hours > 0 ) AND wd.payslip_id = slip.id AND wd.code NOT IN %(bolovanje_fond)s) as user_work_hours

            FROM hr_payslip slip
            LEFT JOIN hr_payslip_run run ON (slip.payslip_run_id = run.id)
            WHERE {0}
            AND slip.employee_id = %(emp_id)s
            AND ( run.salary_in_kind = false OR run.salary_in_kind IS NULL )
            AND ( run.i3_add_only_inputs = false OR run.i3_add_only_inputs IS NULL )
            AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
            ORDER by paid_date ASC
        """.format(slip_cond)
        # salary_in_kind, profit_payment and add_only_inputs can be null
        self.env.cr.execute(query, params)
        slips = self.env.cr.dictfetchall()
        
        gross_sum_year = 0
        gross_avg = 0
        user_hours = 0
        slips_without_izostanak = []
        for slip in slips:
            if slip['salary_payout']: # 'izostanak radnika' => neto = None
                slip_unused_leave_amount = (slip['gon_gross'] or 0) + (slip['gonpr_gross'] or 0)
                slip['salary_payout'] = slip['salary_payout'] - ((slip_unused_leave_amount / slip['salary_gross']) * slip['salary_payout'])
                slip['salary_gross'] = slip['salary_gross'] - slip_unused_leave_amount
                user_hours += slip['user_work_hours'] or 0
                gross_sum_year += slip['salary_gross']
                slips_without_izostanak.append(slip)
        gross_avg = gross_sum_year/user_hours if user_hours else gross_sum_year
        data = {
            'gross_avg': gross_avg,
            'slips_without_izostanak': slips_without_izostanak,
        }
        return data

    @api.onchange('average_salary_line_ids')
    def onchange_slip_ids(self):
        """
        Repeat calculation without deleted payslips.
        """
        gross_sum_year = 0
        gross_avg = 0
        user_hours = 0
        for slip in self.average_salary_line_ids:
            user_hours += slip.user_work_hours
            gross_sum_year += slip.salary_gross
        gross_avg = gross_sum_year / user_hours if user_hours else gross_sum_year
        self.average_gross_wage = gross_avg

    def save_average_gross_wage(self):
        emp_obj = self.env["hr.employee"]
        
        gross_avg = self.average_gross_wage
        period_from = self.date_from
        period_to = self.date_to
        
        data = {
            'average_gross_wage': gross_avg,
            'period_from': period_from,
            'period_to': period_to,
        }
        emp_obj.browse(self.env.context.get('active_id')).write(data)


# salary lines that are filled in wizard for overview
class UnusedAnnualLeaveAverageGrossWageWizardLine(models.TransientModel):
    _name='unused.annual.leave.average.gross.wage.wizard.line'
    _description = 'Stavka obračuna forme za izračun bruto satnice za neiskorišteni godišnji odmor'
 
    wizard_id = fields.Many2one('unused.annual.leave.average.gross.wage.wizard', 'Wizard parent', ondelete='cascade', index=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Obračun plaće')
    paid_date = fields.Char('Datum isplate', size=64, required=True)
    salary_gross = fields.Float('Bruto plaća', digits=('Payroll'))
    salary_payout = fields.Float('Neto plaća', digits=('Payroll'))
    user_work_hours = fields.Integer('Fond sati djelatnika')
    month_work_hours = fields.Integer('Mjesečni fond sati')
