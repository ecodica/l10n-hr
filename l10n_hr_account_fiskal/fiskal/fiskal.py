# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from datetime import datetime
from uuid import uuid4

from lxml import etree
from requests import Session
from requests.exceptions import SSLError
from zeep import Client
from zeep.plugins import HistoryPlugin
from zeep.transports import Transport

from .zeep_signer import EnvelopedSignaturePlugin, Signer, Verifier


def generate_zki(zki_datalist, signer=None):
    """
    as function so it can be called to ckeck generated ZKI without
    instanciating Fiskalizacija class
    parameteras are all strings with actual document data
    zki_datalist:
      invoice data in this order: ž
      oib, datum_vrijeme, br_racuna, oznaka_pp, oznaka_nu, ukupno_iznos
    :return: signed and hashed ZKI
    """
    return signer.sign_zki_payload("".join(zki_datalist))


def format_decimal(decimal):
    """Formats float for Fiskal communication"""
    return "%.2f" % decimal


def get_uuid():
    """recomended for fiscalization is UUID4"""
    return uuid4().hex


class Fiskalizacija:
    """
    Helper class for fiscalization requirement in Croatia
    - generates suds object, send message and handles response
    """

    def _find_all_types(self):
        url_to_ns_map = {url: ns for (ns, url) in self.client.namespaces.items()}
        return {
            f"{url_to_ns_map[t.qname.namespace]}.{t.qname.localname}": t
            for t in self.client.wsdl.types.types
            if t.qname is not None
        }

    def __init__(self, fiskal_data, **other):
        """
        :param fiskal_data: dict containing basic fiscalization data
                keys: key, cert, wsdl, ca_path, ca_list, url, test...
                generated on res.company object
        :param other: optional variables
        """
        session = Session()
        session.verify = fiskal_data["fina_bundle"]
        session.cert = (fiskal_data["cert"], fiskal_data["key"])
        transport = Transport(session=session)
        signer = Signer(cert_path=fiskal_data["cert"], key_path=fiskal_data["key"])
        verifier = Verifier(
            cert_path=fiskal_data["app_cert"],
            ca_cert_paths=[fiskal_data["fina_bundle"]],
        )
        history = HistoryPlugin()
        fiskal_plugin = EnvelopedSignaturePlugin(self, signer, verifier)
        self.client = Client(
            fiskal_data["wsdl"], transport=transport, plugins=[fiskal_plugin, history]
        )
        self.signer = signer
        self.verifier = verifier
        self.history = history
        try:
            tns = [
                ns
                for (ns, url) in self.client.namespaces.items()
                if "apis-it.hr/fin/" in url
            ][0]
        except IndexError:
            existing_namespaces = ", ".join(
                url for url in self.client.namespaces.values()
            )
            raise ValueError(
                f"APIS IT WSDL namespace not found, defined namespaces: {existing_namespaces}"
            )
        self.type_factory = self.client.type_factory(tns)
        self.all_types = self._find_all_types()

    def create_request_header(self):
        """
        Create header (tns:Zaglavlje) to attach to the request
        """
        message_id = uuid4()
        dt = datetime.now()
        return self.type_factory.ZaglavljeType(
            IdPoruke=message_id, DatumVrijeme=dt.strftime("%d.%m.%YT%H:%M:%S")
        )

    def requires_signature(self, operation):
        """
        Check whether the SOAP operation should be signed and response verified.
        This is an internal API for use by Signer and Verifier classes.
        Args:
            * operation - operation to check
        Returns:
            * True if operation should be signed/verified, False otherwise
        """
        return operation.name != "echo"

    def _call_service(self, service_proxy, req_kw):
        try:
            res = service_proxy(**req_kw)
        except Exception as E:
            if isinstance(E, SSLError):
                raise E

            try:
                doc = etree.fromstring(E.detail)
            except etree.XMLSyntaxError:
                # should not happen!!
                raise
            root = doc.find("{*}Body/*")
            if root is None:
                res = doc
            else:
                fault_response = self.client.wsdl.types.deserialize(root)
                res = fault_response
        return res

    def test_service(self, test_message="ping"):
        """
        Test service integration using the "echo" service
        Args:
            * test_message - message to use
        """
        return self.client.service.echo(test_message)

    # def send(self, method_name, data, nosend=False, raw_response=False):
    #     '''Send request'''
    #     method = getattr(self.client.service, method_name)
    #     if not method:
    #         raise ValueError('Unknown method: %s' % method_name)
    #     if method_name == 'echo':
    #         response = method(data)
    #     else:
    #         header = self.generate_header()
    #         if nosend:
    #             pre_nosend = self.client.options.nosend
    #             self.client.options.nosend = True
    #         response = method(header, data)
    #         if nosend:
    #             self.client.options.nosend = pre_nosend
    #             response = response.envelope
    #         if not raw_response:
    #             response = self.process_response(header, response)
    #     return response
