# # -*- coding: utf-8 -*-
# ##############################################################################
# #
# #    Odoo, Open Source ERP Solution
# #    Author: Uvid d.o.o.
# #    Copyright: Uvid d.o.o.
# #    web: https://uvid.hr/
# #    e-mail: info@uvid.hr
# #
# #    This program is free software: you can redistribute it and/or modify
# #    it under the terms of the GNU Affero General Public License as
# #    published by the Free Software Foundation, either version 3 of the
# #    License, or (at your option) any later version.
# #
# #    This program is distributed in the hope that it will be useful,
# #    but WITHOUT ANY WARRANTY; without even the implied warranty of
# #    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# #    GNU Affero General Public License for more details.
# #
# #    You should have received a copy of the GNU Affero General Public License
# #    along with this program.  If not, see <http://www.gnu.org/licenses/>.
# #
# ##############################################################################
# from odoo.tests import tagged
# from odoo import fields, Command
#
# from odoo.addons.account.tests.common import AccountTestInvoicingCommon
#
#
# class FiscalAccountMove(AccountTestInvoicingCommon):
#
#     @classmethod
#     def setUpClass(cls):
#         super().setUpClass()
#
#         cls.cro_company_id = cls.env['res.company'].create({
#             'name': 'CRO Company',
#             'country_id': cls.env['res.country'].search([('code', '=', 'HR')], limit=1).id
#         })
#         cls.env.user.company_ids += cls.cro_company_id
#         cls.cro_journal_id = cls.env['account.journal'].create({
#             'name': 'Sale Journal',
#             'type': 'sale',
#             'code': 'INV1',
#             'company_id': cls.cro_company_id.id
#         })
