# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source ERP Solution
#    Author: Uvid d.o.o.
#    Copyright: Uvid d.o.o.
#    web: https://uvid.hr/
#    e-mail: info@uvid.hr
#
#    This program is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Affero General Public License as
#    published by the Free Software Foundation, either version 3 of the
#    License, or (at your option) any later version.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Affero General Public License for more details.
#
#    You should have received a copy of the GNU Affero General Public License
#    along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
##############################################################################
import base64

from odoo.tests import tagged, TransactionCase
from odoo.tests.form import Form
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.primitives import hashes, serialization
from datetime import datetime, timedelta


@tagged("post_install", "-at_install", "uvid", 'l10n_hr_fiscal', 'l10n_hr', 'uvid_account')
class TestResCompany(TransactionCase):

    def test_onchange_fisc_env(self):
        with self.debug_mode():
            form_company_id = Form(self.env.company.sudo())
            form_company_id.fisc_env = 'none'
            company_id = form_company_id.save()

            self.assertEqual('', company_id.server_port)
            self.assertEqual('', company_id.server_address)
            self.assertEqual('', company_id.service_name)

            form_company_id = Form(self.env.company)
            form_company_id.fisc_env = 'test'
            company_id = form_company_id.save()
            self.assertEqual('8449', company_id.server_port)
            self.assertEqual('cistest.apis-it.hr', company_id.server_address)
            self.assertEqual('FiskalizacijaServiceTest', company_id.service_name)

            form_company_id = Form(self.env.company)
            form_company_id.fisc_env = 'production'
            company_id = form_company_id.save()

            self.assertEqual('8449', company_id.sudo().server_port)
            self.assertEqual('cis.porezna-uprava.hr', company_id.server_address)
            self.assertEqual('FiskalizacijaService', company_id.service_name)

    @staticmethod
    def _generate_test_certificate():
        # Test Key, not secured, and we don't care if leaked as its only purpose it to create testing certificate and be used in testing.
        pem_key = (b'-----BEGIN PRIVATE KEY-----\nMIIEvAIBADANBgkqhkiG9w0BAQEFAASCBKYwggSiAgEAAoIBAQCWYtcXViQFElB'
                   b'/\ngi4MJju4GuPfegdUtJvcoiK1U9zJuzFWkGBVx0NcEC8AbjG9opzl3Q2QjLgtE4c2\nj7IFA+94X+DJyt/PWrfRmYqc09Zi6'
                   b'+LiFHPgr0jIvpFwG7zGRe2x3HN1AbMHQ6eg\ncOtMGnka3aGlvXz9iViPQKe3JEOgwmdqhh/tFMrCTsQhWJqBOBezkFmWmglbvCpi\n/5on8gce'
                   b'/uaRjlB3PiA4bWd8XcQtBNOTE8DpIFGxuUdGE/ctRVkNlhIDXdZAKlkJ\nDbg5Hs810LBgbVk4Zwez6sU1FNbaM4c7EsXIjYpZdPLhkxA'
                   b'+tk5Lgy5TLmJUk2vf\naKASrkx5AgMBAAECggEARFJXQcTizGMLq0IrRV3BV9zvlcHMvtDm1o/akOKutf+T'
                   b'\nZK5m9dF3asX3dIybkHnmKhAJb5hevCvZDBKwX9Lv4pI8f7DpiTy/sju9W45qIbrk\n8q00D'
                   b'+nSeVEKphIT60gtutZapdfFzBESgLOMUqDcUDZMkA3MUSsqzroi9/NDvi6h'
                   b'\nXCuZuqyugcK2IbtvQbbzgn0aDkgMFpK8nU9W7qUNqmIyURq0s7jFwmn8WESpwEIc'
                   b'\nk7nRSQMO2yXgTubt4QkpAk3xAmTNidLeEHW1f4DheXGpbUkWpiUECdvUVdc4I2DZ\nn8PyUGsluiWvJ8/iE1rLYOzb8mb6IsTewzve2SC3'
                   b'+QKBgQDPQJTIwBVpj0iDLvMg\nHCsOylz3Egt07KAQJqOXDfvgEBOCVvSl/IddZca9C8KysxFbW2ID+vSURuw1651U\nHyx+xJIPd5cF'
                   b'/ieWIwFEBKuJJVlkreA3TDirJoA/T19eiHJkFaec0G1K6dRB2+B'
                   b'+\nfw62RgLOmso27CRxJ53tLQ03AwKBgQC5wiNdfAK5CKR6Gm7TCASDHK5Q3NMAGBtn'
                   b'\niEf1kXDhF3wBcVO2oiY7OHRt2v1yl7gIRYiqLeoNMEsRsMuCvmI6gKvv1WmTg/Rr\nr2sRXipACvh7vEwQByXL1rmFUMJVO'
                   b'+O6Og7IA4yDjmn6qSfiAopancEyNVBWc8Y8\nqh2IQk2n0wKBgGdJQxztBX7PBo9CFa5Z+2dqmHwVRRpnVrnV189PC8i1mlNprJEQ'
                   b'\nUhHMyAes1cIjFbJWz3k2Vy+STOPuYUDsLEudAUGuEtjMucPL/DR+s1ItB+jx8nz8\ngn1hOabTkq7VB1UzqY2wHdeowrxzrOS9w4I5T'
                   b'+rRH5fRhbPSz5TE0AIrAoGAU7px\n/l07TPPcTz1C3tQqVH7FA6XFZbF4CL6g0MtxucPAHVZbiWKlIORddnbS7qf8R54v'
                   b'\n76Uqbi9qZtrtoEz4Ma510XC8WcWMkk1LUVTEboGDZyKElmTiYHK0xKaWMZ0BFJu'
                   b'+\nteEDoPi8REOiuniyrA2XW240fANLQ2TaUuSv5AkCgYB03ktidANfDUQACwzIwmdg\nuLSk4IM0+c1sCBtitmjkNuSnB/4mCcEVbe6wHo'
                   b'/2QU1r2FTGgaI5Xmrc4C06tnEt\ntqg77xk08s6XBa4M1GdcfJlSQ9tQscFwFingg7Pt8ZtasYZ/Zc01drtOCvMB0ZVa\nm+CnFi7n3VRE1zI/SySISQ'
                   b'==\n-----END PRIVATE KEY-----\n')
        key = serialization.load_pem_private_key(
            pem_key,
            password=None,
        )
        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COUNTRY_NAME, u"HR"),
            x509.NameAttribute(NameOID.STATE_OR_PROVINCE_NAME, u"TEST"),
            x509.NameAttribute(NameOID.LOCALITY_NAME, u"TEST"),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, u"TEST"),
            x509.NameAttribute(NameOID.COMMON_NAME, u"localhost"),
        ])
        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.now())
            .not_valid_after(datetime.now() + timedelta(days=365))
            .add_extension(
                x509.SubjectAlternativeName([x509.DNSName(u"localhost")]),
                critical=False,
            )
            .sign(key, hashes.SHA256())
        )
        cert_p12 = serialization.pkcs12.serialize_key_and_certificates(
            name=b"px-cert",
            key=key,
            cert=cert,
            cas=None,
            encryption_algorithm=serialization.BestAvailableEncryption(b"TestPassword1234")
        )
        return base64.b64encode(cert_p12), cert, key

    def test_res_company_certificate_write(self):
        p12_certificate, certificate, key = self._generate_test_certificate()
        company_id = self.env.company
        private_key_bytes = key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8, serialization.NoEncryption())
        result_key = base64.b64encode(private_key_bytes)
        pem_bytes = private_key_bytes + certificate.public_bytes(serialization.Encoding.PEM)
        result_pem = base64.b64encode(pem_bytes)
        company_id.write({'certificate': p12_certificate, 'certificate_pass': 'TestPassword1234'})
        self.assertEqual(result_key, company_id.certificate_key)
        self.assertEqual(result_pem, company_id.certificate_pem)
