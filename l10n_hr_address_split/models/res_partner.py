# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import api, models

from ..tools import hr_street_split


class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends('street')
    def _compute_street_data(self):
        """Split street into street_name/street_number/street_number2.

        Overrides base_address_extended to use the improved Odoo 19 splitter
        instead of the Odoo 17 one, which misses the house number on several
        common address shapes (leading number, trailing whitespace, comma
        separators). See tools.street_split.hr_street_split.
        """
        for partner in self:
            partner.update(hr_street_split(partner.street))
