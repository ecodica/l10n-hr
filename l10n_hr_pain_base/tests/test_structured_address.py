# License AGPL-3.0 or later (http://www.gnu.org/licenses/agpl.html).

from lxml import etree

from odoo.tests.common import TransactionCase


class TestStructuredAddress(TransactionCase):
    """_generate_structured_address_block relies on partner.street_number,
    which base_address_extended computes with l10n_hr_address_split's
    splitter (see that module for the regression tests on the splitter
    itself). This checks the two are wired correctly end to end: a partner
    whose street has a leading house number or trailing whitespace - cases
    the original Odoo 17 splitter got wrong - must still produce a
    <BldgNb>, since the HR bank XSD requires a structured PstlAdr.
    """

    def setUp(self):
        super().setUp()
        self.payment_order = self.env["account.payment.order"]
        self.hr_id = self.env.ref("base.hr").id

    def _generate_postal_address(self, street):
        partner = self.env["res.partner"].create({
            "name": "Test HR Partner",
            "country_id": self.hr_id,
            "city": "Zagreb",
            "zip": "10000",
            "street": street,
        })
        parent_node = etree.Element("root")
        self.payment_order._generate_structured_address_block(
            parent_node, partner, gen_args={})
        return parent_node.find("PstlAdr")

    def test_bldgnb_present_for_leading_house_number(self):
        postal_address = self._generate_postal_address("10 Ilica")
        self.assertIsNotNone(postal_address)
        self.assertEqual(postal_address.find("StrtNm").text, "Ilica")
        self.assertEqual(postal_address.find("BldgNb").text, "10")
        self.assertIsNone(postal_address.find("AdrLine"))

    def test_bldgnb_present_with_surrounding_whitespace(self):
        postal_address = self._generate_postal_address("  Ilica 242  ")
        self.assertIsNotNone(postal_address)
        self.assertEqual(postal_address.find("StrtNm").text, "Ilica")
        self.assertEqual(postal_address.find("BldgNb").text, "242")

    def test_no_postal_address_without_city(self):
        partner = self.env["res.partner"].create({
            "name": "Test HR Partner No City",
            "country_id": self.hr_id,
            "street": "Ilica 242",
        })
        parent_node = etree.Element("root")
        self.payment_order._generate_structured_address_block(
            parent_node, partner, gen_args={})
        self.assertIsNone(parent_node.find("PstlAdr"))
