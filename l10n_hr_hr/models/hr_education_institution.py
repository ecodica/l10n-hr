from odoo import models, fields


class EducationInstitution(models.Model):
    _name = "hr.education.institution"
    _description = 'Education institution'

    code = fields.Char()
    name = fields.Char(required=True)
    addr_type = fields.Many2one("hr.address.type")
    street = fields.Char()
    street2 = fields.Char()
    city = fields.Many2one("res.city")
    zip = fields.Char(related='city.zipcode', readonly=False)
    country_id = fields.Many2one('res.country')
    phone = fields.Char()
    institution_description = fields.Text("Description")
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
