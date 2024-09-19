from odoo import models
from odoo.osv import expression


class FiscalFiscalMixin(models.AbstractModel):
    """"Extend to enable select of partners related to the employees."""
    _inherit = "l10n.hr.fiskal.mixin"

    def _get_l10n_hr_fiskal_user_id_domain(self):
        """Extend domain so that employee user can also be selected"""
        domain = super()._get_l10n_hr_fiskal_user_id_domain()
        domain = expression.OR([domain, [('employee_ids', '!=', False)]])
        return domain
