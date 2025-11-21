# -*- coding: utf-8 -*-
##############################################################################

##############################################################################

from odoo import api, fields, models
from datetime import datetime,date
from dateutil.relativedelta import relativedelta
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT
import calendar

class TimesheetReportWizard(models.TransientModel):

    _name ='timesheet.report.wizard'
    _description = 'Timesheet report wizard'


    
    category_ids = fields.Many2many('hr.employee.category', string='Employee tags',
        help='If entered, preselects employees with given tags')
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    print_contract_area = fields.Selection([('employee','Employee'),('other','Other')], required = True, default='employee',
    help="For the selected filtering option 'Employee', time tracking records are printed for workers from the category of employees based on the contract area 'Labor contracts' (where fixed-term/indefinite employment contracts are classified...) defined on the contract."
        "For the selected filtering option 'Other', time tracking records are printed for workers from the category of physical persons based on contract areas that do not belong to the Labor law contracts area (where students, apprentices, professional training... are classified) defined on the contract are classified."
        "Employees are displayed in the list based on the Contract Area related to the last active contract."
        "If records are printed for a past period in which the worker belonged to a different category, it is necessary to change the record filter to the category for which the worker had a contract in the period for which the report is being printed.")
    

    @api.model
    def default_get(self, fields):
        # show data based on filters in info3_timeshhet_line_quickadd_widget
        # employee entered -> only this employee
        # department entered -> list all employees from department
        # neither employee nor department entered -> empty list
        #   - instead of loading all employees, we allow the user to choose filters first
        #       - this case is specially important because loading all employees would mean that the user
        #         needs to remove them one by one first if they want to use filters
        #   - if no filters are used, all employees are printed anyway
        res = super().default_get(fields)
        print_contract_area = res.get('print_contract_area')
        result = self.get_employees(print_contract_area, True)
        res.update(result)
        return res


    @api.onchange('print_contract_area')
    def onchange_print_contract_area(self):
        result = self.get_employees(self.print_contract_area,False)
        self.employee_ids = result

    def get_employees(self,print_contract_area,default_get):    
        data = self._context.copy()
        department_id = data.get('department')
        employee = data.get('employee')
        employees = data.get('employees')
        current_filter = data.get('current_filter')
        active_filter = data.get('active_filter')
        additional_emps = data.get('aditional_emps')
        contract_filter = print_contract_area
        month = data['month']
        year = data['year']
        contract_date = date.today()
        if year and month:
            contract_date = date(int(year), int(month), 1)
        first_day = date(contract_date.year, contract_date.month, 1)
        last_day_num = calendar.monthrange(contract_date.year, contract_date.month)[1]
        last_day = date(contract_date.year, contract_date.month, last_day_num)
        contract_area_type_labor_contracts = self.env.ref('l10n_hr_hr.hr_contract_area_type_2')
        emp_list=[]
        if current_filter == 'has_dep_records':
            employees.clear()
            for each in additional_emps:
                employees.append(each)
        elif current_filter == 'current_and_has_records':
            for each in additional_emps:
                employees.append(each)
        domain = []
        if employee:
            domain.append(['id','=', employee])
            emp_list = [employee]
        elif department_id:
            if active_filter == 'inactive':
                emp_list = [emp['id'] for emp in employees if not emp['active']== True]
            elif active_filter == 'active':
                emp_list = [emp['id'] for emp in employees if emp['active']== True]
            elif active_filter == 'active_and_inactive':
                emp_list = [emp['id'] for emp in employees]
            domain.append(['id','in', emp_list])

        emp_ids = []
        for emp in emp_list:
            consecutive_contracts = self.env['hr.employee'].browse(emp).get_consecutive_contracts(last_day)
            contracts = [c for c in consecutive_contracts if (c.date_end == False or c.date_end >= first_day) and c.date_start <= last_day]

            if contract_filter == 'other':
                emp_ids.append(emp) if contracts and contracts[0].area != contract_area_type_labor_contracts else False
            elif contract_filter =='employee':
                emp_ids.append(emp) if contracts and contracts[0].area == contract_area_type_labor_contracts else False

        if default_get != False:
            res ={
                'print_contract_area' : contract_filter,
                'employee_ids' :  [(6, 0, self.env['hr.employee'].with_context(active_test=False).search([('id','in', emp_ids)]).ids)]
                }
            return res
        res = [(6, 0, self.env['hr.employee'].with_context(active_test=False).search([('id','in', emp_ids)]).ids)]
        return res

    @api.onchange('category_ids')
    def onchange_categories(self):
        # using context to prevent clearing employee filter on init form load
        # wizard is called using buttons on info3.timesheet form -> initially we want to show the data they send
        # after that we allow the categories helper to override:
        #   -> initially it is empty
        #   -> when entered we list only employees in entered categories
        #   -> when cleared we clear employee list
        if self._context.get('hr_timesheet_skip_onchange_category'):
            return
        if not self.category_ids:
            self.employee_ids = []
        else:
            self.employee_ids = self.env['hr.employee'].search([('category_ids', 'in', self.category_ids.ids)])

    def print_report(self):
        data = self._context.copy()
        data.update({
            'employee_ids': self.employee_ids.ids or self.env['hr.employee'].search([]).ids,
            'print_contract_area': self.print_contract_area,
        })
        return {
            'data': data,
            'type': 'ir.actions.report',
            'report_name': data.get('report_name'),
            'model': 'hr.employee',
            'report_type': "qweb-pdf",
        }
