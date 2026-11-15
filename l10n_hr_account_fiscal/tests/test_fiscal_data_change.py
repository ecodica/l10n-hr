"""Changing the customer and payment method of a fiscalized invoice (promijeniPodatkeRacuna).

FINA lets the issuer change only the payment method and the recipient's OIB, and only
until midnight of the day the receipt was issued. The request repeats the receipt as it
was issued and carries the whole new state; nothing changes on the invoice unless FINA
confirms with p005. These tests drive the change against a fake FINA client.
"""
from unittest.mock import patch

from requests.exceptions import ConnectionError as RequestsConnectionError

from odoo.exceptions import AccessError, MissingError, UserError
from odoo.tests import new_test_user, tagged

from odoo import Command, fields
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..fiscal import fiscal as fiscal_module
from .test_fiscal_operation import FakeFiscalization, _error_response, _ns

JIR = "1" * 32
COMPANY_OIB = "12345678901"
CUSTOMER_OIB = "12345678903"
OTHER_OIB = "12345678911"
MSG_TYPE = "promijeniPodatkeRacuna"


class FakeChangeFiscalization(FakeFiscalization):
    """The fake FINA client, also answering promijeniPodatkeRacuna."""

    def __init__(self, data=None, **other):
        super().__init__(data, **other)
        self.client.service[MSG_TYPE] = MSG_TYPE


def _confirmed():
    """Return FINA's p005 reply: the change of fiscal data is registered."""
    return _ns(
        Zaglavlje=_ns(IdPoruke="resp-id", DatumVrijeme="01.01.2026T00:00:01"),
        Greske=None,
        PorukaOdgovora=_ns(SifraPoruke="p005", Poruka="Uspješna prijava promjene podataka računa."),
    )


@tagged("post_install", "-at_install")
class TestFiscalDataChange(AccountTestInvoicingCommon):
    """A fiscalized invoice changes its customer and payment method with FINA."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env.company
        cls.company.write({"company_registry": COMPANY_OIB, "l10n_hr_fiscal_silent_error_logging": False})
        premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "Change premise",
            "l10n_hr_fiscal_code": "CHG1",
            "company_id": cls.company.id,
        })
        cls.device = cls.env["l10n_hr.fiscal.device"].create({
            "l10n_hr_name": "Change device",
            "l10n_hr_fiscal_device_code": 1,
            "l10n_hr_business_premise_id": premise.id,
            "fiscalization_active": True,
        })
        Partner = cls.env["res.partner"]
        cls.private = Partner.create({"name": "Ana Kupac"})
        cls.customer = Partner.create({"name": "Kupac d.o.o.", "is_company": True, "company_registry": CUSTOMER_OIB})
        cls.other = Partner.create({"name": "Drugi d.o.o.", "is_company": True, "company_registry": OTHER_OIB})

    def setUp(self):
        super().setUp()
        FakeChangeFiscalization.responses = {MSG_TYPE: _confirmed()}
        FakeChangeFiscalization.calls = []
        for patcher in (
            patch.object(fiscal_module, "Fiscalization", FakeChangeFiscalization),
            patch.object(type(self.company), "get_fiscal_data", lambda company: {"cert_vat": COMPANY_OIB}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    # ------------------------------------------------------------------ helpers

    def _issued(self, partner=None, payment_method="G", amount=100.0, issued=None, move_type="out_invoice"):
        """Return a posted invoice FINA acknowledged, issued today unless ``issued`` says otherwise."""
        invoice = self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": (partner or self.private).id,
            "l10n_hr_payment_method": payment_method,
            "invoice_date": fields.Date.today(),
            "invoice_line_ids": [Command.create({
                "name": "Sale",
                "quantity": 1.0,
                "price_unit": amount,
                "tax_ids": [Command.clear()],
            })],
        })
        invoice.action_post()
        invoice.write({
            "l10n_hr_fiscal_device_id": self.device.id,
            "l10n_hr_fiscal_number": "1/CHG1/1",
            "l10n_hr_fiscal_time": issued or self.company.get_l10n_hr_time_formatted()["datum_vrijeme"],
            "l10n_hr_zki": "e4d909c290d0fb1ca068ffaddf22cbd0",
            "l10n_hr_jir": JIR,
        })
        return invoice

    def _sent(self):
        """Return the ``Racun`` of the last change request sent to FINA."""
        self.assertTrue(FakeChangeFiscalization.calls, "nothing was sent to FINA")
        service, req_kw = FakeChangeFiscalization.calls[-1]
        self.assertEqual(service, MSG_TYPE)
        return req_kw["Racun"]

    def _wizard(self, document, **vals):
        """Open the change wizard on ``document`` the way its button does."""
        action = document.button_fiscalize_change()
        Wizard = self.env[action["res_model"]].with_context(**action["context"])
        return Wizard.create(vals)

    # ------------------------------------------------------------------ the change

    def test_private_customer_becomes_r1(self):
        """A cash receipt issued to a person is reported again with the company's OIB.

        The customer's own payment term and fiscal position are not taken over: the
        invoice is already issued.
        """
        invoice = self._issued()
        fiscal_position = invoice.fiscal_position_id
        payment_term = invoice.invoice_payment_term_id
        self.customer.write({
            "property_payment_term_id": self.pay_terms_b.id,
            "property_account_position_id": self.env["account.fiscal.position"].create({"name": "Other FP"}).id,
        })

        self.assertFalse(invoice._l10n_hr_change_fiscal_data(self.customer, "G"))

        racun = self._sent()
        self.assertIsNone(racun.OibPrimateljaRacuna, "the receipt was issued without a recipient")
        self.assertEqual(racun.NacinPlac, "G")
        self.assertEqual(racun.PromijenjeniNacinPlac, "G")
        self.assertEqual(racun.PromijenjeniOibPrimateljaRacuna, CUSTOMER_OIB)
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(set(invoice.line_ids.partner_id.ids), {self.customer.id})
        self.assertEqual(invoice.fiscal_position_id, fiscal_position)
        self.assertEqual(invoice.invoice_payment_term_id, payment_term)
        self.assertEqual(invoice.l10n_hr_fiscal_orig_payment_method, "G")
        self.assertFalse(invoice.l10n_hr_fiscal_orig_partner_oib)
        note = invoice.message_ids.filtered(lambda message: "p005" in message.body)
        self.assertEqual(len(note), 1)
        self.assertIn(CUSTOMER_OIB, note.body)
        log = invoice.l10n_hr_fiscal_log_ids.filtered(lambda line: line.type == MSG_TYPE)
        self.assertEqual(log.error_msg, "OK")

    def test_r1_back_to_private_sends_an_empty_oib(self):
        """Removing the recipient sends the mandatory element empty, not leaves it out."""
        invoice = self._issued(partner=self.customer, payment_method="K")

        self.assertFalse(invoice._l10n_hr_change_fiscal_data(self.private, "K"))

        racun = self._sent()
        self.assertEqual(racun.OibPrimateljaRacuna, CUSTOMER_OIB)
        self.assertEqual(racun.PromijenjeniOibPrimateljaRacuna, "")
        self.assertEqual(invoice.partner_id, self.private)
        self.assertEqual(invoice.l10n_hr_fiscal_orig_partner_oib, CUSTOMER_OIB)

    def test_contact_of_a_company_reports_the_company(self):
        """An invoice addressed to a company's contact is reported with the company's OIB."""
        contact = self.env["res.partner"].create({"name": "Ivo Nabava", "parent_id": self.customer.id})
        invoice = self._issued()

        self.assertFalse(invoice._l10n_hr_change_fiscal_data(contact, "G"))

        self.assertEqual(self._sent().PromijenjeniOibPrimateljaRacuna, CUSTOMER_OIB)
        self.assertEqual(invoice.partner_id, contact)

    def test_second_change_repeats_the_receipt_as_issued(self):
        """``Racun`` keeps the original data after a first change, or FINA answers s012."""
        invoice = self._issued()
        invoice._l10n_hr_change_fiscal_data(self.customer, "G")

        self.assertFalse(invoice._l10n_hr_change_fiscal_data(self.other, "K"))

        racun = self._sent()
        self.assertEqual(racun.NacinPlac, "G")
        self.assertIsNone(racun.OibPrimateljaRacuna)
        self.assertEqual(racun.PromijenjeniNacinPlac, "K")
        self.assertEqual(racun.PromijenjeniOibPrimateljaRacuna, OTHER_OIB)
        self.assertEqual((invoice.partner_id, invoice.l10n_hr_payment_method), (self.other, "K"))
        self.assertEqual(invoice.l10n_hr_fiscal_orig_payment_method, "G", "the original is recorded once")

    # ------------------------------------------------------------------ FINA does not confirm

    def test_refusal_changes_nothing_and_keeps_the_log(self):
        """A FINA error leaves the invoice as issued and reports why; the attempt is logged."""
        FakeChangeFiscalization.responses[MSG_TYPE] = _error_response("s012", "Podaci se razlikuju.")
        invoice = self._issued()

        failure = invoice._l10n_hr_change_fiscal_data(self.customer, "G")

        self.assertIn("Podaci se razlikuju.", failure)
        self.assertEqual(invoice.partner_id, self.private)
        self.assertFalse(invoice.l10n_hr_fiscal_orig_payment_method)
        log = invoice.l10n_hr_fiscal_log_ids.filtered(lambda line: line.type == MSG_TYPE)
        self.assertIn("s012", log.error_msg)

    def test_refusal_with_silent_error_logging(self):
        """With silent error logging nothing is raised, and the log still says why."""
        self.company.l10n_hr_fiscal_silent_error_logging = True
        FakeChangeFiscalization.responses[MSG_TYPE] = _error_response("s011", "Datum nije jednak.")
        invoice = self._issued()

        failure = invoice._l10n_hr_change_fiscal_data(self.customer, "G")

        self.assertIn("s011", failure)
        self.assertEqual(invoice.partner_id, self.private)

    def test_lost_reply_changes_nothing(self):
        """Without a reply the change is not made, and the error is logged."""
        self.company.l10n_hr_fiscal_silent_error_logging = True
        FakeChangeFiscalization.responses[MSG_TYPE] = RequestsConnectionError("no route to FINA")
        invoice = self._issued()

        failure = invoice._l10n_hr_change_fiscal_data(self.customer, "G")

        self.assertIn("no route to FINA", failure)
        self.assertEqual(invoice.partner_id, self.private)
        log = invoice.l10n_hr_fiscal_log_ids.filtered(lambda line: line.type == MSG_TYPE)
        self.assertIn("no route to FINA", log.error_msg)

    def test_failed_write_after_confirmation_keeps_the_log(self):
        """FINA holds a change Odoo then fails to write: its log outlives the rollback."""
        invoice = self._issued()
        kept = []

        with (
            patch.object(type(invoice), "_l10n_hr_write_fiscal_change", side_effect=UserError("write refused")),
            patch.object(type(invoice), "_l10n_hr_keep_fiscal_log", side_effect=kept.append),
            self.assertRaisesRegex(UserError, "write refused"),
            self.env.cr.savepoint(),
        ):
            invoice._l10n_hr_change_fiscal_data(self.customer, "G")

        self.assertEqual(len(kept), 1)
        self.assertEqual((kept[0]["type"], kept[0]["res_id"]), (MSG_TYPE, invoice.id))
        self.assertIn("could not be updated: write refused", kept[0]["error_msg"])

    # ------------------------------------------------------------------ refused before sending

    def _refused(self, invoice, partner, payment_method, message):
        """Assert the change is refused with ``message`` and nothing is sent."""
        with self.assertRaisesRegex(UserError, message), self.env.cr.savepoint():
            invoice._l10n_hr_change_fiscal_data(partner, payment_method)
        self.assertFalse(FakeChangeFiscalization.calls)

    def test_error_before_sending_is_raised(self):
        """An error before the request went out is raised, not shown as a FINA refusal."""
        invoice = self._issued()
        with patch.object(type(self.company), "get_fiscal_data",
                          side_effect=MissingError("Fiscal Certificate not found!")):
            self._refused(invoice, self.customer, "G", "Fiscal Certificate not found")
        self.assertFalse(invoice.l10n_hr_fiscal_log_ids.filtered(lambda line: line.type == MSG_TYPE))

    def test_refused_draft_and_vendor_bill(self):
        """Only a posted customer invoice or credit note changes its fiscal data."""
        invoice = self._issued()
        invoice.button_draft()
        self.assertFalse(invoice.l10n_hr_fiscal_change_allowed)
        self._refused(invoice, self.customer, "G", "Only a posted customer invoice")

        bill = self._issued(move_type="in_invoice")
        self._refused(bill, self.customer, "G", "Only a posted customer invoice")

    def test_refused_in_a_locked_period(self):
        """A locked period refuses the new customer on the journal items, so it is not sent."""
        invoice = self._issued()
        self.company.fiscalyear_lock_date = fields.Date.today()
        self.assertFalse(invoice.l10n_hr_fiscal_change_allowed)
        self._refused(invoice, self.customer, "G", "prior to and inclusive of")

    def test_refused_partner_of_another_company(self):
        """A customer of another company would fail the write after FINA confirmed."""
        other_company = self.env["res.company"].create({"name": "Other company"})
        stranger = self.env["res.partner"].create({"name": "Strani d.o.o.", "company_id": other_company.id})
        self._refused(self._issued(), stranger, "G", "belongs to another company")

    def test_refused_after_midnight(self):
        """The day after issue FINA refuses the change (s011), so it is not offered."""
        invoice = self._issued(issued="01.01.2026T10:00:00")
        self.assertFalse(invoice.l10n_hr_fiscal_change_allowed)
        self._refused(invoice, self.customer, "G", "until midnight")

    def test_refused_r1_paid_by_transfer(self):
        """A company recipient cannot be reported with a bank transfer (error 181)."""
        self._refused(self._issued(), self.customer, "T", "R1 invoice cannot be fiscalized with T")

    def test_refused_r1_without_oib(self):
        """A company recipient needs an OIB."""
        no_oib = self.env["res.partner"].create({"name": "Bez OIB-a d.o.o.", "is_company": True})
        self._refused(self._issued(), no_oib, "G", "an OIB must be set")

    def test_refused_r1_cash_over_700(self):
        """A company cannot pay more than 700,00 € in cash."""
        self._refused(self._issued(amount=800.0), self.customer, "G", "bigger than 700,00")

    def test_refused_without_a_change(self):
        """Sending the same data again is refused."""
        self._refused(self._issued(), self.private, "G", "Nothing to change")

    def test_refused_without_jir(self):
        """A document FINA never acknowledged cannot be changed."""
        invoice = self._issued()
        invoice.l10n_hr_jir = False
        self.assertFalse(invoice.l10n_hr_fiscal_change_allowed)
        self._refused(invoice, self.customer, "G", "no JIR")

    def test_refused_with_another_receivable_account(self):
        """A customer whose receivable account differs would move the receivable."""
        self.customer.property_account_receivable_id = self.env["account.account"].create({
            "name": "Other receivable",
            "code": "121099",
            "account_type": "asset_receivable",
            "reconcile": True,
        })
        self._refused(self._issued(), self.customer, "G", "receivable account")

    def test_wizard_needs_invoicing_rights(self):
        """Only an invoicing user may open the change wizard."""
        employee = new_test_user(self.env, login="no_invoicing", groups="base.group_user")
        with self.assertRaises(AccessError):
            self.env["l10n_hr.change.fiscal.data"].with_user(employee).create({})

    # ------------------------------------------------------------------ payments and the wizard

    def _pay_by_hand(self, invoice):
        """Reconcile ``invoice`` with a journal entry booked by hand, and return the entry."""
        receivable = invoice.line_ids.filtered(lambda line: line.display_type == "payment_term")
        entry = self.env["account.move"].create({
            "move_type": "entry",
            "line_ids": [
                Command.create({
                    "account_id": receivable.account_id.id,
                    "partner_id": invoice.commercial_partner_id.id,
                    "credit": invoice.amount_total,
                }),
                Command.create({
                    "account_id": self.company_data["default_journal_bank"].default_account_id.id,
                    "debit": invoice.amount_total,
                }),
            ],
        })
        entry.action_post()
        (receivable | entry.line_ids.filtered(lambda line: line.account_id == receivable.account_id)).reconcile()
        return entry

    def test_payment_by_hand_keeps_its_customer(self):
        """A payment booked by hand stays with the old customer, and the wizard says so."""
        invoice = self._issued()
        entry = self._pay_by_hand(invoice)
        self.assertFalse(invoice.amount_residual)

        wizard = self._wizard(invoice, partner_id=self.customer.id)
        self.assertIn(entry.display_name, wizard.warning)
        self.assertEqual(wizard.recipient_oib, CUSTOMER_OIB)

        action = wizard.change()

        self.assertEqual(action["params"]["type"], "success")
        self.assertEqual(invoice.partner_id, self.customer)
        self.assertEqual(entry.line_ids.partner_id, self.private)
        self.assertFalse(invoice.amount_residual, "the reconciliation stays")

    def test_unverified_confirmation_does_not_change_the_customer(self):
        original_call = FakeChangeFiscalization._call_service

        def unverified(client, service_proxy, req_kw):
            response = original_call(client, service_proxy, req_kw)
            client.fiscal_plugin.last_verification_ok = False
            return response

        for silent in (False, True):
            with self.subTest(silent=silent):
                self.company.l10n_hr_fiscal_silent_error_logging = silent
                invoice = self._issued()
                with patch.object(FakeChangeFiscalization, '_call_service', unverified):
                    failure = invoice._l10n_hr_change_fiscal_data(self.customer, 'G')
                self.assertTrue(failure)
                self.assertEqual(invoice.partner_id, self.private)
                log = invoice._l10n_hr_last_fiscal_log(MSG_TYPE)
                self.assertEqual(log.exchange_outcome, 'uncertain')
                self.assertIn('signature', log.error_msg)
                self.assertTrue(log.reply_msg)

    def test_wizard_reports_a_refusal(self):
        """The wizard shows FINA's refusal instead of raising it, so the log is kept."""
        FakeChangeFiscalization.responses[MSG_TYPE] = _error_response("s012", "Podaci se razlikuju.")
        invoice = self._issued()
        wizard = self._wizard(invoice, partner_id=self.customer.id)
        self.assertEqual((wizard.current_partner_id, wizard.current_payment_method), (self.private, "G"))

        action = wizard.change()

        self.assertEqual(action["params"]["type"], "danger")
        self.assertIn("Podaci se razlikuju.", action["params"]["message"])
        self.assertEqual(invoice.partner_id, self.private)

    def test_wizard_keeps_the_payment_method(self):
        """The wizard changes only the customer; the payment method is reported as it is."""
        invoice = self._issued(payment_method="K")
        wizard = self._wizard(invoice, partner_id=self.customer.id)

        self.assertEqual(wizard.change()["params"]["type"], "success")

        self.assertEqual(self._sent().PromijenjeniNacinPlac, "K")
        self.assertEqual((invoice.partner_id, invoice.l10n_hr_payment_method), (self.customer, "K"))

    def test_post_check_keeps_its_messages(self):
        """Fiscalization still refuses the R1 cases it refused before."""
        invoice = self._issued(partner=self.customer, payment_method="T")
        errors = invoice._l10n_hr_post_fiscal_check()
        self.assertIn("R1 invoice cannot be fiscalized with T payment type", errors)
