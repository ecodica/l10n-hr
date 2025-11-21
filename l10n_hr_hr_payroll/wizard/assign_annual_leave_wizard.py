# -*- coding: utf-8 -*-
##############################################################################

##############################################################################

from datetime import date, datetime
from odoo import models, fields, api, _


class AssignAnnualLeave(models.TransientModel):

    _name ='assign.annual.leave'
    _description = 'Dodijeli godišnji odmor za aktivne zaposlenike'

    year_id = fields.Many2one('account.fiscal.year', 'Godina')
    number_of_days = fields.Float('Broj dana', help='Količina upisana ovdje će se dodijeliti svim zaposlenicima')
    assign_leave_line_ids = fields.One2many('assign.annual.leave.lines', 'wizard_id', 'Godišnji odmori')
    department_id = fields.Many2one('hr.department', 'Odjel')

    @api.onchange('department_id')
    def onchange_department_id(self):
        if self.year_id:
            lines = self.create_leave_lines(self.year_id.id, self.department_id.id)
            self.assign_leave_line_ids = [(5, 0, 0)]
            self.assign_leave_line_ids = [(0, 0, line) for line in lines]
        else:
            self.assign_leave_line_ids = [(5, 0, 0)]

    @api.model
    def default_get(self, fields):
        """
        Default is current year because we assume leaves are assigned in january.
        """
        result = super().default_get(fields)
        year_obj = self.env['account.fiscal.year']
        today_year = datetime.today().year
        year = year_obj.search([('name', '=', today_year)], limit=1)
        if not year:
            return result
        lines = self.create_leave_lines(year.id, self.department_id.id)
        result.update({
            'year_id': year.id,
            'assign_leave_line_ids': [(0, 0, line) for line in lines],
        })
        return result

    @api.onchange('year_id')
    def onchange_year_id(self):
        """
        Year is changed so current lines are invalid -> create new ones from scratch.
        """
        lines = []
        if self.year_id:
            lines = self.create_leave_lines(self.year_id.id, self.department_id.id)
            self.assign_leave_line_ids = [(5, 0, 0)]
            self.assign_leave_line_ids = [(0, 0, line) for line in lines]
        else:
            self.assign_leave_line_ids = [(5, 0, 0)]

    @api.onchange('number_of_days')
    def onchange_number_of_days(self):
        """
        Update all lines when amount is changed.
        """
        if self.number_of_days:
            for line in self.assign_leave_line_ids:
                line.new_leave = self.number_of_days

    def create_leave_lines(self, year_id, department_id):
        """
        Return existing annual leave records for given year for each (active) employee.
        """
        emp_obj = self.env['hr.employee']
        leave_year_obj = self.env['info3.hr.employee.annual.leave.year']
        leave_lines = []
        if not year_id and not department_id: #  in case False is selected
            return leave_lines
        domain = [('category_ids.name', '=', 'Zaposlenik')]
        if department_id:
            domain.append(('department_id.id', '=', department_id))
        emp_ids = emp_obj.search(domain)
        for emp in emp_ids:
            leave_line = {
                'employee_id': emp.id,
                'old_leave': 0,
                'new_leave': 0,
                'leave_year_id': False,
            }
            leave_year_ids = leave_year_obj.search([('employee_id', '=', emp.id), ('year', '=', year_id)])
            if leave_year_ids:
                leave_year = leave_year_ids[0]
                leave_line['old_leave'] = leave_year.old_leave
                leave_line['new_leave'] = leave_year.leave
                leave_line['leave_year_id'] = leave_year.id
            leave_lines.append(leave_line)
        return leave_lines

    def assign_annual_leave(self):
        """
        Create or edit annual leave records.
        """
        leave_year_obj = self.env['info3.hr.employee.annual.leave.year']
        for line in self.assign_leave_line_ids:
            data = {
                'employee_id': line.employee_id.id,
                'year': self.year_id.id,
                'old_leave': line.old_leave,
                'leave': line.new_leave,
            }
            if line.leave_year_id:
                line.leave_year_id.write(data)
            else:
                leave_year_obj.create(data)
        return True

class AssignAnnualLeaveLines(models.TransientModel):
    _name ='assign.annual.leave.lines'
    _description = 'Stavka zaposlenika za formu za dodjelu godišnjeg odmora'

    wizard_id = fields.Many2one('assign.annual.leave','Wizard id')
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik')
    old_leave = fields.Float('Stari godišnji')
    new_leave = fields.Float('Novi godišnji')
    leave_year_id = fields.Many2one('info3.hr.employee.annual.leave.year', 'Godišnji odmor po godina')
    department_id = fields.Many2one(related='employee_id.department_id')
