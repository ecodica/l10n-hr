from odoo import models, fields


class HrMedicalExamType(models.Model):
    _name = 'hr.medical.exam.type'
    _description = "Medical exam type register"

    name = fields.Char()
