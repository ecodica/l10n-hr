from datetime import datetime as dt

from odoo import models, _
from odoo.exceptions import UserError
from . import account_reference as ar


class AccountMove(models.Model):
    _inherit = "account.move"

    def _l10n_hr_get_default_properties(self):
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
            self.env["ir.default"]
            .sudo()
            .search([("field_id", "in", fields.ids)])
        )
        res = {}
        for p in properties:
            res[p.field_id.name] = eval(p.json_value)
        return res

    def _l10n_hr_ar_get(self):

        def getP1_P4data(self, what, defaults):
            result = ""
            what = what or defaults.get(what._name)
            if what == "move_id":
                result = str(self.id)
            elif what == "partner_code":
                result = self.partner_id.ref or str(self.partner_id.id)
            elif what == "partner_id":
                result = str(self.partner_id.id)
            elif what == "invoice_no":
                result = self.name
                if self.country_code == "HR":
                    if not self.l10n_hr_fiscal_number:
                        # checks will be done later now just need the number
                        self.l10n_hr_fiscal_number = self.l10n_hr_gen_fiscal_number() or '0000'
                    result = self.l10n_hr_fiscal_number
                    separator = self.company_id.l10n_hr_fiscal_separator
                    result = result.split(separator)[0]
            elif what == "invoice_ym":
                result = dt.strftime(self.invoice_date, "%Y%m")
            elif what == "delivery_ym":
                result = dt.strftime(self.delivery_date, "%Y%m")
            return ar.get_only_numeric_chars(result)

        model = self.journal_id.invoice_reference_model
        default_properties = self._l10n_hr_get_default_properties()

        P1 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P1_ar, default_properties)
        P2 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P2_ar, default_properties)
        P3 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P3_ar, default_properties)
        P4 = getP1_P4data(
            self, self.journal_id.property_l10n_hr_P4_ar, default_properties)

        res = ar.reference_number_get(model, P1, P2, P3, P4)
        
        return " ".join((model, res))

    def _get_invoice_computed_reference(self):
        """
           Override original method to allow for computing payment_reference 
           according to the Croatian localization.
        """
        self.ensure_one()
        if self.journal_id.invoice_reference_type == 'none':
            return ''
        if self.journal_id.invoice_reference_model[:2] == 'HR' and \
            self.journal_id.invoice_reference_type == 'hr':
            return self._l10n_hr_ar_get()
        ref_function = getattr(self, f'_get_invoice_reference_{self.journal_id.invoice_reference_model}_{self.journal_id.invoice_reference_type}', None)
        if ref_function is None:
            raise UserError(_("The combination of reference model and reference type on the journal is not yet implemented."))
        return ref_function()
