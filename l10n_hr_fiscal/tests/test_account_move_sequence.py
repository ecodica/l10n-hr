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
import re

from odoo.tests import tagged
from odoo import fields, Command
from odoo.tests.form import Form

from odoo.addons.account.tests.common import AccountTestInvoicingCommon


@tagged("uvid", 'l10n_hr_fiscal', 'l10n_hr', 'uvid_account')
class AccountMoveSequence(AccountTestInvoicingCommon):

    @classmethod
    def init_business_premise(cls, company, **kwargs):
        """
        Initializes and returns a Croatian business premise (`l10n_hr.business.premise`)
        for the given company with optional field values.

        :param company: The company to associate the business premise with.
        :param kwargs: Optional field values to pre-fill in the premise form.
        :return: Saved `l10n_hr.business.premise` record.
        """
        premise_form = Form(cls.env['l10n_hr.business.premise'].with_company(company=company))
        for key, value in kwargs.items():
            if hasattr(premise_form, key):
                setattr(premise_form, key, value)
        return premise_form.save()

    @classmethod
    def init_fiscal_device(cls, l10n_hr_business_premise_id, activate_device=False, **kwargs):
        """
        Creates and optionally activates a fiscal device for the given business premise.

        :param l10n_hr_business_premise_id: The business premise to link the device to.
        :param activate_device: Whether to activate the device.
                                It will still require business premise to be activated first
        :param kwargs: Optional field values to pre-fill in the device form.
        :return: Saved `l10n_hr.fiscal.device` record.
        """
        company_id = l10n_hr_business_premise_id.company_id
        device_form = Form(cls.env['l10n_hr.fiscal.device'].with_company(company=company_id))
        device_form.l10n_hr_business_premise_id = l10n_hr_business_premise_id
        for key, value in kwargs.items():
            if hasattr(device_form, key):
                setattr(device_form, key, value)
        device_id = device_form.save()
        if activate_device is True:
            device_id.with_company(company=company_id).button_activate_device()
        return device_id

    @classmethod
    def setUpClass(cls):
        """
        Sets up the test environment:
        - Initializes Croatian company, business premise, and fiscal device.
        - Activates premise and device.
        - Creates a sample invoice for fiscal sequence testing.
        """
        super().setUpClass()
        country_id = cls.env['res.country'].search([('code', '=', 'HR')], limit=1)
        cls.cro_company_id = cls.env['res.company'].search([('country_id', '=', country_id.id)], limit=1)
        cls.env.user.company_ids += cls.cro_company_id
        cls.business_premise = cls.init_business_premise(company=cls.cro_company_id,
                                                         l10n_hr_name='l10n_fiscal_test_by_business_premise',
                                                         l10n_hr_fiscal_code='F1',
                                                         l10n_hr_invoice_sequence_by='P')
        cls.fiscal_device = cls.init_fiscal_device(l10n_hr_business_premise_id=cls.business_premise,
                                                   activate_device=True,
                                                   l10n_hr_name='PoS-1', l10n_hr_fiscal_device_code=1)
        cls.business_premise.with_company(company=cls.cro_company_id).button_activate_premise()
        cls.fiscal_move = cls.init_invoice('out_invoice', company=cls.cro_company_id)
        cls.fiscal_move.sudo().write({
            'company_id': cls.cro_company_id.id,
            'journal_id': cls.business_premise.l10n_hr_journal_ids[0]
        })

    def test_l10n_hr_formated_sequence(self):
        """
        Tests that the `_l10n_hr_formated_sequence` method generates the correct
        initial invoice sequence format for Croatian fiscal rules.
        """
        seq = self.fiscal_move._l10n_hr_formated_sequence()
        year = self.fiscal_move.invoice_date and self.fiscal_move.invoice_date.year or fields.Date.today().year
        self.assertEqual(seq, f'0/F1/1/{year:04d}')

    def test_get_starting_sequence(self):
        """
        Verifies that the starting sequence differs between Croatian and default companies,
        ensuring localized logic is applied properly.
        """
        account_move = self.init_invoice('out_invoice')
        sequence = account_move._get_starting_sequence()
        self.env.user.company_id = self.cro_company_id
        cro_account_move = self.init_invoice('out_invoice', company=self.cro_company_id)
        cro_sequence = cro_account_move._get_starting_sequence()
        self.assertNotEqual(sequence, cro_sequence)

    def test_get_last_sequence_domain(self):
        """
        Tests that `_get_last_sequence_domain` returns a correct domain string
        for querying the last used invoice sequence, both by journal and by business premise.
        """
        business_premise_by_n = self.init_business_premise(self.cro_company_id,
                                                           l10n_hr_name='l10n_fiscal_test_by_device',
                                                           l10n_hr_fiscal_code='F2',
                                                           l10n_hr_invoice_sequence_by='N')
        fiscal_device = self.init_fiscal_device(l10n_hr_business_premise_id=business_premise_by_n,
                                                activate_device=True,
                                                l10n_hr_name='PoS-1', l10n_hr_fiscal_device_code=2)
        business_premise_by_n.with_company(company=self.cro_company_id).button_activate_premise()
        account_move_hr_by_n = self.init_invoice('out_invoice', company=self.cro_company_id,
                                                 journal=business_premise_by_n.l10n_hr_journal_ids[0])

        hr_where_str_by_n, hr_parm_by_n = account_move_hr_by_n._get_last_sequence_domain()
        hr_where_str, hr_parm = self.fiscal_move._get_last_sequence_domain()
        self.assertIn('journal_id in', hr_where_str)
        self.assertIn('journal_id = ', hr_where_str_by_n)

    def test_compute_compute_made_sequence_gap(self):
        """
        Validates that no false gaps in invoice numbering are detected when posting
        sequential invoices across multiple journals and business premises.
        Also verifies expected naming for sequences. ( def _get_last_sequence )
        """
        partner = self.env['res.partner'].search([], limit=1)
        product = self.env['product.product'].search([], limit=1)
        self.fiscal_device = self.init_fiscal_device(l10n_hr_business_premise_id=self.business_premise,
                                                     activate_device=True,
                                                     l10n_hr_name='PoS-2', l10n_hr_fiscal_device_code=2)
        first_invoice_by_journal_and_business_premise = self.init_invoice('out_invoice', company=self.cro_company_id,
                                                                          journal=
                                                                          self.business_premise.l10n_hr_journal_ids[0],
                                                                          partner=partner,
                                                                          products=product)
        second_invoice_by_journal_and_business_premise = self.init_invoice('out_invoice', company=self.cro_company_id,
                                                                           journal=
                                                                           self.business_premise.l10n_hr_journal_ids[0],
                                                                           partner=partner,
                                                                           products=product)
        first_invoice_by_journal_and_third_by_business_premiss = self.init_invoice('out_invoice',
                                                                                   company=self.cro_company_id,
                                                                                   journal=self.business_premise.
                                                                                   l10n_hr_journal_ids[1],
                                                                                   partner=partner,
                                                                                   products=product)
        first_invoice_by_journal_and_business_premise.action_post()
        second_invoice_by_journal_and_business_premise.action_post()
        first_invoice_by_journal_and_third_by_business_premiss.action_post()
        year = first_invoice_by_journal_and_third_by_business_premiss.invoice_date.year or False
        year = year or fields.Date.today().year

        self.assertFalse(first_invoice_by_journal_and_business_premise.made_sequence_gap)
        self.assertFalse(second_invoice_by_journal_and_business_premise.made_sequence_gap)
        self.assertFalse(first_invoice_by_journal_and_third_by_business_premiss.made_sequence_gap)
        self.assertEqual(f'3/F1/2/{year:04d}', first_invoice_by_journal_and_third_by_business_premiss.name)

    def test_sequence_yearly_regex(self):
        """
        Tests that the regex pattern used for parsing invoice numbers (`_sequence_yearly_regex`)
        is valid and compatible with Croatian invoice formats. Ensures it matches expected formats
        and does not raise errors when matching empty or actual values.
        """
        self.assertEqual(r'^(?P<prefix1>.*?)(?P<year>((?<=\D)|(?<=^))((19|20|21)?\d{2}))(?P<prefix2>\D+?)(?P<seq>\d*)(?P<suffix>\D*?)$',
                         self.env['account.move']._sequence_yearly_regex)

        self.env.user.company_id = self.cro_company_id
        self.assertEqual(
            r'^(?P<seq>\d*)/?(?P<prefix1>/[^/]*)?(?P<suffix>/[^.]/)?(?P<year>19\d{2}|20\d{2}|21\d{2}|22\d{2})?$',
            self.env['account.move']._sequence_yearly_regex)

        regex = self.fiscal_move._sequence_yearly_regex
        name = self.fiscal_move._l10n_hr_formated_sequence(15)

        test_regex = self.fiscal_move._make_regex_non_capturing(regex.replace(r"?P<seq>", ""))
        matching = re.match(test_regex, name)
        empty_matching = re.match(test_regex, '')

        self.assertIsNotNone(matching)
        self.assertIsNotNone(empty_matching)

        # Ensure slicing does not raise an exception even when match is empty
        # temp_var is here to stop pycharm from complaining
        temp_var = name[:matching.start(1)]
        temp_var = ''[:empty_matching.start(1)]

        self.assertEqual(15, int(matching.group(1) or 0))
        self.assertEqual(0, int(empty_matching.group(1) or 0))

        match_name = re.match(regex, name)
        requirements = ['seq', 'year']
        self.assertTrue(all(match_name.groupdict().get(req) is not None for req in requirements))
