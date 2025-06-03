from odoo import models


class IrUiMenu(models.Model):
    _inherit = 'ir.ui.menu'

    def _load_menus_blacklist(self):
        res = super()._load_menus_blacklist()
        croatia_id = self.env.ref('base.hr', raise_if_not_found=False)
        user_croatian_companies = self.env.user.company_ids.filtered(lambda c: c.country_id == croatia_id)
        if not user_croatian_companies:
            res.append(self.env.ref('l10n_hr_account_base.menu_finance_config_croatia').id)
            res.append(self.env.ref('l10n_hr_account_base.menu_action_fiscal_premise').id)
            res.append(self.env.ref('l10n_hr_account_base.menu_action_fiscal_device').id)
            res.append(self.env.ref('l10n_hr_account_base.menu_l10n_hr_reports').id)
        return res
