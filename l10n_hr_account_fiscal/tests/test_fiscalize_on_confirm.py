"""``enable_fiscalize_on_confirm`` decides what posting does.

On, posting calls the FINA service and stores the JIR. Off, posting leaves the
invoice unfiscalized: no ZKI, no service call, nothing queued for the cron.
The cron is a retry pass, not a queue - it only touches invoices whose
fiscalization was already attempted (a ZKI without a JIR).

These tests drive the posting flow against a fake FINA client, on the shared
Croatian fixture: journal -> premise -> device, so the fiscal number, issue
time and operator are the production ones.
"""
from unittest.mock import patch

from odoo.tests import tagged

from odoo.addons.l10n_hr_account_base.tests.common import L10nHrAccountTestCommon

from ..fiscal import fiscal as fiscal_module
from .test_fiscal_operation import FakeFiscalization, _ns

COMPANY_OIB = "12345678903"  # checksum-valid: the company is Croatian, the OIB is verified
OPERATOR_OIB = "69435151530"
JIR = "1" * 32


class FakeRacuniFiscalization(FakeFiscalization):
    """The fake FINA client, also answering racuni."""

    def __init__(self, data=None, **other):
        super().__init__(data, **other)
        self.client.service["racuni"] = "racuni"
        # fiscalize() reads fisk.signer before calling generate_zki, which
        # these tests replace: the signer only has to exist
        self.signer = None


def _racuni_ok():
    return _ns(
        Zaglavlje=_ns(IdPoruke="resp-id", DatumVrijeme="01.01.2026T00:00:01"),
        Greske=None,
        Jir=JIR,
    )


@tagged("post_install", "-at_install")
class TestFiscalizeOnConfirm(L10nHrAccountTestCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.hr_company.write({"company_registry": COMPANY_OIB})
        # the fixture's bare sequence numbers "0001"; fiscalization needs the
        # three-part fiscal number (brOzn/oznPoslPr/oznNapUr) the production
        # sequence produces
        cls.premise.l10n_hr_sequence_id = cls.premise._create_sequence()
        cls.operator = cls.env["hr.employee"].sudo().create({
            "name": "Confirm operator", "company_id": cls.hr_company.id,
        })
        cls.operator.work_contact_id.company_registry = OPERATOR_OIB
        cls.customer = cls.env["res.partner"].create({"name": "Confirm customer"})

    def setUp(self):
        super().setUp()
        FakeFiscalization.responses = {"racuni": _racuni_ok()}
        FakeFiscalization.calls = []
        for patcher in (
            patch.object(fiscal_module, "Fiscalization", FakeRacuniFiscalization),
            # the ZKI is not what these tests are about
            patch.object(fiscal_module, "generate_zki", lambda zki_datalist, signer: "z" * 32),
            patch.object(type(self.hr_company), "get_fiscal_data",
                         lambda company: {"cert_vat": COMPANY_OIB}),
            patch.object(type(self.hr_company), "_get_fiscal_certificate", lambda company: True),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def _posted_invoice(self):
        invoice = self.init_invoice("out_invoice", partner=self.customer, products=self.product_a, taxes=[])
        invoice.l10n_hr_fiscal_operator_id = self.operator
        invoice.l10n_hr_payment_method = "G"
        invoice.action_post()
        return invoice

    def test_confirm_fiscalizes_when_enabled(self):
        self.fiscal_device.write({
            "fiscalization_active": True, "enable_fiscalize_on_confirm": True})
        invoice = self._posted_invoice()
        self.assertEqual(len(FakeFiscalization.calls), 1)
        self.assertEqual(FakeFiscalization.calls[0][0], "racuni")
        self.assertTrue(invoice.l10n_hr_zki)
        self.assertEqual(invoice.l10n_hr_jir, JIR)

    def test_confirm_leaves_invoice_alone_when_disabled(self):
        self.fiscal_device.write({
            "fiscalization_active": True, "enable_fiscalize_on_confirm": False})
        invoice = self._posted_invoice()
        self.assertEqual(invoice.state, "posted")
        self.assertFalse(FakeFiscalization.calls,
                         "FINA was called although fiscalization on posting is off")
        self.assertFalse(invoice.l10n_hr_zki)
        self.assertFalse(invoice.l10n_hr_jir)
        self.assertFalse(self.env["l10n_hr.fiscal.log"].search([
            ("res_model", "=", "account.move"), ("res_id", "=", invoice.id)]))

    def test_cron_retries_attempted_invoices_only(self):
        self.fiscal_device.write({
            "fiscalization_active": True, "enable_fiscalize_on_confirm": False,
            "enable_cron_fiscalization": True, "cron_fiscalization_delay_hours": 12,
        })
        untouched = self._posted_invoice()
        attempted = self._posted_invoice()
        # a fiscalization was attempted on the second invoice and never
        # confirmed: it carries a ZKI, and its issue time predates the delay
        attempted.l10n_hr_zki = "0" * 32
        attempted.l10n_hr_fiscal_time = "01.01.2026T00:00:00"
        self.env["account.move"].action_cron_batch_fiscalize()
        self.assertEqual(len(FakeFiscalization.calls), 1)
        self.assertFalse(untouched.l10n_hr_zki)
        self.assertFalse(untouched.l10n_hr_jir)
        self.assertEqual(attempted.l10n_hr_jir, JIR)
