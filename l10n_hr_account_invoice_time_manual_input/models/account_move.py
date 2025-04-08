from pytz import timezone, UTC
from odoo import api, models, fields


class AccountMove(models.Model):
    """Extend to change name generation"""
    _inherit = "account.move"

    l10n_hr_invoice_time_float = fields.Float(
        string="Croatia - Invoice Time", compute='_compute_l10n_hr_invoice_time_float', inverse='_inverse_l10n_hr_invoice_time_float')

    @api.depends('l10n_hr_invoice_time')
    def _compute_l10n_hr_invoice_time_float(self):
        for move in self:
            l10n_hr_invoice_time = move.l10n_hr_invoice_time or fields.Datetime.now()
            # Convert UTC datetime to user's local time using context
            dt_local = fields.Datetime.context_timestamp(move, l10n_hr_invoice_time)
            move.l10n_hr_invoice_time_float = dt_local.hour + dt_local.minute / 60.0

    @api.onchange('invoice_date', 'l10n_hr_invoice_time_float')
    def _inverse_l10n_hr_invoice_time_float(self):
        for move in self:
            min_time = 0.0
            max_time = 23 + (59 / 60)
            if move.l10n_hr_invoice_time_float < min_time:
                move.l10n_hr_invoice_time_float = 0.0
            if move.l10n_hr_invoice_time_float > max_time:
                move.l10n_hr_invoice_time_float = max_time

            l10n_hr_invoice_time = move.l10n_hr_invoice_time or fields.Datetime.now()
            # Convert UTC datetime to local time using context
            dt_local = fields.Datetime.context_timestamp(move, l10n_hr_invoice_time)
            # Modify time part based on float value
            hours = int(move.l10n_hr_invoice_time_float)
            minutes = int((move.l10n_hr_invoice_time_float - hours) * 60)
            new_local = dt_local.replace(hour=hours, minute=minutes, second=0, microsecond=0, tzinfo=None)

            # Sync l10n_hr_invoice_time with invoice_dates
            if move.invoice_date:
                new_local = new_local.replace(
                    day=move.invoice_date.day, month=move.invoice_date.month, year=move.invoice_date.year)

            # Convert back to UTC (Odoo stores datetime in UTC)
            move.l10n_hr_invoice_time = fields.Datetime.to_string(
                timezone(self.env.user.tz or 'UTC').localize(new_local).astimezone(UTC))
