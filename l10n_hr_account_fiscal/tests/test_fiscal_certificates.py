"""Certificate selection follows configuration and the clock, before signing."""
import base64
from datetime import datetime

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import pkcs12
from cryptography.x509.oid import NameOID, ObjectIdentifier
from freezegun import freeze_time

from odoo import Command
from odoo.exceptions import MissingError, UserError, ValidationError
from odoo.tests import TransactionCase, new_test_user, tagged


@tagged('post_install', '-at_install')
class TestFiscalCertificates(TransactionCase):

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.company = cls.env['res.company'].create({
            'name': 'Fiscal certificate company', 'country_id': cls.env.ref('base.hr').id,
            'company_registry': '12345678903',
        })
        cls.Certificate = cls.env['certificate.certificate']
        cls.key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        cls.demo = cls._certificate('Demo current', 'demo', '2029-01-01', '2031-01-01')
        cls.prod = cls._certificate('Production current', 'prod', '2029-01-01', '2033-01-01')
        cls.renewal = cls._certificate('Demo renewal', 'demo', '2030-02-01', '2034-01-01')
        premise = cls.env['l10n_hr.business.premise'].create({
            'l10n_hr_name': 'Certificate premise', 'l10n_hr_fiscal_code': 'CERT', 'company_id': cls.company.id,
        })
        cls.device = cls.env['l10n_hr.fiscal.device'].create({
            'l10n_hr_name': 'Certificate device', 'l10n_hr_business_premise_id': premise.id,
            'l10n_hr_fiscal_device_code': 1, 'fiscalization_active': True,
        })
        cls.operator = cls.env['hr.employee'].create({
            'name': 'Certificate operator', 'company_id': cls.company.id,
        })
        cls.operator.work_contact_id.company_registry = '12345678903'
        cls.customer = cls.env['res.partner'].create({'name': 'Private certificate customer'})

    def setUp(self):
        super().setUp()
        clock = freeze_time('2030-01-15 12:00:00')
        clock.start()
        self.addCleanup(clock.stop)

    @classmethod
    def _content(cls, name, start, end, private_key=True):
        subject = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, name),
            x509.NameAttribute(ObjectIdentifier('2.5.4.97'), 'HR12345678903'),
        ])
        cert = (
            x509.CertificateBuilder().subject_name(subject).issuer_name(subject)
            .public_key(cls.key.public_key()).serial_number(x509.random_serial_number())
            .not_valid_before(datetime.fromisoformat(start))
            .not_valid_after(datetime.fromisoformat(end)).sign(cls.key, hashes.SHA256())
        )
        if not private_key:
            return base64.b64encode(cert.public_bytes(serialization.Encoding.PEM))
        return base64.b64encode(pkcs12.serialize_key_and_certificates(
            name.encode(), cls.key, cert, None, serialization.NoEncryption(),
        ))

    @classmethod
    def _certificate(cls, name, cert_type, start, end, company=None, private_key=True):
        return cls.Certificate.create({
            'name': name, 'company_id': (company or cls.company).id,
            'scope': 'fina', 'l10n_hr_type': cert_type,
            'content': cls._content(name, start, end, private_key),
        })

    def _configure(self, certificates, demo=True):
        self.company.write({
            'l10n_hr_fiscal_cert_ids': [Command.set(certificates.ids)],
            'l10n_hr_fiscal_test_env': demo,
            'l10n_hr_fiscal_schema': 'EDUC_v1.10' if demo else 'PROD_v1.10',
        })

    def test_switching_environment_recomputes_the_selected_certificate(self):
        self._configure(self.demo | self.prod)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.company.l10n_hr_fiscal_test_env = False
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.prod)
        self.company.l10n_hr_fiscal_test_env = True
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)

    def test_expiration_ignores_cached_is_valid_and_uses_the_renewal(self):
        self._configure(self.demo | self.renewal)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.assertTrue(self.demo.is_valid)
        with freeze_time('2032-01-15 12:00:00'):
            # Neither the database nor the cached non-stored flag changed.
            self.assertTrue(self.demo.is_valid)
            self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
            data = self.company.get_fiscal_data()
            self.assertEqual(data['cert_data'], self.renewal.pem_certificate)
            self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.renewal)

    def test_expired_certificate_is_rejected_without_falling_back_to_production(self):
        self._configure(self.demo | self.prod)
        self.assertTrue(self.demo.is_valid)
        with freeze_time('2032-01-15 12:00:00'):
            self.assertTrue(self.demo.is_valid)
            with self.assertRaises(MissingError):
                self.company.get_fiscal_data()
            self.assertFalse(self.company.l10n_hr_fiscal_cert_id)

    def test_future_certificate_activates_without_a_configuration_write(self):
        self._configure(self.renewal)
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        with freeze_time('2030-02-15 12:00:00'):
            data = self.company.get_fiscal_data()
            self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.renewal)
            self.assertEqual(data['cert_data'], self.renewal.pem_certificate)

    def test_invoice_precheck_refreshes_a_previously_empty_selection(self):
        self._configure(self.renewal)
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        invoice = self.env['account.move'].new({
            'company_id': self.company.id, 'move_type': 'out_invoice',
            'currency_id': self.company.currency_id.id,
            'partner_id': self.customer.id, 'l10n_hr_payment_method': 'K',
            'l10n_hr_fiscal_device_id': self.device.id, 'l10n_hr_fiscal_operator_id': self.operator.id,
        })
        with freeze_time('2030-02-15 12:00:00'):
            messages = invoice._l10n_hr_post_fiscal_check()
            self.assertFalse(messages)
            self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.renewal)

    def test_valid_renewal_with_later_expiry_is_preferred(self):
        self._configure(self.demo | self.renewal)
        with freeze_time('2030-02-15 12:00:00'):
            self.assertEqual(self.company.get_fiscal_data()['cert_data'], self.renewal.pem_certificate)

    def test_changing_certificate_type_recomputes_selection(self):
        self._configure(self.demo)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.demo.l10n_hr_type = 'prod'
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)

    def test_archiving_certificate_recomputes_selection(self):
        self._configure(self.demo)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.demo.active = False
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        with self.assertRaises(MissingError):
            self.company.get_fiscal_data()

    def test_archiving_private_key_recomputes_selection(self):
        self._configure(self.demo)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.demo.private_key_id.active = False
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        with self.assertRaises(MissingError):
            self.company.get_fiscal_data()

    def test_replacing_content_updates_dates_and_signing_data(self):
        self._configure(self.demo)
        original = self.company.get_fiscal_data()['cert_data']
        self.demo.content = self._content('Expired replacement', '2020-01-01', '2021-01-01')
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        self.demo.content = self._content('Valid replacement', '2029-01-01', '2035-01-01')
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        data = self.company.get_fiscal_data()
        self.assertNotEqual(data['cert_data'], original)
        self.assertEqual(data['cert_data'], self.demo.pem_certificate)
        self.assertEqual(data['key_data'], self.demo.private_key_id.pem_key)

    def test_failed_replacement_preserves_the_previous_certificate(self):
        self._configure(self.demo)
        original = self.company.get_fiscal_data()['cert_data']
        with self.assertRaises(ValidationError):
            self.demo.write({
                'content': base64.b64encode(b'not a certificate'), 'pkcs12_password': 'incorrect',
            })
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.assertEqual(self.company.get_fiscal_data()['cert_data'], original)

    def test_encrypted_key_is_decrypted_only_for_signing(self):
        from ..fiscal.zeep_signer import BinarySigner

        password = 'fixture key password'
        encrypted = self.env['certificate.key'].create({
            'name': 'Encrypted fiscal key', 'company_id': self.company.id,
            'password': password,
            'content': base64.b64encode(self.key.private_bytes(
                serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(password.encode()),
            )),
        })
        self.renewal.private_key_id = encrypted
        self._configure(self.demo | self.renewal)
        with freeze_time('2030-02-15 12:00:00'):
            data = self.company.get_fiscal_data()
            self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.renewal)
            self.assertIn(b'ENCRYPTED PRIVATE KEY', base64.b64decode(encrypted.pem_key))
            self.assertNotIn(b'ENCRYPTED', base64.b64decode(data['key_data']))
            signer = BinarySigner(cert_data=data['cert_data'], key_data=data['key_data'])
            self.assertEqual(len(signer.sign_zki_payload('fixture fiscal payload')), 32)
            self.assertEqual(encrypted.password, password)

    def test_certificate_without_a_private_key_cannot_displace_a_usable_one(self):
        public_only = self._certificate('Public only', 'demo', '2029-01-01', '2038-01-01', private_key=False)
        self._configure(self.demo | public_only)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self._configure(public_only)
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
        with self.assertRaises(MissingError):
            self.company.get_fiscal_data()

    def test_another_company_certificate_is_never_used(self):
        other = self.env['res.company'].create({'name': 'Other certificate company'})
        foreign = self._certificate('Foreign certificate', 'demo', '2029-01-01', '2038-01-01', company=other)
        self._configure(foreign)
        # Even a manually injected stored value must not return another company's key.
        self.company.l10n_hr_fiscal_cert_id = foreign
        with self.assertRaises(MissingError):
            self.company.get_fiscal_data()
        # assertRaises rolls back the attempt, just like a failed RPC request.
        self.assertFalse(self.company._get_fiscal_certificate())
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)

    def test_a_stale_stored_certificate_from_the_wrong_environment_is_replaced(self):
        self._configure(self.demo | self.prod)
        self.company.l10n_hr_fiscal_cert_id = self.prod
        data = self.company.get_fiscal_data()
        self.assertTrue(data['demo'])
        self.assertEqual(data['cert_data'], self.demo.pem_certificate)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)

    def test_schema_must_match_the_environment(self):
        self._configure(self.demo | self.prod)
        self.company.l10n_hr_fiscal_schema = 'PROD_v1.10'
        with self.assertRaisesRegex(UserError, 'schema does not match'):
            self.company.get_fiscal_data()
        self._configure(self.demo | self.prod, demo=False)
        self.company.l10n_hr_fiscal_schema = 'EDUC_v1.10'
        with self.assertRaisesRegex(UserError, 'schema does not match'):
            self.company.get_fiscal_data()

    def test_signing_data_can_be_read_in_binary_size_context_without_certificate_acl(self):
        self._configure(self.demo)
        cashier = new_test_user(
            self.env, login='certificate_refresh_cashier', groups='base.group_user',
            company_id=self.company.id, company_ids=[Command.set(self.company.ids)],
        )
        data = self.company.with_user(cashier).with_context(bin_size=True).get_fiscal_data()
        self.assertIn(b'BEGIN CERTIFICATE', base64.b64decode(data['cert_data']))
        self.assertIn(b'PRIVATE KEY', base64.b64decode(data['key_data']))

    def test_country_change_clears_selection(self):
        self._configure(self.demo)
        self.assertEqual(self.company.l10n_hr_fiscal_cert_id, self.demo)
        self.company.country_id = self.env.ref('base.si')
        self.assertFalse(self.company.l10n_hr_fiscal_cert_id)
