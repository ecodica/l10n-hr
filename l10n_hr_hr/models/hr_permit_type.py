from odoo import models, fields


class HrPermitType(models.Model):
    _name = 'hr.permit.type'
    _description = "Permit type register"

    name = fields.Char(required=True)
    type = fields.Selection([
        ('work_permit', 'Work Permit'),
        ('visa', 'Visa'),
        ('passport', 'Passport')
        ], string='Permit Type', required=True)
