from odoo import models, fields


class EmployeeEducation(models.Model):
    _name = "hr.employee.education"
    _description = 'Employee education'

    # translate Education Degree -> Education Type
    education_type_id = fields.Many2one('hr.education.type', string='Education Type', ondelete='restrict')
    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    date_from = fields.Date(string='Date from')
    date_to = fields.Date(string='Date to')
    vocation = fields.Char(size=200)
    attachment = fields.Binary(attachment=True)
    attach_file_name = fields.Char(string='Attachment filename', size=128)
    # steceni bodovi
    points = fields.Integer()
    # Obrazovna ustanova [new model]
    edu_institution = fields.Many2one('hr.education.institution', string="Education Institution")
