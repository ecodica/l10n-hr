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
from odoo.tests import tagged
from odoo.tests.common import TransactionCase
from odoo.exceptions import ValidationError


@tagged("uvid", 'l10n_hr_employee', 'l10n_hr', 'uvid_basic')
class TestEmployeeOIBConstraint(TransactionCase):

    def setUp(self):
        super().setUp()

    def test_valid_oib(self):
        employee = self.env['hr.employee'].create({
            'name': 'Valid Employee',
            'l10n_hr_oib': '12345678903',
            'active': True,
        })
        self.assertTrue(employee)

    def test_oib_length_invalid(self):
        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Short OIB',
                'l10n_hr_oib': '12345',
                'active': True,
            })

    def test_oib_not_numeric(self):
        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Non-numeric OIB',
                'l10n_hr_oib': 'ABCDEFGHIJK',
                'active': True,
            })

    def test_oib_invalid_value(self):
        with self.assertRaises(ValidationError):
            self.env['hr.employee'].create({
                'name': 'Invalid OIB',
                'l10n_hr_oib': '12345678901',
                'active': True,
            })
