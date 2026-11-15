from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFiscalReport(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("hr")
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.company_data["company"]
        cls.invoice = cls.init_invoice("out_invoice", products=cls.product_a)

    def _render(self, move):
        # a customer report module may own the template selection; render the standard one under test
        with patch.object(
            self.env.registry["account.move"], "_get_name_invoice_report",
            lambda self: "account.report_invoice_document",
        ):
            html = self.env["ir.actions.report"]._render_qweb_html("account.account_invoices", move.ids)[0]
        return html.decode()

    def test_f1_receipt_prints_zki_jir_and_qr(self):
        self.invoice.write({
            "l10n_hr_zki": "a" * 32,
            "l10n_hr_jir": "b" * 36,
            "l10n_hr_fiscal_time": "01.01.2026T10:00:00",
        })
        html = self._render(self.invoice)
        self.assertIn('id="l10n_hr_fiscal_info"', html)
        self.assertIn("ZKI:", html)
        self.assertIn("a" * 32, html)
        self.assertIn("JIR:", html)
        self.assertIn("b" * 36, html)
        self.assertIn('id="l10n_hr_note"', html)
        self.assertIn("data:image/png;base64,", html)

    def test_non_fiscalized_invoice_prints_no_fiscal_labels(self):
        html = self._render(self.invoice)
        self.assertNotIn('id="l10n_hr_fiscal_info"', html)
        self.assertNotIn("ZKI:", html)
        self.assertNotIn("JIR:", html)
        self.assertNotIn('id="l10n_hr_note"', html)

    def test_tax_groups_hidden_outside_croatian_taxation(self):
        self.assertIn("o_taxes", self._render(self.invoice))
        self.company.l10n_hr_tax_model = "r0"
        self.invoice.invalidate_recordset(["tax_totals"])
        self.assertNotIn("o_taxes", self._render(self.invoice))
