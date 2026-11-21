# License LGPL-3.0 or later (https://www.gnu.org/licenses/lgpl.html).
from datetime import datetime
from pytz import timezone as tz
from types import SimpleNamespace
from uuid import uuid4

from lxml import etree
from requests import Session
from zeep import Client, Settings
from zeep.exceptions import Fault
from zeep.plugins import HistoryPlugin
from zeep.transports import Transport

from .zeep_signer import EnvelopedSignaturePlugin, BinarySigner, Verifier, SOAP_ENV_NS


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
        transport = Transport(
            session=session,
            timeout=100,
            operation_timeout=(30, 100),
        )
        signer = BinarySigner(cert_data=data["cert_data"], key_data=data["key_data"])
        verifier = Verifier(cert_data=data["app_cert_data"])
        history = HistoryPlugin()
        fiscal_plugin = EnvelopedSignaturePlugin(self, signer, verifier)
        settings = Settings(raw_response=False)
        self.client = Client(data["wsdl"], transport=transport, plugins=[fiscal_plugin, history], settings=settings)
        self.signer = signer
        self.verifier = verifier
        self.history = history
        # Per-call mutable state, like `history`: carries last_verification_ok, which
        # res.company._get_log_vals reads afterwards. Not safe to share between threads.
        self.fiscal_plugin = fiscal_plugin
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
        """Call the FINA operation and return its response object.

        FINA reports a rejected request over HTTP 500 with a signed, regular
        response body - ``Greske`` inside ``RacunOdgovor`` - instead of a
        soap:Fault, so zeep raises ``Fault("Unknown fault occured")`` carrying
        the whole response in ``detail``. That payload is recovered here so the
        caller logs FINA's own error (s005 and friends) instead of the generic
        message. A genuine soap fault (code set), or a fault without a usable
        payload, is re-raised unchanged for the wrapper to diagnose.
        """
        try:
            return service_proxy(**req_kw)
        except Fault as fault:
            payload = self._fault_response(fault)
            if payload is None:
                raise
            return payload

    @staticmethod
    def _fault_response(fault):
        """The FINA payload hidden in zeep's generic fault, or None.

        zeep runs the response plugins (signature verification included)
        before it detects the HTTP error, so a payload recovered here has been
        verified like any other response.
        """
        if fault.code is not None or not fault.detail:
            return None
        try:
            document = (
                fault.detail
                if isinstance(fault.detail, etree._Element)
                else etree.fromstring(fault.detail)
            )
        except etree.XMLSyntaxError:
            return None
        body = document.find(f"{{{SOAP_ENV_NS}}}Body")
        payload = body[0] if body is not None and len(body) else None
        if payload is None:
            return None
        tns = etree.QName(payload).namespace

        def text_of(parent, tag):
            return parent.findtext(f"{{{tns}}}{tag}") if parent is not None else None

        zaglavlje = payload.find(f"{{{tns}}}Zaglavlje")
        greske = payload.find(f"{{{tns}}}Greske")
        errors = [
            SimpleNamespace(
                SifraGreske=greska.findtext(f"{{{tns}}}SifraGreske"),
                PorukaGreske=(greska.findtext(f"{{{tns}}}PorukaGreske") or "")
                .replace("\t", "")
                .replace("\n", ""),
            )
            for greska in (greske.iterfind(f"{{{tns}}}Greska") if greske is not None else [])
        ]
        poruka = payload.find(f"{{{tns}}}PorukaOdgovora")
        return SimpleNamespace(
            Zaglavlje=SimpleNamespace(
                IdPoruke=text_of(zaglavlje, "IdPoruke"),
                DatumVrijeme=text_of(zaglavlje, "DatumVrijeme"),
            ) if zaglavlje is not None else None,
            Greske=SimpleNamespace(Greska=errors) if errors else None,
            Jir=text_of(payload, "Jir"),
            PorukaOdgovora=SimpleNamespace(
                SifraPoruke=text_of(poruka, "SifraPoruke"),
                Poruka=text_of(poruka, "Poruka"),
            ) if poruka is not None else None,
        )

    def test_service(self, test_message="ping"):
        """
        Test service integration using the "echo" service
        Args:
            * test_message - message to use
        """
        return self.client.service.echo(test_message)
