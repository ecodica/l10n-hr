from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeDisability(models.Model):
    _name = "hr.employee.disability"
    _description = "Disability"
    _order = "employee_id, date_from"

    employee_id = fields.Many2one('hr.employee', required=True)
    disability_type_id = fields.Many2one('hr.disability.type', string='Disability type', required=True)
    name = fields.Char(size=256, required=True)
    percentage = fields.Float(digits=(1, 3))
    date_from = fields.Date(string='From date')
    date_to = fields.Date(string='To date')
    state_id = fields.Many2one('hr.status', string='Status', required=True)
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('Start date must be earlier than end date.'))
