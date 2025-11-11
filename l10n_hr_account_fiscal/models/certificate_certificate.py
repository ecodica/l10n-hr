from odoo import fields, models, api
from cryptography import x509
from cryptography.x509 import ObjectIdentifier
from cryptography.hazmat.primitives.serialization import pkcs12
import base64


class Certificate(models.Model):
    _inherit = 'certificate.certificate'

    scope = fields.Selection(
        selection_add=[
            ('fina', 'Fina'),
        ],
    )
    l10n_hr_type = fields.Selection(
        selection=[
            ("prod", "Prod"),
            ("demo", "Demo"),
            ("other", "Other/Unknown"),
        ],
        readonly=False,
        string="FINA type"
    )
    l10n_hr_subject_vat = fields.Char('Subject VAT', readonly=True)

    @api.depends('content', 'pkcs12_password')
    def _compute_pem_certificate(self):
        res = super()._compute_pem_certificate()
        for certificate in self:
            certificate.l10n_hr_subject_vat = False
            if certificate.content:
                content = base64.b64decode(certificate.with_context(bin_size=False).content)
                cert = None
                # Try to load the certificate in different format starting with DER then PKCS12 and
                # finally PEM. If none succeeded, we report an error.
                try:
                    cert = x509.load_der_x509_certificate(content)
                except ValueError:
                    pass
                if not cert:
                    try:
                        pkcs12_password = certificate.pkcs12_password.encode(
                            'utf-8') if certificate.pkcs12_password else None
                        _key, cert, _additional_certs = pkcs12.load_key_and_certificates(content, pkcs12_password)
                    except ValueError:
                        pass
                if not cert:
                    try:
                        cert = x509.load_pem_x509_certificate(content)
                    except ValueError:
                        pass
                if cert:
                    try:
                        subject_vat = cert.subject.get_attributes_for_oid(ObjectIdentifier('2.5.4.97'))
                        certificate.l10n_hr_subject_vat = subject_vat[0].value if subject_vat else ""
                    except ValueError:
                        pass
        return res
