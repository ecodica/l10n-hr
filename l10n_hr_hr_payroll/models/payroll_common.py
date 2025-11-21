# -*- coding: utf-8 -*-
from odoo import _


_PAYROLL_CATEGORIES = {
    'priznati_izdatak': ('PIA30','PIU25'),
    # report_payslip, report batch
    'izaslani_porez_u_HR': ('BDI'), # ako se porez placa u HR, placa se i na bruto dodatak za izaslanje (ali ne i doprinosi)
    # ino stavke su razdvojene za potrebe izvjestaja rekapitulacije - zelimo prikazati samo NETOINO u ukupnoj isplati
    'izaslani_porez_ino_neto': ('NETOINO',), # ako se porez placa u inozemstvu, placa se svejedno isplacuje u HR
    'izaslani_porez_ino': ('PDOHINO', 'SDINO'), # porez i solidarni dodatak u inozemstvu
    # parent categories from rules to show in brutto section of report_payslip
    'bruto_dodaci_kategorije': ('DODB','DRDOH'),
    # used in worked_days and inputs selection on payslip form and realized hours report form
    # these are parents of all worked days categories, however DODB, DODN, ODN, NPIZN also have NET as parent so we use 'inputs_categories' to remove them from domain
    'worked_days_parent_categories': ('EBRT','NET'),
    # these are categories of all rules used to calculate inputs
    'inputs_categories': ('DODB','DODN','NPIZN','ODN','BDI','NETOINO','PDOHINO','SDINO','DRDOH','DODNBI'),
    # used in worked_days selection on payslip form - corresponding rules are deactivated so we remove their categories from selection
    # they are included on realized hours form so we can print past reports
    'inactive_categories': ('PRN','PRP','ONR'),
    # reports: sick leave and fees, recap, landscape and lanscape_extend
    # average_wage and average_salary wizard, joppd B, calculate_account_distribution
    'bolovanje_fond': ('BOF50','BOF70','BOF80','BOF100','ONRF50','ONRF70','ONRF80','ONRF100','ONRF','PDT','ODT','PDTK','RDT','NjDF70','NjDF100','IZO'),
    # recap, payslip, joppd B, calculate_account_distribution
    'dodaci_neto': ('PRV','USK','BOZ','REG','OTPN','ODZ','NZRD','TDT','TDI','DD','DI','NAG','DAR','PRIV','DJDOP','SS','NAGST',
                    'PN22','PN61','PREH65','PREH66','SMJ67','SMJ68','ODM','SKRB','PRAKSA','SKOL','PREMZDROSIG','RADIZDVMJ'),
    # recap
    'doprinosi_iz_place':('DMIO1','DMIO2','DMIOI1','DMIOI2','DMIOU1','DMIOU2'),
    # recap, payslip
    'doprinosi_na_placu': ('DZDR','DZNR','DZAP','DMIO1B','DMIO2B','DZDRI','DZNRI','DZAPI'),
    # recap
    'porezi':(  'POSN24','POSN36','POR12','POR24','POR36', # these codes were valid until 31.12.2020., kept here for old reports but not in use anymore
                                                            # (now we have tax groups named as 1st, 2nd etc. and not by percentage)
                'PRIR', # PRIR is no longer used since 1.12.2023. but it is kept here for the need of printing older payslip reports
                'POROSN','POSN1','POSN2','POR1','POR2','PORKAP1','PDOH','PDOHU','OPDOHHRVI'),
    'dohodak_i_odbitak':('DOH','IOOD'),
    # calculate_account_distribution
    'tax_relief':('OPDOHHRVI','PDOHU'),
    # recap
    'obustave': ('OBS','TOPOB','MSPORT'),
    # recap
    'brutto_2':('BASIC','DZDR','DZNR','DZAP','PRV','BOF50','BOF70','BOF80','BOF100','ONRF50','ONRF70','ONRF80','ONRF100',
                'BOZ','USK','REG','ONRF','ODZ','DMIO1B','DMIO2B','OTPN','NZRD','TDT','TDI','DD','DI','NjDF70','NjDF100',
                'NAG','DAR','PRIV','DJDOP','SS','NAGST','PN22','PN61','PREH65','PREH66','SMJ67','SMJ68','ODM','SKRB',
                'NETOINO','BDI','PRAKSA','SKOL','PREMZDROSIG','RADIZDVMJ'),
    'bruto_bez_sati': ('NETSTIM','STIM','OTPO','DODST','DRDOH','DODBRUTO','STRMETPR','PRILPROG','STUPOBR','STIMNN'),
    # earnings and fees reports
    # calculate_account_distribution
    # should be all brutto categories and additions
    'earnings':('RR','PRR','PRP','PRN','DRN','DRP','BO','GO','PD','NOC','BLG','ONR','IZS','BO100','ND','TERI','TERT',
                'SLP','STIM','STIMP','PROV','UTVD','NNAR','AKON','OTPO','DODST','NETSTIM','NETNNAR','DOB','SMJRAD','DRDOH',
                'DODBRUTO','STRMETPR','PRILPROG','STUPOBR','RBP','RNOC','ODSR','STIMNN','RNED'),
    # earnings and fees reports
    'fees':('PRV','BOZ','USK','REG','OTPN','NZRD','TDT','TDI','DD','DI','NAG','DAR','ODZ','PRIV','DJDOP','SS','NAGST',
            'PN22','PN61','PREH65','PREH66','SMJ67','SMJ68','ODM','SKRB','PRAKSA','SKOL','PREMZDROSIG','RADIZDVMJ'),
    # tax recap report
    'rekapitulacija_poreza':('PDOH','PRIR'), #PRIR is not used since 1.1.2024. but we keep it here for printing reports of older payslips
    # landscape and lanscape_extend reports
    'dodaci_neto_bez_putnih': ('USK','BOZ','REG','OTPN','ODZ','NZRD','TDT','TDI','DD','DI','NAG','DAR','PRIV','DJDOP',
                                'SS','NAGST','PN22','PN61','PREH65','PREH66','SMJ67','SMJ68','ODM','SKRB','PRAKSA','SKOL','PREMZDROSIG','RADIZDVMJ'),
    # fees, earnings and sick leave reports
    'sick_leave_company_without_injury_at_work': ('BO','BO100'),
    'sick_leave_fund_without_injury_at_work': ('BOF50','BOF70','BOF80','BOF100','PDT','ODT','PDTK','RDT','NjDF70','NjDF100','IZO'),
    'injury_at_work': ('ONR','ONRF','ONRF50','ONRF70','ONRF80','ONRF100'),
    # RAD-1G
    'not_paid': ('IR', 'NDOP', 'NDOPSKRB','NDOPKAND'),
    # RAD-1G, payslip confirmation
    'worked': ('RR','IZS','TERI','TERT','SLP','RBP','RNOC','RNED'),
    'overtime': ('PRR','PRP','PRN'), # removed NOC because it is not overtime (works as an addition)
    # RAD-1G, joppd B, payslip confirmation
    'not_worked_paid_by_company': ('GO','BLG','BO','BO100','ND','PD','ONR','ODSR'),
    'not_worked_not_paid_by_company': ('BOF50','BOF70','BOF80','BOF100','ONRF50','ONRF70','ONRF80','ONRF100','ONRF','PDT','ODT','PDTK','RDT','NjDF70','NjDF100','IZO'),
    # list of taxless payments we track and have exceptions for when max is exceeded
    'taxless_payments': ('NAG','PREH65','PREH66','ODM','BOZ','USK','REG','PN22','PRAKSA','SKOL','RADIZDVMJ','PREMZDROSIG'),
    'taxless_payments_monthly': ('PRAKSA','SKOL','RADIZDVMJ'),
    # calculate_account_distibution()
    # sorted by joppd receipt code (b15.1 column)
    'receipts_protected_account': ('DJDOP','BOF50','BOF70','BOF80','BOF100','NjDF70','NjDF100','ONRF','PRAKSA','DD','DI','PRV','SS','DAR','NZRD',
                                   'BOZ','USK','REG','PN22','TDT','TDI','SKOL','NAGST','PN61','NAG','NAGZK','PREH65','RADIZDVMJ'),
    # get_worked_day_lines()
    'timesheet_to_payslip_categories': ('RR','GO','BO','PRR','PRP','BLG','NOC','SMJRAD','PD','PDT','ODT','RDT',
                                        'IZO','SLP','BOF70','IR','TERI','TERT', 'NDOP','ODSR','NDOPSKRB','NDOPKAND','RNED'),
    # IP1 report config
    'contributions_base': ('OSNDOP',),
    'contributions_base_deducted': ('OSNDOPUM',),
    'income_tax_1': ('POR1',),
    'income_tax_2': ('POR2',),
    'income_tax_1_base': ('POSN1',),
    'income_tax_2_base': ('POSN2',),
    'profit_tax': ('PORKAP1',),
    'war_disability_tax_relief': ('OPDOHHRVI',),
    'supported_area_tax_relief': ('PDOHU',),
    'total_tax': ('PDOH',),
}

_TAX_PERCENTAGE_FIELDS = {
    'income_tax_1': 'i3_config_razred_1_posto',
    'income_tax_2': 'i3_config_razred_2_posto',
    'profit_tax': 'i3_config_capital_gain_1_pct',
    'war_disability_tax_relief': 'war_disability_pct',
    'supported_area_tax_relief': 50,
}

_PAYROLL_STRUCTURES = {
    # strukture za drugi dohodak
    'additional_income': ('HR6','HR7','HR14'),
    'contributions_only': ('HR3','HR4','HR13'),
    'work_abroad': ('HR15','HR16','HR17','HR18'),
    'work_abroad_ino_tax': ('HR16','HR18'),
    'profit_payment': ('HR12',),
    'without_contributions_on': ('HR2','HR17','HR18'),
}

_JOPPD_CODES = {
    # (code_type, code_name) pairs to be used for searching in get_joppd_code_ids
    'first_employment': [('P-2', '2'), ('P-2', '6')]
}

# all taxless salary rules mapped to their codes and descriptions for SEPA payment
# we need to make sure all categories from dodaci_neto and bolovanje_fond are covered
# there is no setting for protected account because it will be added in a method to keep in sync with receipts_protected_account
# sorted by JOPPD receipt code (b15.1 column in the comment)
_SEPA_INCOME_CODES_NO_ACC = {
    'DJDOP': (_(u'Doplatak za djecu'), '380', False),       # 8
    'BOF100': (_(u'Naknada za bolovanje'), '230', False),   # 12
    'BOF50': (_(u'Naknada za bolovanje'), '230', False),    # 12
    'BOF70': (_(u'Naknada za bolovanje'), '230', False),    # 12
    'BOF80': (_(u'Naknada za bolovanje'), '230', False),    # 12
    'NjDF100': (_(u'Naknada za bolovanje'), '230', False),  # 12
    'NjDF70': (_(u'Naknada za bolovanje'), '230', False),   # 12
    'ONRF': (_(u'Naknada za bolovanje'), '230', False),     # 12
    'ONRF50': (_(u'Naknada za bolovanje'), '230', False),   # 12 # no longer used, added here in case old payslip will be calculated
    'ONRF70': (_(u'Naknada za bolovanje'), '230', False),   # 12 # no longer used, added here in case old payslip will be calculated
    'ONRF80': (_(u'Naknada za bolovanje'), '230', False),   # 12 # no longer used, added here in case old payslip will be calculated
    'ONRF100': (_(u'Naknada za bolovanje'), '230', False),  # 12 # no longer used, added here in case old payslip will be calculated
    'PRAKSA': (_(u'Ostala primanja'), '690', False),        # 13
    'DD': (_(u'Službeni put'), '200', False),               # 17
    'DI': (_(u'Službeni put'), '200', False),               # 17
    'PRIV': (_(u'Naknada za korištenje privatnog automobila u službene svrhe'), '240', False), # 18
    'PRV': (_(u'Prijevoz'), '190', False),                  # 19
    'SS': (_(u'Smrtni slučaj'), '330', False),              # 20
    'DAR': (_(u'Dječji dar'), '280', False),                # 21
    'NZRD': (_(u'Dječji dar'), '280', False),               # 21
    'BOZ': (_(u'Božićnica'), '270', False),                 # 22
    'USK': (_(u'Uskrsnica'), '270', False),                 # 22
    'REG': (_(u'Regres'), '260', False),                    # 22
    'PN22': (_(u'Ostala primanja'), '690', False),          # 22
    'TDI': (_(u'Terenski dodatak'), '210', False),          # 23
    'TDT': (_(u'Terenski dodatak'), '210', False),          # 23
    'ODZ': (_(u'Naknada za odvojeni život'), '220', False), # 25
    'OTPN': (_(u'Otpremnina'), '320', False),               # 26
    'SKOL': (_(u'Ostala primanja'), '690', False),          # 28
    'NAGST': (_(u'Ostala primanja'), '690', False),         # 60
    'PN61': (_(u'Ostala primanja'), '690', False),          # 61
    'NAG': (_(u'Nagrada'), '250', False),                   # 63
    'NAGZK': (_(u'Nagrada'), '250', False),                 # 63
    'PREH65': (_(u'Topli obrok'),'191', False),             # 65
    'PREH66': (_(u'Ostala primanja'), '699', False),        # 66
    'SMJ67': (_(u'Ostala primanja'), '699', False),         # 67
    'SMJ68': (_(u'Ostala primanja'), '699', False),         # 68
    'ODM': (_(u'Ostala primanja'), '699', False),           # 69
    'SKRB': (_(u'Ostala primanja'), '699', False),          # 70
    'PREMZDROSIG': (_(u'Ostala primanja'), '699', False),   # 71
    'RADIZDVMJ': (_(u'Ostala primanja'), '699', False),     # 73
}

# used for rules which have different code depending on whether employee has protected account
# currently this means all sick leave fees: 230 is used if there is no protected account and 340 otherwise
_SEPA_PROTECTED_ACCOUNT_INCOME_CODES_MAPPING = {
    '230': '340'
}

def get_sepa_income_codes():
    """
    Update _SEPA_INCOME_CODES_NO_ACC with protected account setting using receipts_protected_account.
    Both are used for payslip distribution by accounts.
    receipts_protected_account is also used in suspension calculation.
    """
    sepa_income_codes = {}
    for key in _SEPA_INCOME_CODES_NO_ACC:
        item = list(_SEPA_INCOME_CODES_NO_ACC[key])
        if key in _PAYROLL_CATEGORIES['receipts_protected_account']:
            acc = 'protected'
        else:
            acc = 'normal'
        item[2] = acc
        sepa_income_codes.update({
            key: tuple(item)
        })
    return sepa_income_codes

def get_categories():
    return _PAYROLL_CATEGORIES

def get_tax_percentage_fields():
    return _TAX_PERCENTAGE_FIELDS

def get_structures():
    return _PAYROLL_STRUCTURES

def get_joppd_codes():
    return _JOPPD_CODES

def get_joppd_code_ids(self, key):
    """
    Return JOPPD code ids for chosen category (key).
    """
    joppd_b = self.env['hr.joppd.form.b']
    code_ids = list()
    for code_pair in _JOPPD_CODES[key]:
        code_ids.append(joppd_b.get_joppd_sifra(code_pair[0], code_pair[1]))
    return code_ids
    
def get_ids_sql_condition(id_list):
    return u'({0})'.format(','.join( [ str(x) for x in id_list ]))

def get_mio_stup(code):
    mio_stup = []
    for contribution in _PAYROLL_CATEGORIES['doprinosi_iz_place']:
        if contribution.endswith(code):
            mio_stup.append(contribution)
    return mio_stup
