from datetime import datetime as dt

from odoo import models

from . import poziv_na_broj as pnbr


class AccountMove(models.Model):
    _inherit = "account.move"

    def _get_default_properties(self):
        fields = (
            self.env["ir.model.fields"]
            .sudo()
            .search(
                [
                    ("model", "=", "account.journal"),
                    ("name", "like", "property_l10n_hr_P"),
                ]
            )
        )
        properties = (
            self.env["ir.property"]
            .sudo()
            .search([("fields_id", "in", fields.ids), ("res_id", "=", False)])
        )
        res = {}
        for p in properties:
            res[p.fields_id.name] = p.value_text
        return res

    def pnbr_get(self):
        def getP1_P4data(self, what, defaults):
            res = ""
            what = what or defaults.get(what._name)
            if what == "move_id":
                res = str(self.id)
            elif what == "partner_code":
                res = self.partner_id.ref or str(self.partner_id.id)
            elif what == "partner_id":
                res = str(self.partner_id.id)
            elif what == "invoice_no":
                res = self.name
                if self.country_code == "HR":
                    # samo za HR fiskalni broj uz lokalizaciju
                    if not self.l10n_hr_fiskalni_broj:
                        # checks will be done later now just need the number
                        self.l10n_hr_fiskalni_broj = self._gen_fiskal_number()
                    res = self.l10n_hr_fiskalni_broj
                    separator = self.company_id.l10n_hr_fiskal_separator
                    res = res.split(separator)[0]
            elif what == "invoice_ym":
                res = dt.strftime(self.invoice_date, "%Y%m")
            elif what == "delivery_ym":
                res = dt.strftime(self.date_delivery, "%Y%m")
            return pnbr.get_only_numeric_chars(res)

        model = self.journal_id.invoice_reference_model
        default_properties = self._get_default_properties()

        P1 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P1_pnbr, default_properties
        )
        P2 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P2_pnbr, default_properties
        )
        P3 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P3_pnbr, default_properties
        )
        P4 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P4_pnbr, default_properties
        )

        res = pnbr.reference_number_get(model, P1, P2, P3, P4)
        model = "HR" + model
        return " ".join((model, res))

    def _get_invoice_reference_00_hr(self):
        return self.pnbr_get()

    def _get_invoice_reference_01_hr(self):
        return self.pnbr_get()

    def _get_invoice_reference_02_hr(self):
        return self.pnbr_get()

    def _get_invoice_reference_03_hr(self):
        return self.pnbr_get()

    def _get_invoice_reference_06_hr(self):
        return self.pnbr_get()

    # def _get_invoice_computed_reference(self):
    #     if self.journal_id.invoice_reference_type == 'hr':
    #         return self.pnbr_get()
    #     return super(AccountMove, self)._get_invoice_computed_reference()
