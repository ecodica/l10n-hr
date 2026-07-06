# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from datetime import datetime
from pytz import timezone as tz
from uuid import uuid4

from lxml import etree
from requests import Session
from requests.exceptions import SSLError, ConnectionError
from zeep import Client, Settings, exceptions as zeep_exceptions
from zeep.plugins import HistoryPlugin
from zeep.transports import Transport

from .zeep_signer import EnvelopedSignaturePlugin, BinarySigner, Verifier


def generate_zki(zki_datalist, signer=None):
    """
    as function so it can be called to check generated ZKI without
    instantiating Fiscal class
    parameters are all strings with actual document data
    zki_datalist:
      invoice data in this order: ž
      oib, datum_vrijeme, br_racuna, oznaka_pp, oznaka_nu, ukupno_iznos
    :return: signed and hashed ZKI
    """
    return signer.sign_zki_payload("".join(zki_datalist))


def format_decimal(decimal):
    """Formats float for Fiscal communication"""
    return "%.2f" % decimal


def get_uuid():
    """recommended for fiscalization is UUID4"""
    return uuid4().hex


class Fiscalization:
    """
    Helper class for fiscalization requirement in Croatia
    - generates suds object, send messages and handles response
    """

    def _find_all_types(self):
        url_to_ns_map = {url: ns for (ns, url) in self.client.namespaces.items()}
        return {
            f"{url_to_ns_map[t.qname.namespace]}.{t.qname.localname}": t
            for t in self.client.wsdl.types.types
            if t.qname is not None
        }

    def __init__(self, data, **other):
        """
        :param data: dict containing basic fiscalization data
                keys: key, cert, wsdl, ca_path, ca_list, url, test...
                generated on res.company object
        :param other: optional variables
        """
        session = Session()
        session.verify = data["fina_bundle_path"]
        # session.cert = (data["cert"], data["key"])
        transport = Transport(session=session)
        signer = BinarySigner(cert_data=data["cert_data"], key_data=data["key_data"])
        verifier = Verifier(
            cert_path=data["app_cert_path"],
            ca_cert_path=[data["fina_bundle_path"]],
        )
        history = HistoryPlugin()
        fiscal_plugin = EnvelopedSignaturePlugin(self, signer, verifier)
        settings = Settings(raw_response=False)
        self.client = Client(data["wsdl"], transport=transport, plugins=[fiscal_plugin, history], settings=settings)
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

    def create_request_header(self, timezone='Europe/Zagreb'):
        """
        Create header (tns:Zaglavlje) to attach to the request
        """
        message_id = uuid4()
        dt = datetime.now(tz=tz(timezone))
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
        except ConnectionError as E:
            raise E
        except Exception as E:
            if isinstance(E, SSLError):
                raise E
            if isinstance(E, zeep_exceptions.ValidationError):
                raise E
            try:
                doc = etree.fromstring(E.detail)
            except zeep_exceptions.Fault:
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
