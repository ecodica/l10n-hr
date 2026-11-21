"""XML-DSig signing and verification for the FINA fiscalization service.

The request element inside the SOAP Body carries an enveloped RSA-SHA256
signature (exclusive XML canonicalization), appended as its last child where
``FiskalizacijaSchema.xsd`` allows ``ds:Signature``, and referenced through the
element's ``Id`` attribute.

Requests are signed with the pure-Python signxml library (on top of lxml and
cryptography), which replaced the earlier implementation built on the
``xmlsec`` bindings for the C library libxmlsec1. The envelopes FINA receives
keep the same shape as before, including the ``X509IssuerSerial`` +
``X509Certificate`` KeyInfo.

Responses are verified by this module itself, against the pinned FINA
service certificate shipped with the module. FINA's service (.NET SignedXml)
signs the ``SignedInfo`` element rendered *standalone* - the canonical bytes
do not carry the namespace declarations that are only in scope from the SOAP
ancestors - while the stock xmlsec and signxml implementations canonicalize
in document context and compute different bytes. The reference digest, on the
other hand, is computed in document context. Both stages are reproduced here,
pinned by ``tests/data/fina_demo_dohvati_response.xml``, a response captured
from the live demo service.

Note: the Odoo environment pins ``cryptography==42.0.8`` (an Odoo core
requirement), which makes ``signxml==3.2.2`` the newest installable version.
"""
import base64
import hashlib
import logging
import re
import warnings
from datetime import datetime, timezone
from hashlib import md5
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from lxml import etree

# signxml 3.2.2 - the newest version compatible with the Odoo-pinned
# cryptography==42.0.8 - imports pyOpenSSL's deprecated ``crypto.verify``
# binding at import time (it uses it to check RSA signatures). Odoo pins
# pyopenssl==24.1.0, where the binding exists but warns on import - the
# warning reaches the server log as py.warnings on every process start.
# Silence exactly this warning; the binding is only REMOVED in pyOpenSSL 25,
# which the Odoo pin already excludes.
with warnings.catch_warnings():
    warnings.filterwarnings(
        "ignore", message=r"verify\(\) is deprecated", category=DeprecationWarning,
    )
    from signxml import (
        CanonicalizationMethod,
        DigestAlgorithm,
        SignatureMethod,
        XMLSigner,
        methods,
    )

_logger = logging.getLogger(__name__)

SOAP_ENV_NS = "http://schemas.xmlsoap.org/soap/envelope/"
DS_NS = "http://www.w3.org/2000/09/xmldsig#"

# Fiskalizacija signs with RSA-SHA256 over exclusive canonicalization, and
# references the request element through its Id attribute (the schema defines
# that attribute "za potrebe digitalnog potpisa"). Stating the algorithms
# explicitly also freezes them against future signxml default changes.
_C14N_EXCLUSIVE = CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0

# The response verification profile: the algorithms FINA's service is known to
# use, plus the ones our own signer emits so the round-trip tests verify.
_C14N_EXCLUSIVE_PREFIX = "http://www.w3.org/2001/10/xml-exc-c14n#"
_C14N_INCLUSIVE = "http://www.w3.org/TR/2001/REC-xml-c14n-20010315"
_ALLOWED_C14N = {
    CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0.value: False,
    CanonicalizationMethod.EXCLUSIVE_XML_CANONICALIZATION_1_0_WITH_COMMENTS.value: True,
    _C14N_INCLUSIVE: False,
    _C14N_INCLUSIVE + "#WithComments": True,
}
_RSA_SHA256 = "http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"
_SHA256_DIGEST = "http://www.w3.org/2001/04/xmlenc#sha256"
_ENVELOPED_TRANSFORM = "http://www.w3.org/2000/09/xmldsig#enveloped-signature"


def _pem_bytes(data, what):
    """Return *data* as PEM bytes, decoding base64 if necessary.

    ``get_fiscal_data()`` passes the base64-encoded ``pem_certificate`` /
    ``pem_key`` binary fields; other callers may pass raw PEM.
    """
    if not data:
        raise ValueError(f"Company {what} data is missing")
    if isinstance(data, str):
        data = data.encode("utf-8")
    if not data.lstrip().startswith(b"-----BEGIN"):
        try:
            data = base64.b64decode(data, validate=True)
        except (ValueError, TypeError):
            raise ValueError(f"Cannot load {what}: not PEM or base64-encoded PEM") from None
        if not data.lstrip().startswith(b"-----BEGIN"):
            raise ValueError(f"Cannot load {what}: not PEM or base64-encoded PEM")
    return data


def _warn_if_expired(cert_bytes, source):
    """Report a pinned service certificate that is past its validity window.

    The verifier checks the signature against the key it is handed and will
    not tell us the certificate behind that key expired, so a stale pin fails
    silently in the one direction that matters. Checking it here turns
    "verification quietly stops being meaningful" into a log line somebody can
    act on.
    """
    try:
        cert = x509.load_pem_x509_certificate(cert_bytes)
    except Exception:
        _logger.warning("[Fiskal] Could not parse the pinned service certificate: %s", source)
        return
    now = datetime.now(timezone.utc)
    if cert.not_valid_after_utc < now:
        _logger.error(
            "[Fiskal] The pinned fiscalization service certificate EXPIRED on %s (%s). "
            "Response signatures cannot be meaningfully verified until it is refreshed.",
            cert.not_valid_after_utc.date(), source,
        )
    elif cert.not_valid_before_utc > now:
        _logger.error(
            "[Fiskal] The pinned fiscalization service certificate is not valid until %s (%s).",
            cert.not_valid_before_utc.date(), source,
        )


class Signer:
    """Signs fiscalization requests and computes the protective code (ZKI).

    :param cert_data: company certificate, PEM bytes (raw or base64-encoded,
                      as the ``pem_certificate`` binary field stores it)
    :param key_data: company private key, PEM bytes (raw or base64-encoded);
                     defaults to ``cert_data`` for a bundled PEM
    :param password: private key passphrase, if the key is encrypted
    """

    def __init__(self, cert_data, key_data=None, password=None):
        if not key_data:
            key_data = cert_data
        self.cert_pem = _pem_bytes(cert_data, "certificate")
        self.key_pem = _pem_bytes(key_data, "private key")
        self.password = password.encode("utf-8") if password else None
        try:
            self.cert = x509.load_pem_x509_certificate(self.cert_pem)
        except ValueError as error:
            raise ValueError(f"Cannot load certificate: {error}") from error
        try:
            self.hazmat_key = serialization.load_pem_private_key(
                self.key_pem, password=self.password,
            )
        except (ValueError, TypeError) as error:
            raise ValueError(f"Cannot load private key: {error}") from error
        self.signer = XMLSigner(
            method=methods.enveloped,
            signature_algorithm=SignatureMethod.RSA_SHA256,
            digest_algorithm=DigestAlgorithm.SHA256,
            c14n_algorithm=_C14N_EXCLUSIVE,
        )

    def _key_info(self):
        """FINA-style KeyInfo: X509Data with issuer serial and certificate.

        signxml would emit a bare ``X509Certificate``; building the KeyInfo
        explicitly keeps the exact shape FINA has been receiving since the
        libxmlsec1 implementation. KeyInfo is not part of the signed data, so
        this choice cannot break the signature.
        """
        key_info = etree.Element(f"{{{DS_NS}}}KeyInfo", nsmap={None: DS_NS})
        x509_data = etree.SubElement(key_info, f"{{{DS_NS}}}X509Data")
        issuer_serial = etree.SubElement(x509_data, f"{{{DS_NS}}}X509IssuerSerial")
        etree.SubElement(issuer_serial, f"{{{DS_NS}}}X509IssuerName").text = (
            self.cert.issuer.rfc4514_string()
        )
        etree.SubElement(issuer_serial, f"{{{DS_NS}}}X509SerialNumber").text = str(
            self.cert.serial_number
        )
        etree.SubElement(x509_data, f"{{{DS_NS}}}X509Certificate").text = (
            base64.b64encode(self.cert.public_bytes(serialization.Encoding.DER)).decode()
        )
        return key_info

    def sign_document(self, root):
        """Sign the SOAP Body's request element of ``root`` in place.

        The request element gets a fresh ``Id`` attribute and an enveloped
        RSA-SHA256 signature referencing it, appended as its last child -
        where ``FiskalizacijaSchema.xsd`` allows ``ds:Signature``.
        """
        body = root.find(f"{{{SOAP_ENV_NS}}}Body")
        req_node = body[0] if body is not None else None
        if req_node is None:
            raise ValueError("Unable to find request tag element")
        request_id = str(uuid4())
        req_node.attrib["Id"] = request_id
        # signxml returns a signed copy of the request element, so graft it
        # back to keep the request at its position in the SOAP envelope.
        signed_req = self.signer.sign(
            req_node,
            key=self.hazmat_key,
            key_info=self._key_info(),
            reference_uri=f"#{request_id}",
            id_attribute="Id",
        )
        if signed_req is not req_node:
            body.replace(req_node, signed_req)

    def sign_zki_payload(self, data):
        """
        Sign raw ZKI payload using the private key.

        The payload is signed with RSASSA-PKCS1-v1_5 over SHA-256 and the signature is
        hashed with MD5; the digest is returned as lowercase hexadecimal. Chapter 12
        "Zaštitni kod izdavatelja" of the Fiskalizacija technical specification v2.7
        prescribes RSA-SHA256, and production refuses RSA-SHA1 from 01.01.2027. FINA
        receives only the MD5, so it cannot check the hash: the only check is an
        inspector asking for a ZKI to be reproduced from its inputs.

        Args:
            * data - raw ZKI data to be signed
        Returns:
            * ZKI digest calculated by the standard algorithm
        """
        signature = self.hazmat_key.sign(
            data.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA256(),
        )
        return md5(signature).hexdigest()


# Name kept from the libxmlsec1 era: ``get_fiscal_data()`` and the POS
# fiscalization modules pass base64-encoded binary fields, which
# ``_pem_bytes`` accepts.
BinarySigner = Signer


class Verifier:
    """Verifies FINA response signatures against a pinned service certificate.

    FINA's service (a .NET SignedXml stack) signs ``SignedInfo`` rendered
    *standalone*: the canonical bytes do not include the namespace declarations
    that are merely in scope from the SOAP ancestors. Canonicalizing in
    document context - what stock xmlsec and signxml implementations do -
    computes different bytes and the signature check fails with a misleading
    "bad signature". The reference digest, in contrast, is computed in
    document context. ``tests/data/fina_demo_dohvati_response.xml`` holds a
    response captured from the live demo service pinning both behaviors.
    """

    def __init__(self, cert_data, source=None):
        """
        :param cert_data: the pinned FINA service certificate, PEM bytes
                          (raw or base64-encoded)
        :param source: description for the expiry warning, e.g. a file path
        """
        self.cert_pem = _pem_bytes(cert_data, "fiscalization service certificate")
        try:
            self.cert = x509.load_pem_x509_certificate(self.cert_pem)
        except ValueError as error:
            raise ValueError(
                f"Cannot load Fiscalization service certificate: {error}"
            ) from error
        self.cert_der = self.cert.public_bytes(serialization.Encoding.DER)
        _warn_if_expired(self.cert_pem, source or "service certificate (in-memory)")

    @staticmethod
    def _c14n(node, algorithm, standalone, inclusive_ns_prefixes=None):
        """Canonicalize *node* with *algorithm*.

        :param standalone: render the node the way FINA's service does - alone,
                            without the namespace declarations that are only in
                            scope from the ancestors - instead of in document
                            context. For exclusive canonicalization the two
                            renderings are byte-identical.
        """
        exclusive = algorithm.startswith(_C14N_EXCLUSIVE_PREFIX)
        with_comments = algorithm.endswith("#WithComments")
        if standalone:
            node = etree.fromstring(etree.tostring(node))
        return etree.tostring(
            node,
            method="c14n",
            exclusive=exclusive,
            with_comments=with_comments,
            inclusive_ns_prefixes=inclusive_ns_prefixes,
        )

    def verify_document(self, root):
        """Verify the FINA response signature. Returns True/False, never raises.

        A failure must not abort the caller: by the time we are here FINA has
        already accepted the invoice and issued a JIR, so raising would roll back
        a document the tax authority considers issued. Report it instead - loudly
        enough to be noticed, quietly enough not to lose a receipt.
        """
        try:
            return self._verify_document(root)
        except Exception as error:
            _logger.error(
                "[Fiskal] Response signature verification FAILED: %s. "
                "The response may not be genuine, or the pinned service certificate is stale.",
                error,
            )
            return False

    def _verify_document(self, root):
        body = root.find(f"{{{SOAP_ENV_NS}}}Body")
        if body is None or not len(body):
            _logger.error("[Fiskal] Response has no SOAP Body payload; cannot verify signature.")
            return False
        signature = root.find(f".//{{{DS_NS}}}Signature")
        if signature is None:
            _logger.error("[Fiskal] Response carries no XML signature; nothing to verify.")
            return False

        # The pin is the trust anchor: the response must be signed with the
        # pinned key and carry the pinned certificate. The pin is refreshed
        # together with FINA's service certificate, so a mismatch is not
        # legitimate for this service.
        embedded_cert = signature.find(
            f".//{{{DS_NS}}}KeyInfo/{{{DS_NS}}}X509Data/{{{DS_NS}}}X509Certificate"
        )
        if embedded_cert is None or not (embedded_cert.text or "").strip():
            _logger.error("[Fiskal] Response signature carries no certificate to compare with the pin.")
            return False
        embedded_der = base64.b64decode(re.sub(r"\s+", "", embedded_cert.text))
        if embedded_der != self.cert_der:
            _logger.error(
                "[Fiskal] Response certificate does not match the pinned FINA service certificate."
            )
            return False

        signed_info = signature.find(f"{{{DS_NS}}}SignedInfo")
        if signed_info is None:
            _logger.error("[Fiskal] Response signature has no SignedInfo.")
            return False
        references = signed_info.findall(f"{{{DS_NS}}}Reference")
        if len(references) != 1:
            _logger.error("[Fiskal] Expected exactly one signature reference, found %s.", len(references))
            return False

        c14n_method_el = signed_info.find(f"{{{DS_NS}}}CanonicalizationMethod")
        c14n_method = c14n_method_el.get("Algorithm") if c14n_method_el is not None else None
        if c14n_method not in _ALLOWED_C14N:
            _logger.error("[Fiskal] Unsupported canonicalization method: %s", c14n_method)
            return False
        signature_method_el = signed_info.find(f"{{{DS_NS}}}SignatureMethod")
        signature_method = signature_method_el.get("Algorithm") if signature_method_el is not None else None
        if signature_method != _RSA_SHA256:
            _logger.error("[Fiskal] Unsupported signature method: %s", signature_method)
            return False

        public_key = self.cert.public_key()
        if not isinstance(public_key, rsa.RSAPublicKey):
            _logger.error("[Fiskal] The pinned service certificate has no RSA public key.")
            return False
        signature_value = base64.b64decode(
            re.sub(r"\s+", "", signature.findtext(f"{{{DS_NS}}}SignatureValue") or "")
        )
        # FINA signs the standalone rendering of SignedInfo (see the class
        # docstring); for our own exclusive-c14n signatures both renderings
        # are identical.
        signed_info_c14n = self._c14n(signed_info, c14n_method, standalone=True)
        public_key.verify(signature_value, signed_info_c14n, padding.PKCS1v15(), hashes.SHA256())

        reference = references[0]
        transforms = [
            t.get("Algorithm") for t in reference.iter(f"{{{DS_NS}}}Transform")
        ]
        if _ENVELOPED_TRANSFORM not in transforms:
            _logger.error("[Fiskal] The signature reference is missing the enveloped-signature transform.")
            return False
        c14n_transforms = [t for t in transforms if t in _ALLOWED_C14N]
        if not c14n_transforms:
            _logger.error("[Fiskal] The signature reference has no canonicalization transform.")
            return False
        digest_method_el = reference.find(f"{{{DS_NS}}}DigestMethod")
        digest_method = digest_method_el.get("Algorithm") if digest_method_el is not None else None
        if digest_method != _SHA256_DIGEST:
            _logger.error("[Fiskal] Unsupported digest method: %s", digest_method)
            return False

        uri = reference.get("URI") or ""
        if not uri.startswith("#") or not uri[1:]:
            _logger.error("[Fiskal] The signature reference URI %r is not an internal Id reference.", uri)
            return False
        request_id = uri[1:]
        payload = next(
            (element for element in root.iter() if element.get("Id") == request_id), None,
        )
        if payload is None:
            _logger.error("[Fiskal] The signature reference points at a missing Id: %r", uri)
            return False

        declared_digest = re.sub(
            r"\s+", "", reference.findtext(f"{{{DS_NS}}}DigestValue") or ""
        )
        # The digest is computed in document context, with the signature
        # excised by the enveloped-signature transform.
        parent, position = signature.getparent(), list(signature.getparent()).index(signature)
        parent.remove(signature)
        try:
            payload_c14n = self._c14n(payload, c14n_transforms[-1], standalone=False)
            computed_digest = base64.b64encode(hashlib.sha256(payload_c14n).digest()).decode()
        finally:
            parent.insert(position, signature)
        if computed_digest != declared_digest:
            _logger.error(
                "[Fiskal] Response payload digest mismatch for reference %r.", uri
            )
            return False
        return True


class EnvelopedSignaturePlugin:
    def __init__(self, client, signer, verifier):
        self.fiscal_client = client
        self.signer = signer
        self.verifier = verifier
        # None = not attempted yet; read by res.company._get_log_vals.
        self.last_verification_ok = None

    def egress(self, envelope, http_headers, operation, binding_options):
        if self.fiscal_client.requires_signature(operation):
            self.signer.sign_document(envelope)
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        if self.fiscal_client.requires_signature(operation):
            try:
                self.last_verification_ok = bool(self.verifier.verify_document(envelope))
            except Exception as error:
                # verify_document is not supposed to raise; if it does, the response
                # is still not verified and must not take the transaction down.
                self.last_verification_ok = False
                _logger.exception("[Fiskal] Unexpected error verifying the response signature: %s", error)
        return envelope, http_headers
