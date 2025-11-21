import time
import locale
from odoo import api, models
from datetime import datetime, date,timedelta
from dateutil.relativedelta import relativedelta
from operator import itemgetter
from itertools import groupby
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT


class PayrollConfirmationReportParser(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_hr_payslip_confirmation'
    _description = 'Payroll confirmation report parser'


    @api.model
    def _get_report_values(self, docids, data=None):
        employee = self.env['hr.employee'].search([('id', '=', data['employee_id'])])
        date_from, date_to = self.get_dates(data['date'])
        employee_data, data_footer = self.get_data(employee.id, data['date'])
        mio2 = self.get_mio2(employee)
        docargs = {
            'employee':  employee,
            'company': employee.company_id,
            'mio': mio2,
            'date_from': date_from,
            'date_to': date_to,
            'data': employee_data,
            'data_footer': data_footer,
            'currency': self._get_report_currency(data['date'])
        }
        return docargs
    
    def _get_report_currency(self, document_date):
        """ Amount in active currency at the point when salary for the event is being paid.
            E.g.:
                1. event in 11 / 2022 -> payment in 12 / 2022 -> currency = HRK
                2. event in 12 / 2022 -> payment in 01 / 2023 -> currency = EUR
        """
        if document_date <= '2022-12-31':
            return self.env.ref('base.HRK')
        return self.env.ref('base.EUR')
    
    def get_mio2(self, emp):
        params_obj = self.env['hr.salary.parameters']
        contract_id = emp.contract_id.id # employee's latest contract
        params = params_obj.search([('contract_id', '=', contract_id)], order="date_from DESC", limit=1)
        mio2 = "Da" if params.mio2 else "Ne"
        return mio2

    def get_dates(self, date):
        dat_from = datetime.strptime(date,DEFAULT_SERVER_DATE_FORMAT).replace(day=1)
        date_to = dat_from + relativedelta(months=-1, days=-1)
        date_from = dat_from + relativedelta(months=-7)
        date_from = date_from.strftime(DEFAULT_SERVER_DATE_FORMAT)
        date_to = date_to.strftime(DEFAULT_SERVER_DATE_FORMAT)

        return date_from, date_to
    
    def _amount_in_paid_currency(self, payslip):
        """ Amount in active currency at the point when payslip was paid.
        """
        annual_leaves_in_paid_currency = sum(payslip.line_ids.filtered(lambda line: line.code in ['GON', 'GONPR']).mapped('total'))
        brutto_in_paid_currency = sum(payslip.line_ids.filtered(lambda line: line.code == 'BASIC').mapped('total'))
        netto_in_paid_currency = sum(payslip.line_ids.filtered(lambda line: line.code == 'NETO').mapped('total'))
        amount_paid = {
            'brutto': brutto_in_paid_currency - annual_leaves_in_paid_currency,
            'netto': netto_in_paid_currency - ((annual_leaves_in_paid_currency/brutto_in_paid_currency) * netto_in_paid_currency),
        }
        return amount_paid

    def _amount_in_company_currency(self, payslip, document_date):
        """ Amount in active currency at the point when salary for the event is being paid.
        """
        annual_leaves_in_paid_currency = sum(payslip.line_ids.filtered(lambda line: line.code in ['GON', 'GONPR']).mapped('total'))
        brutto_company_currency = sum(payslip.line_ids.filtered(lambda line: line.code == 'BASIC').mapped('total'))
        netto_company_currency = sum(payslip.line_ids.filtered(lambda line: line.code == 'NETO').mapped('total'))
        amount_paid = {
            'brutto': brutto_company_currency - annual_leaves_in_paid_currency,
            'netto': netto_company_currency - ((annual_leaves_in_paid_currency/brutto_company_currency) * netto_company_currency),
        }
        return amount_paid

    def get_data(self, employee_id, date):
        data = {}
        result = []
        payslip_obj = self.env['hr.payslip']
        confirm_date = datetime.strptime(date,DEFAULT_SERVER_DATE_FORMAT).replace(day=1)
        confirm_date_to = confirm_date + relativedelta(months=-1, days=-1)
        confirm_date_from = confirm_date + relativedelta(months=-7)
        # salary_in_kind, i3_profit_payment and i3_add_only_inputs can be null
        self.env.cr.execute("""SELECT slip.id,
                        (SELECT amount
                        FROM hr_payslip_line
                        WHERE code = 'NETO' AND slip_id = slip.id) as salary_payout
                    FROM hr_payslip AS slip
                    --LEFT JOIN hr_payslip_line line ON (line.slip_id = slip.id)
                    LEFT JOIN hr_payslip_run AS run ON (run.id = slip.payslip_run_id)
                    WHERE slip.state in ('paid','posted') and slip.employee_id = {0}
                    AND (run.salary_in_kind = false OR run.salary_in_kind IS NULL)
                    AND (run.i3_add_only_inputs = false OR run.i3_add_only_inputs IS NULL)
                    AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
                    AND slip.paid_date >= '{1}' AND slip.paid_date <= '{2}' ORDER by slip.paid_date DESC""".format(employee_id, confirm_date_from, confirm_date_to))

        res = self.env.cr.dictfetchall()
        payslip_ids = []
        for dict in res:
            #provjera zbog izostanka radnika
            if dict['salary_payout']:
                payslip_ids.append(dict['id'])
        if payslip_ids:
            total_brutto = 0
            total_netto = 0
            total_worked_hours = 0
            tot_work_hours = 0
            tot_overtime_hours = 0
            tot_absence = 0
            tot_sick_leave = 0
            tot_month_hours = 0
            brutto_hour = 0
            netto_hour = 0
            for payslip in payslip_obj.browse(payslip_ids):
                paid_date_str = payslip.paid_date.strftime('%Y-%m-%d')
                if int(paid_date_str[5:7]) == 1:
                    month_year = '12' + './' + str(int(paid_date_str[0:4]) - 1)[2:4] + '.'
                else:
                    month_year = str(int(paid_date_str[5:7]) - 1).zfill(2)  + './' + paid_date_str[2:4] + '.'
                full_work_time = 0
                overtime = 0
                absence = 0
                sick_leave = 0
                wd_lines = payslip.worked_days_line_ids
                amount_in_paid_currency = self._amount_in_paid_currency(payslip)
                amount_in_company_currency = self._amount_in_company_currency(payslip, date)
                payroll_conf = self.env['hr.payroll.salary.rule.configuration']
                full_work_time = sum(wd_lines.filtered(lambda wd: wd.code in payroll_conf.get_rules('worked')).mapped('number_of_hours'))
                overtime = sum(wd_lines.filtered(lambda wd: wd.code in payroll_conf.get_rules('overtime')).mapped('number_of_hours'))
                absence = sum(wd_lines.filtered(lambda wd: wd.code in payroll_conf.get_rules('not_worked_paid_by_company')).mapped('number_of_hours'))
                sick_leave = sum(wd_lines.filtered(lambda wd: wd.code in payroll_conf.get_rules('bolovanje_fond')).mapped('number_of_hours'))
                worked_hours = full_work_time + overtime + absence
                # iznosi po listicima:
                # ako je isplata prije 01.01.2023., iskazuju se u HRK
                # ako je isplata nakon 01.01.2023., iskazuju se u EUR
                data.update({
                    payslip.id:{
                        'mon_year': month_year,
                        'brutto': amount_in_paid_currency.get('brutto', 0),
                        'netto': amount_in_paid_currency.get('netto', 0),
                        'full_work': full_work_time,
                        'overtime': overtime,
                        'absence': absence,
                        'worked_hours': worked_hours,
                        'sick_leave': sick_leave,
                        'month_hours': payslip.month_work_hours,
                        'footer':'remove',
                        'paid_date': paid_date_str
                    }
                })

                city = payslip.company_id.city_id
                total_brutto += amount_in_company_currency.get('brutto', 0)
                total_netto += amount_in_company_currency.get('netto', 0)
                total_worked_hours += worked_hours
                tot_work_hours += full_work_time
                tot_overtime_hours += overtime
                tot_absence += absence
                tot_sick_leave += sick_leave
                tot_month_hours += payslip.month_work_hours

            result = [data[key] for key in data]

            if total_brutto and total_worked_hours and total_netto:
                brutto_hour = total_brutto / total_worked_hours
                netto_hour = total_netto / total_worked_hours

            result = sorted(result, key=itemgetter('paid_date'))
            # in case there aren't 6 paid payslips
            if len(result) < 6:
                for x in range(len(result),6):
                    result = [{
                        'mon_year': '-',
                        'brutto': '-',
                        'netto': '-','full_work': '-',
                        'overtime': '-',
                        'absence': '-',
                        'worked_hours': '-',
                        'sick_leave': '-',
                        'month_hours': '-',
                        'footer': 'remove'
                    }] + result
            result.append({
                'mon_year': 'Ukupno:',
                'brutto': total_brutto,
                'netto': total_netto,
                'full_work': tot_work_hours,
                'overtime': tot_overtime_hours,
                'absence': tot_absence,
                'worked_hours': total_worked_hours,
                'sick_leave': tot_sick_leave,
                'month_hours': tot_month_hours,
                'footer': 'remove'})
        else: # no payslips
            brutto_hour = 0
            netto_hour = 0
            city = self.env['hr.employee'].search([('id', '=', employee_id)]).company_id.city_id
            result = [{
                'mon_year': '-',
                'brutto': '-',
                'netto': '-',
                'full_work': '-',
                'overtime': '-',
                'absence': '-',
                'worked_hours': '-',
                'sick_leave': '-',
                'month_hours': '-',
                'footer': 'remove'
            }]

        result_footer = {
            'brutto_hour': round(brutto_hour, 2),
            'netto_hour': round(netto_hour, 2),
            'city': city.name,
            'date': date,
            'footer': 'add'
        }
        return result, result_footer
