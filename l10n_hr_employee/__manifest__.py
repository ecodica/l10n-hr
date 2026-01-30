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
    "name": "L10N HR Employee",
    "version": "19.0.1.0.0",
    "summary": "Adds required fields for croatia localization",
    "author": "Uvid d.o.o.",
    "category": "Human Resources/Employees",
    "website": "https://uvid.hr/",
    "maintainer": "RadovanLover",
    "contributors": ["Vladimir"],
    "license": "LGPL-3",
    "description": """
L10N HR Employee
----------------
``l10n_hr_employee``
^^^^^^^^^^^^^^^^^^^^
- Add field OIB on employee 
""",
    "depends": [
        'hr'
    ],
    "data": [
        'views/hr_employee_views.xml'
    ],
    "installable": True,
}
