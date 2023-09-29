# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import _, api, fields, models


class AccountAssetProfile(models.Model):
    _inherit = "account.asset.profile"

    @api.model
    def _selection_method_period_start(self):
        return [
            ('current', 'Current'),
            ('next', 'Next')
        ]

    method_period_start = fields.Selection(selection=lambda self: self._selection_method_period_start(),
                                           string='Period Start Method',
                                           default='next',
                                           required=1)
