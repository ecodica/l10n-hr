from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeExperience(models.Model):
    _name = "hr.employee.experience"
    _description = "Experience"
    _order = "employee_id, date_from"

    name = fields.Char(size=256, required=True)
    experience_type_id = fields.Many2one('hr.experience.type', string='Experience type', required=True)
    employee_id = fields.Many2one('hr.employee', required=True)
    note = fields.Text()
    date_from = fields.Date(string='From date')
    date_to = fields.Date(string='To date')
    issuing_partner = fields.Char(string='Issuing partner', size=128)
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)
    state_id = fields.Many2one('hr.status', string='Status')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from > c.date_to):
            raise ValidationError(_('Start date must be earlier than end date.'))
