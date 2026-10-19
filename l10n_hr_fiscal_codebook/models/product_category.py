from odoo import fields, models


class ProductCategory(models.Model):
    _inherit = "product.category"

    # product.category carries no company/country in core, so the
    # Fiscalization 2.0 group is shown based on the current company's
    # fiscal country instead.
    l10n_hr_show_fiscal_fields = fields.Boolean(
        compute="_compute_l10n_hr_show_fiscal_fields",
    )

    def _compute_l10n_hr_show_fiscal_fields(self):
        show = self.env.company.account_fiscal_country_id.code == "HR"
        for category in self:
            category.l10n_hr_show_fiscal_fields = show
