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
    _inherit = ["account.move", "l10n_hr.fiscal1.mixin"]
    _name = "account.move"

    @api.model
    def _get_fiscal_amount_field_name(self):
        return 'amount_total'

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

    def button_fiscalize(self):
        self.ensure_one()
        self.fiscalize()

    def button_fiscalize_check(self):
        self.fiscalize(msg_type='provjera')

    def _l10n_hr_post_out_invoice(self):
        # singleton record! checked in super()
        res = super()._l10n_hr_post_out_invoice()
        if self.l10n_hr_fiscal_device_id.fiscalization_active and self.l10n_hr_business_process_type_id.code == 'XF1':
            self.fiscalize()
        return res

    @api.model
    def search_not_fiscalized_invoice_count(self, company_id):
        """Search for count of Account Moves that are not fiscalized"""
        domain = [
            ('state', '=', 'posted'),
            ('company_id', '=', company_id),
            ('l10n_hr_zki', '!=', False),
            ('l10n_hr_jir', '=', False)
        ]
        count = self.env['account.move'].sudo().search_count(domain)
        return {'count': count}
