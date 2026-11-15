"""The shared fixture is enough to number a Croatian invoice, and nothing else changes elsewhere."""
from psycopg2 import IntegrityError

from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.tools import mute_logger

from .common import L10nHrAccountTestCommon


@tagged("post_install", "-at_install")
class TestFiscalDeviceFixture(L10nHrAccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.eu_data = cls.setup_eu_company("SI")

    def test_croatian_invoice_gets_the_fixture_device(self):
        invoice = self.init_invoice("out_invoice", products=self.product_a, taxes=[])
        self.assertEqual(invoice.l10n_hr_fiscal_device_id, self.fiscal_device)
        self.assertEqual(invoice._l10n_hr_post_check(), [])
        self.assertTrue(invoice.l10n_hr_gen_fiscal_number())

    def test_croatian_journal_without_device_is_refused(self):
        journal = self.company_data["default_journal_sale"].copy({"name": "No device", "code": "NODEV"})
        journal.l10n_hr_business_premise_id = False
        invoice = self.init_invoice("out_invoice", products=self.product_a, taxes=[], journal=journal)
        self.assertFalse(invoice.l10n_hr_fiscal_device_id)
        self.assertIn("No active PoS devices found for this journal.",
                      invoice.with_context(lang="en_US")._l10n_hr_post_check())

    def test_eu_company_invoice_posts_without_fiscal_data(self):
        company = self.eu_data["company"]
        self.assertEqual(company.account_fiscal_country_id.code, "SI")
        invoice = self.init_invoice(
            "out_invoice", products=self.product_a, taxes=[], company=company, post=True)
        self.assertEqual(invoice.state, "posted")
        self.assertFalse(invoice.l10n_hr_allowed_fiscal_device_ids)
        self.assertFalse(invoice.l10n_hr_fiscal_device_id)
        self.assertFalse(invoice.l10n_hr_fiscal_number)

    def test_device_codes_are_unique_per_premise(self):
        with mute_logger("odoo.sql_db"), self.assertRaises(IntegrityError):
            self.env["l10n_hr.fiscal.device"].create({
                "l10n_hr_name": "Duplicate",
                "l10n_hr_business_premise_id": self.premise.id,
                "l10n_hr_fiscal_device_code": self.fiscal_device.l10n_hr_fiscal_device_code,
            })
            self.env.flush_all()

    def test_inactive_device_is_not_offered(self):
        self.fiscal_device.l10n_hr_state = "pause"
        invoice = self.init_invoice("out_invoice", products=self.product_a, taxes=[])
        self.assertFalse(invoice.l10n_hr_fiscal_device_id)
        with self.assertRaises(ValidationError) as cm:
            invoice.with_context(lang="en_US").action_post()
        self.assertIn("No active PoS devices found for this journal.", str(cm.exception))
