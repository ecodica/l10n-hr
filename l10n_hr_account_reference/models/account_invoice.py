# -*- coding: utf-8 -*-

from datetime import datetime as dt
from . import poziv_na_broj as pnbr
from odoo import api, models, fields


class AccountInvoice(models.Model):
    _inherit = "account.invoice"

    payment_reference = fields.Char(string='Payment Reference', copy=False, readonly=True,
                                    states={'draft': [('readonly', False)]})

    def getP1_P4data(self, what):
        res = ''
        if what == 'partner_code':
            res = self.partner_id.ref or str(self.partner_id.id)
        elif what == 'partner_id':
            res = str(self.partner_id.id)
        elif what == 'invoice_no':
            res = self.number
        elif what == 'invoice_ym':
            res = dt.strftime(self.date_invoice, "%Y%m")
        elif what == 'delivery_ym':
            res = dt.strftime(self.date_delivery, "%Y%m")
        return pnbr.get_only_numeric_chars(res)

    def pnbr_get(self):
        model = self.journal_id.model_pnbr
        P1 = self.getP1_P4data(self.journal_id.P1_pnbr or '')
        P2 = self.getP1_P4data(self.journal_id.P2_pnbr or '')
        P3 = self.getP1_P4data(self.journal_id.P3_pnbr or '')
        P4 = self.getP1_P4data(self.journal_id.P4_pnbr or '')
        res = pnbr.reference_number_get(model, P1, P2, P3, P4)
        cc = self.journal_id.country_prefix and \
             self.company_id.country_id and \
             self.company_id.country_id.code or ''
        if cc:
            model = cc + model
        return ' '.join((model, res))

    def _get_computed_reference(self):
        self.ensure_one()
        res = ''
        if self.company_id.invoice_reference_type == 'per_journal':
            if self.journal_id.model_pnbr:
                res = self.pnbr_get()
        else:
            res = super(AccountInvoice, self)._get_computed_reference()
        return res
