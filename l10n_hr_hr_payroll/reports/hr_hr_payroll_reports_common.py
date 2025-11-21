# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from ..models import payroll_common as paycom
from odoo.tools import DEFAULT_SERVER_DATE_FORMAT as DF

class HrHrPayrollReportsCommon(models.AbstractModel):
    _name = 'hr.hr.payroll.reports.common'
    _description = 'This class is used to define common methods for payroll reports'

    def _date_format(self, lang=None):
        """
        lang is optional, if it is not passed, language will be taken from current user
        implemented because when cron job runs -> user is OdooBot
        """
        lang = lang or self.env.user.lang
        return self.env['res.lang'].search([('code', '=', lang)], limit=1).date_format or DF
        
    def _time_format(self, lang=None):
        """
        lang is optional, if it is not passed, language will be taken from current user
        implemented because when cron job runs -> user is OdooBot
        """
        lang = lang or self.env.user.lang
        return self.env['res.lang'].search([('code', '=', lang)], limit=1).time_format
        
    def get_employee_address(self, emp):
        """
        @emp: employee record
        Return desired address format for reports.
        """
        city = emp.city.name
        if not emp.street:
            return city
        return city + ', ' + emp.street
        
    def get_company_address(self, company):
        """
        @company: company record
        Return desired address format for reports.
        """
        city = company.city_id.name
        if not company.street:
            return city
        return city + ', ' + company.street

    def get_brutto2_query_data(self):
        struct_obj = self.env['hr.payroll.structure']
        structures_with_contributions_only_codes = ['HR3', 'HR4', 'HR13']
        structures_with_contributions_only_ids = struct_obj.search([('code', 'in', structures_with_contributions_only_codes)]).ids
        structures_with_contributions_only = tuple(structures_with_contributions_only_ids)
        work_abroad_ino_tax_struct_codes = ['HR16', 'HR18']
        work_abroad_ino_tax_struct_ids = struct_obj.search([('code', 'in', work_abroad_ino_tax_struct_codes)]).ids
        work_abroad_ino_tax_struct = tuple(work_abroad_ino_tax_struct_ids)
        exception_struct_ids = structures_with_contributions_only + work_abroad_ino_tax_struct
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        brutto_2 = payroll_conf.get_rules('brutto_2')      
        doprinosi_iz_place = payroll_conf.get_rules('doprinosi_iz_place')
        doprinosi_na_placu = payroll_conf.get_rules('doprinosi_na_placu')
        izaslani_porez_ino_neto = payroll_conf.get_rules('izaslani_porez_ino_neto')
        dodaci_neto = payroll_conf.get_rules('dodaci_neto')
        bolovanje_fond = payroll_conf.get_rules('bolovanje_fond')
        doprinosi = doprinosi_iz_place + doprinosi_na_placu
        work_abroad_ino_tax_rules = doprinosi + izaslani_porez_ino_neto + dodaci_neto + bolovanje_fond
        query_data = {
            'brutto_2': brutto_2,
            'structures_with_contributions_only_ids': paycom.get_ids_sql_condition(structures_with_contributions_only_ids),
            'doprinosi': doprinosi,
            'work_abroad_ino_tax_struct': work_abroad_ino_tax_struct,
            'exception_struct_ids': exception_struct_ids,
            'work_abroad_ino_tax_rules': work_abroad_ino_tax_rules
        }
        return query_data