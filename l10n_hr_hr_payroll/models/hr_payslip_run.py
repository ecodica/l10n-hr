# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import date, datetime, timedelta
from . import payroll_common as paycom
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT
from operator import itemgetter


_TAXLESS_PAYMENT_CODES = paycom.get_categories().get('taxless_payments',[])

class HrPayslipRun(models.Model):
    _inherit = ['hr.payslip.run', 'mail.thread']
    _name = 'hr.payslip.run'
    _order = 'pay_date desc'
    

    _run_type_help= u'Isplat plaće generira standardan JOPPD.\n'\
                    u'Neisplata plaće generira JOPPD sa 0 u kolonama 15.1 - 16.2\n'\
                    u'Naknadna isplata plaće generira joppd sa 0 u kolonama 12 - 13.9'
  
    def print_all_no1(self):
        slips = self.env['hr.payslip'].search([('payslip_run_id', '=', self.id)])
        if not slips:
            return False
        return self.env.ref('l10n_hr_hr_payroll.no1_report').report_action(slips)
    
    #get working hours in previos month
    def _get_period_hours(self):
        # define holidays if they exist
        # this should be done automatic
        #holidays = [datetime.date(2013, 8, 14)]
        holidays = []

        now = datetime.now()
        first_day = datetime(day=1, month=now.month, year=now.year).date()
        lastMonth = first_day - timedelta(days=1)

        business_days = 0
        for i in range(1, 32):
            try:
                thisdate = datetime(lastMonth.year, lastMonth.month, i).date()
            except(ValueError):
                break
            if thisdate.weekday() < 5 and thisdate not in holidays: # Monday == 0, Sunday == 6 
                business_days += 1

        work_hours = business_days * 8
        return work_hours

    def _get_datestart_default(self):
        now = datetime.now()
        first_day = date(day=1, month=now.month, year=now.year)
        lastMonth = first_day - timedelta(days=1)
        lastMonth = lastMonth - timedelta(lastMonth.day - 1)
        start_date = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return start_date

    def _get_dateend_default(self):
        now = datetime.now()
        first_day = date(day=1, month=now.month, year=now.year)
        lastMonth = first_day - timedelta(days=1)
        end_date = lastMonth.strftime(DEFAULT_SERVER_DATE_FORMAT)
        return end_date

    # override to change defaults (last month instead of current month)
    date_start = fields.Date(string='Od datuma', required=True, readonly=False,
         default=_get_datestart_default, tracking=True)
    date_end = fields.Date(string='Do datuma', required=True, readonly=False,
         default=_get_dateend_default, tracking=True)
    period_work_hours = fields.Float('Mjesečni fond sati', required=True, 
                                        help="Izračun radnih sati za prethodni mjesec", 
                                        digits=('Payroll'),
                                        default=_get_period_hours, tracking=True)
    pay_date = fields.Date('Datum isplate', required=True, tracking=True)
    state = fields.Selection(selection_add=[('paid', 'Plaćeno'),('posted', 'Proknjiženo')], tracking=True)
    move_id = fields.Many2one('account.move','Temeljnica', tracking=True)
    i3_currency = fields.Float('Tečaj za obustave', digits=(16,6), readonly=True, 
                                help="Tečaj za izračun obustava u Eurima. Tečaj se uzima na dan kreiranja obračuna. Ako želite tečaj s nekim drugim datumom, potrebno ga je ručno upisati.", tracking=True) 
    currency_rate = fields.Float('Tečaj',digits=(16,8))
    salary_in_kind = fields.Boolean('Plaća u naravi', help="Označite ako želite obračunati plaću u naravi.", tracking=True)
    i3_add_only_inputs = fields.Boolean('Ostalo', help="Ako je ova opcija uključena, generirat će se listići bez radnih sati i ostalih unosa.", tracking=True)
    i3_profit_payment = fields.Boolean('Isplata dobiti', help="Označite, ako želite obračunati isplatu dobiti.", tracking=True)
    payslip_run_type = fields.Selection([
                            ('salary_payment', 'Isplata plaće'),
                            ('nonpaid_salary', 'Neisplaćena plaća'),
                            ('subsequent_salary_payment', 'Naknadna isplata plaće'),
                            ], 'Vrsta obračuna', default='salary_payment', help=_run_type_help, tracking=True)
    i3_work_abroad_currency = fields.Float('Tečaj za izaslani rad', digits=(16,6), readonly=True, 
                                            help="Koristi se za izračun neto plaće i poreza u Eurima za izaslani rad. Tečaj se uzima na posljednji dan obračunskog razdoblja.", tracking=True)
    disability_fee_payment_id = fields.Many2one('hr.payroll.disability.fee.payment', 'Naknada za nezapošljavanje OSI', compute='get_disability_fee_payment_id', index=True, store=True)
    disability_fee_amount = fields.Float(related='disability_fee_payment_id.disability_fee_amount', string='Iznos naknade za OSI', store=True)
    disability_fee_payment_ids = fields.One2many('hr.payroll.disability.fee.payment', 'payslip_run_id', 'Naknade za nezapošljavanje OSI')
    company_id = fields.Many2one('res.company', string='Tvrtka', readonly=True, copy=False,
                                    default=lambda self: self.env['res.company']._company_default_get(),
                                    )

    annual_calc = fields.Boolean('Godišnji obračun', tracking=True)
    severance = fields.Boolean('Otpremnina', tracking=True)
    # override to change default and states attribute
    journal_id = fields.Many2one(default=lambda self: self.env['account.journal'].search([('type', '=', 'payroll')], limit=1), tracking=True) 
    hr_config_send_payslips_by_email = fields.Boolean(related='company_id.hr_config_send_payslips_by_email')
    hr_accounting_scheme_type_id = fields.Many2one('hr.payroll.accounting.scheme.type', 'Vrsta sheme knjiženja', tracking=True)

    slip_ids_count = fields.Integer(compute='_compute_slip_count', string='Broj listića')
    employee_count = fields.Integer(compute='_compute_employee_count', string='Broj zaposlenika')

    bank_account_id = fields.Many2one('res.partner.bank', 'Račun za isplatu',
        help='Račun tvrtke za isplatu.', domain=[('is_company_account', '=', True)])

    payslip_run_type = fields.Selection([
                            ('salary_payment', 'Isplata plaće'),
                            ('nonpaid_salary', 'Neisplaćena plaća'),
                            ('subsequent_salary_payment', 'Naknadna isplata plaće'),
                            ], 'Vrsta obračuna', default='salary_payment', help=_run_type_help, tracking=True)

    show_nonpaid_salary_options = fields.Boolean(string='Prikaži postavke za neisplaćenu plaću', related='company_id.i3_config_show_nonpaid_salary_options')
    payslips_without_tax_return_tolerance = fields.Float('Tolerancija za godišnji obračun', help='Tolerancija za brisanje listića godišnjeg obračuna koji nemaju iznos povrata poreza')

    def _compute_employee_count(self):
        for payslip_run in self:
            payslip_run.employee_count = len(payslip_run.slip_ids.mapped('employee_id'))

    def _compute_slip_count(self):
        for payslip_run in self:
            payslip_run.slip_ids_count = len(payslip_run.slip_ids)

    def unlink(self):
        """Override to constrain delete when paid."""
        for payslip_run in self:
            if payslip_run.state not in ['draft', 'close']:
                raise ValidationError('Ne može se obrisati listić koji je već plaćeni!')
            for slip in payslip_run.slip_ids:
                slip.unlink()
        return super(HrPayslipRun, self).unlink()

    @api.model_create_multi
    def create(self, vals_list):
        """
        Get EUR currency rates for suspension and work abroad calculation.
        """
        for vals in vals_list:
            vals.update(self.get_currency_rates(vals))
        return super(HrPayslipRun, self).create(vals_list)

    def print_all_ip1(self):
        """
        Print all payslip directly from payslip run.
        """
        slip_ids = self.slip_ids
        if not slip_ids:
            return False
        report_id = 'l10n_hr_hr_payroll.ip1_form_report'
        return self.env.ref(report_id).report_action(slip_ids)

    def print_all_io1_reports(self):
        "Print all IO1 reports directly from payslip run"
        slip_ids = self.slip_ids
        if not slip_ids:
            return False
        report_id = 'l10n_hr_hr_payroll.io1_report'
        return self.env.ref(report_id).report_action(self.slip_ids)

    @api.onchange('date_start','date_end')
    def onchange_date(self):
        """
        Calculates working hours in given date span.
        """
        if self.date_start and self.date_end:# and self.date_start <= self.date_end:
            period_work_hours = 0
            holidays = []
            
            date_start = datetime.strftime(self.date_start, DEFAULT_SERVER_DATE_FORMAT)
            date_end = datetime.strftime(self.date_end, DEFAULT_SERVER_DATE_FORMAT)
            #control for calculation
            dates_valid = True
            start_format = date_start.split("-") if date_start != False else []
            if not (len(start_format) == 3 and len(start_format[0]) == 4 and (len(start_format[1]) == 1 or len(start_format[1]) == 2) and (len(start_format[2]) == 1 or len(start_format[2]) == 2)):
                dates_valid = False
            end_format = date_end.split("-") if date_end != False else []
            if not (len(end_format) == 3 and len(end_format[0]) == 4 and (len(end_format[1]) == 1 or len(end_format[1]) == 2) and (len(end_format[2]) == 1 or len(end_format[2]) == 2)):
                dates_valid = False
            if int(start_format[0]) > int(end_format[0]) or int(start_format[1]) > int(end_format[1]):
                dates_valid = False
            if int(start_format[1]) == int(end_format[1]) and int(start_format[2]) > int(end_format[2]):
                dates_valid = False
            
            if dates_valid:
                start = date(int(start_format[0]), int(start_format[1]), int(start_format[2]))
                end = date(int(end_format[0]), int(end_format[1]), int(end_format[2]))
                business_days = 0

                monthup = False

                day = int(start_format[2])
                month = int(start_format[1])
                year = int(start_format[0])
                for i in range(1, 93):
                    try:
                        thisdate = date(year, month, day)
                    except(ValueError):
                        if monthup:
                            month = 0
                            year += 1
                        day = 1
                        month += 1
                        monthup = True
                    else:

                        if thisdate.weekday() < 5 and thisdate not in holidays: # Monday == 0, Sunday == 6 
                            business_days += 1
                        if year == int(end_format[0]) and month == int(end_format[1]) and day == int(end_format[2]):
                            break
                        elif i == 92: #date span is too big
                            business_days = 0

                        monthup = False
                        day += 1

                period_work_hours = business_days * 8
            self.period_work_hours = period_work_hours

    def draft_payslip_run(self):
        self.payslip_run_set_state('draft')
        self.update_employee_tax_base()
        # self.update_employee_bonuses()
        self.write({'state': 'draft'})
        return True
    
    def cancel_payment(self):
        """
        Change state.
        Remove monthly annual leaves and taxless payment records from employee.
        Remove suspension payments.
        Clear related account move.
        """
        # self.unlink_leaves()
        self.unlink_taxless_payments()
        self.unlink_suspension_payments()
        # self.update_average_wages(cr, uid, ids, payslip_run, context=context)
        self._clear_account_move()
        self.payslip_unset_paid_date()
        self.payslip_run_set_state('done')
        self.write({'state':'close'})
        if self.disability_fee_payment_id:
            self.disability_fee_payment_id.draft_disability_fee()
        return True

    def pay_payslip_run(self):
        """
        Method for payslip run payment.
        If regular salary payment:
        - update average salary data until last paid salary (will be used for calc on next run)
        - set annual leave
        - create suspension payment
        """
        sick_leave_number_of_months = self.company_id.i3_config_sick_leave_number_of_months - 1
        annual_leave_number_of_months = self.company_id.i3_config_annual_leave_wage_number_of_months- 1
        sick_leave_period = self.get_period_for_average_wage(self.date_end, sick_leave_number_of_months)
        annual_leave_period = self.get_period_for_average_wage(self.date_end, annual_leave_number_of_months)
        # annual_list = ""
        
        salary_payment = not self.salary_in_kind and not self.i3_add_only_inputs and not self.i3_profit_payment
        for slip in self.slip_ids:
            # payslip run with annual calculation has both regular slips and annual calculation slips for employees which have differences in tax payment, we only want the updates for regular slips
            if salary_payment and not slip.annual_calculation:
                self.update_sick_leave_wages(sick_leave_period, slip)
                self.update_annual_leave_wages(annual_leave_period, slip)
            if not self.salary_in_kind and not self.i3_profit_payment:
                # can be done through salary payment or only inputs, as per request
                slip.update_taxless_payments()

        self.calculate_employee_suspensions()

        # last salary of the year
        if salary_payment and self.date_start.month == 12:
            self.annual_leave_recap()

        self.payslip_run_set_state('paid')
        self.payslip_set_paid_date()
        self.write({'state': 'paid'})

        self.create_payroll_account_move()

        if self.disability_fee_payment_id:
            self.disability_fee_payment_id.pay_disability_fee()
        return True
    
    def close_payslip_run(self):
        """
        Confirms payslip run and run difference check.
        """
        #TO-DO zbrajanje porezne osnovice za sve zaposlenike i upis u hr_employee
        #self.annual_calculation(cr, uid, ids, context)
        self.calc_payslip_run()
        if not self.i3_profit_payment:
            self.check_for_difference()   
        self.payslip_run_set_state('done')
        
        # tax base is already updated on calc_payslip_run
        #self.update_employee_tax_base(cr, uid, ids, context)
        # self.update_employee_bonuses()
        self.write({'state': 'close'})
        return True

    def calc_payslip_run(self):
        slip_obj = self.env["hr.payslip"]
        emp_obj = self.env["hr.employee"]
        # update used tax deduction in case of multiple payments in same month so tax calculation is correct
        # */ not needed any more /*
        # self.update_employee_tax_base()
        # update taxless bonus amount paid so we can check if it is exceeded
        # self.update_employee_bonuses(cr, uid, ids, context)
        
        annual_list = ''
        taxless_exceeded_yearly = []
        taxless_exceeded_monthly = []
        invalid_contract = []
        sick_leave_fund_dates_not_entered = []
        invalid_leave = []
        # need to sort by (date_from, ID) to ensure correct calculation for multiple payslips for same employee
        # suspension calculation relies on payslips being calculated chronologically by date_from or ID (see get_suspension_calculated_amount())
        for slip in self.slip_ids.sorted(lambda slip: (slip.date_from, slip.id)):
            if slip.annual_calculation:
                res = slip.annual_tax_calculation()
            else:
                res = slip.compute_sheet()
                invalid_leave += res['invalid_leave']
                if not slip.annual_calculation:
                    leaves = slip.get_yearly_annual_leave_qty()
                    if leaves['used'] > leaves['total']:
                        annual_list += _(u"\n{0}").format(slip.employee_id.name)
                # exceptions are raised here because they cause form inconsistency (invisible worked_days or inputs) when raised on compute_sheet in edit mode
                slip.check_payslip(res)
                if 'contract_id' in res and not res['contract_id']:
                    invalid_contract.append(slip.employee_id.name)

                if 'sick_leave_fund_dates_not_entered' in res and res['sick_leave_fund_dates_not_entered']:
                    sick_leave_fund_dates_not_entered.append(slip.employee_id.name)
                max_taxless_amounts = slip.get_taxless_payments_max_amounts() # call for each slip since settings can be edited on slip
                paid = slip.get_taxless_fee_amount_paid()
                res = slip.check_taxless_payment_amount(max_taxless_amounts['yearly'], _TAXLESS_PAYMENT_CODES, paid['yearly'])
                if res:
                    taxless_exceeded_yearly.append(res)
                monthly_codes = self._monthly_amount_check_get_codes(slip.check_taxless_lunch_fee_amout)
                res = slip.check_taxless_payment_amount(max_taxless_amounts['monthly'], monthly_codes, paid['monthly'])
                if res:
                    taxless_exceeded_monthly.append(res)

        self.check_payslip_run(
            invalid_contract, taxless_exceeded_yearly, taxless_exceeded_monthly,
            annual_list, sick_leave_fund_dates_not_entered, invalid_leave
        )
        return True

    def get_calculation_parameters(self):
        for slip in self.slip_ids:
            slip.get_calculation_parameters()

    def _monthly_amount_check_get_codes(self, check_taxless_lunch_fee_amount):
        """
        Lunch fees get included in the monthly check only if the check_taxless_lunch_fee_amount checkbox is selected.
        This is due to of legal limitations of lunch fees which are a combination of annual and monthly limits. 
        Limit is defined as a total value of all months in current year up to the payment month.
        By default we check the monthly amount, but we also allow the user to turn the validation off and just check the yearly limit.
        All other fees are checked regardless.
        """
        codes_monthly = list(self.env['hr.payroll.salary.rule.configuration'].get_rules('taxless_payments_monthly'))
        if check_taxless_lunch_fee_amount:
            codes_monthly += ['PREH66', 'PREH65']
        return codes_monthly

    def action_update_account_move(self):
        """
        Enable update so user doesn't have to cancel payment and pay again just to update account move.
        """
        self._clear_account_move()
        self.create_payroll_account_move()
        return True
    
    def _clear_account_move(self):
        """
        Clear only account move lines and leave the account move so we don't create a new one each time move lines are updated.
        """
        if self.move_id:
            self.move_id.line_ids.unlink()
        return True

    def payslip_run_set_state(self, state):
        """
        Get state from payslip run and change state on payslips as well.
        """
        # no need to delete annual calculation payslips when drafting since it is on separate payslip run
        # if state == 'draft':        
        #     sql = "UPDATE hr_payslip SET state = %s WHERE payslip_run_id = %s AND annual_calculation = FALSE"
        #     sql_delete = "DELETE FROM hr_payslip WHERE payslip_run_id = %s AND annual_calculation = TRUE"
        # else:
        sql = "UPDATE hr_payslip SET state = %s WHERE payslip_run_id = %s"
        try:
            self.env.cr.execute(sql, (state, self.id,) )
            self.env.cr.commit()
            # if state == 'draft':
            #     self.env.cr.execute(sql_delete, (self.id,) )
            #     self.env.cr.commit()
            return True
        except:
            return False
    
    def check_leaves(self):
        annual_list = ""
        for slip in self.slip_ids:
            leaves = slip.get_yearly_annual_leave_qty()
            if leaves['used'] > leaves['total']:
                annual_list += _(u"\n{0}").format(slip.employee_id.name)
        if annual_list != "":
            raise ValidationError(_(u"List of employees who want to use more leave than available: {0}".format(annual_list)))

    def annual_leave_recap(self):
        """
        Create or edit annual leave for next year - unused leave is set as old leave and 0 as new leave.
        """
        annual_leave_year_obj = self.env['info3.hr.employee.annual.leave.year']
        new_year_date = self.date_start + relativedelta(months = +1)
        new_year = new_year_date.year
        new_year_id = self.env['account.fiscal.year'].search([('name', '=', new_year)])
        if not new_year_id:
            raise ValidationError(_(u'Nije moguće ažurirati godišnji odmor za {0} godinu prije nego se otvori fiskalna godina.').format(new_year))
        for slip in self.slip_ids:
            # get existing new year records
            new_year_leave_ids = annual_leave_year_obj.search([('year', 'in', new_year_id.ids), ('employee_id', '=', slip.employee_id.id)])
            # if employee has more than one record - raise error
            if len(new_year_leave_ids) > 1:
                raise ValidationError(_(u"Djelatnik {0} ima naknadu za rođenje djeteta veću od {1}.").format(slip.employee_id.name_related))
            leaves = slip.get_yearly_annual_leave_qty()
            data = {
                'employee_id': slip.employee_id.id,
                'year': new_year_id[0].id,
                'leave': 0,
                'old_leave': leaves['total'] - leaves['used'],
            }
            if not new_year_leave_ids:
                annual_leave_year_obj.create(data)
        return True
     
    def unlink_taxless_payments(self):
        taxless_payment_obj = self.env["employee.taxless.payment.line"]
        taxless_payment_ids = taxless_payment_obj.search([('payslip_run_id','in',self.ids)])
        taxless_payment_ids.unlink()
        return True

    def unlink_suspension_payments(self):
        suspension_payment_obj = self.env['hr.salary.suspension.payment']
        history_ids = suspension_payment_obj.search([('payslip_id','in',self.slip_ids.ids)])
        history_ids.unlink()
        return True

    def calculate_employee_suspensions(self):
        """
        Create suspension payment when salary is paid.
        """
        payments = self.env['hr.salary.suspension.payment']
        # grouped by (suspension_id, bank_account_id, slip.id)
        # in company currency
        result = self.update_employee_suspensions()
        data = {}
        for el in result:
            key = el[0]
            # if suspension is in foreign currency, we need to convert back from company to suspension currency
            # because this amount will be compared to end_amount on hr.salary.suspension which is in suspension currency
            if result[el]['currency'] and result[el]['currency'] != (self.company_id.currency_id.symbol) and self.i3_currency:
                result[el]['amount'] = result[el]['amount'] / self.i3_currency
            if key not in data:
                data.update({
                    key: {
                        'payslip_id': result[el]['payslip_id'],
                        'suspension_id': result[el]['suspension_id'],
                        'amount': result[el]['amount']
                    }
                })
            else:
                data[key]['amount'] += result[el]['amount']
        for key in data:
            payments.create(data[key])
        return True
    
    def update_employee_suspensions(self):
        """
        Calculate suspensions for each employee and update them.
        """
        result = {}
        for slip in self.slip_ids:
            result.update(slip.i3_update_employee_suspensions())
        return result

    def payslip_set_paid_date(self):
        """
        Read paid date from payslip run and sets it on payslip when payslip run is being paid.
        """
        sql = "UPDATE hr_payslip SET paid_date = %s WHERE payslip_run_id = %s"
        paid_date = self.pay_date
        try:
            self.env.cr.execute(sql, (paid_date, self.id) )
            self.env.cr.commit()
            return True
        except:
            return False
    
    def payslip_unset_paid_date(self):
        """
        Read paid date from payslip run and sets it on payslip when payslip run is being paid.
        """
        sql = "UPDATE hr_payslip SET paid_date = null WHERE payslip_run_id = %s"
        try:
            self.env.cr.execute(sql, (self.id,) )
            self.env.cr.commit()
            return True
        except:
            return False
    
    def update_sick_leave_wages(self, period, slip):
        """
        Update average salary fields on contract for sick leave calculation.
        """
        avg_salary_wiz_obj = self.env['sick.leave.average.wage.wizard']
        date_from = period['date_from']
        date_to = period['date_to']
        res = avg_salary_wiz_obj.get_payslips_data(slip.employee_id.id, date_from, date_to)
        data = {
            'average_salary_net': res['average_salary_net'],
            'average_salary_gross': res['average_salary_gross'],
            'average_salary_date_from': date_from,
            'average_salary_date_to': date_to,
        }
        slip.salary_parameters_id.write(data)
        return True
    
    def update_annual_leave_wages(self, period, slip):
        """
        Update average wage field on employee for annual leave calculation.
        """
        avg_wage_wiz_obj = self.env['unused.annual.leave.average.gross.wage.wizard']
        date_from = period['date_from']
        date_to = period['date_to']
        emp_id = slip.employee_id.id
        res = avg_wage_wiz_obj.get_payslip_data(emp_id, date_from, date_to, slip.payslip_run_id.id)
        data = {
            'average_gross_wage': res['gross_avg'],
            'period_from': date_from,
            'period_to': date_to,
        }
        slip.employee_id.write(data)
        return True

    def get_period_for_average_wage(self, date_end, no_of_months):
        """
        Return period for average wage calculation - n months prior to this run (period is for date_paid!)
        """
        date_from = (date_end - relativedelta(months=no_of_months)).replace(day=1)
        period = {
            'date_from': date_from,
            'date_to': date_end
        }
        return period

    def check_for_difference(self):
        """
        Check if there is difference in account distribution for suspension and payment.
        Called on payslip run close (confirmation).
        """
        payslip_line_obj = self.env['hr.payslip.line']
        slip_obj = self.env['hr.payslip']
        slip_ids = slip_obj.search([('payslip_run_id','=',self.id)])  
        suspension_payslip_line_ids = payslip_line_obj.search(['&',('code','=','OBS'), ('slip_id','in',slip_ids.ids)])

        payment_payslip_line_ids = payslip_line_obj.search(['&',('code','in',['ISPL','ISPLM']), ('slip_id','in',slip_ids.ids)])
        suspensions = {}
        payments = {}
        for suspension in suspension_payslip_line_ids:
            suspensions.update({suspension.slip_id.id:{'total':suspension['total']}})
        for payment in payment_payslip_line_ids:
            if payment.slip_id.id not in payments:
                payments.update({payment.slip_id.id: {'total': payment['total']}})
            else:
                payments[payment.slip_id.id]['total'] += payment['total']
        difference_list_payments = []
        difference_list_suspensions = []
        payments_slip_ids=[] #list of valid slip_ids in payments to avoid error if code = 'IR'
        for payment in payments:
            payments_slip_ids.append(payment)
        for slip in self.slip_ids:
            bank_amount = 0
            suspension_amount = 0
            if slip.bank_lines:
                for bank_line in slip.bank_lines:
                    bank_amount += bank_line.amount
                #payments[slip.id] doesn't exist if code = 'IR'
                if slip.id in payments_slip_ids and payments[slip.id]['total'] != round(bank_amount,2):
                    difference_list_payments.append(slip.employee_id.name)
            if slip.suspension_lines:
                for suspension_line in slip.suspension_lines:
                    suspension_amount += suspension_line.amount
                if suspensions[slip.id]['total'] != round(suspension_amount,2):
                    difference_list_suspensions.append(slip.employee_id.name)
        if len(difference_list_payments) > 0:
            text = ''
            for difference in difference_list_payments:
                text += difference + ', '
            raise ValidationError(_(u'Zaposlenici koji imaju pogrešnu raspodjelu iznosa po računima: {0}').format(text[:-2]))
        if len(difference_list_suspensions) > 0:
            text = ''
            for difference in difference_list_suspensions:
                text += difference + ', '
            raise ValidationError(_(u'Zaposlenici koji imaju pogrešnu raspodjelu iznosa za obustave: {0}').format(text[:-2]))
        return True

    def check_payslip_run(self, invalid_contract, taxless_exceeded_yearly, taxless_exceeded_monthly, annual_list, sick_leave_fund_dates_not_entered, invalid_leave):
        if invalid_contract:
            raise ValidationError(_(u'Zaposlenici koji nemaju valjani ugovor za odabrano razdoblje: {0}').format('\n'+'\n'.join(invalid_contract)))
        if taxless_exceeded_yearly:
            raise ValidationError(_(u'Popis zaposlenika koji su prekoračili maksimalni godišnji iznos neoporezivih isplata: {0}').format('\n'+'\n'.join(taxless_exceeded_yearly)))
        if taxless_exceeded_monthly:
            raise ValidationError(_(u'Zaposlenici koji su prekoračili maksimalni mjesečni iznos neoporezivih naknada: {0}').format('\n'+'\n'.join(taxless_exceeded_monthly)))
        if annual_list:
            raise ValidationError(_(u"Popis zaposlenika koji žele koristiti više godišnjeg nego što imaju: {0}").format(annual_list))
        if sick_leave_fund_dates_not_entered:
            raise ValidationError(_(u"Potrebno je unijeti razdoblje bolovanja na fond na listiću:\n{0}").format('\n'+'\n'.join(sick_leave_fund_dates_not_entered)))
        if invalid_leave:
            raise ValidationError(_(u'Godišnji odmor za godinu {0} mora biti unesen prije unosa po mjesecima. Lista zaposlenika bez godišnjeg odmora: {1}').format(self.pay_date.year, '\n\n' + '\n'.join(set(invalid_leave))))
        return True        
    
    def update_employee_tax_base(self):
        """
        Update tax base for all employees on payslip run because we can have more then one salary in one month.
        Method is called on creating payslip run payslips.
        """
        month = self.pay_date.month
        year = self.pay_date.year
        
        sql = "UPDATE hr_employee SET (total_tax_base, total_tax_deduction) = ( 0,  0)"
                       
        try:     
            self.env.cr.execute(sql)
            self.env.cr.commit()        
        except:
            return False
        
        sql = "SELECT s.employee_id, l.CODE, sum(total) as total " \
              "FROM hr_payslip_line l, hr_payslip s, hr_payslip_run r " \
              "WHERE l.slip_id = s.id AND s.payslip_run_id = r.id AND l.CODE IN ('POROSN', 'IOOD')" \
              "AND DATE_PART('month', r.pay_date) = %s AND DATE_PART('year', r.pay_date) = %s AND s.state = 'paid' " \
              "GROUP BY s.employee_id, l.CODE " \
              "ORDER BY s.employee_id, l.CODE"                       
        try:  
            self.env.cr.execute(sql, (month, year, ) )
            self.env.cr.commit()
        except:
            return False
        
        lines = self.env.cr.fetchall()
        emp_id = -1
                                            
        for row in lines:
            if (emp_id == -1 or (emp_id != -1 and emp_id != row[0])):
                emp_id = row[0]
                vals = {}
            
            if row[1] == 'POROSN':     
                vals['total_tax_base'] =  row[2]
            elif row[1] == 'IOOD':
                vals['total_tax_deduction'] =  row[2]
            
            if len(vals) == 2:
                emp = self.env['hr.employee'].search([('id', '=', emp_id)])
                emp.write(vals)
        return True

    @api.depends('disability_fee_payment_ids')
    def compute_disability_fee_payment(self):
        if len(self.disability_fee_payment_ids) > 0:
            self.disability_fee_payment_id = self.disability_fee_payment_ids[0]

    def disability_fee_payment_inverse(self):
        if len(self.disability_fee_payment_ids) > 0:
            # delete previous reference
            fee_payment = self.env['hr.payroll.disability.fee.payment'].browse(self.disability_fee_payment_ids[0].id)
            fee_payment.payslip_run_id = False
        # set new reference
        self.disability_fee_payment_id.payslip_run_id = self
    
    def action_update_payslips_name(self):
        payslips_list = self.slip_ids
        for payslip in payslips_list:
            run_name = payslip.get_payslip_run_name()
            payslip.name = _('{1} {0}').format(payslip.employee_id.name, run_name)

    def calculate_disability_fee(self):
        """
        Create disability fee payment object.
        """
        payment_obj = self.env['hr.payroll.disability.fee.payment']
        data = self.get_disability_fee_data()
        payment = payment_obj.create(data)

    def cancel_disability_fee(self):
        """
        Unlink disability fee payment object.
        """
        run_id = self.disability_fee_payment_id.unlink()

    def get_disability_fee_data(self):
        payment_obj = self.env['hr.payroll.disability.fee.payment']
        emps = self.count_employees()
        company = self.company_id
        run_id = self.id
        min_wage = company.i3_config_minimal_wage
        fee_pct = company.i3_config_disability_fee_percentage
        quota_pct = company.i3_config_disability_quota_percentage
        min_total_emps = company.i3_config_disability_fee_min_number_of_employees
        debit_account = company.i3_config_account_debit_disability.id
        credit_account = company.i3_config_account_credit_disability.id
        emps_with_disabilities = emps['with_disabilities']
        emps_total = emps['total']
        min_required_emps = payment_obj._calculate_employee_quota(emps_total, min_total_emps, quota_pct)
        disability_fee_number_of_emps = payment_obj._calculate_number_of_emps_for_disability_fee(min_required_emps, emps_with_disabilities)
        amount = payment_obj._calculate_disability_fee_amount(min_wage, fee_pct, disability_fee_number_of_emps)
        data = {
            'payslip_run_id': run_id,
            'minimal_wage': min_wage,
            'disability_fee_pct': fee_pct,
            'emps_with_disabilities_quota_pct': quota_pct,
            'number_of_emps_total': emps_total,
            'number_of_emps_with_disabilities': emps_with_disabilities,
            'min_number_of_emps_with_disabilities': min_required_emps,
            'disability_fee_amount': amount,
            'min_total_number_of_emps_to_pay_fee': min_total_emps,
            'disability_fee_number_of_emps': disability_fee_number_of_emps,
            'credit_disability_fee': company.i3_config_disability_fee_crediting,
            'disability_fee_credit_account_id': debit_account,
            'disability_fee_debit_account_id': credit_account,
        }
        return data
        
    def count_employees(self):
        """
        We have 2 types of employees (hr.employee records):
            - employees (doesn't have additional income structure on salary parameters)
            - associates (has additional income structure on salary parameters)
        For disability fee payment we consider only active employees (and not associates).
        """
        emp_ids = []
        emp_ids_with_disability = []
        date = self.date_end
        employees = self.env['hr.employee'].search([('is_employee', '=', True)])
        for emp in employees:
            emp_ids.append(emp.id)
            if emp._has_disability_on_date(date) and emp.id not in emp_ids_with_disability:
                emp_ids_with_disability.append(emp.id)
        res = {
            'total': len(emp_ids),
            'with_disabilities': len(emp_ids_with_disability),
        }
        return res

    @api.depends('disability_fee_payment_ids')
    def get_disability_fee_payment_id(self):
         for record in self:
            record.disability_fee_payment_id = record.disability_fee_payment_ids and record.disability_fee_payment_ids[0] or False

    def annual_calculation_get_employees(self, min_pay_date, max_pay_date):
        """
        Return list of employees with payments in current year.
        """
        query = """
            SELECT DISTINCT(employee_id) AS employee_id
            FROM hr_payslip AS slip
            LEFT JOIN hr_payslip_run AS run ON (slip.payslip_run_id = run.id)
            WHERE run.pay_date >= '{0}'
            AND run.pay_date <= '{1}'
            AND (run.i3_add_only_inputs = false OR run.i3_add_only_inputs IS NULL)
            AND (run.i3_profit_payment = false OR run.i3_profit_payment IS NULL)
            AND (run.annual_calc = false OR run.annual_calc IS NULL)
        """.format(min_pay_date, max_pay_date)
        self.env.cr.execute(query)
        res = self.env.cr.dictfetchall()
        return [line['employee_id'] for line in res]
    
    # def annual_calculation_filter_employees(self, emp_ids, only_emps_with_payment_in_each_month):
    #     return emp_ids
    
    def annual_calculation_get_payslips(self, emp_ids, min_pay_date, max_pay_date):
        """
        Return regular payslips for selected employees.
        """
        payslip_obj = self.env['hr.payslip']
        pay_date_clause = ['&', ('payslip_run_id.pay_date', '>=', min_pay_date), ('payslip_run_id.pay_date', '<=', max_pay_date)]
        payslip_run_type_clause = [
            ('payslip_run_id', '!=', False),
            ('payslip_run_id.i3_add_only_inputs', '=', False),
            ('payslip_run_id.i3_profit_payment', '=', False),
            ('annual_calculation', '=', False),
            ('state', '!=', 'draft')
        ]
        emp_clause = [('employee_id', 'in', emp_ids)]
        final_clause = emp_clause + pay_date_clause + payslip_run_type_clause
        slip_ids = payslip_obj.search(final_clause)
        # slip_ids.sort() # is sorting necessary?
        return slip_ids

    def annual_calculation_get_employee_payslips_data(self, slip_ids, company, max_pay_date, annual_slip=False):
        """
        Return payslip data needed for annual tax calculation.
        """
        payslip_line = self.env['hr.payslip.line']
        additional_income_structs = paycom.get_structures()['additional_income']
        osnovica = company.i3_config_osnovica
        max_pay_date = fields.Date.to_date(max_pay_date)

        data = {}
        zadnji_odbitak = 0.00
        for slip in slip_ids:
            slip_line_codes = ['IOOD', 'OOD', 'DOH', 'PDOH', 'POROSN', 'ISPL', 'BASIC', 'DMIO']
            employees = slip_ids.mapped('employee_id.id')
            for emp in employees:
                employee_id = self.env['hr.employee'].browse(emp)
                city = employee_id.city
                city_tax_lower, city_tax_higher = city._get_tax_rate_on_date(max_pay_date)
                razred_1_posto = city_tax_lower or company.i3_config_razred_1_posto
                razred_2_posto = city_tax_higher or company.i3_config_razred_2_posto
                emp_slip_ids = slip_ids.filtered(lambda slip: slip.employee_id.id == emp)
                odbitak_po_mjesecu = {}
                for slip in emp_slip_ids:
                    lines = []
                    slip_month = slip.payslip_run_id.date_end.month
                    if not odbitak_po_mjesecu.get(slip_month):
                        odbitak_po_mjesecu[slip_month] = 0
                    line_ids = payslip_line.search(['&', ('slip_id', '=', slip.id), ('code', 'in', slip_line_codes)])
                    for line in line_ids:
                        osobni_odbitak = 0.00
                        osnovica_odbitka = osnovica
                        dohodak = 0.00
                        osnovica = 0.00
                        porez = 0.00
                        brutto = 0.00
                        salary_contributions = 0.00

                        osnovica_odbitka_moguce = 0

                        if slip.struct_id.code not in additional_income_structs:
                            if line.code == 'IOOD':
                                osobni_odbitak = line.amount
                                osnovica_odbitka = line.total
                                if slip.payslip_run_id.pay_date.month == max_pay_date.month:
                                    zadnji_odbitak = line.amount
                            if line.code == 'OOD' and line.total > odbitak_po_mjesecu[slip_month]:
                                odbitak_po_mjesecu[slip_month] = line.total
                                osnovica_odbitka_moguce = line.total
                            if line.code == 'DOH':
                                dohodak = line.amount
                            if line.code == 'POROSN':
                                osnovica = line.amount
                            if line.code == 'PDOH':
                                porez = line.amount
                            if line.code == 'BASIC':
                                brutto = line.amount
                            if line.code == 'DMIO':
                                salary_contributions = line.amount

                            lines.append({
                                'code': line.code,
                                'amount': line.amount,
                                'line_id': line.id,
                                'contract_id': line.contract_id.id,
                                'name': line.name,
                                'salary_rule_id': line.salary_rule_id.id,
                                'category_id': line.category_id.id
                            })
                            if slip.employee_id.id not in data:
                                data.update({slip.employee_id.id: {}})
                                data.update({slip.employee_id.id: {
                                    'odbitak': osobni_odbitak,
                                    'dohodak': dohodak,
                                    'salary_parameters_id': slip.salary_parameters_id.id,
                                    'contract_id':slip.contract_id.id,
                                    'osnovica': osnovica,
                                    'porez': porez,
                                    'brutto': brutto,
                                    'salary_contributions': salary_contributions,
                                    'osnovica_odbitka': osnovica_odbitka,
                                    'osnovica_odbitka_moguce': osnovica_odbitka_moguce,
                                    'lines': lines,
                                    'slip_id': slip.id,
                                    'number': slip.number,
                                    'osobni_odbici': [],
                                    'osobni_odbici_moguce': [osnovica_odbitka_moguce] if osnovica_odbitka_moguce else [],
                                    'journal_id': slip.journal_id.id,
                                    'state': slip.state,
                                    'godisnji_odbitak': slip.salary_parameters_id.annual_deduction,
                                    'zadnji_odbitak': zadnji_odbitak,
                                    'contract_id': slip.contract_id.id,
                                    'razred_1_posto': razred_1_posto,
                                    'razred_2_posto': razred_2_posto,
                                }})
                            else:
                                data[slip.employee_id.id]['odbitak'] += osobni_odbitak
                                data[slip.employee_id.id]['dohodak'] += dohodak
                                data[slip.employee_id.id]['osnovica'] += osnovica

                                data[slip.employee_id.id]['porez'] += porez
                                data[slip.employee_id.id]['brutto'] += brutto
                                data[slip.employee_id.id]['salary_contributions'] += salary_contributions
                                if osobni_odbitak > 0:
                                    data[slip.employee_id.id]['osobni_odbici'].append(osobni_odbitak)
                                if osnovica_odbitka_moguce > 0:
                                    data[slip.employee_id.id]['osobni_odbici_moguce'].append(osnovica_odbitka_moguce)
                                data[slip.employee_id.id]['osnovica_odbitka_moguce'] += osnovica_odbitka_moguce
                                data[slip.employee_id.id]['lines'] = lines
                                data[slip.employee_id.id]['slip_id'] = slip.id
                                data[slip.employee_id.id]['number'] = slip.number
                                data[slip.employee_id.id]['journal_id'] = slip.journal_id.id
                                data[slip.employee_id.id]['state'] = slip.state
                                data[slip.employee_id.id]['godisnji_odbitak'] = slip.salary_parameters_id.annual_deduction
                                data[slip.employee_id.id]['zadnji_odbitak'] = zadnji_odbitak
                                data[slip.employee_id.id]['razred_1_posto'] = razred_1_posto
                                data[slip.employee_id.id]['razred_2_posto'] = razred_2_posto
                                osobni_odbitak = 0
                                osnovica_odbitka_moguce = 0
                                dohodak = 0
                                osnovica = 0
                                porez = 0
                if annual_slip:
                    data[slip.employee_id.id].update({
                        'slip_annual_planned_deduction' : annual_slip.annual_planned_deduction,
                        'slip_annual_used_deduction' : annual_slip.annual_used_deduction,
                        'slip_annual_tax_base' : annual_slip.annual_tax_base,
                        'slip_annual_total_tax' : annual_slip.annual_total_tax,
                        'slip_annual_income' : annual_slip.annual_income,
                        'slip_annual_brutto' : annual_slip.annual_brutto,
                        'slip_annual_salary_contributions' : annual_slip.annual_salary_contributions,
                        'slip_annual_razred_1_posto' : annual_slip.i3_config_razred_1_posto,
                        'slip_annual_razred_2_posto' : annual_slip.i3_config_razred_2_posto
                    })
        return data

    def annual_calculation_get_planned_deduction(self, emp_data):
        params_obj = self.env['hr.salary.parameters']
        if emp_data['godisnji_odbitak'] == 0.00:
            # uzimamo odbitak s posljednjeg ugovora i mnozimo s 12
            # ako se odbitak mijenjao tijekom godine potrebno je na posljednji ugovor upisati ukupni godisnji iznos odbitka
            # ako zaposlenik nije radio cijelu godinu iznos ce sigurno biti pogresan, ali za takve se ionako ne radi godisnji obracun
            planirani_odbitak = 12 * params_obj.browse(emp_data['salary_parameters_id']).tax_deduction_amount

            # zakomentirani kod ne radi dobro u slucaju vise isplata mjesecno
            # na prvi listic se zapise kompletni moguci odbitak, a ne drugi preostali odbitak
            # radi dobro jedino u slucaju kad se na prvom listicu iskoristi cijeli odbitak
            # to je gotovo nikad jer se prvo isplacuje placa u naravi, sto su u pravilu manji iznosi
            # TODO: mozda bi radilo dobro kad bi se gledao samo prvi listic?
            # for odbitak_moguce in data[employee_id]['osobni_odbici_moguce']:
            #     planirani_odbitak += odbitak_moguce

            # sljedeci kod nije ispravan jer je moguce racunati udio osnovice odbitka, npr. 0,4*3800
            # planirani_odbitak = 3800
            # for deduction in contract_obj.browse(cr, uid, data[employee_id]['contract_id'], context).tax_deduction_ids:
            #     if deduction.status == True and deduction.tax_deduction_id.name != 'Osnovni osobni odbitak':
            #         planirani_odbitak += 2500 * deduction.tax_deduction_coef
            # planirani_odbitak *= number_of_payslip
        else:
            planirani_odbitak = emp_data['godisnji_odbitak']
        return planirani_odbitak
    def get_annual_calc_payslip_data(self, data, employee_id, fetch_data):
            planirani_odbitak = 0.00
            mjesecni_odbitak = 0.00

            dohodak = data[employee_id]['dohodak']
            if data[employee_id].get('slip_annual_income') and not fetch_data:
                dohodak = data[employee_id].get('slip_annual_income')

            osnovica = data[employee_id]['osnovica']
            if data[employee_id].get('slip_annual_tax_base') and not fetch_data:
                osnovica = data[employee_id].get('slip_annual_tax_base')

            porez = data[employee_id]['porez']
            if data[employee_id].get('slip_annual_total_tax') and not fetch_data:
                porez = data[employee_id].get('slip_annual_total_tax')

            brutto = data[employee_id]['brutto']
            if data[employee_id].get('slip_annual_brutto') and not fetch_data:
                brutto = data[employee_id].get('slip_annual_brutto')

            salary_contributions = data[employee_id]['salary_contributions']
            if data[employee_id].get('slip_annual_salary_contributions') and not fetch_data:
                salary_contributions = data[employee_id].get('slip_annual_salary_contributions')

            razred_1_posto = data[employee_id]['razred_1_posto']
            if data[employee_id].get('slip_annual_razred_1_posto') and not fetch_data:
                razred_1_posto = data[employee_id].get('slip_annual_razred_1_posto')

            razred_2_posto = data[employee_id]['razred_2_posto']
            if data[employee_id].get('slip_annual_razred_2_posto') and not fetch_data:
                razred_2_posto = data[employee_id].get('slip_annual_razred_2_posto')

            if data[employee_id].get('slip_annual_used_deduction') and not fetch_data:
                mjesecni_odbitak = data[employee_id].get('slip_annual_used_deduction')
            else:
                for odbitak in data[employee_id]['osobni_odbici']:
                    mjesecni_odbitak += odbitak
            planirani_odbitak = data[employee_id].get('osnovica_odbitka_moguce') #self.annual_calculation_get_planned_deduction(data[employee_id])
            if data[employee_id].get('slip_annual_planned_deduction') and not fetch_data:
                planirani_odbitak = data[employee_id].get('slip_annual_planned_deduction')
            return dohodak, osnovica, porez, mjesecni_odbitak, planirani_odbitak, brutto, salary_contributions, razred_1_posto, razred_2_posto


    def get_number_of_annual_payslips(self, employee_payslips):
        months_with_slip = list()
        for slip in employee_payslips:
            pay_month = slip.payslip_run_id.pay_date.month
            if pay_month not in months_with_slip:
                months_with_slip.append(pay_month)
        return len(months_with_slip)

    def annual_calculation_create_tax_difference_payslips(self, data, company, payslip_run, min_pay_date, max_pay_date, tolerance, fetch_data=False):
        """
        Create new payslips for differences - to keep tax payment history and shown on JOPPD form.

        If employee does not have a payslip, then create a new one. If employee already has a payslip and it is not manually edited, then refresh that payslip. If the payslip is manually edited, then do not alter it.
        """
        payslip_obj = self.env['hr.payslip']
        payslip_line_obj = self.env['hr.payslip.line']
        struct_id = self.env['hr.payroll.structure'].search([('code', '=', 'HR1')]).id

        razred_1 = company.i3_config_razred_1


        for employee_id in data:
            annual_calculation_payslips = self.annual_calculation_get_payslips([employee_id], min_pay_date, max_pay_date)
            address_changed = True if len(set([slip.city.zipcode for slip in annual_calculation_payslips])) > 1 else False #used for deleting payslips if employee changed address
            number_of_payslips = self.get_number_of_annual_payslips(annual_calculation_payslips) #used for deleting payslips if there are less than 12 payslips for annual calculation
            dohodak, osnovica, porez, mjesecni_odbitak, planirani_odbitak, brutto, salary_contributions, razred_1_posto, razred_2_posto = self.get_annual_calc_payslip_data(data, employee_id, fetch_data)
            nova_osnovica = 0.00
            nova_odbitak = 0.00
            razlika_odbitak = 0.00
            razlika_osnovica = 0.00
            razlika_porez = 0.00
            isplata = 0.00

            dohodak = brutto - salary_contributions #calculate again because we want brutto and salary_contributions fields to have impact on calculation               

            planirana_osnovica = dohodak - planirani_odbitak
            if planirana_osnovica < 0: # ako je osnovica manje od 0 vratiti cjelokupni iznos poreza
                if porez > 0:
                    planirani_porez = porez
                    razlika_porez = -1 *(porez)
                    isplata = -1 * razlika_porez
                    mjesecni_odbitak = planirani_odbitak
                    osnovica = planirana_osnovica
                else:
                    planirani_porez = 0
                    planirana_osnovica = 0
                    mjesecni_odbitak = planirani_odbitak
                    data[employee_id]['osnovica'] = planirana_osnovica
            else:
                if planirana_osnovica <= razred_1:
                    planirani_porez = (planirana_osnovica * (razred_1_posto / 100))
                else:
                    planirani_porez = (razred_1 * (razred_1_posto / 100)) + ((planirana_osnovica - razred_1) * (razred_2_posto / 100))
                if round(osnovica, 2) != round(planirana_osnovica, 2):
                    razlika_odbitak = -1 * round((mjesecni_odbitak - planirani_odbitak), 2)
                    razlika_osnovica = -1 * round((osnovica - planirana_osnovica), 2)
                    razlika_porez = -1 * (porez - planirani_porez)
                    isplata = -1 * razlika_porez

            number = data[employee_id]['number'][5:]
            if tolerance * (-1) <= isplata <= tolerance:
                annual_type = 'no_values'
            else:
                annual_type = 'values'

            employee_payslip = payslip_run.slip_ids.filtered(lambda s: s.employee_id.id == employee_id)
            if len(employee_payslip) <= 0:
                new_slip = payslip_obj.create({
                    'payslip_run_id': payslip_run.id,
                    'number': 'SLIP/' + number + '/annual',
                    # 'state': data[employee_id]['state'],
                    'name': 'Godišnji obračun poreza',
                    'date_from': min_pay_date,
                    'date_to': max_pay_date,
                    'employee_id': employee_id,
                    'line_ids': [],
                    'company_id': company.id,
                    'journal_id':  data[employee_id]['journal_id'],
                    'annual_calculation': True,
                    'salary_parameters_id': data[employee_id]['salary_parameters_id'],
                    'contract_id': data[employee_id]['contract_id'],
                    'struct_id': struct_id,
                    'payslips_number': number_of_payslips,
                    'annual_type': annual_type,
                    'annual_planned_deduction': planirani_odbitak,#data[employee_id]['osnovica_odbitka_moguce'],
                    'annual_used_deduction': mjesecni_odbitak,
                    'annual_tax_base': osnovica,
                    'annual_total_tax': porez,
                    'annual_income': dohodak,
                    'annual_brutto': brutto,
                    'annual_salary_contributions': salary_contributions,
                    'annual_tax_obligation': planirani_porez,
                    'annual_tax_calculated': razlika_porez,
                    'annual_planned_tax_base': planirana_osnovica,
                    'employee_changed_municipality': address_changed,
                })

                # parameters are not needed for calculation, but we need to copy address for report
                new_slip.get_calculation_parameters()
                for line in data[employee_id]['lines']:
                    tax_diff_data = {
                        'condition_python': 'result=True',
                        'contract_id': line['contract_id'],
                        'employee_id': employee_id,
                        'name': line['name'],
                        'code': line['code'],
                        'slip_id': new_slip.id, 
                        'salary_rule_id': line['salary_rule_id'],
                        'appears_on_payslip': True,
                        'amount_select': 'fix',
                        'category_id': line['category_id']
                    }
                    if line['code'] == 'OOD':
                        tax_diff_data.update({'amount': razlika_odbitak})
                        payslip_line_obj.create(tax_diff_data)
                    if line['code'] == 'POROSN':
                        tax_diff_data.update({'amount': razlika_osnovica})
                        payslip_line_obj.create(tax_diff_data)
                    if line['code'] == 'PDOH':
                        tax_diff_data.update({'amount': razlika_porez})
                        payslip_line_obj.create(tax_diff_data)
                    if line['code'] == 'ISPL':
                        tax_diff_data.update({'amount': isplata})
                        payslip_line_obj.create(tax_diff_data)
                new_slip.calculate_account_distribution()
            elif not employee_payslip.manual_edit:
                for line in data[employee_id]['lines']:
                    tax_diff_data = {
                        'condition_python': 'result=True',
                        'contract_id': line['contract_id'],
                        'employee_id': employee_id,
                        'name': line['name'],
                        'code': line['code'],
                        'slip_id': employee_payslip.id, 
                        'salary_rule_id': line['salary_rule_id'],
                        'appears_on_payslip': True,
                        'amount_select': 'fix',
                        'category_id': line['category_id']
                    }
                    if line['code'] == 'OOD':
                        tax_diff_data.update({'amount': razlika_odbitak})
                        payslip_line = employee_payslip.line_ids.filtered(lambda l: l.code == 'OOD')
                        if payslip_line:
                            payslip_line.write(tax_diff_data)
                        else:
                            payslip_line.create(tax_diff_data)
                    if line['code'] == 'POROSN':
                        tax_diff_data.update({'amount': razlika_osnovica})
                        payslip_line = employee_payslip.line_ids.filtered(lambda l: l.code == 'POROSN')
                        if payslip_line:
                            payslip_line.write(tax_diff_data)
                        else:
                            payslip_line.create(tax_diff_data)
                    if line['code'] == 'PDOH':
                        tax_diff_data.update({'amount': razlika_porez})
                        payslip_line = employee_payslip.line_ids.filtered(lambda l: l.code == 'PDOH')
                        if payslip_line:
                            payslip_line.write(tax_diff_data)
                        else:
                            payslip_line.create(tax_diff_data)
                    if line['code'] == 'ISPL':
                        tax_diff_data.update({'amount': isplata})
                        payslip_line = employee_payslip.line_ids.filtered(lambda l: l.code == 'ISPL')
                        if len(payslip_line) > 0:
                            payslip_line.write(tax_diff_data)
                        else:
                            payslip_line.create(tax_diff_data)
                #reset fields for manual input in Annual calculation tab
                employee_payslip.write({
                    'annual_planned_deduction': planirani_odbitak,
                    'annual_used_deduction': mjesecni_odbitak,
                    'annual_tax_base': osnovica,
                    'annual_total_tax': porez,
                    'annual_income': dohodak,
                    'annual_brutto': brutto,
                    'annual_salary_contributions': salary_contributions,
                    'employee_changed_municipality': address_changed,
                    'annual_type': annual_type,
                    'payslips_number': number_of_payslips,
                    'annual_tax_obligation': planirani_porez,
                    'annual_tax_calculated': razlika_porez,
                    'annual_planned_tax_base': planirana_osnovica,
                })
                employee_payslip.calculate_account_distribution()
        return True
    
    def annual_calculation(self, employees, tolerance):
        """
        Annual tax calculation.
        Iterate through all payslips from whole year for all employees that are on current (12 month) payslip.
        Only regular salary and salary in kind are included.
        """
        payslip_run = self.browse(self.id)
        pay_date = payslip_run.pay_date
        company = self.env.user.company_id

        max_pay_date = str(pay_date.year) + '-12-31'
        min_pay_date = str(pay_date.year) + '-01-01'

        emp_ids = self.annual_calculation_get_employees(min_pay_date, max_pay_date) if len(employees) == 0 else employees
        slip_ids = self.annual_calculation_get_payslips(emp_ids, min_pay_date, max_pay_date)
        data = self.annual_calculation_get_employee_payslips_data(slip_ids, company, max_pay_date)
        tolerance = self.payslips_without_tax_return_tolerance
        self.annual_calculation_create_tax_difference_payslips(data, company, payslip_run, min_pay_date, max_pay_date, tolerance)
        self.write({'annual_calc': True})
        return True

    def annual_calculation_open_wizard(self):
        return {
            'name': "Annual calculation wizard",
            'type': 'ir.actions.act_window',
            'view_type': 'form',
            'view_mode': 'form',
            'res_model': 'annual.calculation.wizard',
            'view_id': self.env.ref('l10n_hr_hr_payroll.view_annual_calculation_wizard').id,
            'target': 'new',
            'context': {'payslip_run_id': self.id},
            }

    def annual_calculation_delete_employees_without_tax_return(self):
        """
        Delete payslips that dont have tax differences for this payslip run.
        """
        slips = self.slip_ids.filtered(lambda s: s.annual_type == 'no_values')
        return self.delete_payslips(slips)

    def annual_calculation_delete_incomplete_employees(self):
        """
        Delete payslips for this payslip run for those employees who did not work full year, i.e. who have less than 12 payslips.
        """
        slips = self.slip_ids.filtered(lambda s: s.payslips_number < 12)
        return self.delete_payslips(slips)

    def annual_calculation_delete_employees_residence(self):
        """
        Delete payslips of employees whose address has changed in the current year. Only applies if the address has been changed to different municipality.
        """
        slips = self.slip_ids.filtered(lambda s: s.employee_changed_municipality)
        return self.delete_payslips(slips)

    def delete_payslips(self, slips):
        if len(slips) > 0:
            query = "delete from hr_payslip where id in %s"
            self._cr.execute(query, (tuple(slips.ids),))
        return True
    def annual_calculation_action(self):
        c = self.env.context.copy()
        c = {'payslip_run_id': self.id}
        action_rec = self.env['ir.model.data'].xmlid_to_object('l10n_hr_hr_payroll.action_annual_calculation_wizard')
        if action_rec:
            action = action_rec.read([])[0]
            action.update({'context': c})
            return action
        return True

    def get_move_id(self):
        move_obj = self.env['account.move']
        header = self.get_move_header()
        if not self.move_id:
            move_id = move_obj.create(header)
        else:
            move_id = self.move_id
            move_id.sudo().write(header)
        return move_id
    
    def create_payroll_account_move(self):
        """
        @var data - accounting data gathered based on settings entered on salary rules and payslip run.
        1. There is no related account move:
            a) there is no data - do nothing
            b) there is data - create account move
        2. Related account move exists:
            a) overwrite header and lines, even if data is empty
        """
        data = self.accounting_calculation_prepare_data()
        if not data and not self.move_id:
            return True
        move_id = self.get_move_id()
        self.create_move_lines(data, move_id)
        self.write({'move_id': move_id.id})
        return True
    
    def get_tags_from_accounts(self, accounts):
        dist_obj = self.env['account.analytic.distribution']
        tag_ids = []
        for account in accounts:
            dist = dist_obj.search([('account_id', '=', account.id), ('tag_id.created_from_account', '=', True)], limit=1)
            tag_ids.append(dist.tag_id.id)
        return tag_ids
    
    def accounting_get_default_lines(self, payslip_line):
        """
        Default amount for account move line used when there is no analytic distribution.
        """
        default_lines = [{
            'amount': payslip_line.total,
            'tag_ids': [],
        }]
        return default_lines
    
    def accounting_get_analytic_lines(self, payslip_line, scheme):
        """
        Create analytic distribution for payslip line.
        Return percentage of payslip line amount, as set on department distribution line.
        For last department line use deduction instead of multiplication so totals match.
        """
        line_data = []
        if not scheme.use_analytic_distribution:
            return line_data
        dep_lines = payslip_line.slip_id.department_distribution_ids
        dep_lines_len = len(dep_lines)
        dep_lines_total = 0
        for i, dep_line in enumerate(dep_lines):
            if i == (dep_lines_len - 1):
                amount = payslip_line.total - dep_lines_total
            else:
                amount = round(payslip_line.total * dep_line.percentage / 100.00, 2)
            line_data.append({
                'amount': amount,
                'tag_ids': self.get_tags_from_accounts([dep_line.department_analytic_id, dep_line.cost_center_id]),
            })
            dep_lines_total += amount
        return line_data
    
    def use_analytic_lines(self, account, analytic_account_type_ids, department_distribution_ids):
        """
        Analytic lines are used if account type matches one of the types defined in company settings.
        If there is no distribution set on payslip / employee, we do not use analytic lines even if account type says we should.
        The reason for that is because analytic lines are not created if there is no distribution,
        meaning account move is not balanced and not all payslip lines are taken into account.
        We prefer the account move to be balanced and all payslip lines to be considered, even if not all required analytics are satisfied.
        There is an analytics tag validation for move lines (validate_required_analytic_accounts())
        which prevents posting such account move so we don't have to worry about that.
        """
        return department_distribution_ids and account.user_type_id and account.user_type_id.id in analytic_account_type_ids
    
    def add_key_to_account_data(self, account_data, key, line_name, line_type, code, tag_ids):
        account_data.update({
            key: {
                'amount': 0,
                'name': line_name,
                'type': line_type,
                'code': code,
                'tag_ids': tag_ids,
            }
        })
        return account_data
    
    def update_move_line_data(self, account_data, line_type, account, default_lines, analytic_lines, line_key, line_name, 
                                department_distribution, analytic_account_type_ids):
        """
        Add or update move line based on given parameters.
        """
        use_analytic_lines = self.use_analytic_lines(account, analytic_account_type_ids, department_distribution)
        lines = use_analytic_lines and analytic_lines or default_lines
        for line in lines:
            # update move line key with analytic tags
            # final key needs to be a tuple, recieved key is a list
            tag_ids = line['tag_ids']
            tag_key = tuple(set(tag_ids))
            line_key.append(tag_key)
            key = tuple(line_key)
            if key not in account_data:
                account_data = self.add_key_to_account_data(account_data, key, line_name, line_type, account.code, tag_ids)
            account_data[key]['amount'] += line['amount']
        return account_data
    
    def _accounting_get_rule_schemes(self, scheme_type_id):
        """
        Create rule -> scheme mapping for easier access to scheme settings.
        The direction we need is payslip_line -> salary_rule_id -> corresponding scheme (as set on payslip run).
        """
        scheme_obj = self.env['hr.payroll.accounting.scheme']
        schemes = scheme_obj.search([('type_id.id', '=', scheme_type_id.id)])
        rules = schemes.mapped('rule_id')
        mapping = {}
        for scheme in schemes:
            mapping.update({
                scheme.rule_id.id: scheme
            })
        return rules, mapping

    def accounting_calculation_prepare_data(self):
        """
        Gather data based on crediting and grouping settings entered on salary rules and payslip run.
        Specific settings can be used for salary in kind.
        Disability fee can be credited if payment exists and crediting settings are entered.
        """
        run = self.browse(self.id)
    
        lines_obj = self.env['hr.payslip.line']
        rule_obj = self.env['hr.salary.rule']
        account_data = {}
        scheme_type_id = run.hr_accounting_scheme_type_id
        if not scheme_type_id:
            return account_data
        rules, scheme_mapping = self._accounting_get_rule_schemes(scheme_type_id)

        employee_list = []
        for slip in run.slip_ids:
            # read here to use n times later
            department = slip.salary_parameters_id.department_id
            employee = slip.employee_id
            department_distribution = slip.department_distribution_ids
            analytic_account_type_ids = slip.i3_config_analytic_distribution_account_type_ids.ids
            if employee.id not in employee_list:
                employee_list.append(employee.id)
            payslip_line_ids = lines_obj.search([('salary_rule_id', 'in', rules.ids), ('slip_id', '=', slip.id)])
            for payslip_line in payslip_line_ids:
                rule = payslip_line.salary_rule_id
                scheme = scheme_mapping.get(rule.id)

                debit_account = scheme.account_debit
                credit_account = scheme.account_credit
                default_lines = self.accounting_get_default_lines(payslip_line)
                analytic_lines = self.accounting_get_analytic_lines(payslip_line, scheme)
                if scheme.department_account_ids:
                    # case where every department has account
                    for account in scheme.department_account_ids:
                        dep_debit_account = account.debit_account_id
                        dep_credit_account = account.credit_account_id
                        # debit
                        payslip_in_department = (account.department_id.id == department.id)
                        if dep_debit_account and payslip_in_department and not scheme.group_debit:
                            line_key = [dep_debit_account.id, account.department_id.id, 'debit']
                            line_name = run.name + " - " + account.department_id.name
                            account_data = self.update_move_line_data(
                                account_data, 'debit', dep_debit_account, default_lines, analytic_lines, 
                                line_key, line_name, department_distribution, analytic_account_type_ids)

                        # credit
                        if dep_credit_account and payslip_in_department and not scheme.group_credit:
                            line_key = [dep_credit_account.id, account.department_id.id, 'credit']
                            line_name = run.name + " - " + account.department_id.name
                            account_data = self.update_move_line_data(
                                account_data, 'credit', dep_credit_account, default_lines, analytic_lines, 
                                line_key, line_name, department_distribution, analytic_account_type_ids)
                # case when grouping by department is set  
                elif scheme.group_by_department:
                    # debit
                    line_key = [debit_account.id, department.id, 'debit']
                    line_name = run.name + ' - ' + department.name
                    account_data = self.update_move_line_data(
                        account_data, 'debit', debit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)
                    
                    # credit
                    line_key = [credit_account.id, department.id, 'credit']
                    line_name = run.name + ' - ' + department.name
                    account_data = self.update_move_line_data(
                        account_data, 'credit', credit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                elif scheme.group_by_employee:
                    # debit
                    line_key = [debit_account.id, employee.id, rule.id, 'debit']
                    line_name = employee.name + ' - ' + payslip_line.name
                    account_data = self.update_move_line_data(
                        account_data, 'debit', debit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                    # credit
                    line_key = [credit_account.id, employee.id, rule.id, 'credit']
                    line_name = employee.name + ' - ' + payslip_line.name
                    account_data = self.update_move_line_data(
                        account_data, 'credit', credit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)
                    
                # debit
                if debit_account and scheme.group_debit:
                    line_key = [debit_account.id, 'placeholder', 'debit']
                    line_name = run.name
                    account_data = self.update_move_line_data(
                        account_data, 'debit', debit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                elif debit_account and not scheme.group_debit and not scheme.group_by_municipality and not scheme.group_by_department and not scheme.group_by_employee:
                    # debit
                    line_key = [debit_account.id, 'placeholder', 'debit']
                    line_name = run.name
                    account_data = self.update_move_line_data(
                        account_data, 'debit', debit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                # credit
                if credit_account and scheme.group_credit:
                    line_key = [credit_account.id, 'placeholder', 'credit']
                    line_name = run.name
                    account_data = self.update_move_line_data(
                        account_data, 'credit', credit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                elif credit_account and not scheme.group_credit and not scheme.group_by_municipality and not scheme.group_by_department and not scheme.group_by_employee:
                    # credit
                    line_key = [credit_account.id, 'placeholder', 'credit']
                    line_name = run.name
                    account_data = self.update_move_line_data(
                        account_data, 'credit', credit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                if scheme.group_by_municipality and scheme.department_account_ids:
                    # TODO: this isn't fully supported
                    # #debit
                    # if debit_account and not scheme.group_debit:
                    #     if (credit_account.id,city.id) not in account_data:
                    #             account_data.update({(debit_account.id,city.id): 
                    #                                 {'amount': payslip_line.total, 'name': city.name + ' ' +  payslip_line.name, 
                    #                                 'journal_id':slip.journal_id.id, 'type':'debit'}})
                    #     else:
                    #         account_data[(debit_account.id,city.id)]['amount'] += payslip_line.total
                    # credit
                    city = slip.city
                    key = (credit_account.id, city.id, 'credit')
                    if credit_account and not scheme.group_credit:
                        if key not in account_data:
                            account_data.update({
                                key: {
                                    'amount': payslip_line.total,
                                    'name': city.name + ' ' + payslip_line.name ,
                                    'type':'credit',
                                    'code': credit_account.code
                                }
                            })
                        else:
                            account_data[key]['amount'] += line['amount'] 
                elif scheme.group_by_municipality:
                    city = slip.city
                    # debit
                    line_key = [debit_account.id, city.id, 'debit']
                    line_name = city.name + ' ' + payslip_line.name
                    account_data = self.update_move_line_data(
                        account_data, 'debit', debit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

                    # credit
                    line_key = [credit_account.id, city.id, 'credit']
                    line_name = city.name + ' ' + payslip_line.name
                    account_data = self.update_move_line_data(
                        account_data, 'credit', credit_account, default_lines, analytic_lines, line_key, line_name, 
                        department_distribution, analytic_account_type_ids)

        if run.disability_fee_payment_id:
            payment = run.disability_fee_payment_id
            credit_account = payment.disability_fee_credit_account_id
            debit_account = payment.disability_fee_debit_account_id
            credit_disability_fee = payment.credit_disability_fee and credit_account and debit_account
            if credit_disability_fee:
                credit_key = (credit_account.id, False)
                debit_key = (debit_account.id, False)
                account_data.update({
                    credit_key: {
                        'amount': payment.disability_fee_amount,
                        'name': run.name,
                        'type':'credit'
                    },
                    debit_key: {
                        'amount': payment.disability_fee_amount,
                        'name': run.name,
                        'type': 'debit'
                    }
                })

        delete_list = []
        for el in account_data:
            if account_data[el]['amount'] == 0:
                delete_list.append(el)
        for el in delete_list:
            del account_data[el]  
        return account_data

    def get_move_header(self):
        """
        Create account move for payslip run or write if it already exists.
        """
        run = self.browse(self.id)
        name = run.name or ("Batch " + timenow)

        #move header data
        header_data = {
            'narration': name,
            'date': run.date_end,
            'ref': name,
            'journal_id': run.journal_id.id,
        }
        return header_data


    def create_move_lines(self, data, move_id):
        """
        Use context to skip analytic tags constraint so user can see actually the lines before error message.
        The constraint is instead triggered manually on post().
        """
        run = self.browse(self.id)
        move_lines_list = []
        for line in data:
            debit_amount = ((data[line]['type'] == 'debit') and data[line]['amount']) or 0.0
            credit_amount = ((data[line]['type'] == 'credit') and data[line]['amount']) or 0.0
            code = data[line]['code'] if 'code' in data[line] else '5000' # disability fee has no code
            # period_id, tax_code_id, tax_amount fields do not exist (yet) so they are commented out
            move_line_dict = {
                'name': data[line]['name'],
                'date': run.date_end,
                'partner_id': False,
                'account_id': line[0],
                'debit': debit_amount,
                'credit': credit_amount,
                'code': code, # used only for sorting
            }
            move_lines_list.append(move_line_dict)
        
        move_lines_list = sorted(move_lines_list, key=itemgetter('code'), reverse = True)
        for move_line in move_lines_list:
            del move_line['code'] # to avoid warning in log
        # use sudo() to avoid stock picking read access error
        move_id.with_context({'skip_analytic_tags_constraint': True}).sudo().write({'line_ids': [(0, 0, i) for i in move_lines_list]})
        return True

    def post_salary_account_move(self):
        """
        Post existing account move related to payslip run.
        Trigger move lines constraint manually because it has been skipped on create (in pay_payslip_run()).
        Use sudo() to avoid missing access rights for asset depreciation line - if hr_assets is installed.
        """
        if self.move_id:
            self.write({'state':'posted'})       
            self.move_id.sudo().action_post()
        return True

    def cancel_post(self):
        """Cancel existing account move related to payslip run."""
        if self.move_id:
            self.write({'state':'paid'})       
            self.move_id.button_cancel()
        return True

    def get_currency_rates(self, vals):
        """
        Get rates for EUR for work abroad and suspensions calculation.
        """
        currency_obj = self.env['res.currency']
        rates = {
            'i3_currency': 0.0,
            'i3_work_abroad_currency': 0.0,
        }
        company = self.env.user.company_id
        from_currency = currency_obj.search([('name', '=', 'EUR')], limit=1)
        to_currency = company.currency_id
        if not from_currency or not to_currency:
            return rates
        work_abroad_date = vals.get('date_end')
        suspensions_date = fields.Datetime.today()
        rates['i3_work_abroad_currency'] = currency_obj._get_conversion_rate(from_currency, to_currency, company, work_abroad_date)
        rates['i3_currency'] = currency_obj._get_conversion_rate(from_currency, to_currency, company, suspensions_date)
        return rates

    def clear_payslip_lines(self):
        """
        Delete all payslip lines.
        """
        sql = "DELETE FROM hr_payslip_line WHERE slip_id in " \
              "(SELECT id FROM hr_payslip WHERE payslip_run_id = %s)"
        try:    
            self.env.cr.execute(sql, (self.id,))
            self.env.cr.commit()
        except:
            return False
        
        return True

    def action_send_payslips_by_email(self):
        for run in self:
            run.slip_ids.action_send_by_email()
