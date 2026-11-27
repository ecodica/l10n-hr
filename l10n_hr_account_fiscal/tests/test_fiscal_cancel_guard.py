"""The fiscalized-invoice cancel guard is button-only, not a state constraint.

Sekom imports create already-fiscalized receipts in draft with JIR/ZKI carried
from the external system. A blanket ``@api.constrains('state')`` refused that
draft-with-ZKI creation; the guard now fires only on the cancel/reset buttons
and only for issued (posted) or cancelled documents.
"""
from odoo import Command, fields
from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

ZKI = "e4d909c290d0fb1ca068ffaddf22cbd0"
JIR = "1191b4cc-81f0-418f-9be8-3685a48a9e01"


@tagged("post_install", "-at_install")
class TestFiscalCancelGuard(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.company.account_fiscal_country_id = cls.env.ref("base.hr")

    def _invoice(self, zki=False, jir=False):
        vals = {
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "company_id": self.company.id,
            "l10n_hr_payment_method": "G",
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [Command.create({
                "name": "Imported fiscal receipt",
                "quantity": 1.0,
                "price_unit": 10.0,
                "tax_ids": [Command.clear()],
            })],
        }
        if zki:
            vals.update({"l10n_hr_zki": zki, "l10n_hr_jir": jir})
        return self.env["account.move"].create(vals)

    def test_draft_invoice_with_zki_can_be_created(self):
        """An imported, externally fiscalized draft is not refused at create."""
        invoice = self._invoice(zki=ZKI, jir=JIR)
        self.assertEqual(invoice.state, "draft")
        self.assertEqual(invoice.l10n_hr_zki, ZKI)
        self.assertEqual(invoice.l10n_hr_jir, JIR)
        # and a draft document may still be cancelled
        invoice.button_cancel()
        self.assertEqual(invoice.state, "cancel")

    def test_posted_invoice_with_zki_cannot_be_cancelled(self):
        """The guard still protects an issued document on both buttons."""
        invoice = self._invoice()
        invoice.write({"state": "posted", "l10n_hr_zki": ZKI, "l10n_hr_jir": JIR})
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            invoice.button_cancel()
        with self.assertRaises(ValidationError), self.env.cr.savepoint():
            invoice.button_draft()
        self.assertEqual(invoice.state, "posted")
