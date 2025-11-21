from odoo import fields, models


class ContractInterruptionReasonType(models.Model):
    _name = 'hr.contract.interruption.reason.type'
    _description = "Contract interruption reason type"
    _order = 'code'

    code = fields.Char(size=7)
    name = fields.Char(size=256, required=True)
    description = fields.Char(size=512)
    company_id = fields.Many2one('res.company', readonly=True, required=True,
        default=lambda self: self.env.user.company_id.id)
