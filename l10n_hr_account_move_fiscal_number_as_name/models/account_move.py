from odoo import _, api, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    """Extend to change name generation"""
    _inherit = "account.move"

    def _force_fiscal_number_as_name(self):
        """Check if fiscal number should be forced as a name."""
        self.ensure_one()
        if (
            # NOTE: state must be posted so that we don't increment sequences
            # in on_change function (e.g. on journal change)
            self.state == 'posted' and
            self.company_id.account_fiscal_country_id.code == "HR" and
            self.move_type in self.get_sale_types() and
            self.company_id.l10n_hr_fiscal_number_as_move_name
        ):
            return True
        return False

    @api.constrains('name', 'l10n_hr_fiscal_number')
    def _check_account_move_name_fiscal_number(self):
        """Move name must be same as the l10n_hr_fiscal_number."""
        for move in self.filtered(lambda m: m.state == 'posted'):
            if (
                move._force_fiscal_number_as_name() and
                move.name != move.l10n_hr_fiscal_number
            ):
                raise ValidationError(
                    _("Move name (%(move_name)s) is different from the Fiscal Number (%(fiscal_number)s)",
                    move_name=move.name, fiscal_number=move.l10n_hr_fiscal_number)
                )

    def _set_fiscal_number_as_name(self):
        """Set fiscal_number as name"""
        for move in self:
            move_has_name = move.name and move.name != '/'
            if (move_has_name or not move._force_fiscal_number_as_name()):
                continue
            fiscal_number = move._gen_fiscal_number()
            if fiscal_number:
                move.name = fiscal_number
                move.l10n_hr_fiscal_number = fiscal_number

    def _compute_name(self):
        """Extend to force fiscal number as account move name"""
        self._set_fiscal_number_as_name()
        return super()._compute_name()

    def _compute_made_sequence_gap(self):
        """Extend to skip checking gap for invoices that are using fiscalni broj as invoice name"""
        # NOTE: existing checks are not good enough to verify if there are any number gaps because
        # fiscal number is generated from custom sequence number
        # TODO: implement checks that will take custom sequences by fiscal device and
        # fiscal place in consideration
        res = None
        fiscal_moves = self.filtered(
            lambda m: m.company_id.l10n_hr_fiscal_number_as_move_name and m.move_type in self.get_sale_types())
        fiscal_moves.made_sequence_gap = False
        if moves := self - fiscal_moves:
            res = super(AccountMove, moves)._compute_made_sequence_gap()
        return res
