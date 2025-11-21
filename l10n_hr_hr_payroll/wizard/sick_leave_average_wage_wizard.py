from odoo import fields, models, api
from ..models import payroll_common as paycom
from datetime import date, datetime, timedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from dateutil.relativedelta import relativedelta


class SickLeaveAverageWageWizard(models.TransientModel):
    _name='sick.leave.average.wage.wizard'
    _description = 'Forma za izračun satnica za bolovanje'

    def _get_datefrom_default(self):
        """
        Get period of <number_of_months> months ending before previous month.
        """
        company = self.env.user.company_id
        number_of_months = company.i3_config_sick_leave_number_of_months
        now =fields.Date.context_today(self)
        first_day = date(day = 1, month = now.month, year = now.year)
        lastMonth = first_day - relativedelta(months = number_of_months)
        date_from = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return date_from

    def _get_dateto_default(self):
        """
        Get period of <number_of_months> months ending before previous month.
        """
        now =fields.Date.context_today(self)
        first_day = date(day = 1, month = now.month, year = now.year)
        lastMonth = first_day - timedelta(days = 1)
        date_to = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return date_to

    date_from = fields.Date('Od datuma', required=True, default=_get_datefrom_default)
    date_to = fields.Date('Datum do', required=True, default=_get_dateto_default)
    average_salary_net = fields.Float('Prosječna neto satnica', digits=(16,8))
    average_salary_gross = fields.Float('Prosječna bruto satnica', digits=(16,8))
    average_salary_line_ids = fields.One2many('sick.leave.average.wage.wizard.line', 'wizard_id', 'Plaće', help='Plaće za određeni period.', readonly=True)

    def get_payslips_data(self, emp_id, date_from, date_to):
        """
        Helper method for getting payslips data.
        Enables easier access to the data from other objects (e.g. from pay_payslip_run).
        """
        bolovanje_fond = list(self.env['hr.payroll.salary.rule.configuration'].get_rules('bolovanje_fond'))
        bolovanje_fond.extend(['GON', 'GONPR'])
        params = {
            'emp_id': emp_id,
            'bolovanje_fond': tuple(bolovanje_fond)
        }
        #TODO insted of write_date check paid_date - add paid_date
        # salary_in_kind, i3_profit_payment and i3_add_only_inputs can be null
        query ="""
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
            COALESCE( SUM (number_of_hours), 0)
            FROM hr_payslip_worked_days as wd 
            LEFT JOIN hr_payslip_line as pl ON (wd.payslip_id = pl.slip_id)
            LEFT JOIN hr_salary_rule_category as c ON wd.category_id = c.id
            WHERE wd.code = pl.code AND (pl.amount <> 0 or wd.number_of_hours > 0 )
            AND wd.payslip_id = slip.id AND wd.code NOT IN %(bolovanje_fond)s
            AND NOT c.skip_hours) as user_work_hours

            FROM hr_payslip slip
            LEFT JOIN hr_payslip_run run ON (run.id = slip.payslip_run_id)
            WHERE slip.state in ('paid','posted') and slip.employee_id = '%(emp_id)s'
            AND (run.salary_in_kind = false OR run.salary_in_kind IS NULL)
            AND (run.i3_add_only_inputs = false OR run.i3_add_only_inputs IS NULL)
            AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
            AND paid_date >= '{0}' AND paid_date <= '{1}' ORDER by paid_date ASC
        """.format(date_from, date_to)
        self.env.cr.execute(query, params)
        slips = self.env.cr.dictfetchall()
        data = {}

        gross_total = 0
        net_total = 0
        gross_avg = 0
        net_avg = 0
        user_hours = 0
        slips_without_izostanak = []
        slips_count = 0
        for slip in slips:
            if slip['salary_payout']:
                slip_unused_leave_amount = (slip['gon_gross'] or 0) + (slip['gonpr_gross'] or 0)
                slip['salary_payout'] = slip['salary_payout'] - ((slip_unused_leave_amount / slip['salary_gross']) * slip['salary_payout'])
                slip['salary_gross'] = slip['salary_gross'] - slip_unused_leave_amount
                user_hours += slip['user_work_hours'] or 0
                gross_total += slip['salary_gross']
                net_total += slip['salary_payout']
                slips_without_izostanak.append(slip)
                slips_count+=1

        gross_avg = gross_total/user_hours if user_hours != 0 else gross_total
        net_avg = net_total/user_hours if user_hours != 0 else net_total
        data = {
            'total_user_work_hours': user_hours,
            'average_salary_net': net_avg,
            'average_salary_gross': gross_avg,
            'average_salary_line_ids': slips_without_izostanak,
            'total_gross_salary': gross_total,
            'slips_count': slips_count
        }
        return data

    @api.onchange('date_from','date_to',)
    def onchange_date(self):
        """
        On date change calculate average salary.
        Method is written so that the data it uses can easily be accessed from other objects.
        Remove current written slip lines and show new ones.
        Called by pay_payslip_run to update average wage on every paycheck.
        Doesn't count work hours of bolovanje_fond (get from payroll_common).
        Doesn't include salary_in_kind, profit_payment and add_only_inputs.
        Doesn't include IR - absence by fault (key: NETO is None).
        Doesn't include work hours of categories with skip_hours.
        NOTE: needs to be in sync with info3_payslip_confirmation in info3_hr_payroll/report
        """
        Params = self.env["hr.salary.parameters"]
        emp_id = Params.browse(self.env.context['active_id']).employee_id.id
        data = self.get_payslips_data(emp_id, self.date_from, self.date_to)
        slip_list = []
        for line in data['average_salary_line_ids']:
            slip_list.append((0,0,line))
        self.write({
            'average_salary_line_ids':slip_list,
            'average_salary_net': data['average_salary_net'],
            'average_salary_gross': data['average_salary_gross']
            })

    def save_average_salary(self):
        Params = self.env["hr.salary.parameters"]
        data = {
            'average_salary_gross': self.average_salary_gross,
            'average_salary_net': self.average_salary_net,
            'average_salary_date_to': self.date_to,
            'average_salary_date_from': self.date_from,
        }
        Params.browse(self.env.context['active_id']).write(data)
        return True


class SickLeaveAverageWageWizard(models.TransientModel):
    _name='sick.leave.average.wage.wizard.line'
    _description = 'Stavka obračuna forme za izračun satnica za bolovanje'

    wizard_id = fields.Many2one(
        'sick.leave.average.wage.wizard',
        'Forma za izračun prosječnih satnica za bolovanje', ondelete='cascade', index=True)
    payslip_run_id = fields.Many2one('hr.payslip.run', 'Obračun plaće', required=False)
    paid_date = fields.Char('Datum isplate', size=64, required=True)
    salary_gross = fields.Float('Bruto plaća')
    salary_payout = fields.Float('Neto plaća')
    user_work_hours = fields.Integer('Fond sati djelatnika')
    month_work_hours = fields.Integer('Mjesečni fond sati')
    gon_gross = fields.Integer('Bruto neiskorišteni godišnji')
    gonpr_gross = fields.Integer('Bruto godišnji za prethodnu godinu')
