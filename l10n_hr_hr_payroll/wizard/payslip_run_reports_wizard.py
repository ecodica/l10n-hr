# -*- encoding: utf-8 -*-
from odoo import fields, models, api, _
from odoo.exceptions import ValidationError
from datetime import date, datetime


class PayslipRunReportsWizard(models.TransientModel):
    _name = 'payslip.run.reports.wizard'
    _description = 'Forma za ispis izvještaja obračuna plaće'
    
    _report_types = [
        ('recap', 'Rekapitulacija obračuna plaće'),
        ('emp_recap', 'Rekapitulacija po zaposleniku'),
        ('emp_average_salary', 'Prosjek plaće zaposlenika'),
        ('ip1_form', 'IP1 obrazac'),
        ('earnings', 'Popis zarada'),
        ('fees', 'Popis naknada'),
        ('suspensions', 'Obustave'),
        ('tax_cities', 'Porez po gradu'),
        ('sick_leave_company', 'Bolovanje na teret poslodavca'),
        ('sick_leave_fund', 'Bolovanje na teret HZZO-a'),
        ('injury_at_work', 'Ozljede na radu'),
        ('io1_report','IO1 obrazac')
    ]
    
    _report_types_help = u"Odabir vrste izvještaja za odabrani obračun plaća. \n"\
                         u" * Rekapitulacija obračuna plaća - izvještaj za sve zaposlenike u obračunu \n"\
                         u" * Potpisna lista - potpisna lista obračuna plaća po obračunu i poslovnoj jedinici \n"\
                         u" * Rekapitulacija naloga - lista virmanskih plaćanja  \n"\
                         u" * Lista obračuna plaće - rekapitulacija po zaposlenicima i kategorijama \n"\
                         u" * Isplatni listići plaće - isplatni listići za pojedini obračun \n"\
                         u" * Zbrojni nalog - Ispis računa za uplate \n"\
                         u" * IO1 obrazac - obrazac otpremnine i neiskorištenog godišnjeg odmora"
    
    date_from = fields.Date('Od datuma', help="Helper field to get payslip runs based on pay date.")
    date_to = fields.Date('Do datuma')
    payslip_run_ids = fields.Many2many('hr.payslip.run', 'reports_wizard_payslip_run_rel', 'wizard_id', 'run_id', 'Obračuni plaće')
    batch_id = fields.Many2one('hr.payslip.run','Obračun plaće')
    report_type = fields.Selection(_report_types, 'Vrsta izvještaja', required=True, help=_report_types_help, default='recap')
    department_id = fields.Many2one('hr.department', 'Odjel')
    employee_ids = fields.Many2many('hr.employee', 'payslip_run_reports_wizard_employee_rel', 'wizard_id', 'employee_id', 'Zaposlenici')
    
    def select_report_type(self):
        report_type = self.report_type
        if not self.payslip_run_ids:
            raise ValidationError(_('Potrebno je odabrati barem jedan obračun plaće kako bi se ispisao izvještaj.'))
        if report_type == 'recap':
            return self.print_recap()
        elif report_type == 'emp_recap':
            return self.print_employee_recap()
        elif report_type == 'emp_average_salary':
            return self.print_employee_average_salary()
        elif report_type == 'payslip':
            return self.print_payslip()
        elif report_type == 'ip1_form':
            return self.print_ip1_form()
        elif report_type == 'tax_cities':
            return self.print_tax_cities()
        elif report_type in ['fees', 'earnings', 'sick_leave_company', 'sick_leave_fund', 'injury_at_work']:
            return self.print_fees_earnings_or_sick_leave_list()
        elif report_type == 'suspensions':
            return self.print_suspensions()
        elif report_type == 'io1_report':
            return self.print_io1_report()
        else:
            pass

    def select_report_type_xlsx(self):
        report_type = self.report_type
        if not self.payslip_run_ids:
            raise ValidationError(_('Potrebno je odabrati barem jedan obračun plaće kako bi se ispisao izvještaj.'))
        if report_type == 'recap':
            return self.print_recap_xlsx()
        elif report_type == 'suspensions':
            return self.print_suspensions_xslx()
        elif report_type == 'emp_recap':
            return self.print_employee_recap_xslx()
        elif report_type == 'tax_cities':
            return self.print_tax_cities_xslx()
        elif report_type == 'payslip':
            return self.print_payslip_xlsx()
        elif report_type in ['fees', 'earnings', 'sick_leave_company', 'sick_leave_fund', 'injury_at_work']:
            return self.print_fees_earnings_or_sick_leave_list_xlsx()
        else:
            pass

    def print_recap(self):
        data = self.prepare_recap_data()
        report_id = 'l10n_hr_hr_payroll.hr_payslip_run_recap_report'
        return self.env.ref(report_id).report_action(self, data)

    def print_recap_xlsx(self):
        data = self.prepare_recap_data()
        report_id = 'l10n_hr_hr_payroll.hr_payslip_run_recap_report_xlsx'
        report = self.env.ref(report_id)
        report.sudo().report_file = _("Recap_report")
        return report.report_action(self, data=data)

    def prepare_recap_data(self):
        dep = self.department_id
        run_ids = self.payslip_run_ids
        list_ids = self.get_departments(run_ids, dep.id, [])
        return {
            'run_ids': run_ids.ids,
            'department_id': dep.id,
            'department_ids': list_ids,
        }

    def print_employee_recap(self):
        data = self._prepare_employee_recap_data()
        report_id = 'l10n_hr_hr_payroll.employee_recap_report'
        return self.env.ref(report_id).report_action(self, data)

    def print_employee_recap_xslx(self):
        data = self._prepare_employee_recap_data()
        report_id = 'l10n_hr_hr_payroll.report_employee_recap_xlsx'
        report = self.env.ref(report_id)
        report.sudo().report_file = _("Employee_recap_report")
        return report.report_action(self, data=data)

    def _prepare_employee_recap_data(self):
        run_ids = self.payslip_run_ids
        period = self.get_period()
        data = {
            'run_ids': run_ids.ids,
            'emp_ids': self.employee_ids.ids,
            'period': period,
        }
        return data

    def print_employee_average_salary(self):
        run_ids = self.payslip_run_ids
        emp_ids = self.get_employees()
        period = self.get_period()
        data = {
            'run_ids': run_ids.ids,
            'emp_ids': emp_ids.ids,
            'period': period,
        }
        report_id ='l10n_hr_hr_payroll.employee_average_salary_report'
        return self.env.ref(report_id).report_action(self, data)

    def prepare_payslip_data(self):
        batch = self.payslip_run_ids
        dep_id = self.department_id.id
        domain = [('payslip_run_id','in',batch.ids)]
        if dep_id:
            domain.append(('department_id', '=', dep_id))
        slips = self.env['hr.payslip'].search(domain)
        if not slips:
            raise ValidationError(_('No payslips to print!'))
        return slips

    def print_ip1_form(self):
        slips = self.prepare_payslip_data()
        report_id = 'l10n_hr_hr_payroll.ip1_form_report'
        return self.env.ref(report_id).report_action(slips)

    def print_fees_earnings_or_sick_leave_list(self):
        data = self.prepare_earnings_data()
        return self.env.ref('l10n_hr_hr_payroll.fees_earnings_report').report_action(self, data=data)

    def print_fees_earnings_or_sick_leave_list_xlsx(self):
        data = self.prepare_earnings_data()
        report = self.env.ref('l10n_hr_hr_payroll.hr_payslip_fees_earning_report_xlsx')
        report.sudo().report_file = self.get_report_name(self.report_type)
        return report.report_action(self, data=data)

    def print_io1_report(self):
        slips = self.prepare_payslip_data()
        report_id = 'l10n_hr_hr_payroll.io1_report'
        return self.env.ref(report_id).report_action(slips)
    
    def prepare_earnings_data(self):
        data = {}
        data['run_ids'] = self.payslip_run_ids.ids
        data['department'] = self.department_id.name
        data['department_id'] = self.department_id.id
        data['name'] = self.batch_id.name
        data['type'] = self.report_type
        return data

    def print_suspensions(self):
        data = self.prepare_suspensions_data()
        return self.env.ref('l10n_hr_hr_payroll.hr_payslip_run_suspensions_report').report_action(self, data=data)

    def print_suspensions_xslx(self):
        data = self.prepare_suspensions_data()
        report = self.env.ref('l10n_hr_hr_payroll.report_hr_payslip_run_suspensions_xlsx')
        report.sudo().report_file = _("Obustave")
        return report.report_action(self, data=data)

    def prepare_suspensions_data(self):
        dep = self.department_id
        run_ids = self.payslip_run_ids
        list_ids = self.get_departments(run_ids, dep.id, [])
        return {
            'run_ids': run_ids.ids,
            'department_id': dep.id,
            'department_ids': list_ids,
        }

    def print_tax_cities(self):
        data = self.prepare_tax_cities_data()
        report_id = 'l10n_hr_hr_payroll.tax_cities'
        return self.env.ref(report_id).report_action(self, data=data)

    def print_tax_cities_xslx(self):
        data = self.prepare_tax_cities_data()
        report_id = 'l10n_hr_hr_payroll.report_tax_city_xlsx'
        report = self.env.ref(report_id)
        report.sudo().report_file = _("Porez i prirez po gradu")
        return report.report_action(self, data)
    
    def prepare_tax_cities_data(self):
        data = {}
        data['run_ids'] = self.payslip_run_ids.ids
        data['department'] = self.department_id.name
        data['department_id'] = self.department_id.id
        data['name'] = self.batch_id.name
        return data

    @api.onchange('date_from', 'date_to')
    def onchange_period(self):
        if self.date_from and self.date_to:
            self.payslip_run_ids = self.env['hr.payslip.run'].search([('pay_date', '>=', self.date_from), ('pay_date', '<=', self.date_to)]).ids
        else:
            self.payslip_run_ids = []
      
    def get_departments(self, batch_ids, dep_id, id_list):
        """
        @batch_ids - recordset
        @dep_id - int
        @id_list - list
        """
        if not id_list:
            id_list = []
        # get all user departments from payslip_run
        if dep_id == False:
            id_list = batch_ids.mapped('slip_ids').mapped('department_id.id')
        # for given department get all children
        else:
            departments = self.env['hr.department']
            child_ids = departments.search([('parent_id', '=', dep_id)])
            if dep_id not in id_list:
                id_list.append(dep_id)
            for child_id in child_ids:
                if child_id.id not in id_list:
                    id_list.append(child_id.id)
                self.get_departments(batch_ids, child_id.id, id_list)
        return id_list
    
    def get_employees(self):
        """
        Employees selected on form or all employees if none were selected.
        """
        if len(self.employee_ids):
            return self.employee_ids 
        return self.env['hr.employee'].search(['|', ('active', '=', True), ('active', '=', False)])
    
    def get_period(self):
        if not self.date_from or not self.date_to:
            return {}
        return {
            'date_from': self.date_from,
            'date_to': self.date_to,
        }

    def get_report_name(self, report_type):
        if report_type == 'fees':
            return _("Fees_report")
        elif report_type == 'earnings':
            return _("Earnings_report")
        elif report_type == 'sick_leave_company':
            return _("Sick_leave_company_report")
        elif report_type == 'sick_leave_fund':
            return _("Sick_leave_fund_report")
        else:
            return _("Injury_at_work_report")
