"""End-to-end: an Odoo invoice becomes a FINA 1.10 message that validates against the XSD.

The tax helpers are pinned by unit tests; these tests go the rest of the way:
build the real ``RacunType`` through ``_prepare_fiscal_invoice`` with Zeep's own
``type_factory`` from the bundled EDUC 1.10 WSDL, serialize the full
``RacunZahtjev`` with Zeep, and validate the XML against the bundled
``FiskalizacijaSchema.xsd``. No network, no certificate, no FINA.
"""
import base64
import datetime
import uuid
from pathlib import Path
from types import SimpleNamespace

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
from lxml import etree
from zeep import Client
from zeep.transports import Transport

from odoo import Command
from odoo.exceptions import ValidationError
from odoo.tests import tagged
from odoo.addons.account.tests.common import AccountTestInvoicingCommon

from ..fiscal.zeep_signer import Signer, Verifier
from .test_fiscal_operation import OPERATOR_OIB

COMPANY_OIB = "12345678901"

MODULE_ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = MODULE_ROOT / "fiscal/schema/Fiskalizacija-WSDL-EDUC_v1.10"
WSDL_URL = SCHEMA_DIR.as_uri() + "/wsdl/FiskalizacijaService.wsdl"
XSD_PATH = SCHEMA_DIR / "schema/FiskalizacijaSchema.xsd"

TNS = "http://www.apis-it.hr/fin/2012/types/f73"
SOAP_ENV = "http://schemas.xmlsoap.org/soap/envelope/"
DS = "http://www.w3.org/2000/09/xmldsig#"


def _flat_list(value):
    if value is None:
        return []
    return value if isinstance(value, list) else [value]


@tagged("post_install", "-at_install", "l10n_hr", "l10n_hr_account_fiscal")
class TestFiscalXml(AccountTestInvoicingCommon):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company_data["company"].l10n_hr_tax_model = "r1"
        cls.company_data["company"].company_registry = COMPANY_OIB

        cls.tax_pdv_25 = cls.env["account.tax"].create({
            "name": "PDV 25% (xml)", "amount_type": "percent", "amount": 25.0,
            "type_tax_use": "sale", "l10n_hr_fiscal_type": "Pdv",
            "company_id": cls.company_data["company"].id,
        })
        cls.tax_pdv_25_other = cls.env["account.tax"].create({
            "name": "PDV 25% twin (xml)", "amount_type": "percent", "amount": 25.0,
            "type_tax_use": "sale", "l10n_hr_fiscal_type": "Pdv",
            "company_id": cls.company_data["company"].id,
        })
        cls.tax_exempt = cls.env["account.tax"].create({
            "name": "Exempt (xml)", "amount_type": "percent", "amount": 0.0,
            "type_tax_use": "sale", "l10n_hr_fiscal_type": "oslobodenje",
            "company_id": cls.company_data["company"].id,
        })
        cls.tax_fee = cls.env["account.tax"].create({
            "name": "Ambalaza (xml)", "amount_type": "fixed", "amount": 1.5,
            "type_tax_use": "sale", "l10n_hr_fiscal_type": "Naknade",
            "company_id": cls.company_data["company"].id,
        })

        premise = cls.env["l10n_hr.business.premise"].create({
            "l10n_hr_name": "XML premise", "l10n_hr_fiscal_code": "XMLPP",
            "company_id": cls.company_data["company"].id,
        })
        cls.device = cls.env["l10n_hr.fiscal.device"].create({
            "l10n_hr_name": "XML device", "l10n_hr_fiscal_device_code": 1,
            "l10n_hr_business_premise_id": premise.id, "fiscalization_active": False,
        })
        cls.operator = cls.env["hr.employee"].sudo().create({
            "name": "XML operator", "company_id": cls.company_data["company"].id,
        })
        cls.operator.work_contact_id.company_registry = OPERATOR_OIB

        # A real Zeep client over the bundled WSDL, offline. Only type_factory
        # and message serialization are used: no signing, no request is sent.
        cls.zeep = Client(WSDL_URL, transport=Transport())
        cls.factory = cls.zeep.type_factory(
            [ns for ns, url in cls.zeep.namespaces.items() if "apis-it.hr/fin/" in url][0]
        )
        cls.xsd = etree.XMLSchema(etree.parse(str(XSD_PATH)))

    @classmethod
    def _fiscal_shim(cls):
        factory = cls.factory

        class _Fakish:
            type_factory = factory

            @staticmethod
            def create_request_header():
                return factory.ZaglavljeType(
                    IdPoruke=str(uuid.uuid4()),
                    DatumVrijeme="03.08.2026T14:35:00",
                )

        return _Fakish()

    def _invoice(self, lines, move_type="out_invoice"):
        return self.env["account.move"].create({
            "move_type": move_type,
            "partner_id": self.partner_a.id,
            "invoice_date": "2026-08-03",
            "date": "2026-08-03",
            "invoice_line_ids": [
                Command.create({
                    "name": "xml line %s" % index,
                    "quantity": 1.0,
                    "price_unit": price_unit,
                    "tax_ids": [Command.set(tax.ids)],
                })
                for index, (price_unit, tax) in enumerate(lines)
            ],
        })

    def _fiscalized(self, move):
        move.l10n_hr_fiscal_device_id = self.device.id
        move.l10n_hr_fiscal_number = "1/XMLPP/1"
        move.l10n_hr_payment_method = "G"
        move.l10n_hr_fiscal_time = "03.08.2026T14:35:00"
        move.l10n_hr_zki = "e4d909c290d0fb1ca068ffaddf22cbd0"
        move.l10n_hr_fiscal_operator_id = self.operator.id
        return move

    def _message(self, move):
        """Prepare the RacunType, serialize RacunZahtjev, and validate the XSD."""
        move = self._fiscalized(move)
        shim = self._fiscal_shim()
        fiscal_data = {"cert_vat": COMPANY_OIB, "racun": ["1", "XMLPP", "1"]}
        racun = move._prepare_fiscal_invoice(shim, fiscal_data, "racuni")

        envelope = self.zeep.create_message(
            self.zeep.service, "racuni",
            Zaglavlje=shim.create_request_header(), Racun=racun,
        )
        body = envelope.find("{%s}Body" % SOAP_ENV)
        root = body[0]
        self.assertTrue(self.xsd.validate(root), self.xsd.error_log)
        racun_xml = root.find("{%s}Racun" % TNS)
        return SimpleNamespace(root=racun_xml, racun=racun, move=move)

    def _txt(self, element, name):
        node = element.find("{%s}%s" % (TNS, name))
        return node.text if node is not None else None

    def _assert_porez(self, message, stopa, osnovica, iznos):
        pdv = message.root.find("{%s}Pdv" % TNS)
        self.assertIsNotNone(pdv, "no Pdv element in the serialized message")
        taxes = _flat_list(pdv.findall("{%s}Porez" % TNS))
        self.assertTrue(taxes)
        found = False
        for porez in taxes:
            if float(porez.findtext("{%s}Stopa" % TNS)) == stopa:
                found = True
                self.assertAlmostEqual(
                    float(porez.findtext("{%s}Osnovica" % TNS)), osnovica, places=2)
                self.assertAlmostEqual(
                    float(porez.findtext("{%s}Iznos" % TNS)), iznos, places=2)
        self.assertTrue(found, "no Porez with rate %s" % stopa)
        return taxes


@tagged("post_install", "-at_install")
class TestFiscalXmlInvoice(TestFiscalXml):

    def test_regular_invoice_serializes_and_validates(self):
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.action_post()
        message = self._message(invoice)
        self.assertEqual(self._txt(message.root, "Oib"), COMPANY_OIB)
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "1250.00")
        self.assertEqual(self._txt(message.root, "NacinPlac"), "G")
        self.assertEqual(self._txt(message.root, "OibOper"), OPERATOR_OIB)
        self.assertEqual(self._txt(message.root, "ZastKod"), "e4d909c290d0fb1ca068ffaddf22cbd0")
        self._assert_porez(message, 25.0, 1000.0, 250.0)
        self.assertIsNone(message.root.find("{%s}IznosOslobPdv" % TNS))
        invoice._validate_fiscal_invoice(message.racun)

    def test_two_taxes_with_the_same_rate_share_one_porez(self):
        invoice = self._invoice([
            (1000.0, self.tax_pdv_25), (2000.0, self.tax_pdv_25_other),
        ])
        invoice.action_post()
        message = self._message(invoice)
        taxes = self._assert_porez(message, 25.0, 3000.0, 750.0)
        self.assertEqual(len(taxes), 1)
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "3750.00")
        invoice._validate_fiscal_invoice(message.racun)

    def test_two_taxes_with_the_same_rate_share_one_porez_on_refund(self):
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.action_post()
        refund = invoice.sudo()._reverse_moves()
        message = self._message(refund)
        self._assert_porez(message, 25.0, -1000.0, -250.0)
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "-1250.00")

    def test_exempt_and_fee_are_carried_and_valid(self):
        invoice = self._invoice([
            (1000.0, self.tax_pdv_25), (200.0, self.tax_exempt),
        ])
        message = self._message(invoice)
        self._assert_porez(message, 25.0, 1000.0, 250.0)
        self.assertEqual(self._txt(message.root, "IznosOslobPdv"), "200.00")
        # Total reflects both the exempt base and the VAT.
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "1450.00")

    def test_fee_tax_is_carried_as_naknade(self):
        invoice = self._invoice([(100.0, self.tax_pdv_25 | self.tax_fee)])
        message = self._message(invoice)
        self._assert_porez(message, 25.0, 100.0, 25.0)
        naknade = message.root.find("{%s}Naknade" % TNS)
        self.assertIsNotNone(naknade)
        naknada = _flat_list(naknade.findall("{%s}Naknada" % TNS))[0]
        self.assertEqual(self._txt(naknada, "NazivN"), "Ambalaza (xml)")
        self.assertEqual(self._txt(naknada, "IznosN"), "1.50")
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "126.50")

    def test_refund_is_signed_and_validates(self):
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.action_post()
        refund = invoice.sudo()._reverse_moves()
        message = self._message(refund)
        self._assert_porez(message, 25.0, -1000.0, -250.0)
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "-1250.00")

    def test_foreign_currency_carries_company_currency_amounts(self):
        foreign = self.setup_other_currency("HRK")
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.currency_id = foreign
        message = self._message(invoice)
        # 1000 + 25% HRK at the historical rate 2.0 -> 625.00 EUR company total.
        self.assertEqual(self._txt(message.root, "IznosUkupno"), "625.00")
        self._assert_porez(message, 25.0, 500.0, 125.0)

    def test_inconsistent_total_is_rejected_before_sending(self):
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.action_post()
        shim = self._fiscal_shim()
        fiscal_data = {"cert_vat": COMPANY_OIB, "racun": ["1", "XMLPP", "1"]}
        racun = invoice._prepare_fiscal_invoice(shim, fiscal_data, "racuni")
        racun.IznosUkupno = "999.00"
        with self.assertRaises(ValidationError):
            invoice._validate_fiscal_invoice(racun)

    def test_untyped_tax_rejects_instead_of_sending(self):
        untyped = self.env["account.tax"].create({
            "name": "Untyped", "amount_type": "fixed", "amount": 1.0,
            "type_tax_use": "sale", "company_id": self.company_data["company"].id,
        })
        invoice = self._fiscalized(self._invoice([(100.0, self.tax_pdv_25 | untyped)]))
        shim = self._fiscal_shim()
        fiscal_data = {"cert_vat": COMPANY_OIB, "racun": ["1", "XMLPP", "1"]}
        with self.assertRaises(ValidationError):
            invoice._prepare_fiscal_invoice(shim, fiscal_data, "racuni")


@tagged("post_install", "-at_install")
class TestFiscalXmlSignature(TestFiscalXml):
    """The signer produces the enveloped signature FINA's schema allows.

    A real ``RacunZahtjev`` is serialized with Zeep from the bundled EDUC 1.10
    WSDL and signed with the module's signer. The result must validate against
    the bundled XSD and verify through the module's verifier. Together with
    ``test_fiscal_response_verification`` this pins the signature construction -
    exclusive c14n, RSA-SHA256, the ``Id`` reference, ``ds:Signature`` as the
    request element's last child, issuer serial and certificate in KeyInfo -
    which is the shape the FINA service depends on.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # A small serial: libxml2 cannot validate xs:integer values beyond 64
        # bits, so a realistic serial would fail the bundled XSD for a reason
        # unrelated to what these tests check. Real FINA certificates have
        # large serials, which FINA's service accepts; only the local XSD
        # validation is limited.
        cls.sign_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "fiscal-signature-test")])
        now = datetime.datetime.now(datetime.timezone.utc)
        cls.sign_cert = (
            x509.CertificateBuilder()
            .subject_name(name).issuer_name(name)
            .public_key(cls.sign_key.public_key())
            .serial_number(1)
            .not_valid_before(now - datetime.timedelta(days=1))
            .not_valid_after(now + datetime.timedelta(days=365))
            .sign(cls.sign_key, hashes.SHA256())
        )
        cls.sign_cert_pem = cls.sign_cert.public_bytes(serialization.Encoding.PEM)
        cls.sign_key_pem = cls.sign_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

    def _signed_envelope(self):
        """Serialize a real RacunZahtjev and sign it the way egress does."""
        invoice = self._invoice([(1000.0, self.tax_pdv_25)])
        invoice.action_post()
        move = self._fiscalized(invoice)
        shim = self._fiscal_shim()
        fiscal_data = {"cert_vat": COMPANY_OIB, "racun": ["1", "XMLPP", "1"]}
        racun = move._prepare_fiscal_invoice(shim, fiscal_data, "racuni")
        envelope = self.zeep.create_message(
            self.zeep.service, "racuni",
            Zaglavlje=shim.create_request_header(), Racun=racun,
        )
        Signer(cert_data=self.sign_cert_pem, key_data=self.sign_key_pem).sign_document(envelope)
        return envelope

    def _request(self, envelope):
        return envelope.find("{%s}Body" % SOAP_ENV)[0]

    def test_signature_is_the_requests_last_child(self):
        """The XSD sequence places ds:Signature after the payload."""
        envelope = self._signed_envelope()
        request = self._request(envelope)
        signature = request.find("{%s}Signature" % DS)
        self.assertIsNotNone(signature, "no signature was appended")
        self.assertIs(list(request)[-1], signature)

    def test_signature_structure_matches_the_fina_specification(self):
        envelope = self._signed_envelope()
        request = self._request(envelope)
        signature = request.find("{%s}Signature" % DS)
        signed_info = signature.find("{%s}SignedInfo" % DS)
        self.assertEqual(
            signed_info.find("{%s}CanonicalizationMethod" % DS).get("Algorithm"),
            "http://www.w3.org/2001/10/xml-exc-c14n#",
        )
        self.assertEqual(
            signed_info.find("{%s}SignatureMethod" % DS).get("Algorithm"),
            "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256",
        )
        reference = signed_info.find("{%s}Reference" % DS)
        self.assertEqual(reference.get("URI"), "#" + request.get("Id"))
        transforms = [t.get("Algorithm") for t in reference.iter("{%s}Transform" % DS)]
        self.assertIn("http://www.w3.org/2000/09/xmldsig#enveloped-signature", transforms)
        self.assertIn("http://www.w3.org/2001/10/xml-exc-c14n#", transforms)
        self.assertEqual(
            reference.find("{%s}DigestMethod" % DS).get("Algorithm"),
            "http://www.w3.org/2001/04/xmlenc#sha256",
        )

    def test_key_info_carries_issuer_serial_and_certificate(self):
        """The KeyInfo keeps the issuer serial + certificate shape FINA receives."""
        envelope = self._signed_envelope()
        signature = self._request(envelope).find("{%s}Signature" % DS)
        x509_data = signature.find(".//{%s}X509Data" % DS)
        self.assertIsNotNone(x509_data)
        self.assertEqual(
            x509_data.findtext("{%s}X509IssuerSerial/{%s}X509SerialNumber" % (DS, DS)),
            str(self.sign_cert.serial_number),
        )
        certificate = x509_data.findtext("{%s}X509Certificate" % DS)
        self.assertEqual(
            certificate,
            base64.b64encode(self.sign_cert.public_bytes(serialization.Encoding.DER)).decode(),
        )

    def test_signed_request_validates_against_the_schema(self):
        """The whole signed envelope is schema-valid, signature included."""
        envelope = self._signed_envelope()
        request = self._request(envelope)
        self.assertTrue(self.xsd.validate(request), self.xsd.error_log)

    def test_signed_request_round_trips_through_the_verifier(self):
        """What the signer emits, the module's own verifier accepts."""
        envelope = self._signed_envelope()
        self.assertTrue(Verifier(cert_data=self.sign_cert_pem).verify_document(envelope))