from odoo import _, models
from odoo.addons.l10n_hr_account_fiskal.fiskal import fiskal
from odoo.tools import float_compare
from odoo.exceptions import ValidationError


class FiscalFiscalMixin(models.AbstractModel):
    """"Extend to support tips fiscalization"""
    _inherit = "l10n.hr.fiskal.mixin"

    def _l10n_hr_fiscalization_needed(self, message_type):
        """"Check if tips should be fiskalized"""
        if message_type not in ['napojnica', 'provjera_napojnica']:
            return super()._l10n_hr_fiscalization_needed(message_type)
        precision = self.currency_id.decimal_places
        # NOTE: Conditions to fiskalize tips are following:
        #   1. l10n_hr_zki must be set on invoice
        #   2. l10n_hr_napojnica_iznos must be > 0
        #   3. l10n_hr_napojnica_nacin_placanja must be != "T" or transaction fiskalization must be enabled
        if self.l10n_hr_zki and float_compare(self.l10n_hr_napojnica_iznos, 0.0, precision_rounding=precision) > 0 and (
            not self.company_id.l10n_hr_fiskal_transaction_type_skip or
            self.l10n_hr_napojnica_nacin_placanja != "T"
        ):
            return True
        return False

    def _get_fisk_racun_type(self, factory, msg_type):
        if msg_type == 'napojnica':
            return factory.type_factory.RacunNapojnicaType
        return super()._get_fisk_racun_type(factory, msg_type)

    def _prepare_fisk_racun_napojnica(self, factory):
        # NOTE: refunds are fiskalized with negative tip amounts
        amount_coeff = self.move_type == 'out_refund' and (-1) or 1
        # NOTE: if fiskal refund is called then force negative amount
        if self._context.get('l10n_hr_tip_refund'):
            amount_coeff = amount_coeff * (-1)
        return factory.type_factory.NapojnicaType(
            iznosNapojnice=fiskal.format_decimal(
                self.l10n_hr_napojnica_iznos * amount_coeff),
            nacinPlacanjaNapojnice=self.l10n_hr_napojnica_nacin_placanja)

    def _prepare_fisk_racun(self, factory, fiskal_data, msg_type):
        """Extend ta add tips to fisk invoice"""
        racun = super()._prepare_fisk_racun(factory, fiskal_data, msg_type)
        if msg_type == 'napojnica':
            racun.Napojnica = self._prepare_fisk_racun_napojnica(factory)
        return racun

    def _fisk_msg_type(self):
        """Extend to fiscalize 'napojnica' type."""
        return super()._fisk_msg_type() + ["napojnica"]

    def _handle_fisk_response(self, response, msg_type):
        """Extend to write if fiskalization of tips is successful)"""
        res = super()._handle_fisk_response(response, msg_type)
        if (
            msg_type == 'napojnica' and
            hasattr(response, 'PorukaOdgovora') and
            response.PorukaOdgovora and
            response.PorukaOdgovora.SifraPoruke == 'p002'
        ):
            self.l10n_hr_napojnica_is_fiscalized = True
            if self._context.get('l10n_hr_tip_refund'):
                self.l10n_hr_napojnica_refund_fiscalized = True

        return res

    def _check_tips_before_fiskalize(self, msg_type):
        """Check if ZKI, napojnica_iznos, and napojnica_payment_type are set before fisk."""
        if msg_type != 'napojnica':
            return
        if self.l10n_hr_napojnica_refund_fiscalized:
            raise ValidationError(_("Tip refund is already fiskalized."))
        # NOTE: skip check if refund is called
        if (
            self.l10n_hr_napojnica_is_fiscalized and
            not self.l10n_hr_napojnica_refund_fiscalized and
            not self._context.get('l10n_hr_tip_refund')
        ):
            raise ValidationError(_("Tip is already fiskalized."))
        if not self.l10n_hr_zki:
            raise ValidationError(
                _("To fiskalize invoice tip, ZKI must be set."))
        if not self.l10n_hr_napojnica_nacin_placanja:
            raise ValidationError(
                _("To fiskalize invoice tip, payment type must be set."))
        if round(self.l10n_hr_napojnica_iznos or 0.0, self.currency_id.decimal_places) <= 0:
            raise ValidationError(
                _("Tip amount must be set to fiskalize tips."))

    def fiskaliziraj(self, msg_type="racuni", delay_fiscalization=False):
        """Extend to do base check before tip fiskalization."""
        self._check_tips_before_fiskalize(msg_type)
        return super().fiskaliziraj(msg_type=msg_type, delay_fiscalization=delay_fiscalization)
