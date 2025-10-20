from odoo import _, api, fields, models
from odoo.exceptions import ValidationError

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
    _name = "account.move"
    _inherit = ["account.move", "l10n.hr.fiskal.mixin", "l10n.hr.xml.mixin"]

    l10n_hr_nacin_placanja = fields.Selection(
        selection_add=[
            ("G", "Cash"),
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
            if invoice._l10n_hr_fiscalization_needed('racuni') and not invoice.l10n_hr_zki:
                raise ValidationError(_("""ZKI number is not set on invoice that should be fiscalized.
                    Check if fiscalization is properly configured."""))

    def _must_check_constrains_date_sequence(self):
        """Extend to skip check if l10n_hr_fiskal_uredjaj_id is set."""
        # NOTE: fiskal number are specific and they don't have date reference in them so we can skip that check
        if self.l10n_hr_fiskal_uredjaj_id:
            return False
        return super()._must_check_constrains_date_sequence()

    def _post(self, soft=True):
        """Extend to verify if required fiscalization data is set on posted invoices"""
        invoices = super()._post(soft=soft)
        invoices._check_zki_on_confirm()
        return invoices

    def button_fiskaliziraj(self):
        self.ensure_one()
        # ako imam JIR pokreće provjeru ili ako nema fiskalizaciju.
        self.fiskaliziraj()  # from 10n.hr.fixcal.mixin

    def button_provjera_fiskalizacije(self):
        self.fiskaliziraj(msg_type='provjera')

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        delay_fiscalization = not self.company_id.l10n_hr_fiskal_on_confirm
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
