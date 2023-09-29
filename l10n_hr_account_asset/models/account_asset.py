# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAssetAsset(models.Model):
    _inherit = "account.asset"

    method_period_start = fields.Selection(
        selection=lambda self: self.env['account.asset.profile']._selection_method_period_start(),
        compute='_compute_method_period_start',
        string='Period Start Method',
        store=1)

    @api.model
    def _method_period_to_relativedelta_keyword_mapper(self, kw):
        mapper = dict(year='years', month='months', day='days')
        if kw not in mapper:
            raise UserError('Keyword %s not allowed to use for calculation!' % kw)
        return mapper.get(kw)

    @api.depends("profile_id")
    def _compute_method_period_start(self):
        for asset in self:
            asset.method_period_start = asset.profile_id.method_period_start

    def _get_depreciation_start_date(self, fy):
        start_date = super()._get_depreciation_start_date(fy)
        if self.method_period_start == 'next':
            add = {self._method_period_to_relativedelta_keyword_mapper(self.method_period): 1}
            start_date = fields.Date.start_of(fields.Date.add(start_date, **add), self.method_period)
        return start_date

    def _compute_depreciation_amount_per_fiscal_year(
            self, table, line_dates, depreciation_start_date, depreciation_stop_date
    ):
        if self.method_period_start == 'next' and self.method_time == 'year' and self.prorata:
            self.ensure_one()
            currency = self.company_id.currency_id
            fy_residual_amount = self.depreciation_base
            i_max = len(table) - 1
            asset_sign = self.depreciation_base >= 0 and 1 or -1
            day_amount = 0.0
            if self.days_calc:
                days = (depreciation_stop_date - depreciation_start_date).days + 1
                day_amount = self.depreciation_base / days

            for i, entry in enumerate(table):
                if self.method_time == "year":
                    year_amount = self._compute_year_amount(
                        fy_residual_amount,
                        depreciation_start_date,
                        depreciation_stop_date,
                        entry,
                    )
                    if self.method_period == "year":
                        period_amount = year_amount
                    elif self.method_period == "quarter":
                        period_amount = year_amount / 4
                    elif self.method_period == "month":
                        period_amount = year_amount / 12
                    if i == i_max:
                        if self.method in ["linear-limit", "degr-limit"]:
                            fy_amount = fy_residual_amount - self.salvage_value
                        else:
                            fy_amount = fy_residual_amount
                    else:
                        firstyear = i == 0 and True or False
                        fy_factor = self._get_fy_duration_factor(entry, firstyear)
                        fy_amount = year_amount * fy_factor
                    if (
                            currency.compare_amounts(
                                asset_sign * (fy_amount - fy_residual_amount), 0
                            )
                            > 0
                    ):
                        fy_amount = fy_residual_amount
                    period_amount = currency.round(period_amount)
                    fy_amount = currency.round(fy_amount)
                else:
                    fy_amount = False
                    if self.method_time == "number":
                        number = self.method_number
                    else:
                        number = len(line_dates)
                    period_amount = currency.round(self.depreciation_base / number)
                entry.update(
                    {
                        "period_amount": period_amount,
                        "fy_amount": fy_amount,
                        "day_amount": day_amount,
                    }
                )
                if self.method_time == "year":
                    fy_residual_amount -= fy_amount
                    if currency.is_zero(fy_residual_amount):
                        break
                if self.method_period_start == 'next' and self.method_time == 'year' and self.prorata:
                    entry.update(fy_amount=entry['period_amount'])
            i_max = i
            table = table[: i_max + 1]
            return table
        else:
            return super()._compute_depreciation_amount_per_fiscal_year(table, line_dates,
                                                                        depreciation_start_date, depreciation_stop_date)
