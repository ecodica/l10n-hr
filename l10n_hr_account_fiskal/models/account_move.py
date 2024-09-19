from odoo import _, api, fields, models
from odoo.exceptions import ValidationError


class AccountMove(models.Model):
    _name = "account.move"
    _inherit = ["account.move", "l10n.hr.fiskal.mixin", "l10n.hr.xml.mixin"]

    l10n_hr_nacin_placanja = fields.Selection(
        selection_add=[
            ("G", "Cash (bills and coins)"),
            ("K", "Credit or debit cards"),
            ("C", "Bank Cheque"),
            ("O", "Other payment means"),
        ],
        help="According to Fiscalization Law and regulative "
        "there is 5 possible options: \n"
        "T - Transaction bank account\n"
        "G - Cash (coins or bills), fiskalisation required\n"
        "K - Bank cards, fiskalisation required\n"
        "C - Cheque payment, fiskalisation required\n"
        "O - Other payment, fiskalisation required\n",
    )
    l10n_hr_fiskal_log_ids = fields.One2many(
        comodel_name="l10n.hr.fiskal.log",
        inverse_name="invoice_id",
        string="Fiskal message logs",
        help="Log of all messages sent and received for FINA",
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
            if invoice._l10n_hr_fiscalization_needed() and not invoice.l10n_hr_zki:
                raise ValidationError(_("""ZKI number is not set on invoice that should be fiscalized.
                    Check if fiscalization is properly configured."""))

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post()
        invoices._check_zki_on_confirm()
        return invoices

    def button_fiskaliziraj(self):
        self.ensure_one()
        # ako imam JIR pokreće provjeru ili ako nema fiskalizaciju.
        self.fiskaliziraj()  # from 10n.hr.fixcal.mixin

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        delay_fiscalization = not self.company_id.l10n_hr_fiskal_on_confirm
        if self.l10n_hr_fiskal_uredjaj_id.fiskalisation_active:
            self.fiskaliziraj(delay_fiscalization=delay_fiscalization)
        return res
