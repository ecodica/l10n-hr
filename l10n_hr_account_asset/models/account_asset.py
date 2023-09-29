# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, fields, models
from odoo.exceptions import UserError


class AccountAssetAsset(models.Model):
    _inherit = "account.asset"

    method_period_start = fields.Selection(selection=lambda self: self.env['account.asset.profile']._selection_method_period_start(),
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



