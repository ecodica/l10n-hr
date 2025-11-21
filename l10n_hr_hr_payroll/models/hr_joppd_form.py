#-*- coding:utf-8 -*-

from odoo import models, fields, api, _
from datetime import date, datetime
from odoo.exceptions import ValidationError
from . import payroll_common as paycom
from dateutil.relativedelta import relativedelta
from lxml import etree
import json
import copy


_BOLOVANJE_FOND = "Molimo Vas da provjerite: 6.1. Oznaka stjecatelja/ osiguranika,\n"\
                  "6.2. Oznaka primitka/ obveze doprinosa, 8. Oznaka mjeseca osiguranja,\n"\
                  "10. Ukupni sati rada,10.0. Ukupni neodrađeni sati rada,\n"\
                  "10.1 Razdoblje obračuna do i 10.2. Razdoblje obračuna do"
_UMJETNICKI = "Molimo Vas da provjerite:\n 6.1. Oznaka stjecatelja/ osiguranika,\n"\
              "6.2. Oznaka primitka/ obveze doprinosa "
_IZASLANI_RAD =  "Molimo Vas da provjerite: 6.1. Oznaka stjecatelja/ osiguranika,\n"\
                 "6.2. Oznaka primitka/ obveze doprinosa, 8. Oznaka mjeseca osiguranja,\n"\
                 "10. Ukupni sati rada,10.0. Ukupni neodrađeni sati rada,\n"\
                 "10.1 Razdoblje obračuna do i 10.2. Razdoblje obračuna do"


class HrJoppdForm(models.Model):
    _inherit = 'hr.joppd.form'
    
    payslip_run_ids = fields.Many2many('hr.payslip.run','hr_joppd_payslip_run_rel','joppd_id','run_id','Obračuni plaće')
    
    show_nonpaid_salary_options = fields.Boolean(string='Prikaži postavke za neisplaćenu plaću', related='company_id.i3_config_show_nonpaid_salary_options')
    joppd_payslip_run_type = fields.Selection([
                                        ('salary_payment', 'Isplata plaće'),
                                        ('nonpaid_salary', 'Neisplaćena plaća'),
                                        ('subsequent_salary_payment', 'Naknadna isplata plaće')], 'Vrsta obračuna', default='salary_payment')


    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        res = super(HrJoppdForm, self).fields_view_get(view_id, view_type, toolbar, submenu)
        doc = etree.XML(res['arch'])

        if view_type == 'list':
            for node in doc.xpath("//field[@name='joppd_payslip_run_type']"):
                if self.env.user.company_id.i3_config_show_nonpaid_salary_options:
                    continue
                node.getparent().remove(node)

        res['arch'] = etree.tostring(doc, encoding='unicode')
        return res

    def get_joppd_b8(self, line, contract_list, cur):
        """
        Ako je zaposlenik unutar mjeseca bio izaslan, za svako razdoblje (ne)izaslanja je napravljen po jedan listić i ugovor.
        Za svako to razdoblje je potrebno odrediti je li počelo ili/i završilo unutar mjeseca.
        Ako nije bilo izaslanja, oznaka se određuje na temelju datuma početka prvog ugovora i eventualnog datuma prestanka radnog odnosa.
        """
        # work_abroad_obj = self.pool.get('info3.hr.work.abroad')
        slip_obj = self.env['hr.payslip']
        run = slip_obj.browse(line['slip_id']).payslip_run_id
        # work_abroad_ids = work_abroad_obj.search([('employee_id', '=', line['hr_employee_id']), '|', 
                                                # '&', ('date_from', '>=', run.date_start),('date_from', '<=', run.date_end),
                                                # '&', ('date_to', '>=', run.date_start),('date_to', '<=', run.date_end)])
        # if work_abroad_ids:
        #     first = line['contract_start'] == line['b101']
        #     last = line['contract_end'] == line['b102']
        #     if first:
        #         if last:
        #             return '4'
        #         return '1'
        #     if last:
        #         return '2'
        #     return '3'
        start_date = contract_list[0].date_start # first contract start_date
        end_date = contract_list[-1].termination_date # last contract end_date
        start = start_date if start_date else date(1970, 1, 1)
        end = end_date if end_date else date(3000, 1, 1)
        prvi = start.year == cur.year and start.month == cur.month
        zadnji = end.year == cur.year and end.month == cur.month
        if prvi:
            if zadnji:
                return '4'
            return '1'
        if zadnji:
            return '2'
        return '3'

    def get_sick_leave_fund_joppd_b8(self, line):
        slip_date_from = line['b101']
        slip_date_to = line['b102']
        sick_leave_date_from = line['sick_leave_fund_date_from']
        sick_leave_date_to = line['sick_leave_fund_date_to']
        prvi = sick_leave_date_from > slip_date_from and sick_leave_date_to <= slip_date_to
        zadnji = sick_leave_date_from >= slip_date_from and sick_leave_date_to < slip_date_to
        if prvi:
            if zadnji:
                return '4'
            return '1'
        if zadnji:
            return '2'
        return '3'

    def get_batch_data_stranaB(self):
        """
        Nakon odabira batcha puni se B strana obrasca podacima o slipovima iz batcha
        """
        JoppdSifre = self.env['l10n.hr.joppd.sifre']
        sB = self.env['hr.joppd.form.b']
        CheckLine = self.env['hr.joppd.form.check.line']
        Payslip = self.env['hr.payslip']
        Employee = self.env['hr.employee']
        Structure = self.env['hr.payroll.structure']
        City = self.env['res.city']
        Parameters = self.env['hr.salary.parameters']

        run_ids = self.payslip_run_ids.ids
        if not(run_ids): 
            raise ValidationError((u'Trenutno nema odabranih obračuna plaće pa nema podataka za preuzimanje!'))
        
        batch_ids = paycom.get_ids_sql_condition(run_ids)
        
        self.clear_joppd_B()

        provjera_lista = []       

        structures = Structure.search([])
        #untaxable_list = ('USK','BOZ','REG','TDT','TDI','DD','DI','BOF50','BOF70','BOF80','NETO','PRV','OTPN','NZRD','NjDF70','NjDF100','NAG','DAR','ONRF')
        # previously used untaxable list is copied using lists from payroll_common so we at least have some sort of auto update
        # PDT and PDTK are included because there isn't any payment anyway
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        neto_dodaci = payroll_conf.get_rules('dodaci_neto')
        bolovanje_fond = payroll_conf.get_rules('bolovanje_fond') # koristi se za izracun broja sati bolovanja na fond i izracun neoporezivog iznosa
        priznati_izdatak = payroll_conf.get_rules('priznati_izdatak') # koristi se za izracun broja sati bolovanja na fond i izracun neoporezivog iznosa
        untaxable_list = ('NETO',) + bolovanje_fond + neto_dodaci # koristi se za izracun neoporezivog iznosa
        # an instance of res.city with code '000' is created in .xml
        # we have set up an ir.rule to disable access to such res.city so we need to use sudo() here
        sifra_opcine_rada_bolovanje = City.sudo().search([('code', '=', '000')], limit=1) # koristi se za oznaku 3 za bolovanje na fond
        
        oznaka_primitka_bolovanje = JoppdSifre.search([('code_type', '=', 'P-3'),('name', '=', '0')]) # koristi se za oznaku 6.2 za bolovanje na fond
        oznaka_stjecatelja_mladi = JoppdSifre.search([('code_type', '=', 'P-2'),('name', 'in', ['10', '11'])])

        not_worked = payroll_conf.get_rules('not_worked_paid_by_company')
        additional_income_structs = paycom.get_structures().get('additional_income')
        work_abroad_struct_codes = paycom.get_structures().get('work_abroad')
        params = {
            'self_id': self.id,
            'untaxable_list': untaxable_list,
            'batch_ids': batch_ids,
            'not_worked': not_worked,
            'bolovanje_fond': bolovanje_fond,
            'work_abroad_struct_codes': work_abroad_struct_codes,
            'priznati_izdatak': priznati_izdatak,
        }
        ######################
        ### QUERY COMMENTS ###
        ######################
        # is grouping by hr_employee_state needed? it doesn't seem to do anything since b3 column is work_address
        # add work.city_id to hr.payslip and read from there?
        sql = """
            SELECT 
            %(self_id)s as joppd_id,
            slip.employee_id as hr_employee_id,
            comp.city_id as hr_employee_state,
            FALSE as user_edit,
            slip.city as b2,
            (CASE WHEN struct.code IN %(work_abroad_struct_codes)s THEN params.work_abroad_city_id ELSE work.city_id END) as b3,
            emp.first_name as first_name,
            emp.last_name as last_name,
            b61.id as b61,
            b61.name as b61_name,
            1 as b62,
            params.joppd_b9 as b9,
            contract.date_start contract_start,
            contract.date_end contract_end,
            (SELECT COALESCE(sum(wd.number_of_hours), 0)
            FROM hr_payslip_worked_days wd
            WHERE wd.code in %(bolovanje_fond)s
            and wd.payslip_id = slip.id) as bof_hours,
            (SELECT COALESCE(sum(wd.number_of_hours), 0)
            FROM hr_payslip_worked_days wd
            WHERE wd.code = 'IZO'
            and wd.payslip_id = slip.id) as iso_hours,
            slip.user_work_hours as b10,
            (SELECT COALESCE(sum(wd.number_of_hours), 0)
            FROM hr_payslip_worked_days wd
            WHERE wd.code in %(not_worked)s
            and wd.payslip_id = slip.id) as b100,
            slip.date_from as b101,
            slip.date_to as b102,
            run.pay_date as pay_date,
            slip.id as slip_id,
            slip.annual_calculation as annual_calculation,
            slip.struct_id as struct_id,
            params.joppd_b61 as params_joppd_b61,      
            COALESCE(sum(case when line.code IN ('DMIO1','DMIOI1','DMIOU1') then line.total end), 0) as b121,
            COALESCE(sum(case when line.code IN ('DMIO2','DMIOI2','DMIOU2') then line.total end), 0) as b122,
            COALESCE(sum(case when line.code IN ('DZDR','DZDRI') then line.total end), 0) as b123,
            COALESCE(sum(case when line.code IN ('DZNR','DZNRI') then line.total end), 0) as b124,
            COALESCE(sum(case when line.code IN ('DZAP','DZAPI') then line.total end), 0) as b125,
            COALESCE(sum(case when line.code IN ('UMOSNDOP') then line.total end), 0) as b129,
            COALESCE(sum(case line.code when 'DMIO1B' then line.total end), 0) as b126,
            COALESCE(sum(case line.code when 'DMIO2B' then line.total end), 0) as b127,
            COALESCE(sum(case when line.code in %(priznati_izdatak)s then line.total end), 0) as b131,
            COALESCE(sum(case when line.code in ('DMIO','DMIOUM') then line.total end), 0) as b132,
            COALESCE(
                COALESCE(sum(case line.code when 'DOH' then line.total end), 0)
                - COALESCE(sum(case when line.code in %(priznati_izdatak)s then line.total end), 0), 0) as b133,
            COALESCE(sum(case line.code when 'OOD' then line.total end), 0) as b134,
            COALESCE(sum(case line.code when 'POROSN' then line.total end), 0) as b135,
            COALESCE(sum(case when line.code in ('PDOH') then line.total end), 0) as b141,
            COALESCE(sum(case line.code when 'PRIR' then line.total end), 0) as b142,
            COALESCE(sum(case when rule.joppd_b151 is not null then line.total end), 0) as b152,
            COALESCE(sum(case when line.code in %(untaxable_list)s then line.total end), 0) as b162,
            COALESCE(sum(case when line.code in ('BASIC', 'BDI') then line.total end), 0) as b11,
            COALESCE(sum(case line.code when 'BASIC' then line.total end), 0) as b12,
            COALESCE(sum(case line.code when 'OSNDOP' then line.total end), 0) as contributions_base,
            COALESCE(sum(case when line.code in ('BASIC', 'BDI') then line.total end), 0) as b17,
            b151.name as b151,
            b161.name as b161,
            rule_b61.id as b61_id,
            slip.id,
            run.payslip_run_type as payslip_run_type,
            params.joppd_b62 as con_b62,
            params.id as params_id,
            slip.sick_leave_fund_date_from as sick_leave_fund_date_from,
            slip.sick_leave_fund_date_to as sick_leave_fund_date_to,
            slip.name as slip_name
            FROM hr_payslip_run run
            LEFT JOIN hr_payslip slip on slip.payslip_run_id = run.id
            LEFT JOIN hr_payslip_line line on line.slip_id = slip.id
            LEFT JOIN hr_employee emp on emp.id = slip.employee_id
            LEFT JOIN res_partner comp on comp.id = emp.address_id
            LEFT JOIN res_partner home on home.id = emp.partner_id
            LEFT JOIN res_partner work on work.id = emp.address_work_id
            LEFT JOIN hr_salary_parameters params on params.id = slip.salary_parameters_id
            LEFT JOIN hr_contract contract on contract.id = slip.contract_id
            LEFT JOIN hr_payroll_structure struct on struct.id = slip.struct_id
            LEFT JOIN hr_salary_rule rule on rule.id = line.salary_rule_id
            LEFT JOIN l10n_hr_joppd_sifre b151 on b151.id = rule.joppd_b151
            LEFT JOIN l10n_hr_joppd_sifre b161 on b161.id = rule.joppd_b161
            LEFT JOIN l10n_hr_joppd_sifre rule_b61 on rule_b61.id = rule.joppd_b61
            LEFT JOIN l10n_hr_joppd_sifre b61 on b61.id = struct.b61
            WHERE run.id in {0}
            GROUP BY hr_employee_id, hr_employee_state, b2, b3, b61.id, b10, b100, b101, b102, b151, b161, slip.id, contract_start, contract_end, slip.struct_id,
            b61_id, params_joppd_b61, pay_date, run.payslip_run_type, params.joppd_b62, run.id, params.id, emp.first_name, emp.last_name
            --line.code, emp.name_related
            ORDER BY emp.last_name, emp.first_name, (case when b151.name is null then 1 else 0 end) DESC, b151
        """.format(batch_ids)
        self.env.cr.execute(sql, params)
        result = self.env.cr.dictfetchall()

        result += self.get_additional_lines(result, Payslip)
        result.sort(key=lambda x: (x['last_name'], x['first_name'], x['b151'] if x['b151'] else '')) #sort again because additional lines were added 

        for line in result:
            params = Parameters.browse(line['params_id'])
            payslip = Payslip.browse(line['slip_id'])
            employee = Employee.browse(line['hr_employee_id'])
            is_bolovanje_fond = False # razdoblje obracuna NIJE mjesec isplate kao za ostale neoporezive kategorije nego mjesec obracuna
            is_bolovanje_fond_2 = False

            line['b62'] = sB.get_joppd_sifra(code_type='P-3', name=line['b62']) # get proper ID for b62, default is wrong (code is ok, ID not)
            cur = line['b102']
            izaslani_rad = False
            contract_list = employee.get_consecutive_contracts(cur)
            line['b8'] = self.get_joppd_b8(line, contract_list, cur)
            if line['b61_id']:
                b61_sifra = JoppdSifre.browse((line['b61_id']))
                b61_sifra_name = int(b61_sifra.name)
                # procitamo b61 sifru da mozemo izbjeci ulazak u postavke za strukturu za izaslani rad
                #TODO: vidjeti moze li se objediniti sa is_bolovanje_fond
                bolovanje_fond = (5201 <= b61_sifra_name <= 5211)
                is_bolovanje_fond_2 = (5201 <= b61_sifra_name <= 5211)

            # neisplacena placa -> nema isplate
            if line['payslip_run_type'] == 'nonpaid_salary':
                line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='41')
                line['b151'] = line['b161'] = '0'
                line['b152'] = line['b162'] = 0.0
            # naknadna isplata place -> nema doprinosa i poreza
            elif line['payslip_run_type'] == 'subsequent_salary_payment' and line['b11']: # ne zelimo gaziti neto dodatke, za njih je b11=None
                line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='51')
                line['b10'] = line['b100'] = line['b12'] = line['b121'] = line['b122'] = line['b123'] = line['b124'] = line['b125'] = 0
                line['b126'] = line['b127'] = line['b128'] = line['b129'] = line['b134'] = line['b135'] = line['b141'] = line['b142'] = line['b17'] = 0
                line['b151'] = '59'
            
            limit_2 = payslip.hr_config_contributions_base_deduction_limit_2
            base_for_contributions_base_deduction = payslip.line_ids.filtered(lambda x: x.code == 'OSNUMOSNDOP')
            contributions_base_deduction_line = payslip.line_ids.filtered(lambda x: x.code == 'UMOSNDOP')
            contributions_base_deduction_dob = payslip.line_ids.filtered(lambda x: x.code == 'DOB')
            line['b129'] = contributions_base_deduction_line.total if contributions_base_deduction_line else False
            if contributions_base_deduction_dob:
                line['b72'] = '0'
            elif payslip.joppd_b72:
                line['b72'] = payslip.joppd_b72
            elif base_for_contributions_base_deduction and base_for_contributions_base_deduction.total > limit_2:
                line['b72'] = '0'
            else:
                line['b72'] = '1'
                
            for structure in structures:
                # structure with work exp benefits and benefit contributions exist (to elimimate taxless line)
                if line['struct_id'] == structure['id'] and structure['code'] in ['HR5','HR10'] and (line['b127'] != None or line['b126'] != None):
                    benefit_type = params.internship_type
                    if benefit_type == 'benefit_14':
                        line['b71'] = '1'
                    elif benefit_type == 'benefit_15':
                        line['b71'] = '2'
                    elif benefit_type == 'benefit_16':
                        line['b71'] = '3'
                    elif benefit_type == 'benefit_18':
                        line['b71'] = '4'
                    else:
                        line['b71'] = '0'
                #minimalna placa
                if line['struct_id'] == structure['id'] and structure['code'] == 'HR11':
                    line['b132'] = line['b121'] + line['b122'] if line['b122'] else line['b121']
                    additional_line = self.prepare_data(untaxable_list, line['slip_id'])
                    line['b62'] = '9'
                    if additional_line[0] not in result:
                        result.append(additional_line[0])
                #isplata dobiti
                if line['struct_id'] == structure['id'] and structure['code'] == 'HR12':
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='1001')
                    line['b161'] = '1'
                    line['b12'] = 0
                    line['b17'] = 0
                    line['b133'] = line['b11']
                    line['b135'] = line['b11']
                    line['b8'] = '0'
                    line['b9'] = '0'
                    line['b101'] = date.today().strftime("%Y") + '-01-01'
                    line['b102'] = date.today().strftime("%Y") + '-12-31'
                #isplata doprinosa
                if line['struct_id'] == structure['id'] and structure['code'] == 'HR13':
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='45') #oznaka primitka je 45
                    if not payslip.line_ids.filtered(lambda l: l.code in ['NDOPSKRB']):
                        # prikaz u danima, svi dani su neodradjeni -> za IR, NDOP, ali ne i NDOPSKRB
                        line['b10'] = line['b10'] / 8
                    line['b100']  = line['b10']
                    line['b11'] = 0 #nema primitka
                    line['b132'] = 0 #nema isplate pa se doprinos ne gleda kao izdatak
                    line['b161'] = '0' #nema isplate
                    line['b17'] = 0 #primitak od nesamostalnog rada
                    line['b72'] = '0'
                #strucno osposobljavanje
                if line['struct_id'] == structure['id'] and structure['code'] in ['HR3','HR4']:
                    line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='5702')
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='5703')
                    line['b161'] = '0'
                    line['b10'] = (line['b102'] - line['b101']).days + 1
                    line['b100'] /= 8
                    line['b11'] = 0
                    line['b132'] = 0
                    line['b17'] = 0
                #autorski honorar
                if line['struct_id'] == structure['id'] and structure['code'] in ['HR6','HR7']:
                    line['b12'] = 0
                #drugi dohodak
                if line['struct_id'] == structure['id'] and structure['code'] in additional_income_structs:
                    line['b62'] = line['con_b62']
                    line['b72'] = '0'
                    if not sifra_opcine_rada_bolovanje:
                        raise ValidationError(u'There is no city with code 000 for additional income b3 code.')
                    line['b3'] = sifra_opcine_rada_bolovanje.id
                #izaslani rad - porez u Hrvatskoj
                if line['struct_id'] == structure['id'] and structure['code'] in ['HR15','HR17'] and not is_bolovanje_fond_2:
                    sifra_naziv = '10' if structure['code'] in ['HR17'] else '5'
                    line['b61'] = sB.get_joppd_sifra(code_type='P-2', name=sifra_naziv)
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='1')
                    line['b72'] = '0'
                    izaslani_rad = True
                #izaslani rad - porez u inozemstvu
                if line['struct_id'] == structure['id'] and structure['code'] in ['HR16','HR18'] and not is_bolovanje_fond_2:
                    sifra_naziv = '10' if structure['code'] in ['HR18'] else '5'
                    line['b61'] = sB.get_joppd_sifra(code_type='P-2', name=sifra_naziv)
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='61')
                    # svi iznosi su 0 osim doprinosa
                    line['b11'] = line['b132'] = line['b133'] = line['b134'] = line['b135'] = line['b141'] = line['b142'] = line['b152'] = line['b162'] = line['b17'] = 0
                    line['b151'] = line['b161'] = '0'
                    line['b72'] = '0' 
                    izaslani_rad = True
            porodiljni = False
            izolacija = False
            if payslip.line_ids.filtered(lambda line: line.code in ['NETNNAR', 'NNAR']):
                line['b161'] = sB.get_joppd_sifra(code_type='P-5', name='5')
                # mladim osobama se placa u naravi tretira kao placa - stoga su 6.1, 6.2, 10.1, 10.2 kao za placu
                if line['params_joppd_b61'] in oznaka_stjecatelja_mladi.ids:
                    line['b61'] = line['params_joppd_b61']
                else:
                    line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='1')
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='21')
                    line['b101'] = date.today().replace(month=1, day=1)
                    line['b102'] = date.today().replace(month=12, day=31)
                    
                line['b151'] = sB.get_joppd_sifra(code_type='P-4', name='0')
                line['b17'] = 0
                line['b134'] = min(line['b134'], line['b133'])
                line['b72'] = '0'
                
            else:
                if line['annual_calculation'] == True:
                    # za godisnji obracun 13.4 i 13.5 moraju biti suprotnog iznosa, inace se javlja greska kod uploada na poreznu
                    line['b134'] = -1 * line['b135']
                    if line['b141'] == None:
                        line['b141'] = 0
                    if line['b142'] == None:
                        line['b142'] = 0
                    line['b162'] = -1 * (line['b141'] + line['b142'])
                    line['b62'] = '406'
                    line['b62'] = sB.get_joppd_sifra(code_type='P-3', name=line['b62'])
                provjera_lista = []
                provjera = {}
                line['b151'] = line['b151'] or '0'
                b151 = line['b151']
            
                line['b161'] = line['b161'] or '1'
                if line['b61_id']:
                    line['b61'] = line['b61_id'] 
                elif not line['b61']:
                    # b61 nije postavljeno na pravilu (najcesce kod neoporezivih primitaka = '0'),
                    # nije placa u naravi, nije izaslani rad, strucno osposobljavanje
                    line['b61'] = line['params_joppd_b61'] or Parameters._default_joppd_b61()

            
                if not line['annual_calculation']:
                    line['b134'] = min(line['b134'], line['b133'])
                line['b151'] = sB.get_joppd_sifra(code_type='P-4', name=line['b151'])
                line['b161'] = sB.get_joppd_sifra(code_type='P-5', name=line['b161'])
           
                for sifra in JoppdSifre.browse([int(line['b61'])]):
                    sifra_name = int(sifra.name)
                    #bolovanje
                    if 5201<=sifra_name<=5211:
                        # izolacija se od bolovanja na fond razlikuje po oznaci 15.1 jer nema primitka
                        # od porodiljnog se razlikuje po oznaci 6.1
                        # sati IZO su ukljuceni u bof_hours pa ih ovdje oduzimamo za slucaj da na istom listicu postoji jos koja naknada na teret fonda
                        if not sifra_opcine_rada_bolovanje:
                            raise ValidationError(u'There is no city with code 000 for sick leave paid by health insurance fund.')
                        if not line['sick_leave_fund_date_from'] or not line['sick_leave_fund_date_to']:
                            msg = _(u'Potrebno je unijeti razdoblje bolovanja na fond na listiću:\n\n{0}').format(line['slip_name'])
                            raise ValidationError(msg)
                        line['b3'] = sifra_opcine_rada_bolovanje.id
                        line['b62'] = oznaka_primitka_bolovanje.id
                        line['b9'] = '0'
                        line['b100'] = line['b10'] = line['bof_hours'] - line['iso_hours']
                        line['b72'] = '0'
                        line['b129'] = 0
                        if sifra_name in [5203,5204,5207]:
                            porodiljni = True
                            line['b10'] = '0'                    
                            line['b100'] = '0'
                            line['b72'] = '0'
                        if sifra_name == 5201 and b151 == '0' and line['iso_hours']:
                            izolacija = True
                            line['b10'] = line['b100'] = line['iso_hours']
                        else:
                            line['b100'] = line['b10'] = line['bof_hours']
                        line['b8'] = self.get_sick_leave_fund_joppd_b8(line) # has to be before b101 and b102 assignment
                        line['b101'] = line['sick_leave_fund_date_from']
                        line['b102'] = line['sick_leave_fund_date_to']
                        provjera_lista.append(_BOLOVANJE_FOND)
                        is_bolovanje_fond = True
                    #honorari, umjetnički, autorski
                    if 4001<=sifra_name<=4002:
                        dummy1, method, dummy2 = payslip._additional_income_bank_account()
                        line['b8'] = '0'
                        line['b9'] = '0'
                        line['b10'] = '0'                    
                        line['b100'] = '0'
                        line['b101'] = date.today().strftime("%Y") + '-01-01'
                        line['b102'] = date.today().strftime("%Y") + '-12-31'
                        line['b17'] = 0
                        line['b161'] = method.id
                        provjera_lista.append(_UMJETNICKI)
                    #neoporezivi primici
                    if sifra_name==0:
                        line['b8'] = '0'
                        line['b62'] = '0'
                        line['b9'] = '0'
                        line['b10'] = '0'
                        line['b100'] = '0'
                        line['b72'] = '0'
                        line['b129'] = 0
                        line['b62'] = sB.get_joppd_sifra(code_type='P-3', name=line['b62'])
                    #izaslani rad
                    if sifra_name==5:
                        provjera_lista.append(_IZASLANI_RAD)

                # mora biti nakon provjere sifri za bolovanje
                if b151 != '0' and not is_bolovanje_fond: # datum za neoporezive dodatke mora biti mjesec isplate
                    if line['pay_date'] > line['b102']:
                        # razdoblje uvijek mora biti cijeli mjesec
                        date_from = (line['b101'] + relativedelta(months=1)).replace(day=1)
                        date_to = (date_from + relativedelta(months=1)) - relativedelta(days=1)
                        line['b101'] = date_from
                        line['b102'] = date_to

            # neiskorišteni godišnji i otpremnina
            godisnji = False
            godisnji_prethodna = False
            otpremnina = False
            nadoknada_neto = False
            if payslip.line_ids.filtered(lambda line: line.code in ['GON', 'OTPO', 'GONPR','STIMNN']):
                payslip_line = payslip.line_ids.filtered(lambda line: line.code in ['GON','GONPR','OTPO','STIMNN'])

                for slip_line in payslip_line:
                    if slip_line.code == 'GON' and slip_line.amount == line['b11']:
                        godisnji = True
                        line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='1')
                        line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='21')
                        line['b8'] = '0'
                        line['b9'] = '0'
                        line['b10'] = '0'
                        line['b151'] = sB.get_joppd_sifra(code_type='P-4', name='0')
                        line['b161'] = sB.get_joppd_sifra(code_type='P-5', name='1')
                        first_of_curr_year = (line['b101'] + relativedelta()).strftime("%Y") + '-01-01'
                        last_of_curr_year = (line['b101'] + relativedelta()).strftime("%Y") + '-12-31'
                        line['b101'] = first_of_curr_year
                        line['b102'] = last_of_curr_year
                        line['b17'] = 0
                    elif slip_line.code == 'GONPR' and slip_line.amount == line['b11']:
                        godisnji_prethodna = True
                        line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='1')
                        line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='21')
                        line['b8'] = '0'
                        line['b9'] = '0'
                        line['b10'] = '0'
                        line['b151'] = sB.get_joppd_sifra(code_type='P-4', name='0')
                        line['b161'] = sB.get_joppd_sifra(code_type='P-5', name='1')
                        first_of_prev_year = (line['b101'] + relativedelta(years=-1)).strftime("%Y") + '-01-01'
                        last_of_prev_year = (line['b101'] + relativedelta(years=-1)).strftime("%Y") + '-12-31'
                        line['b101'] = first_of_prev_year
                        line['b102'] = last_of_prev_year
                        line['b17'] = 0
                    elif slip_line.code == 'OTPO' and slip_line.amount == line['b11']:
                        otpremnina = True
                        line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='1')
                        line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='25')
                        line['b8'] = '0'
                        line['b9'] = '0'
                        line['b10'] = '0'
                        line['b151'] = sB.get_joppd_sifra(code_type='P-4', name='0')
                        line['b161'] = sB.get_joppd_sifra(code_type='P-5', name='1')
                        first_of_curr_year = (line['b101'] + relativedelta()).strftime("%Y") + '-01-01'
                        last_of_curr_year = (line['b101'] + relativedelta()).strftime("%Y") + '-12-31'
                        line['b101'] = first_of_curr_year
                        line['b102'] = last_of_curr_year
                        line['b17'] = 0
                    elif slip_line.code == 'STIMNN' and slip_line.amount == line['b11']:
                        nadoknada_neto = True
                        line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='21')
                        line['b10'] = '0'
                        first_day_year = line['b101'].replace(day=1,month=1)
                        last_day_year= (first_day_year + relativedelta(years=1)) - relativedelta(days=1)
                        line['b101'] = first_day_year
                        line['b102'] = last_day_year

                #id = PayslipLine.search(cr,uid,[('slip_id', '=', line['slip_id']), ('code', 'in', ['OTPN'])])
                #payslip_line = PayslipLine.browse(cr, uid, id, context)
                #for slip_line in payslip_line:
                #    if slip_line.code == 'OTPN' and slip_line.amount == line['b162']:
                        #line['b61'] = sB.get_joppd_sifra(code_type='P-2', name='0')[0]
                        #line['b62'] = sB.get_joppd_sifra(code_type='P-3', name='0')[0]
                        #line['b8'] = '0'
                        #line['b9'] = '0'
                        #line['b10'] = '0'

            if not is_bolovanje_fond and line['bof_hours'] and int(line['b10']) > 0:
                # korekcija ukupnog broja sati - samo ako postoji bolovanje na fond i odrađeni sati (ako nije neoporeziva stavka)
                line['b10'] -= line['bof_hours']

            if line['contributions_base'] > line['b12']:
                # bilo bi najpravilnije direktno citati osnovicu za doprinose s pravila OSNDOP umjesto BASIC
                # ali na starijim listicima tog pravila nema pa je dodan uvjet da se cita samo kad je OSNDOP > BASIC
                line['b12'] = line['contributions_base']

            #if income > 0 -> set dates to first and last day of month
            if line['b17'] > 0 and not izaslani_rad and not nadoknada_neto:
                first_day_month = line['b101'].replace(day=1)
                last_day_month = (first_day_month + relativedelta(months=1)) - relativedelta(days=1)
                line['b101'] = first_day_month
                line['b102'] = last_day_month

            # delete fields we no longer need to create Joppd B (otherwise we get warnings in log)
            unnecessary_fields_list = [
                'b61_id','struct_id','b61_name','id','contract_end','contract_start','slip_id','params_joppd_b61','pay_date',
                'payslip_run_type','annual_calculation','bof_hours','con_b62','contributions_base','iso_hours','params_id',
                'slip_name', 'sick_leave_fund_date_to', 'sick_leave_fund_date_from', 'first_name', 'last_name'
            ]
            for key in unnecessary_fields_list:
                del line[key]

            if (line['b11'] or line['b12'] or line['b121'] or line['b122'] or line['b123'] or line['b124'] or line['b125'] 
                or line['b126'] or line['b127'] or line['b132'] or line['b133'] or line['b134'] or line['b135'] or line['b141']
                or line['b142'] or line['b152'] or line['b162'] or line['b17'] or porodiljni or izolacija or godisnji or godisnji_prethodna or otpremnina or nadoknada_neto):
                sb_id = sB.create(line)

            if len(provjera_lista) > 0:
                # remove previous check lines and create new ones
                for seq in sb_id:
                    sequence = seq.b1
                provjera.update({
                    'joppd_id': self.id,
                    'employee_id': line['hr_employee_id'],
                    'sequence':sequence,
                    'description':provjera_lista[0]
                })
                CheckLine.create(provjera)
        
        self.calc_stranaA()
        return True

    def get_additional_lines(self, result, Payslip):
        """
            Creates new lines for joppd for salary rules GON, GONPR and OTPO.
            Deducts amount of newly created lines from the original line.
        """
        additional_lines = []
        processed_payslips = []

        for joppd_line in result:
            payslip = Payslip.browse(joppd_line['slip_id'])
            if payslip in processed_payslips:
                continue
            processed_payslips.append(payslip)

            filtered_lines = payslip.line_ids.filtered(lambda line: line.code in ['GON','GONPR','OTPO','STIMNN'])
            if not filtered_lines:
                continue

            non_work_hours = sum(line.number_of_hours for line in payslip.worked_days_line_ids if line.code in ['GON', 'GONPR', 'STIMNN'])

            """
                'result' contains employees joppd lines. We want to split brutto line if some of the 'filtered_lines' exist in 'result'.
                Brutto line is identified by 'b11' > 0
            """
            line_to_copy = list(filter(lambda x: x['b11'] > 0 and x['slip_id'] == joppd_line['slip_id'], result))[0]
            total = line_to_copy['b11']

            joppd_columns = ['b121','b122','b123','b124','b125','b126','b127','b129','b131','b132','b133','b134','b135','b141','b142','b152','b162','b11','b12','b17','contributions_base']
            dict_total_lines = {}
            for key in joppd_columns:
                dict_total_lines[key] = 0

            for line_to_duplicate in filtered_lines:
                percentage = line_to_duplicate.total / total
                additional_line = copy.deepcopy(line_to_copy)

                dict_current_line = {}
                for key in joppd_columns:
                    dict_current_line[key] = additional_line[key]*percentage
                    dict_total_lines[key] += dict_current_line[key]
                    additional_line.update({ 
                        key: round(dict_current_line[key], 2),
                    })
                additional_lines.append(additional_line)

            for key in joppd_columns:
                line_to_copy.update({
                        key: round(line_to_copy[key] - dict_total_lines[key], 2),
                })

            #GON and GONPR don't have work hours on JOPPD
            line_to_copy.update({
                'b10': line_to_copy['b10'] - non_work_hours
            })
        return additional_lines

    def prepare_data(self, untaxable_list, slip_id):
        sql = """
        SELECT  
        {0} as joppd_id,            
        slip.employee_id as hr_employee_id,            
        comp.city_id as hr_employee_state,            
        FALSE as user_edit,home.city_id as b2,            
        comp.city_id as b3,            
        b61.id as b61,            
        b61.name as b61_name,            
        1 as b62,            
        contract.date_start contract_start,            
        contract.date_end contract_end,                 
        0 as b10,
        0 as b100,     
        slip.date_from as b101,            
        slip.date_to as b102,            
        slip.id as slip_id,            
        slip.annual_calculation as annual_calculation,            
        Null as struct_id,      
         --line.code, 
        emp.name_related,                       
        sum(case when line.code IN ('DMIO1M','DMIOI1M
        ') then line.total end) as b121,            
        sum(case when line.code IN ('DMIO2M','DMIOI2M') then line.total end) as b122,            
        sum(case when line.code IN ('DZDRM','DZDRMI') then line.total end) as b123,            
        sum(case when line.code IN ('DZNRM','DZNRMI') then line.total end) as b124,            
        sum(case when line.code IN ('DZAPM','DZAPMI') then line.total end) as b125,            
        sum(case line.code when 'DMIO1B' then line.total end) as b126,            
        sum(case line.code when 'DMIO2B' then line.total end) as b127,            
        sum(case when line.code IN ('DMIO1M','DMIO2M') then line.total end) as b132,               
        sum(case line.code when 'DOHM' then line.total end) as b133,            
        sum(case line.code when 'IOODM' then line.total end) as b134,            
        sum(case line.code when 'POROSN' then line.total end) as b135,            
        sum(case line.code when 'PDOHM' then line.total end) as b141,            
        sum(case line.code when 'PRIRM' then line.total end) as b142,            
        sum(case when rule.joppd_b151 is not null then line.total end) as b152,            
        sum(case when line.code = 'NETOM' then line.total end) as b162,            
        sum(case line.code when 'BASICM' then line.total end) as b11,            
        sum(case line.code when 'BASICM' then line.total end) as b12,            
        sum(case line.code when 'BASICM' then line.total end) as b17,            
        Null as b151,
        Null as b161,
        Null as b61_id,            
        --sum(line.amount) as amount            
        slip.id 
        FROM hr_payslip_run run            
        LEFT JOIN hr_payslip slip on slip.payslip_run_id = run.id            
        LEFT JOIN hr_payslip_line line on line.slip_id = slip.id            
        LEFT JOIN hr_employee emp on emp.id = slip.employee_id            
        LEFT JOIN res_partner comp on comp.id = emp.address_id            
        LEFT JOIN res_partner home on home.id = emp.address_home_id           
        LEFT JOIN res_partner work on work.id = emp.address_work_id            
        LEFT JOIN hr_contract contract on contract.id = slip.contract_id            
        LEFT JOIN hr_payroll_structure struct on struct.id = contract.struct_id            
        LEFT JOIN hr_salary_rule rule on rule.id = line.salary_rule_id            
        --LEFT JOIN l10n_hr_joppd_sifre b151 on b151.id = rule.joppd_b151            
        LEFT JOIN l10n_hr_joppd_sifre b161 on b161.id = rule.joppd_b161            
        LEFT JOIN l10n_hr_joppd_sifre rule_b61 on rule_b61.id = rule.joppd_b61            
        LEFT JOIN l10n_hr_joppd_sifre b61 on b61.id = struct.b61 WHERE slip.id = {2}            
        GROUP BY hr_employee_id, hr_employee_state, b2, b3, b61.id, b10, b100, b101, b102, b161, slip.id, contract_start, contract_end,b61_id,
        struct.id,            
        --line.code, 
        emp.name_related 
        ORDER BY slip.id DESC

        """.format(self.id,untaxable_list,slip_id)
        
        self.env.cr.execute(sql)
        
        result = self.env.cr.dictfetchall()
        
        return result
