from odoo import fields, models


class CategoryType(models.Model):
    _name = "hr.category.type"
    _description = "Category type"
    _order = 'name'

    name = fields.Char(size=256, required=True)
    employee_ids = fields.Many2many('hr.employee', string='Employees')
    company_id = fields.Many2one('res.company', readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
