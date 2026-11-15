"""The ZKI algorithm, pinned by golden vectors.

``tests/data/zki_vectors.json`` holds payloads, a fixed test-only key and the ZKI each
payload must produce: ``md5(RSASSA-PKCS1-v1_5-SHA256(payload))`` (Fiskalizacija technical
specification v2.7, chapter 12). The POS computes the same ZKI in JavaScript from the same
file, so a vector failing here means the two implementations no longer agree.

FINA receives only the MD5 and never checks the ZKI. Nothing but these vectors catches a
wrong hash before an inspector asks for a ZKI to be reproduced.
"""
import base64
import datetime
import hashlib
import json
import os
import tempfile

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.x509.oid import NameOID
from odoo.tests import TransactionCase, tagged

from ..fiscal import fiscal
from ..fiscal.zeep_signer import BinarySigner, Signer

VECTORS_PATH = os.path.join(os.path.dirname(__file__), "data", "zki_vectors.json")


def load_vectors():
    """The golden vectors file, as written by brain/.../golden_vectors/generate.py."""
    with open(VECTORS_PATH, encoding="utf-8") as vectors_file:
        return json.load(vectors_file)


def self_signed_pem(key):
    """A throwaway certificate for ``key``: the signers load one, the ZKI ignores it."""
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "zki test")])
    now = datetime.datetime.now(datetime.timezone.utc)
    certificate = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(key.public_key())
        .serial_number(1)
        .not_valid_before(now - datetime.timedelta(days=1))
        .not_valid_after(now + datetime.timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return certificate.public_bytes(serialization.Encoding.PEM)


@tagged("post_install", "-at_install")
class TestFiscalZki(TransactionCase):
    """Both signers produce the specification's ZKI for every golden vector."""

    vectors = None
    key = None
    key_pem = None
    cert_pem = None

    def _load_fixture(self):
        """Read the vectors and their key once per test."""
        self.vectors = load_vectors()
        der = base64.b64decode(self.vectors["pkcs8_b64"])
        self.key = serialization.load_der_private_key(der, password=None)
        self.key_pem = self.key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        self.cert_pem = self_signed_pem(self.key)

    def _binary_signer(self):
        """The signer ``fiscalize()`` uses: base64 PEM, as ``get_fiscal_data()`` returns it."""
        return BinarySigner(
            cert_data=base64.b64encode(self.cert_pem),
            key_data=base64.b64encode(self.key_pem),
        )

    def test_vectors_are_sha256(self):
        """The fixture itself states the algorithm, and its signatures verify with SHA-256."""
        self._load_fixture()
        self.assertEqual(self.vectors["algorithm"], "md5(RSASSA-PKCS1-v1_5-SHA256(payload))")
        for vector in self.vectors["vectors"]:
            signature = base64.b64decode(vector["signature_b64"])
            self.key.public_key().verify(
                signature, vector["payload"].encode("utf-8"), padding.PKCS1v15(), hashes.SHA256(),
            )
            self.assertEqual(hashlib.md5(signature).hexdigest(), vector["zki"], vector["name"])

    def test_binary_signer_matches_every_vector(self):
        """``generate_zki`` with the signer ``fiscalize()`` builds gives each vector's ZKI."""
        self._load_fixture()
        signer = self._binary_signer()
        for vector in self.vectors["vectors"]:
            fields = vector["fields"]
            datalist = [
                fields["Oib"], fields["DatVrijeme"], fields["BrOznRac"],
                fields["OznPosPr"], fields["OznNapUr"], fields["IznosUkupno"],
            ]
            self.assertEqual(fiscal.generate_zki(datalist, signer=signer), vector["zki"], vector["name"])

    def test_file_signer_matches_every_vector(self):
        """The file-based signer signs the same way."""
        self._load_fixture()
        with tempfile.TemporaryDirectory() as folder:
            key_path = os.path.join(folder, "key.pem")
            cert_path = os.path.join(folder, "cert.pem")
            with open(key_path, "wb") as key_file:
                key_file.write(self.key_pem)
            with open(cert_path, "wb") as cert_file:
                cert_file.write(self.cert_pem)
            signer = Signer(cert_path, key_path)
            for vector in self.vectors["vectors"]:
                self.assertEqual(signer.sign_zki_payload(vector["payload"]), vector["zki"], vector["name"])

    def test_zki_is_not_signed_with_sha1(self):
        """Production refuses RSA-SHA1 from 01.01.2027; a SHA-1 ZKI would match nothing."""
        self._load_fixture()
        signer = self._binary_signer()
        payload = self.vectors["vectors"][0]["payload"]
        sha1_zki = hashlib.md5(
            self.key.sign(payload.encode("utf-8"), padding.PKCS1v15(), hashes.SHA1())
        ).hexdigest()
        self.assertNotEqual(signer.sign_zki_payload(payload), sha1_zki)

    def test_zki_is_lowercase_hex_of_32(self):
        """The printed ZKI: 32 characters, digits and lowercase a-f (chapter 12)."""
        self._load_fixture()
        zki = self._binary_signer().sign_zki_payload(self.vectors["vectors"][0]["payload"])
        self.assertRegex(zki, r"^[0-9a-f]{32}$")
