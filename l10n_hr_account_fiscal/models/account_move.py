import logging

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta

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
