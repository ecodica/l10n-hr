# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api

from odoo.addons.l10n_hr_pain_base.models.account_payment_order import (
    HR_PAIN_FLAVORS,
    HR_SCT_03,
    HR_SCT_09,
    HR_SCT_INST_09,
)

HR_PAYMENT_METHOD_CODES = (
    'sepa_credit_transfer_hr',
    'sepa_credit_transfer_hr09',
    'sepa_credit_transfer_hr09_inst',
)


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    pain_version = fields.Selection(selection_add=[
        (HR_SCT_03,
         'scthr:pain.001.001.03 Credit Transfer v03HR (used in Croatia)'),
        (HR_SCT_09,
         'scthr:pain.001.001.09 Credit Transfer v09HR (used in Croatia)'),
        (HR_SCT_INST_09,
         'sctinsthr:pain.001.001.09 Instant Credit Transfer v09HR '
         '(used in Croatia)'),
        ], ondelete={
            HR_SCT_03: 'set null',
            HR_SCT_09: 'set null',
            HR_SCT_INST_09: 'set null',
        })

    def get_xsd_file_path(self):
        self.ensure_one()
        painv = self.pain_version
        if painv in HR_PAIN_FLAVORS:
            path = 'l10n_hr_pain_credit_transfer/data/%s.xsd' % painv
            return path
        return super().get_xsd_file_path()

    @api.model
    def _get_payment_method_information(self):
        """Without an entry here the method is absent from a journal's
        available_payment_method_ids, so it cannot be picked in
        Journals > Outgoing Payments."""
        res = super()._get_payment_method_information()
        for code in HR_PAYMENT_METHOD_CODES:
            res[code] = {'mode': 'multi', 'domain': [('type', '=', 'bank')]}
        return res
