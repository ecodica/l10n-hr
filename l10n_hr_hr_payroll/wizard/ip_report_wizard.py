# -*- encoding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class IpReportWizardEmployeeLine(models.TransientModel):
    _name = 'ip.report.wizard.employee.line'
    _description = 'Stavka zaposlenika za ispis IP obrasca'
    
    wizard_id = fields.Many2one('ip.report.wizard', 'Čarobnjak')
    print_ip = fields.Boolean('Ispis')
    # employee_id is used to show as readonly on form, emp_id is the "actual" field
    # if we only use readonly field, then it can not be read from wizard for some reason so this is a workaround
    employee_id = fields.Many2one(related='emp_id', string='Zaposlenik')
    emp_id = fields.Many2one('hr.employee', 'Emp')


class IpReportWizard(models.TransientModel):
    _name = 'ip.report.wizard'
    _description = 'Forma za ispis IP obrasca'
    
    ip_form_employee_ids = fields.One2many('ip.report.wizard.employee.line', 'wizard_id', 'Zaposlenici')
    year_id = fields.Many2one('account.fiscal.year', 'Godina')
    date = fields.Date('Datum ispisa', default=fields.Date.today())
    select_all = fields.Boolean('Označi sve')

    @api.onchange('select_all')
    def onchange_select_all(self):
        select_all = self.select_all
        for line in self.ip_form_employee_ids:
            line.print_ip = select_all

    def employees_with_payment_in_year(self, year_id, select_all):
        """
        Return list of employees with payment in selected year.
        """
        emp_obj = self.env['hr.employee']
        emp_list = []
        # default returns only active employees, we need inactive ones as well
        domain = ['|', ('active', '=', True), ('active', '=', False)]
        emp_ids = emp_obj.search(domain)
        for emp in emp_ids:
            has_payment_in_year = emp.has_payment_in_year(year_id)
            if emp.is_employee and has_payment_in_year:
                emp_list.append({'emp_id': emp.id, 'print_ip': select_all})
        return emp_list

    @api.onchange('year_id')
    def onchange_year_id(self):
        emp_list = self.employees_with_payment_in_year(self.year_id.id, self.select_all)
        new_records = [(0, 0, emp) for emp in emp_list]
        self.update({
            'ip_form_employee_ids': new_records
        })
    
    def print_ip_form(self):
        year = self.year_id.name
        date = self.date
        ip_form_emp_ids = self.ip_form_employee_ids
        emp_ids = [emp_line.emp_id.id for emp_line in ip_form_emp_ids if emp_line.print_ip]
        if not emp_ids:
            raise ValidationError(_('Nije odabran nijedan zaposlenik'))
        data = {}
        data['employee_ids'] = emp_ids
        data['year'] = year
        data['date'] = date
        return self.env.ref('l10n_hr_hr_payroll.ip_form_report').report_action(self, data=data)
