import logging

from dateutil.relativedelta import relativedelta
from odoo.exceptions import UserError, ValidationError
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

    def _l10n_hr_default_fiscal_operator(self):
        """The salesperson's employee, falling back to the acting user's: whoever issued it."""
        self.ensure_one()
        salesperson = self.invoice_user_id.with_company(self.company_id).sudo().employee_id
        return salesperson or super()._l10n_hr_default_fiscal_operator()

    def _get_fisc_tax_values(self):
        """Tax breakdown for the message, computed with Odoo's own tax engine.

        Reading ``tax_base_amount`` from the posted tax journal items cannot
        aggregate two taxes sharing a rate (only the first base wins) and counts
        a base once per repartition line. The engine's ``tax_details`` carry one
        entry per (base line, leaf tax), without the repartition split, so their
        aggregation by fiscal type and rate is unambiguous. Amounts are already
        signed like ``IznosUkupno``: positive on an invoice, negative on a storno.
        """
        self.ensure_one()
        tax_data = {"Pdv": {}, "Pnp": {}, "OstaliPor": [], "Naknade": []}
        untaxed = {"IznosOslobPdv": 0.0, "IznosNePodlOpor": 0.0, "IznosMarza": 0.0}
        base_lines, _tax_lines = self._get_rounded_base_and_tax_lines()
        for base_line in base_lines:
            tax_details = base_line["tax_details"]
            saw_base = False
            # The engine reports positive magnitudes; the fiscal convention is the
            # mirror of the accounting sign: + invoice, - storno.
            direction = -self.direction_sign
            for entry in tax_details["taxes_data"]:
                saw_base |= self._add_fisc_tax_entry(tax_data, untaxed, entry, direction)
            # A line with no base-bearing tax still belongs to the untaxed total.
            # Fees alone have no base of their own, so their line base is not yet
            # reported anywhere; put it with the non-taxable base.
            if not saw_base:
                untaxed["IznosNePodlOpor"] += direction * tax_details["total_excluded"]
        tax_data.update({
            key: fiscal.format_decimal(amount)
            for key, amount in untaxed.items()
            if amount
        })
        return tax_data

    def _add_fisc_tax_entry(self, tax_data, untaxed, entry, direction):
        """File one tax-detail entry under its Croatian fiscal type.

        :return: whether the entry contributed to a base-bearing bucket
        """
        tax = entry["tax"]
        if not tax.l10n_hr_fiscal_type:
            raise ValidationError(_("Tax '%s' missing fiscal type!") % tax.name)
        base_amount = direction * entry["base_amount"]
        tax_amount = direction * entry["tax_amount"]
        fiscal_type = tax.l10n_hr_fiscal_type
        if fiscal_type in ["Pdv", "Pnp"]:
            bucket = tax_data[fiscal_type].setdefault(
                tax.amount, {"Osnovica": 0.0, "Iznos": 0.0})
            bucket["Osnovica"] += base_amount
            bucket["Iznos"] += tax_amount
            return True
        elif fiscal_type == "OstaliPor":
            raise ValidationError(_(
                "Tax '%s' is an 'Ostali por' which fiscalization cannot send yet.",
                tax.name))
        elif fiscal_type == "Naknade":
            tax_data["Naknade"].append({"NazivN": tax.name, "IznosN": tax_amount})
            return False
        elif fiscal_type == "oslobodenje":
            untaxed["IznosOslobPdv"] += base_amount
            return True
        elif fiscal_type == "ne_podlijeze":
            untaxed["IznosNePodlOpor"] += base_amount
            return True
        elif fiscal_type == "marza":
            untaxed["IznosMarza"] += base_amount
            return True
        raise ValidationError(_("Tax '%s' has an unknown fiscal type!") % tax.name)

    def _validate_fiscal_invoice(self, racun):
        """Check the generated fiscal receipt against the source document."""
        racun_osnovica = racun.Pdv and sum([float(porez.Osnovica) for porez in racun.Pdv.Porez]) or 0.0
        pdv_iznos = racun.Pdv and sum([float(porez.Iznos) for porez in racun.Pdv.Porez]) or 0.0
        pnp_iznos = racun.Pnp and sum([float(porez.Iznos) for porez in racun.Pnp.Porez]) or 0.0
        naknade_iznos = 0.0
        naknade = getattr(racun, "Naknade", None)
        if naknade:
            items = getattr(naknade, "Naknada", None)
            if items and not isinstance(items, (list, tuple)):
                items = [items]
            naknade_iznos = sum([float(item.IznosN) for item in items or []])
        # NOTE: osnovice koje se ne salju kroz Pdv/Pnp, ali su dio ukupnog iznosa racuna.
        # Bez njih bi svaki racun sa oslobodenjem / marzom / neoporezivim stavkama
        # pao na provjeri osnovice, iako je poruka ispravna.
        # NOTE: Pnp dijeli osnovicu sa Pdv-om pa se njegova
        # osnovica namjerno NE dodaje - inace bi bila dvostruko zbrojena.
        for field_name in ("IznosOslobPdv", "IznosNePodlOpor", "IznosMarza"):
            racun_osnovica += float(getattr(racun, field_name, None) or 0.0)
        # NOTE: ako tvrtka nije u sustavu PDV_a, tada je iznos racuna jednak ukupnom iznosu racuna
        if not racun.USustPdv:
            racun_osnovica = float(racun.IznosUkupno)
        precision = self.company_currency_id.decimal_places
        amount_untaxed = self.amount_untaxed_signed
        # NOTE: provjera da li iznos poreza na fisk racunu odgovara iznosu odoo poreza
        tax_amount = sum(self.line_ids.filtered(
            lambda l: l.display_type == 'tax' and l.tax_line_id.l10n_hr_fiscal_type == 'Pdv').mapped('balance')) * (-1)
        if float_compare(pdv_iznos, tax_amount, precision_digits=precision):
            raise ValidationError(_('Iznos poreza na fisk računu se razlikuje od iznosa poreza na Odoo računu'))
        # NOTE: provjera da li je osnovica na Odoo računu jednaka osnovici koju fiskaliziramo
        # NOTE: za sada nisu podržani dodani porezi, naknade koje mijenjaju osnovicu
        if float_compare(racun_osnovica, amount_untaxed, precision_digits=precision):
            raise ValidationError(_('Osnovica na fisk računu se razlikuje od osnovice na Odoo računu'))
        # NOTE: provjera da li suma osnovice i poreza sa fisk racuna odgovara ukupnom iznosu odoo racuna
        if racun.USustPdv and float_compare(
                (racun_osnovica + pdv_iznos + pnp_iznos + naknade_iznos),
                float(racun.IznosUkupno),
                precision_digits=precision):
            raise ValidationError(_('Osnovica + Iznosi poreza ne odgovaraju ukupnom iznosu na fisk računu'))

    @api.constrains('state')
    def _l10n_hr_check_fiscalization_invoice_cancel(self):
        for invoice in self.filtered(
                lambda i: i.country_code == 'HR'
                and i.move_type in ["out_invoice", "out_refund"]):
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
        if any(self.mapped("l10n_hr_fiscal_device_id")):
            return False
        return super()._must_check_constrains_date_sequence()

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post(soft=soft)
        invoices.filtered(
            lambda m: m.country_code == 'HR')._check_zki_on_confirm()
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
                        self.reversed_entry_id.name, self.reversed_entry_id.l10n_hr_fiscal_device_id.display_name)
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
            # fiscalization only applies to Croatian companies
            ('company_id.account_fiscal_country_id.code', '=', 'HR'),
            ('l10n_hr_zki', '!=', False),
            ('l10n_hr_jir', '=', False)
        ]
        return {'count': self.env['account.move'].search_count(domain)}

    def button_fiscalize(self):
        self.ensure_one()
        self.fiscalize()

    def button_fiscalize_check(self):
        self._l10n_hr_fiscal_check()

    @api.model
    def _l10n_hr_fiscal_change_depends(self):
        """Extend: the state, type, hash and date the invoice is refused by."""
        return super()._l10n_hr_fiscal_change_depends() + ['state', 'move_type', 'inalterable_hash', 'date']

    def _l10n_hr_fiscal_change_document_errors(self):
        """Extend: only a posted customer invoice or credit note, not hashed or locked.

        A new customer is written on the journal items of the invoice and of the payments
        that follow it, which core refuses in a locked period.
        """
        errors = super()._l10n_hr_fiscal_change_document_errors()
        if errors:
            return errors
        if self.state != 'posted' or self.move_type not in ('out_invoice', 'out_refund'):
            return [self.env._("Only a posted customer invoice or credit note can change its fiscal data.")]
        if self.inalterable_hash:
            # hashed journal items refuse a new partner
            return [self.env._("%(move)s is secured by a hash, so its customer cannot change.",
                               move=self.display_name)]
        try:
            (self | self._l10n_hr_fiscal_change_counterparts()[0].move_id)._check_fiscal_lock_dates()
        except UserError as error:
            return [error.args[0]]
        return []

    def _l10n_hr_fiscal_change_errors(self, partner, payment_method):
        """Extend: an invoice needs a customer, and keeps its receivable account.

        A new customer recomputes the receivable account of a single installment from
        the customer's own account. Moving the receivable would break its reconciliation
        with the payment, so a customer with another receivable account is refused.
        """
        errors = super()._l10n_hr_fiscal_change_errors(partner, payment_method)
        if errors:
            return errors
        if not partner:
            return [self.env._("An invoice needs a customer.")]
        receivable = partner.commercial_partner_id.with_company(self.company_id).property_account_receivable_id
        if self.fiscal_position_id:
            receivable = self.fiscal_position_id.map_account(receivable)
        term_accounts = self.line_ids.filtered(lambda line: line.display_type == 'payment_term').account_id
        if receivable and term_accounts != receivable:
            errors.append(self.env._(
                "%(partner)s uses the receivable account %(account)s, the invoice %(accounts)s. "
                "Cancel the invoice and issue a new one instead.",
                partner=partner.display_name,
                account=receivable.display_name,
                accounts=", ".join(term_accounts.mapped("display_name")),
            ))
        return errors

    def _l10n_hr_fiscal_change_warnings(self, partner, payment_method):
        """Extend: name the payments that keep the old customer."""
        warnings = super()._l10n_hr_fiscal_change_warnings(partner, payment_method)
        kept = self._l10n_hr_fiscal_change_counterparts()[1]
        if kept and partner != self.partner_id:
            warnings.append(self.env._(
                "These payments stay with %(partner)s: %(payments)s. Change their customer by hand "
                "if needed.",
                partner=self.partner_id.display_name,
                payments=", ".join(kept.mapped("display_name")),
            ))
        return warnings

    def _l10n_hr_fiscal_change_counterparts(self):
        """Split what is reconciled with this invoice into what follows its customer and the rest.

        :return: ``(movable, kept)``: the journal items that take the new customer with the
            invoice, and the entries left as they are. Here nothing moves: a payment
            registered by hand or matched on a bank statement is its own record of who
            paid. Modules whose payments are part of the sale override this.
        """
        self.ensure_one()
        receivable = self.line_ids.filtered(lambda line: line.display_type == 'payment_term')
        counterparts = receivable.matched_debit_ids.debit_move_id | receivable.matched_credit_ids.credit_move_id
        return self.env['account.move.line'], counterparts.move_id

    @api.model
    def _l10n_hr_fiscal_change_kept_fields(self):
        """Fields recomputed from the customer that must keep their value on a posted invoice.

        Recomputing them would rebuild the payment-term lines, reset the bank account and
        the terms, or remap accounts on an invoice that is already issued.
        """
        return [
            'fiscal_position_id',
            'invoice_payment_term_id',
            'preferred_payment_method_line_id',
            'partner_bank_id',
            'narration',
        ]

    def _l10n_hr_write_fiscal_change(self, vals):
        """Extend: write the customer of a posted invoice, and of the payments that follow it."""
        self.ensure_one()
        movable = self._l10n_hr_fiscal_change_counterparts()[0]
        kept = {
            name: self._fields[name].convert_to_write(self[name], self)
            for name in self._l10n_hr_fiscal_change_kept_fields()
        }
        self.with_context(skip_readonly_check=True).write({**kept, **vals})
        if 'partner_id' in vals:
            movable.write({'partner_id': self.commercial_partner_id.id})

    def action_cron_batch_fiscalize(self):
        moves = self.search([
            ('l10n_hr_jir', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'not in', ['draft']),
            # fiscalization only applies to Croatian companies
            ('company_id.account_fiscal_country_id.code', '=', 'HR'),
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
