from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    """Extend to change name generation"""
    _inherit = "account.move"

    @api.constrains('name', 'l10n_hr_fiskalni_broj')
    def _check_account_move_name_fiskalni_broj(self):
        """Move name must be same as the l10n_hr_fiskalni_broj."""
        for move in self.filtered(lambda m: m.state == 'posted'):
            if (
                move.company_id.l10n_hr_fiskalni_broj_as_move_name and
                move.name != move.l10n_hr_fiskalni_broj
            ):
                raise ValidationError(
                    _("Move name (%s) is different from the Fiskal Number (%s)",
                    move.name, move.l10n_hr_fiskalni_broj)
                )

    def _force_fiskalni_broj_as_name(self):
        """Set fiskalni_broj as name"""
        for move in self:
            move_has_name = move.name and move.name != '/'
            if (move_has_name or
                move.company_id.account_fiscal_country_id.code != "HR" or
                not move.is_invoice(include_receipts=False) or
                not move.company_id.l10n_hr_fiskalni_broj_as_move_name
            ):
                continue
            fiskal_number = move._gen_fiskal_number()
            if fiskal_number:
                move.name = fiskal_number
                move.l10n_hr_fiskalni_broj = fiskal_number

    def _compute_name(self):
        """Extend to force fiskal number as account move name"""
        self._force_fiskalni_broj_as_name()
        return super()._compute_name()
