from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class ContractSubareaType(models.Model):
    _name = 'hr.contract.subarea.type'
    _description = "Contract subarea type"
    _order = 'code'

    code = fields.Char(size=7)
    name = fields.Char(size=256, required=True)
    description = fields.Char(size=512)
    area_type_id = fields.Many2one('hr.contract.area.type', string='Contract area type', required=True)
    used_in_internship_calculation = fields.Boolean(default=True, string="Used in internship calculation")
    company_id = fields.Many2one('res.company', readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)

    @api.constrains('used_in_internship_calculation')
    def _check_contracts_internship(self):

        if not self.used_in_internship_calculation:
            return

        for contract in self.env['hr.contract'].search([('area_type', '=', self.id)]):
            try:
                contract._check_used_for_internship()
            except ValidationError:
                raise ValidationError(_('There are overlaping contracts of this Area Type.'))
