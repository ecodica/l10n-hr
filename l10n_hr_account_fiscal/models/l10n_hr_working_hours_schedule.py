from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import UserError

from .l10n_hr_business_working_hours import DAYS_OF_WEEK

MAX_SCHEDULE_DAYS = 366


class L10nHrWorkingHoursSchedule(models.TransientModel):
    """Master model answering a single question: what are the working hours on a
    given date for a given business premise?

    It does not store working hours itself - those live on
    ``l10n_hr.business.working.hours`` per premise. It resolves them for a date
    range (regulars by day of week + validity, exceptions overriding a single
    date) and materializes one ``line`` per premise/date/shift, so the effective
    schedule can be read, filtered and grouped like any other list.
    """
    _name = "l10n_hr.working.hours.schedule"
    _description = "L10n HR working hours schedule (per premise, per date)"

    date_from = fields.Date(string='From', required=True, default=fields.Date.context_today)
    date_to = fields.Date(string='To', required=True, default=fields.Date.context_today)
    business_premise_ids = fields.Many2many(
        comodel_name='l10n_hr.business.premise',
        string='Business Premises',
        help="Leave empty to cover every business premise of the current company.",
    )
    line_ids = fields.One2many(
        comodel_name='l10n_hr.working.hours.schedule.line',
        inverse_name='schedule_id',
        string='Schedule',
        readonly=True,
    )

    @api.onchange('date_from')
    def _onchange_date_from(self):
        if self.date_from and (not self.date_to or self.date_to < self.date_from):
            self.date_to = self.date_from

    def _premises(self):
        self.ensure_one()
        if self.business_premise_ids:
            return self.business_premise_ids
        return self.env['l10n_hr.business.premise'].search(
            [('company_id', '=', self.env.company.id)])

    def action_compute(self):
        """(Re)build the schedule lines for the selected range and premises."""
        self.ensure_one()
        if self.date_to < self.date_from:
            raise UserError(_('The end date cannot be before the start date.'))
        if (self.date_to - self.date_from).days > MAX_SCHEDULE_DAYS:
            raise UserError(_('The schedule range is limited to one year at a time.'))
        self.line_ids.unlink()
        self.env['l10n_hr.working.hours.schedule.line'].create(self._collect_lines())
        return {
            'type': 'ir.actions.act_window',
            'name': _('Working Hours Schedule'),
            'res_model': self._name,
            'res_id': self.id,
            'view_mode': 'form',
            'target': 'new',
        }

    def _collect_lines(self):
        self.ensure_one()
        vals_list = []
        for premise in self._premises():
            day = self.date_from
            while day <= self.date_to:
                hours = premise.get_working_hours_for_date(day)
                if hours:
                    for line in hours:
                        vals_list.append({
                            'schedule_id': self.id,
                            'business_premise_id': premise.id,
                            'date': day,
                            'shift_type': line.type,
                            'split_shift': line.split_shift,
                            'time_from': line.time_from,
                            'time_to': line.time_to,
                            'source_id': line.id,
                        })
                else:
                    vals_list.append({
                        'schedule_id': self.id,
                        'business_premise_id': premise.id,
                        'date': day,
                        'closed': True,
                    })
                day += timedelta(days=1)
        return vals_list


class L10nHrWorkingHoursScheduleLine(models.TransientModel):
    _name = "l10n_hr.working.hours.schedule.line"
    _description = "L10n HR working hours schedule line"
    _order = 'business_premise_id, date, split_shift, time_from'

    schedule_id = fields.Many2one(
        comodel_name='l10n_hr.working.hours.schedule',
        string='Schedule',
        required=True,
        ondelete='cascade',
    )
    business_premise_id = fields.Many2one(
        comodel_name='l10n_hr.business.premise',
        string='Business Premise',
        required=True,
    )
    date = fields.Date(string='Date', required=True)
    dow = fields.Selection(DAYS_OF_WEEK, string='Day of Week', compute='_compute_dow')
    shift_type = fields.Selection(
        selection=[('regular', 'Regular'), ('exception', 'Exception')],
        string='Type',
    )
    split_shift = fields.Selection(
        selection=[('1', 'First shift'), ('2', 'Second shift')],
        string='Shift',
    )
    time_from = fields.Char(string='From')
    time_to = fields.Char(string='To')
    closed = fields.Boolean(string='Closed')
    source_id = fields.Many2one(
        comodel_name='l10n_hr.business.working.hours',
        string='Working Hours',
    )

    @api.depends('date')
    def _compute_dow(self):
        for line in self:
            line.dow = line.date and str(line.date.isoweekday()) or False
