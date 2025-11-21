# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from ..models import payroll_common as paycom
from dateutil.relativedelta import relativedelta
from datetime import datetime
from odoo.tools.misc import DEFAULT_SERVER_DATE_FORMAT, format_date

class HrPayslipNO1Report(models.AbstractModel):
    _name = 'report.l10n_hr_hr_payroll.report_no1'
    _description = 'N01 report'

    @api.model
    def _get_report_values(self, slip_ids, data=None):
        Config = self.env['res.config.settings']
        obj_name = 'hr.payslip'
        company_data = self.get_company_data(self.env.user.company_id)
        slip_data = []
        slip = self.env[obj_name].browse(data['active_ids'])
        for s in slip:
            run_id = s.payslip_run_id
            severance_data = self.get_severance_data(run_id.id, [s.employee_id.id])
            s_data = self.get_payslip_data(s, self.env['res.partner.bank'], s.employee_id, run_id, severance_data, data['wizard_data'])
            if s_data:
                slip_data.append(s_data) 
                
        return {
            'doc_ids': slip_ids,
            'doc_model': obj_name,
            'docs': slip,
            'data': slip_data,
            'payroll_prec': self.env['decimal.precision'].precision_get('Payroll'),
            'secondary_currency': Config._get_secondary_currency(),
            'secondary_currency_rate_text': Config._secondary_currency_rate_text(),
            'secondary_currency_amount_column_label': Config._secondary_currency_amount_text(),
            'company_data': company_data,
            'dates': self._get_dates(data['wizard_data'])
        }
        
    def _get_joppd(self, pay_date):
        paydate_date = datetime.strptime(pay_date, DEFAULT_SERVER_DATE_FORMAT)
        joppd_date = paydate_date.strftime("%y")+paydate_date.strftime("%j")
        joppd_num = pay_date and joppd_date or ''
        return joppd_num
    
    def _get_dates(self, wizard_data):
        return {
            'pay_date': format_date(self.env, wizard_data['pay_date']),
            'print_date': format_date(self.env, wizard_data['print_date']),
            'handover_date': format_date(self.env, wizard_data['handover_date']),
        }
        
    def get_payslip_data(self, slip, bank_obj, employee, run_id, severance_data, wizard_data):
        data = {}
        data['display_severance'] = slip.input_line_ids.filtered(lambda l: l.code in ['OTPO','OTPN'])
        data['display_go'] = slip.worked_days_line_ids.filtered(lambda l: l.code in ['GON','GONPR'])
        if not (data['display_go'] or data['display_severance']):
            return {}
            
        bank_account =  employee.get_bank_accounts_on_date(run_id.pay_date)['normal']
        severance_params = slip.get_severance_params()
        data['name'] = employee.name
        data['oib'] = employee.oib
        data['city_name'] = ("%s %s") % (employee.zip, employee.city.name);
        data['city_iban'] = employee.city.acc_number
        data['address'] = self.get_employee_address(employee)
        data['bank_account'] = bank_account.acc_number
        data['bank_name'] = bank_account.bank_id.name
        data['year_start'] = slip.severance_from_year
        data['year_end'] = slip.severance_to_year
        data['work_years'] = slip.number_of_years_severance 
        data['neoporezivi_iznos'] = severance_data[0]['neoporezivi_iznos'] 
        data['oporezivi_iznos'] = severance_data[0]['oporezivi_iznos']
        data['iznos_otpremnine'] = data['neoporezivi_iznos'] + data['oporezivi_iznos'] 
        data['godisnji_tekuca'] = run_id.pay_date.year 
        data['godisnji_prethodna'] = data['godisnji_tekuca'] - 1 
        data['ugovoreni_go'] = severance_params['defined_leave'] 
        data['neiskoristeni_go_tekuci'] = severance_params['unused_leave_current_year'] 
        data['neiskoristeni_go_prethodni'] = severance_params['unused_leave_previous_year'] 
        data['ukupno_godisnji'] = data['neiskoristeni_go_tekuci'] + data['neiskoristeni_go_prethodni'] 
        data['naknada_go_tekuci'] = severance_data[0]['naknada_go_tekuci'] 
        data['naknada_go_prethodni'] = severance_data[0]['naknada_go_prethodni'] 
        data['mir_stup_1'] = severance_data[0]['mir_stup_1'] 
        data['mir_stup_2'] = severance_data[0]['mir_stup_2'] 
        data['model_poziv_na_broj'] = severance_data[0]['model_poziv_na_broj'] 
        data['dohodak'] = severance_data[0]['dohodak'] #VI.
        data['osobni_odbitak'] = severance_data[0]['osobni_odbitak'] #VI.1
        data['porezna_osnovica'] = severance_data[0]['porezna_osnovica'] #VI.2
        data['ukupno_porez'] = severance_data[0]['porez_dohodak'] #VIII.
        data['osnovica_doprinosi'] = severance_data[0]['osnovica_doprinosi'] #X.1.
        data['osnovica'] = severance_data[0]['osnovica']
        
        koef_otpo = 1
        if data['display_severance'] and data['display_go']:
            koef_otpo = float(data['oporezivi_iznos']) / float(data['osnovica']) \
                                            if float(data['osnovica']) != 0 else 0 
        if not data['display_severance']:
            koef_otpo = 0
        data['mir_stup_1_otpremnina'] = float(data["mir_stup_1"]) * koef_otpo
        data['mir_stup_2_otpremnina'] = float(data["mir_stup_2"]) * koef_otpo
        data['por_otpo'] = float(data["ukupno_porez"]) * koef_otpo
        data['mir_stup_1_go'] = float(data["mir_stup_1"]) - data["mir_stup_1_otpremnina"] if float(data['osnovica']) != 0 else 0 
        data['mir_stup_2_go'] = float(data["mir_stup_2"]) - data["mir_stup_2_otpremnina"] if float(data['osnovica']) != 0 else 0 
        data['por_go'] = float(data["ukupno_porez"]) - data["por_otpo"] if float(data['osnovica']) != 0 else 0 
        data['odgovorna_osoba'] = wizard_data['authorised_person']
    
        data['joppd'] = self._get_joppd(wizard_data['pay_date'])
        return data

    def get_employee_address(self, emp):
        city = emp.city.name
        if not emp.street:
            return city
        return city + ', ' + emp.street

    def get_company_data(self, company):
        bank = company.partner_id.bank_ids and company.partner_id.bank_ids[0]
        return {
            'name': company.name,
            'address': self.get_company_address(company),
            'oib': company.company_registry,
            'iban': bank and bank.acc_number or '',
            'bank': bank and bank.bank_id.name or '',
            'city' : company.city_id
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
            SUM(COALESCE( (SELECT total FROM hr_payslip_line WHERE code = 'BASIC' AND slip.id = slip_id), 0)) as osnovica,
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
    
    def format_date(self, date):
        date_obj = date
        if isinstance(date, str):
            date_obj = datetime.strptime(date, DEFAULT_SERVER_DATE_FORMAT)
        return date_obj and date_obj.strftime('%d.%m.%Y') or ''
