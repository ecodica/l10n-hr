from odoo import fields, models


class EmployeeCessionOverseas(models.Model):
    _name = "hr.employee.cession.overseas"
    _description = "Cession Overseas"
    _inherit = "hr.employee.cession"

    work_license_id = fields.Char()  # Broj radne dozvole
    visa_id = fields.Char()  # Broj vize
    visa_expiration_date = fields.Date()  # Datum isteka vize
    visa_issue_authority = fields.Char(string='Visa issuing authority')  # Tijelo koje je izdalo vizu
    extra_att_data = fields.Binary(string='Attachment file - Accessories')  # Datoteka privitka - Dodaci
    extra_att_fname = fields.Char(string='Attachment filename - Accessories')
