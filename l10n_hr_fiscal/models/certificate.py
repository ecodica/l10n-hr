# -*- coding: utf-8 -*-
##############################################################################
#
#    Odoo, Open Source ERP Solution
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
# import base64
# from typing import Union, Tuple, List
# from odoo.fields import _String
# from cryptography import x509
# from cryptography.x509 import Certificate
# from cryptography.hazmat.primitives.asymmetric.types import PrivateKeyTypes
# from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption, \
#     load_pem_private_key
#
######  It was decided to copy the old fiscal, so this is no longer needed. #####
###### Leaving it here in case it's needed in the future. #####
# class FiscalCertificate(_String):
#     """
#     A custom Odoo field for handling fiscal certificates (e.g., PKCS12 or PEM formats).
#
#     This field extends the standard Odoo `_String` field to enable transparent parsing,
#     conversion, and validation of certificate data, including support for both private
#     keys and public certificates in PEM format.
#
#     Attributes:
#         type (str): Specifies the base field type as 'text'.
#         _column_type (tuple): Declares the SQL column type as a text field.
#         certificate_type (str): Indicates the type of certificate being handled, either 'PK' for private key or 'PEM' for public certificate.
#         encoding (Encoding): Specifies the encoding used (PEM by default).
#         privateFormat (PrivateFormat): Defines the serialization format for private keys.
#         encryption: Encryption method for private key serialization (NoEncryption by default).
#
#     Methods:
#         process_certificate_file(file, password):
#             Static method that decodes a PKCS12 file and extracts the private key, main certificate,
#             and any additional certificates.
#
#         convert_to_pem(cert, additional_cert):
#             Class method that serializes a certificate and its additional chain into PEM format.
#
#         _convert_cache(value):
#             Converts and serializes a value to be stored in the Odoo field cache, based on its type.
#
#         _convert(value):
#             Parses and reconstructs certificate objects from their serialized (string) form.
#
#         convert_to_column(value, record, values=None, validate=True):
#             Prepares the value to be stored in the database column, converting bytes to UTF-8 strings.
#
#         convert_to_cache(value, record, validate=True):
#             Wrapper for _convert_cache, integrated into Odoo's cache conversion pipeline.
#
#         convert_to_record(value, record):
#             Converts stored database values back into usable certificate or key objects.
#     """
#     type = 'text'
#     _column_type = ('text', 'text')
#
#     certificate_type = None
#     encoding = Encoding.PEM
#     privateFormat = PrivateFormat.PKCS8
#     encryption = NoEncryption()
#
#     @staticmethod
#     def process_certificate_file(file: Union[str, bytes], password: Union[str, bytes]) -> Tuple[
#         PrivateKeyTypes, Certificate, List[Certificate]]:
#         if isinstance(file, str):
#             file = base64.b64decode(file)
#         if isinstance(password, str):
#             password = bytes(password, 'utf-8')
#         return pkcs12.load_key_and_certificates(file, password)
#
#     @classmethod
#     def convert_to_pem(cls, cert: Certificate, additional_cert: {Certificate}) -> Certificate:
#         cert_dump = cert.public_bytes(cls.encoding)
#         for node in additional_cert:
#             cert_dump += node.public_bytes(cls.encoding)
#         return x509.load_pem_x509_certificate(cert_dump)
#
#     def _convert_cache(self, value: Union[PrivateKeyTypes, Certificate, str]) -> str:
#         if not value:
#             return None
#         if self.certificate_type == 'PK':
#             return str(value.private_bytes(self.encoding, self.privateFormat, self.encryption), 'utf-8')
#         elif self.certificate_type == 'PEM':
#             return str(value.public_bytes(self.encoding), 'utf-8')
#         else:
#             return value
#
#     def _convert(self, value: str) -> Union[PrivateKeyTypes, Certificate, str, None, bytes]:
#         if not value:
#             return None
#         if self.certificate_type == 'PK':
#             return load_pem_private_key(bytes(value, 'utf-8'), None)
#         elif self.certificate_type == 'PEM':
#             return x509.load_pem_x509_certificate(bytes(value, 'utf-8'))
#         else:
#             return value
#
#     def convert_to_column(self, value, record, values=None, validate=True):
#         if value is None:
#             return None
#         if isinstance(value, bytes):
#             return str(value, 'utf-8')
#         return value
#
#     def convert_to_cache(self, value, record, validate=True):
#         return self._convert_cache(value)
#
#     def convert_to_record(self, value, record):
#         if not value or value == 'false':
#             return None
#         return self._convert(value)
