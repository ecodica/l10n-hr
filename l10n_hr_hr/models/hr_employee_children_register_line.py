from stdnum.hr import oib
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class EmployeeChildrenRegisterLine(models.Model):
    _name = 'hr.employee.children.register.line'
    _description = 'Children register line'
    _order = 'date_of_birth, id'
    _inherit = 'mail.thread'

    employee_id = fields.Many2one('hr.employee', ondelete='cascade')
    name = fields.Char(required=True, tracking=True)
    surname = fields.Char(tracking=True)
    oib = fields.Char(size=11, index=True, copy=False, tracking=True)
    date_of_birth = fields.Date('Date of brith', tracking=True)
    gender = fields.Selection([
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other')
    ], default="male", tracking=True)

    _sql_constraints = [
        ('unique_oib', 'unique(oib)', 'You can not have children with the same OIB.')
    ]

    @api.constrains("oib")
    def check_child_oib_valid(self):
        """Check for OIB uniqueness for hr.employee.children.register.line
        - OIBs must be unique and of length == 11
        - OIB is mandatory"""
        for record in self:
            if record.oib:
                if len(record.oib) != 11:
                    raise ValidationError(_("OIB field must be exactly 11 characters long"))
                if not record.oib.isnumeric():
                    raise ValidationError(_("OIB field must be a number"))
                if not oib.is_valid(record.oib):
                    raise ValidationError(_("Child OIB is not valid"))
