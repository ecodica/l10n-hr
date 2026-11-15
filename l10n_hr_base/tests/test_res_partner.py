from odoo.exceptions import ValidationError
from odoo.tests import TransactionCase, tagged


@tagged('post_install', '-at_install', 'audit_13')
class TestPartnerOIB(TransactionCase):

    def test_valid_croatian_registry(self):
        partner = self.env['res.partner'].create({
            'name': 'Valid Croatian OIB',
            'country_id': self.env.ref('base.hr').id,
            'company_registry': '12345678903',
        })
        self.assertEqual(partner.company_registry, '12345678903')

    def test_invalid_croatian_registry(self):
        for value in ('12345678901', '12345', 'ABCDEFGHIJK', 'HR12345678903', '12345678903 '):
            with self.subTest(value=value), self.assertRaises(ValidationError), self.cr.savepoint():
                self.env['res.partner'].create({
                    'name': 'Invalid Croatian OIB',
                    'country_id': self.env.ref('base.hr').id,
                    'company_registry': value,
                })

    def test_invalid_checksum_on_write(self):
        partner = self.env['res.partner'].create({
            'name': 'Croatian OIB write',
            'country_id': self.env.ref('base.hr').id,
            'company_registry': '12345678903',
        })
        with self.assertRaises(ValidationError), self.cr.savepoint():
            partner.company_registry = '12345678901'

    def test_foreign_registry_unaffected(self):
        partner = self.env['res.partner'].create({
            'name': 'Foreign registry',
            'country_id': self.env.ref('base.us').id,
            'company_registry': 'Foreign-registry-123',
        })
        partner.company_registry = '12345678901'
        self.assertEqual(partner.company_registry, '12345678901')
        with self.assertRaises(ValidationError), self.cr.savepoint():
            partner.country_id = self.env.ref('base.hr')

    def test_empty_croatian_registry_allowed(self):
        partner = self.env['res.partner'].create({
            'name': 'No OIB yet',
            'country_id': self.env.ref('base.hr').id,
        })
        self.assertFalse(partner.company_registry)