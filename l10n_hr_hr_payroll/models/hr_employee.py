# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
import datetime
from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from . import payroll_common as paycom


class Employee(models.Model):
    _inherit = 'hr.employee'

    def _get_max_annual_leave_amount(self):
        params_obj = self.env['ir.config_parameter']
        return float(params_obj.sudo().get_param('l10n_hr_hr_payrol.i3_config_max_annual_leave'))

    # @api.model
    def _is_employee_search(self, operator, value):
        """
        Return ids of all employees with same is_employee value.
        Used to filter domain on reports, creating payslip_run and employee tree view.
        Implemented this way because it didn't always work with store=True.
        """
        result = [('id', '=', '0')]
        # we need to return both active and inactive employees here because other filters do the rest
        emp_ids = self.search(['|', ('active', '=', True), ('active', '=', False)])
        ids = []
        for emp in emp_ids:
            if emp.is_employee == value:
                ids.append(emp.id)
        result = [('id', 'in', ids)]
        return result
    is_foreign_citizen = fields.Boolean('Strani državljanin')
    termination_date = fields.Date('Datum prestanka radnog odnosa', help="Datum raskida ugovora.", compute='_calculate_termination', store=True)
    hire_date = fields.Date('Datum zaposlenja', help="Datum zaposlenja", tracking =True)

    bank_account_ids = fields.One2many('employee.bank.account.line', 'employee_id', string='Bankovni Računi', tracking=True, required=True)
    rescheduled_hours_ids = fields.One2many('info3.rescheduled.hours', 'employee_id', compute='_get_rescheduled_hours', string='Preraspodjeljeni Sati',help='Preraspodjeljeni sati po mjesecima')
    total_tax_deduction = fields.Float('Iskorišteni Osobni Odbitak', digits=('Payroll'))
    total_tax_base = fields.Float('Prethodna Porezna Osnovica', digits=('Payroll'))
    suspension_ids = fields.One2many('hr.salary.suspension', 'employee_id', 'Obustave', help='Lista obustava za ovog korisnika koja se koristi kod izračuna plaće', tracking=True)
    average_wage = fields.Float('Postavka Prosječne Plaće', related='company_id.i3_config_average_wage')
    taxless_payment_ids = fields.One2many('employee.taxless.payment.line', 'employee_id', 'Neoporezive Isplate')
    annual_leave_yearly_ids = fields.One2many('info3.hr.employee.annual.leave.year','employee_id','Godišnji odmor po godinama', tracking=True)
    annual_leave_periodically_ids = fields.One2many('info3.hr.employee.annual.leave.periodically','employee_id','Godišnji odmor po mjesecima', tracking=True)
    average_gross_wage = fields.Float('Prosječna bruto satnica', digits=('Payroll Hourly Wage'), tracking=True)
    period_from = fields.Date('Razdoblje Od', required=False, tracking=True)
    period_to = fields.Date('Razdoblje Do', required=False, tracking=True)
    params_id = fields.Many2one('hr.salary.parameters', compute='_compute_params_id', string='Trenutni Parametri Plaće')
    is_employee = fields.Boolean('Je Zaposlenik', compute='_get_is_employee', search='_is_employee_search', compute_sudo=True,
        help="Govori da li je osoba zaposlenika u tvrtki ili je vanjski suradnik")
    use_avg_hourly_wage_for_annual_leave_calculation = fields.Boolean('Računaj godišnji odmor prema satnici', tracking=True, compute='_compute_hourly_wage_for_annual_leave_calculation_usage')
    #added to allow setting up more departments for one employee
    department_distribution_ids = fields.One2many('hr.employee.department.distribution', 'employee_id', 'Analitička raspodjela po odjelima')
    department_weighted_distribution = fields.Boolean("Težinska Raspodjela")
    annual_leave_max_amount = fields.Float('Maksimalna količina godišnjeg odmora', default=_get_max_annual_leave_amount, tracking=True)
    job_history_ids = fields.One2many(string='Povijest napredovanja', comodel_name='hr.employee.job.history', inverse_name='employee_id', tracking=True)

    @api.constrains('bank_account_ids')
    def _check_bank_account_ids(self):
        for rec in self:
            for acc in rec.bank_account_ids:
                if acc.bank_account_id.partner_id != rec.partner_id:
                    raise ValidationError(_('Vlasnik bankovnog računa mora biti jednak partneru zaposlenika.'))

    @api.depends('use_avg_hourly_wage_for_annual_leave_calculation')
    def _compute_hourly_wage_for_annual_leave_calculation_usage(self):
        for rec in self:
            rec.use_avg_hourly_wage_for_annual_leave_calculation = rec.company_id.i3_config_use_avg_hourly_wage_for_annual_leave_calculation

    @api.depends('contract_ids', 'contract_ids.termination_date')
    def _calculate_termination(self):
        for emp in self:
            latest_contract = emp.contract_ids.sorted(key=lambda c: c.date_start, reverse=True)[:1]
            emp.termination_date = latest_contract.termination_date

    @api.onchange('department_distribution_ids','department_weighted_distribution')
    def _onchange_percentage(self):
        """
        onchange method called to update percentage field if there is more than one
        - if department_weighted_distribution is checked skip calculation
        """''
        if self.department_weighted_distribution:
            return
        for rec in self.department_distribution_ids:
            rec.percentage = 100.00 / len(self.department_distribution_ids)

    def _compute_params_id(self):
        """Get the latest salary parameters"""
        params_obj = self.env['hr.salary.parameters']
        for employee in self:
            employee.params_id = params_obj.search([('employee_id', '=', employee.id)], order='date_from desc', limit=1)

    @api.constrains('suspension_ids')
    def is_bank_account_distribution_set(self):
        """
        Do not allow suspensions without bank distribution.
        """
        for suspension in self.suspension_ids:
            if not suspension.bank_account_distribution_ids:
                raise ValidationError('Raspodjela po bankovnim računima mora biti postavljena za obustavu {0}.'.format(suspension.name))

    def _get_is_employee(self):
        """
        Return if employee is an actual employee or an associate, based on information from last contract.
        Employee is considered an associate if one of additional income structures is selected.
        """
        additional_income_structs = paycom.get_structures()['additional_income']
        for emp in self:
            is_employee = True
            if emp.params_id and emp.params_id.sudo().struct_id.code in additional_income_structs:
                is_employee = False
            emp.is_employee = is_employee

    def has_payment_in_year(self, year_id):
        """
        Return whether employee has payment in selected year (for IP card).
        """
        emp_id = self.id
        year = self.env['account.fiscal.year'].browse(year_id)
        domain = [
            ('payslip_run_id.pay_date', '>=', year.date_from),
            ('payslip_run_id.pay_date', '<=', year.date_to),
            ('employee_id', '=', emp_id)
        ]
        emp_slip_ids = self.env['hr.payslip'].search(domain)
        has_payment = True if emp_slip_ids else False
        return has_payment


    @api.constrains('annual_leave_yearly_ids', 'annual_leave_periodically_ids')
    def _check_annual_leaves(self):
        """
        Each monthly annual leave record must have corresponding yearly record.
        Constraint is only triggered when adding annual leave manually on form.
        Monthly annual leave can also be added through compute_sheet method on hr.payslip.
        """
        monthly_obj = self.env['info3.hr.employee.annual.leave.periodically']
        yearly_ids = [leave_yearly.year.id for leave_yearly in self.annual_leave_yearly_ids]
        years_missing = []
        monthly_ids = self.annual_leave_periodically_ids.filtered(
            lambda r: r.period.fiscal_year.id not in yearly_ids
        )
        for leave_monthly in monthly_ids:
            if leave_monthly.period.fiscal_year.name not in years_missing:
                years_missing.append(leave_monthly.period.fiscal_year.name)
        if years_missing:
            raise ValidationError(_(u'Annual leave for the year must be entered before entering monthly leaves. Years: {0}'.format('\n' + '\n'.join(years_missing))))
    
    def get_used_annual_leave_before_date(self, date):
        """
        Return total used annual leave for the year including period which contains given date.
        """
        monthly_obj = self.env['info3.hr.employee.annual.leave.periodically']
        domain = [('employee_id', '=', self.id), ('period.fiscal_year.name', '=', date.year), ('period.date_start', '<=', date)]
        leave_ids = self.annual_leave_periodically_ids.filtered(
            lambda r: r.period.fiscal_year.name == date.year and
                    r.period.date_start <= date
        )
        used_leave = sum([leave.used_leave for leave in leave_ids])
        return used_leave
        

    @api.onchange('annual_leave_periodically_ids')
    def onchange_annual_leave_by_period(self):
        """ Update yearly leaves when monthly leaves are updated on employee form view."""
        self.update_used_leave_by_year()
        
    def update_used_leave_by_year(self):
        """ Update used leave by year based on monthly leaves."""
        res = {}
        for leave_yearly in self.annual_leave_yearly_ids:
            res.update({leave_yearly.year.id: 0})
        for leave_monthly in self.annual_leave_periodically_ids:
            if leave_monthly.period.fiscal_year.id not in res:
                res.update({leave_monthly.period.fiscal_year.id: 0})
            res[leave_monthly.period.fiscal_year.id] += leave_monthly.used_leave
        for leave_yearly in self.annual_leave_yearly_ids:
            leave_yearly.used_leave = res[leave_yearly.year.id]

    def get_bank_accounts_on_date(self, date):
        """
        Get bank accounts for employee on given date.
        Only one account per type is returned.
        If there are more accounts per type, we return the one with main_account=True or the latest one.
        """
        PartnerBank = self.env['res.partner.bank']
        bank_accounts = {
            'normal': PartnerBank,
            'protected': PartnerBank,
            'giro_account': PartnerBank,
        }
        bank_line_obj = self.env['employee.bank.account.line']
        domain = [
            ('employee_id', '=', self.id),
            ('date_from', '<=', date),
            '|', ('date_to', '>=', date), ('date_to', '=', False)
        ]
        bank_lines = bank_line_obj.search(domain, order="account_type, main_account ASC, date_from ASC, id DESC")
        for bank_line in bank_lines:
            bank_accounts[bank_line.account_type] = bank_line.bank_account_id
        return bank_accounts

    def _get_rescheduled_hours(self):
        """
        Delete previous records and create new ones based on current timesheet for employee.
        """
        if 'info3.timesheet' in self.env:
            sheet_obj = self.env['info3.timesheet']
            resch_obj = self.env['info3.rescheduled.hours']
            for emp in self:
                resch_ids = resch_obj.search([('employee_id', '=', emp.id)])
                resch_ids.unlink()
                emp_resch_hours = []
                emp_month_data = {}
                emp_sheets = sheet_obj.search([('employee_id', '=', emp.id), ('rescheduled_hours', '!=', 0)], order="date")
                previous_date = False
                date = False
                for sheet in emp_sheets:
                    date = sheet.date
                    if not emp_month_data:
                        # first sheet -> init dict for first month
                        previous_date = sheet.date
                        emp_month_data = {
                            'employee_id': emp.id,
                            'date': str(date.year) + '-' + "{:0>2}".format(str(date.month)),
                            'number_of_hours': sheet.rescheduled_hours,
                        }
                    else:
                        if date.month == previous_date.month:
                            # same month -> add hours
                            emp_month_data['number_of_hours'] += sheet.rescheduled_hours
                        else:
                            # different month -> create record for previous month, init dict for new month
                            resch_id = resch_obj.create(emp_month_data)
                            emp_resch_hours.append(resch_id)
                            previous_date = date
                            emp_month_data = {
                                'employee_id': emp.id,
                                'date': str(date.year) + '-' + "{:0>2}".format(str(date.month)),
                                'number_of_hours': sheet.rescheduled_hours,
                            }
                if date and previous_date and date.month == previous_date.month:
                    # last timesheet record was in the same month as the second to last so hours were added but rescheduled hours record was not created
                    resch_id = resch_obj.create(emp_month_data)
                    emp_resch_hours.append(resch_id)
                emp_resch_hours = resch_obj.search([('employee_id', '=', emp.id)])
                emp.rescheduled_hours_ids = emp_resch_hours

    # override of get_contract in l10n_hr_payroll_base.py because it didn't recognize contracts with both start and end date within given period
    def info3_get_contract_in_period(self, date_from, date_to):
        "Return ids of all contracts for given employee and time span."
        con_ids = []
        if self.id:
            sql = """SELECT id FROM hr_contract
                        WHERE active = True AND
                        employee_id = {0} AND (
                        date_start >= '{1}' AND date_start <= '{2}'
                        OR date_end >= '{1}' AND date_end <= '{2}'
                        OR date_start < '{1}' AND (date_end >= '{1}' OR date_end IS NULL)
                        )
                        ORDER BY date_start DESC""".format(self.id, date_from, date_to)
            self.env.cr.execute(sql)
            con_ids = self.env.cr.dictfetchall()
        con_ids = [x['id'] for x in con_ids]
        return con_ids

    def get_consecutive_contracts(self, date):
        """
        Return all contracts since employee last joined company without interruption (in ascending order).
        """
        contract_obj = self.env['hr.contract']
        domain = [('employee_id', '=', self.id), ('date_start', '<=', date), '|', ('active', '=', True), ('active', '=', False)]
        contracts = contract_obj.search(domain, order='date_start DESC')
        previous_date_start = None
        contract_list = []
        for contract in contracts:
            # last contract
            if not previous_date_start:
                previous_date_start = contract.date_start
                contract_list.append(contract)
            # not last contract and it ends just before the next one
            elif (contract.date_end and previous_date_start and
                    previous_date_start == contract.date_end + relativedelta(days = 1)):
                previous_date_start = contract.date_start
                contract_list.append(contract)
            # not last contract and no end date - in an ideal case we dont have those, in reality however...
            elif not contract.date_end:
                previous_date_start = contract.date_start
                contract_list.append(contract)
            else:
                break
        contract_list.reverse()
        return contract_list

    def _payslip_lines_total(self, date_from, date_to, line_codes):
        """ Calculate used tax base in period.
            There are 2 tax rates applied in salary calculation, based on total tax base.
            Yearly limit is written in company.i3_config_razred_1 field, and monthly limit is the same amount divided by 12.
            Salary is calculated monthly and tax base limit is also applied monthly so in most cases we don't need the info this method provides.
            However in some specific cases we want to know where we are with the tax base on yearly basis.
            At the end of the year (December) tax is calculated on yearly basis anyway to see if there is need for tax returns, and this method is basically used to manipulate this.
            Example:
                - limit is 360.000 yearly => 30.000 monthly
                - in December we want to pay the equivalent of 100.000 tax base to an employee
                - by default the lower rate is applied on 30.000, and the higher rate on the remaining 70.000
                - however, we know that the employee has more than the 100.000 'unused' for the year and on yearly tax calculation a lot of tax paid will be returned to them
                - we want to manipulate this in advance and see on which amount the lower rate will be applied
                - for this we need to calculate how much tax base has been used already
        Args:
            date_from (date): start of the period
            date_to (date): end of the period
    
        Returns:
            dict: {employee: total of payslip lines paid in period}
        """
        payslip_domain = [
            ('date_from', '>=', date_from),
            ('date_to', '<=', date_to),
            ('employee_id', 'in', self.ids),
            ('state', '=', 'paid'),
        ]
        payslips = self.env['hr.payslip'].search(payslip_domain)
        data = dict()
        for employee in self:
            employee_slips = payslips.filtered(lambda slip: slip.employee_id == employee)
            data.update({
                employee.id: sum(employee_slips.mapped('line_ids').filtered(lambda line: line.code in line_codes).mapped('total'))
            })
        return data

    def _planned_tax_deduction(self, date_from, date_to):
        """ Calculate planned tax deduction for employee.
            Can be used for annual tax calculation.
            For each month (in period), find a set of salary parameters and add its tax deduction.
            Issues:
                - if we have more than one set in same month, we add deduction from the first one and the rest are disregarded
        Args:
            date_from (date): period start date
            date_to (date): period end date
        Returns:
            dict: {employee: total tax deduction in period}
        """
        def are_parameters_valid(employee, loop_date_from):
            return lambda param: param.employee_id == employee and param.date_from <= loop_date_from and (not param.date_to or param.date_to >= loop_date_from)

        # all parameters ending after period start or not ending at all
        parameters_domain = [
            ('employee_id', 'in', self.ids),
            '|', ('date_to', '=', False),
            ('date_to', '>=', date_from)
        ]
        parameters = self.env['hr.salary.parameters'].search(parameters_domain, order='employee_id, date_from ASC')
        data = dict()
        for employee in self:
            data.update({employee.id: 0})
            month = date_from.month
            year = date_from.year
            # new variable to use specifically for looping and to not spoil original date_from
            loop_date_from = date_from.replace(day=1)
            params = parameters.filtered(are_parameters_valid(employee, loop_date_from))
            # there should be no overlap between employees parameters so we should always get one or none from the above condition
            # just in case, make sure there is not more than one parameters in set
            if len(params) > 1:
                params = params[0]
            while(len(params) > 0 and loop_date_from <= date_to):
                # add tax deduction once per month
                data[employee.id] += params.tax_deduction_amount or 0
                # step: move to next month and check if parameters are still valid
                if month == 12:
                    year += 1
                    month = 0
                month += 1
                loop_date_from = loop_date_from.replace(month=month, year=year)
                # change parameters if the previous has expired
                if params.date_to and params.date_to <= loop_date_from:
                    params = parameters.filtered(are_parameters_valid(employee, loop_date_from))
        return data
