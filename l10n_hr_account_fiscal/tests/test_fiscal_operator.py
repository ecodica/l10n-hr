"""``OibOper`` names the person who issued the document: the fiscal operator.

The operator is an ``hr.employee``, and the OIB reported is the one on their work
contact (``company_registry``). The login that transmitted, ``l10n_hr_fiscal_user_id``,
is recorded too but never reported: one login can be shared by many people. A document
whose operator has no OIB is refused, because FINA accepts an empty ``OibOper``.
"""
import base64
from unittest.mock import patch

from odoo.addons.l10n_hr_account_fiscal.models.l10n_hr_fiscal_v1_mixin import (
    L10nHrFiscalV1Mixin,
    employee_oib,
)
from odoo.exceptions import AccessError, ValidationError
from odoo.tests import tagged
from odoo.tools import file_open

from odoo import Command
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

OIB = "69435151530"


@tagged("post_install", "-at_install")
class TestFiscalOperator(AccountTestInvoicingCommon):
    """Who is reported as having issued a fiscalized document."""

    device = None

    def _employee(self, name, user=None, oib=OIB):
        """Create an employee of the company, with ``oib`` on their work contact.

        As superuser: the test user has Accounting rights only, and creating an
        employee reads HR fields of the contact.
        """
        employee = self.env["hr.employee"].sudo().create({
            "name": name,
            "company_id": self.env.company.id,
            "user_id": user.id if user else False,
        })
        employee.work_contact_id.company_registry = oib
        return employee.sudo(False)

    def _invoice(self, salesperson=False):
        """Create a draft customer invoice on a fiscalizing device."""
        if not self.device:
            premise = self.env["l10n_hr.business.premise"].create({
                "l10n_hr_name": "Operator premise",
                "l10n_hr_fiscal_code": "OPER1",
                "company_id": self.env.company.id,
            })
            self.device = self.env["l10n_hr.fiscal.device"].create({
                "l10n_hr_name": "Operator device",
                "l10n_hr_fiscal_device_code": 1,
                "l10n_hr_business_premise_id": premise.id,
                "fiscalization_active": True,
            })
        return self.env["account.move"].create({
            "move_type": "out_invoice",
            "partner_id": self.partner_a.id,
            "invoice_user_id": salesperson.id if salesperson else False,
            "l10n_hr_fiscal_device_id": self.device.id,
            # cash: a transfer ("T") may be one the company does not fiscalize
            "l10n_hr_payment_method": "G",
        })

    def _operator_at_check(self, move):
        """Run fiscalize() up to its check and return the operator the check saw."""
        seen = []

        def check(document):
            seen.append(document.l10n_hr_fiscal_operator_id)
            return ["stopped by the test"]

        with (
            patch.object(L10nHrFiscalV1Mixin, "_l10n_hr_post_fiscal_check", check),
            self.assertRaises(ValidationError),
        ):
            move.fiscalize()
        return seen[0]

    def test_employee_oib_is_on_the_work_contact(self):
        """Test that an employee's OIB is read from their work contact."""
        self.assertEqual(employee_oib(self._employee("Ana")), OIB)
        self.assertFalse(employee_oib(self._employee("Ivo", oib=False)))
        self.assertFalse(employee_oib(self.env["hr.employee"]))

    def _refusal(self, move):
        """Fiscalize ``move`` and return the message it is refused with.

        The test company has no certificate, so a refusal always comes; what it says
        about the operator is what these tests read.
        """
        with self.assertRaises(ValidationError) as refused:
            move.fiscalize()
        return str(refused.exception)

    def test_default_operator_is_the_salespersons_employee(self):
        """Test that an invoice is issued by its salesperson's employee."""
        salesperson = self.env.ref("base.user_admin")
        employee = self._employee("Salesperson", user=salesperson)
        self._employee("Acting", user=self.env.user)
        self.assertEqual(self._operator_at_check(self._invoice(salesperson=salesperson)), employee)

    def test_default_operator_falls_back_to_the_acting_users_employee(self):
        """Test that without a salesperson the acting user's employee issues it."""
        employee = self._employee("Acting", user=self.env.user)
        self.assertEqual(self._operator_at_check(self._invoice()), employee)

    def test_check_refuses_a_document_without_operator(self):
        """Test that a document without an operator is refused, not sent empty."""
        self.assertIn("No fiscal operator", self._refusal(self._invoice()))

    def test_check_refuses_an_operator_without_oib(self):
        """Test that an operator without an OIB is refused."""
        move = self._invoice()
        move.l10n_hr_fiscal_operator_id = self._employee("No OIB", oib=False)
        self.assertIn("has no OIB", self._refusal(move))

    def test_check_accepts_an_operator_with_oib(self):
        """Test that an operator with an OIB raises no operator error."""
        move = self._invoice()
        move.l10n_hr_fiscal_operator_id = self._employee("With OIB")
        message = self._refusal(move)
        self.assertNotIn("operator", message.lower())
        self.assertIn("certificate", message, "the refusal must still come, from the certificate")

    def test_fiscalize_stamps_the_operator_before_checking(self):
        """Test that fiscalize() sets the operator first, so the check sees it."""
        employee = self._employee("Acting", user=self.env.user)
        self.assertEqual(self._operator_at_check(self._invoice()), employee)

    def test_fiscalize_keeps_an_operator_already_set(self):
        """Test that a later send keeps the operator of the first one."""
        self._employee("Acting", user=self.env.user)
        first = self._employee("First issuer")
        move = self._invoice()
        move.l10n_hr_fiscal_operator_id = first
        self.assertEqual(self._operator_at_check(move), first)


@tagged("post_install", "-at_install")
class TestFiscalCertificateAccess(AccountTestInvoicingCommon):
    """Signing a fiscal message without the right to read the company's certificate."""

    def test_fiscal_data_is_not_callable_over_rpc(self):
        """Test that the data holding the private key cannot be fetched over RPC."""
        self.assertTrue(getattr(type(self.env.company).get_fiscal_data, "_api_private", False))

    def test_a_user_without_certificate_rights_gets_the_signing_data(self):
        """Test that a cashier, who may not read certificates, can still sign: the
        certificate is read as superuser where the message is signed."""
        certificate = self.env["certificate.certificate"].sudo().create({
            "name": "FINA test certificate",
            "pkcs12_password": "example",
            "content": base64.b64encode(
                file_open("certificate/tests/data/cert.pfx", "rb").read()
            ),
            "l10n_hr_type": "demo",
        })
        company = self.env.company
        company.sudo().write({
            "l10n_hr_fiscal_cert_id": certificate.id,
            "l10n_hr_fiscal_schema": "EDUC_v1.10",
        })
        cashier = self.env["res.users"].sudo().create({
            "name": "Cashier",
            "login": "fiscal_cashier",
            "company_id": company.id,
            "company_ids": [Command.set(company.ids)],
            "group_ids": [Command.set(self.env.ref("base.group_user").ids)],
        })
        with self.assertRaises(AccessError):
            certificate.with_user(cashier).read(["pem_certificate"])
        data = company.with_user(cashier).get_fiscal_data()
        self.assertTrue(data["cert_data"])
        self.assertTrue(data["key_data"])
