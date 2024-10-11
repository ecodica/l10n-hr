from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    """Extend to change name generation"""
    _inherit = "account.move"

    def _force_fiskalni_broj_as_name(self):
        """Check if fiskal number should be forced as a name."""
        self.ensure_one()
        if (
            # NOTE: state must be posted so that we don't increment sequences
            # in on_change function (e.g. on journal change)
            self.state == 'posted' and
            self.company_id.account_fiscal_country_id.code == "HR" and
            self.move_type in self.get_sale_types() and
            self.company_id.l10n_hr_fiskalni_broj_as_move_name
        ):
            return True
        return False

    @api.constrains('name', 'l10n_hr_fiskalni_broj')
    def _check_account_move_name_fiskalni_broj(self):
        """Move name must be same as the l10n_hr_fiskalni_broj."""
        for move in self.filtered(lambda m: m.state == 'posted'):
            if (
                move._force_fiskalni_broj_as_name() and
                move.name != move.l10n_hr_fiskalni_broj
            ):
                raise ValidationError(
                    _("Move name (%s) is different from the Fiskal Number (%s)",
                    move.name, move.l10n_hr_fiskalni_broj)
                )

    def _set_fiskalni_broj_as_name(self):
        """Set fiskalni_broj as name"""
        for move in self:
            move_has_name = move.name and move.name != '/'
            if (move_has_name or not move._force_fiskalni_broj_as_name()):
                continue
            fiskal_number = move._gen_fiskal_number()
            if fiskal_number:
                move.name = fiskal_number
                move.l10n_hr_fiskalni_broj = fiskal_number

    def _compute_name(self):
        """Extend to force fiskal number as account move name"""
        self._set_fiskalni_broj_as_name()
        return super()._compute_name()
