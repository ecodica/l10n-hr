# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields


class AccountPaymentLine(models.Model):
    _inherit = 'account.payment.line'

    def _default_communication_type(self):
        return 'HR ref'

    communication_type = fields.Selection(selection_add=[('HR ref', 'HR ref')], default=_default_communication_type,
                                          ondelete={"HR ref": "cascade"})
