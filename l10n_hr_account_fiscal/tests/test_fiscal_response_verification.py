"""The FINA response verifier reports its verdict, and never raises.

Verification was a no-op in three separate places: ``Verifier.verify_document``
swallowed every exception, ``BinaryVerifier.verify_document`` returned a verdict
nobody read, and the zeep plugin's ``ingress`` caught what was left and printed
it. Nothing could fail, which is why both bundled service certificates expired in
2024 without anyone noticing. Until this was fixed, TLS was the only integrity
control on an inbound JIR.

Two properties matter and both are tested here. The verifier must **report** -
a failure has to reach a human, via the log and via ``l10n_hr.fiscal.log``. And it
must **not raise**: by the time a response is being checked FINA has already
accepted the invoice and issued a JIR, so an exception would roll back a document
the tax authority considers issued, in order to report a problem that a log line
reports just as well.
"""
import os
from types import SimpleNamespace

from odoo.tests import TransactionCase, tagged

from ..fiscal import zeep_signer


def _expired_certificate():
    """A self-signed certificate whose validity window closed yesterday."""
    from datetime import datetime, timedelta, timezone

    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID

    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "expired-test-cert")])
    now = datetime.now(timezone.utc)
    cert = (
        x509.CertificateBuilder()
        .subject_name(name).issuer_name(name)
        .public_key(key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(days=30))
        .not_valid_after(now - timedelta(days=1))
        .sign(key, hashes.SHA256())
    )
    return cert.public_bytes(serialization.Encoding.PEM)


def _cert_dir():
    return os.path.join(os.path.dirname(os.path.dirname(__file__)), "fiscal", "fina_cert", "demo")


@tagged("post_install", "-at_install")
class TestResponseVerification(TransactionCase):
    """The verifier reports; it does not swallow, and it does not raise."""

    def test_expired_pin_is_reported(self):
        """A lapsed pin must say so, loudly.

        xmlsec verifies against the key it is handed and never mentions that the
        certificate behind it expired, so a stale pin quietly stops meaning anything.
        That is exactly what happened here: both bundled service certificates lapsed in
        2024 and nothing noticed for two years.

        The certificate is generated rather than read from the bundle - the bundled one
        is meant to be refreshed, and a test that fails when somebody does the right
        thing is a test that trains people to ignore it.
        """
        with self.assertLogs(zeep_signer.__name__, level="ERROR") as logs:
            zeep_signer._warn_if_expired(_expired_certificate(), "test")
        self.assertTrue(
            any("EXPIRED" in line for line in logs.output),
            "an expired pinned certificate was not reported",
        )

    def test_a_current_pin_is_not_reported(self):
        """The other half: a valid pin must stay silent, or the check becomes noise."""
        with open(os.path.join(_cert_dir(), "certificate.pem"), "rb") as fh:
            current = fh.read()
        with self.assertNoLogs(zeep_signer.__name__, level="ERROR"):
            zeep_signer._warn_if_expired(current, "bundled demo service certificate")

    def test_unparseable_pin_is_reported_but_tolerated(self):
        with self.assertLogs(zeep_signer.__name__, level="WARNING") as logs:
            zeep_signer._warn_if_expired(b"not a certificate", "test")
        self.assertTrue(any("Could not parse" in line for line in logs.output))

    def test_missing_signature_returns_false_instead_of_raising(self):
        """An unsigned response is a failed verification, not an exception.

        Raising here would abort a transaction in which FINA has already issued a
        JIR - losing a document the tax authority considers issued, to report a
        problem that a log line reports just as well.
        """
        from lxml import etree

        verifier = zeep_signer.Verifier(
            cert_path=os.path.join(_cert_dir(), "certificate.pem"),
            ca_cert_path=[os.path.join(_cert_dir(), "fina_bundle.pem")],
        )
        envelope = etree.fromstring(
            b'<Envelope xmlns="http://schemas.xmlsoap.org/soap/envelope/">'
            b"<Body><RacunOdgovor/></Body></Envelope>"
        )
        with self.assertLogs(zeep_signer.__name__, level="ERROR"):
            self.assertFalse(verifier.verify_document(envelope))

    def test_plugin_records_the_verdict(self):
        """The outcome has to survive the call, or nobody ever learns of it."""
        plugin = zeep_signer.EnvelopedSignaturePlugin(
            client=SimpleNamespace(requires_signature=lambda op: True),
            signer=None,
            verifier=SimpleNamespace(verify_document=lambda env: False),
        )
        self.assertIsNone(plugin.last_verification_ok, "should start unattempted")
        plugin.ingress(envelope=None, http_headers={}, operation="racuni")
        self.assertIs(plugin.last_verification_ok, False)

    def test_plugin_survives_a_verifier_that_raises(self):
        plugin = zeep_signer.EnvelopedSignaturePlugin(
            client=SimpleNamespace(requires_signature=lambda op: True),
            signer=None,
            verifier=SimpleNamespace(
                verify_document=lambda env: (_ for _ in ()).throw(RuntimeError("boom"))
            ),
        )
        with self.assertLogs(zeep_signer.__name__, level="ERROR"):
            plugin.ingress(envelope=None, http_headers={}, operation="racuni")
        self.assertIs(plugin.last_verification_ok, False)


@tagged("post_install", "-at_install")
class TestFiscalLogProcessTime(TransactionCase):
    """The duration recorded next to each message has to be a real duration.

    It is the only continuous measurement of how long the FINA round-trip takes,
    so it decides whether the synchronous call is sustainable at POS volumes.
    """

    def _elapsed(self, delta):
        """Run _get_log_vals over a known interval and read back what it stored.

        Uses the ``delay_message`` response - the delayed-fiscalization path - so
        the log is built without a zeep response or a history plugin to stub.
        ``process_time`` is computed before that branching, so it is still the
        real code path.
        """
        from unittest.mock import patch

        company = self.env.company
        # Stands in for the fiscalized document: _get_log_vals reads only these.
        origin = SimpleNamespace(
            _name="account.move", id=1, l10n_hr_late_delivery=False, _fields={}
        )
        start = company.get_l10n_hr_time_formatted()
        stop = dict(start, time_stamp=start["time_stamp"] + delta)
        with patch.object(type(company), "get_l10n_hr_time_formatted", return_value=stop):
            vals = company._get_log_vals(
                "racuni", SimpleNamespace(), {"delay_message": True}, start, origin
            )
        return float(vals["process_time"].replace(" s", ""))

    def test_sub_millisecond_is_not_overstated(self):
        """112 us used to be stored as "0.112 s" and read as 112 ms."""
        from datetime import timedelta

        self.assertAlmostEqual(self._elapsed(timedelta(microseconds=112)), 0.000112, places=6)

    def test_a_normal_call_round_trips(self):
        from datetime import timedelta

        self.assertAlmostEqual(self._elapsed(timedelta(seconds=2.5)), 2.5, places=6)

    def test_a_negative_interval_does_not_wrap(self):
        """timedelta.seconds drops .days, so -2.237 s came out as 86397.763 s."""
        from datetime import timedelta

        self.assertAlmostEqual(self._elapsed(timedelta(seconds=-2.237)), -2.237, places=6)


@tagged("post_install", "-at_install")
class TestFiscalLogVerificationWarning(TransactionCase):
    """A failed signature verification has to reach l10n_hr.fiscal.log.

    It used to be written into error_msg *before* the response branching, and the
    error and delay branches then overwrote error_msg wholesale - so the warning
    survived only when the response was otherwise a success. That is backwards:
    an unverified signature matters most when the response was also an error,
    which is exactly when a forged or corrupted reply is most plausible.
    """

    def _error_msg(self, response):
        """Run _get_log_vals with verification reported as failed."""
        company = self.env.company
        origin = SimpleNamespace(
            _name="account.move", id=1, l10n_hr_late_delivery=False, _fields={}
        )
        msg_obj = SimpleNamespace(
            fiscal_plugin=SimpleNamespace(last_verification_ok=False)
        )
        start = company.get_l10n_hr_time_formatted()
        return company._get_log_vals("racuni", msg_obj, response, start, origin)["error_msg"]

    def test_warning_survives_a_failed_response(self):
        """The branch that overwrote it: error_message."""
        msg = self._error_msg({"error_message": "Neispravan racun"})
        self.assertIn("Neispravan racun", msg, "the original error was dropped")
        self.assertIn("could not be verified", msg, "the verification warning was lost")

    def test_warning_survives_a_delayed_response(self):
        """The other branch that overwrote it: delay_message."""
        msg = self._error_msg({"delay_message": True})
        self.assertIn("could not be verified", msg, "the verification warning was lost")

    def test_no_warning_when_verification_passed(self):
        """The check must stay quiet when the signature verified."""
        company = self.env.company
        origin = SimpleNamespace(
            _name="account.move", id=1, l10n_hr_late_delivery=False, _fields={}
        )
        msg_obj = SimpleNamespace(
            fiscal_plugin=SimpleNamespace(last_verification_ok=True)
        )
        start = company.get_l10n_hr_time_formatted()
        vals = company._get_log_vals(
            "racuni", msg_obj, {"delay_message": True}, start, origin
        )
        self.assertNotIn("could not be verified", vals["error_msg"])
