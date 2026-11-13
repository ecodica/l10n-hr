"""Transport failures keep their diagnosis and available XML evidence."""
from types import SimpleNamespace
from unittest.mock import Mock, patch

from lxml import etree
from requests.exceptions import ReadTimeout
from zeep.exceptions import Fault

from odoo.tests import TransactionCase, tagged

from ..fiscal import fiscal


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

    def test_wsdl_and_operation_timeouts_are_explicit(self):
        fake_client = Mock()
        fake_client.namespaces = {'ns0': 'http://www.apis-it.hr/fin/2012/types/f73'}
        data = {
            'fina_bundle_path': 'bundle.pem', 'cert_data': b'cert', 'key_data': b'key',
            'app_cert_path': 'server.pem', 'wsdl': 'local.wsdl',
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
