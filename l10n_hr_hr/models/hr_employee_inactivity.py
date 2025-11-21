from odoo import models, fields


class EmployeeInactivity(models.Model):
    _name = "hr.employee.inactivity"
    _description = 'Employee inactivity'
    _inherit = 'mail.thread'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    type_id = fields.Many2one('hr.inactivity.type', required=True)
    name = fields.Char(size=200, required=True)
    state_id = fields.Many2one('hr.status', required=True, tracking=True)
    date_from = fields.Date(string='Date from', required=True)
    date_to = fields.Date(string='Date to')
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)
    note = fields.Char()
