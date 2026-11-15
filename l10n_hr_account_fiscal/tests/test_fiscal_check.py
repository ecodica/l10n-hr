"""The fiscal check (``provjera``) exists in the FINA test environment only."""
from unittest.mock import patch

from odoo.exceptions import UserError
from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon

FISCALIZE = "odoo.addons.l10n_hr_account_fiscal.models.l10n_hr_fiscal_v1_mixin.L10nHrFiscalV1Mixin.fiscalize"


@tagged("post_install", "-at_install")
class TestFiscalCheck(AccountTestInvoicingCommon):

    @classmethod
    @AccountTestInvoicingCommon.setup_country("hr")
    def setUpClass(cls):
        super().setUpClass()
        cls.invoice = cls.init_invoice("out_invoice", products=cls.product_a)
        cls.invoice.write({"l10n_hr_jir": "b" * 36})

    def test_check_offered_and_sent_in_test_environment(self):
        self.company_data["company"].l10n_hr_fiscal_test_env = True
        self.assertTrue(self.invoice.l10n_hr_fiscal_check_allowed)
        with patch(FISCALIZE) as fiscalize:
            self.invoice.button_fiscalize_check()
        fiscalize.assert_called_once()
        self.assertEqual(fiscalize.call_args.kwargs["msg_type"], "provjera")

    def test_check_hidden_and_refused_in_production(self):
        self.company_data["company"].l10n_hr_fiscal_test_env = False
        self.assertFalse(self.invoice.l10n_hr_fiscal_check_allowed)
        with patch(FISCALIZE) as fiscalize, self.assertRaises(UserError):
            self.invoice.button_fiscalize_check()
        fiscalize.assert_not_called()

    def test_check_hidden_without_jir(self):
        self.company_data["company"].l10n_hr_fiscal_test_env = True
        self.invoice.l10n_hr_jir = False
        self.assertFalse(self.invoice.l10n_hr_fiscal_check_allowed)
