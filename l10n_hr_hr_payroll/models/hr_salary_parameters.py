#-*- coding:utf-8 -*-

from odoo import models, fields, api, _
from dateutil import relativedelta
from datetime import date, datetime, timedelta
from lxml.html import fromstring
from odoo.exceptions import ValidationError


_calculation_type_sel = [
    ('employee_work_hours', _('Temeljem mjesečnog fonda sati po radnom vremenu zaposlenika')),
    ('hourly_wage', _('Temeljem satnice')),
    ('fixed_salary', _('Fiksna plaća')),
    ('month_work_hours', _('Temeljem mjesečnog fonda sati za puno radno vrijeme')),
]

_CALCULATION_TYPE_HELP = _(
    "Svi primjeri su na bazi mjeseca od 21 radnog dana i zaposlenjem na nepuno radno vrijeme od 4 sata / dan uz plaću 1.000:\n"\
    "1. Temeljem mjesečnog fonda sati zaposlenika: odrađeno sati = 21 * 4 =  84, mjesečni fond zaposlenika = 21 * 4 = 84, plaća = 84 / 84 * 1.000 = 1.000\n"\
    "2. Temeljem satnice: odrađeno sati = 21 * 4 = 84, satnica = 20, plaća = 84 * 20 = 1.680\n"\
    "3. Fiksna plaća: plaća = 1.000 čim je odrađeno > 0 sati (ako su svi sati redovni, tj. nema bolovanja ili prekovremenih itd.)\n"\
    "4. Temeljem mjesečnog fonda sati za puno radno vrijeme: odrađeno sati = 21 * 4 = 84, mjesečni fond = 21 * 8 = 168, plaća = 84 / 168 * 1.000 = 500\n"
)

class HrSalaryParameters(models.Model):
    """
    This class is used to define parameters for employee salary calculation.
    Read access is given to system users and payroll officers so they can open contract form and view salary parameters, but not edit them.
    Payroll manager has all access rights.
    """
    _name = 'hr.salary.parameters'
    _description = 'Skup parametara za izračun plaće'
    _order = 'date_from desc'
    _inherit= 'mail.thread'

    @api.model
    def _update_deduction_ids(self):
        # dohvati sve moguće odbitke po novom
        new_deduction_ids = self._get_deduction_ids()
        # svi odbitci trenutno na parametrima (iz šifrarnika Osobni odbitci)
        current_deduction_ids = self.tax_deduction_ids.mapped("tax_deduction_id").mapped("id")
        result = []
        # iteriram po novim odbitcima
        for tax_deduction in new_deduction_ids:
            # record iz novog šifrarnika
            tax_deduction_data = tax_deduction[2]
            
            # ako record iz novog šifrarnika nemam na trenutnim parametrima
            if not tax_deduction_data['tax_deduction_id'] in current_deduction_ids:
                # dodajemo novu stavku osobbnog odbitka
                result.append((0, 0, tax_deduction_data)) 
            # ako record iz novog šifrarnika imam na trenutnim parametrima
            else:
                current_contract_tax_deduction = self.tax_deduction_ids.filtered(
                    lambda d: d.tax_deduction_id.id == tax_deduction_data['tax_deduction_id'])
                tax_deduction_data['qty'] = current_contract_tax_deduction.qty
                tax_deduction_data['deduction_shared_with'] = current_contract_tax_deduction.deduction_shared_with
                tax_deduction_data['status'] = current_contract_tax_deduction.status
                # ažuriramo koeficijent
                result.append((1, current_contract_tax_deduction.id, tax_deduction_data))
        self.write({'tax_deduction_ids':result})
    
    @api.model
    def _get_deduction_ids(self):
        deductions_obj = self.env['tax.deduction']
        deduction_ids = deductions_obj.search([])

        deduction_ref = self.env['ir.model.data']._xmlid_lookup('l10n_hr_hr_payroll.21') #import iz tax.deduction.csv! ovo dohvaća osobni odbitak koji bi trebao biti pod ID 21
        #developer : PAZI koji je tax.decuction.csv importan! 
        #       v1 je bila sa numeričkim id, (21,22,23... 
        #       v2 sa ospisnim id (
        basic_id = deduction_ref and deduction_ref[1] or False
        r=[]
        for deduction_id in deduction_ids:
            if deduction_id.id == basic_id:
                r.append({
                    'tax_deduction_id':deduction_id.id,
                    'status':True,
                    'qty':1,
                    'deduction_shared_with': '',
                })
            elif deduction_id.status:
                r.append({
                    'tax_deduction_id':deduction_id.id,
                    'status':False,
                    'qty':1,
                    'deduction_shared_with': '',
                })
        return [(0, 0, line) for line in r]

    @api.model
    def _get_default_contract(self):
        """
        Get contract_id from context when creating throught contract form view.
        """
        return self.env.context.get('contract_id', False)
            
    
    @api.model
    def _get_default_department(self):
        """
        Get contract_id from context when creating throught contract form view.
        """
        return self.env.context.get('department_id', False)
    
    @api.model
    def _get_default_job(self):
        """
        Get contract_id from context when creating throught contract form view.
        """
        return self.env.context.get('job_id', False)
    
    @api.model
    def _get_default_job_description(self):
        """
        Get contract_id from context when creating throught contract form view.
        """
        return self.env.context.get('job_description', False)
    
    def _default_calculate_salary_by_coefficient(self):
        params_obj = self.env['ir.config_parameter']
        return bool(params_obj.sudo().get_param('l10n_hr_hr_payroll.i3_config_calculate_salary_by_coefficient'))

    def _default_base_salary(self):
        params_obj = self.env['ir.config_parameter']
        return float(params_obj.sudo().get_param('l10n_hr_hr_payroll.i3_config_base_salary'))
        
    def _joppd_b9_sel(self):
        return self.env['hr.joppd.form.b']._b9_sel()
    
    def _joppd_b72_sel(self):
        return self.env['hr.joppd.form.b']._b72_sel()
    
    def _default_joppd_b61(self):
        return self.env['hr.joppd.form.b'].get_joppd_sifra(code_type='P-2', name='1')
    
    ##############
    ### HEADER ###
    ##############
    contract_id = fields.Many2one('hr.contract', 'Ugovor', required=True, ondelete='restrict', default=_get_default_contract)
    name = fields.Char('Naziv', size=64, required=True, tracking=True)
    note = fields.Text('Bilješka', copy=False, tracking=True)
    date_from = fields.Date('Datum od', required=True, copy=False, tracking=True)
    date_to = fields.Date('Datum do', copy=False, tracking=True)
    # added store=True to enable grouping
    employee_id = fields.Many2one(related='contract_id.employee_id', string='Zaposlenik', store=True)
    company_id = fields.Many2one('res.company', default=lambda self: self.env.user.company_id,string='Tvrtka')
    currency_id = fields.Many2one(string="Valuta", related='company_id.currency_id', readonly=True, tracking=True)

    department_id = fields.Many2one('hr.department', string="Odjel", required=True, default=_get_default_department, tracking=True)
    job_id = fields.Many2one('hr.job', string='Radno mjesto', required=True, default=_get_default_job, tracking=True)
    job_description = fields.Html(string="Opis posla", default=_get_default_job_description)
    # active = fields.Boolean(default=True)

    struct_id = fields.Many2one('hr.payroll.structure', string='Struktura plaće', required=True, 
                                    default=lambda self: self.env['hr.payroll.structure'].search([('code', '=', 'HR1')]))
    # used to distinguish structures with benefits and abroad work
    struct_code = fields.Char(related='struct_id.code', tracking=True)
    ##################
    ### PARAMETERS ###
    ##################

    salary_calculation_type = fields.Selection(_calculation_type_sel, 'Način izračuna', default='employee_work_hours', help=_CALCULATION_TYPE_HELP)
    wage = fields.Monetary('Bruto plaća', required=True, tracking=True, help="Mjesečna bruto plaća zaposlenika.")
    wage_hour = fields.Monetary('Bruto satnica', help="Fiksna bruto satnica za djelatnika.", tracking=True)
    use_wage_hour = fields.Boolean('Koristi bruto satnicu', help="Kada je odabrano, satnica će se koristiti kod obračuna plaća i drugih funkcionalnosti.", tracking=True)

    # salary calculation by coefficent
    calculate_salary_by_coefficient = fields.Boolean('Izračun plaće na temelju koeficijenta', default=_default_calculate_salary_by_coefficient, tracking=True)
    base_salary = fields.Float('Osnovica plaće', default=_default_base_salary, tracking=True)
    salary_coef = fields.Float('Koeficijent plaće', default=1.00, digits=(6,4), tracking=True)

    # public sector
    degree_bonus = fields.Selection([
            ('none', 'Bez dodataka'),
            ('masters', 'Magisterij'),
            ('phd', 'Doktorat'),
        ],'Dodatak za stupanj obrazovanja', default='none', tracking=True)
        
    # countributions base
    max_con_base_setting = fields.Float('Postavka za maksimalni iznos osnovice', related='company_id.i3_config_max_contributions_base')
    min_con_base_setting = fields.Float('Postavka za minimalnu osnovicu za doprinose', related='company_id.i3_config_min_contributions_base')
    min_con_base_setting_directors = fields.Float('Postavka za minimalnu osnovicu za doprinose za članove uprave', related='company_id.i3_config_min_contributions_base_directors')
    is_director = fields.Boolean('Član uprave', help='Ova opcija govori koji je iznos minimalne osnovice za doprinose.')
    min_contributions_base = fields.Float('Minimalna mjesečna osnovica za doprinose', compute='_calculate_min_contributions_base')
    max_contributions_base = fields.Float('Maksimalna mjesečna osnovica za doprinose', compute='_calculate_max_contributions_base')
    
    # contributions
    health_insurance_contribution_pct = fields.Float('Doprinos za zdravstveno osiguranje (%)',
                            default=lambda self: self.env.user.company_id.i3_config_health_insurance_contribution_pct)
    health_insurance_contribution_pct_additional_income = fields.Float('Doprinos za zdravstveno osiguranje - drugi dohodak (%)',
                            default=lambda self: self.env.user.company_id.i3_config_health_insurance_contribution_pct_additional_income)
    mio2 = fields.Boolean('MIO II stup')
    
    internship_type = fields.Selection([
        ('0', '0 - None'),
        ('1', '1 - 12/14'),
        ('2', '2 - 12/15'),
        ('3', '3 - 12/16'),
        ('4', '4 - 12/18'),
    ], string='Staž s povećanim trajanjem', required=True, default='0')
    benefit_id = fields.Many2one('info3.work.exp.benefit', 'Razina beneficiranog staža')
    dmio1b_percentage = fields.Float(related='benefit_id.dmio1b', string='Dodatni doprinos za 1. stup (%)')
    dmio2b_percentage = fields.Float(related='benefit_id.dmio2b', string='Dodatni doprinos za 2. stup (%)')

    # average wages for sick leave calculation
    average_salary_net = fields.Float('Prosječna neto satnica', digits=('Payroll Hourly Wage'))
    average_salary_gross = fields.Float('Prosječna bruto satnica', digits=('Payroll Hourly Wage'))
    average_salary_date_from = fields.Date('Ažurirano od', required=False)
    average_salary_date_to = fields.Date('Ažurirano do', required=False)

    # dodaci i olaksice
    experience_coef = fields.Float('Koeficijent za dodatak na staž (%)', digits=('Payroll'))
    supported_area = fields.Boolean('Potpomognuto područje', help='Ova opcija uključuje 50%% porezne olakšice kod izračuna plaće. Primjenjuje se nakon porezne olakšice za ratne invalide.')
    has_war_disability = fields.Boolean('Hrvatski ratni vojni invalid', help='Ova opcija uključuje olakšicu na porez na dohodak za HRVI kod obračuna plaće.')
    war_disability_pct = fields.Float('Postotak invalidnosti (%)', help='Postotak poreza na dohodak koji će se odbiti kod obračuna plaće. Primjenjuje se prije olakšice za potpomognuto područje.')
    
    # izaslani rad
    joppd_b62 = fields.Many2one('l10n.hr.joppd.sifre', 'Joppd oznaka primitka (6.2.)', domain=[('code_type','=','P-3')])
    work_abroad_city_id = fields.Many2one('res.city', 'Mjesto izaslanja', help='Koristi se za joppd kolonu b3 u slučaju izaslanog rada.')
    
    # needed to calculate contributions base
    day_hours = fields.Float('Sati rada dnevno', default=8.00)
    #?
    month_hours = fields.Float('Mjesečni fond sati', digits=('Payroll'))

    # ostalo
    joppd_b61 = fields.Many2one('l10n.hr.joppd.sifre', 'JOPPD oznaka stjecatelja (6.1)', domain=[('code_type','=','P-2')],
                                default=_default_joppd_b61, help="Potrebno je unijeti oznaku kolone 6.1 na B strani ako nije 1")

    # tax deduction
    tax_deduction_ids = fields.One2many('hr.contract.tax.deduction', 'salary_parameters_id', string="Osobni odbitci",
                                        default=_get_deduction_ids, copy=True)
    tax_deduction_coef = fields.Float(string='Koeficijent osobnog odbitka', compute='_calculate_tax_deduction')
    tax_deduction_amount = fields.Float(string='Iznos osobnog odbitka', compute='_calculate_tax_deduction')
    annual_deduction = fields.Float(string='Godišnji odbitak')
    
    # accounting
    analytic_account_id = fields.Many2one('account.analytic.account', 'Konto analitike')
    journal_id = fields.Many2one('account.journal', 'Dnevnik plaća')
    input_line_ids = fields.One2many('hr.salary.parameters.input.line', 'parameters_id', 'Ulazi', copy=True)

    contract_date_from = fields.Date(related='contract_id.date_start')
    contract_date_to = fields.Date(related='contract_id.date_end_with_annexes')

    joppd_b9 = fields.Selection(_joppd_b9_sel, 'Oznaka radnog vremena', default='1', required=True)
    joppd_b72 = fields.Selection(_joppd_b72_sel, 'Tip umanjenja osnovice')

    def copy_parameters(self):
        return self.copy()
    
    @api.constrains('date_from', 'date_to', 'contract_date_from', 'contract_date_to')
    def _compare_dates_with_contract(self):
        """
        Params dates have to be within contract dates.
        Params begin before contract if params.date_from < contract.date_start (both fields are required).
        Params begin after contract if params.date_from > contract.date_end_with_annexes.
        Params end after contract if:
            1. both params and contract end dates are set and params.date_to > contract.date_end_with_annexes
            2. only contract end date is set
            3. (*) if contract end date is not set there is no need to check because params can not end after it
        """
        for params in self:
            if not params.contract_id:
                continue
            con = params.contract_id
            if params.date_from < con.date_start:
                msg = u'Parametri za ugovor {0} nisu valjani. Početni datum ne može biti prije početka ugovora ({1}).'
                raise ValidationError(msg.format(con.name, con.date_start))
            if con.date_end_with_annexes and params.date_from > con.date_end_with_annexes:
                msg = u'Parametri za ugovor {0} nisu valjani. Početni datum ne može biti nakon završetka ugovora ({1}).'
                raise ValidationError(msg.format(con.name, con.date_end_with_annexes))
            if (
                (params.date_to and con.date_end_with_annexes and params.date_to > con.date_end_with_annexes) or
                (con.date_end_with_annexes and not params.date_to)
            ):
                msg = u'Parametri za ugovor {0} nisu valjani. Završni datum ne može biti nakon završetka ugovora ({1}).'
                raise ValidationError(msg.format(con.name, con.date_end_with_annexes))
    
    @api.constrains('date_from', 'date_to')
    def _check_dates_for_employee_parameters(self):
        for params in self:
            # 1. employee has a params without end_date which started before this one
            domain = [
                ('employee_id', '=', params.employee_id.id), ('id', '<>', params.id),
                ('date_from', '<=', params.date_from), ('date_to', '=', False)
            ]
            params_ids = self.search(domain)
            if len (params_ids) > 0:
                p = params_ids[0]
                msg = u'Parametri za zaposlenika {0} nisu valjani. Već postoje parametri bez završnog datuma: {1}, {2}.'
                raise ValidationError(msg.format(params.employee_id.name, p.name, p.date_from))
            
            # 2. employee has a params with same start_date
            domain = [
                ('employee_id', '=', params.employee_id.id), ('id', '<>', params.id),
                ('date_from', '=', params.date_from)
            ]
            params_ids = self.search(domain)
            if len(params_ids) > 0:
                p = params_ids[0]
                msg = u'Parametri za zaposlenika {0} nisu valjani. Već postoje parametri s istim početnim datumom ({1}): {2}.'
                raise ValidationError(msg.format(params.employee_id.name, params.date_from, p.name,))

            # 3. employee has a params starting before and ending after date_from
            domain = [
                ('employee_id', '=', params.employee_id.id), ('id', '<>', params.id),
                ('date_from', '<=', params.date_from), ('date_to', '>=', params.date_from)
            ]
            params_ids = self.search(domain)
            if len (params_ids) > 0:
                p = params_ids[0]
                msg = u'Parametri za zaposlenika {0} nisu valjani. Već postoje parametri koji počinju prije i završavaju nakon odabranog početnog datuma ({1}): {2}.'
                raise ValidationError(msg.format(params.employee_id.name, params.date_from, p.name,))
            
            # 4. employee has params starting after this one while this one has no end date
            if not params.date_to:
                domain = [
                    ('employee_id', '=', params.employee_id.id), ('id', '<>', params.id),
                    ('date_from', '>=', params.date_from)
                ]
                params_ids = self.search(domain)
                if len (params_ids) > 0:
                    p = params_ids[0]
                    msg =  u'Parametri za zaposlenika {0} nisu valjani. Nije moguće kreirati parametre bez završnog datuma jer zaposlenik već ima parametre koji počinju nakon odabranog početnog datuma ({1}): {2}.'
                    raise ValidationError(msg.format(params.employee_id.name, params.date_from, p.name,))

            # 5. employee has a params starting before this one ends and ending after it
            if params.date_to:
                domain = [
                    ('employee_id', '=', params.employee_id.id), ('id', '<>', params.id),
                    ('date_from', '<=', params.date_to),
                    '|', ('date_to', '>=', params.date_from), ('date_to', '=', False),
                ]
                params_ids = self.search(domain)
                if len(params_ids) > 0:
                    p = params_ids[0]
                    msg = u'Parametri za zaposlenika {0} nisu valjani. Već postoje parametri koji počinju prije odabranog završnog datuma ({1}) i završavaju nakon odabranog početnog datuma ({2}): {3}.'
                    raise ValidationError(msg.format(params.employee_id.name, params.date_to, params.date_from, p.name,))
                
            #6 employee has a start date later then end date param in salary parameters
                if params.date_from > params.date_to:
                    msg = u"Greška pri unosu parametara. Završni datum ne smije biti prije početnog datuma."
                    raise ValidationError(msg)   
                             
        return True

    def is_contract_completed(self, contract_date_end):
        """
        Contract is completed if it has end_date and salary parameters which end on the same date.
        The purpose is to enable duplicate even if there is no more "space" (in terms of period) left on the contract for new salary parameters.
        In that case, we will search for a new contract which starts immediately after this one ends and create new salary parameters for the new contract.
        If there is no new contract, duplicate won't be allowed.
        """
        if not contract_date_end:
            return False
        domain = [('contract_id', '=', self.contract_id.id)]
        params = self.search(domain, order='date_from desc', limit=1)
        params_date_end = params.date_to
        contract_completed = params_date_end and (params_date_end == contract_date_end)
        return contract_completed
    
    def get_new_contract(self, contract_date_end):
        """
        Check if there is a contract with date_start = date_end_with_annexes (from this contract) + 1.
        """
        contract_obj = self.env['hr.contract']
        new_contract_date_start = contract_date_end + relativedelta.relativedelta(days=+1)
        domain = [
            ('employee_id', '=', self.employee_id.id),
            ('contract_type', '=', 'contract'),
            ('date_start', '=', new_contract_date_start),
            ('salary_parameters_ids', '=', False)
        ]
        new_contract = contract_obj.search(domain, order='date_start ASC', limit=1)
        return new_contract

    @api.returns('self', lambda value: value.id)
    def copy(self, default=None):
        """
        Duplicating salary paramaters creates a new instance with date_from:
            1. one day after date_to if latest params has end date
            2. today if latest params has no end date and is running
            3. one day after date_from if latest params has no end date and hasn't started yet
        Date end = contract end date.
        If there is no more space on this contract for new parameters
        (criteria: contract end date is set and there is params with date_to = contract date_end_with_annexes),
        we try to move the new params to a new contract if it exists
        (criteria: new contract start date = current contract end date + 1).
        """
        default = default or {}
        emp_id = self.employee_id.id
        contract_date_end = self.contract_id.date_end_with_annexes
        domain = [
            ('employee_id', '=', emp_id),
            ('contract_id', '=', self.contract_id.id)
        ]
        params = self.search(domain, order='date_from desc', limit=1)
        latest_params_start_date = params.date_from
        latest_params_end_date = params.date_to
        if not latest_params_end_date:
            if latest_params_start_date >= date.today():
                date_start = latest_params_start_date + relativedelta.relativedelta(days=+1) 
            else:
                date_start = date.today()
        else:
            date_start = latest_params_end_date + relativedelta.relativedelta(days=+1)
        
        if not self.env.context.get('custom_parameters'):
            default.update({
                'date_from': date_start,
                'date_to': contract_date_end,
            })
        contract_completed = self.is_contract_completed(contract_date_end)
        if contract_completed:
            new_contract = self.get_new_contract(contract_date_end)
            if new_contract:
                default.update({
                    'contract_id': new_contract.id,
                })
                if not self.env.context.get('custom_parameters'):
                    default.update({
                        'date_from': new_contract.date_start,
                        'date_to': new_contract.date_end_with_annexes,
                    })
        return super(HrSalaryParameters, self).copy(default)

    @api.onchange('contract_id')
    def onchange_contract_id(self):
        """
        Get transport amount from hr_employee when employee is changed.
        """
        employee = self.contract_id.employee_id
        if employee and employee.overall_transportation_for_payment:
            transport_rule = self.env['hr.salary.rule'].search([('code', '=', 'PRV')])
            data = [{
                'rule_id': transport_rule.id,
                'amount': employee.overall_transportation_for_payment,
            }]
            self.input_line_ids = data
            return
        self.input_line_ids = False
        return

    @api.depends('tax_deduction_ids')
    def _calculate_tax_deduction(self):
        """
        Use company settings with fixed tax base amounts to calculate total deduction amount and coef.
        """
        company = self.env.user.company_id
        base = company.i3_config_osnovica
        base_dependants = company.i3_config_osnovica_uzdrzavani
        for contract in self:
            total = 0.0
            base_coef = 0
            dependants_coef = 0
            for deduction in contract.tax_deduction_ids:
                if deduction.status:
                    if deduction.tax_deduction_id.name == 'Osnovni osobni odbitak':
                        base_coef = deduction.tax_deduction_coef
                    else:
                        dependants_coef += deduction.tax_deduction_coef
            total = base * base_coef + base_dependants * dependants_coef

            contract.tax_deduction_coef = base_coef + dependants_coef
            contract.tax_deduction_amount = total

    @api.onchange('struct_id')
    def onchange_struct_id(self):
        """
        Update struct_code when structure is selected.
        Remove work_abroad_city_id if non-work_abroad structure is selected.
        """
        if self.struct_code not in ['HR15', 'HR16', 'HR17', 'HR18']:
            self.work_abroad_city_id = False

    @api.onchange('internship_type', 'mio2')
    def onchange_benefit_type(self):
        """
        Update additional contribution percentages based on benefit type and mio2.
        """
        benefit_type = self.internship_type
        mio2 = self.mio2
        benefit_id = False
        benefit_obj = self.env['info3.work.exp.benefit']
        benefit = benefit_obj.search([('mio_2', '=', mio2), ('internship_type', '=', benefit_type)])
        if benefit and len(benefit) == 1:
            benefit_id = benefit.id
        self.benefit_id = benefit_id

    @api.onchange('benefit_id')
    def onchange_benefit_id(self):
        """
        Update additional contribution percentages based on benefit type and mio2.
        """
        if self.benefit_id:
            benefit = self.benefit_id
            self.dmio1b_percentage = benefit.dmio1b
            self.dmio2b_percentage = benefit.dmio2b

    @api.onchange('base_salary', 'salary_coef', 'calculate_salary_by_coefficient')
    def update_wage(self):
        for params in self:
            if params.calculate_salary_by_coefficient:
                params.wage = params.base_salary * params.salary_coef

    @api.onchange('job_id')
    def onchange_job(self):
        self.job_description = self.job_id.description
        self.salary_coef = self.job_id.coefficient
    @api.onchange('day_hours')
    def onchange_day_hours(self):
        """
        Set default work time code based on day hours.
        Code '3' (part time with child care) will have to be set manually.
        """
        if not self.day_hours:
            code = '0'
        elif self.day_hours == 8:
            code = '1'
        else:
            code = '2'
        self.joppd_b9 = code

    @api.depends('is_director','min_con_base_setting','min_con_base_setting_directors','day_hours')
    def _calculate_min_contributions_base(self):
        for param in self:
            coef = param.day_hours / 8
            if param.is_director:
                param.min_contributions_base = param.min_con_base_setting_directors * coef
            else:
                param.min_contributions_base = param.min_con_base_setting * coef

    @api.depends('max_con_base_setting','day_hours')
    def _calculate_max_contributions_base(self):
        for param in self:
            coef = param.day_hours / 8
            param.max_contributions_base = param.max_con_base_setting * coef
