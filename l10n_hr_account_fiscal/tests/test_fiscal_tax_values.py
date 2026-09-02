"""
Amounts in the Fiskalizacija 1.0 message, and the guard that checks them.

Two invariants hold for an ordinary invoice and for a credit note alike, and
most of these tests are one facet of them:

    sum(Pdv.Osnovica) + sum(Pdv.Iznos) + sum(Pnp.Iznos) == IznosUkupno
    ZKI payload amount == IznosUkupno == QR 'izn'

Both matter beyond the message being well-formed. CIS does not recompute the
ZKI, so an inconsistent message is accepted silently; it surfaces during a
Porezna uprava inspection, where the ZKI is recomputed from the printed invoice
plus the taxpayer certificate, and where the QR is what gets scanned.

What is covered:

Signs        Every fiscal amount is signed by document direction - positive on
             an ``out_invoice``, negative on an ``out_refund`` - and the tax
             breakdown adds up to the total in both directions.

Currency     Every amount in the message is in *company* currency, including
             the ZKI payload and the QR, so a foreign-currency invoice reports
             the converted amount rather than its own.

One amount   The ZKI payload, ``IznosUkupno`` and the QR ``izn`` are the same
             number, asserted against each other rather than each against a
             constant, so they cannot drift apart.

Exemptions   Bases with no VAT (``IznosOslobPdv``, ``IznosNePodlOpor``,
             ``IznosMarza``) are reported outside the ``Pdv`` breakdown and
             still count towards the total.

Validation   ``_validate_fiscal_invoice()`` accepts a coherent message - in
             company and foreign currency, with and without exempt bases - and
             rejects an inverted base, an understated base and a tax amount
             that does not follow from its base, so a bad payload cannot leave
             the system.

Endpoints    Each bundled WSDL points at the endpoint its directory name
             promises: a ``PROD_*`` schema at the production service, the rest
             at the test service.

Batching     ``fiscalize()`` reports whether it fiscalized anything, the batch
             counters reflect that, a database error on one record is contained
             by its savepoint and logged instead of aborting the batch.

Counter      The systray count is scoped to the session's enabled companies and
             takes no arguments, since it is callable from the browser.

Naknade      A tax of fiscal type ``Naknade`` reports its own name and amount
             rather than the literal strings ``NazivN``/``IznosN``.
"""
import re
from types import SimpleNamespace
from unittest.mock import patch

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon


def _racun_stub(osnovica, iznos, iznos_ukupno, u_sust_pdv=True, **extra):
    """Minimal stand-in for the zeep ``RacunType`` object.

    ``_validate_fiscal_invoice`` only reads attributes off it, so a namespace is
    enough - this keeps the validator tests free of the WSDL/zeep stack, and
    lets them feed in payloads the builder would never produce.
    """
    values = {
        "USustPdv": u_sust_pdv,
        "IznosUkupno": "%.2f" % iznos_ukupno,
        "Pdv": SimpleNamespace(Porez=[
            SimpleNamespace(
                Stopa="25.00",
                Osnovica="%.2f" % osnovica,
                Iznos="%.2f" % iznos,
            ),
        ]),
        "Pnp": None,
        "IznosOslobPdv": None,
        "IznosNePodlOpor": None,
        "IznosMarza": None,
    }
    values.update(extra)
    return SimpleNamespace(**values)


@tagged("post_install", "-at_install", "l10n_hr", "l10n_hr_account_fiscal")
class TestFiscalTaxValues(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].l10n_hr_tax_model = "r1"
        cls.tax_pdv_25 = cls.env["account.tax"].create({
            "name": "PDV 25% (fiscal test)",
            "amount_type": "percent",
            "amount": 25.0,
            "type_tax_use": "sale",
            "l10n_hr_fiscal_type": "Pdv",
            "company_id": cls.company_data["company"].id,
        })
        cls.tax_exempt = cls.env["account.tax"].create({
            "name": "Oslobodjeno PDV-a (fiscal test)",
            "amount_type": "percent",
            "amount": 0.0,
            "type_tax_use": "sale",
            "l10n_hr_fiscal_type": "oslobodenje",
            "company_id": cls.company_data["company"].id,
        })
        # rate 2.0 from 2017-01-01: 1 company currency == 2 foreign, so a
        # 1000 + 25% foreign invoice is 625.00 in company currency.
        cls.foreign_currency = cls.setup_other_currency("HRK")
        assert cls.foreign_currency != cls.company_data["currency"], (
            "the currency tests are meaningless unless this really is a "
            "currency other than the company's"
        )

    def _create_hr_invoice(self, move_type="out_invoice", lines=None, currency=None):
        lines = lines or [(1000.0, self.tax_pdv_25)]
        return self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "invoice_date": "2026-08-03",
            "date": "2026-08-03",
            "currency_id": (currency or self.company_data["currency"]).id,
            "invoice_line_ids": [
                Command.create({
                    "name": "fiscal test line %s" % index,
                    "quantity": 1.0,
                    "price_unit": price_unit,
                    "tax_ids": [Command.set(tax.ids)],
                })
                for index, (price_unit, tax) in enumerate(lines)
            ],
        })

    def _refund_of(self, invoice):
        """Post an invoice and return its credit note.

        The reversal runs as superuser. Building it deletes and recreates tax
        journal items, and unlink on account.move.line is gated by record rules
        that depend on which modules are installed: with `purchase` present the
        accounting test user inherits Purchase / Administrator, whose rule
        narrows account.move.line to vendor bills, so removing a customer
        invoice tax line is denied. These tests are about fiscal amounts, not
        about access rights.
        """
        invoice.action_post()
        return invoice.sudo()._reverse_moves()

    # -- sign of the taxable base ---------------------------------------------

    def test_osnovica_positive_on_out_invoice(self):
        """An ordinary customer invoice must report a positive taxable base."""
        invoice = self._create_hr_invoice("out_invoice")
        tax_data = invoice._get_fisc_tax_values()

        self.assertEqual(list(tax_data["Pdv"]), [25.0])
        pdv = tax_data["Pdv"][25.0]
        self.assertAlmostEqual(pdv["Osnovica"], 1000.0, places=2)
        self.assertAlmostEqual(pdv["Iznos"], 250.0, places=2)
        self.assertEqual(invoice._prepare_fiscal_invoice_total(), "1250.00")

    def test_osnovica_negative_on_out_refund(self):
        """A credit note keeps base, tax and total all negative."""
        refund = self._refund_of(self._create_hr_invoice("out_invoice"))
        tax_data = refund._get_fisc_tax_values()

        pdv = tax_data["Pdv"][25.0]
        self.assertAlmostEqual(pdv["Osnovica"], -1000.0, places=2)
        self.assertAlmostEqual(pdv["Iznos"], -250.0, places=2)
        self.assertEqual(refund._prepare_fiscal_invoice_total(), "-1250.00")

    def test_osnovica_plus_iznos_equals_iznos_ukupno(self):
        """The tax breakdown must add up to the submitted total."""
        invoice = self._create_hr_invoice("out_invoice")
        refund = self._refund_of(invoice)

        for move in (invoice, refund):
            tax_data = move._get_fisc_tax_values()
            total = sum(
                rate_data["Osnovica"] + rate_data["Iznos"]
                for rate_data in tax_data["Pdv"].values()
            )
            self.assertAlmostEqual(
                total,
                float(move._prepare_fiscal_invoice_total()),
                places=2,
                msg="Osnovica + Iznos must equal IznosUkupno for %s" % move.move_type,
            )

    def test_exempt_base_is_reported_separately(self):
        """Exempt lines land in IznosOslobPdv, outside the Pdv breakdown."""
        invoice = self._create_hr_invoice("out_invoice", lines=[
            (1000.0, self.tax_pdv_25),
            (200.0, self.tax_exempt),
        ])
        tax_data = invoice._get_fisc_tax_values()

        self.assertAlmostEqual(tax_data["Pdv"][25.0]["Osnovica"], 1000.0, places=2)
        self.assertEqual(tax_data.get("IznosOslobPdv"), "200.00")
        self.assertEqual(invoice._prepare_fiscal_invoice_total(), "1450.00")

    # -- every WSDL points at the endpoint its name promises -------------------

    def test_every_prod_wsdl_points_at_the_production_endpoint(self):
        """A PROD schema must address the production service, and only it.

        The bundled WSDLs are third-party files, so this walks all of them
        rather than the one that is currently in use: a schema whose directory
        says PROD while its ``soap:address`` says otherwise would send live
        invoices to the test service and return unusable JIRs.
        """
        import glob
        import os
        from odoo.modules.module import get_module_path

        schema_root = os.path.join(
            get_module_path("l10n_hr_account_fiscal"), "fiscal", "schema")
        wsdls = glob.glob(os.path.join(
            schema_root, "Fiskalizacija-WSDL-*", "wsdl", "FiskalizacijaService.wsdl"))
        self.assertTrue(wsdls, "no WSDLs found under %s" % schema_root)

        for wsdl in wsdls:
            with open(wsdl) as wsdl_file:
                content = wsdl_file.read()
            is_prod = "WSDL-PROD_" in wsdl
            expected = (
                "https://cis.porezna-uprava.hr:8449/FiskalizacijaService"
                if is_prod
                else "https://cistest.apis-it.hr:8449/FiskalizacijaServiceTest"
            )
            self.assertIn(
                'soap:address location="%s"' % expected, content,
                "%s must point at the %s endpoint" % (
                    os.path.basename(os.path.dirname(os.path.dirname(wsdl))),
                    "production" if is_prod else "test",
                ),
            )

    # -- one canonical amount for ZKI, IznosUkupno and the QR ------------------

    def test_zki_amount_equals_iznos_ukupno(self):
        """The ZKI must be signed over the amount that is submitted."""
        invoice = self._create_hr_invoice("out_invoice")
        self.assertEqual(invoice._get_fiscal_amount_formatted(), "1250.00")
        self.assertEqual(
            invoice._get_fiscal_amount_formatted(),
            invoice._prepare_fiscal_invoice_total(),
        )

    def test_zki_amount_is_negative_on_a_credit_note(self):
        """A storno signs the negative amount, in step with IznosUkupno."""
        refund = self._refund_of(self._create_hr_invoice("out_invoice"))
        self.assertEqual(refund._get_fiscal_amount_formatted(), "-1250.00")
        self.assertEqual(
            refund._get_fiscal_amount_formatted(),
            refund._prepare_fiscal_invoice_total(),
        )

    def test_zki_amount_is_in_company_currency(self):
        """A foreign-currency invoice signs its *company* currency total.

        1000 + 25% foreign at rate 2.0 is 1250.00 foreign but 625.00 in company
        currency, and 625.00 is what IznosUkupno carries.
        """
        invoice = self._create_hr_invoice(
            "out_invoice", currency=self.foreign_currency)
        self.assertEqual(invoice.currency_id, self.foreign_currency)
        self.assertAlmostEqual(invoice.amount_total, 1250.0, places=2)

        self.assertEqual(invoice._get_fiscal_amount_formatted(), "625.00")
        self.assertEqual(
            invoice._get_fiscal_amount_formatted(),
            invoice._prepare_fiscal_invoice_total(),
        )

    def test_iznos_ukupno_matches_the_payment_term_lines(self):
        """The submitted total must equal what the invoice actually books.

        The payment_term lines are the receivable, so their balance is an
        independent check on IznosUkupno: it is derived from the accounting
        entry rather than from the same field the message is built from.
        """
        for move_type, currency in (
            ("out_invoice", None),
            ("out_invoice", self.foreign_currency),
        ):
            invoice = self._create_hr_invoice(move_type, currency=currency)
            invoice.action_post()
            payment_term_total = sum(
                invoice.line_ids
                .filtered(lambda line: line.display_type == "payment_term")
                .mapped("balance")
            )
            self.assertAlmostEqual(
                float(invoice._prepare_fiscal_invoice_total()),
                payment_term_total,
                places=2,
                msg="IznosUkupno changed for %s in %s" % (
                    move_type, invoice.currency_id.name),
            )

    def test_qr_url_carries_the_company_currency_amount(self):
        """The QR 'izn' must be the fiscalized amount, in company currency."""
        invoice = self._create_hr_invoice(
            "out_invoice", currency=self.foreign_currency)
        invoice.l10n_hr_zki = "0" * 32
        invoice.l10n_hr_fiscal_time = "03.08.2026T14:35:00"

        url = invoice.generate_fiscal_url()
        self.assertIn("izn=62500", url)
        self.assertNotIn("izn=125000", url)

    def test_qr_url_amount_is_signed_for_a_credit_note(self):
        """A storno must advertise the negative amount it fiscalized.

        The QR is what a customer or an inspector scans to verify the invoice
        against the Tax Administration, so a positive 'izn' next to a negative
        ZKI and IznosUkupno would not resolve to the registered amount.
        """
        refund = self._refund_of(self._create_hr_invoice("out_invoice"))
        refund.l10n_hr_zki = "0" * 32
        refund.l10n_hr_fiscal_time = "03.08.2026T14:35:00"

        url = refund.generate_fiscal_url()
        self.assertIn("izn=-125000", url)

    def test_qr_url_amount_matches_the_zki_and_iznos_ukupno(self):
        """One canonical amount: ZKI payload == IznosUkupno == QR 'izn'.

        Asserted on the URL rather than on the field, so that a change to how
        `izn` is formatted still has to keep the three in step.
        """
        invoice = self._create_hr_invoice("out_invoice")
        refund = self._refund_of(invoice)

        for move, expected in ((invoice, "1250.00"), (refund, "-1250.00")):
            move.l10n_hr_zki = "0" * 32
            move.l10n_hr_fiscal_time = "03.08.2026T14:35:00"

            self.assertEqual(move._get_fiscal_amount_formatted(), expected)
            self.assertEqual(move._prepare_fiscal_invoice_total(), expected)

            izn = re.search(r"izn=(-?\d+)", move.generate_fiscal_url()).group(1)
            self.assertEqual(
                izn,
                expected.replace(".", ""),
                "QR izn must be the same amount as the ZKI payload and "
                "IznosUkupno for %s" % move.move_type,
            )

    # -- the pre-send guard accepts good payloads and rejects bad ones ---------

    def test_validator_accepts_consistent_invoice(self):
        invoice = self._create_hr_invoice("out_invoice")
        invoice._validate_fiscal_invoice(_racun_stub(1000.0, 250.0, 1250.0))

    def test_validator_accepts_consistent_refund(self):
        refund = self._refund_of(self._create_hr_invoice("out_invoice"))
        refund._validate_fiscal_invoice(_racun_stub(-1000.0, -250.0, -1250.0))

    def test_validator_rejects_inverted_osnovica(self):
        """A base whose sign contradicts the total must not leave the system."""
        invoice = self._create_hr_invoice("out_invoice")
        with self.assertRaises(ValidationError):
            invoice._validate_fiscal_invoice(_racun_stub(-1000.0, 250.0, 1250.0))

    def test_validator_rejects_understated_osnovica(self):
        """A base that does not match the Odoo untaxed amount must be caught.

        This is the shape a dropped base produces - two tax lines sharing a rate
        where only one of them ends up in the breakdown.
        """
        invoice = self._create_hr_invoice("out_invoice")
        with self.assertRaises(ValidationError):
            invoice._validate_fiscal_invoice(_racun_stub(800.0, 250.0, 1250.0))

    def test_validator_rejects_mismatched_tax_amount(self):
        invoice = self._create_hr_invoice("out_invoice")
        with self.assertRaises(ValidationError):
            invoice._validate_fiscal_invoice(_racun_stub(1000.0, 300.0, 1300.0))

    # -- fiscalize() reports its outcome, and a batch survives one failure -----

    def test_fiscalize_returns_falsy_when_not_needed(self):
        """No active fiscal device -> nothing was fiscalized, so falsy."""
        invoice = self._create_hr_invoice("out_invoice")
        invoice.action_post()
        self.assertFalse(invoice.fiscalize())

    def test_batch_fiscalize_counts_untouched_moves_as_skipped(self):
        """The batch counters must reflect the return value, not swallow it."""
        invoices = self.env["account.move"]
        for _index in range(2):
            invoice = self._create_hr_invoice("out_invoice")
            invoice.action_post()
            invoices |= invoice

        success, skipped, error = invoices._batch_fiscalize()
        self.assertEqual((success, skipped, error), (0, 2, 0))

    # -- the systray counter endpoint ------------------------------------------

    def test_counter_is_scoped_to_the_enabled_companies(self):
        """The endpoint is callable from the browser, so it must not trust it.

        The scope comes from env.companies - the companies enabled in the
        switcher, which the ORM validates - and the method takes no arguments,
        so there is nothing a client could pass to widen it.
        """
        other_company = self.setup_other_company()["company"]
        invoice = self._create_hr_invoice("out_invoice")
        invoice.action_post()
        invoice.l10n_hr_zki = "0" * 32

        Move = self.env["account.move"]
        self.assertEqual(
            Move.search_not_fiscalized_invoice_count(),
            {"count": 1},
            "the invoice's own company is enabled, so it must be counted",
        )
        self.assertEqual(
            Move.with_company(other_company)
                .with_context(allowed_company_ids=other_company.ids)
                .search_not_fiscalized_invoice_count(),
            {"count": 0},
            "switching to another company must exclude it",
        )
        with self.assertRaises(TypeError):
            Move.search_not_fiscalized_invoice_count(other_company.id)

    def test_batch_fiscalize_isolates_a_failing_record(self):
        """A DB error on one record must not poison the rest of the batch.

        A failed statement aborts the whole transaction in PostgreSQL, so
        without a per-record savepoint every *following* record fails too with
        "current transaction is aborted" - one bad invoice would be reported as
        a batch of failures. The three invoices here must come back as
        (2 fiscalized, 0 skipped, 1 failed).
        """
        invoices = self.env["account.move"]
        for _index in range(3):
            invoice = self._create_hr_invoice("out_invoice")
            invoice.action_post()
            invoices |= invoice
        failing_id = invoices[1].id

        def fiscalize(move, *args, **kwargs):
            if move.id == failing_id:
                move.env.cr.execute("SELECT 1 / 0")
            # Stands in for the real ORM writes fiscalize() performs (ZKI, JIR,
            # fiscal log). On a cursor left aborted by the previous record this
            # raises "current transaction is aborted".
            move.env.cr.execute("SELECT 1")
            return True

        with patch.object(type(invoices), "fiscalize", fiscalize):
            with self.assertLogs(
                "odoo.addons.l10n_hr_account_fiscal.models.account_move",
                level="ERROR",
            ) as captured:
                success, skipped, error = invoices._batch_fiscalize()

        self.assertEqual((success, skipped, error), (2, 0, 1))
        self.assertTrue(
            any("Fiscalization failed" in line for line in captured.output),
            "the swallowed exception must be logged with its traceback",
        )

    def test_validator_accepts_a_foreign_currency_invoice(self):
        """The guard must compare like with like: company currency throughout.

        ``amount_untaxed`` is in invoice currency and ``amount_untaxed_signed``
        in company currency; the fiscal bases are company currency, so only the
        latter is a valid comparison. Getting this wrong rejects every
        foreign-currency invoice even though its message is correct.
        """
        invoice = self._create_hr_invoice(
            "out_invoice", currency=self.foreign_currency)
        self.assertAlmostEqual(invoice.amount_untaxed, 1000.0, places=2)
        self.assertAlmostEqual(invoice.amount_untaxed_signed, 500.0, places=2)

        tax_data = invoice._get_fisc_tax_values()
        pdv = tax_data["Pdv"][25.0]
        self.assertAlmostEqual(pdv["Osnovica"], 500.0, places=2)
        self.assertAlmostEqual(pdv["Iznos"], 125.0, places=2)

        invoice._validate_fiscal_invoice(_racun_stub(500.0, 125.0, 625.0))

    def test_validator_accepts_exempt_base(self):
        """IznosOslobPdv counts towards the base, so it must not false-trigger."""
        invoice = self._create_hr_invoice("out_invoice", lines=[
            (1000.0, self.tax_pdv_25),
            (200.0, self.tax_exempt),
        ])
        self.assertAlmostEqual(invoice.amount_untaxed, 1200.0, places=2)
        invoice._validate_fiscal_invoice(
            _racun_stub(1000.0, 250.0, 1450.0, IznosOslobPdv="200.00")
        )


@tagged("post_install", "-at_install")
class TestNaknade(AccountTestInvoicingCommon):
    """A 'Naknade' tax reports a name and an amount, not two dictionary keys."""

    def test_naknada_carries_its_values(self):
        captured = {}

        class _Factory:
            type_factory = SimpleNamespace(
                Naknada=lambda NazivN, IznosN: captured.update(naziv=NazivN, iznos=IznosN)
            )

        move = self.env["account.move"].create({
            "move_type": "out_invoice", "partner_id": self.partner_a.id,
        })
        move.company_id.l10n_hr_tax_model = "r1"
        with patch.object(
            type(move), "_get_fisc_tax_values",
            return_value={
                "Pdv": {}, "Pnp": {}, "OstaliPor": [],
                "Naknade": [{"NazivN": "Naknada za ambalazu", "IznosN": 1.5}],
            },
        ):
            move._prepare_fisc_taxes(_Factory())

        self.assertEqual(captured.get("naziv"), "Naknada za ambalazu")
        self.assertEqual(captured.get("iznos"), "1.50")
