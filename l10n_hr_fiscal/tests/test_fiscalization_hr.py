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
from odoo.tests import tagged, TransactionCase
from odoo import fields, Command
from odoo.tests.form import Form


@tagged("post_install", "-at_install", "uvid", 'l10n_hr_fiscal', 'l10n_hr', 'uvid_account')
class TestFiscalization(TransactionCase):

    def test_empty_input(self):
        self.assertEqual(self.env['fiscalization.hr'].nice_xml(""), "")

    def test_basic_xml(self):
        input_xml = "<root><child>value</child></root>"
        result = self.env['fiscalization.hr'].nice_xml(input_xml)
        self.assertIn("<root>", result)
        self.assertIn("<child>value</child>", result)
        self.assertIn("</root>", result)
        self.assertTrue(result.startswith('<?xml'))

    def test_pretty_xml(self):
        input_xml = """<?xml version="1.0" ?><root><child>value</child></root>"""
        result = self.env['fiscalization.hr'].nice_xml(input_xml)
        self.assertIn("<root>", result)
        self.assertIn("child", result)
        self.assertTrue(result.count('\n') > 1)  # Should have line breaks

    def test_malformed_xml(self):
        with self.assertRaises(Exception):
            self.env['fiscalization.hr'].nice_xml("<root><child>value</root>")
