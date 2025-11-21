# -*- coding: utf-8 -*-
# Part of Odoo. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api, _
from datetime import date, datetime
from . import payroll_common as paycom
from odoo.exceptions import ValidationError
from dateutil.relativedelta import relativedelta
from . import hr_salary_parameters as _PARAMS
from odoo.tools import float_compare
from calendar import monthrange
import workdays

# mapping used to map payslip line codes into the _SEPA_INCOME_CODES keys
# TODO: merge into one or extract settings on salary rule if possible
_SEPA_INCOME_CODES = paycom.get_sepa_income_codes()


class HrPayslipBankLine(models.Model):    
    """This class is used to show payments on payslip."""

    _name = 'hr.payslip.bank.line'
    _description = 'Stavka isplate po bankovnom računu zaposlenika za isplatni listić'
    _order = "code ASC"

    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', required=True, ondelete='cascade')
    description = fields.Char('Opis', help='Opis primitka koji se koristi za Opis u SEPA datoteci')
    code = fields.Char('Šifra primitka', help='Šifra primitka za poziv na broj u SEPA datoteci')
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun')
    acc_type = fields.Char('Vrsta')
    amount = fields.Float('Iznos', digits=('Payroll'))
    payment_method_id = fields.Many2one('l10n.hr.joppd.sifre', 'Način plaćanja', domain=[('code_type', '=', 'P-5')])


class HrPayslipSuspensionLine(models.Model):    
    """This class is used to show suspension payments on payslip."""
    _name = 'hr.payslip.suspension.line'
    _description = 'Stavka isplate obustave na listiću'

    payslip_id = fields.Many2one('hr.payslip', 'Isplatni listić', required=True, ondelete='cascade')
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun')
    amount = fields.Float('Iznos', digits=('Payroll')) 
    description = fields.Char('Opis', size=128)
    suspension_id = fields.Many2one('hr.salary.suspension', 'Obustava')
    is_company_account = fields.Boolean('Račun tvrtke',default=False)


class HrPayslip(models.Model):
    _inherit = 'hr.payslip'

    _order = 'name asc, date_from asc'

    def _check_lunch_fees(self):
        """
        Method limits payslips to only one type of lunch fee per month.
        """
        for payslip in self:
            current_lunch_line = payslip.input_line_ids.filtered(lambda x: x.code == 'PREH65' or x.code == 'PREH66')
            if not current_lunch_line:
                continue
            if len(current_lunch_line) > 1:
                raise ValidationError(_("Zaposlenik {0} ima pogrešne parametre na listiću {1}. Samo jedna stavka neoporezivog dodatka za prehranu je dozvoljena na mjesec.").format(payslip.employee_id.name, payslip.number))
            last_of_month = payslip.payslip_run_id.pay_date + relativedelta(months=+1, day=1, days=-1)
            domain = [
            ('id', '!=', payslip.id),
            ('employee_id', '=', payslip.employee_id.id),
            ('payslip_run_id.pay_date', '<=', last_of_month),
            ('payslip_run_id.pay_date', '>=', payslip.payslip_run_id.pay_date.replace(day=1))
            ]
            other_payslips = self.search(domain)
            for line in other_payslips.mapped('input_line_ids').filtered(lambda l: l.code in ['PREH65', 'PREH66']):
                if line.code != current_lunch_line.code:
                    raise ValidationError(_("Samo jedna stavka neoporezivog dodatka za prehranu je dozvoljena na mjesec.\nListić {0} - {1}\nListić {2} - {3}").format(payslip.number, current_lunch_line.code, line.payslip_id.number, line.code))
        return True

    def action_delete_payslip(self):
        """
        An action to enable force-deleting payslips in order to correct them.
        Every payslip needs to be on a payslip run, which means that
        in order to delete a single payslip which is not in 'draft' a user needs to
        first return the payslip run to draft and then calculate / pay it again.im using odoo 1
        This is a problem because it takes time and more importantly, payslips
        can not just be re-calculated at any point in time because not all input data is stored
        (e.g. sick leave hourly wages). 
        A possible alternative would be enabling modifications on paid payslips, but that solution
        requires much more effort than simple allowing delete.
        Returns:
            reload action to refresh the current view
        """
        # need to delete suspension payments first because of restricted foreign key (payslip_id)
        self.env.cr.execute("DELETE FROM hr_salary_suspension_payment WHERE payslip_id = %s", (self.id,))
        self.env.cr.execute("DELETE FROM hr_payslip WHERE id = %s", (self.id,))

        if self.env.context.get('not_on_run'):
            action = self.env.ref('l10n_hr_payroll_base.action_view_hr_payslip_form').read()[0]
            action['target'] = 'main'
            return action
        else:
            return {
                'type': 'ir.actions.client',
                'tag': 'reload',
            }
    
    def _calculation_type_sel(self):
        return _PARAMS._calculation_type_sel

    def _joppd_b72_sel(self):
        return self.env['hr.joppd.form.b']._b72_sel()
    

    _SICK_LEAVE_FUND_DATES_HELP = _(u"Ovo polje se koristi za određivanje oznake kolone 8 na JOPPD obrascu (prvi ili posljednji mjesec) "
                                    "u slučaju bolovanja na teret fonda. Obavezno ga je upisati ako postoji  "
                                    "bolovanje na teret fonda na listiću.")

    paid_date = fields.Date('Datum dospijeća', help='Datum isplate obračuna (u sustavu).')
    month_work_hours = fields.Float('Mjesečni fond sati', digits=('Payroll'))
    user_work_hours = fields.Float('Fond sati djelatnika', digits=('Payroll'))
    day_hours = fields.Float('Sati rada dnevno', default=8.00)
    state =  fields.Selection( selection_add=[('paid', 'Plaćeno')])
    annual_calculation = fields.Boolean('Godišnji obračun')
    manual_input = fields.Boolean('Ručni unos putnih troškova', default=False, help="Označite, ako želite ručno unijeti iznos za troškove prijevoza.")
    bank_lines = fields.One2many('hr.payslip.bank.line','payslip_id','Bankovni računi',readonly=True)
    suspension_lines = fields.One2many('hr.payslip.suspension.line','payslip_id','Stavke obustave',readonly=True)
    suspension_payment_ids = fields.One2many('hr.salary.suspension.payment', 'payslip_id', 'Povijest plaćanja')
    # used to color annual calculation payslips on tree view
    annual_type = fields.Selection([ ('no_values', ''),
                                ('values', 'Vrijednosti'),
                                ], 'Godišnji tip')
    payslips_number = fields.Integer('Broj razdoblja isplate')
    salary_in_kind = fields.Boolean(related='payslip_run_id.salary_in_kind', string='Plaća u naravi', readonly=True, store=True)
    min_sick_leave_hourly_rate = fields.Float('Minimalna satnica za obračun naknade za bolovanje na teret fonda', digits=('Payroll Hourly Wage'))
    max_sick_leave_hourly_rate = fields.Float('Maksimalna satnica za izračun bolovanja', digits=('Payroll Hourly Wage'))
    employee_number_of_days_in_month = fields.Float('Ukupan broj dana u mjesecu')
    employee_number_of_days_at_work = fields.Float('Broj dana u mjesecu za koje se plaćaju doprinosi')
    payslip_run_id = fields.Many2one('hr.payslip.run', string='Obračun plaće', required=True,
        copy=False,  ondelete='cascade') # override to add ondelete and required
    check_taxless_lunch_fee_amout = fields.Boolean('Provjeri iznos naknade za prehranu', default=True)
    
    employee_changed_municipality = fields.Boolean(default = False) #used on annual leave calculation
    # _constraints = [ (_check_worked_days_and_inputs, warning_message, ['worked_days_line_ids','input_line_ids'])]

    #######################################
    ### EMPLOYEE CALCULATION PARAMETERS ###
    #######################################
    salary_calculation_type = fields.Selection(_calculation_type_sel, 'Način izračuna', default='employee_work_hours', help=_PARAMS._CALCULATION_TYPE_HELP)
    use_hourly_wage = fields.Boolean('Temeljem satnice')
    hourly_wage = fields.Float('Bruto satnica')
    wage = fields.Float('Bruto plaća', tracking=True)
    sick_leave_average_hourly_wage_net = fields.Float('Prosječna neto satnica za bolovanje', digits=('Payroll Hourly Wage'))
    sick_leave_average_hourly_wage_gross = fields.Float('Prosječna bruto satnica za bolovanje', digits=('Payroll Hourly Wage'))
    sick_leave_average_no_salary_hourly_wage_gross = fields.Float('Prosječna bruto satnica za bolovanje na FOND kada nema prosjeka dvije isplaćene plaće', digits=('Payroll Hourly Wage'))
    sick_leave_average_no_salary_hourly_wage_net = fields.Float('Prosječna neto satnica za bolovanje na FOND kada nema prosjeka dvije isplaćene plaće', digits=('Payroll Hourly Wage'))
    min_contributions_base = fields.Float('Minimalna mjesečna osnovica za doprinose')
    max_contributions_base = fields.Float('Maksimalna mjesečna osnovica za doprinose')
    unused_leave_average_hourly_wage = fields.Float('Prosječna bruto satnica za neiskorišteni godišnji', digits=('Payroll Hourly Wage'))
    experience_coef = fields.Float('Koeficijent za dodatak na staž (%)', digits=('Payroll'))
    internship_total_years = fields.Integer('Godina',compute="_compute_internship_total_years",store=True)
    mio2 = fields.Boolean('MIO II stup')
    porez_razred_1_granica = fields.Float('Raspon 1. poreznog razreda')
    total_tax_base = fields.Float('Prethodna porezna osnovica', digits=('Payroll'))    
    supported_area = fields.Boolean('Potpomognuto područje', help='Ova opcija uključuje 50%% porezne olakšice kod izračuna plaće. Primjenjuje se nakon porezne olakšice za ratne invalide.')
    has_war_disability = fields.Boolean('Hrvatski ratni vojni invalid', help='Ova opcija uključuje olakšicu na porez na dohodak za HRVI kod obračuna plaće.')
    war_disability_pct = fields.Float('Postotak invalidnosti (%)', help='Postotak poreza na dohodak koji će se odbiti kod obračuna plaće. Primjenjuje se prije olakšice za potpomognuto područje.')
    suspension_ids = fields.One2many('hr.payslip.employee.salary.suspension', 'payslip_id', 'Obustave')
    total_tax_deduction = fields.Float('Ukupno iskorišteni osobni odbitak', digits=('Payroll'))
    tax_deduction_amount = fields.Float('Iznos osobnog odbitka')
    tax_deduction_coef = fields.Float('Koeficijent osobnog odbitka')
    dmio1b_percentage = fields.Float('Dodatni doprinos za 1. stup (%)')
    dmio2b_percentage = fields.Float('Dodatni doprinos za 2. stup (%)')
    health_insurance_contribution_pct = fields.Float('Doprinos za zdravstveno osiguranje (%)')
    health_insurance_contribution_pct_additional_income = fields.Float('Doprinos za zdravstveno osiguranje - drugi dohodak (%)')

    transport_amount = fields.Float('Prijevoz', digits=('Payroll'))
    
    calculate_salary_by_coefficient = fields.Boolean('Izračun plaće na temelju koeficijenta', default=1.00)
    base_salary = fields.Float('Osnovica plaće', default=0.0)
    salary_coef = fields.Float('Koeficijent plaće', default=1.00, digits=(6,4))
    degree_bonus = fields.Selection([
            ('none', 'Bez dodataka'),
            ('masters', 'Magisterij'),
            ('phd', 'Doktorat'),
        ],'Dodatak za stupanj obrazovanja', default='none')
    work_exp_bonus_coef = fields.Float('Koeficijent za dodatak na staž', digits=(6,4))
    department_distribution_ids = fields.One2many('hr.payslip.department.distribution', 'payslip_id', 'Analitička raspodjela po odjelima', help="Postavke za raspodjelu po odjelima za knjiženje")
    department_id = fields.Many2one('hr.department', related='salary_parameters_id.department_id', store=True)
    use_avg_hourly_wage_for_annual_leave_calculation = fields.Boolean('Računaj godišnji odmor prema satnici')
    work_exp_fee_limit_ids = fields.One2many('hr.payslip.work.experience.fee.limit', 'payslip_id', 'Ograničenja za jubilarnu nagradu')

    addr_type = fields.Many2one("hr.address.type", "Vrsta adrese")
    street = fields.Char('Ulica')
    street2 = fields.Char('Ulica2')
    city = fields.Many2one('res.city',string="Grad")
    zip_code = fields.Char('Prebivalište')
    county_id = fields.Many2one('res.country.state', 'Županija')
    country_id = fields.Many2one('res.country', string="Država")
    
    skip_minimum_check_sickleave_calculations = fields.Boolean(default=False)
    
    skip_minimum_check_sickleave_calculations = fields.Boolean(default=False)
    
    ###########################
    ### RES.CONFIG.SETTINGS ###
    ###########################
    i3_config_max_child_birth_fee = fields.Float('Maksimalni iznos naknade za rođenje djeteta')
    i3_config_taxless_bonus_amount = fields.Float('PN22 - Prigodne nagrade')
    i3_config_max_taxless_reward_amount = fields.Float('NAG - Nagrade za radne rezultate')
    i3_config_max_undocumented_lunch_fee_amount = fields.Float('Paušalna naknada za prehranu')
    i3_config_max_documented_lunch_fee_amount = fields.Float('Naknada za prehranu na temelju dokumentacije')
    i3_config_max_vacation_amount = fields.Float('ODM - Odmor radnika')
    i3_config_max_remote_work_fee_amount = fields.Float('RADIZDVMJ - mjesečna naknada za rad na izdvojenom mjestu')
    i3_config_max_supplementary_insurance = fields.Float('PREMZDROSIG - Premije dodatnog i dopunskog zdravstvenog osiguranja')
    i3_config_average_wage = fields.Float('Prosječna plaća za izračun obustava')
    i3_config_minimal_wage = fields.Float('Minimalna plaća')
    i3_config_min_contributions_base = fields.Float('Konfiguracija - Minimalna mjesečna osnovica za doprinose')
    i3_config_min_contributions_base_directors = fields.Float('Minimalna mjesečna osnovica za doprinose za članove uprave')
    i3_config_max_contributions_base = fields.Float('Konfiguracija - Maksimalna mjesečna osnovica za doprinose')
    i3_config_osnovica = fields.Float('Osnovica osobnog odbitka', default=4000.00)
    i3_config_osnovica_uzdrzavani = fields.Float('Osnovica za uzdržavane članove i djecu', default=2500.00)
    i3_config_razred_1 = fields.Float('Raspon prvog poreznog razreda')
    i3_config_razred_1_posto = fields.Float('Postotak poreza za 1. porezni razred')
    i3_config_razred_2_posto = fields.Float('Postotak poreza za 2. porezni razred')
    i3_config_capital_gain_1_pct = fields.Float('Postotak za 1. razred poreza na dohodak od kapitala', help='Koristi se za isplatu dobiti kroz obračun plaće')
    i3_config_min_sick_leave_fee_net = fields.Float('Minimalni neto iznos naknade za bolovanje')
    i3_config_max_sick_leave_fee_net = fields.Float('Maksimalni neto iznos naknade za bolovanje')
    i3_config_sick_hours_travel = fields.Boolean('Nemoj uračunati bolovanje za putne troškove')
    i3_config_sick_leave_company_percentage = fields.Float('Postotak za izračun bolovanja na teret poslodavca')
    i3_config_analytic_distribution_account_type_ids = fields.Many2many('account.account', 'payslip_account_account_rel', 'slip_id', 'account_type_id',
                                                        string='Vrste konta za analitičku raspodjelu')
    manual_edit = fields.Boolean('Ručno uređivanje', default=False)
    salary_parameters_id = fields.Many2one('hr.salary.parameters', 'Parametri plaće', required=True)
    sick_leave_fund_date_from = fields.Date('Početni datum bolovanja na teret fonda', help=_SICK_LEAVE_FUND_DATES_HELP)
    sick_leave_fund_date_to = fields.Date('Završni datum bolovanja na teret fonda', help=_SICK_LEAVE_FUND_DATES_HELP)
    
    mail_id = fields.Many2one('mail.mail', 'Email')
    mail_state = fields.Selection(related='mail_id.state', string='Status maila')
    hr_config_send_payslips_by_email = fields.Boolean(related='company_id.hr_config_send_payslips_by_email')
    show_nonpaid_salary_options = fields.Boolean(string='Prikaži postavke za neisplaćenu plaću', related='company_id.i3_config_show_nonpaid_salary_options')
    i3_config_min_sickleave_min_base = fields.Float('Minimalna mjesečna osnovica za bolovanje na FOND kad nema prosjeka dvije isplaćene plaće')

    employee_partner = fields.Many2one(related='employee_id.partner_id')
    bank_account_id = fields.Many2one('res.partner.bank', 'Bankovni račun',
        domain="[('partner_id', '=', employee_partner)]", readonly=True)
    protected_bank_account_id = fields.Many2one('res.partner.bank', 'Zaštićeni račun',
        domain="[('partner_id', '=', employee_partner)]", readonly=True)
    giro_bank_account_id = fields.Many2one('res.partner.bank', 'Žiro račun',
        domain="[('partner_id', '=', employee_partner)]", readonly=True)

    #fields for severance report
    severance = fields.Boolean(related='payslip_run_id.severance', string='Otpremnina', readonly=True, store=True)
    severance_from_year = fields.Char('Godina početka rada') #III. 1.
    severance_to_year = fields.Char('Godina završetka rada') #III. 2.
    number_of_years_severance = fields.Integer('Broj godina rada') #2.1
    average_gross_salary = fields.Float('Prosječna bruto plaća tri mjeseca prije završetka rada') #2.2 compute='get_average_gross_salary', 
    average_gross_salary_third = fields.Float('Trećina prosječne bruto plaće tri mjeseca prije završetka rada') #2.3
    calc_elem_average_gross_salary = fields.Char('Elementi izračuna - prosječna bruto plaća') #2.2. -> elementi obračuna
    calc_elem_average_gross_salary_third = fields.Char('Elementi izračuna - trećina prosječne bruto plaće') #2.3. -> elementi obračuna
    severance_pay_other_criteria = fields.Float('Druga mjerila za izračun otpremnine') #2.4
    calc_elem_severance_pay_other_criteria = fields.Char('Elementi izračuna - druga mjerila za izračun otpremnine') #2.4 -> elementi obračuna
    defined_leave = fields.Integer('Ugovoreni GO') #IV 2.1.
    unused_leave_current_year = fields.Integer('Neiskorišteni GO tekuća godina') #IV 2.2.
    unused_leave_previous_year = fields.Integer('Neiskorišteni GO prethodna godina') #IV 2.3.
    severance_remark = fields.Char('Napomena') #XII.

    hr_config_contributions_base_deduction_limit_1 = fields.Float(
        'Donja granica za umanjenje osnovice za doprinose', default=700,
        help='Donja granica bruto plaće za primjenu umanjenja osnovice za doprinose.\n'\
'Ako je plaća zaposlenika niža od donje granice, osnovica se umanjuje za fiksni iznos.')
    hr_config_contributions_base_deduction_limit_2 = fields.Float(
        'Gornja granica za umanjenje osnovice za doprinose', default=1300,
        help='Gornja granica bruto plaće za primjenu umanjenja osnovice za doprinose.\n'\
'Ako je plaća zaposlenika viša od gornje granice, nema umanjenja osnovice.')
    hr_config_contributions_base_deduction_fixed_amount = fields.Float(
        'Fiksni iznos umanjenja osnovice za doprinose', default=30,
        help='Ako je plaća zaposlenika niža od donje granice za umanjenje osnovice za doprinose, onda je ovo iznos za koji se osnovica umanjuje.')
    contributions_base_deduction_amount = fields.Float('Umanjenje osnovice za doprinose',
        help='Ručni unos umanjenja osnovice za doprinose - ako je unesen, pravilo UMOSNDOP se ne računa već uzima ovaj iznos.')
    use_manual_contributions_base_deduction = fields.Boolean('Koristi ručno unešeni iznos umanjenja osnovice', default=False)
    joppd_b72 = fields.Selection(_joppd_b72_sel, 'Tip umanjenja osnovice')

    #fields for annual calculation
    annual_planned_deduction = fields.Float('Godišnji osobni odbitak (planirani)', help='Ukupni odbitak na koji zaposlenik ima pravo u godini')
    annual_used_deduction = fields.Float('Iskorišteni osobni odbitak', help='Ukupni iskorišteni odbitak u godini') #IOOD
    annual_tax_base = fields.Float('Porezna osnovica', help='Ukupna porezna osnovica po kojoj je plaćen porez u godini') #POROSN
    annual_total_tax = fields.Float('Uplaćeni porez na dohodak', help='Ukupno plaćeni porez u godini') #PDOH
    annual_income = fields.Float('Prihod', help='Ukupni dohodak u godini')
    annual_brutto = fields.Float('Isplaćena bruto plaća', help='Ukupno isplaćeni bruto u godini')
    annual_salary_contributions = fields.Float('Obračunati doprinosi iz plaće', help='Uplaćeni doprinosi iz plaće u godini')
    annual_tax_obligation = fields.Float('Obveza poreza', help='Obveza poreza u godini (planirana porezna osnovica * stopa poreza)', readonly=True)
    annual_tax_calculated = fields.Float('Razlika poreza za uplatu/isplatu', help='Razlika između planiranog i uplaćenog poreza u godini', readonly=True)
    annual_planned_tax_base = fields.Float('Planirana porezna osnovica', help='Planirana porezna oznovica (dohodak - godišnji osobni odbitak)', readonly=True)

    hr_config_sick_leave_company_calc_method = fields.Selection([
        ('average_hourly_wage', 'Prosječna satnica'),
        ('contract_hourly_wage', 'Ugovorena satnica'),
        ('contract_salary', 'Ugovorena plaća')], 'Bolovanje - Način izračuna')

    @api.depends('employee_id','employee_id.internship_total_years','employee_id.internship_company_years')
    def _compute_internship_total_years(self):
        param = self.env['ir.config_parameter'].sudo().get_param('l10n_hr_hr_payroll.i3_config_calculate_experiance_allowance', default=0)
        for slip in self:
            if param == 'internal_experience':
                slip.internship_total_years = slip.employee_id.internship_company_years
            else:
                slip.internship_total_years = slip.employee_id.internship_total_years


    def get_severance_params(self):
        average = self.get_average_gross_salary()
        severance_from = self.env['hr.contract'].search([('employee_id', '=', self.employee_id.id)], order='date_start', limit=1).date_start.year
        severance_to = self.payslip_run_id.pay_date.year #or use newest contract?
        nb_of_years = severance_to - severance_from

        defined_leave = unused_current = unused_previous = 0
        annual_leave = self.employee_id.annual_leave_yearly_ids
        for leave in annual_leave:
            if leave.year.date_from.year == datetime.now().year:
                defined_leave = leave.leave
                unused_current = leave.remaining_leave
            elif leave.year.date_from.year == datetime.now().year - 1:
                unused_previous = leave.remaining_leave

        data = {
            'average_gross_salary': average,
            'average_gross_salary_third': average/3,
            'severance_from_year': severance_from,
            'severance_to_year': severance_to,
            'number_of_years_severance': nb_of_years,
            'defined_leave': defined_leave,
            'unused_leave_current_year': unused_current,
            'unused_leave_previous_year': unused_previous
        }
        return data

    @api.model
    def fields_view_get(self, view_id=None, view_type='form', toolbar=False, submenu=False):
        """
        Used to restrict user access when using payslips stat-button on employee form view.
        The purpose is to make the form readonly:
            - disable all m2o links (actually we add the class to all fields but it doesn't make a difference)
        """
        res = super().fields_view_get(view_id=view_id, view_type=view_type, toolbar=toolbar, submenu=submenu)
        if view_type=='form' and self._context.get('i3_my_employees_view_button'):
            res = IBC._update_node_attributes(['//field'], res, 'style', "pointer-events: none;")
        return res

    def get_calculation_parameters(self):
        """
        Add sick leave calculation method to payslip.
        """
        res = super().get_calculation_parameters()
        company = self.company_id
        data = {
            'hr_config_sick_leave_company_calc_method': company.hr_config_sick_leave_company_calc_method,
        }
        self.write(data)
        return res
    
    def set_severance_fields(self):
        severance_params = self.get_severance_params()
        self.write(severance_params)
        return True

    def get_average_gross_salary(self):
        sick_leave_wizard = self.env['sick.leave.average.wage.wizard']
        date_from = (self.payslip_run_id.pay_date + relativedelta(months=-3)).replace(day=1)
        date_to = (self.payslip_run_id.pay_date + relativedelta(months=-1)).replace(day=28)
        res = sick_leave_wizard.get_payslips_data(self.employee_id.id, date_from, date_to)
        return res['total_gross_salary'] / len(res['average_salary_line_ids']) if res['average_salary_line_ids'] else 0.00

    @api.onchange('severance_from_year', 'severance_to_year')
    def onchange_severance_year(self):
        if self.severance_from_year.isdigit() and self.severance_to_year.isdigit():
            severance_from_year = int(self.severance_from_year)
            severance_to_year = int(self.severance_to_year)
            self.number_of_years_severance = severance_to_year - severance_from_year

    @api.onchange('average_gross_salary')
    def onchange_average_gross_salary(self):
        if self.average_gross_salary:
            self.average_gross_salary_third = self.average_gross_salary / 3

    def unlink(self):
        """
        Trigger onchange to update yearly annual leaves in case a slip with annual leave was deleted.
        """
        emps = []
        for slip in self:
            emp = slip.employee_id
            if emp not in emps:
                emps.append(emp)
        res = super(HrPayslip, self).unlink()
        for emp in emps:
            emp.update_used_leave_by_year()
        return True

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create for purpose of adding month_work_hours and user_work_hours.
        month_work_hours are calculated for month before one in which this is created.
        """   
        for values in vals_list:
            employee_obj = self.env['hr.employee']
            payslip_run_obj = self.env["hr.payslip.run"]
            payroll_structure = self.env['hr.payroll.structure']
            
            salary_in_kind = payslip_run_obj.browse(values["payslip_run_id"]).salary_in_kind
            add_only_inputs = payslip_run_obj.browse(values["payslip_run_id"]).i3_add_only_inputs
            profit_payment = payslip_run_obj.browse(values["payslip_run_id"]).i3_profit_payment
            # if salary_in_kind:
            #     struct_id = payroll_structure.search([('code','=','HR8')])[0]
            #     if 'struct_id' in values:
            #         values['struct_id'] = struct_id.ud
            if profit_payment:
                struct_id = payroll_structure.search([('code','=','HR12')])[0]
                if 'struct_id' in values:
                    values['struct_id'] = struct_id.id
            # bank_account_id = employee_obj.browse(cr, uid,values['employee_id'], context=context).bank_account_id.id
            # protected_bank_account_id = employee_obj.browse(cr, uid,values['employee_id'], context=context).protected_bank_account_id.id

            # values.update({'bank_lines': [(0,0,{'bank_account_id': bank_account_id, 'type': 'normal'})]})
            # if protected_bank_account_id != False:           
            #     values['bank_lines'].append((0,0,{'bank_account_id': protected_bank_account_id, 'type': 'protected'}))
            if not add_only_inputs and not salary_in_kind:
                if "month_work_hours" not in values:           
                    params_obj = self.env['hr.salary.parameters']
                    wh = 0
                    if 'salary_parameters_id' in values and values['salary_parameters_id'] != False:
                        day_hours = params_obj.browse(values["salary_parameters_id"]).day_hours
                        if "payslip_run_id" in values and values["payslip_run_id"] != False:
                            payslip_hours_total = payslip_run_obj.browse(values["payslip_run_id"]).period_work_hours
                            payslip_days = payslip_hours_total / 8
                            wh = day_hours * payslip_days         
                    else:
                        name = employee_obj.browse(values['employee_id']).name
                        raise ValidationError(_('Employee {0} doesn\'t have valid parameters.').format(name))
                        wh = payslip_run_obj._get_period_hours(cr, uid, context) # TODO: what is this line supposed to do?
                    values["month_work_hours"] = wh

                if "worked_days_line_ids" in values:
                    wh = self.calculate_user_hours(values["worked_days_line_ids"])
                    values['user_work_hours'] = wh

        return super(HrPayslip, self).create(vals_list)

    def write(self, values):
        """
        Override write for purpose of adding user_work_hours.
        month_work_hours are calculated for month before one in which this is created.

        Added check for lunch fees in payslip 
        """   
        if "worked_days_line_ids" in values:
            wh = self.calculate_user_hours(values["worked_days_line_ids"])
            values['user_work_hours'] = wh
        res = super(HrPayslip, self).write(values)
        self._check_lunch_fees()
        return res

    def update_employee_tax_base(self):
        """
        Update tax base for single employee because we can have more than one salary in one month.
        Method with the same name exists on hr.payslip.run object.
        This one is added so we can update data for a single payslip on button.
        """

        ## TODO : rijesiti ovo preko ORM-a (try / except)
        for record in self:
            month = record.payslip_run_id.pay_date.month
            year = record.payslip_run_id.pay_date.year
            emp_id = record.employee_id.id

            sql = "UPDATE hr_employee SET (total_tax_base, total_tax_deduction) = (0, 0) WHERE id = %s"
                        
            try:     
                self.env.cr.execute(sql, (emp_id,))
                self.env.cr.commit()
            except:
                return False
            
            sql = """
                SELECT s.employee_id, l.CODE, sum(total) as total
                FROM hr_payslip_line l
                JOIN hr_payslip s ON l.slip_id = s.id
                JOIN hr_payslip_run r ON s.payslip_run_id = r.id
                WHERE l.CODE IN ('POROSN', 'IOOD')
                AND DATE_PART('month', r.pay_date) = %s
                AND DATE_PART('year', r.pay_date) = %s
                AND s.state = 'paid'
                AND s.employee_id = %s
                GROUP BY s.employee_id, l.CODE
                ORDER BY s.employee_id, l.CODE
            """
            try:  
                self.env.cr.execute(sql, (month, year, emp_id,))
                self.env.cr.commit()
            except:
                return False
            
            lines = self.env.cr.fetchall()
            emp_id = -1
                                                
            for row in lines:
                if emp_id == -1 or (emp_id != -1 and emp_id != row[0]):
                    emp_id = row[0]
                    vals = {}
                
                if row[1] == 'POROSN':     
                    vals['total_tax_base'] = row[2]
                elif row[1] == 'IOOD':
                    vals['total_tax_deduction'] = row[2]
                
                if len(vals) == 2:
                    emp = self.env['hr.employee'].search([('id', '=', emp_id)])
                    emp.write(vals)
        return True


    def _get_worked_days_lines(self, codes):
        return self.worked_days_line_ids.filtered(lambda wd: wd.code in codes and wd.number_of_hours > 0)
    
    def get_suspension_paid_amount(self, s):
        """
        In case there is more than one payslip in month:
        - 'distraint' and 'membership' have no limit because they depend directly on netto or brutto salary
        - 'fixed_amount' and 'alimony' have monthly amounts which need to be paid so we make sure they are not overpaid
        """
        paid_this_month = 0
        if s.suspension_type not in ('fixed','alimony') and s.amount:
            return paid_this_month
        payments = s.payment_ids.filtered(
            lambda p: p.payslip_id.paid_date and
                (p.payslip_id.paid_date.month == self.payslip_run_id.pay_date.month) and
                (p.payslip_id.paid_date.year == self.payslip_run_id.pay_date.year)
        )
        paid_this_month = sum(payment.amount for payment in payments)
        return paid_this_month
    
    def amount_on_payslip_run(self, code):
        # copy of method with same name in _get_payslip_lines method, Payslip class
        query = """
            SELECT SUM(pl.total)
            FROM hr_payslip AS hp, hr_payslip_line as pl
            WHERE hp.employee_id = %s AND 
            (hp.date_from < %s OR (hp.date_from = %s AND hp.id < %s))
            AND hp.id = pl.slip_id
            AND hp.payslip_run_id = %s
            AND pl.code = %s
        """
        self.env.cr.execute(query, (self.employee_id.id, self.date_from, self.date_from, self.id, self.payslip_run_id.id, code))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    def get_payslip_suspensions(self, emp):
        payslip_suspension_obj = self.env['hr.payslip.employee.salary.suspension']
        for susp in self.suspension_ids:
            susp.bank_account_distribution_ids.unlink()
        suspensions = []
        for suspension in emp.suspension_ids.filtered(lambda x: x.i3_active == True):
            susp_data = suspension.get_suspension_data()
            susp_data.update({
                'payslip_id': self.id,
                'suspension_id': suspension.id,
                'bank_account_distribution_ids': [(0, 0, {
                    'bank_account_id': line.bank_account_id.id,
                    'partner_id': line.partner_id.id,
                    'share': line.share,
                }) for line in susp_data['bank_account_distribution_ids']],
                'paid_this_month': self.get_suspension_paid_amount(suspension)
            })
            suspensions.append(susp_data)
        context_with_nosubscribe = self.env.context.copy()
        context_with_nosubscribe['mail_create_nosubscribe'] = True
        susp_ids = payslip_suspension_obj.with_context(context_with_nosubscribe).create(suspensions)
        return susp_ids
        
    def get_transport_input_amount(self, params):
        """
        Return PRV rule amount from input line if it exists.
        """
        amount = 0
        input_obj = self.env['hr.salary.parameters.input.line']
        transport_domain = [('parameters_id', '=', params.id), ('rule_id.code', '=', 'PRV')]
        transport_line = input_obj.search(transport_domain)
        if transport_line:
            amount = transport_line.amount
        return amount
    
    def get_payslip_departments(self, emp):
        """
        Get settings for accounting from employee.
        """
        slip_dep_obj = self.env['hr.payslip.department.distribution']
        self.department_distribution_ids.unlink()
        deps_data = []
        for line in emp.department_distribution_ids:
            deps_data.append({
                'department_analytic_id': line.department_analytic_id.id,
                'cost_center_id': line.cost_center_id.id,
                'percentage': line.percentage
            })
        dep_ids = slip_dep_obj.create(deps_data)
        return dep_ids
    
    def get_work_exp_fee_limits(self):
        data = []
        for limit in self.env['work.experience.fee.limit'].search([], order='years ASC'):
            data.append({
                'years': limit.years,
                'max_amount': limit.max_amount,
            })
        limit_ids = self.env['hr.payslip.work.experience.fee.limit'].create(data)
        return limit_ids

    def get_calculation_parameters(self):
        for each in self:
            each._compute_internship_total_years() ## update the internship_total_years calculation
            each.update_employee_tax_base() # needed so used tax deduction fields are up to date
            emp = each.sudo().employee_id # sudo() needed to read country_id
            param = each.salary_parameters_id
            city = emp.city
            company = each.company_id
            run = each.payslip_run_id
            work_hours =  each.payslip_run_id.period_work_hours

            city_tax_lower,city_tax_higher = city._get_tax_rate_on_date(run.pay_date)
            susp_ids = each.get_payslip_suspensions(emp)
            transport_amount = each.get_transport_input_amount(param)
            dep_ids = each.get_payslip_departments(emp)
            work_exp_fee_limit_ids = each.get_work_exp_fee_limits()
            emp_bank_accounts = each.employee_id.get_bank_accounts_on_date(each.payslip_run_id.pay_date)

            sick_leave_wages = each.get_sick_leave_wages()
            annual_leave_wage = each.get_annual_leave_wages()
            

            data = {
                'bank_account_id': emp_bank_accounts.get('normal').id,
                'protected_bank_account_id': emp_bank_accounts.get('protected').id,
                'giro_bank_account_id': emp_bank_accounts.get('giro_account').id,
                'salary_calculation_type': param.salary_calculation_type,
                'use_hourly_wage': param.use_wage_hour,
                'hourly_wage': param.wage_hour,
                'wage': param.wage,
                'day_hours': param.day_hours,
                'sick_leave_average_hourly_wage_gross': sick_leave_wages['average_salary_gross'],
                'sick_leave_average_hourly_wage_net': sick_leave_wages['average_salary_net'],
                'sick_leave_average_no_salary_hourly_wage_gross': sick_leave_wages['sick_leave_average_no_salary_hourly_wage_gross'],
                'sick_leave_average_no_salary_hourly_wage_net': sick_leave_wages['sick_leave_average_no_salary_hourly_wage_net'],
                'min_contributions_base': param.min_contributions_base,
                'max_contributions_base': param.max_contributions_base,
                'experience_coef': param.experience_coef,
                'mio2': param.mio2,
                'supported_area': param.supported_area,
                'has_war_disability': param.has_war_disability,
                'war_disability_pct': param.war_disability_pct,
                'tax_deduction_amount': param.tax_deduction_amount,
                'tax_deduction_coef': param.tax_deduction_coef,
                'dmio1b_percentage': param.dmio1b_percentage,
                'dmio2b_percentage': param.dmio2b_percentage,
                'calculate_salary_by_coefficient': param.calculate_salary_by_coefficient,
                'base_salary': param.base_salary,
                'salary_coef': param.salary_coef,
                'degree_bonus': param.degree_bonus,
                'health_insurance_contribution_pct': param.health_insurance_contribution_pct,
                'health_insurance_contribution_pct_additional_income': param.health_insurance_contribution_pct_additional_income,
                'transport_amount': transport_amount,
                'suspension_ids': [(6, 0, susp_ids.ids)],
                'department_distribution_ids': [(6, 0, dep_ids.ids)],
                'work_exp_fee_limit_ids': [(6, 0, work_exp_fee_limit_ids.ids)],
                'total_tax_base': emp.total_tax_base,
                'total_tax_deduction': emp.total_tax_deduction,
                'unused_leave_average_hourly_wage': annual_leave_wage,
                'internship_total_years': each.internship_total_years,
                'work_exp_bonus_coef': each.internship_total_years * param.experience_coef / 100.0,
                'addr_type': emp.addr_type.id,
                'street': emp.street,
                'street2': emp.street2,
                'city': emp.city.id,
                'zip_code': emp.zip,
                'county_id': emp.county_id.id,
                'country_id': emp.country_id.id,
                'use_avg_hourly_wage_for_annual_leave_calculation': emp.use_avg_hourly_wage_for_annual_leave_calculation,
                'porez_razred_1_granica': company.i3_config_razred_1 / 12,
                'i3_config_average_wage': company.i3_config_average_wage,
                'min_sick_leave_hourly_rate': company.i3_config_min_sick_leave_fee_net / work_hours,
                'max_sick_leave_hourly_rate': company.i3_config_max_sick_leave_fee_net / work_hours,
                'i3_config_max_child_birth_fee': company.i3_config_max_child_birth_fee,
                'i3_config_taxless_bonus_amount': company.i3_config_taxless_bonus_amount,
                'i3_config_max_taxless_reward_amount': company.i3_config_max_taxless_reward_amount,
                'i3_config_max_undocumented_lunch_fee_amount': company.i3_config_max_undocumented_lunch_fee_amount,
                'i3_config_max_documented_lunch_fee_amount': company.i3_config_max_documented_lunch_fee_amount,
                'i3_config_max_vacation_amount': company.i3_config_max_vacation_amount,
                'i3_config_max_remote_work_fee_amount': company.i3_config_max_remote_work_fee_amount,
                'i3_config_max_supplementary_insurance': company.i3_config_max_supplementary_insurance,
                'i3_config_average_wage': company.i3_config_average_wage,
                'i3_config_minimal_wage': company.i3_config_minimal_wage,
                'i3_config_min_contributions_base': company.i3_config_min_contributions_base,
                'i3_config_min_contributions_base_directors': company.i3_config_min_contributions_base_directors,
                'i3_config_max_contributions_base': company.i3_config_max_contributions_base,
                'i3_config_osnovica': company.i3_config_osnovica,
                'i3_config_osnovica_uzdrzavani': company.i3_config_osnovica_uzdrzavani,
                'i3_config_razred_1': company.i3_config_razred_1,
                'i3_config_razred_1_posto': city_tax_lower if city_tax_lower else company.i3_config_razred_1_posto,
                'i3_config_razred_2_posto': city_tax_higher if city_tax_higher else company.i3_config_razred_2_posto,
                'i3_config_capital_gain_1_pct': company.i3_config_capital_gain_1_pct,
                'i3_config_min_sickleave_min_base': company.i3_config_min_sickleave_min_base,
                'i3_config_max_sick_leave_fee_net': company.i3_config_max_sick_leave_fee_net,
                'i3_config_sick_hours_travel': company.i3_config_sick_hours_travel,
                'manual_input': company.i3_config_payslip_transport_amount_manual_input,
                'i3_config_sick_leave_company_percentage': company.i3_config_sick_leave_company_percentage,
                'i3_config_analytic_distribution_account_type_ids': [(6, 0, company.i3_config_analytic_distribution_account_type_ids.ids)],
                'hr_config_contributions_base_deduction_limit_1': company.hr_config_contributions_base_deduction_limit_1,
                'hr_config_contributions_base_deduction_limit_2': company.hr_config_contributions_base_deduction_limit_2,
                'hr_config_contributions_base_deduction_fixed_amount': company.hr_config_contributions_base_deduction_fixed_amount,
                'joppd_b72': param.joppd_b72,
            }
            if run.salary_in_kind:
                data.update({
                    'use_manual_contributions_base_deduction': True
                })
            if not each.env.context.get('on_create') and not each.payslip_run_id.i3_profit_payment:
                # used for profit payment - we set struct = profit_payment on create() so we don't want to immediately revert it to the usual struct
                # when using the button we always overwrite (except when payslip run is profit payment)
                data.update({
                    'struct_id': param.struct_id.id,
                })
            if each.payslip_run_id.severance:
                severance_params = each.get_severance_params()
                data.update(severance_params)

            if each.payslip_run_id.annual_calc:
                max_pay_date = fields.Date.to_string(each.payslip_run_id.pay_date.replace(month=12, day=31))
                min_pay_date = fields.Date.to_string(each.payslip_run_id.pay_date.replace(month=1,day=1))
                slip_ids = each.payslip_run_id.annual_calculation_get_payslips([emp.id], min_pay_date, max_pay_date)
                annual_calc_data = each.payslip_run_id.annual_calculation_get_employee_payslips_data(slip_ids, company, max_pay_date, annual_slip=each)
                dohodak, osnovica, porez, mjesecni_odbitak, planirani_odbitak, brutto, salary_contributions, razred_1_posto, razred_2_posto = each.payslip_run_id.get_annual_calc_payslip_data(annual_calc_data, emp.id, fetch_data=True)

                data.update({
                    'annual_brutto': brutto,
                    'annual_salary_contributions': salary_contributions,
                    'annual_planned_deduction': planirani_odbitak,
                    'annual_used_deduction': mjesecni_odbitak,
                    'annual_tax_base': osnovica,
                    'annual_total_tax': porez,
                    'annual_income': dohodak,
                    'i3_config_razred_1_posto': razred_1_posto,
                    'i3_config_razred_2_posto': razred_2_posto,
                })
            each.write(data)
        return True
    
    def clear_payslip_lines(self):
        """
        Delete all payslip lines.
        """
        self._clear_payslip_lines('hr_payslip_line', 'slip_id')
        self._clear_payslip_lines('hr_payslip_bank_line', 'payslip_id')
        self._clear_payslip_lines('hr_payslip_suspension_line', 'payslip_id')        
        return True

    def _clear_payslip_lines(self, model, payslip_key):
        """
        Delete all payslip lines.
        """
        sql = "DELETE FROM {} WHERE {} in " \
              "(SELECT id FROM hr_payslip WHERE id IN %s AND annual_calculation != true AND manual_edit != true)".format(model, payslip_key)
        try:    
            self.env.cr.execute(sql, (tuple(self.ids),))
            self.env.cr.commit()
        except:
            return False

        return True



    def get_sick_leave_wages(self):
        # Take date_to as last day of previous month
        date_to = self.payslip_run_id.date_end - relativedelta(months=1)
        date_to = date_to.replace(day=monthrange(date_to.year, date_to.month)[1])
        sick_leave_number_of_months = self.company_id.i3_config_sick_leave_number_of_months - 1
        period = self.payslip_run_id.get_period_for_average_wage(date_to, sick_leave_number_of_months)
        avg_salary_wiz_obj = self.env['sick.leave.average.wage.wizard']
        res = avg_salary_wiz_obj.get_payslips_data(self.employee_id.id, period['date_from'], period['date_to'])
        date_start_sick = self.payslip_run_id.date_start - relativedelta(months=1)
        workday_diff = workdays.networkdays(date_start_sick, date_to)
        workday_hours = workday_diff * 8
        data = {
            'average_salary_net': res['average_salary_net'],
            'average_salary_gross': res['average_salary_gross'],
            'sick_leave_average_no_salary_hourly_wage_gross': ({False: self.company_id.i3_config_min_contributions_base, True: self.i3_config_min_contributions_base} [self.i3_config_min_contributions_base != 0]) / workday_hours,
            'sick_leave_average_no_salary_hourly_wage_net': ({False: self.company_id.i3_config_min_sickleave_min_base, True: self.i3_config_min_sickleave_min_base} [self.i3_config_min_sickleave_min_base != 0]) / workday_hours,
        }
        self.skip_minimum_check_sickleave_calculations = (False, True) [res['slips_count'] < 2]
        return data

    def get_annual_leave_wages(self):
        date_to = self.payslip_run_id.date_end + relativedelta(months=-1)
        date_to = date_to.replace(day=monthrange(date_to.year, date_to.month)[1])
        annual_leave_number_of_months = self.company_id.i3_config_annual_leave_wage_number_of_months- 1
        period = self.payslip_run_id.get_period_for_average_wage(date_to, annual_leave_number_of_months)
        avg_wage_wiz_obj = self.env['unused.annual.leave.average.gross.wage.wizard']
        res = avg_wage_wiz_obj.get_payslip_data(self.employee_id.id, period['date_from'], period['date_to'], self.payslip_run_id.id)

        return res['gross_avg']

    def calculate_user_hours(self, lines):
        """
        Calculates how many hours user worked.
        Depends on one2many widget, and therefore only interpretes that data.
        """
        wh = 0
        payslip_wd_obj = self.env['hr.payslip.worked_days']
        rule_category_obj = self.env['hr.salary.rule.category']
        for line in lines:
            if line[0] != 2:
                if line[2] != False and "category_id" in line[2] and line[2]["category_id"] != False and 'number_of_hours' in line[2]:
                    cat = rule_category_obj.browse(line[2]["category_id"])
                    if not cat.skip_hours:
                        wh += line[2]["number_of_hours"]
                else:
                    if line[1] != False:
                        wd = payslip_wd_obj.browse(line[1])
                        if not wd.category_id.skip_hours:
                            if line[2] != False and "number_of_hours" in line[2]:
                                h = line[2]["number_of_hours"]
                            else:
                                h = wd.number_of_hours
                            wh += h
        return wh

    def calc_payslip_work_hours(self):
        """
        Calculate work hours for payslip.
        """
        self.ensure_one()
        hours = 0
        for line in self.worked_days_line_ids:
            if not line.category_id.skip_hours:
                hours += line.number_of_hours
        return hours

    def calc_month_work_hours(self):
        """
        Calculate total work hours for the month for employee.
        """
        self.ensure_one()
        employee_period_hours = 0
        full_time_hours = 8
        employee_day_hours = self.day_hours
        if self.payslip_run_id:
            full_time_period_hours = self.payslip_run_id.period_work_hours
            employee_period_hours = full_time_period_hours * employee_day_hours / full_time_hours
        return employee_period_hours
    
    def update_work_hours(self):
        """
        Update month and user work hours.
        """
        self.write({
            'month_work_hours': self.calc_month_work_hours(),
            'user_work_hours': self.calc_payslip_work_hours(),
        })
        return True

    def get_taxless_payments_max_amounts(self):
        params_obj = self.env['ir.config_parameter']
        max_apprentice = float(params_obj.sudo().get_param('l10n_hr_hr_payroll.i3_config_max_apprenticeship_amount'))
        max_scholarship = float(params_obj.sudo().get_param('l10n_hr_hr_payroll.i3_config_max_scholarship_amount'))
        max_bonuses = self.i3_config_taxless_bonus_amount
        max_rewards = self.i3_config_max_taxless_reward_amount
        max_lunch_fee_undoc = self.i3_config_max_undocumented_lunch_fee_amount
        max_lunch_fee_doc = self.i3_config_max_documented_lunch_fee_amount
        max_vacation_fee = self.i3_config_max_vacation_amount
        max_remote_work_expense = self.i3_config_max_remote_work_fee_amount
        max_supplementary_insurance = self.i3_config_max_supplementary_insurance
        data = {
            'yearly': {
                'PN22': max_bonuses,
                'NAG': max_rewards,
                'PREH65': max_lunch_fee_undoc,
                'PREH66': max_lunch_fee_doc,
                'ODM': max_vacation_fee,
                'PRAKSA': max_apprentice,
                'SKOL': max_scholarship,
                'RADIZDVMJ': max_remote_work_expense * 12,
                'PREMZDROSIG': max_supplementary_insurance,
            },
            'monthly': {
                'PREH65': max_lunch_fee_undoc / 12,
                'PREH66': max_lunch_fee_doc / 12,
                'PRAKSA': max_apprentice / 12,
                'SKOL': max_scholarship / 12,
                'RADIZDVMJ': max_remote_work_expense,
                'PREMZDROSIG': max_supplementary_insurance / 12, 
            }
        }
        return data

    def get_taxless_fee_amount_paid(self):
        """
        Return dict with all taxless payments made this year for employee.
        """
        taxless_payment_obj = self.env['employee.taxless.payment.line']
        amount_paid = {'yearly': {}, 'monthly': {}}
        for code in self.env['hr.payroll.salary.rule.configuration'].get_rules('taxless_payments'):
            if code in ('BOZ','USK','REG'): # PN22 is set as parent rule of these three rules so we only need one amount
                code = 'PN22'
            amount_paid['yearly'].update({code: 0.0})
            amount_paid['monthly'].update({code: 0.0})
        taxless_payment_ids = taxless_payment_obj.search([('employee_id', '=', self.employee_id.id)])
        for p in taxless_payment_ids:
            if p.payment_date.year == self.payslip_run_id.pay_date.year:
                key = p.salary_rule_id.code if p.salary_rule_id.code in amount_paid['yearly'] else p.salary_rule_id.parent_rule_id.code # group REG, USK and BOZ with PN22
                amount_paid['yearly'][key] += p.payment_amount
                if p.payment_date.month == self.payslip_run_id.pay_date.month:
                    key = p.salary_rule_id.code if p.salary_rule_id.code in amount_paid['yearly'] else p.salary_rule_id.parent_rule_id.code # group REG, USK and BOZ with PN22
                    amount_paid['monthly'][key] += p.payment_amount
        return amount_paid
    
    def check_taxless_payment_amount(self, max_taxless_amounts, codes_list, amount_paid):
        slip_line_obj = self.env['hr.payslip.line']
        exceeded = {}
        taxless_line_ids = slip_line_obj.search([('code', 'in', codes_list), ('slip_id', '=', self.id)])
        for line in taxless_line_ids:
            key = line.code if line.code in amount_paid else line.salary_rule_id.parent_rule_id.code # group USK, BOZ, REG with PN22
            exceeded.update({key: False})
            if float_compare((key in amount_paid and amount_paid[key]) + line.total, max_taxless_amounts[key], precision_rounding=self.company_id.currency_id.rounding) == 1:
                exceeded.update({key: True})
        return self.format_employee_msg(exceeded)

    def format_employee_msg(self, exceeded_taxless_payment_amount):
        emp_msg = ''
        for code in exceeded_taxless_payment_amount:
            if exceeded_taxless_payment_amount[code]:
                if not emp_msg:
                    emp_msg += self.employee_id.name + ' (' + code
                else:
                    emp_msg += ', ' + code
        emp_msg += ')' if emp_msg else ''
        return emp_msg

    def update_taxless_payments(self):
        payslip_line_obj = self.env['hr.payslip.line']
        emp_obj = self.env['hr.employee']
        taxless_line_ids = payslip_line_obj.search([('code', 'in', self.env['hr.payroll.salary.rule.configuration'].get_rules('taxless_payments')), ('slip_id', '=', self.id)])
        for line in taxless_line_ids:
            data = {
                'taxless_payment_ids': [(0, 0, {
                    'payslip_run_id': self.payslip_run_id.id,
                    'salary_rule_id': line.salary_rule_id.id,
                    'payment_date': self.payslip_run_id.pay_date,
                    'payment_amount': line.total
                })]
            }
            self.employee_id.write(data)
        return True

    def check_payslip(self, res):
        """
        All exceptions are raised here because they cause inconsistencies if raised on compute_sheet.
        """
        if res.get('exceeded_work_exp_fee'):
            max_amount = res.get('exceeded_work_exp_fee').get('max_amount')
            emp_amount = res.get('exceeded_work_exp_fee').get('emp_amount')
            raise ValidationError(_(u'Employee {0} has work experience fee ({1}) higher than maximum ({2}).').format(
                self.employee_id.name, emp_amount, max_amount))
        if 'exceeded_nzrd' in res and res['exceeded_nzrd']:
            max_child_birth_fee = self.i3_config_max_child_birth_fee
            raise ValidationError(_(u'Employee {0} has child birth fee higher than {1}.').format(self.employee_id.name, max_child_birth_fee))
        if 'unused_leave' in res and res['unused_leave']:
            raise ValidationError(_(u"Unused leaves can not be computed because average gross wage setting on payslip is non-positive. Payslip: {0}").format(
                ' - '.join([self.employee_id.name])))
        if 'tax_diff' in res and res['tax_diff']:
            raise ValidationError(u"Zaposlenik {0} ima razliku za porez vecu od 0,02.".format(self.employee_id.name))
        if 'contributions_diff' in res and res['contributions_diff']:
            raise ValidationError(u"Zaposlenik {0} ima razliku za doprinose vecu od 0,02.".format(self.employee_id.name))
        if 'base_diff' in res and res['base_diff']:
            raise ValidationError(u"Zaposlenik {0} ima razliku za osnovicu vecu od 0,02.".format(self.employee_id.name))
        if 'brutto_diff' in res and res['brutto_diff']:
            raise ValidationError(u"Zaposlenik {0} ima razliku u bruto iznosima.".format(self.employee_id.name))
        if 'payment_diff' in res and res['payment_diff']:
            raise ValidationError(u"Zaposlenik {0} ima razliku u isplati.".format(self.employee_id.name))
        if 'annual_leave_valid' in res and not res['annual_leave_valid']:
            raise ValidationError(u"Broj sati godisnjeg mora biti cijeli broj! Zaposlenik: {0}".format(self.employee_id.name))
        if res.get('exceeded_lunch_amount'):
            max_amount = res.get('exceeded_lunch_amount').get('max_amount')
            emp_amount = res.get('exceeded_lunch_amount').get('emp_amount')
            raise ValidationError(_(u'Employee {0} has lunch fee ({1}) higher than maximum ({2}).').format(self.employee_id.name, round(emp_amount,2), round(max_amount,2)))
        return True

    def calculate_lunch_fee_amount(self, line):
        year_limit, spent65, spent66 = self.calc_lunch_fee_limit(line)
        if line.code == 'PREH65':
            spent = spent65
        elif line.code == 'PREH66':
            spent = spent66
        spent += line.amount
        if float_compare(spent, year_limit, precision_rounding=self.company_id.currency_id.rounding) == 1:
            return {
                'emp_amount': spent,
                'max_amount': year_limit,
            }
        return False

    def calc_lunch_fee_limit(self, current_line):
        """ Check payments made between payslip run pay_date and beginning of the year."""
        max_lunch_fee_undoc_monthly = self.i3_config_max_undocumented_lunch_fee_amount / 12
        max_lunch_fee_doc_monthly = self.i3_config_max_documented_lunch_fee_amount / 12
        pay_date = current_line.slip_id.payslip_run_id.pay_date
        
        untaxed_payments = current_line.employee_id.taxless_payment_ids
        lunch_65_payments = untaxed_payments.filtered(
            lambda x: x.salary_rule_id.code == 'PREH65'
            and x.payment_date >= date(pay_date.year, 1, 1) 
            and x.payment_date <= pay_date)
        lunch_66_payments = untaxed_payments.filtered(
            lambda x: x.salary_rule_id.code == 'PREH66'
            and x.payment_date >= date(pay_date.year, 1, 1)
            and x.payment_date <= pay_date)

        spent65 = sum(payment.payment_amount for payment in lunch_65_payments)
        spent66 = sum(payment.payment_amount for payment in lunch_66_payments)
        
        limit = 0
        if current_line.code == 'PREH65':
            limit = pay_date.month * max_lunch_fee_undoc_monthly
            
        elif current_line.code == 'PREH66':
            limit = pay_date.month * max_lunch_fee_doc_monthly
        return limit, spent65, spent66
        
    def save_lines(self):
       return self.write({})

    def compute_sheet(self):
        """
        *** DO NOT RAISE EXCEPTIONS HERE! *** - they cause inconsistencies - use calc_payslip_run
        Calculate payslip and check if there is some difference in account distribution or suspension and distribute amount for payment on bank account (if protected exists).
        If there is an error in calculation, use slip_calc_completed to tell payslip_run something is wrong and don't allow close_payslip_run.
        Do not rewrite payslip lines if manual_edit is enabled.
        """
        slip_line_obj = self.env['hr.payslip.line']
        sequence_obj = self.env['ir.sequence']
        emp_obj = self.env['hr.employee']
        contract_obj = self.env['hr.contract']
        result = {}
        annual_leave_qty_valid = True
        additional_income_structs = paycom.get_structures()['additional_income']
        invalid_leave = ''
        for slip in self:
            # we need to update work hours first because calculation depends on it
            # month_work_hours depends on payslip run hours and employee day hours
            # user_work_hours depends on worked_days object
            # all of these requirements should be set before calculation and will not be changed by it
            slip.update_work_hours()
            if not slip.annual_calculation:
                # refresh contract data in case there were changes after slip was added on payslip run
                salary_payment = not slip.payslip_run_id.i3_add_only_inputs and not slip.payslip_run_id.i3_profit_payment and not slip.payslip_run_id.salary_in_kind
                additional_income_payment = slip.struct_id.code in additional_income_structs
                if not slip.manual_edit:
                    if salary_payment and not additional_income_payment:
                        # this function creates input line for PRV so it should be before 'get_payslip_lines'
                        slip.get_transport_amount()
                    # delete old payslip lines, get new ones
                    number = slip.number or sequence_obj.get('salary.slip')
                    old_slipline_ids = slip_line_obj.search([('slip_id', '=', slip.id)])
                    old_slipline_ids.unlink()

                    lines = [(0,0,line) for line in slip._get_payslip_lines([slip.contract_id.id], slip.id)]
                    slip.write({'line_ids': lines, 'number': number,})

                if salary_payment and not additional_income_payment:
                    if not slip.manual_edit:
                        slip.calculate_suspension_distribution()
                    invalid_leave = slip.update_annual_leave_qty()

            
            result = slip.calculate_account_distribution()
            result['invalid_leave'] = invalid_leave or []
            if result['invalid_leave'] and not self._context.get('whole_payslip_run'):
                raise ValidationError(_(u'Annual leave for the year {0} must be entered before entering monthly leaves for employee {1}').format(self.payslip_run_id.pay_date.year, ''.join(result['invalid_leave'])))
        return result
    
    def annual_leave_on_slip(self):
        annual_on_slip = 0
        day_work_hours = self.contract_id.resource_calendar_id.hours_per_day or 8.0
        for wd in self.worked_days_line_ids:
            if wd.code == 'GO':
                annual_on_slip += wd.number_of_hours
        annual_on_slip = annual_on_slip / day_work_hours
        return annual_on_slip

    def get_yearly_annual_leave_qty(self):
        leave_yearly_obj = self.env['info3.hr.employee.annual.leave.year']
        total_leave = 0
        used_leave = 0
        period_domain = [
            ('date_start', '<=', self.date_from),
            ('date_end', '>=', self.date_to),
            ('company_id', '=', self.company_id.id)
        ]
        period = self.env['date.range'].search(period_domain)
        employee_id = self.employee_id.id
        leave_yearly_ids = leave_yearly_obj.search([('employee_id', '=', employee_id), ('year', '=', period.fiscal_year.id)])
        if leave_yearly_ids:
            total_leave = leave_yearly_ids[0].total_leave
            used_leave = leave_yearly_ids[0].used_leave
        data = {
            'total': total_leave,
            'used': used_leave,
        }
        return data

    def update_annual_leave_qty(self):
        """
        If there is annual leave on slip - create or update monthly data for employee.
        Else delete corresponding record.
        Trigger onchange to update yearly data.
        """
        wd_obj = self.env['hr.payslip.worked_days']
        leave_monthly_obj = self.env['info3.hr.employee.annual.leave.periodically']
        leave_yearly_obj = self.env['info3.hr.employee.annual.leave.year']
        period_obj = self.env['date.range']
        employee_id = self.employee_id.id
        period_domain = [
            ('date_start', '<=', self.date_from),
            ('date_end', '>=', self.date_to),
            ('company_id', '=', self.company_id.id),
        ]
        period = period_obj.search(period_domain)
        slip_id = self.id
        day_hours = self.contract_id.resource_calendar_id.hours_per_day if self.contract_id.resource_calendar_id.hours_per_day else 8.0
        leave_monthly = leave_monthly_obj.search([
            ('employee_id', '=', employee_id),
            ('slip_id', '=', slip_id),
            ('period', '=', period.id)
        ], limit=1) # one record per run per employee is expected
        used_leave = 0.0
        annual_wd = wd_obj.search([('payslip_id', '=', slip_id), ('code', '=', 'GO')])
        if annual_wd:
            used_leave = annual_wd.number_of_hours / day_hours
        leave_yearly_ids = leave_yearly_obj.search([('employee_id', '=', employee_id), ('year', '=', period.fiscal_year.id)])
        employees_without_annual_leave = []
        if not leave_yearly_ids:
            employees_without_annual_leave.append(self.employee_id.name)
        leave_data = {
            'period': period.id,
            'used_leave': used_leave,
            'employee_id': employee_id,
            'slip_id': slip_id,
        }
        if leave_monthly:
            leave_monthly.write(leave_data)
        else:
            leave_monthly_obj.create(leave_data)
        self.employee_id.update_used_leave_by_year()
        return employees_without_annual_leave

    #calculate suspension distribution
    def calculate_suspension_distribution(self):
        suspension_line_obj = self.env['hr.payslip.suspension.line']
        vals = {}

        suspension_line_ids = suspension_line_obj.search([('payslip_id','=', self.id)])
        suspension_line_ids.unlink()
        result = self.i3_update_employee_suspensions()

        for line in result:
            vals.update({
                'payslip_id':self.id,
                'amount':result[line]['amount'],
                'description': result[line]['name'],
                'suspension_id':result[line]['suspension_id'],
                'bank_account_id': result[line]['bank_account_id'].id,
                'is_company_account': result[line]['is_company_account']
            })
            suspension_line_obj.create(vals)
        
        return True
    
    def get_suspendable_amount(self, s, suspendable_wage, average_wage):
        suspendable = 0
        if s.suspension_type == 'membership':
            suspendable = 0
        #if ratio is 1/1 or 1/2 we take that amount of salary for suspension (with the consent of worker/alimony)
        elif s.max_ratio == '1':
            ratio = 1.0
            suspendable = suspendable_wage
        elif s.max_ratio == '2':
            ratio = 1.0 / 2.0
            if suspendable_wage < average_wage:
                # 1/2 of employees wage is protected => 1/2 is suspendable
                suspendable = suspendable_wage * 1.0 / 2.0
            else:
                # 1/2 of average wage is protected => everything above it is suspendable
                suspendable = suspendable_wage - 1.0 / 2.0 * average_wage
        elif s.max_ratio == '34':
            ratio = 3.0 / 4.0
            if suspendable_wage < average_wage:
                # 1/4 of employees wage is protected => 3/4 is suspendable
                suspendable = suspendable_wage * 3.0 / 4.0
            else:
                # 1/4 of average wage is protected => everything above it is suspendable
                suspendable = suspendable_wage - 1.0 / 4.0 * average_wage
        else:
            ratio = 1.0 / 4.0
            if (suspendable_wage *(3.0/4.0)) > (average_wage * (2.0/3.0)):
                # 2/3 of average wage is protected => everything above it is suspendable
                suspendable = suspendable_wage - ((2.0/3.0) * average_wage)
            else:
                # 3/4 of employees wage is protected => 1/4 is suspendable
                suspendable = suspendable_wage * (1.0/4.0)
        return suspendable

    def get_membership_amount(self, s, bruto, neto):
        base = 0
        if s.membership_base == 'brutto':
            base = bruto
        elif s.membership_base == 'netto':
            base = neto
        return float(base * s.membership_base_pct) / 100.0
    
    def get_suspension_calculated_amount(self, s):
        """
        Return suspended amount for given suspension on same payslip run (from already calculated payslips).
        """
        query = """
            SELECT SUM(line.amount)
            FROM hr_payslip_suspension_line AS line
            LEFT JOIN hr_payslip AS slip ON slip.id = line.payslip_id
            WHERE line.suspension_id = %s AND
            (slip.date_from < %s OR (slip.date_from = %s AND slip.id < %s)) AND
            slip.payslip_run_id = %s
        """
        self.env.cr.execute(query, (s.id, self.date_from, self.date_from, self.id, self.payslip_run_id.id))
        res = self.env.cr.fetchone()
        return res and res[0] or 0.0

    def i3_update_employee_suspensions(self):
        """
        Calculate suspensions for each employee and update them.
        Copies of suspensions on payslips are used for calculation, as well as other parameters (average_wage and total_paid_amount)
        Payments are linked to the 'actual' suspension defined on employee.
        UPDATE salary rule for any changes because it has largely similar code.
        """
        result = {}
        search_ids = []
        bo_neto = 0
        lines = self.env['hr.payslip.line']
        susp_obj = self.env['hr.payslip.employee.salary.suspension']

        for slip in self:
            bo_neto = 0
            suspension_ids = [[s.sequence, s.id] for s in slip.suspension_ids]
            suspension_ids.sort()
            
            #PROSJECNA PLACA
            average_wage = slip.i3_config_average_wage

            #NETO
            neto = 0
            bruto = 0
            if slip.struct_id.code =='HR11':                    
                search_ids = lines.search([('code', 'in', ('NETO','NETOM')), ('slip_id', '=', slip.id)])
                for el in search_ids:
                    neto += el.total        
            else:
                search_ids = lines.search([('code', '=', 'NETO'), ('slip_id', '=', slip.id)])
                if search_ids:
                    neto = search_ids[0].total
            
            #BRUTO
            if slip.struct_id.code =='HR11':                  
                search_ids = lines.search([('code', 'in', ('BASIC','BASICM')), ('slip_id', '=', slip.id)])
                for el in search_ids:
                    bruto += el.total                       
            else:
                search_ids = lines.search([('code', '=', 'BASIC'), ('slip_id', '=', slip.id)])
                if search_ids:
                    bruto = search_ids[0].total
           
            #BOLOVANJE
            search_ids = lines.search([('code', 'in', ['BO','BO100']), ('slip_id', '=', slip.id)])
            if search_ids:
                bo = search_ids[0].total if len(search_ids) else 0
                bo_neto = bo * (neto / bruto) if bruto and bruto > 0 else 0

            if bo_neto:
                suspendable_wage = neto - bo_neto
            else:
                suspendable_wage = neto

            suspended = 0
            for s in susp_obj.browse([sus[1] for sus in suspension_ids]):

                if (s.start_date > slip.payslip_run_id.pay_date) or not s.i3_active:
                    continue
                amount = 0

                suspendable = self.get_suspendable_amount(s, suspendable_wage, average_wage)

                if s.suspension_type == 'membership':
                    amount = self.get_membership_amount(s, bruto, neto)
                elif s.suspension_type == 'distraint':
                    if s.end_amount:
                        remaining = s.end_amount - (s.start_amount + s.paid_amount)
                        amount = min(remaining, suspendable)
                    else:
                        amount = suspendable
                else:
                    remaining = s.end_amount - (s.start_amount + s.paid_amount) if s.end_amount > 0 else s.amount
                    amount = s.amount if remaining >= s.amount else remaining
                take = 0
                if amount > 0:
                    if s.suspension_type == 'membership':
                        take = amount
                    elif amount < (suspendable - suspended):
                        take = amount 
                    else:
                        take = max(suspendable - suspended, 0)
                    take = round(take, 2) # rounding is needed to match payslip_line (which is rounded to match amount in category_sum which is used in ISPL calculation)
                    
                    if s.suspension_type in ('fixed','alimony') and s.amount:
                        # in case there is more than one payslip in month
                        # distraint and membership have no limit because they depend directly on netto or brutto salary
                        # fixed_amount and alimony have monthly amounts which need to be paid so we make sure they are not overpaid
                        paid_this_month = slip.get_suspension_paid_amount(s.suspension_id)
                        paid_on_this_payslip_run = slip.get_suspension_calculated_amount(s.suspension_id)
                        suspension_amount = s.amount
                        to_pay = max(suspension_amount - paid_this_month - paid_on_this_payslip_run, 0)
                        take = min(take, to_pay)

                    if take:
                        for dist_line in s.bank_account_distribution_ids:
                            # added grouping by payslip to account for suspension payment creation in pay_payslip_run
                            key = (s.suspension_id.id, dist_line.bank_account_id.id, slip.id)
                            bank_acc_amount = round(float(take * dist_line.share) / 100, 2)
                            is_company_account = dist_line.partner_id == s.employee_id.company_id.partner_id or False
                            # group by actual suspension.id (on hr.employee) for payment history
                            if key not in result:
                                result.update({
                                    key: {
                                        'payslip_id': slip.id,
                                        'amount': bank_acc_amount,
                                        'name': s.name,
                                        'currency': s.currency_id.symbol,
                                        'suspension_id': s.suspension_id.id, 
                                        'employee_id': s.employee_id,
                                        'bank_account_id': dist_line.bank_account_id,
                                        'ref': s.ref,
                                        'model': s.model,
                                        'type': s.suspension_type,
                                        'is_company_account': is_company_account
                                    }
                                })
                            else:
                                result[key]['amount'] += bank_acc_amount
                suspended += take
        return result

    def get_transport_amount(self):
        """
        Calculate transport amount if manual input for transport amount is False.
        User can enter amount if manual input is True.
        """
        payslip_input_obj = self.env['hr.payslip.input']
        values = {}
        sick_hours = 0 
        amount = 0
        input_exists = False
        dont_calculate_sick_hours = self.i3_config_sick_hours_travel
        contract = self.contract_id
        if self.manual_input == True:           
            for line in self.input_line_ids:
                if line.code == 'PRV':
                    amount = line.amount
                    input_exists = True
        else: 
            input_exists = True         
            if not dont_calculate_sick_hours:
                for wd in self.worked_days_line_ids:
                    #list of hours when employee is not working
                    if wd.code in ('BO','BOF50', 'BOF70', 'BOF80', 'ONR', 'ONRF100', 'ONRF80', 'ONRF70', 'ONRF50', 'BO100'):     
                        sick_hours += wd.number_of_hours
                           	
            if sick_hours > 0:
                amount = ( self.transport_amount / self.month_work_hours ) * ( self.month_work_hours - sick_hours ) 
            else:
                amount = self.transport_amount
        values.update({
            'payslip_id': self.id,
            'contract_id': contract.id,
            'code': 'PRV',
            'name':'Putni trošak',
            'amount':amount
        })
        
        input_ids = payslip_input_obj.search(['&',('payslip_id', '=', self.id), ('code', '=' ,'PRV')])
        if len(input_ids) == 0:
            if input_exists:
                payslip_input_obj.create(values)
        else:
            input_ids.write({'amount': amount})
        return True

    def get_employee_slip_data(self, date_from, date_to, employee_id=False, contract_id=False, params=False):
        """
        Method is called when generating payslips using payslips_by_employees wizard.
        We need to provide data we don't yet have at that point: name, worked_days and inputs.
        """
        res = {
            'value': {
                'line_ids': [],
                #delete old input lines
                'input_line_ids': [(2, x,) for x in self.input_line_ids.ids],
                #delete old worked days lines
                'worked_days_line_ids': [(2, x,) for x in self.worked_days_line_ids.ids],
                'name': '',
            }
        }
        if (not employee_id) or (not date_from) or (not date_to):
            return res
        employee = self.env['hr.employee'].browse(employee_id)
        run_name = self.get_payslip_run_name()
        res['value'].update({
            'name': _('{0} {1}').format(run_name, employee.name),
            'company_id': employee.company_id.id,
        })

        if contract_id:
            #set the list of contract for which the input have to be filled
            contract_ids = [contract_id]
        else:
            #if we don't give the contract, then the input to fill should be for all current contracts of the employee
            contract_ids = employee.info3_get_contract_in_period(date_from, date_to)

        if not contract_ids:
            return res
        contract = self.env['hr.contract'].browse(contract_ids[0])
        res['value'].update({
            'contract_id': contract.id
        })
        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        input_line_ids = self.get_inputs(contracts, date_from, date_to, params)
        res['value'].update({
            'worked_days_line_ids': worked_days_line_ids,
            'input_line_ids': input_line_ids,
        })
        return res

    @api.onchange('date_from','date_to')
    def onchange_date(self):
        """
        Update employee worked days (= days for which contributions are paid).
        Find corresponding salary_parameters if no parameters is set.
        Read contract and structure from parameters.
        Recalculate worked days lines.
        """
        contract_obj = self.env['hr.contract']
        worked_days_obj = self.env['hr.payslip.worked_days']
        params_obj = self.env['hr.salary.parameters']

        #delete old worked days lines
        old_worked_days_ids = worked_days_obj.search([('payslip_id', '=', self.id)])
        old_worked_days_ids.unlink()

        employee_id = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        contract_id = self.contract_id
        params_id = self.salary_parameters_id
        struct_id = self.struct_id
        run_id = self.payslip_run_id

        if date_from and date_to:
            self.employee_number_of_days_at_work = (date_to - date_from).days + 1

        if (not employee_id) or (not date_from) or (not date_to):
            return

        param_domain = [
            '&', ('employee_id', '=', employee_id.id),
            '&', ('date_from', '<=', date_to),
            '|', ('date_to', '>=', date_from), ('date_to', '=', False)
        ]
        params_ids = params_obj.search(param_domain, order='date_from DESC')
        if not params_ids:
            self.salary_parameters_id = self.contract_id = self.struct_id = False
            return
        params_id = params_ids[0]
        
        self.salary_parameters_id = params_id.id

        #set the list of contract for which the input have to be filled
        contract_ids = params_id.contract_id.ids

        contract_record = contract_obj.browse(contract_ids[0])
        self.contract_id = contract_record and contract_record.id or False

        # get struct from salary_parameters if not already set
        if not struct_id:
            struct_record = params_id and params_id.struct_id or False
            if not struct_record:
                return
            self.struct_id = struct_record.id
        
        #computation of the salary input if not add_only_inputs and not salary_in_kind
        if not run_id.i3_add_only_inputs and not run_id.salary_in_kind:
            self.worked_days_line_ids = self.get_worked_day_lines([contract_record], date_from, date_to)
        return

    @api.onchange('employee_id')
    def onchange_employee(self):
        """
        Try to get salary parameters in given period.
        If not successful -> clear contract, parameters, structure (all depend on parameters).
        Else update contract and structure and get worked_days and inputs.
        """
        if not self.employee_id:
            self.salary_parameters_id = self.contract_id = self.struct_id = False
        if (not self.employee_id) or (not self.date_from) or (not self.date_to):
            return

        params_obj = self.env['hr.salary.parameters']
        employee = self.employee_id
        date_from = self.date_from
        date_to = self.date_to
        run_id = self.payslip_run_id
        contract_ids = []

        run_name = self.get_payslip_run_name()
        self.name = _('{1} {0}').format(employee.name, run_name)
        self.company_id = employee.company_id

        param_domain = [
            '&', ('employee_id', '=', employee.id),
            '&', ('date_from', '<=', date_to),
            '|', ('date_to', '>=', date_from), ('date_to', '=', False)
        ]
        params_ids = params_obj.search(param_domain, order='date_from DESC')
        if not params_ids:
            self.salary_parameters_id = False
            return
        params_id = params_ids[0]
        self.salary_parameters_id = params_id
        self.struct_id = params_id.struct_id.id
        self.contract_id = params_id.contract_id
        if not self.contract_id:
            return
        contract_ids = self.contract_id.ids

        #computation of the salary input
        contracts = self.env['hr.contract'].browse(contract_ids)
        worked_days_line_ids = self.get_worked_day_lines(contracts, date_from, date_to)
        worked_days_lines = self.worked_days_line_ids.browse([])
        for r in worked_days_line_ids:
            worked_days_lines += worked_days_lines.new(r)
        self.worked_days_line_ids = worked_days_lines

        input_line_ids = self.get_inputs(contracts, date_from, date_to, params_id)
        input_lines = self.input_line_ids.browse([])
        for r in input_line_ids:
            input_lines += input_lines.new(r)
        self.input_line_ids = input_lines
        return

    @api.onchange('contract_id')
    def onchange_contract(self):
        """
        Method copied from hr_payroll module to avoid calling override in payroll_account
        which forces journal from contract to payslip which is not desired behavior.
        We want to copy journal from contract only if it is set.
        """
        if not self.contract_id:
            self.struct_id = False
        self.with_context(contract=True).onchange_employee()
        if self.contract_id and self.contract_id.journal_id:
            self.journal_id = self.contract_id.journal_id.id
        return
    
    @api.onchange('salary_parameters_id')
    def onchange_salary_parameters(self):
        """
        Update contract and struct.
        """
        if not self.salary_parameters_id:
            self.struct_id = self.contract_id = False
            return
        self.contract_id = self.salary_parameters_id.contract_id.id
        self.struct_id = self.salary_parameters_id.struct_id.id
        return


    def get_payslip_run_name(self):
        """Return payslip run name based on ids or active_id."""
        context = self.env.context
        run_name = ''
        if 'active_id' in context and context['active_id']:
            run_name = self.env['hr.payslip.run'].browse(context['active_id']).name + ':'
        elif self.payslip_run_id:
            run_name = (self.payslip_run_id.name + ':') if self.payslip_run_id else run_name
        return run_name
    
    def get_inputs(self, contracts, date_from, date_to, params):
        """
        TODO: new model for payslip inputs
        """
        res = []
        run = False
        context = self.env.context
        payslip_run_obj = self.env['hr.payslip.run']
        if 'active_ids' in context:
            run = payslip_run_obj.browse(context['active_ids'])
        additional_income_structs = paycom.get_structures()['additional_income']
        salary_payment = run and (not run[0].i3_add_only_inputs and not run[0].salary_in_kind and not run[0].i3_profit_payment)
        additional_income_payment = params.struct_id.code in additional_income_structs
        if salary_payment or additional_income_payment or run == False:
            contract = params.contract_id
            for input_line in params.input_line_ids:
                rule = input_line.rule_id
                res.append({
                    'name': rule.name,
                    'code': rule.code,
                    'contract_id': contract.id,
                    'amount': input_line.amount
                })
        return res
    
    def _get_report_filename(self):
        name = ('Isplatni listić - {0}').format(self.employee_id.name)
        return name
    
    def get_timesheet_categories_domain(self):
        return self.env['hr.payroll.salary.rule.category.configuration'].get_category('timesheet_to_payslip_categories')
    
    def get_worked_day_lines(self, contracts, date_from, date_to):
        """
        Get worked day from timesheet to payslip.
        """        
        payslip_run_obj = self.env['hr.payslip.run']
        contract_obj = self.env['hr.contract']
        cat_obj = self.env['hr.salary.rule.category']
        
        ###
        #timesheet_obj is time tracking module named info3.timesheet
        #if module is not installed default times will be generated
        #if installed for each user times from timesheet will be collected
        ###
        res = {}
        run = False
        context = self.env.context
        if 'active_ids' in context:
            run =  payslip_run_obj.browse(context['active_ids'])
        if run and (not run[0].i3_profit_payment and not run[0].i3_add_only_inputs and not run[0].salary_in_kind ) or run == False:
            timesheet_obj = self.env['info3.timesheet'] if 'info3.timesheet' in self.env else None

            if timesheet_obj is None:
                work_hours = 0         
                if run:
                    work_hours = run[0].period_work_hours
        
                cat_rules = cat_obj.search([('code','=','RR')])
                    
                res = []
                for contract in contracts:
                    contract_hours =0
                    if work_hours > 0:              
                        contract_hours = work_hours
                    else:
                        contract_hours = contract.month_hours

                    contract.write({'month_hours':contract_hours})                
        
                    for rule in cat_rules:
                        if rule.code == "RR":
                            res.append({
                                'code':rule.code,
                                'name':rule.name,
                                'category_id':rule.id,
                                'contract_id':contract.id,
                                'number_of_days':0,
                                'number_of_hours':contract_hours
                            })                                                                                                                            
                return res
    
            else:
                ###TIMESHEET get data
                employee_ids = [ contracts[0].employee_id.id ]
                cat_codes = self.get_timesheet_categories_domain()

                #all codes that can be added/removed in worked_days
                domain = [('code', 'in', cat_codes)]
                cat_ids = cat_obj.search(domain)
                cats = cat_ids.read(['id','code','name'])

                ###API from info3.timesheet###
                #takes: employee_ids -> employee ids for who it needs to return times as [X, Y, Z...]
                #       date_from -> from which date should search times as YYYY-MM-DD
                #       date_to -> to which date should it search times as YYYY-MM-DD
                #       sum -> if True sums time by user
                #returns: 
                #       if sum {emp_id: {emp_name, total, night...}, emp_id: {...}...}
                #       else [{emp_id, emp_name, total, night...}, {...}, {...}]
                emp_times = timesheet_obj.get_employee_times(employee_ids, date_from, date_to, True)
                ###########


                #TODO: to hr_salary_rule_category add ref to info3.timesheet to avoid situation below
                res = []
                for id, times in emp_times.items(): #here will be only one user / line
                    for cat in cats: #iterate wanted categories and append hours
                        key = False
                        days = 0
                        if cat['code'] == 'RR' and 'total' in times:
                            key = 'total'
                        elif cat['code'] == 'GO' and 'annual_leave_hours' in times and times['annual_leave_hours'] > 0:
                            key = 'annual_leave_hours'
                        elif cat['code'] == 'BLG' and 'holiday' in times and times['holiday'] > 0:
                            key = 'holiday'
                        elif cat['code'] == 'BO' and 'sick_leave' in times and times['sick_leave'] > 0:
                            key = 'sick_leave'
                        elif cat['code'] == 'BOF70' and 'sick_leave_fund' in times and times['sick_leave_fund'] > 0:
                            key = 'sick_leave_fund'
                        elif cat['code'] == 'PRR' and 'overtime' in times and times['overtime'] > 0:
                            key = 'overtime'
                        elif cat['code'] == 'PRP' and 'non_working_day' in times and times['non_working_day'] > 0:
                            key = 'non_working_day'
                        elif cat['code'] == 'NOC' and 'night_work' in times and times['night_work'] > 0:
                            key = 'night_work'
                        elif cat['code'] == 'SMJRAD' and 'shift_work' in times and times['shift_work'] > 0:
                            key = 'shift_work'
                        elif cat['code'] == 'PD' and 'paid_leave' in times and times['paid_leave'] > 0:
                            key = 'paid_leave'
                        elif cat['code'] == 'PDT' and 'maternity_leave' in times and times['maternity_leave'] > 0:
                            key = 'maternity_leave'
                        elif cat['code'] == 'ODT' and 'paternity_leave' in times and times['paternity_leave'] > 0:
                            key = 'paternity_leave'
                        elif cat['code'] == 'RDT' and 'parental_leave' in times and times['parental_leave'] > 0:
                            key = 'parental_leave'
                        elif cat['code'] == 'TERI' and 'fieldwork_abroad_hours' in times and times['fieldwork_abroad_hours'] > 0:
                            key = 'fieldwork_abroad_hours'
                            days = times['fieldwork_abroad_days']
                        elif cat['code'] == 'TERT' and 'fieldwork_hours' in times and times['fieldwork_hours'] > 0:
                            key = 'fieldwork_hours'
                            days = times['fieldwork_days']
                        elif cat['code'] == 'SLP' and 'business_trip' in times and times['business_trip'] > 0:
                            key = 'business_trip'
                        elif cat['code'] == 'IZO' and 'isolation_hours' in times and times['isolation_hours'] > 0:
                            key = 'isolation_hours'
                        elif cat['code'] == 'RNED' and 'sunday_work_hours' in times and times['sunday_work_hours'] > 0:
                            key = 'sunday_work_hours'
                        elif cat['code'] == 'IR' and 'absence_fault' in times and times['absence_fault'] > 0:
                            key = 'absence_fault'
                        elif cat['code'] == 'NDOP' and 'unpaid_leave' in times and times['unpaid_leave'] > 0:
                            key = 'unpaid_leave'
                        elif cat['code'] == 'ODSR' and times.get('work_absence',0.0) > 0:
                            key = 'work_absence'
                        elif cat['code'] == 'NDOPSKRB' and times.get('unpaid_personal_care',0.0) > 0:
                            key = 'unpaid_personal_care'
                        if key:
                            res.append({
                                'category_id': cat['id'],
                                'code': cat['code'],
                                'contract_id': contracts[0].id,
                                'name': cat['name'],
                                'number_of_days': days,
                                'number_of_hours': times[key]
                            })
                if len(emp_times) == 0:
                    rr_cat = cat_obj.search([('code','=','RR')])
                    res.append({
                        'category_id': rr_cat.id,
                        'code': rr_cat.code,
                        'contract_id': contracts[0].id,
                        'name': rr_cat.name,
                        'number_of_days': 0,
                        'number_of_hours': 0
                    })

                ##RETURNS [{'category_id': 21, 'code': u'RR', 'contract_id': 7, 'name': u'Sati rada', 'number_of_days': 0, 'number_of_hours': 176.0}...]
            return res
        else:
            return res
    
    def check_work_exp_fee(self, payslip_line):
        emp_years = self.internship_total_years
        limits = self.work_exp_fee_limit_ids.filtered(lambda limit: limit.years <= emp_years).sorted('years', reverse=True)
        if not limits:
            return {
                'emp_amount': payslip_line.total,
                'max_amount': 0.00,
            }
        max_amount = limits[0].max_amount
        if payslip_line.total <= max_amount:
            return False
        return {
            'emp_amount': payslip_line.total,
            'max_amount': max_amount,
        }
        
    def init_sepa_income_dict(self):
        """
        Initialize data structure which will be used to create payments for SEPA file.
        _SEPA_INCOME_CODES is a mapping between salary rule code and its SEPA settings (payment name, payment code, whether or not it is paid on protected account).
        Here we use SEPA settings as primary key, add payment method as secondary key and in calculate_account_distribution() we distribute amounts.
        This structure is only used for taxless receipts, salary payment settings are integrated into create_payslip_bank_lines() method. TODO: add salary payment here?
        Each taxless receipt salary rule has the option to define payment method (using JOPPD code register) - this is why we can and need to group by payment method.
        All payments will be shown on payslip, for SEPA file we only use payment methods '1' and '2' (payment on bank account).
        """
        sifre_obj = self.env['l10n.hr.joppd.sifre']
        sifre_ids = sifre_obj.search([('code_type', '=', 'P-5')])
        sepa_income = {}
        for key in set(_SEPA_INCOME_CODES.values()):
            sepa_income[key] = {}
            for sifra_id in sifre_ids.ids:
                sepa_income[key][sifra_id] = 0
        return sepa_income
    
    #distribute amount for payment on regular and protected account and check if there is wrong distribution
    def calculate_account_distribution(self):
        # *** DO NOT RAISE EXCEPTIONS HERE! *** - they cause inconsistencies - use calc_payslip_run
        max_child_birth_fee = self.i3_config_max_child_birth_fee
        payroll_conf = self.env['hr.payroll.salary.rule.configuration']
        list_earnings = payroll_conf.get_rules('earnings')
        list_neto_dodaci = payroll_conf.get_rules('dodaci_neto')
        list_bolovanje_fond = payroll_conf.get_rules('bolovanje_fond')
        list_receipts_prot_acc = payroll_conf.get_rules('receipts_protected_account')
        list_unpaid = payroll_conf.get_rules('not_paid')
        list_tax_relief = payroll_conf.get_rules('tax_relief')
        sifre_obj = self.env['l10n.hr.joppd.sifre']
        default_payment_method = sifre_obj.search([('code_type', '=', 'P-5'), ('name','=', '1')])[0]

        # initialize variables
        total = 0
        
        average_wage = self.employee_id.average_wage
        amount = 0
        amount_protected = 0
        neto = 0
        bruto = 0
        ispl = 0
        bolovanje_fond = 0
        bolovanje = 0
        dodaci = 0
        putni = 0
        bez_putnih = 0
        dodaci_zasticeni_racun = 0
        dodaci_redovni_racun = 0
        sepa_income = self.init_sepa_income_dict()
        dodaci_bez_isplate = 0

        dohodak = 0
        porez = 0 
        porez_umanjenje = 0
        porez24_novo = 0  
        porez_novo = 0
        porez12 = 0
        porez24 = 0
        porez36 = 0
        doprinosi = 0
        doprinosi_ukupno = 0
        #for checking bruto
        ebrt = 0
        line_radni = 0
        line_bolovanje = 0
        line_ozljeda = 0
        line_bolovanje_100 = 0
        line_prr = 0
        line_prp = 0
        line_prn = 0
        line_drn = 0
        line_drp = 0
        line_go = 0
        line_izs = 0
        line_pd = 0
        line_categ_amount = 0
        line_blg = 0
        line_noc = 0
        line_nd = 0
        doprinosi_12 = 0
        line_dmio2 = 0
        obustave = 0

        radni_id = False
        line_bo_id = False
        line_onr_id = False
        line_bo100_id = False
        line_prr_id = False
        line_prp_id = False
        line_prn_id = False
        line_drn_id = False
        line_drp_id = False
        line_go_id= False
        line_izs_id = False
        line_pd_id = False
        line_categ_id = False
        line_blg_id = False
        line_noc_id = False
        line_dmio2_id = False
        line_24_id = False
        line_36_id = False
        line_nd_id = False
        update_id = False

        exceeded_work_exp_fee = False
        exceeded_nzrd = False
        izostanak = False
        unused_leave_on_slip = False
        unused_leave_invalid = False
        exceeded_bonuses = False
        tax_diff = False
        base_diff = False
        contributions_diff = False
        brutto_diff = False
        payment_diff = False
        sick_leave_fund_dates_not_entered = False
        exceeded_lunch_amount = False
        for line in self.line_ids:
            sepa_key = False # indicates if line has a specific SEPA receipt code
            payment_method = line.salary_rule_id.joppd_b161 or default_payment_method
            if line.category_id.code == 'DODNBI':
                dodaci_bez_isplate += line.total
            if line.category_id.code == 'NPIZN':
                total += line.total
            if line.code in ('NETO','NETOM','NETOINO'):
                neto += line.total
            if line.code in ('BASIC','BASICM'):
                bruto += line.total
            if line.code in ('ISPL','ISPLM'):
                ispl += line.total
            if line.code in list_bolovanje_fond:
                bolovanje_fond += line.total
                if line.total: # to avoid PDT, PDTK, RDT, IZO - for which there is no payment so no need to group for SEPA (so there are no settings in payroll_common)
                    sepa_key = True
                if not self.sick_leave_fund_date_from or not self.sick_leave_fund_date_to:
                    sick_leave_fund_dates_not_entered = True
            if line.code in ('BO','ONR','BO100'):
                if line.code == 'BO':
                    line_bo_id = line.id
                    line_bolovanje = line.total
                elif line.code == 'ONR':
                    line_onr_id = line.id
                    line_ozljeda = line.total
                else:
                    line_bo100_id = line.id
                    line_bolovanje_100 = line.total
                bolovanje += line.total
            if line.code in list_neto_dodaci:
                if line.code != 'PRV':
                    bez_putnih += line.total
                else:
                    putni += line.total
                # distribute receipts to normal and protected account - for suspension calculation and payment distribution
                # needs to be kept in sync with _SEPA_INCOME_CODES
                if line.code in list_receipts_prot_acc:
                    dodaci_zasticeni_racun += line.total
                else:
                    dodaci_redovni_racun += line.total
                sepa_key = True

            if line.code in ('DMIO1','DMIO2','DMIOI1','DMIOI2','DMIOU1','DMIOU2'):
                doprinosi_12 += line.total
                if line.code == 'DMIO2':
                    line_dmio2_id = line.id
                    line_dmio2 = line.total
            if line.code in ('DMIO','DMIOUM'):
                doprinosi += line.total
            if line.category_id.code =='DMIOU':
                doprinosi_ukupno += line.total
            if line.code =='DOH':
                dohodak += line.total
            if line.code =='PDOH':
                porez += line.total
                line_id = line.id
            if line.code =='POR12':
                porez12 += line.total
                line_12_id = line.id
            if line.code in ('POR24','POR1'):
                porez24 += line.total
                line_24_id = line.id
            if line.code in ('POR36','POR2'):
                porez36 += line.total
                line_36_id = line.id
            if line.code in list_tax_relief:
                porez_umanjenje += line.total
            if line.code in ('OBS','TOPOB','MSPORT'):
                obustave += line.total
            # PRN and PRP rules are not active, maybe we can remove them from this list? if so, we will have a problem calculating payslips where they were used
            if line.code in list_earnings:
                if line.code == 'RR':
                    radni_id = line.id
                    line_radni = line.total
                elif line.code == 'PRR':
                    line_prr_id = line.id
                    line_prr = line.total
                elif line.code == 'PRP':
                    line_prp_id = line.id
                    line_prp = line.total
                elif line.code == 'PRN':
                    line_prn_id = line.id
                    line_prn = line.total
                elif line.code == 'DRN':
                    line_drn_id = line.id
                    line_drn = line.total
                elif line.code == 'DRP':
                    line_drp_id = line.id
                    line_drp = line.total
                elif line.code == 'GO':
                    line_go_id = line.id
                    line_go = line.total               
                elif line.code == 'IZS':
                    line_izs_id = line.id
                    line_izs = line.total
                elif line.code == 'PD':
                    line_pd_id = line.id
                    line_pd = line.total
                elif line.code == 'BLG':
                    line_blg_id = line.id
                    line_blg = line.total
                elif line.code == 'NOC':
                    line_noc_id = line.id
                    line_noc = line.total
                elif line.code == 'ND':
                    line_nd_id = line.id
                    line_nd = line.total
                elif line.code == 'ODSR': 
                    line_odsr_id = line.id
                    line_odrs = line.total    
                elif line.code == 'RNED':
                    line_rned_id = line.id
                    line_rned = line.total
                else:
                    line_categ_id = line.id
                    line_categ_amount = line.total

                ebrt += line.total
            if line.code == 'NAGST':
                exceeded_work_exp_fee = self.check_work_exp_fee(line)
            if line.code == 'NZRD' and line.total > max_child_birth_fee:
                exceeded_nzrd = True
            if line.code in list_unpaid:
                izostanak = True
            if line.code in ('GON', 'GONPR'):
                unused_leave_on_slip = True
                if self.unused_leave_average_hourly_wage <= 0:
                    unused_leave_invalid = True
            if line.code == 'PREH65' or line.code == 'PREH66':
                exceeded_lunch_amount = self.calculate_lunch_fee_amount(line)
            # update sepa_income dict
            if sepa_key and payment_method._add_to_payment_order():
                sepa_income[_SEPA_INCOME_CODES[line.code]][payment_method.id] += line.total
        # provjera nema smisla za listice godisnjeg obracuna stoga je dodana iznimka
        # od 01.01.2024. pravilo PRIR se vise ne koristi, ali je provjera ostavljena kako bi se mogla obracunati stara placa samo dodavanjem pravila u strukturu
        # kad pravila nema u strukturi iznos je 0 pa ne smeta
        if ((round(dohodak - porez,2)) != neto
                and porez > 0 and not self.annual_calculation):
                # the following condition is probably ineffective as tax is updated as soon as payslip is created
                #'updated_tax' in context and context.get('updated_tax', False) and 
            razlika = round(round(dohodak - porez,2) - neto,2)
            if abs(razlika) > 2:
                tax_diff = True
            else:
                porez_novo = porez + razlika
                porez24_novo = porez24 + razlika
                #line_ids = payslip_line_obj.search(cr,uid,[('code','=','PDOH'),('slip_id','=',slip.id)],context=context)
                sql = """update hr_payslip_line set amount = {0}, total = {0}, computed_total = {0} where id = {1} """.format(porez_novo, line_id)
                self.env.cr.execute(sql)
                self.env.cr.commit()
        
                sql = """update hr_payslip_line set amount = {0}, total = {0}, computed_total = {0} where id = {1} """.format(porez24_novo, line_24_id)

                self.env.cr.execute(sql)
                self.env.cr.commit()
        
        #    #print 'u{0}'.format(str(slip.employee_id.id))
        #if round((ebrt - doprinosi),2) != round(dohodak,2):
        #    print 'u{0}'.format(str(slip.employee_id.id))
        #if round(ebrt,2) != round((dohodak + doprinosi),2):
        #    print 'u{0}'.format(str(slip.employee_id.id))

        #if round(ebrt,2) != round(bruto,2):
        #    print 'u{0}'.format(str(slip.employee_id.id))
        if round(doprinosi,2) != round(doprinosi_12,2):
            razlika_doprinos = round(round(doprinosi,2) - round(doprinosi_12,2),2)            
            if abs(razlika_doprinos) > 2:
                contributions_diff = True
            elif line_dmio2_id and razlika_doprinos != 0:
                dmio2 = line_dmio2 + razlika_doprinos
                line_record = self.env['hr.payslip.line'].browse(line_dmio2_id)
                line_record.with_context(skip_compute_total=True).sudo().write({'total': dmio2,'amount': dmio2,'computed_total': dmio2})

        #check difference for brutto and categories that goes into brutto, it should be same if not and or substract difference from one of category
        if round(ebrt,2) != round(bruto,2) and not izostanak and not unused_leave_on_slip:
            razlika_ebrt = round(round(bruto,2) - round(ebrt,2),2)
            if abs(razlika_ebrt) > 2:
                base_diff = True
            elif radni_id and line_radni > 0:
                line_razlika = line_radni + razlika_ebrt
                update_id = radni_id
            elif line_bo_id and line_bolovanje > 0:
                line_razlika = line_bolovanje + razlika_ebrt
                update_id = line_bo_id
            elif line_onr_id and line_ozljeda > 0:
                line_razlika = line_ozljeda + razlika_ebrt
                update_id = line_onr_id
            elif line_bo100_id and line_bolovanje_100 > 0:
                line_razlika = line_bolovanje_100 + razlika_ebrt
                update_id = line_bo100_id
            elif line_prr_id and line_prr > 0:
                line_razlika = line_prr + razlika_ebrt
                update_id = line_prr_id
            elif line_prp_id and line_prp > 0:
                line_razlika = line_prp + razlika_ebrt
                update_id = line_prp_id
            elif line_prn_id and line_prn > 0:
                line_razlika = line_prn + razlika_ebrt
                update_id = line_prn_id
            elif line_drn_id and line_drn > 0:
                line_razlika = line_drn + razlika_ebrt
                update_id = line_drn_id
            elif line_drp_id and line_drp > 0:
                line_razlika = line_drp + razlika_ebrt
                update_id = line_drp_id
            elif line_go_id and line_go > 0:
                line_razlika = line_go + razlika_ebrt
                update_id = line_go_id
            elif line_izs_id and line_izs > 0:
                line_razlika = line_izs + razlika_ebrt
                update_id = line_izs_id
            elif line_pd_id and line_pd > 0:
                line_razlika = line_pd + razlika_ebrt
                update_id = line_pd_id
            elif line_blg_id and line_blg > 0:
                line_razlika = line_blg + razlika_ebrt
                update_id = line_blg_id
            elif line_noc_id and line_noc > 0:
                line_razlika = line_noc + razlika_ebrt
                update_id = line_noc_id
            elif line_nd_id and line_nd > 0:
                line_razlika = line_nd + razlika_ebrt
                update_id = line_nd_id
            elif line_categ_id and line_categ_amount > 0:
                line_razlika = line_categ_amount + razlika_ebrt
                update_id = line_categ_id
            elif line_odsr_id and line_odrs > 0:
                line_razlika = line_odrs + razlika_ebrt
                update_id = line_odsr_id
            elif line_rned_id and line_rned > 0:
                line_razlika =line_rned + razlika_ebrt
                update_id = line_rned_id
            else:
                brutto_diff = True
            if update_id and line_razlika > 0:
                line_record = self.env['hr.payslip.line'].browse(update_id)
                line_record.with_context(skip_compute_total=True).sudo().write({'total': line_razlika,'amount': line_razlika,'computed_total': line_razlika})

        if bruto > 0 and bolovanje > 0:
            suma = ispl - putni - (bolovanje * (neto/bruto)) - (bez_putnih)
        else:
            suma = ispl - putni - bez_putnih
        dodaci =  putni + bez_putnih    
        
        # there is no payment for salary in kind so no need for this check
        # for annual_calculation there is always difference in payment
        # if (not self.annual_calculation and not self.payslip_run_id.salary_in_kind and
        #         round(round(dodaci,2) + round(bolovanje_fond,2) + round(neto,2) - round(obustave,2) - round(dodaci_bez_isplate, 2),2) != round(ispl,2)):
        #     payment_diff = True
        
        #Ako je 3/4 neto place vece od 2/3 prosjecne neto place na zasticeni racun moze maksimalno 2/3 prosjecne neto place
        #U slucaju da je 3/4 neto place manje onda na zasticeni racun ide 3/4 neto place
        if self.protected_bank_account_id:
            if (neto *(3.0/4.0)) > (average_wage * (2.0/3.0)):
                neto23 = round(((2.0/3.0) * average_wage),2)
            else:
                neto23 = round(neto * (3.0/4.0),2)
            
            #ako je iznos bez putnih i dodataka na placu manji od iznosa koji ide na zasticeni racun, sve ide na zasticeni racun
            if suma <= neto23:
                amount = 0
                amount_protected = suma
            else:
                amount = suma - neto23 # x ide na normalan racun
                amount_protected = neto23 #zasticeni racun + dodaci + bolovanje

            #ukoliko imamo dodataka na placu oni idu direktno na zasticeni racun ili bolovanje na fond
            if dodaci:
                amount_protected += dodaci_zasticeni_racun
                amount += dodaci_redovni_racun
            if bolovanje_fond:
                amount_protected += bolovanje_fond
                amount = ispl - round(amount_protected,2)

            #bolovanje na teret poduzeca -> na zasticeni racun ide udio bruto bolovanja u neto iznosu
            if bolovanje:
                if bruto > 0:
                    amount_protected += bolovanje * (neto/ bruto)
                    amount = ispl - round(amount_protected,2)                

            # ako je iznos na zasticenom veci od isplate -> zasticeni = isplata, redovni = 0
            if amount_protected > ispl:
                amount_protected = ispl
                amount = ispl - amount_protected
            
            # ponekad zbog zaokruzivanja jedna lipa ode na redovni kad bi sav iznos trebao ici na zasticeni
            if amount < 0.02:
                amount_protected += amount
                amount -= amount
        else: 
            amount = ispl

        self.create_payslip_bank_lines(amount, amount_protected, neto,
                                dodaci_redovni_racun, dodaci_zasticeni_racun, sepa_income, default_payment_method)

        # return whether employee has exceeded max bonuses so we can print warning for all users at once
        res = {}

        res.update({
            'exceeded_work_exp_fee': exceeded_work_exp_fee,
            'exceeded_nzrd': exceeded_nzrd,
            'unused_leave': unused_leave_invalid,
            'tax_diff': tax_diff,
            'contributions_diff': contributions_diff,
            'base_diff': base_diff,
            'brutto_diff': brutto_diff,
            'payment_diff': payment_diff,
            'sick_leave_fund_dates_not_entered': sick_leave_fund_dates_not_entered,
            'exceeded_lunch_amount': exceeded_lunch_amount,
        })
        return res

    def create_payslip_bank_lines(self, amount, amount_prot,
                                    neto, dodaci_red, dodaci_zast, sepa_income, default_payment_method):
        """
        Željeno ponašanje:
        1. Drugi dohodak:
            - jedna stavka sa šifrom primitka '130' i način isplate = 2 (žiro račun)
        2. Redovni dohodak (plaća):
            a) Nema zaštićenog računa
                - jedna stavka sa šifrom '100'
                - po jedna stavka za svaku kombinaciju (šifra primitka, način isplate)
            b) Postoji zaštićeni račun
                - jedna stavka sa šifrom '110' na zaštićeni račun
                - jedna stavka sa šifrom '120' na redovni račun
                - po jedna stavka za svaku kombinaciju (šifra primitka, način isplate, vrsta računa (redovni ili zaštićeni))
        """
        additional_income_structs = paycom.get_structures()['additional_income']
        bank_line_obj = self.env['hr.payslip.bank.line']
        old_bank_line_ids = bank_line_obj.search([('payslip_id', '=', self.id)])
        old_bank_line_ids.with_context(skip_compute_total=True).unlink() # unlink calls recompute_all after the ORM (formally SQL ) injection for one cent corrections so it recomputes the total field in hr.payslip.line with wrong info 
        if self.struct_id.code in additional_income_structs:
            return self._additional_income_bank_lines(amount)
        if not amount_prot:
            return self._regular_payment_bank_lines(amount, sepa_income, default_payment_method)
        return self._protected_payment_bank_lines(amount, amount_prot, sepa_income, default_payment_method)

    def _additional_income_bank_account(self):
        sifre_obj = self.env['l10n.hr.joppd.sifre']
        if self.giro_bank_account_id:
            payment_method = sifre_obj.search([('code_type', '=', 'P-5'), ('name','=', '2')], limit=1)[0]
            return self.giro_bank_account_id, payment_method, 'gyro'
        payment_method = sifre_obj.search([('code_type', '=', 'P-5'), ('name','=', '1')], limit=1)[0]
        return self.bank_account_id, payment_method, 'normal'
    
    def _additional_income_bank_lines(self, amount):
        # drugi dohodak
        account, payment_method, account_type = self._additional_income_bank_account()
        self.create_bank_line((self.payslip_run_id.name, '130'), payment_method.id, amount, account.id, account_type)
        return True
    
    def _regular_payment_bank_lines(self, amount, sepa_income, default_payment_method):
        # izdvojimo dodatke s posebnom sifrom, ostalo ide sa sifrom 100 (osim ako je ugovor o djelu)
        acc_id = self.bank_account_id.id
        redovni = amount - sum([sepa_income[code][payment_method] for code in sepa_income for payment_method in sepa_income[code]])
        income_code = '150' if self.payslip_run_id.i3_profit_payment else '100'
        self.create_bank_line((self.payslip_run_id.name, income_code), default_payment_method.id, redovni, acc_id, 'normal')
        for key in sepa_income:
            for payment_method_id in sepa_income[key]:
                if sepa_income[key][payment_method_id]:
                    amount = sepa_income[key][payment_method_id]
                    self.create_bank_line(key, payment_method_id, amount, acc_id, 'normal')
        return True
    
    def _protected_payment_bank_lines(self, amount, amount_prot, sepa_income, default_payment_method):
        # izdvojimo dodatke za zasticeni racun s posebnom sifrom, ostatak iznosa ide na zasticeni racun sa sifrom 110
        # izdvojimo dodatke za redovni racun s posebnom sifrom, ostatak iznos ide na redovni racun sa sifom 120
        acc_id = self.bank_account_id.id
        prot_acc_id = self.protected_bank_account_id.id
        dodaci_red = 0
        dodaci_zast = 0
        for key in sepa_income:
            for payment_method_id in sepa_income[key]:
                if key[2] == 'protected':
                    dodaci_zast += sepa_income[key][payment_method_id]
                else:
                    dodaci_red += sepa_income[key][payment_method_id]
        redovni = amount - dodaci_red
        zasticeni = amount_prot - dodaci_zast
        line_desc = self.payslip_run_id.name + ' zasticeni racun'
        self.create_bank_line((line_desc, '110'), default_payment_method.id, zasticeni, prot_acc_id, 'protected')
        self.create_bank_line((self.payslip_run_id.name, '120'), default_payment_method.id, redovni, acc_id, 'normal')
        for key in sepa_income:
            for payment_method_id in sepa_income[key]:
                if sepa_income[key][payment_method_id]:
                    amount = sepa_income[key][payment_method_id]
                    if key[2] == 'protected':
                        self.create_bank_line(key, payment_method_id, amount, prot_acc_id, 'protected')
                    else:
                        self.create_bank_line(key, payment_method_id, amount, acc_id, 'normal')
        return True
    
    def get_bank_line_code(self, account_type, code):
        """
        Some salary rules have different receipt codes for SEPA file depending on whether employee has protected account.
        For these rules we have code mapping (regular: protected) so we use this method to decide which code is used.
        """
        if account_type == 'protected' and code in paycom._SEPA_PROTECTED_ACCOUNT_INCOME_CODES_MAPPING.keys():
            return paycom._SEPA_PROTECTED_ACCOUNT_INCOME_CODES_MAPPING[code]
        return code

    def create_bank_line(self, data, payment_method_id, amount, account_id, acc_type):
        """
        Isplata na tekuci ili ziro racun - ispunjavamo sva polja.
        U suprotnom ne ispunjavamo sifru primitka, iban i vrstu racuna jer se stavke ne isplacuju.
        """
        bank_line_obj = self.env['hr.payslip.bank.line']
        code = self.get_bank_line_code(acc_type, data[1])
        bank_line_data = {
            'payslip_id': self.id,
            'description': data[0],
            'code': code,
            'amount': amount,
            'bank_account_id': account_id,
            'acc_type': acc_type,
        }
        if payment_method_id:
            bank_line_data.update({'payment_method_id': payment_method_id})
            method = self.env['l10n.hr.joppd.sifre'].browse(payment_method_id)
            if method.name not in ['1', '2']:
                bank_line_data.update({
                    'bank_account_id': False,
                    'acc_type': False,
                    'code': False,
                })
        bank_line_obj.create(bank_line_data)
        return True

    def _get_ip1_report_base_filename(self):
        self.ensure_one()
        return _('IP1 form - %s') % (self.name)

    def _get_io1_report_base_filename(self):
        self.ensure_one()
        return _('IO1 form - %s') % (self.name)
    
    def _get_no1_report_base_filename(self):
        self.ensure_one()
        return _('NO1 form - %s') % (self.name)

    def _get_zpn1_report_base_filename(self):
        self.ensure_one()
        return _('ZPN1 form - %s') % (self.name)

    def _get_np1_report_base_filename(self):
        self.ensure_one()
        return _('NP1 form - %s') % (self.name)

    def action_send_by_email(self):
        """
        Send payslips by email.
        Notify user when sending has failed.
        Mail ID is written to payslip when sent.
        Mail state is used to color payslips which were not successfully sent.
        Known issues:
        - mail is marked as sent as soon as recipient mail address is in valid format, e.g. x@y.z
        """
        template_xmlid = 'l10n_hr_hr_payroll.hr_payslip_email_template'
        mail_obj = self.env['mail.mail']
        template_id = self.env.ref(template_xmlid)
        if not template_id:
            raise ValidationError(_('E-mails can not be sent because there is no template for payslip!'))
        failed_slips = []
        for slip in self:
            mail_id = template_id.send_mail(slip.id, force_send=True)
            slip.write({'mail_id': mail_id})
            if mail_obj.browse(mail_id).state != 'sent':
                failed_slips.append(slip)
        if failed_slips:
            title = _('Warning!')
            msg = _('Some mails were not sent:<br/>{0}').format(
                '<br/>'.join(['{0} {1}'.format(slip.number, slip.name) for slip in failed_slips])
            )
            self.env.user.notify_warning(msg, title, sticky=True)
        return True
    
    def annual_tax_calculation(self):
        """
        Annual tax calculation.
        Iterate through all payslips from whole year for this employee if the employee is on current (12 month) payslip.
        Only regular salary and salary in kind are included.
        """
        PayslipRun = self.env['hr.payslip.run']
        payslip_run = self.payslip_run_id
        pay_date = payslip_run.pay_date
        company = self.env.user.company_id

        max_pay_date = str(pay_date.year) + '-12-31'
        min_pay_date = str(pay_date.year) + '-01-01'

        emp_ids = self.employee_id.ids
        slip_ids = payslip_run.annual_calculation_get_payslips(emp_ids, min_pay_date, max_pay_date)
        data = payslip_run.annual_calculation_get_employee_payslips_data(slip_ids, company, max_pay_date, self)
        tolerance = self.payslip_run_id.payslips_without_tax_return_tolerance
        payslip_run.annual_calculation_create_tax_difference_payslips(data, company, payslip_run, min_pay_date, max_pay_date, tolerance)
        return True
    
    def print_ip1_report(self):
        report_id = 'l10n_hr_hr_payroll.ip1_form_report'
        return self.env.ref(report_id).report_action(self.id)

    def print_io1_report(self):
        report_id = 'l10n_hr_hr_payroll.io1_report'
        return self.env.ref(report_id).report_action(self.id)

    @api.model
    def _get_payslip_lines(self, contract_ids, payslip_id):
        """
        Method copied from source to make some changes:
            1. added states parameter to sum method in Payslips class
            2. added amount_on_payslip_run method to Payslips class
                - sums payslip lines with given code on payslips from same employee on same payslip run
                    which are calculated before current payslip
            3. added get_suspension_calculated_amount method to Payslips class
                - copy of same method from hr.payslip.class
        """
        def _sum_salary_rule_category(localdict, category, amount):
            if category.parent_id:
                localdict = _sum_salary_rule_category(localdict, category.parent_id, amount)
            localdict['categories'].dict[category.code] = category.code in localdict['categories'].dict and localdict['categories'].dict[category.code] + amount or amount
            return localdict

        class BrowsableObject(object):
            def __init__(self, employee_id, dict, env):
                self.employee_id = employee_id
                self.dict = dict
                self.env = env

            def __getattr__(self, attr):
                return attr in self.dict and self.dict.__getitem__(attr) or 0.0

        class InputLine(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(amount) as sum
                    FROM hr_payslip as hp, hr_payslip_input as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()[0] or 0.0

        class WorkedDays(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""
            def _sum(self, code, from_date, to_date=None):
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""
                    SELECT sum(number_of_days) as number_of_days, sum(number_of_hours) as number_of_hours
                    FROM hr_payslip as hp, hr_payslip_worked_days as pi
                    WHERE hp.employee_id = %s AND hp.state = 'done'
                    AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pi.payslip_id AND pi.code = %s""",
                    (self.employee_id, from_date, to_date, code))
                return self.env.cr.fetchone()

            def sum(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[0] or 0.0

            def sum_hours(self, code, from_date, to_date=None):
                res = self._sum(code, from_date, to_date)
                return res and res[1] or 0.0

        class Payslips(BrowsableObject):
            """a class that will be used into the python code, mainly for usability purposes"""

            def sum(self, code, from_date, to_date=None, states=None):
                """
                States parameter is added to enable sums for different states.
                """
                if to_date is None:
                    to_date = fields.Date.today()
                self.env.cr.execute("""SELECT sum(case when hp.credit_note = False then (pl.total) else (-pl.total) end)
                            FROM hr_payslip as hp, hr_payslip_line as pl
                            WHERE hp.employee_id = %s AND hp.state in %s
                            AND hp.date_from >= %s AND hp.date_to <= %s AND hp.id = pl.slip_id AND pl.code = %s""",
                            (self.employee_id, states, from_date, to_date, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0
            
            def amount_on_payslip_run(self, code):
                """
                Sum payslip lines from same payslip run on payslips from same employee which have been calculated before current payslip.
                To do that we need to define a unique order:
                    p1 < p2  <=>  p1.date_from < p2.date_from or (p1.date_from == p2.date_from and p1.id < p2.id)
                """
                query = """
                    SELECT SUM(pl.total)
                    FROM hr_payslip AS hp, hr_payslip_line as pl
                    WHERE hp.employee_id = %s AND 
                    (hp.date_from < %s OR (hp.date_from = %s AND hp.id < %s))
                    AND hp.id = pl.slip_id
                    AND hp.payslip_run_id = %s
                    AND pl.code = %s
                """
                self.env.cr.execute(query, (self.employee_id, self.date_from, self.date_from, self.id, self.payslip_run_id.id, code))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0
            
            def get_suspension_calculated_amount(self, s):
                """
                Copy of method with same name in hr.payslip class.
                Return suspended amount for given suspension on same payslip run (from already calculated payslips).
                """
                query = """
                    SELECT SUM(line.amount)
                    FROM hr_payslip_suspension_line AS line
                    LEFT JOIN hr_payslip AS slip ON slip.id = line.payslip_id
                    WHERE line.suspension_id = %s AND
                    (slip.date_from < %s OR (slip.date_from = %s AND slip.id < %s)) AND
                    slip.payslip_run_id = %s
                """
                self.env.cr.execute(query, (s.id, self.date_from, self.date_from, self.id, self.payslip_run_id.id))
                res = self.env.cr.fetchone()
                return res and res[0] or 0.0
            
        #we keep a dict with the result because a value can be overwritten by another rule with the same code
        result_dict = {}
        rules_dict = {}
        worked_days_dict = {}
        inputs_dict = {}
        blacklist = []
        payslip = self.env['hr.payslip'].browse(payslip_id)
        for worked_days_line in payslip.worked_days_line_ids:
            worked_days_dict[worked_days_line.code] = worked_days_line
        for input_line in payslip.input_line_ids:
            inputs_dict[input_line.code] = input_line

        categories = BrowsableObject(payslip.employee_id.id, {}, self.env)
        inputs = InputLine(payslip.employee_id.id, inputs_dict, self.env)
        worked_days = WorkedDays(payslip.employee_id.id, worked_days_dict, self.env)
        payslips = Payslips(payslip.employee_id.id, payslip, self.env)
        rules = BrowsableObject(payslip.employee_id.id, rules_dict, self.env)

        baselocaldict = {'categories': categories, 'rules': rules, 'payslip': payslips, 'worked_days': worked_days, 'inputs': inputs}
        #get the ids of the structures on the contracts and their parent id as well
        contracts = self.env['hr.contract'].browse(contract_ids)
        if len(contracts) == 1 and payslip.struct_id:
            structure_ids = list(set(payslip.struct_id._get_parent_structure().ids))
        else:
            structure_ids = contracts.get_all_structures()
        #get the rules of the structure and thier children
        rule_ids = self.env['hr.payroll.structure'].browse(structure_ids).get_all_rules()
        #run the rules by sequence
        sorted_rule_ids = [id for id, sequence in sorted(rule_ids, key=lambda x:x[1])]
        sorted_rules = self.env['hr.salary.rule'].browse(sorted_rule_ids)

        for contract in contracts:
            employee = contract.employee_id
            localdict = dict(baselocaldict, employee=employee, contract=contract)
            deductable_base = 0
            for rule in sorted_rules:
                key = rule.code + '-' + str(contract.id)
                localdict['result'] = None
                localdict['result_qty'] = 1.0
                localdict['result_rate'] = 100
                #check if the rule can be applied
                if rule._satisfy_condition(localdict) and rule.id not in blacklist:
                    #compute the amount of the rule
                    amount, qty, rate = rule._compute_rule(localdict)
                    #check if there is already a rule computed with that code
                    previous_amount = rule.code in localdict and localdict[rule.code] or 0.0
                    #set/overwrite the amount computed for this rule in the localdict
                    tot_rule = amount * qty * rate / 100.0
                    # hack for computing UMOSNDOP
                    if rule.is_for_contributions_base_deduction:
                        deductable_base += amount
                    amount, tot_rule = self._compute_base_for_contributions_base_deduction(rule, deductable_base, amount, tot_rule)
                    # /hack
                    localdict[rule.code] = tot_rule
                    rules_dict[rule.code] = rule
                    #sum the amount for its salary category
                    localdict = _sum_salary_rule_category(localdict, rule.category_id, tot_rule - previous_amount)
                    #create/overwrite the rule in the temporary results
                    result_dict[key] = {
                        'salary_rule_id': rule.id,
                        'contract_id': contract.id,
                        'name': rule.name,
                        'code': rule.code,
                        'category_id': rule.category_id.id,
                        'sequence': rule.sequence,
                        'appears_on_payslip': rule.appears_on_payslip,
                        'condition_select': rule.condition_select,
                        'condition_python': rule.condition_python,
                        'condition_range': rule.condition_range,
                        'condition_range_min': rule.condition_range_min,
                        'condition_range_max': rule.condition_range_max,
                        'amount_select': rule.amount_select,
                        'amount_fix': rule.amount_fix,
                        'amount_python_compute': rule.amount_python_compute,
                        'amount_percentage': rule.amount_percentage,
                        'amount_percentage_base': rule.amount_percentage_base,
                        'register_id': rule.register_id.id,
                        'amount': amount,
                        'employee_id': contract.employee_id.id,
                        'quantity': qty,
                        'rate': rate,
                    }
                else:
                    #blacklist this rule and its children
                    blacklist += [id for id, seq in rule._recursive_search_of_rules()]

        return list(result_dict.values())
    
    def _compute_base_for_contributions_base_deduction(self, rule, deductable_base, amount, tot_rule):
        """ Apply rule for base for contributions base deduction (OSNUMOSNDOP rule): """
        if rule.code != 'OSNUMOSNDOP':
            return amount, tot_rule
        return deductable_base, deductable_base

    
class HrPayslipWorkedDays(models.Model):

    _inherit = 'hr.payslip.worked_days'
    
    # all categories whose parent is either EBRT or NET
    def _work_days_code_selection(self):        
        res = {}
        
        category_obj = self.env["hr.salary.rule.category"]
        parent_ids = category_obj.search(['|',('code','=','EBRT'),('code','=','NET')])
        if parent_ids:
            # DODN, ODN, DODB, NPIZN are not working days categories, but have NET as parent so we have to disable them
            # PRR, PRN, and PRP rules are disabled so we want to remove their categories from selection as well
            # should be kept in snyc with info3_work_hours_form
            input_cats = self.env['hr.payroll.salary.rule.category.configuration'].get_category('inputs_categories')
            inactive_cats = self.env['hr.payroll.salary.rule.category.configuration'].get_category('inactive_categories')
            category_ids = category_obj.search([('parent_id', 'in', parent_ids.ids),('code', 'not in', input_cats + inactive_cats)])
            res = category_ids.read(['code','name'])
            res = [(r['code'], r['code'] + ' - ' + r['name']) for r in res]
        res = sorted(res)
        return res
    
    def _get_category_domain(self):
        return [
            ('parent_id.code', 'in', self.env['hr.payroll.salary.rule.category.configuration'].get_category('worked_days_parent_categories')),
            ('code', 'not in', self.env['hr.payroll.salary.rule.category.configuration'].get_category('inputs_categories')),
            ('code', 'not in', self.env['hr.payroll.salary.rule.category.configuration'].get_category('inactive_categories'))
        ]
    
    code = fields.Selection(_work_days_code_selection,'Kod')
    name = fields.Char('Opis', size=256, required=False)
    category_id = fields.Many2one(
        'hr.salary.rule.category', 'Naziv',
        domain=lambda self: self._get_category_domain()
    )

    @api.onchange('category_id')
    def on_change_category(self):                        
        cat_obj = self.env["hr.salary.rule.category"]
        values = {}
        if self.category_id:
            cat = self.category_id
            self.code = cat['code']
            self.name = cat['name']
        elif self.code != False:
            cat = cat_obj.search([("code", "=", self.code)])[0]
            self.category_id = cat.id
            self.name = cat.name
       
    # #on change code return name of category 
    @api.onchange('code')
    def on_change_code(self):
        values = {}           
        cat_obj = self.env["hr.salary.rule.category"]
        cat_ids = cat_obj.search([('code','=',self.code)])

        if len(cat_ids) > 0:
            cat = cat_ids[0]
            self.category_id = cat['id']
            self.name = cat['name']
        elif self.category_id != False: 
            cat = self.category_id
            self.code = cat.code
    
    @api.model_create_multi
    def create(self, vals_list):
        """
        Get contract_id from payslip because it is a mandatory field.
        """
        for values in vals_list:
            payslip = self.env["hr.payslip"].browse(values["payslip_id"])
            if "name" in values:
                cat_name = values["name"]
            else:
                cat_name = self.env["hr.salary.rule.category"].browse(values["category_id"]).name
            values.update({
                'contract_id':payslip.contract_id.id,
                'name': cat_name
            })
        return super(HrPayslipWorkedDays, self).create(vals_list)
        
class HrPayslipInput(models.Model):
    _inherit = 'hr.payslip.input'
    
    # @DEV: any changes here should be considered in add_inputs_form as well
    def _input_code_selection(self):
        """
        Show rule joppd_151 code if it exists, alongside rule name and code.
        """
        res=[]
        category_obj = self.env["hr.salary.rule.category"]
        category_ids = category_obj.search([('code', 'in', self.env['hr.payroll.salary.rule.category.configuration'].get_category('inputs_categories'))])
        rule_obj = self.env["hr.salary.rule"]
        if category_ids:
            rules = rule_obj.search([('category_id','in',category_ids.ids),])                                
            # rules = rule_obj.browse(cr, uid, ids, context)
            # context.update({'show_rule_name': True})
            for r in rules:
                joppd_code = r.joppd_b151 and (r.joppd_b151.name + ' - ') or ''
                rule_desc = joppd_code +  r.code + ' - ' + r.name
                res.append((r.code, rule_desc))
        res = sorted(res, key=lambda res: res[1])
        return res
    
    code = fields.Selection(_input_code_selection, 'Kod')

    @api.model_create_multi
    def create(self, vals_list):
        """
        Get contract_id from payslip because it is a mandatory field.
        """
        for values in vals_list:
            payslip = self.env["hr.payslip"].browse(values["payslip_id"])
            values.update({'contract_id': payslip.contract_id.id})
        return super(HrPayslipInput, self).create(vals_list)

    @api.onchange('code')
    def onchange_code(self):
        #set amount to max_child_birth_fee if 'NZRD', else 0
        if self.code == 'NZRD':
            amount = self.payslip_id.i3_config_max_child_birth_fee
        else:
            amount = 0.00
        res = {
            'value': {
                'code': self.code,
                'name': self.get_rule_name(self.code),
                'amount': amount
            }
        }
        return res

    def get_rule_name(self, code):
        rule_obj = self.env['hr.salary.rule']
        rule_name = ''
        rules = rule_obj.search([('code', '=', code)])
        # some rules have duplicates (for netto and brutto structures), but they should all have the same name
        for rule in rules:
            rule_name = rule.name
        return rule_name

    def action_from_netto(self):
        action_rec = self.env['ir.model.data']._xmlid_to_res_model_res_id('l10n_hr_hr_payroll.action_netto_to_brutto_wizard')
        action = self.env['ir.binary']._find_record(res_model=action_rec[0],res_id=action_rec[1])
        slip = self.payslip_id
        is_additional_income = slip.struct_id.code in paycom.get_structures().get('additional_income')
        expenditure_pct = 0
        if slip.struct_id.code == 'HR6':
            expenditure_pct = 30
        if slip.struct_id.code == 'HR7':
            expenditure_pct = 55
        # send default settings from payslip
        used_on_this_payslip_run = slip.amount_on_payslip_run('POROSN')
        donos_osnovice = slip.total_tax_base + used_on_this_payslip_run
        
        category_obj = self.env['hr.salary.rule.category']
        category_ids = category_obj.search([('code', 'in', ['DODN','NPIZN','ODN'])])
        rule_obj = self.env['hr.salary.rule']
        if category_ids:
            rules = rule_obj.search([('category_id','in',category_ids.ids),])

         #if employee has multiple payslips -> sum up deduction amount and use it in netto/brutto calculator
        deduction_amount_all_payslips = slip.amount_on_payslip_run('UMOSNDOP')
        use_manual_contributions_base_deduction = True
        if not deduction_amount_all_payslips and not slip.use_manual_contributions_base_deduction:
            use_manual_contributions_base_deduction = False
        contributions_base_deduction_amount = slip.contributions_base_deduction_amount
        if deduction_amount_all_payslips:
            contributions_base_deduction_amount = slip.hr_config_contributions_base_deduction_fixed_amount - deduction_amount_all_payslips

        action['context'] = {
            # tax_deduction_amount = total tax deduction
            # total_tax_deduction = tax deduction used in current month on paid payslip runs (same as payslip.sum() method in rule calculation)
            # slip.amount_on_payslip_run = tax deduction used on current payslip run in previously calculated payslips
            'default_tax_deduction': slip.tax_deduction_amount - slip.total_tax_deduction - slip.amount_on_payslip_run('IOOD'),
            'default_tax_1_pct': slip.i3_config_razred_1_posto,
            'default_tax_2_pct': slip.i3_config_razred_2_posto,
            'default_tax_1_limit': max(slip.i3_config_razred_1 / 12 - donos_osnovice, 0),
            'default_expenditure_pct': expenditure_pct,
            'default_calc_type': 'additional_income' if is_additional_income else 'salary',
            'default_use_work_exp_bonus': False,
            'default_work_exp_bonus_coef': slip.work_exp_bonus_coef,
            'default_payslip_brutto_salary': slip.wage,
            'default_payslip_netto_fees': sum(slip.input_line_ids.filtered(lambda i: i.code in rules.mapped('code')).mapped('amount')),
            'default_use_manual_contributions_base_deduction': use_manual_contributions_base_deduction,
            'default_contributions_base_deduction_amount': contributions_base_deduction_amount,
            'default_mio2': slip.mio2,
            'default_lower_brutto_contributions_base_deduction_limit': slip.hr_config_contributions_base_deduction_limit_1,
            'default_upper_brutto_contributions_base_deduction_limit': slip.hr_config_contributions_base_deduction_limit_2,
            'default_contribution_base_deduction': slip.hr_config_contributions_base_deduction_fixed_amount,
            'from_payslip_input': True,
            'input_id': self.id,
            'payslip_id': self.payslip_id.id,
        }
        return action.read([])[0]


class HrPayslipLine(models.Model):
    _inherit = 'hr.payslip.line'

    computed_total = fields.Float('Obračunati iznos polja Ukupno', digits=('Payroll'),
                                    help="Ovo polje se koristi za zapisivanje izračunate vrijednosti za slučaj da se iznosi ručno uređuju." )
    total_hrk = fields.Float('Total in HRK', digits=('Payroll'),
        help="Payslip line total in HRK currency. Used for migration to EUR currency specifically for Payslip confirmation report.")

    def _get_computed_total(self, quantity, amount, rate):
        """
        Copy computation of 'total' field (_compute_total method)
        """
        return float(quantity) * amount * rate / 100

    @api.model_create_multi
    def create(self, vals_list):
        """
        Save a copy of computed value of 'total' field in 'computed_total'.
        """
        for values in vals_list:
            if 'quantity' in values and 'amount' in values and 'rate' in values:
                quantity = values.get('quantity')
                amount = values.get('amount')
                rate = values.get('rate')
                values.update({'computed_total': self._get_computed_total(quantity, amount, rate)})
        return super(HrPayslipLine, self).create(vals_list)
