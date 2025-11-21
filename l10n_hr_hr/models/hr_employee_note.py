from odoo import models, fields, _


class EmployeeNote(models.Model):
    """This class is used to enable multiple notes per employee,
    i.e. it is meant to replace single note fields in l10n_hr_hr module."""
    _name = 'hr.employee.note'
    _description = 'Notes for employee'
    _order = 'date DESC'

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    date = fields.Date()
    note = fields.Text(required=True)
    note_data = fields.Binary('Attachment file')
    note_fname = fields.Char('Attachment filename', size=128)
