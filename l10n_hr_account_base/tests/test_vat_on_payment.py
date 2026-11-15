from odoo.tests import TransactionCase, tagged


@tagged("post_install", "-at_install")
class TestVatOnPayment(TransactionCase):

    def test_vat_on_payment_follows_tax_model(self):
        company = self.env["res.company"].create({"name": "HR VAT on payment"})
        self.assertEqual(company.l10n_hr_tax_model, "r1")
        self.assertFalse(company.l10n_hr_pdv_po_naplati)
        company.l10n_hr_tax_model = "r2"
        self.assertTrue(company.l10n_hr_pdv_po_naplati)
        company.l10n_hr_tax_model = "r0"
        self.assertFalse(company.l10n_hr_pdv_po_naplati)
        self.assertTrue(self.env["res.company"]._fields["l10n_hr_pdv_po_naplati"].readonly)
