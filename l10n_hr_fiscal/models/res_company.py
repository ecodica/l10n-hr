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
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError, UserError
import base64
from cryptography.hazmat.primitives.serialization import pkcs12, Encoding, PrivateFormat, NoEncryption, \
    load_pem_private_key
# from .certificate import FiscalCertificate


class Company(models.Model):
    _inherit = 'res.company'

    use_fiscalization = fields.Boolean(string='Use fiscalization?', default=False)
    fisc_env = fields.Selection([('none', 'Inactive'), ('test', 'Test'), ('production', 'Production')],
                                string='Fiscalization Environment', copy=False, required=True, default='none')
    fisc_paid_invoice = fields.Boolean(string='Automatic Fiscalization', default=False,
                                       help='Fiscalize automatically as soons as the invoice moves to the paid state.')
    fisc_use_logged_user = fields.Boolean(string='Fiscalize as logged in user', default=False,
                                          help='Fiscalize as logged in user, otherwise will use the sales person from the invoice.')

    certificate = fields.Binary(string='Certificate PFX')
    certificate_pass = fields.Char(string='Certificate password', size=64)
    # certificate_pem = FiscalCertificate(string='Certificate PEM', certificate_type='PEM')
    # certificate_key = FiscalCertificate(string='Certificate KEY', certificate_type='PK')
    certificate_pem = fields.Binary(string='Certificate PEM')
    certificate_key = fields.Binary(string='Certificate KEY')

    server_address = fields.Char(string='Server address', size=64)
    server_port = fields.Char(string='Server port', size=8)
    service_name = fields.Char(string='WEB Service name', size=64)
    echo_message = fields.Char('Echo Message', readonly=True, copy=False)

    vat_system = fields.Selection([('yes', 'Yes'), ('no', 'No')], string='In VAT system', required=True, default='yes')
    default_payment_note = fields.Char(string='Default payment note on invoices', translate=True)
    tax_note = fields.Char('Tax note')

    @api.onchange('fisc_env')
    def _onchange_fisc_env(self):
        self.server_port = '8449' if self.fisc_env != 'none' else ''
        if self.fisc_env == 'test':
            self.server_address = 'cistest.apis-it.hr'
            self.service_name = 'FiskalizacijaServiceTest'
        elif self.fisc_env == 'production':
            self.server_address = 'cis.porezna-uprava.hr'
            self.service_name = 'FiskalizacijaService'
        else:
            self.server_address = ''
            self.service_name = ''

    def button_test_fiscalization_echo(self):
        res = fields.Datetime.context_timestamp(self, fields.Datetime.now()).strftime("%Y-%m-%d %H:%M:%S")
        test_message = 'TEST FISCALIZATION!'
        echo_reply = self.env['fiscalization.hr'].soap_echo_message_send(test_message)
        if test_message in echo_reply:
            res += _(' Fiscalization ECHO test successful!')
        else:
            res += _(' Fiscalization ECHO test failed!')
        return self.write({'echo_message': res})

    def write(self, values):
        # pfx_cert = values.get('certificate')
        # password = values.get('certificate_pass') or self.env.company.certificate_pass
        # if pfx_cert and password:
        #     private_key, cert, additional_cet = FiscalCertificate.process_certificate_file(pfx_cert, password)
        #     values.update({
        #         'certificate_key': private_key,
        #         'certificate_pem': FiscalCertificate.convert_to_pem(cert, additional_cet)
        #     })
        # return super().write(values)
        pfx_cert = values.get('certificate', False)
        if pfx_cert:
            pfx_cert_decoded = base64.b64decode(pfx_cert)
            if not self.env.company.certificate_pass and not values.get('certificate_pass', False):
                raise UserError(_('Password is required for converting the certificate file!'))

            password = values.get('certificate_pass', False)
            if not password:
                password = self.env.company.certificate_pass

            # p12 = crypto.load_pkcs12(pfx_cert_decoded, bytes(password, 'utf-8'))
            p12 = pkcs12.load_key_and_certificates(pfx_cert_decoded, bytes(password, 'utf-8'))
            pem_pkey = p12[0]
            pem_cert = p12[1]
            cert_chain = p12[2]

            pkey_dump = pem_pkey.private_bytes(Encoding.PEM, PrivateFormat.PKCS8, NoEncryption())
            pkey_encoded = base64.b64encode(pkey_dump)

            cert_dump = pem_cert.public_bytes(Encoding.PEM)
            for node in cert_chain:
                cert_dump += node.public_bytes(Encoding.PEM)

            # dodajem private key na pocetak
            cert_dump = pkey_dump + cert_dump
            cert_encoded = base64.b64encode(cert_dump)

            values.update({'certificate_key': pkey_encoded})
            values.update({'certificate_pem': cert_encoded})

        return super().write(values)
