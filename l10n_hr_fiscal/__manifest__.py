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
{
    "name": "Croatian Fiscalization",
    "version": "18.0.0.0.0",
    "summary": "Croatian fiscalisation for invoices",
    "author": "Uvid d.o.o.",
    "category": "Accounting/Accounting",
    "website": "https://uvid.hr/",
    "maintainer": "RadovanLover",
    "contributors": ["Vladimir"],
    "license": "LGPL-3",
    "description": """
Croatian Fiscalization
----------------------
``l10n_hr_fiscal``
^^^^^^^^^^^^^^^^^^

Adds Croatian Fiscalization
""",
    "depends": [
        'base',
        'l10n_hr_account_base',
        'l10n_hr',
        'l10n_hr_employee'
    ],
    'external_dependencies': {
        'python': ['signxml']
    },
    "data": [
        'security/ir.model.access.csv',
        'views/res_company_view.xml',
        'views/account_move_view.xml',
        'views/hr_employee_view.xml',
        'views/account_tax_view.xml',
        'data/tax_administration_data_hr.xml',
        'report/report_invoice.xml'
    ],
    "installable": True,
}
