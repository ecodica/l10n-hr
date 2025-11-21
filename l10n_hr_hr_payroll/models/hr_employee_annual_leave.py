# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class Info3HrEmployeeAnnualLeaveYear(models.Model):
    """
    This class is used as an overview of yearly annual leave for employee.
    System user and payroll officer are given read access so they are able to open employee form, but are not allowed to edit records.
    Payroll manager is given all access rights.
    The tab on employee form view is visible to payroll officer.
    Records can be created manually or using assign annual leave wizard.
    """
    _name = 'info3.hr.employee.annual.leave.year'
    _description = 'Godišnji odmor zaposlenika po godinama'
    _order = "year desc"
    _inherit='mail.thread'

    year = fields.Many2one('account.fiscal.year', 'Godina', required = True, tracking=True)
    old_leave = fields.Float('Stari godišnji', tracking=True)
    leave = fields.Float('Godišnji', tracking=True)
    total_leave = fields.Float('Ukupno', compute='_get_total_leave', help="Zbroj godišnjeg i starog godišnjeg", tracking=True)
    used_leave = fields.Float('Iskorišteno godišnjeg', help="Zbroj iskorištenog godišnjeg po mjesecima u ovoj godini", tracking=True)
    used_leave_qty = fields.Float('Iskorišteno', compute='_get_used_leave_qty', help="Zbroj iskorištenog godišnjeg po mjesecima u ovoj godini", tracking=True)
    remaining_leave = fields.Float('Preostalo', compute='_get_remaining_leave', tracking=True)
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', required = True)
    write_time = fields.Datetime('Posljednja promjena', compute='_get_write_data')
    write_user = fields.Many2one('res.users', 'Korisnik', compute='_get_write_data')
    write_date = fields.Datetime('Datum promjene', readonly=True)
    write_uid = fields.Many2one('res.users', 'Zadnje promjenjeno od korisnika', readonly=True)
    create_date = fields.Datetime('Kreirano', readonly=True)
    create_uid = fields.Many2one('res.users', 'Kreirao', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Odjel')


    @api.depends('employee_id', 'year')
    def _compute_display_name(self):
        for leave in self:
            leave.display_name = f"{leave.employee_id.name} - {leave.year.name}"

    @api.depends('used_leave')
    def _get_used_leave_qty(self):
        """
        Copy value from used_leave to used_leave_qty.
        Used to enable changes to used_leave on form.
        """
        for leave in self:
            leave.used_leave_qty = leave.used_leave

    @api.depends('used_leave', 'total_leave')
    def _get_remaining_leave(self):
        for leave in self:
            leave.remaining_leave = leave.total_leave - leave.used_leave

    @api.depends('write_date', 'create_date')
    def _get_write_data(self):
        for leave in self:
            if leave.write_date == leave.create_date:
                leave.write_time = ''
                leave.write_user = False
            else:
                leave.write_time = leave.write_date
                leave.write_user = leave.write_uid.id

    @api.depends('old_leave', 'leave')
    def _get_total_leave(self):
        for leave in self:
            leave.total_leave = leave.old_leave + leave.leave

    #override unlink if the employee has leave loged in periodic(monthly) table
    def unlink(self):
        for leave_year in self:
            leave_periodically = self.env['info3.hr.employee.annual.leave.periodically'].search([('employee_id','=',leave_year.employee_id.id), ('period.fiscal_year.id', '=', leave_year.year.id)])        
            if len(leave_periodically) > 0:
                raise ValidationError(_('Godišnji odmor za godinu mora biti unesen prije unosa po mjesecima. Godina:\n  %s ') % leave_year.year.name)  
        return super(Info3HrEmployeeAnnualLeaveYear, self).unlink()

class Info3HrEmployeeAnnualLeavePeriodically(models.Model):
    """
    This class is used as an overview of monthly annual leave for employee.
    System user and payroll officer are given read access so they are able to open employee form, but are not allowed to edit records.
    Payroll manager is given all access rights.
    The tab on employee form view is visible to payroll officer.
    Records are created when annual leave is calculated on payslip, but can be added and edited manually as well.
    """
    _name = 'info3.hr.employee.annual.leave.periodically'
    _description = 'Monthly annual leave for employee'
    _order = "period desc"
    _inherit='mail.thread'

    period = fields.Many2one('date.range', 'Period', required = True, tracking=True)
    used_leave = fields.Float('Iskorišteno godišnjeg', tracking=True)
    employee_id = fields.Many2one('hr.employee', 'Zaposlenik', required = True, ondelete='cascade')
    slip_id = fields.Many2one('hr.payslip','Isplatni listić', readonly = True, ondelete='cascade', tracking=True)
    payslip_run_id = fields.Many2one(related='slip_id.payslip_run_id', string='Obračun plaće', readonly = True, tracking=True)
    write_time =  fields.Datetime('Posljednja promjena', compute='_get_write_data')
    write_user = fields.Many2one('res.users', 'Korisnik', compute='_get_write_data')
    write_date =  fields.Datetime('Datum promjene', readonly=True)
    write_uid = fields.Many2one('res.users', 'Zadnje promjenjeno od korisnika', readonly=True)
    create_date =  fields.Datetime('Kreirano', readonly=True)
    create_uid = fields.Many2one('res.users', 'Kreirao', readonly=True)
    department_id = fields.Many2one(related='employee_id.department_id', store=True, string='Odjel')

    def _compute_display_name(self):
        for leave in self:
            leave.display_name = f"{leave.employee_id.name} - {leave.period.name}"

    @api.depends('write_date', 'create_date')
    def _get_write_data(self):
        for leave in self:
            if leave.write_date == leave.create_date:
                leave.write_time = ''
                leave.write_user = False
            else:
                leave.write_time = leave.write_date
                leave.write_user = leave.write_uid.id

    def write(self, vals):
        """ Update yearly leave when monthly leave is changed from monthly leave view (and not employee view).
        For changes on employee form view an onchange method is used.
        """
        res = super().write(vals)
        for employee in self.mapped('employee_id'):
            employee.update_used_leave_by_year()
        return res
