from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, MONTHLY, WEEKLY, YEARLY, rrule

class DateRangeGenerator(models.TransientModel):
    _inherit = 'date.range.generator'
    _description = 'Date Range Generator'

    # prefx is not required in out implementation
    name_prefix = fields.Char('Range name prefix', default="", required=False)
    fiscal_year = fields.Many2one(
        'account.fiscal.year',
        string="Fiscal Year",
        required=True,
        domain="[('company_id', '=', company_id)]"
    )

    unit_of_time = fields.Selection(
            default =str(YEARLY) 
    )

    def _generate_date_ranges(self, batch=False):
        """Overriding to modify name_prefix use and date_range.name.
        The usual format for our purposes is MM-YYYY (month-fiscal_year)
        """
        self.ensure_one()
        vals = rrule(freq=int(self.unit_of_time), interval=self.duration_count,
                     dtstart=self.date_start,
                     count=self.count+1)
        vals = list(vals)
        date_ranges = []
        count_digits = len(str(self.count))
        for idx, dt_start in enumerate(vals[:-1]):
            date_start = dt_start.date()
            # always remove 1 day for the date_end since range limits are inclusive
            date_end = vals[idx+1].date() - relativedelta(days=1)
            date_ranges.append({
                'name': '%s%0*d-%s' % (
                    self.name_prefix if self.name_prefix else "", count_digits, idx + 1, self.fiscal_year.name),
                'date_start': date_start,
                'date_end': date_end,
                'type_id': self.type_id.id,
                'fiscal_year': self.fiscal_year.id,
                'company_id': self.company_id.id})
        return date_ranges
