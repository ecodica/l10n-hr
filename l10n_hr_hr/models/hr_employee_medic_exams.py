from odoo import fields, models, _


class EmployeeMedicExam(models.Model):
    _name = "hr.employee.medic_exam"
    _description = "Medical exam"
    _inherit = "mail.thread"
    _rec_name = 'employee_id'

    employee_id = fields.Many2one('hr.employee', required=True)
    medical_exam_type_id = fields.Many2one('hr.medical.exam.type', 'Medical exam type', ondelete = 'restrict')
    name = fields.Char(size=50)
    date = fields.Date()
    start_date = fields.Date(string="Start date", required=True)
    end_date = fields.Date(string="End date", required=True, tracking=True)
    medical_institution = fields.Char(string='Medical institution', size=512)
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)
    note = fields.Text()
