"""Transport failures keep their diagnosis and available XML evidence."""
import os
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lxml import etree
from requests.exceptions import ReadTimeout
from zeep.exceptions import Fault

from odoo.tests import TransactionCase, tagged

from ..fiscal import fiscal

# A RacunOdgovor captured from the live demo service: FINA reports a rejected
# invoice (s005 - the message OIB does not match the certificate's) over HTTP
# 500, with a signed regular response body instead of a soap:Fault.
FINA_REJECT_RESPONSE = os.path.join(
    os.path.dirname(__file__), "data", "fina_demo_racun_reject_response.xml"
)


@tagged('post_install', '-at_install')
class TestFiscalTransport(TransactionCase):

    def test_read_timeout_is_not_replaced_by_detail_attribute_error(self):
        client = fiscal.Fiscalization.__new__(fiscal.Fiscalization)
        timeout = ReadTimeout('FINA response timed out')
        with self.assertRaises(ReadTimeout) as caught:
            client._call_service(Mock(side_effect=timeout), {})
        self.assertIs(caught.exception, timeout)

    def test_soap_fault_with_parsed_detail_keeps_original_fault(self):
        client = fiscal.Fiscalization.__new__(fiscal.Fiscalization)
        fault = Fault('FINA SOAP fault', code='Server', detail=etree.Element('detail'))
        with self.assertRaises(Fault) as caught:
            client._call_service(Mock(side_effect=fault), {})
        self.assertIs(caught.exception, fault)
        self.assertEqual(caught.exception.code, 'Server')

    def test_fina_rejection_payload_is_recovered_from_fake_fault(self):
        """FINA rejects an invoice over HTTP 500 with a signed RacunOdgovor.

        There is no soap:Fault in that body, so zeep raises
        Fault("Unknown fault occured") with the whole response in ``detail``.
        The client recovers the payload instead, so the fiscal log shows
        FINA's own error (s005 and its message) rather than the generic text.
        zeep has already run the response plugins at that point, so the
        recovered payload has been signature-verified like any other reply.
        """
        client = fiscal.Fiscalization.__new__(fiscal.Fiscalization)
        with open(FINA_REJECT_RESPONSE, "rb") as fh:
            detail = fh.read()
        fake = Fault(message="Unknown fault occured", code=None, detail=detail)
        response = client._call_service(Mock(side_effect=fake), {})
        self.assertEqual(response.Greske.Greska[0].SifraGreske, "s005")
        self.assertIn("OIB", response.Greske.Greska[0].PorukaGreske)
        self.assertTrue(response.Zaglavlje.IdPoruke)
        self.assertFalse(response.Jir)

    def test_genuine_soap_fault_is_preserved_by_the_recovery(self):
        """A fault with a code is a soap fault, not FINA's error convention."""
        client = fiscal.Fiscalization.__new__(fiscal.Fiscalization)
        fault = Fault('FINA SOAP fault', code='Server', detail=etree.Element('detail'))
        with self.assertRaises(Fault) as caught:
            client._call_service(Mock(side_effect=fault), {})
        self.assertIs(caught.exception, fault)

    def test_payloadless_fake_fault_is_preserved_by_the_recovery(self):
        client = fiscal.Fiscalization.__new__(fiscal.Fiscalization)
        with self.assertRaises(Fault):
            client._call_service(
                Mock(side_effect=Fault("Unknown fault occured", code=None, detail=None)), {},
            )

    def test_wsdl_and_operation_timeouts_are_explicit(self):
        fake_client = Mock()
        fake_client.namespaces = {'ns0': 'http://www.apis-it.hr/fin/2012/types/f73'}
        data = {
            'fina_bundle_path': 'bundle.pem', 'cert_data': b'cert', 'key_data': b'key',
            'app_cert_data': b'pin', 'wsdl': 'local.wsdl',
        }
        with (
            patch.object(fiscal, 'Session') as session,
            patch.object(fiscal, 'Transport') as transport,
            patch.object(fiscal, 'BinarySigner'),
            patch.object(fiscal, 'Verifier'),
            patch.object(fiscal, 'EnvelopedSignaturePlugin'),
            patch.object(fiscal, 'Client', return_value=fake_client),
            patch.object(fiscal.Fiscalization, '_find_all_types', return_value={}),
        ):
            fiscal.Fiscalization(data)
        self.assertEqual(session.return_value.verify, 'bundle.pem')
        self.assertEqual(transport.call_args.kwargs['timeout'], 100)
        self.assertEqual(transport.call_args.kwargs['operation_timeout'], (30, 100))

    def _log_values(self, history, response):
        origin = SimpleNamespace(
            _name='test.fiscal.origin', id=1, _fields={}, l10n_hr_late_delivery=False,
        )
        message = SimpleNamespace(history=history)
        company = self.env.company
        return company._get_log_vals(
            'racuni', message, response, company.get_l10n_hr_time_formatted(), origin,
        )

    def test_error_log_retains_sent_xml_without_received_history(self):
        history = SimpleNamespace(last_sent={'envelope': etree.Element('SentRequest')})
        values = self._log_values(history, {'error_message': 'FINA response timed out'})
        self.assertIn('SentRequest', values['content'])
        self.assertFalse(values['reply_msg'])
        self.assertIn('timed out', values['error_msg'])

    def test_empty_history_does_not_hide_the_original_error(self):
        values = self._log_values(fiscal.HistoryPlugin(), {'error_message': 'No connection'})
        self.assertFalse(values['content'])
        self.assertFalse(values['reply_msg'])
        self.assertEqual(values['error_msg'], 'No connection')
