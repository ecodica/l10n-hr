from odoo import models, fields, api, _


class TransportationWork(models.Model):

    _name = "hr.transportation.work"
    _description = "Transportation from and to work"

    employee_id = fields.Many2one('hr.employee', required=True, ondelete='cascade')
    transport_type_id = fields.Many2one('hr.transportation.type', string='Transportation type', required=True)
    carrier_id = fields.Many2one('hr.transportation.carrier')
    amount = fields.Float(required=True)
    percentage = fields.Float(string="Percentage %", required=True)
    overall = fields.Float(store=True)
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)

    @api.onchange('percentage', 'amount', 'overall')
    def _onchange_stuff(self):
        self.overall = self.amount * (self.percentage / 100)
