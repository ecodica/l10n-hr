# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from odoo.tests.common import TransactionCase


class TestStreetSplit(TransactionCase):
    """Regression tests for hr_street_split / _compute_street_data override.

    The first block reuses the upstream Odoo 19 base_address_extended test
    vectors, so the splitter port cannot silently regress on them. The second
    block covers Croatian address shapes that Odoo 17's original splitter
    got wrong, plus the non-numeric door designations Odoo 19 would drop.
    """

    def test_upstream_v19_vectors(self):
        mx_id = self.env.ref('base.mx').id
        partner = self.env['res.partner'].create({'name': 'Test Address', 'country_id': mx_id})

        values = [
            ['', '', '', ''],
            ['Place Royale', 'Place Royale', '', ''],
            ['Chaussee de Namur 40a - 2b', 'Chaussee de Namur', '40a', '2b'],
            ['Chaussee de Namur 1', 'Chaussee de Namur', '1', ''],
            ['40 Chaussee de Namur', 'Chaussee de Namur', '40', ''],
            ['Chaussee de Namur, 40 - Apt 2b', 'Chaussee de Namur', '40', 'Apt 2b'],
            ['header Chaussee de Namur, 40 trailer ', 'header Chaussee de Namur', '40', ''],
            ['\nCl 53\n # 43 - 81', 'Cl 53\n #', '43', '81'],
            ['Street Line 1\nNumber Line 2 44 76', 'Street Line 1\nNumber Line 2 44', '76', ''],
            ['1600 Pennsylvania Ave NW, Apt 4B', 'Pennsylvania Ave NW', '1600', 'Apt 4B'],
            ['10, Rue de la Paix', 'Rue de la Paix', '10', ''],
            ['Calle Gran Vía, 42, 3º Dcha', 'Calle Gran Vía', '42', '3º Dcha'],
            ['Jean-Baptiste-Lebas 12 - A-3', 'Jean-Baptiste-Lebas', '12', 'A-3'],
            ['Jean-Baptiste-Lebas, 12 / A-3', 'Jean-Baptiste-Lebas', '12', 'A-3'],
            ['1-7-1 Nagatacho, Chiyoda-ku, Apt 3', 'Nagatacho, Chiyoda-ku', '1-7-1', 'Apt 3'],
        ]

        for street, name, number, number2 in values:
            partner.street = street
            self.assertEqual(partner.street_name, name)
            self.assertEqual(partner.street_number, number)
            self.assertEqual(partner.street_number2, number2)

    def test_croatian_addresses(self):
        hr_id = self.env.ref('base.hr').id
        partner = self.env['res.partner'].create({'name': 'Test HR Address', 'country_id': hr_id})

        values = [
            # street, expected street_name, street_number, street_number2
            ['Ilica 242', 'Ilica', '242', ''],
            ['Ulica grada Vukovara 269d', 'Ulica grada Vukovara', '269d', ''],
            ['Savska cesta 32/II', 'Savska cesta', '32/II', ''],
            ['Trg bana Josipa Jelačića 1', 'Trg bana Josipa Jelačića', '1', ''],
            ['Obala kralja Petra Krešimira IV 1', 'Obala kralja Petra Krešimira IV', '1', ''],
            # Odoo 17's regex failed on these: leading number and trailing whitespace.
            ['10 Ilica', 'Ilica', '10', ''],
            ['  Ilica 242  ', 'Ilica', '242', ''],
            # No house number at all must stay empty, not be misparsed.
            ['Ilica bb', 'Ilica bb', '', ''],
            # Non-numeric door designation: Odoo 19 alone would drop this.
            ['Heinzelova 62a - prizemlje', 'Heinzelova', '62a', 'prizemlje'],
            ['Vukovarska 271 - potkrovlje', 'Vukovarska', '271', 'potkrovlje'],
            ['Ilica 1 - A', 'Ilica', '1', 'A'],
        ]

        for street, name, number, number2 in values:
            partner.street = street
            self.assertEqual(
                partner.street_name, name,
                'Wrongly formatted street name for %r: expected %r, received %r'
                % (street, name, partner.street_name))
            self.assertEqual(
                partner.street_number, number,
                'Wrongly formatted street number for %r: expected %r, received %r'
                % (street, number, partner.street_number))
            self.assertEqual(
                partner.street_number2, number2,
                'Wrongly formatted street number2 for %r: expected %r, received %r'
                % (street, number2, partner.street_number2))
