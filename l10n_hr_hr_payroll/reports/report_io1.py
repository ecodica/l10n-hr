# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from ..models import payroll_common as paycom
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_date

class HrPayslipIO1Report(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_io1'
    _description = 'IO1 report'

    @api.model
    def _get_report_values(self, slip_ids, data=None):
        Config = self.env['res.config.settings']
        obj_name = 'hr.payslip'
        slips = self.env[obj_name].browse(slip_ids)
        slip_data={}
        for slip in slips:
            employee = slip.employee_id
            if self.check_if_rules_exist(slip, ['OTPO', 'OTPN', 'GON', 'GONPR']):
                severance_data = self.get_severance_data(slip.payslip_run_id.id, [employee.id])
                slip_data[employee.id] = self.get_payslip_data(slip, employee, slip.payslip_run_id, severance_data, Config)
        
        company = self.env.user.company_id
        company_data = self.get_company_data(company)
        return {
            'doc_ids': slip_ids,
            'doc_model': obj_name,
            'docs': slips,
            'data': slip_data,
            'payroll_prec': self.env['decimal.precision'].precision_get('Payroll'),
            'display_secondary_currency': Config._display_secondary_currency(),
            'secondary_currency': Config._get_secondary_currency(),
            'secondary_currency_rate_text': Config._secondary_currency_rate_text(),
            'secondary_currency_amount_column_label': Config._secondary_currency_amount_text(),
            'company_data': company_data,
            'currency': company.currency_id,
            'print_date': self.format_date(slips[0].payslip_run_id.pay_date),
        }
    
    def get_payslip_data(self, slip, employee, run_id, severance_data, Config):
        tax_calculation = self.get_tax_calculations(severance_data[0])
        slip_has_severance = self.check_if_rules_exist(slip, ['OTPO', 'OTPN'])
        slip_has_unused_leave = self.check_if_rules_exist(slip, ['GON', 'GONPR'])
        data = {}
        data['name'] = employee.name
        data['oib'] = employee.oib
        data['address'] = self.get_employee_address(slip)
        data['bank_account'] = slip.bank_account_id.acc_number
        data['bank_name'] = slip.bank_account_id.bank_id.name
        data['protected_bank_account'] = slip.protected_bank_account_id.acc_number
        data['protected_bank_name'] = slip.protected_bank_account_id.bank_id.name
        data['year_start'] = slip.severance_from_year
        data['year_end'] = slip.severance_to_year

        data['work_years'] = slip.number_of_years_severance if slip_has_severance else 0 #2.1
        data['gross_salary'] = slip.average_gross_salary if slip_has_severance else 0 #2.2
        data['calc_elem_gross_salary'] = slip.calc_elem_average_gross_salary if slip_has_severance else '' #2.2
        data['trecina_place'] = slip.average_gross_salary_third if slip_has_severance else 0 #2.3
        data['calc_elem_trecina_place'] = slip.calc_elem_average_gross_salary_third if slip_has_severance else '' #2.3
        data['druga_mjerila'] = slip.severance_pay_other_criteria if slip_has_severance else 0 #2.4
        data['calc_elem_druga_mjerila'] = slip.calc_elem_severance_pay_other_criteria if slip_has_severance else '' #2.4
        data['neoporezivi_iznos'] = severance_data[0]['neoporezivi_iznos'] if slip_has_severance else 0 #3.1
        data['oporezivi_iznos'] = severance_data[0]['oporezivi_iznos'] if slip_has_severance else 0 #3.2
        data['iznos_otpremnine'] = (data['neoporezivi_iznos'] + data['oporezivi_iznos']) if slip_has_severance else 0 #III.

        data['godisnji_tekuca'] = run_id.pay_date.year #IV 1.1.
        data['godisnji_prethodna'] = data['godisnji_tekuca'] - 1 #IV 1.2.
        data['ugovoreni_go'] = slip.defined_leave if slip_has_unused_leave else 0 #IV 2.1.
        data['neiskoristeni_go_tekuci'] = slip.unused_leave_current_year if slip_has_unused_leave else 0 #IV 2.2.
        data['neiskoristeni_go_prethodni'] = slip.unused_leave_previous_year if slip_has_unused_leave else 0 #IV 2.3.
        data['ukupno_godisnji'] = data['neiskoristeni_go_tekuci'] + data['neiskoristeni_go_prethodni'] if slip_has_unused_leave else 0 #IV 2.4
        data['naknada_go_tekuci'] = severance_data[0]['naknada_go_tekuci'] # 3.1
        data['naknada_go_prethodni'] = severance_data[0]['naknada_go_prethodni'] #3.2
        data['naknada_neiskoristeni_godisnji'] = (data['naknada_go_tekuci'] + data['naknada_go_prethodni']) or 0 #3
        data['osnovica_obracun_doprinosa'] = (data['naknada_neiskoristeni_godisnji'] + severance_data[0]['oporezivi_iznos']) or 0 #V
        data['mir_stup_1'] = severance_data[0]['mir_stup_1'] #5.1
        data['mir_stup_2'] = severance_data[0]['mir_stup_2'] #5.2
        data['dohodak'] = severance_data[0]['dohodak'] #VI.
        data['osobni_odbitak'] = severance_data[0]['osobni_odbitak'] #VI.1
        data['porezna_osnovica'] = severance_data[0]['porezna_osnovica'] #VI.2
        data['taxes_total'] = tax_calculation['taxes_total'] #VII.
        data['taxes'] = tax_calculation['taxes']
        data['neto_otpremnina_hrk'] = Config._convert_secondary_currency_amount(severance_data[0]['neto_otpremnina']) #VII.
        data['neto_otpremnina'] = severance_data[0]['neto_otpremnina'] #VII.
        data['osnovica_doprinosi'] = severance_data[0]['osnovica_doprinosi'] #IX.1.

        data['doprinos_zdravstveno'] = severance_data[0]['doprinos_zdravstveno'] #IX. 2.1.
        data['zbroj_doprinos_osnovica'] = data['doprinos_zdravstveno'] #IX. 2.2. # + ostali doprinosi
        data['remark'] = slip.severance_remark #XI.
        
        return data

    def check_if_rules_exist(self, slip, rules):
        slip_line_codes = [x.code for x in slip.input_line_ids] + [x.code for x in slip.worked_days_line_ids]
        return any(rule in rules for rule in slip_line_codes)

    def get_employee_address(self, slip):
        city = slip.city.name
        if not slip.street:
            return city
        return city + ', ' + slip.street

    def get_company_data(self, company):
        bank = company.partner_id.bank_ids and company.partner_id.bank_ids[0]
        return {
            'name': company.name,
            'address': self.get_company_address(company),
            'oib': company.company_registry,
            'iban': bank and bank.acc_number or '',
            'bank': bank and bank.bank_id.name or ''
        }
    
    def get_company_address(self, company):
        city = company.city_id.name
        if not company.street:
            return city
        return city + ', ' + company.street
    
    def get_severance_data(self, run_id, emp_ids):
        """
        Get data from additional income payslips for all employees in given year.
        """
        emps_cond = paycom.get_ids_sql_condition(emp_ids)
        query = """
            SELECT emp.id,
            slip.i3_config_razred_1_posto as stopa_razred_1,
            slip.i3_config_razred_2_posto as stopa_razred_2,
            ct.name as naziv_primatelja,
            ct.acc_number as iban_porez,
            MIN(cont.date_start) as employment_start,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'OTPN' AND slip.id = slip_id), 0)) as neoporezivi_iznos,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'OTPO' AND slip.id = slip_id), 0)) as oporezivi_iznos,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'OSNDOP' AND slip.id = slip_id), 0)) as osnovica_doprinosi,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'DMIO1' AND slip.id = slip_id), 0)) as mir_stup_1,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'DMIO2' AND slip.id = slip_id), 0)) as mir_stup_2,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'DOH' AND slip.id = slip_id), 0)) as dohodak,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'IOOD' AND slip.id = slip_id), 0)) as osobni_odbitak,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'POROSN' AND slip.id = slip_id), 0)) as porezna_osnovica,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'POR1' AND slip.id = slip_id), 0)) as porez_razred_1,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'POSN1' AND slip.id = slip_id), 0)) as osnovica_razred_1,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'POR2' AND slip.id = slip_id), 0)) as porez_razred_2,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'POSN2' AND slip.id = slip_id), 0)) as osnovica_razred_2,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'GON' AND slip.id = slip_id), 0)) as naknada_go_tekuci,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'GONPR' AND slip.id = slip_id), 0)) as naknada_go_prethodni,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'PDOH' AND slip.id = slip_id), 0)) as porez_dohodak,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'DZDR' AND slip.id = slip_id), 0)) as doprinos_zdravstveno,
            (SELECT CONCAT(rl.broj_modela, '-', rl.poziv_na_broj)
                            FROM hr_payslip_line ln 
                            LEFT JOIN hr_salary_rule rl 
                            ON rl.id = ln.salary_rule_id 
                            WHERE ln.code = 'PDOH' AND slip.id = slip_id)
                            as model_poziv_na_broj,
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'ISPL' AND slip.id = slip_id), 0)) as neto_otpremnina
            FROM hr_payslip_run run
            LEFT JOIN hr_payslip slip ON slip.payslip_run_id = run.id
            LEFT JOIN hr_employee emp ON slip.employee_id = emp.id
            LEFT JOIN res_city ct ON emp.city = ct.id
            LEFT JOIN hr_contract cont ON (cont.id = (
                select id from hr_contract where employee_id = emp.id order by date_start asc limit 1
            ))
            WHERE run.id = {0}
            AND emp.id IN {1}
            GROUP BY emp.id, stopa_razred_1, stopa_razred_2, model_poziv_na_broj, naziv_primatelja, iban_porez
        """.format(run_id, emps_cond)
        self.env.cr.execute(query)
        data = self.env.cr.dictfetchall()
        return data
    

    def get_tax_calculations(self, data):
        return {
            'taxes': [
                {
                    'stopa': data['stopa_razred_1'],
                    'osnovica': data['osnovica_razred_1'],
                    'iznos': data['porez_razred_1'],
                },
                {
                    'stopa': data['stopa_razred_2'],
                    'osnovica': data['osnovica_razred_2'],
                    'iznos': data['porez_razred_2'],
                },
            ],
            'taxes_total': data['porez_razred_1'] + data['porez_razred_2']
        }
    
    def format_date(self, date):
        date_obj = date
        if isinstance(date, str):
            date_obj = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date_obj and date_obj.strftime('%d.%m.%Y') or ''
