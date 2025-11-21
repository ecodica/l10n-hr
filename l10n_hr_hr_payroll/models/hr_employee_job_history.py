from odoo import fields, models


class EmployeeJobHistory(models.Model):
    _name = 'hr.employee.job.history'
    _description = 'HR Employee Job History'
    _order = 'create_date DESC'
    _inherit='mail.thread'

    employee_id = fields.Many2one(string='Zaposlenik', comodel_name='hr.employee',tracking = True )
    department_id = fields.Many2one(string='Odjel', comodel_name='hr.department',tracking = True)
    job_id = fields.Many2one(string='Radno mjesto', comodel_name='hr.job',tracking = True)
    parent_id = fields.Many2one(string='Nadređeni', comodel_name='hr.employee',tracking = True)
    date_to = fields.Date(string='Datum do',tracking = True)

