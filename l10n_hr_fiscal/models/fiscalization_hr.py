# -*- encoding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source ERP and CRM
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

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError
from signxml import XMLSigner, XMLVerifier, methods
from OpenSSL import crypto
import lxml.etree as ET
import xml
import xml.dom.minidom
import textwrap
import http.client
import base64
import ssl
import os


class Fiscalization(models.Model):
    _name = 'fiscalization.hr'
    _description = "Fiscalization HR"

    def nice_xml(self, xml_msg):
        if not xml_msg:
            return ""
        pretty_xml = xml.dom.minidom.parseString(xml_msg)

        new_xml = ""
        for line in pretty_xml.toprettyxml().split('\n'):
            if len(line.replace('\t', '').strip()) > 0:
                new_xml = new_xml + "\n".join(textwrap.wrap(line, 120)) + "\n"

        return new_xml

    def _post_soap_message(self, soap_message):
        company = self.env.company
        if not company.server_address:
            raise UserError(_('No server address available for current company!'))
        if not company.server_port:
            raise UserError(_('No server port available for current company!'))
        if not company.service_name:
            raise UserError(_('No service name available for current company!'))

        server_address = company.server_address + ":" + company.server_port
        service_name = "/" + company.service_name

        module_path = os.path.dirname(os.path.dirname(__file__))

        cert_file = module_path + "/data/certs/{}"
        if company.fisc_env == 'production':
            cert_file = cert_file.format('prodCAfile.pem')
        else:
            cert_file = cert_file.format('demoCAfile.pem')

        context = ssl.create_default_context(cafile=cert_file)
        context.set_ciphers('DEFAULT')

        webservice = http.client.HTTPSConnection(server_address, timeout=20, context=context)

        webservice.putrequest("POST", service_name)
        webservice.putheader("Host", company.server_address)
        webservice.putheader("User-Agent", "Python post")
        webservice.putheader("Content-type", "text/xml")
        webservice.putheader("Content-length", "%d" % len(soap_message))
        webservice.putheader("SOAPAction", "\"\"")
        webservice.endheaders()
        webservice.send(soap_message.encode('utf-8'))
        res = webservice.getresponse().read()
        webservice.close()

        return res.decode('utf-8')

    def soap_message(self, message):
        res = {}
        try:
            state = 'ok'
            response = self.soap_fisc_message_send(message)
            # provjera greske
            if response.find('<tns:Greske>') >= 0 or response.find('<env:Fault>') >= 0:
                state = 'error'
        except Exception as e:
            state = 'wrong'
            response = e

        res['state'] = state
        res['response'] = response
        return res

    def soap_fisc_message_send(self, message):
        SM_TEMPLATE = """<soapenv:Envelope
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
        xmlns:xsd="http://www.w3.org/2001/XMLSchema"
        xmlns:xsi="http://www.w3.org/2001/XMLSchemainstance">
        <soapenv:Body>
        %s
        </soapenv:Body>
        </soapenv:Envelope>
        """

        soap_message = SM_TEMPLATE % (message)
        return self._post_soap_message(soap_message)

    def soap_echo_message_send(self, message):
        SM_TEMPLATE = """
        <soapenv:Envelope 
        xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/" 
        xmlns:f73="http://www.apis-it.hr/fin/2012/types/f73">
           <soapenv:Body> 
              <f73:EchoRequest>%s</f73:EchoRequest> 
           </soapenv:Body> 
        </soapenv:Envelope> 
        """

        soap_message = SM_TEMPLATE % (message)
        return self._post_soap_message(soap_message)

    def _sanitize_cert(self, data):
        data = data.decode('utf-8')
        data = data.replace('-----BEGIN CERTIFICATE-----\n', '')
        data = data.replace('-----END CERTIFICATE-----\n', '')
        data = data.replace('\n', '')
        data.strip()
        data = data.encode('utf-8')
        return data

    def _construct_keyinfo(self, cert):

        KI_template = '''
              <KeyInfo>
              </KeyInfo>
        '''

        keyinfo = ET.fromstring(KI_template)

        cert_crypto = crypto.load_certificate(crypto.FILETYPE_PEM, cert)
        cert_raw = crypto.dump_certificate(crypto.FILETYPE_PEM, cert_crypto)
        cert_serial_int = cert_crypto.get_serial_number()
        cert_serial_text = str(cert_serial_int)

        cert_issuer = cert_crypto.get_issuer()
        cert_issuer_components = cert_issuer.get_components()
        cit = []
        for label in ['CN', 'L', 'O', 'C']:
            for comp, val_oid in cert_issuer_components:
                if comp == label:
                    cit.append("{}={}".format(comp, val_oid))

        cert_issuer_text = ', '.join(cit)

        cert_text = self._sanitize_cert(cert_raw)

        x509Data = ET.SubElement(keyinfo, 'X509Data', xmlns="http://www.w3.org/2000/09/xmldsig#")

        X509IssuerSerial = ET.SubElement(x509Data, 'X509IssuerSerial')
        X509IssuerName = ET.SubElement(X509IssuerSerial, 'X509IssuerName')
        X509IssuerName.text = cert_issuer_text
        X509SerialNumber = ET.SubElement(X509IssuerSerial, 'X509SerialNumber')
        X509SerialNumber.text = cert_serial_text

        X509Certificate = ET.SubElement(x509Data, 'X509Certificate')
        X509Certificate.text = cert_text

        # print ET.tostring(keyinfo, encoding='utf-8')
        return keyinfo

    def sign_file(self, msg, uri_id):
        company_id = self.env.company
        cert = company_id.certificate
        if not cert:
            raise UserError(_('No certificate available for current company!'))

        password = company_id.certificate_pass
        if not password:
            raise UserError(_('No certificate password available for current company!'))

        cert_64enc = company_id.certificate_pem
        key_64enc = company_id.certificate_key

        if not key_64enc:
            raise ValidationError(_('No certificate key available for current company!'))

        if not cert_64enc:
            raise ValueError(_('No certificate available for current company!'))

        key = base64.decodebytes(key_64enc)
        cert = base64.decodebytes(cert_64enc)

        root = ET.fromstring(msg)

        signer = XMLSigner(c14n_algorithm=u'http://www.w3.org/2001/10/xml-exc-c14n#', signature_algorithm="rsa-sha256",
                           digest_algorithm="sha256")

        ns = {}
        ns[None] = signer.namespaces['ds']
        signer.namespaces = ns

        keyinfo = self._construct_keyinfo(cert)

        signed_root = signer.sign(root, key=key, cert=cert, reference_uri=('#%s' % uri_id), key_info=keyinfo)
        signed_xml = ET.tostring(signed_root, encoding='utf-8')
        signed_xml_string = signed_xml.decode('utf-8')

        return signed_xml_string
