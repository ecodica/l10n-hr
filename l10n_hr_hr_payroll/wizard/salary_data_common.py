# coding=utf-8
from odoo import models, fields, api, _
from ..models import payroll_common as paycom
from odoo.exceptions import ValidationError

SJEDPRIM = 'Zagreb' # Sjediste banke primatelja za doprinose
NO_MODEL = 'HR99' #kada nije definiran model i poziv na broj
SALARY_REFERENCE = 'HR6940002'
CITY_BANK_BIC_FOR_TAX = 'NBHR HR 2X'
DISABILITY_FEE_PARTNER_NAME = 'ZAVOD ZA VJEŠTAČENJE, PROFESIONALNU REHABILITACIJU I ZAPOŠLJAVANJE OSI'
CONTRIBUTIONS_PARTNER_NAME = 'Državni proračun RH'
CONTRIBUTIONS_BANK_BIC = DISABILITY_FEE_BANK_BIC = 'NBHR HR 2X'
DISABILITY_FEE_ACC_NUMBER = 'HR12 1001 0051 8630 0016 0'
DISABILITY_FEE_DESCRIPTION = u'PLACANJE NOVCANE NAKNADE ZA NEZAPOSLJAVANJE OSI-ja'


def generate_301(self, run, line_number, suma):
    debtor_data = {}
    cur = run.journal_id.currency_id.name if run.journal_id.currency_id else run.journal_id.company_id.currency_id.name
    name = run.journal_id.company_id.name
    address = run.journal_id.company_id.city_id.name
    country_code = run.journal_id.company_id.country_id.code
    street = run.journal_id.company_id.street
    zip_code = run.journal_id.company_id.zip
    oib = run.journal_id.company_id.partner_id.oib 

    debtor_data.update({
        'debtor': {
            'currency':cur,
            'name':name,
            'address':address,
            'country_code':country_code,
            'street': street,
            'zip_code': zip_code,
            'oib': oib
        }
    })
    return debtor_data

def generate_309(self, suma, payment_type, disability_fee):

    objects = []
    joppd = self.joppd_num
    first_employment_code_ids = paycom.get_joppd_code_ids(self, 'first_employment')
    additional_income_structs = paycom.get_structures()['additional_income']
    profit_payment_structs = paycom.get_structures()['profit_payment']
    run_ids = paycom.get_ids_sql_condition([run.id for run in self.payslip_run_ids])
    model_primatelja = 'HR685118-{0}-{1}'.format(self.company_id.company_registry, joppd)
    company_lang = self.env.user.company_id.partner_id.lang
    if disability_fee:
        query = """
            SELECT
            'Naziv' AS naziv,
            '{5}' AS ibanprim,
            '{4}' AS nazivprim,
            '{4}' AS nazbanprim,
            '{4}' AS primatelj,
            '{6}' AS bic,
            null AS oib,
            '{2}' AS opis,
            '' AS kod,
            'HR99' AS modelplat,
            '{0}' AS sjedprim,
            '{0}' AS sjedbnprim,
            '{3}' AS modelprim,
            sum(payment.disability_fee_amount) AS ispl
            FROM hr_payroll_disability_fee_payment AS payment
            LEFT JOIN hr_payslip_run AS run ON run.id = payment.payslip_run_id
            WHERE run.id IN {1}
            GROUP BY naziv, modelprim, opis, ibanprim, kod, nazivprim, sjedprim, bic
            ORDER BY kod
        """.format(SJEDPRIM, run_ids, DISABILITY_FEE_DESCRIPTION, model_primatelja, DISABILITY_FEE_PARTNER_NAME,
                    DISABILITY_FEE_ACC_NUMBER, DISABILITY_FEE_BANK_BIC)
        self.env.cr.execute(query)
        obj_list = self.env.cr.dictfetchall()
        return obj_list

    if payment_type == 'other' or payment_type == 'all':
        # Generiranje Doprinosa
        query = u"""
            SELECT ru.name as naziv,
                    ru.bank_account_number as ibanprim,
                    '{3}' as nazivprim,
                    '{3}' as nazbanprim,
                    '{3}' as primatelj,
                    '{4}' as bic,
                    null oib,
                    pl.name as opis,
                    pl.code kod,
                    'HR99' modelplat,
                    '{0}' sjedprim,
                    '{0}' sjedbnprim,
                    ru.broj_modela || replace(replace(replace(ru.poziv_na_broj,'OIBP',cpar.company_registry),'JOPPD','{2}'),'OIB',em.oib) as modelprim,
                    sum(pl.total) as ispl
            FROM hr_payslip AS ps
            JOIN hr_payslip_run as pr ON (ps.payslip_run_id = pr.id)
            JOIN hr_payslip_line AS pl ON (ps.id = pl.slip_id) AND pl.code IN  ('DZAP','DZDR','DZNR','DMIO1','DMIO2','DMIO1B', 'DMIO2B','DMIO1M','DMIO2M','DZAPM','DZDRM','DZNRM','DZAPI','DZDRI','DZNRI','DMIOI1','DMIOI2','DMIOU1','DMIOU2')
            JOIN hr_salary_rule as ru ON (pl.salary_rule_id = ru.id)
            JOIN hr_employee AS em ON (pl.employee_id = em.id)
            LEFT OUTER JOIN hr_department AS dep ON (dep.id = em.department_id)
            JOIN res_company AS co ON (dep.company_id = co.id)
            LEFT OUTER JOIN res_partner AS cpar ON (co.partner_id = cpar.id)
            WHERE pr.id IN {1}
            GROUP BY naziv, modelprim, opis, ibanprim, kod, nazivprim, sjedprim, bic
            ORDER BY kod
        """.format(SJEDPRIM, run_ids, joppd, CONTRIBUTIONS_PARTNER_NAME, CONTRIBUTIONS_BANK_BIC)
        self.env.cr.execute(query)
        obj_list = self.env.cr.dictfetchall()
        objects.extend(obj_list)

    if payment_type == 'salary' or payment_type == 'all':
        # Generiranje place
        query = u"""
            SELECT
            rpb.id,
            slip.id AS s_id,
            bank.name AS nazivprim,
            bank.bic AS bic,
            emp.id,
            emp.oib as oib,
            slip.struct_id,
            null sjedprim,
            null sjedbnprim,
            emp.name primatelj,
            --(case when emp.broj_modela is not null then emp.broj_modela else 'HR00' end) ||
            --(case when emp.poziv_na_broj is not null then emp.poziv_na_broj else substring(replace(rpb.acc_number, ' ', ''), 12, 10) end) modelprim,
            'HR67' || cpar.company_registry || '-' || '{0}' || '-0' modelprim,
            bank.name nazbanprim,
            ru.broj_modela || replace(replace(replace(ru.poziv_na_broj,'OIBP',cpar.oib),'JOPPD','{0}'),'PP', 
            (case when slip.mio2 = 'f' then '3' else case when slip.struct_id = 3 then '4' else '0' end end)) as modelplat,
            CASE WHEN bank_line.code IS NOT NULL THEN bank_line.code ELSE '100' END as code,
            CASE WHEN bank_line.description IS NOT NULL THEN bank_line.description ELSE pr.name END as opis,
            rpb.acc_number as ibanprim,
            ppb.id protbank,
            ppb.acc_number protiban,
            bank_protected.name protbanprim,
            bank_protected.bic protbanbic,
            struct.code as struct_code,
            slip.mio2 as mio2,
            slip.annual_calculation annual,  
            neto_line.total neto,                                                                  
            -- neto_line_dodatak.total neto_dodatak,                                                                  
            bank_line.amount as ispl,
            -- slip_line_dodatak.total ispl_dodatak,
            bank_line.acc_type as bank_type,
            slip.health_insurance_contribution_pct as dzdr_pct,
            pr.i3_add_only_inputs as only_inputs,
            params.joppd_b61 as joppd_b61
            FROM hr_payslip as slip
            LEFT JOIN hr_payslip_line as slip_line ON (slip_line.slip_id = slip.id AND slip_line.code = 'ISPL')  
            --LEFT JOIN hr_payslip_line as slip_line_dodatak ON (slip_line_dodatak.slip_id = slip.id AND slip_line_dodatak.code = 'ISPLM')                  
            LEFT JOIN hr_payslip_run as pr ON slip.payslip_run_id = pr.id
            LEFT JOIN hr_payslip_line as neto_line ON (neto_line.slip_id = slip.id AND neto_line.code in ('NETO'))
            LEFT JOIN hr_salary_rule as ru ON neto_line.salary_rule_id = ru.id
            LEFT JOIN hr_employee as emp ON (emp.id = slip.employee_id)
            LEFT JOIN hr_payslip_bank_line bank_line ON slip.id = bank_line.payslip_id
            LEFT JOIN res_partner_bank as rpb ON (rpb.id = bank_line.bank_account_id)
            LEFT JOIN res_bank as bank on (bank.id = rpb.bank_id)
            LEFT JOIN res_partner_bank as ppb ON (ppb.id = slip.protected_bank_account_id)
            LEFT JOIN res_bank as bank_protected on (bank_protected.id = ppb.bank_id)
            LEFT JOIN res_partner as rp ON (rp.id = emp.address_id)
            LEFT JOIN hr_department dep ON dep.id = emp.department_id
            LEFT JOIN hr_payroll_structure struct ON struct.id = slip.struct_id
            JOIN res_company co ON dep.company_id = co.id
            LEFT JOIN res_partner cpar ON co.partner_id = cpar.id
            LEFT JOIN hr_salary_parameters AS params ON params.id = slip.salary_parameters_id
            WHERE slip.payslip_run_id IN {1}
            AND (
                bank_line.payment_method_id IS NULL
                OR bank_line.payment_method_id IN (
                    SELECT id
                    FROM l10n_hr_joppd_sifre
                    WHERE code_type = 'P-5' AND name IN ('1','2')
                )
            )
            ORDER BY emp.name, bank_line.code
        """.format(joppd, run_ids, additional_income_structs)
        self.env.cr.execute(query)
        obj_list = self.env.cr.dictfetchall()
        length = len(obj_list)
        list_for_deduction_employee = {} 
        for y in objects:      
            if y['ispl'] < 0 and y['primatelj'] not in list_for_deduction_employee:
                list_for_deduction_employee.update({y['primatelj']:y['ispl']})  
            
        for y in objects:
            if y['primatelj'] in list_for_deduction_employee:
                y['ispl'] += list_for_deduction_employee[y['primatelj']]
                
        for placa in range(length):
            placa = obj_list[placa]

            #promjena sifre na modelu platitelja ovisno o strukturi ili isplati
            if not placa['only_inputs'] and (
                placa['struct_code'] == 'HR2'
                or not placa['dzdr_pct']
                or placa['joppd_b61'] in first_employment_code_ids
            ): # struktura bez doprinosa
                placa['modelprim'] = placa['modelprim'][:-1] +  '4'
            if placa['mio2'] == False:
                placa['modelprim'] = placa['modelprim'][:-1] +  '3'
            if placa['neto'] == 0 and not placa['only_inputs']:
                placa['modelprim'] = placa['modelprim'][:-1] +  '9'
            if placa['struct_code'] in additional_income_structs: # autorski honorar i ugovor o djelu
                placa['modelprim'] = placa['modelprim'][:-1] +  '8'
            if placa['struct_code'] in profit_payment_structs: # isplata dobiti
                placa['modelprim'] = placa['modelprim'][:-1] +  '12'

           
            if placa['protbank'] and not placa['annual']:
                if placa['bank_type'] == 'protected':
                    placa['ibanprim'] = placa['protiban']
                    placa['nazivprim'] = placa['protbanprim']
                    placa['nazbanprim'] = placa['protbanprim']                    
                    placa['bic'] = placa['protbanbic']                    

        objects.extend(obj_list)

    if payment_type == 'other' or payment_type == 'all':
        #Obustave     
        joppd = self.joppd_num
        oib = self.company_id.company_registry
        rule_obj = self.env['hr.salary.rule']
        rule = rule_obj.search([('code', '=', 'OBS')])[0]
        modelplat = (rule.broj_modela + rule.poziv_na_broj.replace('OIBP', oib).replace('JOPPD', joppd)) if rule.broj_modela else 'missing model'
        query = """
            SELECT
            em.name as emp_name,
            suspension_line.amount,
            partner_bank.acc_number as ibanprim,
            suspension.ref as ref,
            suspension.model as model,
            suspension.name as name,
            partner_bank.id as bank_id,
            partner_bank.acc_number as acc_number,
            pbank.name as bank_name,
            ps.mio2 as mio2,
            ps.struct_id as struct_id,
            pbank.bic as bic
            FROM hr_payslip AS ps
            LEFT JOIN hr_payslip_run as pr ON (ps.payslip_run_id = pr.id)
            LEFT JOIN hr_employee AS em ON (ps.employee_id = em.id)    
            LEFT JOIN hr_payslip_suspension_line suspension_line ON ps.id = suspension_line.payslip_id
            LEFT JOIN hr_salary_suspension suspension ON suspension_line.suspension_id = suspension.id 
            LEFT JOIN res_partner_bank partner_bank ON suspension_line.bank_account_id = partner_bank.id
            LEFT JOIN res_bank pbank ON partner_bank.bank_id = pbank.id
            WHERE pr.id IN {0} and suspension_line.amount > 0 and not COALESCE(suspension_line.is_company_account, False)
        """.format(run_ids)
        self.env.cr.execute(query)

        suspension_list = self.env.cr.dictfetchall()

        for el in suspension_list:                   
            if not el['model'] and not el['ref']:
                raise ValidationError(_("Potrebno je upisati model i poziv na broj na obustavu '%s' zaposlenika '%s'") % (el['name'], el['emp_name'])) 
            accept_number = (el['model'] if el['model'] else '') + (el['ref'] if el['ref'] else '')

            #raise error if bank account is not set for suspension to avoid error in file generate
            if not el['bank_id']:
                raise ValidationError(_("Potrebno je upisati bankovni račun na obustavu '%s' zaposlenika '%s'") % (el['name'], el['emp_name'])) 

            bank_number = el['acc_number'] if el['acc_number'] else "missing account"
            bank_name = el['bank_name'] if el['bank_name'] else "missing account"
            bic = el['bic']
         
            pp = '0'
            if el['mio2'] == 'f':
                pp = '3'
            elif el['struct_id'] == 3:
                pp = '4'

            objects.append({
                'modelprim': accept_number,
                'ispl': el['amount'],
                'ibanprim': el['ibanprim'],
                'nazbanprim': bank_name,
                'sjedprim': '',
                'opis': el['name'],
                'modelplat': modelplat.replace('PP', pp) if 'PP' in modelplat else 'missing normal',
                'nazivprim': bank_name,
                'primatelj':bank_name,
                'bic': bic,
                'sjedbnprim': '',
            })

        # Po opcinama
        tax_desc = get_tax_payment_description(self, self.payslip_run_ids)
        params = {
            'joppd':  joppd,
            'run_ids': tuple(self.payslip_run_ids.ids),
            'bic':CITY_BANK_BIC_FOR_TAX,
            'additional_income_structs':additional_income_structs,
            'tax_desc':tax_desc,
            'profit_payment_structs': profit_payment_structs[0],
        }
        query = u"""
            SELECT
            ROW_NUMBER() OVER (),
            city.id AS nazivprim,
            'Porez za ' || %(tax_desc)s AS opis,
            'HR99' modelplat,
            null sjedprim,
            null sjedbnprim,
            city.id AS nazbanprim,
            city.id AS primatelj,
            (CASE WHEN hps.code in %(additional_income_structs)s THEN 'HR681945-' ELSE
            (CASE WHEN hps.code = %(profit_payment_structs)s THEN 'HR681910-' ELSE 'HR681880-' END)
            END) ||  cpar.company_registry || '-' || %(joppd)s AS modelprim,
            city.acc_number ibanprim,
            %(bic)s as bic,
            sum(pl.total) as ispl
            FROM hr_payslip AS ps
            JOIN hr_payslip_run as pr ON (ps.payslip_run_id = pr.id)
            JOIN hr_payslip_line AS pl ON (ps.id = pl.slip_id) AND pl.code IN  ('PDOH','PRIR','PDOHM','PRIRM')
            JOIN hr_employee AS em ON (pl.employee_id = em.id)
            JOIN hr_payroll_structure AS hps ON (hps.id = ps.struct_id)
            LEFT OUTER JOIN hr_department AS dep ON (dep.id = em.department_id)
            JOIN res_company AS co ON (dep.company_id = co.id)
            LEFT OUTER JOIN res_partner AS cpar ON (co.partner_id = cpar.id)
            LEFT OUTER JOIN res_city AS city ON (city.id = ps.city)
            LEFT OUTER JOIN res_partner AS par ON (par.id = em.address_home_id)
            WHERE pr.id IN %(run_ids)s
            GROUP BY city.id, city.acc_number, cpar.oib, modelprim
            ORDER BY nazivprim
        """
        self.env.cr.execute(query,params)
        obj_list = self.env.cr.dictfetchall()

        city_ids = self.env['res.city'].search([])
        city_names = {city.id: city.name for city in city_ids}
        for object in obj_list:
            object_city_id =  object.get('nazivprim', None)
            object.update({'nazivprim': city_names.get(object_city_id,None)})

        objects.extend(obj_list)
        objects = [y for y in objects if y['ispl'] and y['ispl'] > 0 ]

    list_for_deduction = {}
    for y in objects:        
        if y['ispl'] and y['ispl'] < 0 and y['primatelj'] not in list_for_deduction:
            list_for_deduction.update({y['primatelj']:y['ispl']})  
            
    for y in objects:
        if y['primatelj'] in list_for_deduction:   
            y['ispl'] += list_for_deduction[y['primatelj']] if list_for_deduction[y['primatelj']] else 0

    objects = [y for y in objects if y['ispl'] and y['ispl'] > 0 ]  # brisanje linija kojima je iznos 0
    obj = generate_crref_and_endtoend(self, objects)
    return obj

def generate_crref_and_endtoend(self, sepa_lines):
    """
    Append creditor reference and EndToEndId to each line so they can be shown and edited on sepa form.
    """
    use_end_to_end = not(self.company_id.i3_config_use_end_to_end)
    res = []
    debtor_data = generate_301(self, self.payslip_run_ids[0], '', 0)
    for elem in sepa_lines:
        if 'company_registry' not in elem or ('company_registry' in elem and elem['company_registry'] is None):
            elem.update({'company_registry': False})
        elem.update({
            'modelprim': generate_creditor_reference(self, elem, debtor_data),
            'modelplat': generate_EndToEndId(self, elem, debtor_data, use_end_to_end),
        })
        res.append(elem)
    return res

def generate_creditor_reference(self, elem, debtor_data):
    if 'company_registry' in elem and elem['company_registry'] != None and elem['company_registry'] != False:
        pozivprim = SALARY_REFERENCE + '-' + debtor_data['debtor']['company_registry'] + '-' + elem['code']
    elif 'company_registry' in elem and elem['company_registry'] != None and elem['company_registry'] == False:
        pozivprim = elem['modelprim']
    else:
        pozivprim = NO_MODEL
    return pozivprim

def generate_EndToEndId(self, elem, debtor_data, use_end_to_end):
    if 'modelplat' in elem and elem['modelplat'] != None and elem['modelplat'][0:7] == 'missing': # missing model or missing normal for suspension => NO_MODEL
        elem['modelplat'] = None
    if 'company_registry' in elem and elem['company_registry'] != None and elem['company_registry'] != False:
        if elem['modelprim'] == False:
            raise ValidationError(_("The bank account of partner '%s' with description '%s' must have an associated IBAN.") % (elem['primatelj'], elem['opis'])) 
        pozivplat = elem['modelprim'] if 'modelprim' in elem and elem['modelprim'] != None and elem['modelprim'] != False and use_end_to_end else NO_MODEL
    else:
        pozivplat = elem['modelplat'] if 'modelplat' in elem and elem['modelplat'] != None and elem['modelprim'] != False else NO_MODEL
    return pozivplat

def get_tax_payment_description(self, payslip_run_ids):
    desc = ', '.join([run.name for run in payslip_run_ids])
    return desc[:140]
