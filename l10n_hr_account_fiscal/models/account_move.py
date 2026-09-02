import logging

from dateutil.relativedelta import relativedelta
from odoo.exceptions import ValidationError
from odoo.tools import float_compare

from odoo import _, api, fields, models

from ..fiscal import fiscal

_logger = logging.getLogger(__name__)

"""
Invoice/POS Issue timestamp should be readonly on form views.   
With additional customization modul or Studio it should be easy for some rare companies to make it editable.  
On invoice/POS slip _post() action current time stamp and and user should be recorded (if not entered manually).    
Fiscal user OIB(vat) is mandatory.
Invoice/POS Issue timestamp needs to be in Europe/Zagreb timezone (regardles of current user TZ) on:  
  - printed Invoice
  - printed POS slip
  - Fiscalization 1.0 XML
  - Fiscalization 2.0 XML(s)
Context:
Invoice Issue time is controlled with the oficially registered Buisines premise working time.   
Buisines premise code must be second part of the invoice number separated by '/'. 
 
"""


class AccountMove(models.Model):
    _inherit = ["account.move", "l10n_hr.fiscal.v1.mixin"]
    _name = "account.move"

    @api.model
    def _get_fiscal_amount_field_name(self):
        return 'amount_total_signed'

    def _l10n_hr_default_fiscal_user(self):
        """The salesperson on the invoice, falling back to the acting user."""
        return self.invoice_user_id.id or super()._l10n_hr_default_fiscal_user()

    def _get_fisc_tax_values(self):
        tax_data = {
            "Pdv": {},
            "Pnp": {},
            "OstaliPor": [],
            "Naknade": [],
        }
        iznos_oslob_pdv, iznos_ne_podl_opor, iznos_marza = 0.00, 0.00, 0.00

        for tax_line in self.line_ids.filtered(lambda l: l.display_type == 'tax'):
            if not tax_line.tax_line_id.l10n_hr_fiscal_type:
                raise ValidationError(_("Tax %s missing fiscal type!") % tax_line.tax_line_id.name)
            fiscal_type = tax_line.tax_line_id.l10n_hr_fiscal_type
            rate = tax_line.tax_line_id.amount
            # tax_base_amount is already signed by move.direction_sign - negative for
            # out_invoice, the mirror of what we send. Negating it, like balance, puts
            # Osnovica and Iznos on IznosUkupno's convention: + invoice, - storno.
            base_amount = tax_line.tax_base_amount * (-1)
            amount = tax_line.balance * (-1)

            if fiscal_type in ['Pdv', 'Pnp']:
                if not tax_data[fiscal_type].get(rate):
                    tax_data[fiscal_type][rate] = {'Osnovica': base_amount, 'Iznos': 0.0}
                tax_data[fiscal_type][rate]['Iznos'] += amount
            elif fiscal_type == "OstaliPor":
                tax_data["OstaliPor"].append({
                    "Naziv": tax_line.tax_line_id.name,
                    "Stopa": rate,
                    "Osnovica": base_amount,
                    "Iznos": amount,
                })

            elif fiscal_type == "Naknade":
                tax_data["Naknade"].append({"NazivN": tax_line.tax_line_id.name, "IznosN": amount})

        # NOTE: Stavke oslobodjene od poreza, Odoo ne kreira stavke temeljnice ako je stop 0.0
        # TODO: provjeriti kako slati stavke sa stopom 0 i da li ima takvih slucajeva u praksi
        for line in self.line_ids.filtered(lambda line: line.display_type == "product"):
            for tax in line.tax_ids:
                if not tax.l10n_hr_fiscal_type:
                    raise ValidationError(_("Tax '%s' missing fiskal type!") % tax.name)
                fiscal_type = tax.l10n_hr_fiscal_type
                # TODO verify if this logic is valid to get invoice and refund amounts
                base_amount = line.balance * (-1)
                if fiscal_type not in ['oslobodenje', 'ne_podlijeze', 'marza']:
                    continue
                if fiscal_type == "oslobodenje":
                    iznos_oslob_pdv += base_amount
                elif fiscal_type == "ne_podlijeze":
                    iznos_ne_podl_opor += base_amount
                elif fiscal_type == "marza":
                    iznos_marza += base_amount

        # TODO: ovi porezi se ne salju, potrebno ih je ukljuciti ako ih ima
        if iznos_oslob_pdv:
            tax_data["IznosOslobPdv"] = fiscal.format_decimal(iznos_oslob_pdv)
        if iznos_ne_podl_opor:
            tax_data["IznosNePodlOpor"] = fiscal.format_decimal(iznos_ne_podl_opor)
        if iznos_marza:
            tax_data["IznosMarza"] = fiscal.format_decimal(iznos_marza)
        return tax_data

    def _validate_fiscal_invoice(self, racun):
        """Provjeri ispravnost generiranog fisk racuna prije slanja"""
        racun_osnovica = racun.Pdv and sum([float(porez.Osnovica) for porez in racun.Pdv.Porez]) or 0.0
        pdv_iznos = racun.Pdv and sum([float(porez.Iznos) for porez in racun.Pdv.Porez]) or 0.0
        pnp_iznos = racun.Pnp and sum([float(porez.Iznos) for porez in racun.Pnp.Porez]) or 0.0
        # NOTE: osnovice koje se ne salju kroz Pdv/Pnp, ali su dio ukupnog iznosa racuna.
        # Bez njih bi svaki racun sa oslobodenjem / marzom / neoporezivim stavkama
        # pao na provjeri osnovice, iako je poruka ispravna.
        # NOTE: Pnp dijeli osnovicu sa Pdv-om pa se njegova
        # osnovica namjerno NE dodaje - inace bi bila dvostruko zbrojena.
        for field_name in ("IznosOslobPdv", "IznosNePodlOpor", "IznosMarza"):
            racun_osnovica += float(getattr(racun, field_name, None) or 0.0)
        # NOTE: ako tvrtka nije u sustava PDV_a, tada j iznos racuna jednak ukupnom iznosu racuna
        if not racun.USustPdv:
            racun_osnovica = float(racun.IznosUkupno)
        amount_untaxed = self.amount_untaxed_signed
        # NOTE: provjera da li iznos poreza na fisk racunu odgovora iznosu odoo poreza
        tax_amount = sum(self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id.l10n_hr_fiscal_type == 'Pdv').mapped('balance')) * (-1)
        if float_compare(pdv_iznos, tax_amount, precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Iznos poreza na fisk računu se razlikuje od iznosa poreza na Odoo računu'))
        # NOTE: provjera da li je osnovica na Odoo računu isto osnovici koju fiskaliziramo
        # kao iznos osnovice koji fiskaliziramo dovoljno dobro je uzeti osnovice Pdv-a koje fiskaliziramo
        # TODO: za sada nisu podržani dodani porezi, naknade, ...
        if float_compare(racun_osnovica, amount_untaxed, precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Osnovica na fisk računu se razlikuje od osnovice na Odoo računu'))
        # NOTE: provjera da li suma osnovice i poreza sa fisk računa odgovara ukupno iznosu odoo računa
        if float_compare(
                (racun_osnovica + pdv_iznos + pnp_iznos),
                float(racun.IznosUkupno),
                precision_digits=self.currency_id.decimal_places):
            raise ValidationError(_('Osnovica + Iznosi poreza ne odgovaraju ukupnom iznosu na fisk računu'))

    @api.constrains('state')
    def _check_fiscalization_invoice_cancel(self):
        for invoice in self.filtered(lambda i: i.move_type in ["out_invoice", "out_refund"]):
            # if invoice.company_id.l10n_hr_fiskal_cancel_confirmed_invoice:
            #     continue
            if invoice.l10n_hr_zki and invoice.state != 'posted':
                raise ValidationError(_("""Canceling or returning fiscalized invoiced in draft is disabled.
                    If necessary, enable this feature on company."""))

    def _check_zki_on_confirm(self):
        """Check if on confirmed invoice ZKI is set for invoiced that should be fiscalized"""
        for invoice in self.filtered(lambda i: i.state == 'posted'):
            if invoice._l10n_hr_fiscalization_needed() and not invoice.l10n_hr_zki:
                raise ValidationError(_("""ZKI number is not set on invoice that should be fiscalized.
                    Check if fiscalization is properly configured."""))

    def _must_check_constrains_date_sequence(self):
        """Extend to skip check if l10n_hr_fiscal_device_id is set."""
        # NOTE: fiscal number are specific and they don't have date reference in them so we can skip that check
        if self.l10n_hr_fiscal_device_id:
            return False
        return super()._must_check_constrains_date_sequence()

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post(soft=soft)
        invoices._check_zki_on_confirm()
        return invoices

    def _l10n_hr_post_fiscal_check(self):
        res = super()._l10n_hr_post_fiscal_check()
        if self.move_type == 'out_refund' and self.reversed_entry_id:
            # NOTE: if invoice is refunded, then force same payment type on created credit note
            if self.l10n_hr_payment_method != self.reversed_entry_id.l10n_hr_payment_method:
                res.append(
                    _("Croatia Payment Means on origin invoice %s is different from the Croatia Payment Means on this "
                      "invoice. Please change Croatia Payment Means to the %s"
                      ) % (self.reversed_entry_id.name,
                           dict(self._fields['l10n_hr_payment_method'].selection).get(self.l10n_hr_payment_method))
                )
            # NOTE: if invoice is refunded, then force same l10n_hr_fiskal_uredjaj_id on the created credit note
            if self.l10n_hr_fiscal_device_id != self.reversed_entry_id.l10n_hr_fiscal_device_id:
                res.append(
                    _("Fiscal Device on origin invoice %s is different from the Fiscal Device on this "
                      "invoice. Please change Fiscal Device to the %s"
                      ) % (
                        self.reversed_entry_id.name, self.reversed_entry_id.l10n_hr_fiscal_device_id.name_get()[0][1])
                )
        return res

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        delay_fiscalization = not self.l10n_hr_fiscal_device_id.enable_fiscalize_on_confirm
        if self.l10n_hr_fiscal_device_id.fiscalization_active and not self.l10n_hr_jir:
            self.fiscalize(delay_fiscalization=delay_fiscalization)
        return res

    def _get_notification_action(self, title, message, type):
        """Returns notification action for client"""
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': True,
            },
        }

    def _batch_fiscalize(self):
        """Attempts fiscalization for records in the current set."""
        success_count = 0
        skipped_count = 0
        error_count = 0

        for move in self:
            try:
                with self.env.cr.savepoint():
                    fiscalized = move.fiscalize()
            except Exception:
                error_count += 1
                _logger.exception(
                    "Fiscalization failed for %s (id=%s)", move.display_name, move.id)
                continue
            if fiscalized:
                success_count += 1
            else:
                skipped_count += 1

        return success_count, skipped_count, error_count

    @api.model
    @api.readonly
    def search_not_fiscalized_invoice_count(self):
        """Count posted invoices that have a ZKI but no JIR (for systray badge) """
        domain = [
            ('state', '=', 'posted'),
            ('company_id', 'in', self.env.companies.ids),
            ('l10n_hr_zki', '!=', False),
            ('l10n_hr_jir', '=', False)
        ]
        return {'count': self.env['account.move'].search_count(domain)}

    def button_fiscalize(self):
        self.ensure_one()
        self.fiscalize()

    def button_fiscalize_check(self):
        self.fiscalize(msg_type='provjera')

    def button_fiscalize_change(self):
        return {
            "name": self.env._("Change Fiscal Data"),
            "type": "ir.actions.act_window",
            "res_model": "l10n_hr.change.fiscal.data",
            "view_mode": "form",
            "target": "new",
            "context": self.env.context,
        }

    def action_cron_batch_fiscalize(self):
        moves = self.search([
            ('l10n_hr_jir', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'not in', ['draft']),
            ('l10n_hr_fiscal_device_id.fiscalization_active', '=', True),
            ('l10n_hr_fiscal_device_id.enable_cron_fiscalization', '=', True),
        ])
        moves_to_process = self.env['account.move']
        now = fields.Datetime.now()
        for move in moves:
            delay_hours = move.l10n_hr_fiscal_device_id.cron_fiscalization_delay_hours or 0
            required_processing_time = move.l10n_hr_fiscal_time_calc + relativedelta(hours=delay_hours)
            if required_processing_time < now:
                moves_to_process += move
        if len(moves_to_process) > 0:
            moves_to_process._batch_fiscalize()

    def action_manual_batch_fiscalize(self):
        total_selected_count = len(self)
        fiscalized_moves = self.filtered(lambda x: x.l10n_hr_jir and x.l10n_hr_zki)
        already_fiscalized_count = len(fiscalized_moves)
        not_fiscalized_moves = self - fiscalized_moves

        if not not_fiscalized_moves:
            return self._get_notification_action(
                _("Already Fiscalized"),
                _("All selected invoices are already fiscalized"),
                "info",
            )

        success, skipped, failed = not_fiscalized_moves._batch_fiscalize()

        if success == 0 and failed == 0:
            return self._get_notification_action(
                _("Fiscalization Skipped"),
                _(
                    "All selected invoices are fiscalized or do not need fiscalization"
                ),
                "info",
            )

        elif failed == 0:
            return self._get_notification_action(
                _("Fiscalization Successfull"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s"
                )
                % (total_selected_count, already_fiscalized_count + skipped, success),
                "success",
            )
        else:
            return self._get_notification_action(
                _("Fiscalization Finished: Failures Detected"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s | Failed: %s"
                )
                % (
                    total_selected_count,
                    already_fiscalized_count + skipped,
                    success,
                    failed,
                ),
                "warning",
            )
