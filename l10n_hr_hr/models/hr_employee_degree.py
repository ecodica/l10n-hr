from odoo import models, fields


class EmployeeDegree(models.Model):
    _name = "hr.employee.degree"
    _description = "Employee degree"

    name = fields.Char('Employee degree', size=128)
