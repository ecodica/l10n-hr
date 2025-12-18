from datetime import timedelta

from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.hr.fiskal.mixin", "l10n.hr.xml.mixin"]

    l10n_hr_fiskal_log_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.log",
        inverse_name="invoice_id",
        string="Fiskal message logs",
        help="Log of all messages sent and received for FINA",
    )

    @api.constrains('invoice_date')
    def _check_invoice_date_fiscal_time(self):
        """ Ensure that Invoice Date is not later than Time of Invoicing """
        for move in self:
            if not move.invoice_date or not move.l10n_hr_vrijeme_izdavanja:
                continue

            fiscal_date = move.l10n_hr_vrijeme_izdavanja.date()
            if move.invoice_date > fiscal_date:
                raise ValidationError(
                    _("The Invoice Date (%s) cannot be later than the Time of Invoicing (%s).")
                    % (move.invoice_date, fiscal_date)
                )

    @api.constrains('state')
    def _check_fiscalization_invoice_cancel(self):
        for invoice in self.filtered(lambda i: i.move_type in  ["out_invoice", "out_refund"]):
            if invoice.company_id.l10n_hr_fiskal_cancel_confirmed_invoice:
                continue
            if invoice.l10n_hr_zki and invoice.state != 'posted':
                raise ValidationError(_("""Canceling or returning fiscalized invoiced in draft is disabled.
                    If necessary, enable this feature on company."""))

    def _check_zki_on_confirm(self):
        """Check if on confirmed invoice ZKI is set for invoiced that should be fiscalized"""
        for invoice in self.filtered(lambda i: i.state == 'posted'):
            if invoice._l10n_hr_fiscalization_needed('racuni') and not invoice.l10n_hr_zki:
                raise ValidationError(_("""ZKI number is not set on invoice that should be fiscalized.
                    Check if fiscalization is properly configured."""))

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post(soft=soft)
        invoices._check_zki_on_confirm()
        return invoices

    def button_draft(self):
        """ Extend to clear ZKI if not fully fiscalized """
        if self.l10n_hr_zki and not self.l10n_hr_jir:
            self.l10n_hr_zki = False
        super().button_draft()

    def action_cron_fiskaliziraj_batch(self):
        move_ids = self.search([
            ('l10n_hr_jir', '=', False),
            ('move_type', 'in', ['out_invoice', 'out_refund']),
            ('state', 'not in', ['draft']),
            ('l10n_hr_fiskal_uredjaj_id.fiskalisation_active', '=', True),
            ('l10n_hr_fiskal_uredjaj_id.enable_cron_fiskalisation', '=', True)
        ])

        moves_to_process = self.env['account.move']
        timestamp = fields.Datetime.now()
        for move in move_ids:

            delay_hours = move.l10n_hr_fiskal_uredjaj_id.cron_fiskalisation_delay_hours or 0
            required_processing_time = move.l10n_hr_vrijeme_izdavanja + timedelta(hours=delay_hours)

            if required_processing_time < timestamp:
                moves_to_process += move

        total_found = len(moves_to_process)
        if total_found > 0:
            moves_to_process._fiskaliziraj_batch()

    def action_manual_fiskaliziraj_batch(self):
        total_selected_count = len(self)
        fiscalized_move_ids = self.filtered(lambda x: x.l10n_hr_jir and x.l10n_hr_zki)
        already_fiscalized_count = len(fiscalized_move_ids)
        not_fiscalized_move_ids = self - fiscalized_move_ids

        if not not_fiscalized_move_ids:
            return self._get_notification_action(
                _("Already Fiscalized"),
                _("All selected invoices are already fiscalized"),
                "info"
            )

        success, skipped, failed = not_fiscalized_move_ids._fiskaliziraj_batch()

        if success == 0 and failed == 0:
            return self._get_notification_action(
                _("Fiscalization Skipped"),
                _("All selected invoices are fiscalized or do not need fiscalization"),
                "info"
            )

        elif failed == 0:
            return self._get_notification_action(
                _("Fiscalization Successfull"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s"
                ) % (total_selected_count, already_fiscalized_count + skipped, success),
                "success"
            )
        else:
            return self._get_notification_action(
                _("Fiscalization Finished: Failures Detected"),
                _(
                    "Fiscalization result: Started: %s | Skipped: %s | Fiscalized: %s | Failed: %s"
                ) % (total_selected_count, already_fiscalized_count + skipped, success, failed),
                "warning"
            )

    def _fiskaliziraj_batch(self):
        """
        Attempts fiscalization for records in the current set, handling success (res=True),
        skips (res=False), and errors (exceptions).
        """
        success_count = 0
        skipped_count = 0
        error_count = 0

        for move in self:
            try:
                res = move.fiskaliziraj()
                if res:
                    success_count += 1
                else:
                    skipped_count += 1

            except Exception as e:
                error_count += 1
                continue

        return success_count, skipped_count, error_count

    def _get_notification_action(self, title, message, type):
        """ Returns notification action for client """
        return {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'title': title,
                'message': message,
                'type': type,
                'sticky': True,
            }
        }

    def button_fiskaliziraj(self):
        self.ensure_one()
        # ako imam JIR pokreće provjeru ili ako nema fiskalizaciju.
        self.fiskaliziraj()  # from 10n.hr.fixcal.mixin

    def button_provjera_fiskalizacije(self):
        self.fiskaliziraj(msg_type='provjera')

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        delay_fiscalization = not self.l10n_hr_fiskal_uredjaj_id.enable_fiskalise_on_confirm
        if self.l10n_hr_fiskal_uredjaj_id.fiskalisation_active:
            self.fiskaliziraj(delay_fiscalization=delay_fiscalization)
        return res

    @api.model
    def search_not_fiscalized_invoice_count(self, company_id):
        """Search for count of Account Moves that are not fiscalized"""
        domain = [
            ('l10n_hr_zki', '!=', False),
            ('l10n_hr_jir', '=', False),
            ('state', '=', 'posted'),
            ('company_id', '=', company_id)
        ]
        count = self.env['account.move'].sudo().search_count(domain)
        return {
            'count': count
        }
