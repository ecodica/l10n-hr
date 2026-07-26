import os
import uuid
from copy import deepcopy
from hashlib import md5
import base64
import xmlsec
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
from lxml import etree

SIGNATURE_FRAGMENT = """
<Signature xmlns="http://www.w3.org/2000/09/xmldsig#">
    <SignedInfo>
        <CanonicalizationMethod Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
        <SignatureMethod Algorithm="http://www.w3.org/2001/04/xmldsig-more#rsa-sha256"/>
        <Reference>
             <Transforms>
                 <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>
                 <Transform Algorithm="http://www.w3.org/2001/10/xml-exc-c14n#"/>
             </Transforms>
             <DigestMethod Algorithm="http://www.w3.org/2001/04/xmlenc#sha256"/>
             <DigestValue></DigestValue>
        </Reference>
    </SignedInfo>
    <SignatureValue/>
</Signature>
"""


class Signer:
    def __init__(self, cert_path, key_path=None, password=None):
        if not key_path:
            key_path = cert_path

        self.xmlsec_key = self._load_xmlsec_key(key_path, password)
        self._load_xmlsec_cert(cert_path)
        self.signature_template = etree.fromstring(SIGNATURE_FRAGMENT)
        self.hazmat_key = self._load_hazmat_key(key_path, password)

    @staticmethod
    def _load_xmlsec_key(pem_path, password=None):
        if not os.path.exists(pem_path):
            raise ValueError("Company private key PEM file not found")

        try:
            key = xmlsec.Key.from_file(
                pem_path,
                xmlsec.KeyFormat.PEM,
                password=password,
            )
        except xmlsec.Error:
            raise ValueError("Cannot load private key")

        return key

    def _load_xmlsec_cert(self, pem_path):
        if not os.path.exists(pem_path):
            raise ValueError("Company certificate PEM file not found")

        try:
            self.xmlsec_key.load_cert_from_file(pem_path, xmlsec.KeyFormat.PEM)
        except xmlsec.Error:
            raise ValueError("Cannot load certificate")

    @staticmethod
    def _load_hazmat_key(pem_path, password=None):
        with open(pem_path, "rb") as key_file:
            return serialization.load_pem_private_key(
                key_file.read(),
                password=password.encode("utf-8") if password else None,
            )

    def sign_document(self, root):
        req_node = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body/*")
        # Find the XML node with the request itself (eg. RacunZahtjev)
        if req_node is None:
            raise ValueError("Unable to find request tag element")
        request_id = str(uuid.uuid4())

        # The request node needs an Id so it can be referenced from the Reference node
        req_node.attrib["Id"] = request_id
        req_node.append(deepcopy(self.signature_template))

        sig_node = xmlsec.tree.find_node(req_node, xmlsec.constants.NodeSignature)

        # Set URI attribute of the Reference node to point to the request node
        ref_node = sig_node.find("SignedInfo/Reference", namespaces=sig_node.nsmap)
        ref_node.attrib["URI"] = f"#{request_id}"

        # Add required KeyInfo/X509Data information to the signature
        key_info = xmlsec.template.ensure_key_info(sig_node)
        x509_data = xmlsec.template.add_x509_data(key_info)
        xmlsec.template.x509_data_add_issuer_serial(x509_data)
        xmlsec.template.x509_data_add_certificate(x509_data)

        ctx = xmlsec.SignatureContext()
        ctx.key = self.xmlsec_key

        # Register <request_tag>.Id as a valid Id attribute so it can be used for
        # internal references (from Reference URI)
        ctx.register_id(req_node, id_attr="Id")

        # Signing will populate the Signature subtree in-place
        ctx.sign(sig_node)

    def sign_zki_payload(self, data):
        """
        Sign raw ZKI payload using the private key
        Payload is signed using SHA1+RSA algorithm. The signature is
        hashed using MD5 digest algorithm. The resulting digest is
        returned as hexadecimal string.

        See section 12 "Zaštitni kod izdavatelja" in the Fiskalizacija technical
        specification for the description of the algorithm.

        Args:
            * data - raw ZKI data to be signed
        Returns:
            * ZKI digest calculated the standard algorithm
        """
        signature = self.hazmat_key.sign(
            data.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return md5(signature).hexdigest()


class Verifier:
    """ """

    def __init__(self, cert_path, ca_cert_path):
        if not os.path.exists(cert_path):
            raise ValueError(
                f"Fiscalization service certificate not found: {cert_path}"
            )
        try:
            self.key = xmlsec.Key.from_file(cert_path, xmlsec.KeyFormat.CERT_PEM, None)
        except xmlsec.Error:
            raise ValueError("Cannot load Fiscal service certificate")
        self.manager = xmlsec.KeysManager()
        try:
            self.manager.load_cert(
                ca_cert_path,
                xmlsec.constants.KeyDataFormatPem,
                xmlsec.constants.KeyDataTypeTrusted,
            )
        except Exception as E:  # xmlsec.Error:
            pass
            # raise ValueError(f"Cannot load CA cert {ca_cert}")

    def verify_document(self, root):
        ctx = xmlsec.SignatureContext(manager=self.manager)
        ctx.key = self.key
        req_node = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body/*")
        ctx.register_id(req_node, "Id")
        sig_node = xmlsec.tree.find_node(root, xmlsec.constants.NodeSignature)
        try:
            ctx.verify(sig_node)
        except Exception as E:
            # print(repr(E))
            pass


class BinarySigner:

    def __init__(self, cert_data, key_data=None, password=None):
        """
        Initializes the Signer with certificate and private key data.

        :param cert_data: Binary data (bytes) of the certificate in PEM format.
        :param key_data: Binary data (bytes) of the private key in PEM format.
                         If None, it defaults to cert_data (assuming bundled PEM).
        :param password: Password for the private key, if encrypted.
        """
        # If key_data is None, assume the key is bundled in cert_data
        if not key_data:
            key_data = cert_data

        # Load keys and certs from binary data
        self.xmlsec_key = self._load_xmlsec_key(key_data, password)
        self._load_xmlsec_cert(cert_data)

        self.signature_template = etree.fromstring(SIGNATURE_FRAGMENT)
        self.hazmat_key = self._load_hazmat_key(key_data, password)

    @staticmethod
    def _load_xmlsec_key(key_data, password=None):
        if password and not isinstance(password, bytes):
            password = password.encode('utf-8')
        if not key_data:
            raise ValueError("Company private key data is missing")

        try:
            key = xmlsec.Key.from_memory(base64.b64decode(key_data), xmlsec.KeyFormat.PEM,
                                         password.encode("utf-8") if password else None)
        except xmlsec.Error as e:
            raise ValueError(f"Cannot load private key from buffer: {e}")
        return key

    def _load_xmlsec_cert(self, cert_data):
        if not cert_data:
            raise ValueError("Company certificate data is missing")
        try:
            self.xmlsec_key.load_cert_from_memory(base64.b64decode(cert_data), xmlsec.KeyFormat.CERT_PEM)
        except xmlsec.Error as e:
            raise ValueError(f"Cannot load certificate from buffer: {e}")

    @staticmethod
    def _load_hazmat_key(key_data, password=None):
        if not key_data:
            raise ValueError("Company private key data is missing for hazmat loading")

        # serialization.load_pem_private_key handles bytes directly
        return serialization.load_pem_private_key(
            base64.b64decode(key_data),
            password=password.encode("utf-8") if password else None,
        )

    def sign_document(self, root):
        req_node = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body/*")
        # Find the XML node with the request itself (eg. RacunZahtjev)
        if req_node is None:
            raise ValueError("Unable to find request tag element")
        request_id = str(uuid.uuid4())

        # The request node needs an Id so it can be referenced from the Reference node
        req_node.attrib["Id"] = request_id
        req_node.append(deepcopy(self.signature_template))

        sig_node = xmlsec.tree.find_node(req_node, xmlsec.constants.NodeSignature)

        # Set URI attribute of the Reference node to point to the request node
        ref_node = sig_node.find("SignedInfo/Reference", namespaces=sig_node.nsmap)
        ref_node.attrib["URI"] = f"#{request_id}"

        # Add required KeyInfo/X509Data information to the signature
        key_info = xmlsec.template.ensure_key_info(sig_node)
        x509_data = xmlsec.template.add_x509_data(key_info)
        xmlsec.template.x509_data_add_issuer_serial(x509_data)
        xmlsec.template.x509_data_add_certificate(x509_data)

        ctx = xmlsec.SignatureContext()
        ctx.key = self.xmlsec_key

        # Register <request_tag>.Id as a valid Id attribute so it can be used for
        # internal references (from Reference URI)
        ctx.register_id(req_node, id_attr="Id")

        # Signing will populate the Signature subtree in-place
        ctx.sign(sig_node)

    def sign_zki_payload(self, data):
        """
        Sign raw ZKI payload using the private key
        Payload is signed using SHA1+RSA algorithm. The signature is
        hashed using MD5 digest algorithm. The resulting digest is
        returned as hexadecimal string.

        See section 12 "Zaštitni kod izdavatelja" in the Fiskalizacija technical
        specification for the description of the algorithm.

        Args:
            * data - raw ZKI data to be signed
        Returns:
            * ZKI digest calculated the standard algorithm
        """
        signature = self.hazmat_key.sign(
            data.encode("utf-8"),
            padding.PKCS1v15(),
            hashes.SHA1(),
        )
        return md5(signature).hexdigest()


class BinaryVerifier:
    """ """

    """
        A class to verify XML digital signatures using binary certificate data.
        """

    def __init__(self, cert_data, ca_cert_data):
        """
        Initializes the Verifier with service and CA certificate data.

        :param cert_data: Binary data (bytes) of the service certificate in PEM format.
        :param ca_cert_data: Binary data (bytes) for trusted CA certificates.
        """
        if not cert_data:
            raise ValueError("Fiscalization service certificate data is missing")

        try:
            # Load the service certificate from binary data using from_buffer
            self.key = xmlsec.Key.from_buffer(cert_data, xmlsec.KeyFormat.CERT_PEM, None)
        except xmlsec.Error as e:
            raise ValueError(f"Cannot load Fiscalization service certificate from buffer: {e}")

        self.manager = xmlsec.KeysManager()

        # Iterate over the list of CA certificate binary data
        for ca_cert_data in ca_cert_data:
            try:
                # Load the CA certificate from binary data using load_cert_from_buffer
                self.manager.load_cert_from_buffer(
                    ca_cert_data,
                    xmlsec.constants.KeyDataFormatPem,
                    xmlsec.constants.KeyDataTypeTrusted,
                )
            except Exception:
                # Keep the original behavior of silently passing on CA loading failure
                pass

    def verify_document(self, root):
        """
        Verifies the XML digital signature in the document.

        :param root: The root element of the XML document (lxml.etree._Element).
        """
        ctx = xmlsec.SignatureContext(manager=self.manager)
        ctx.key = self.key

        # Find the node to register the ID for (e.g., the payload node)
        req_node = root.find("{http://schemas.xmlsoap.org/soap/envelope/}Body/*")
        if req_node is not None:
            ctx.register_id(req_node, "Id")

        # Find the signature node
        sig_node = xmlsec.tree.find_node(root, xmlsec.constants.NodeSignature)

        if sig_node is None:
            # Handle a case where signature node isn't found
            return False  # Or raise an appropriate error

        try:
            ctx.verify(sig_node)
            return True
        except Exception:
            # Handle verification failure (e.g., log the error)
            return False


class EnvelopedSignaturePlugin:
    def __init__(self, client, signer, verifier):
        self.fiscal_client = client
        self.signer = signer
        self.verifier = verifier

    def egress(self, envelope, http_headers, operation, binding_options):
        if self.fiscal_client.requires_signature(operation):
            self.signer.sign_document(envelope)
        return envelope, http_headers

    def ingress(self, envelope, http_headers, operation):
        if self.fiscal_client.requires_signature(operation):
            try:
                self.verifier.verify_document(envelope)
            except Exception as E:
                print(E)
        return envelope, http_headers
