from odoo import api, fields, models

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
    display_name = fields.Char(compute='_compute_display_name')

    @api.depends('business_premise_id', 'business_premise_id.l10n_hr_name', 'type', 'dow', 'valid_from', 'valid_on')
    def _compute_display_name(self):
        type_labels = dict(self._fields['type'].selection)
        dow_labels = dict(self._fields['dow'].selection)
        for record in self:
            premise = record.business_premise_id.display_name or ''
            type_label = type_labels.get(record.type, record.type)
            dow_label = dow_labels.get(record.dow, record.dow)
            if record.type == 'exception' and record.valid_on:
                valid = fields.Date.to_string(record.valid_on)
            else:
                valid = fields.Date.to_string(record.valid_from) if record.valid_from else ''
            record.display_name = "{} - {}, {}, {} ({} - {})".format(
                premise, type_label, dow_label, valid, record.time_from, record.time_to
            )
