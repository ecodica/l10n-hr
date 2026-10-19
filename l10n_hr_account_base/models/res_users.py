from odoo import api, fields, models


class ResUsers(models.Model):
    _inherit = 'res.users'

    # res.users has no company_registry of its own in Odoo 19; expose the
    # partner's (core, computed) field for the user preferences form.
    company_registry = fields.Char(related='partner_id.company_registry')

    # OIB is a Croatian registry number
    l10n_hr_show_oib = fields.Boolean(compute='_compute_l10n_hr_show_oib')

    @api.depends('company_ids')
    def _compute_l10n_hr_show_oib(self):
        croatia = self.env.ref('base.hr', raise_if_not_found=False)
        for user in self:
            user.l10n_hr_show_oib = bool(
                croatia
                and user.company_ids.filtered(lambda c: c.country_id == croatia)
            )
