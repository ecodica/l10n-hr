from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        croatia_id = self.env.ref('base.hr', raise_if_not_found=False)
        user_croatian_companies = self.env.user.company_ids.filtered(
            lambda c: c.country_id == croatia_id
        )
        if not user_croatian_companies:
            res.append(self.env.ref('l10n_hr_fiscal_codebook.l10n_hr_fiscal_codebooks').id)
        return res
