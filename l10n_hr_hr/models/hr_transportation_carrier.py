from stdnum.hr import oib
from odoo import models, fields, api, _
from odoo.exceptions import ValidationError


class TransportationCarrier(models.Model):
    _name = "hr.transportation.carrier"
    _description = "Company which employee uses to go to work or from work."

    code = fields.Char(size=10)
    name = fields.Char(size=50, required=True)
    oib = fields.Char(string='OIB', size=11, required=True)
    description = fields.Text()
    company_id = fields.Many2one("res.company", readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)

    _sql_constraints = [
        ('unique_oib', 'unique(oib, company_id)', "You can not have two carriers with the same OIB and company.")
    ]

    @api.constrains("oib")
    def check_employee_oib_unique(self):
        """Check Transportation Carrier OIB uniqueness
        - OIBs must be unique and of length == 11"""
        for record in self:
            if record.oib:
                if len(record.oib) != 11:
                    raise ValidationError(_("OIB field must be exactly 11 characters long"))
                if not record.oib.isnumeric():
                    raise ValidationError(_("OIB field must be a number"))
                if not oib.is_valid(record.oib):
                    raise ValidationError(_("Employee OIB is not valid"))
