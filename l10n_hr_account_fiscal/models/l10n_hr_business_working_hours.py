from odoo import fields, models

DOW_CHOICES = ('Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday', 'Public holiday')
DAYS_OF_WEEK = [(str(index), day) for index, day in enumerate(DOW_CHOICES, start=1)]


class L10nHrBusinessWorkingHours(models.Model):
    _name = "l10n_hr.business.working.hours"
    _description = "L10n HR business working hours"
    _order = 'business_premise_id, type, valid_from ASC, dow ASC, split_shift ASC'

    business_premise_id = fields.Many2one('l10n_hr.business.premise', string='Business Premise', required=True,
                                          readonly=True)
    type = fields.Selection([
        ('regular', 'Regular'),
        ('exception', 'Exception'),
    ], string='Type', required=True, default='regular')
    description = fields.Char(string='Description', required=False)
    dow = fields.Selection(DAYS_OF_WEEK, string='Day of Week', required=True, default='1')
    valid_from = fields.Date(string='Valid from', required=False)
    valid_on = fields.Date(string='Valid on')
    time_from = fields.Char(string='Time from', required=True)
    time_to = fields.Char(string='Time to', required=True)
    split_shift = fields.Selection([('1', 'First shift'), ('2', 'Second shift')], string='Split shift')
    to_remove = fields.Boolean('To Remove', required=False)
    to_register = fields.Boolean('To Register', required=False)
