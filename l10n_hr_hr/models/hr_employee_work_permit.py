from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeWorkPermit(models.Model):
    _name = "hr.employee.work.permit"
    _description = "Work permit"
    _inherit = 'mail.thread'
    _order = "employee_id, estimated_length_of_stay_date_from"

    employee_id = fields.Many2one('hr.employee', required=True)
    number = fields.Char(size=64)
    start_date = fields.Date(string='Start date', required=True)
    expiration_date = fields.Date(string='Expiration date', required=True, tracking=True)
    issuing_authority = fields.Char(string='Issuing authority', size=512)
    work_permit_number = fields.Char(string='Work permit number', size=64)
    permit_type_id = fields.Many2one('hr.permit.type', 'Work permit type')
    residence_permit_att_data = fields.Binary(string='Residence permit attachment file')
    residence_permit_att_filename = fields.Char(string='Residence permit attachment filename', size=128)

    residence_and_work_permit_att_data = fields.Binary(string='Residence and work permit attachment file')
    residence_and_work_permit_att_filename = fields.Char(
        string='Residence and work permit attachment filename', size=128)

    estimated_length_of_stay_date_from = fields.Date(string='Estimated length of stay date from')
    estimated_length_of_stay_date_to = fields.Date(string='Estimated length of stay date to')
    att_data = fields.Binary(string='Attachment file')
    att_filename = fields.Char(string='Attachment filename', size=128)

    estimated_length_of_stay_date_period = fields.Char(
        size=64, readonly=True, store=False, compute='_estimated_length_of_stay_to_str')

    @api.constrains('estimated_length_of_stay_date_from', 'estimated_length_of_stay_date_to')
    def _check_dates(self):
        if self.filtered(lambda c: c.estimated_length_of_stay_date_to and c.estimated_length_of_stay_date_from and c.estimated_length_of_stay_date_from > c.estimated_length_of_stay_date_to):
            raise ValidationError(_('Estimated length of stay start date must be earlier than estimated length of stay end date.'))

    def _estimated_length_of_stay_to_str(self):
        for permit in self:
            date_format = self.env['res.lang'].search(
                [('code', '=', (self.env.context.get('lang') or self.env.user.lang))]
            ).date_format

            if date_format is None:
                date_format = "%d-%m-%Y"

            str_period = ""
            if permit.estimated_length_of_stay_date_from:
                str_period += permit.estimated_length_of_stay_date_from.strftime(date_format)
            else:
                str_period += "..."
            str_period += ' : '
            if permit.estimated_length_of_stay_date_to:
                str_period += permit.estimated_length_of_stay_date_to.strftime(date_format)
            else:
                str_period += "..."
            permit.estimated_length_of_stay_date_period=str_period
