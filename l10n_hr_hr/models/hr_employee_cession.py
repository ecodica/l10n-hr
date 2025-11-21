from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class EmployeeCession(models.Model):
    _name = "hr.employee.cession"
    _description = "Cession"
    _order = "employee_id, date_from"

    employee_id = fields.Many2one('hr.employee', required=True)
    name = fields.Char(size=256)
    cession_business_entity = fields.Char(string='Cession business entity', size=128)
    note = fields.Text()
    date_from = fields.Date(string='From date')
    date_to = fields.Date(string='To date')
    probation_date_from = fields.Date(string='Probation from date')
    probation_date_to = fields.Date(string='Probation to date')
    state_id = fields.Many2one('hr.status', string='Status')
    place_of_work = fields.Char(string='Place of work', size=256)
    att_data = fields.Binary(string='Attachment file')
    att_fname = fields.Char(string='Attachment filename', size=128)

    work_place = fields.Char(string='Job Position')
    description = fields.Text(string='Jobs description')
    work_duration = fields.Integer(string='Work duratioin [Day/Week]')
    writen_agreement_att_data = fields.Binary(string='Writen Agreement attachment file')
    writen_agreement_att_fname = fields.Char(string='Written Agreement attachment filename')

    # for list view display
    probation_period = fields.Char(string="Probation period", size=64, readonly=True, compute='_probation_period')
    work_period = fields.Char(string="Work period",size=64, readonly=True, compute='_work_period')

    @api.constrains('date_from', 'date_to')
    def _check_dates(self):
        if self.filtered(lambda c: c.date_to and c.date_from and c.date_from > c.date_to):
            raise ValidationError(_('Start date must be earlier than end date.'))

    @api.constrains('probation_date_from', 'probation_date_to')
    def _check_probation_dates(self):
        if self.filtered(
            lambda c: c.probation_date_to and c.probation_date_from and c.probation_date_from > c.probation_date_to):
            raise ValidationError(_('Probation start date must be earlier than probation end date.'))

    @staticmethod
    def _period_display(date_from, date_to, date_format="%d-%m-%Y"):
        period = ""
        if date_from:
            period += date_from.strftime(date_format)
        else:
            period += "..."
        period += ' : '
        if date_to:
            period += date_to.strftime(date_format)
        else:
            period += '...'
        return period

    @api.depends('probation_date_from', 'probation_date_to')
    def _probation_period(self):
        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)])
        date_format = lang.date_format

        for record in self:
            record.probation_period = self._period_display(
                record.probation_date_from, record.probation_date_to, date_format)

    @api.depends('date_from', 'date_to')
    def _work_period(self):
        lang_code = self.env.context.get('lang') or self.env.user.lang
        lang = self.env['res.lang'].search([('code', '=', lang_code)], limit=1)
        date_format = lang.date_format

        for record in self:
            record.work_period = self._period_display(record.date_from, record.date_to, date_format)
