"""Outside Croatia the fiscalization modules must leave an invoice alone.

The test company runs the generic chart with a US fiscal country. Its invoices
post as in plain Odoo: no fiscal device, number, ZKI or FINA call. The same
invoice is refused once the company's fiscal country is Croatia, which proves the
country guard is what lets it through.
"""
from unittest.mock import patch

from odoo.exceptions import ValidationError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

FISCALIZE = "odoo.addons.l10n_hr_account_fiscal.models.l10n_hr_fiscal_v1_mixin.L10nHrFiscalV1Mixin.fiscalize"


@tagged("post_install", "-at_install")
class TestCountryGuard(AccountTestInvoicingCommon):

    def _invoice(self, move_type="out_invoice", taxes=None):
        return self.init_invoice(move_type, products=self.product_a, taxes=taxes)

    def test_non_croatian_invoice_posts_untouched(self):
        self.assertNotEqual(self.company_data["company"].account_fiscal_country_id.code, "HR")
        invoice = self._invoice()
        with patch(FISCALIZE) as fiscalize:
            invoice.action_post()
        fiscalize.assert_not_called()
        self.assertEqual(invoice.state, "posted")
        self.assertFalse(invoice.l10n_hr_fiscal_device_id)
        self.assertFalse(invoice.l10n_hr_fiscal_number)
        self.assertFalse(invoice.l10n_hr_zki)
        self.assertFalse(invoice.l10n_hr_fiscal_time)
        self.assertFalse(invoice.l10n_hr_fiscal_check_allowed)

    def test_non_croatian_credit_note_posts_untouched(self):
        refund = self._invoice("out_refund")
        with patch(FISCALIZE) as fiscalize:
            refund.action_post()
        fiscalize.assert_not_called()
        self.assertEqual(refund.state, "posted")
        self.assertFalse(refund.l10n_hr_fiscal_number)

    def test_croatian_invoice_without_device_is_refused(self):
        # untaxed: the generic chart's taxes do not belong to the Croatian fiscal country
        invoice = self._invoice(taxes=[])
        self.company_data["company"].account_fiscal_country_id = self.env.ref("base.hr")
        with patch(FISCALIZE), self.assertRaises(ValidationError) as cm:
            invoice.with_context(lang="en_US").action_post()
        self.assertIn("No active PoS devices found for this journal.", str(cm.exception))

    def test_unfiscalized_counter_ignores_non_croatian_companies(self):
        self._invoice().action_post()
        self.assertEqual(self.env["account.move"].search_not_fiscalized_invoice_count(), {"count": 0})
