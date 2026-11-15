"""Credit-note device validation uses the Odoo 19 display-name API."""

from odoo.tests import tagged

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("post_install", "-at_install")
class TestFiscalRefundCompatibility(AccountTestInvoicingCommon):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Refund compatibility premise",
            "l10n_hr_fiscal_code": "REFCOMP",
            "company_id": cls.env.company.id,
        })
        cls.original_device, cls.refund_device = cls.env["l10n_hr.fiscal.device"].create([
            {
                "l10n_hr_name": name,
                "l10n_hr_fiscal_device_code": code,
                "l10n_hr_business_premise_id": premise.id,
                # Skip certificate/operator checks; no fiscalization is requested.
                "fiscalization_active": False,
            }
            for code, name in ((1, "Original device"), (2, "Refund device"))
        ])
        cls.original = cls.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": cls.partner_a.id,
            "l10n_hr_fiscal_device_id": cls.original_device.id,
            "l10n_hr_payment_method": "G",
        })
        cls.refund = cls.env["account.move"].create({
            "move_type": "out_refund",
            "partner_id": cls.partner_a.id,
            "reversed_entry_id": cls.original.id,
            "l10n_hr_fiscal_device_id": cls.refund_device.id,
            "l10n_hr_payment_method": "G",
        })

    def test_different_device_returns_original_device_message(self):
        """A mismatch returns a useful message, not a removed-name_get error."""
        messages = self.refund.with_context(lang="en_US")._l10n_hr_post_fiscal_check()

        self.assertEqual(len(messages), 1)
        self.assertIn("Fiscal Device on origin invoice %s" % self.original.name, messages[0])
        self.assertIn(
            "Please change Fiscal Device to the %s" % self.original_device.display_name,
            messages[0],
        )
        self.assertNotIn(self.refund_device.display_name, messages[0])

    def test_same_device_returns_no_errors(self):
        """A linked credit note on the original device needs no correction."""
        self.refund.l10n_hr_fiscal_device_id = self.original_device

        self.assertEqual(self.refund._l10n_hr_post_fiscal_check(), [])
