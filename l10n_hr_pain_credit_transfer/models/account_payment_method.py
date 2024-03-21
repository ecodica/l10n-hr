# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo import models, fields, api


class AccountPaymentMethod(models.Model):
    _inherit = 'account.payment.method'

    pain_version = fields.Selection(selection_add=[
        ('scthr:pain.001.001.03',
         'scthr:pain.001.001.03 Credit Transfer v03HR (used in Croatia)'),
        ('scthr:pain.001.001.09',
         'scthr:pain.001.001.09 Credit Transfer v09HR (used in Croatia)'),
        ])

    def get_xsd_file_path(self):
        self.ensure_one()
        painv = self.pain_version
        if painv in ['scthr:pain.001.001.03', 'scthr:pain.001.001.09']:
            path = 'l10n_hr_pain_credit_transfer/data/%s.xsd' % painv
            return path
        return super().get_xsd_file_path()
